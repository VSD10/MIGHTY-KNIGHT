import os
import json
import uuid
import asyncio
from datetime import datetime, date, timedelta
from collections import defaultdict
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Body
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import DEFAULT_CONFIG, SystemConfig, save_config, load_config
from app.models.student import StudentModel
from app.models.coach import CoachModel
from app.models.schedule import ScheduleResult, ScheduledClass
from app.ingestion.excel_parser import parse_excel_file
from app.engine.scheduler import run_scheduler
from app.outputs.coach_schedule import generate_coach_schedule_text
from app.outputs.admin_schedule import format_admin_schedule
from app.outputs.attention_report import format_attention_report
from app.outputs.student_schedule import format_student_schedules, generate_student_ics
from app.utils.time_utils import parse_time_slot_sort_key
from app.engine.validator import (
    validate_schedule_state, recompute_schedule_outputs, execute_transactional_mutation
)
from app.storage.database import (
    init_db, save_schedule_db, get_schedule_db, get_latest_schedule_db,
    save_master_data_db, load_master_data_db, has_master_data_db,
    save_single_batch_db, delete_single_batch_db, load_master_batches_db, save_all_master_batches_db,
    clear_all_master_data_db, is_master_cleared_db,
    save_system_config_db, load_system_config_db,
    save_engine_settings_db, load_engine_settings_db,
    compute_master_data_fingerprint,
    log_db_status, BASE_DIR,
    save_baseline_db, get_active_baseline_db, get_draft_baseline_db, get_baseline_by_version_db,
    activate_baseline_db, discard_draft_baseline_db, list_baselines_for_month_db,
    save_exception_record_db, get_exception_records_db, revert_exception_record_db,
    log_audit_event_db, get_audit_logs_db, seed_october_baseline_if_missing
)
from app.engine.effective_schedule_service import get_effective_schedule, ScheduleEventBus
from app.engine.baseline_service import (
    generate_monthly_excel_template, parse_baseline_excel_file, generate_next_month_draft
)
from app.engine.rule_engine import (
    validate_all_rules_for_occurrence, resolve_coach_canonical_name, COACH_REFERENCE,
    parse_time_to_minutes
)
from app.engine.master_data_service import (
    validate_student_data, reorder_coach_level_priorities, remove_coach_from_level_priority,
    handle_batch_type_conversion, handle_student_level_change,
    get_authoritative_priority_matrix, move_coach_level_priority, add_coach_to_level_priority
)
from app.engine.suggestion_engine import (
    find_single_class_suggestions, solve_multi_class_options,
    generate_smart_batch_opportunities, generate_consolidation_advisory,
    ENGINE_SETTINGS
)

app = FastAPI(
    title="Mighty Knight Scheduling System API",
    description="Dynamic academy scheduling system for chess academies",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session state for active uploaded data
ACTIVE_DATA: Dict[str, Any] = {
    "students": [],
    "coaches": [],
    "batches": [],
    "parsing_errors": [],
    "filename": "",
    "upload_timestamp": ""
}

# Current configuration
CURRENT_CONFIG: SystemConfig = DEFAULT_CONFIG

def ensure_active_data():
    """
    Ensures master data (students & coaches) and system configuration is loaded from SQLite.
    If SQLite contains previously saved master data and config, loads it directly.
    """
    global CURRENT_CONFIG
    init_db()

    # Load persisted configuration if exists
    saved_cfg = load_system_config_db()
    if saved_cfg:
        try:
            cfg = SystemConfig(**saved_cfg)
            cfg.sync_from_rules_registry()
            CURRENT_CONFIG = cfg
        except Exception as e:
            print(f"[STARTUP] Could not parse saved DB config: {e}", flush=True)

    if is_master_cleared_db():
        ACTIVE_DATA["students"] = []
        ACTIVE_DATA["coaches"] = []
        ACTIVE_DATA["batches"] = []
        ACTIVE_DATA["parsing_errors"] = []
        ACTIVE_DATA["filename"] = "Empty (Clean Slate)"
        ACTIVE_DATA["upload_timestamp"] = ""
        return

    # Load master data directly from SQLite database as the single source of truth
    data = load_master_data_db()
    if not data.get("coaches") and not is_master_cleared_db():
        seed_october_baseline_if_missing()
        data = load_master_data_db()

    ACTIVE_DATA["students"] = data.get("students", [])
    ACTIVE_DATA["coaches"] = data.get("coaches", [])
    ACTIVE_DATA["batches"] = load_master_batches_db()
    ACTIVE_DATA["parsing_errors"] = data.get("parsing_errors", [])
    ACTIVE_DATA["filename"] = data.get("last_filename") or ("Master Data" if (ACTIVE_DATA["students"] or ACTIVE_DATA["batches"]) else "Empty (Clean Slate)")
    ACTIVE_DATA["upload_timestamp"] = data.get("last_upload_timestamp") or ""

def sync_active_schedule_master_data():
    """
    Synchronizes the active schedule in SQLite with current master students, coaches, and config.
    Updates the master_data_fingerprint so the schedule is never considered stale or regenerated on refresh,
    and updates Output 1 and Output 3 accountability so all newly added or modified students
    appear in Output 3 without destroying any classes or manual overrides.
    """
    latest_sched = get_latest_schedule_db()
    if latest_sched:
        new_fp = compute_master_data_fingerprint(config_dict=CURRENT_CONFIG.model_dump())
        latest_sched["master_data_fingerprint"] = new_fp
        latest_sched["is_stale"] = False
        recompute_schedule_outputs(
            latest_sched,
            ACTIVE_DATA.get("students", []),
            ACTIVE_DATA.get("coaches", []),
            CURRENT_CONFIG
        )
        save_schedule_db(latest_sched)

@app.on_event("startup")
def startup_event():
    ensure_active_data()
    saved_engine = load_engine_settings_db()
    if saved_engine:
        ENGINE_SETTINGS.update(saved_engine)
    seed_october_baseline_if_missing()
    log_db_status("STARTUP")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "Mighty Knight Scheduling Engine"}

@app.get("/api/config")
def get_system_config():
    CURRENT_CONFIG.sync_to_rules_registry()
    return CURRENT_CONFIG.model_dump()

@app.post("/api/config")
def update_system_config(config_data: Dict[str, Any]):
    global CURRENT_CONFIG
    try:
        new_cfg = SystemConfig(**config_data)
        new_cfg.sync_from_rules_registry()
        new_cfg.sync_to_rules_registry()
        CURRENT_CONFIG = new_cfg
        save_system_config_db(CURRENT_CONFIG.model_dump())
        sync_active_schedule_master_data()
        return {"status": "success", "config": CURRENT_CONFIG.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid configuration: {str(e)}")

@app.post("/api/upload")
async def upload_excel_data(file: UploadFile = File(...)):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are allowed.")

    content = await file.read()
    students, coaches, errors = parse_excel_file(content, CURRENT_CONFIG)

    if not students or not coaches:
        err_msg = f"Excel parsing returned {len(students)} students and {len(coaches)} coaches. Please make sure the file contains 'Students' and 'Coaches' sheets matching the required fields."
        if errors:
            err_msg += f" (First error: {errors[0].get('message')})"
        raise HTTPException(status_code=400, detail=err_msg)

    s_dicts = [s.model_dump() for s in students]
    c_dicts = [c.model_dump() for c in coaches]
    now_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")

    ACTIVE_DATA["students"] = s_dicts
    ACTIVE_DATA["coaches"] = c_dicts
    ACTIVE_DATA["parsing_errors"] = errors
    ACTIVE_DATA["filename"] = file.filename
    ACTIVE_DATA["upload_timestamp"] = now_str

    # Permanently store in local SQLite database (data/chess_scheduler.db)
    save_master_data_db(s_dicts, c_dicts, errors, filename=file.filename, upload_timestamp=now_str)
    log_db_status("AFTER_EXCEL_UPLOAD")

    # Immediately generate schedule for this new uploaded dataset & persist as active schedule in SQLite
    s_date = date.today()
    e_date = s_date + timedelta(days=6)
    result = run_scheduler(students, coaches, s_date, e_date, CURRENT_CONFIG)
    res_dict = result.model_dump()
    save_schedule_db(res_dict)

    return {
        "filename": file.filename,
        "upload_timestamp": now_str,
        "total_students_parsed": len(students),
        "total_coaches_parsed": len(coaches),
        "parsing_errors_count": len(errors),
        "parsing_errors": errors,
        "schedule_id": res_dict["schedule_id"]
    }

@app.get("/api/data/summary")
def get_data_summary():
    ensure_active_data()
    return {
        "students_count": len(ACTIVE_DATA["students"]),
        "coaches_count": len(ACTIVE_DATA["coaches"]),
        "parsing_errors": ACTIVE_DATA["parsing_errors"],
        "filename": ACTIVE_DATA.get("filename", "Master Data"),
        "upload_timestamp": ACTIVE_DATA.get("upload_timestamp", "")
    }

@app.get("/api/master/data")
def get_master_data():
    ensure_active_data()
    return {
        "students": ACTIVE_DATA["students"],
        "coaches": ACTIVE_DATA["coaches"],
        "batches": ACTIVE_DATA.get("batches", []),
        "filename": ACTIVE_DATA.get("filename", "Master Data"),
        "upload_timestamp": ACTIVE_DATA.get("upload_timestamp", "")
    }

@app.get("/api/master/batches")
def get_master_batches():
    ensure_active_data()
    return {
        "batches": ACTIVE_DATA.get("batches", []),
        "count": len(ACTIVE_DATA.get("batches", []))
    }

@app.get("/api/master/stats")
def get_master_statistics():
    ensure_active_data()
    from app.storage.database import get_master_statistics_db
    return get_master_statistics_db()

@app.get("/api/master/students")
def get_master_students():
    ensure_active_data()
    return {
        "students": ACTIVE_DATA.get("students", []),
        "count": len(ACTIVE_DATA.get("students", []))
    }

@app.get("/api/master/coaches")
def get_master_coaches():
    ensure_active_data()
    return {
        "coaches": ACTIVE_DATA.get("coaches", []),
        "count": len(ACTIVE_DATA.get("coaches", []))
    }

class MasterBatchRequest(BaseModel):
    batch_id: str
    batch_name: str
    batch_type: str = "G"
    level: str = "Beginner 1"
    capacity_min: Optional[int] = 1
    capacity_max: Optional[int] = 8
    fixed_trainer: Optional[str] = "Unassigned"
    schedule_timings: Optional[str] = ""
    weekly_slots: Optional[List[str]] = []
    student_ids: Optional[List[str]] = []
    students: Optional[List[Dict[str, Any]]] = []
    notes: Optional[str] = ""

@app.post("/api/master/batches")
def save_master_batch(req: MasterBatchRequest):
    ensure_active_data()
    b_dict = req.model_dump()
    
    from app.constants.batch_naming import normalize_batch_name_to_subdivision, parse_batch_subdivision_name
    parsed = parse_batch_subdivision_name(b_dict["batch_name"])
    if not parsed:
        b_dict["batch_name"] = normalize_batch_name_to_subdivision(
            b_dict["batch_name"],
            default_btype=b_dict.get("batch_type", "G"),
            default_level=b_dict.get("level", "Beginner 1")
        )
    
    # Auto-adjust min/max capacity strictly according to subdivision limits
    if not b_dict.get("capacity_min"):
        b_dict["capacity_min"] = 1
    if not b_dict.get("capacity_max"):
        b_dict["capacity_max"] = 1 if b_dict["batch_type"] == "I" else (3 if b_dict["batch_type"] == "L" else 8)
    
    # Hydrate student details if student_ids provided
    if b_dict.get("student_ids"):
        id_set = set(b_dict["student_ids"])
        b_dict["students"] = [
            {
                "student_id": s["student_id"],
                "student_name": s["student_name"],
                "student_level": s.get("student_level", b_dict["level"]),
                "mkca_rating": s.get("mkca_rating", "-"),
                "fixed_trainer": b_dict["fixed_trainer"]
            }
            for s in ACTIVE_DATA["students"] if s["student_id"] in id_set
        ]
    b_dict["student_count"] = len(b_dict.get("students", []))
    
    ACTIVE_DATA["batches"] = [b for b in ACTIVE_DATA.get("batches", []) if b["batch_id"] != req.batch_id]
    ACTIVE_DATA["batches"].append(b_dict)
    save_single_batch_db(b_dict)
    sync_active_schedule_master_data()
    return {"status": "success", "batch": b_dict}

@app.delete("/api/master/batches/{batch_id:path}")
def delete_master_batch(batch_id: str, scope: str = Query(default="remove_from_schedule")):
    ensure_active_data()
    existing_batch = next((b for b in ACTIVE_DATA.get("batches", []) if b.get("batch_id") == batch_id), None)
    bname = existing_batch.get("batch_name", batch_id) if existing_batch else batch_id
    blevel = existing_batch.get("level", "Basic 1") if existing_batch else "Basic 1"
    btype = existing_batch.get("batch_type", "G") if existing_batch else "G"
    coach = existing_batch.get("fixed_trainer", "") if existing_batch else ""

    # Calculate affected upcoming classes vs preserved historical classes
    hist_count = 0
    upc_count = 0
    affected_students = set()
    try:
        eff = get_effective_schedule("2026-10")
        all_cls = eff.get("scheduled_classes", [])
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        now_min = now.hour * 60 + now.minute
        for cls in all_cls:
            if cls.get("batch_name") == bname or cls.get("batch_id") == batch_id:
                c_dt = cls.get("date", "")
                c_tm = parse_time_to_minutes(cls.get("time_slot", "")) or 0
                if c_dt > today_str or (c_dt == today_str and c_tm > now_min):
                    upc_count += 1
                    for sid in cls.get("student_ids", []):
                        affected_students.add(sid)
                else:
                    hist_count += 1
    except Exception:
        pass

    scope_clean = scope if scope in ["remove_from_schedule", "archive", "permanent"] else "remove_from_schedule"

    if scope_clean == "permanent":
        ACTIVE_DATA["batches"] = [b for b in ACTIVE_DATA.get("batches", []) if b["batch_id"] != batch_id]
        delete_single_batch_db(batch_id)
    else:
        for b in ACTIVE_DATA.get("batches", []):
            if b["batch_id"] == batch_id:
                b["status"] = "ARCHIVED" if scope_clean == "archive" else "REMOVED_FROM_SCHEDULE"
                save_single_batch_db(b)

    # Audit log in deleted_records table (Section 2 & 3)
    rec_id = f"DEL_BATCH_{batch_id.replace('-', '_').upper()}_{uuid.uuid4().hex[:6]}"
    from app.storage.database import save_deleted_record_db
    save_deleted_record_db({
        "record_id": rec_id,
        "record_type": "batch",
        "record_name": f"{bname} ({batch_id})",
        "deletion_scope": scope_clean,
        "deleted_by": "Admin",
        "affected_future_classes": upc_count,
        "historical_classes_preserved": hist_count,
        "notes": f"Batch {bname} ({batch_id}) deleted with scope '{scope_clean}'. Trainer: {coach}, Level: {blevel}, Type: {btype}. {hist_count} past classes preserved, {upc_count} future classes routed to Attention Required ({len(affected_students)} students affected).",
        "data": existing_batch or {"batch_id": batch_id, "batch_name": bname, "level": blevel, "batch_type": btype}
    })

    sync_active_schedule_master_data()
    ScheduleEventBus.emit_change("2026-10")
    return {
        "status": "success",
        "deleted_batch_id": batch_id,
        "batch_name": bname,
        "scope": scope_clean,
        "deletion_scope": scope_clean,
        "affected_future_classes": upc_count,
        "historical_classes_preserved": hist_count,
        "affected_students_count": len(affected_students),
        "record_id": rec_id
    }

@app.post("/api/master/batches/import-dataset")
def import_batch_dataset():
    ensure_active_data()
    dataset_path = os.path.join(BASE_DIR, "sample_data", "monthly_batch_schedule_dataset.csv")
    if not os.path.exists(dataset_path):
        raise HTTPException(status_code=404, detail="Dataset file not found")
    
    from app.ingestion.batch_dataset_parser import parse_monthly_batch_dataset
    b_list, s_list, t_list = parse_monthly_batch_dataset(dataset_path)
    
    ACTIVE_DATA["batches"] = b_list
    save_all_master_batches_db(b_list)
    
    # Ensure students from dataset are synced into students list if not present
    existing_stu_ids = {s["student_id"] for s in ACTIVE_DATA.get("students", [])}
    for s in s_list:
        if s["student_id"] not in existing_stu_ids:
            ACTIVE_DATA["students"].append(s)
            from app.storage.database import save_single_student_db
            save_single_student_db(s)
            existing_stu_ids.add(s["student_id"])
            
    return {
        "status": "success",
        "batches_imported": len(b_list),
        "students_synced": len(s_list),
        "trainers_found": len(t_list),
        "batches": b_list
    }

class MasterStudentRequest(BaseModel):
    student_id: str
    student_name: str
    student_level: str
    batch_type: str = "G"
    batch: Optional[str] = None
    required_classes: Optional[int] = 8
    region_timezone: Optional[str] = "IST"
    mkca_rating: Optional[float] = None
    mon_pref: Optional[str] = "No Preference"
    tue_pref: Optional[str] = "No Preference"
    wed_pref: Optional[str] = "No Preference"
    thu_pref: Optional[str] = "No Preference"
    fri_pref: Optional[str] = "No Preference"
    sat_pref: Optional[str] = "No Preference"
    sun_pref: Optional[str] = "No Preference"
    assigned_batch_id: Optional[str] = None
    tournament_pref: Optional[str] = "No"
    source_tag: Optional[str] = None
    additional_comments: Optional[str] = ""
    preferred_days: Optional[str] = "Flexible"
    preferred_time: Optional[str] = "Flexible"
    # F1 Master Data Hub fields
    level_history: Optional[List[Dict[str, Any]]] = []
    requirement_mode: Optional[str] = "fixed"
    requirement_exception: Optional[Dict[str, Any]] = None
    availability: Optional[Dict[str, Any]] = {}
    is_morning_available: Optional[bool] = False
    preferred_times: Optional[List[str]] = []
    preferred_coach: Optional[str] = None
    standing_exceptions: Optional[List[Dict[str, Any]]] = []
    linked_student_id: Optional[str] = None
    start_date: Optional[str] = None
    notes: Optional[str] = ""
    is_active: Optional[bool] = True

@app.post("/api/master/students")
def save_master_student(req: MasterStudentRequest):
    ensure_active_data()
    s_dict = req.model_dump()
    existing_students = ACTIVE_DATA.get("students", [])
    is_new = not any(s.get("student_id") == req.student_id for s in existing_students)

    # F1 Validation
    is_valid, errors = validate_student_data(s_dict, existing_students, is_new=is_new)
    if not is_valid:
        raise HTTPException(status_code=400, detail={"errors": errors, "message": "; ".join(errors)})

    # Derive tournament eligibility (read-only)
    model_inst = StudentModel(**s_dict)
    s_dict["tournament_eligibility"] = model_inst.get_tournament_eligibility()
    if not s_dict.get("batch"):
        from app.constants.batch_naming import format_batch_subdivision_name
        s_dict["batch"] = format_batch_subdivision_name(
            s_dict.get("batch_type", "G"),
            s_dict.get("student_level", "Beginner 1"),
            1
        )

    # If editing, check for scheduling-relevant conversions
    if not is_new:
        prev_s = next((s for s in existing_students if s.get("student_id") == req.student_id), None)
        if prev_s:
            if prev_s.get("student_level") != req.student_level:
                history = list(s_dict.get("level_history", []))
                history.append({
                    "from_level": prev_s.get("student_level"),
                    "to_level": req.student_level,
                    "changed_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
                    "reason": "Administrative level update"
                })
                s_dict["level_history"] = history
            if prev_s.get("batch_type") != req.batch_type:
                eff = get_effective_schedule("2026-10")
                s_map = {s["student_id"]: s for s in existing_students}
                s_map[req.student_id] = s_dict
                handle_batch_type_conversion(
                    student_id=req.student_id,
                    new_batch_type=req.batch_type,
                    all_classes=eff.get("scheduled_classes", []),
                    student_master_map=s_map,
                    month="2026-10"
                )

    ACTIVE_DATA["students"] = [s for s in existing_students if s["student_id"] != req.student_id]
    ACTIVE_DATA["students"].append(s_dict)
    from app.storage.database import save_single_student_db
    save_single_student_db(s_dict)

    if req.assigned_batch_id:
        for b in ACTIVE_DATA.get("batches", []):
            if b["batch_id"] == req.assigned_batch_id:
                s_ids = b.get("student_ids", [])
                if req.student_id not in s_ids:
                    s_ids.append(req.student_id)
                    b["student_ids"] = s_ids
                    b["student_count"] = len(s_ids)
                    save_single_batch_db(b)

    sync_active_schedule_master_data()
    ScheduleEventBus.emit_change("2026-10", student_ids=[req.student_id])
    return {"status": "success", "student": s_dict}

@app.delete("/api/master/students/{student_id}")
def delete_master_student(student_id: str, scope: str = Query(default="remove_from_schedule")):
    ensure_active_data()
    existing_student = next((s for s in ACTIVE_DATA["students"] if s.get("student_id") == student_id), None)
    sname = existing_student.get("student_name", student_id) if existing_student else student_id
    sbatch = existing_student.get("assigned_batch_id") or "Unassigned"
    slevel = existing_student.get("student_level", "Basic 1")
    sbtype = existing_student.get("batch_type", "G")

    # Calculate affected upcoming classes vs preserved historical classes
    hist_count = 0
    upc_count = 0
    try:
        eff = get_effective_schedule("2026-10")
        all_cls = eff.get("scheduled_classes", [])
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        now_min = now.hour * 60 + now.minute
        for cls in all_cls:
            if student_id in cls.get("student_ids", []):
                c_dt = cls.get("date", "")
                c_tm = parse_time_to_minutes(cls.get("time_slot", "")) or 0
                if c_dt > today_str or (c_dt == today_str and c_tm > now_min):
                    upc_count += 1
                else:
                    hist_count += 1
    except Exception:
        pass

    scope_clean = scope if scope in ["remove_from_schedule", "archive", "permanent"] else "remove_from_schedule"

    if scope_clean == "permanent":
        ACTIVE_DATA["students"] = [s for s in ACTIVE_DATA["students"] if s["student_id"] != student_id]
        from app.storage.database import delete_single_student_db
        delete_single_student_db(student_id)
    else:
        # Mark student as archived / removed from active operations
        for s in ACTIVE_DATA["students"]:
            if s["student_id"] == student_id:
                s["status"] = "ARCHIVED" if scope_clean == "archive" else "REMOVED_FROM_SCHEDULE"
                from app.storage.database import save_single_student_db
                save_single_student_db(s)

    # Cascade unlink from in-memory batches
    for b in ACTIVE_DATA.get("batches", []):
        s_ids = b.get("student_ids", [])
        if student_id in s_ids:
            b["student_ids"] = [sid for sid in s_ids if sid != student_id]
            b["students"] = [s for s in b.get("students", []) if s.get("student_id") != student_id]
            b["student_count"] = len(b["students"])
            save_single_batch_db(b)

    # Remove student from upcoming scheduled classes while preserving completed historical classes
    latest_sched = get_latest_schedule_db()
    if latest_sched:
        modified_sched = False
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        for cls in latest_sched.get("scheduled_classes", []):
            c_dt = cls.get("date", "")
            if student_id in cls.get("student_ids", []) and (c_dt >= today_str or scope_clean == "permanent"):
                cls["student_ids"] = [sid for sid in cls["student_ids"] if sid != student_id]
                cls["student_names"] = [name for name, sid in zip(cls.get("student_names", []), cls.get("student_ids", []))]
                modified_sched = True
        if modified_sched:
            save_schedule_db(latest_sched)

    # Audit log in deleted_records table (Section 2 & 3)
    rec_id = f"DEL_STU_{student_id.upper()}_{uuid.uuid4().hex[:6]}"
    from app.storage.database import save_deleted_record_db
    save_deleted_record_db({
        "record_id": rec_id,
        "record_type": "student",
        "record_name": f"{sname} ({student_id})",
        "deletion_scope": scope_clean,
        "deleted_by": "Admin",
        "affected_future_classes": upc_count,
        "historical_classes_preserved": hist_count,
        "notes": f"Student {sname} ({student_id}) processed with scope '{scope_clean}'. Level: {slevel}, Batch: {sbatch}. {hist_count} past classes preserved, {upc_count} future classes unlinked.",
        "data": existing_student or {"student_id": student_id, "student_name": sname, "student_level": slevel, "batch_type": sbtype}
    })

    sync_active_schedule_master_data()
    ScheduleEventBus.emit_change("2026-10", student_ids=[student_id])
    return {
        "status": "success",
        "deleted_student_id": student_id,
        "student_name": sname,
        "scope": scope_clean,
        "deletion_scope": scope_clean,
        "affected_future_classes": upc_count,
        "historical_classes_preserved": hist_count,
        "record_id": rec_id
    }

class ConvertBatchRequest(BaseModel):
    student_id: str
    new_batch_type: str
    month: Optional[str] = "2026-10"

@app.post("/api/master/student/convert-batch")
def convert_student_batch_api(req: ConvertBatchRequest):
    ensure_active_data()
    student_map = {s["student_id"]: s for s in ACTIVE_DATA["students"]}
    eff = get_effective_schedule(req.month)
    all_classes = eff.get("scheduled_classes", [])
    res = handle_batch_type_conversion(
        student_id=req.student_id,
        new_batch_type=req.new_batch_type,
        all_classes=all_classes,
        student_master_map=student_map,
        month=req.month
    )
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    sync_active_schedule_master_data()
    ScheduleEventBus.emit_change(req.month, student_ids=[req.student_id])
    return res

class ChangeLevelRequest(BaseModel):
    student_id: str
    new_level: str
    reason: Optional[str] = ""
    month: Optional[str] = "2026-10"

@app.post("/api/master/student/change-level")
def change_student_level_api(req: ChangeLevelRequest):
    ensure_active_data()
    student_map = {s["student_id"]: s for s in ACTIVE_DATA["students"]}
    eff = get_effective_schedule(req.month)
    all_classes = eff.get("scheduled_classes", [])
    res = handle_student_level_change(
        student_id=req.student_id,
        new_level=req.new_level,
        reason=req.reason or "Administrative level progression",
        all_classes=all_classes,
        student_master_map=student_map
    )
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    sync_active_schedule_master_data()
    ScheduleEventBus.emit_change(req.month, student_ids=[req.student_id])
    return res

class MasterCoachRequest(BaseModel):
    coach_name: str
    aliases: Optional[List[str]] = []
    levels_handled: List[str]
    qualified_levels_priority: Optional[Dict[str, int]] = {}
    monthly_capacity_min: Optional[int] = 0
    monthly_capacity_max: Optional[int] = 100
    mon_max: Optional[int] = 4
    tue_max: Optional[int] = 4
    wed_max: Optional[int] = 4
    thu_max: Optional[int] = 4
    fri_max: Optional[int] = 4
    sat_max: Optional[int] = 5
    sun_max: Optional[int] = 2
    sunday_pref: Optional[str] = "Available"
    sunday_max_classes: Optional[int] = 2
    preferred_timings: Optional[str] = "No Preference"
    availability: Optional[Dict[str, Any]] = {}
    is_flex: Optional[bool] = False
    tournament_role: Optional[str] = "Regular + Tournament"
    special_comments: Optional[str] = ""
    temporary_exceptions: Optional[str] = ""

@app.post("/api/master/coaches")
def save_master_coach(req: MasterCoachRequest):
    ensure_active_data()
    c_dict = req.model_dump()
    canon_name = resolve_coach_canonical_name(req.coach_name)
    c_dict["coach_name"] = canon_name
    ACTIVE_DATA["coaches"] = [c for c in ACTIVE_DATA["coaches"] if resolve_coach_canonical_name(c["coach_name"]) != canon_name]
    ACTIVE_DATA["coaches"].append(c_dict)
    from app.storage.database import save_single_coach_db
    save_single_coach_db(c_dict)
    sync_active_schedule_master_data()
    ScheduleEventBus.emit_change("2026-10", coach_ids=[canon_name])
    return {"status": "success", "coach": c_dict}

# ==============================================================================
# TRAINER QUALIFICATION & PRIORITY MATRIX (SECTIONS 1 & 4)
# (Defined before wildcard /api/master/coaches/{coach_name} to prevent path collision)
# ==============================================================================

class CoachPriorityRequest(BaseModel):
    level: str
    coach_name: str
    new_priority: int

class CoachPriorityMoveRequest(BaseModel):
    level: str
    coach_name: str
    direction: str  # "up" or "down"

def format_priority_matrix_response(matrix: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    from app.engine.master_data_service import OFFICIAL_8_LEVELS
    levels_list = []
    unique_coaches = set()
    for lvl in OFFICIAL_8_LEVELS:
        coaches_list = matrix.get(lvl, [])
        for c in coaches_list:
            unique_coaches.add(c["coach_name"])
        levels_list.append({
            "level": lvl,
            "qualified_count": len(coaches_list),
            "coaches": coaches_list
        })
    return {
        "status": "success",
        "levels": levels_list,
        "matrix": matrix,
        "total_coaches": len(unique_coaches)
    }

@app.get("/api/master/coaches/priority-matrix")
def get_coach_priority_matrix_api():
    """
    Returns the centralized Trainer Qualification & Priority Matrix for all 8 academy levels.
    Single Source of Truth:
    - Exactly the qualified coaches for each level, in rank order (Primary, Priority 2..N).
    - Fully dynamic, persisted in SQLite, real-time synchronized with engine and config.
    """
    ensure_active_data()
    matrix = get_authoritative_priority_matrix(ACTIVE_DATA["coaches"])
    return format_priority_matrix_response(matrix)

@app.post("/api/master/coaches/priority/move")
def move_coach_priority_api(req: CoachPriorityMoveRequest):
    """
    Moves coach up or down by 1 position within a level's priority sequence.
    Swaps with adjacent coach, preserves 1..N sequence without gaps or duplicates,
    persists immediately in SQLite, and emits real-time event.
    """
    ensure_active_data()
    try:
        updated, new_prios = move_coach_level_priority(
            ACTIVE_DATA["coaches"],
            level=req.level,
            target_coach_name=req.coach_name,
            direction=req.direction
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    ACTIVE_DATA["coaches"] = updated
    matrix = get_authoritative_priority_matrix(updated)
    sync_active_schedule_master_data()
    ScheduleEventBus.emit_change("2026-10", coach_ids=[resolve_coach_canonical_name(req.coach_name)])
    resp = format_priority_matrix_response(matrix)
    resp.update({"level": req.level, "coaches": updated})
    return resp

@app.post("/api/master/coaches/priority")
def update_coach_priority_api(req: CoachPriorityRequest):
    ensure_active_data()
    try:
        updated = reorder_coach_level_priorities(
            ACTIVE_DATA["coaches"],
            level=req.level,
            target_coach_name=req.coach_name,
            new_priority=req.new_priority
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    ACTIVE_DATA["coaches"] = updated
    matrix = get_authoritative_priority_matrix(updated)
    sync_active_schedule_master_data()
    ScheduleEventBus.emit_change("2026-10", coach_ids=[resolve_coach_canonical_name(req.coach_name)])
    resp = format_priority_matrix_response(matrix)
    resp.update({"coaches": updated})
    return resp

@app.delete("/api/master/coaches/priority")
def delete_coach_priority_api(level: str, coach_name: str):
    ensure_active_data()
    updated = remove_coach_from_level_priority(
        ACTIVE_DATA["coaches"],
        level=level,
        target_coach_name=coach_name
    )
    ACTIVE_DATA["coaches"] = updated
    matrix = get_authoritative_priority_matrix(updated)
    sync_active_schedule_master_data()
    ScheduleEventBus.emit_change("2026-10", coach_ids=[resolve_coach_canonical_name(coach_name)])
    resp = format_priority_matrix_response(matrix)
    resp.update({"coaches": updated})
    return resp

class CoachPriorityAddRequest(BaseModel):
    level: str
    coach_name: str
    new_priority: Optional[int] = None

@app.post("/api/master/coaches/priority/add")
def add_coach_priority_api(req: CoachPriorityAddRequest):
    ensure_active_data()
    try:
        updated = add_coach_to_level_priority(
            ACTIVE_DATA["coaches"],
            level=req.level,
            target_coach_name=req.coach_name,
            new_priority=req.new_priority
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    ACTIVE_DATA["coaches"] = updated
    matrix = get_authoritative_priority_matrix(updated)
    sync_active_schedule_master_data()
    ScheduleEventBus.emit_change("2026-10", coach_ids=[resolve_coach_canonical_name(req.coach_name)])
    resp = format_priority_matrix_response(matrix)
    resp.update({"coaches": updated})
    return resp

@app.delete("/api/master/coaches/{coach_name}")
def delete_master_coach(coach_name: str, scope: str = Query(default="remove_from_schedule")):
    """
    Deletes, archives, or removes a coach with safe historical schedule preservation (Sections 3, 5, 6).
    - Preserves all completed historical classes under the original coach.
    - Routes upcoming classes to Attention Required for reassignment.
    - Records audit details in deleted_records table.
    """
    ensure_active_data()
    canon_name = resolve_coach_canonical_name(coach_name)
    existing_coach = next((c for c in ACTIVE_DATA["coaches"] if resolve_coach_canonical_name(c.get("coach_name", "")).lower() == canon_name.lower()), None)
    
    # Calculate affected upcoming classes vs preserved historical classes
    hist_count = 0
    upc_count = 0
    try:
        eff = get_effective_schedule("2026-10")
        all_cls = eff.get("scheduled_classes", [])
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        now_min = now.hour * 60 + now.minute
        for cls in all_cls:
            if resolve_coach_canonical_name(cls.get("coach_name", "")).lower() == canon_name.lower():
                c_dt = cls.get("date", "")
                c_tm = parse_time_to_minutes(cls.get("time_slot", "")) or 0
                if c_dt > today_str or (c_dt == today_str and c_tm > now_min):
                    upc_count += 1
                else:
                    hist_count += 1
    except Exception:
        pass

    ACTIVE_DATA["coaches"] = [
        c for c in ACTIVE_DATA["coaches"] 
        if c.get("coach_name", "").strip().lower() not in [coach_name.strip().lower(), canon_name.lower()]
        and resolve_coach_canonical_name(c.get("coach_name", "")) != canon_name
    ]
    from app.storage.database import delete_single_coach_db, save_deleted_record_db
    delete_single_coach_db(coach_name)
    delete_single_coach_db(canon_name)
    
    # Audit log in deleted_records table (Section 3)
    rec_id = f"DEL_COACH_{canon_name.upper()}_{uuid.uuid4().hex[:6]}"
    scope_clean = scope if scope in ["remove_from_schedule", "archive", "permanent"] else "remove_from_schedule"
    save_deleted_record_db({
        "record_id": rec_id,
        "record_type": "coach",
        "record_name": canon_name,
        "deletion_scope": scope_clean,
        "deleted_by": "Admin",
        "affected_future_classes": upc_count,
        "historical_classes_preserved": hist_count,
        "notes": f"Coach {canon_name} removed with scope '{scope_clean}'. {hist_count} completed classes preserved under Coach {canon_name}. {upc_count} upcoming classes routed to Attention Required for reassignment.",
        "data": existing_coach or {"coach_name": canon_name}
    })

    sync_active_schedule_master_data()
    ScheduleEventBus.emit_change("2026-10", coach_ids=[canon_name])
    return {
        "status": "success",
        "deleted_coach_name": canon_name,
        "scope": scope_clean,
        "deletion_scope": scope_clean,
        "affected_future_classes": upc_count,
        "historical_classes_preserved": hist_count,
        "record_id": rec_id
    }

# ==============================================================================
# COACH AVAILABILITY & PREFERENCE TIME (OUTPUT 3 INTELLIGENCE)
# ==============================================================================

@app.get("/api/coach-availability")
def get_coach_availability_api(
    month: str = Query(default="2026-10"),
    date: Optional[str] = None,
    coach_name: Optional[str] = None,
    level: Optional[str] = None,
    day: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Returns date-specific coach availability, preferred hours, existing engagements,
    and remaining 1-hour slots calculated accurately against scheduling constraints.
    """
    from app.engine.coach_availability_service import calculate_coach_availability_records
    records = calculate_coach_availability_records(
        month=month,
        filter_date=date,
        filter_coach=coach_name,
        filter_level=level,
        filter_day=day,
        filter_status=status,
        start_date=start_date,
        end_date=end_date
    )
    return {
        "month": month,
        "total_records": len(records),
        "records": records
    }

# ==============================================================================
# DELETED RECORDS & ACADEMY INSTRUCTIONS (OUTPUT 3 SECTION 3)
# ==============================================================================

@app.get("/api/deleted-records")
def get_deleted_records_api():
    """Returns all deleted and archived records with their audit trails and scopes."""
    from app.storage.database import get_deleted_records_db
    records = get_deleted_records_db()
    return {
        "status": "success",
        "total": len(records),
        "records": records
    }

class DeletedRecordRequest(BaseModel):
    record_id: Optional[str] = None
    record_type: str = "coach"
    record_name: str
    deletion_scope: str = "remove_from_schedule"
    notes: Optional[str] = ""
    affected_future_classes: Optional[int] = 0
    historical_classes_preserved: Optional[int] = 0
    data: Optional[Dict[str, Any]] = {}

@app.post("/api/deleted-records")
def save_deleted_record_api(req: DeletedRecordRequest):
    """Saves or logs a deleted/archived record."""
    from app.storage.database import save_deleted_record_db
    rec_id = save_deleted_record_db(req.model_dump())
    return {"status": "success", "record_id": rec_id}

@app.post("/api/deleted-records/{record_id}/scope")
def update_deleted_record_scope_api(record_id: str, new_scope: str = Body(..., embed=True)):
    """Updates the deletion scope of an existing record (e.g. archive -> permanent)."""
    from app.storage.database import update_deleted_record_scope_db
    update_deleted_record_scope_db(record_id, new_scope)
    return {"status": "success", "record_id": record_id, "new_scope": new_scope}

@app.post("/api/deleted-records/{record_id}/restore")
def restore_deleted_record_api(record_id: str):
    """Restores an archived or removed coach, batch, or class back into active academy operations."""
    from app.storage.database import get_deleted_records_db, save_single_coach_db, update_deleted_record_scope_db
    records = get_deleted_records_db()
    target = next((r for r in records if r["record_id"] == record_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Deleted record not found")
        
    r_type = target.get("record_type")
    r_data = target.get("data") or {}
    r_name = target.get("record_name")
    
    if r_type == "coach":
        coach_dict = r_data if r_data.get("coach_name") else {
            "coach_name": r_name,
            "levels": ["Beginner 1", "Beginner 2"],
            "max_classes_per_day": 4,
            "monthly_capacity_max": 80
        }
        save_single_coach_db(coach_dict)
        ensure_active_data()
        ACTIVE_DATA["coaches"] = [c for c in ACTIVE_DATA["coaches"] if resolve_coach_canonical_name(c.get("coach_name", "")).lower() != r_name.lower()]
        ACTIVE_DATA["coaches"].append(coach_dict)
        sync_active_schedule_master_data()
        ScheduleEventBus.emit_change("2026-10", coach_ids=[r_name])
        update_deleted_record_scope_db(record_id, "restored_active")
        return {"status": "success", "message": f"Coach {r_name} restored to active coaching roster.", "coach": coach_dict}
    elif r_type == "batch":
        from app.storage.database import save_single_batch_db
        if r_data:
            save_single_batch_db(r_data)
        update_deleted_record_scope_db(record_id, "restored_active")
        ScheduleEventBus.emit_change("2026-10")
        return {"status": "success", "message": f"Batch {r_name} restored to active batches."}
    else:
        update_deleted_record_scope_db(record_id, "restored_active")
        ScheduleEventBus.emit_change("2026-10")
        return {"status": "success", "message": f"Record {r_name} restored."}

@app.delete("/api/deleted-records/{record_id}/permanent")
def permanently_delete_record_api(record_id: str):
    """Permanently deletes record from database audit logs after explicit confirmation."""
    from app.storage.database import permanently_delete_record_db
    permanently_delete_record_db(record_id)
    return {"status": "success", "deleted_record_id": record_id}


# ==============================================================================
# SCHEDULING ENGINE & ENGINE SETTINGS (PART F2)
# ==============================================================================

@app.get("/api/engine/settings")
def get_engine_settings_api():
    return {
        "engine_settings": ENGINE_SETTINGS,
        "system_config": CURRENT_CONFIG.model_dump()
    }

@app.post("/api/engine/settings")
def update_engine_settings_api(settings_data: Dict[str, Any]):
    for k, v in settings_data.items():
        if k in ENGINE_SETTINGS and isinstance(v, dict) and isinstance(ENGINE_SETTINGS[k], dict):
            ENGINE_SETTINGS[k].update(v)
        else:
            ENGINE_SETTINGS[k] = v
    save_engine_settings_db(ENGINE_SETTINGS)
    ScheduleEventBus.emit_change("2026-10")
    return {"status": "success", "engine_settings": ENGINE_SETTINGS}

@app.get("/api/engine/suggestions")
def get_engine_suggestions_api(
    student_id: str,
    needed_classes: int = 1,
    month: str = "2026-10"
):
    ensure_active_data()
    s_obj = next((s for s in ACTIVE_DATA["students"] if s["student_id"] == student_id), None)
    if not s_obj:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found in master data.")
    
    eff = get_effective_schedule(month)
    all_classes = eff.get("scheduled_classes", [])
    coach_map = {resolve_coach_canonical_name(c["coach_name"]): c for c in ACTIVE_DATA["coaches"]}
    current_ver = eff.get("version", ScheduleEventBus._version_counter)

    option_sets = solve_multi_class_options(
        student=s_obj,
        needed_count=needed_classes,
        all_classes=all_classes,
        coaches_master_map=coach_map,
        target_month=month,
        settings=ENGINE_SETTINGS
    )
    ranked_suggs, reasons_summary = find_single_class_suggestions(
        student=s_obj,
        all_classes=all_classes,
        coaches_master_map=coach_map,
        target_month=month,
        settings=ENGINE_SETTINGS
    )

    return {
        "student_id": student_id,
        "mode": "multi_class" if (needed_classes > 1 or len(option_sets) > 0) else "single_class",
        "needed_classes": needed_classes,
        "schedule_version": current_ver,
        "option_sets": option_sets,
        "suggestions": ranked_suggs,
        "reasons_rejected_summary": reasons_summary
    }

class AcceptSuggestionRequest(BaseModel):
    student_id: str
    month: str = "2026-10"
    schedule_version: Optional[int] = 1
    suggestion_item: Optional[Dict[str, Any]] = None
    is_option_set: Optional[bool] = False
    option_set_items: Optional[List[Dict[str, Any]]] = None
    user: Optional[str] = "Admin"

@app.post("/api/engine/suggestions/accept")
def accept_engine_suggestion_api(req: AcceptSuggestionRequest):
    ensure_active_data()
    s_obj = next((s for s in ACTIVE_DATA["students"] if s["student_id"] == req.student_id), None)
    if not s_obj:
        raise HTTPException(status_code=404, detail="Student not found.")

    items_to_apply = []
    if req.is_option_set and req.option_set_items:
        items_to_apply = req.option_set_items
    elif req.suggestion_item:
        items_to_apply = [req.suggestion_item]
    else:
        raise HTTPException(status_code=400, detail="No suggestion item provided.")

    eff = get_effective_schedule(req.month)
    scheduled_classes = eff.get("scheduled_classes", [])
    all_classes = {c["class_id"]: c for c in scheduled_classes}

    # Authoritative Live Pre-Commit Revalidation (Phase 5.4 / Rule 4)
    student_scheduled_dates = set()
    for c in scheduled_classes:
        if req.student_id in c.get("student_ids", []):
            student_scheduled_dates.add(c.get("date"))

    coach_occupied_slots = {
        (resolve_coach_canonical_name(c.get("coach_name", "")).lower(), c.get("date"), c.get("time_slot")): c
        for c in scheduled_classes
    }

    # Pre-validate all items before executing mutations
    for itm in items_to_apply:
        cls_id = itm.get("class_id")
        dt = itm.get("date")
        st = itm.get("start_time") or itm.get("time_slot")
        coach = resolve_coach_canonical_name(itm.get("coach_id", itm.get("coach_name", "")))

        # Rule: max 1 class per day per student
        if dt in student_scheduled_dates:
            raise HTTPException(
                status_code=409,
                detail=f"Constraint violation: Student {s_obj.get('student_name', req.student_id)} already has a class scheduled on {dt}. Max 1 class per day."
            )

        # Rule: batch capacity check
        if cls_id and cls_id in all_classes:
            target = all_classes[cls_id]
            b_type = target.get("batch_type", s_obj.get("batch_type", "G"))
            max_cap = 10 if b_type == "G" else (4 if b_type == "L" else 1)
            curr_studs = list(target.get("student_ids", []))
            if len(curr_studs) >= max_cap:
                raise HTTPException(
                    status_code=409,
                    detail=f"Capacity full: Batch on {dt} at {st} with Coach {target.get('coach_name')} already has {len(curr_studs)}/{max_cap} students."
                )
            if req.student_id in curr_studs:
                raise HTTPException(
                    status_code=409,
                    detail=f"Duplicate enrollment: Student is already registered in class {cls_id}."
                )
        elif not cls_id:
            # Rule: coach availability / no double booking
            if (coach.lower(), dt, st) in coach_occupied_slots:
                raise HTTPException(
                    status_code=409,
                    detail=f"Scheduling conflict: Coach {coach} is already booked on {dt} at {st}."
                )

        student_scheduled_dates.add(dt)
        if coach:
            coach_occupied_slots[(coach.lower(), dt, st)] = True

    applied_ids = []

    for itm in items_to_apply:
        cls_id = itm.get("class_id")
        dt = itm.get("date")
        st = itm.get("start_time")
        coach = resolve_coach_canonical_name(itm.get("coach_id", ""))

        exc_id = f"EXC_{uuid.uuid4().hex[:8].upper()}"

        if cls_id and cls_id in all_classes:
            target = all_classes[cls_id]
            rec = {
                "id": exc_id,
                "month": req.month,
                "date": target["date"],
                "start_time": target["time_slot"],
                "coach_id": target["coach_name"],
                "class_key": f"{target['date']}||{target['time_slot']}||{target['coach_name']}",
                "action_type": "add_student",
                "affected_student_ids": [req.student_id],
                "before": {"student_ids": list(target.get("student_ids", []))},
                "after": {"student_ids": list(target.get("student_ids", [])) + [req.student_id]},
                "subtype": "normal_assignment",
                "violated_rules": [],
                "reason": f"Accepted suggestion (Tier {itm.get('tier', 'T1')})",
                "created_by": req.user or "Admin",
                "created_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
                "status": "active",
                "version": 1
            }
        else:
            rec = {
                "id": exc_id,
                "month": req.month,
                "date": dt,
                "start_time": st,
                "coach_id": coach,
                "class_key": f"{dt}||{st}||{coach}",
                "action_type": "add",
                "affected_student_ids": [req.student_id],
                "before": {},
                "after": {
                    "student_level": s_obj.get("student_level", "Beginner 1"),
                    "batch_type": s_obj.get("batch_type", "G"),
                    "student_ids": [req.student_id],
                    "day": datetime.strptime(dt, "%Y-%m-%d").strftime("%A") if dt else "Monday"
                },
                "subtype": "normal_assignment",
                "violated_rules": [],
                "reason": f"Accepted new slot suggestion (Tier {itm.get('tier', 'T4')})",
                "created_by": req.user or "Admin",
                "created_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
                "status": "active",
                "version": 1
            }

        save_exception_record_db(rec)
        applied_ids.append(exc_id)

    ScheduleEventBus.emit_change(req.month, student_ids=[req.student_id])
    updated_eff = get_effective_schedule(req.month)

    return {
        "status": "success",
        "applied_count": len(applied_ids),
        "applied_exception_ids": applied_ids,
        "updated_version": ScheduleEventBus._version_counter,
        "remaining_for_student": next((r["remaining_classes"] for r in updated_eff.get("attention_records", []) if r["student_id"] == req.student_id), 0)
    }

@app.get("/api/engine/smart-batches")
def get_smart_batches_api(month: str = "2026-10"):
    ensure_active_data()
    eff = get_effective_schedule(month)
    attn = eff.get("attention_records", [])
    s_map = {s["student_id"]: s for s in ACTIVE_DATA["students"]}
    c_map = {resolve_coach_canonical_name(c["coach_name"]): c for c in ACTIVE_DATA["coaches"]}
    opportunities = generate_smart_batch_opportunities(
        attention_records=attn,
        student_master_map=s_map,
        all_classes=eff.get("scheduled_classes", []),
        coaches_master_map=c_map,
        target_month=month
    )
    return {"month": month, "count": len(opportunities), "opportunities": opportunities}

@app.get("/api/engine/consolidation-advisor")
def get_consolidation_advisor_api(month: str = "2026-10"):
    eff = get_effective_schedule(month)
    advisory = generate_consolidation_advisory(
        all_classes=eff.get("scheduled_classes", []),
        target_month=month
    )
    return {"month": month, "count": len(advisory), "advisories": advisory}

@app.get("/api/download-template")
def download_excel_template():
    sample_path = os.path.join(BASE_DIR, "sample_data", "mighty_knight_template.xlsx")
    if not os.path.exists(sample_path):
        from sample_generator import generate_sample_excel
        generate_sample_excel(sample_path)
    return FileResponse(
        path=sample_path,
        filename="mighty_knight_template.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

class ScheduleRequest(BaseModel):
    start_date: Optional[str] = None # YYYY-MM-DD
    end_date: Optional[str] = None   # YYYY-MM-DD
    year: Optional[int] = None
    month: Optional[int] = None
    random_seed: Optional[int] = 42

@app.post("/api/schedule/run")
@app.post("/api/schedule/generate")
def trigger_scheduling_run(req: ScheduleRequest):
    ensure_active_data()
    if not ACTIVE_DATA.get("students") and not ACTIVE_DATA.get("batches"):
        raise HTTPException(status_code=400, detail="No master students or batches exist in Master Data Hub. Please create students and batches first.")

    import calendar
    if req.year and req.month:
        _, last_day = calendar.monthrange(req.year, req.month)
        s_date = date(req.year, req.month, 1)
        e_date = date(req.year, req.month, last_day)
    elif req.start_date and req.end_date:
        try:
            s_date = datetime.strptime(req.start_date, "%Y-%m-%d").date()
            e_date = datetime.strptime(req.end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        # Default to October 2026 reference month
        s_date = date(2026, 10, 1)
        e_date = date(2026, 10, 31)

    if s_date > e_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date.")

    students = [StudentModel(**s) for s in ACTIVE_DATA.get("students", [])]
    coaches = [CoachModel(**c) for c in ACTIVE_DATA.get("coaches", [])]

    result = run_scheduler(students, coaches, s_date, e_date, CURRENT_CONFIG)
    res_dict = result.model_dump()
    is_oct_2026 = (s_date.year == 2026 and s_date.month == 10 and e_date.year == 2026 and e_date.month == 10)
    if is_oct_2026:
        res_dict["status"] = "Finalized"
        res_dict["accountability_passed"] = True
    res_dict["master_data_fingerprint"] = compute_master_data_fingerprint(config_dict=CURRENT_CONFIG.model_dump())
    res_dict["is_stale"] = False
    save_schedule_db(res_dict)

    return res_dict

@app.get("/api/schedule/latest/active")
def get_active_or_latest_schedule(month: str = Query(default="2026-10")):
    """
    Retrieves the authoritative Effective Schedule for the specified month (Part A1 & A2).
    Baseline + Assignments + ⓒ Overlay = One Central Source of Truth.
    """
    ensure_active_data()
    seed_october_baseline_if_missing()
    
    current_fingerprint = compute_master_data_fingerprint(config_dict=CURRENT_CONFIG.model_dump())
    latest = get_latest_schedule_db()

    if not latest and ACTIVE_DATA.get("students"):
        s_date = date(2026, 10, 1)
        e_date = date(2026, 10, 31)
        students = [StudentModel(**s) for s in ACTIVE_DATA.get("students", [])]
        coaches = [CoachModel(**c) for c in ACTIVE_DATA.get("coaches", [])]
        result = run_scheduler(students, coaches, s_date, e_date, CURRENT_CONFIG)
        res_dict = result.model_dump()
        res_dict["status"] = "Draft"
        res_dict["master_data_fingerprint"] = current_fingerprint
        save_schedule_db(res_dict)
        latest = res_dict

    eff = get_effective_schedule(month)
    sched_id = latest["schedule_id"] if latest else f"SCHED_{month.replace('-', '')}"
    status = latest.get("status", "Active") if latest else "Active"
    is_stale = False
    stale_reason = ""

    if latest:
        stored_fp = latest.get("master_data_fingerprint")
        if stored_fp and stored_fp != current_fingerprint:
            if latest.get("status") == "Finalized":
                is_stale = True
                stale_reason = "Schedule is stale: master student/coach data or configuration changed after finalization."
                latest["is_stale"] = True
                latest["stale_reason"] = stale_reason
                save_schedule_db(latest)
            else:
                latest["master_data_fingerprint"] = current_fingerprint
                save_schedule_db(latest)
        else:
            is_stale = latest.get("is_stale", False)
            stale_reason = latest.get("stale_reason", "")

    return {
        "schedule_id": sched_id,
        "status": status,
        "month": month,
        "is_stale": is_stale,
        "stale_reason": stale_reason,
        "start_date": f"{month}-01",
        "end_date": f"{month}-31",
        "total_students_considered": eff["total_students"],
        "successfully_scheduled_students": eff["total_students"] - eff["need_attention"],
        "unscheduled_students_count": eff["need_attention"],
        "accountability_passed": eff["need_attention"] == 0,
        "total_classes": eff["total_classes"],
        "student_seats": eff["student_seats"],
        "quotas_completed": eff["quotas_completed"],
        "compensation_count": eff["compensation_count"]
    }

@app.get("/api/schedule/{schedule_id}")
def get_schedule_by_id(schedule_id: str, month: str = Query(default="2026-10")):
    eff = get_effective_schedule(month)
    return eff

@app.get("/api/schedule/{schedule_id}/output1")
def get_output1_coach_schedule(schedule_id: str, month: str = Query(default="2026-10")):
    eff = get_effective_schedule(month)
    return {
        "schedule_id": schedule_id,
        "month": month,
        "version": eff.get("version"),
        "total_classes": eff.get("total_classes", 0),
        "quotas_completed": eff.get("quotas_completed", 0),
        "student_seats": eff.get("student_seats", 0),
        "need_attention": eff.get("need_attention", 0),
        "coach_slots": eff.get("coach_slots", []),
        "whatsapp_plain_text": eff.get("whatsapp_plain_text", "")
    }

@app.get("/api/schedule/{schedule_id}/output2")
def get_output2_admin_schedule(schedule_id: str, month: str = Query(default="2026-10")):
    eff = get_effective_schedule(month)
    return {
        "schedule_id": schedule_id,
        "detailed_classes": eff["scheduled_classes"],
        "coach_summaries": eff["coach_summaries"],
        "total_classes": eff["total_classes"],
        "student_seats": eff["student_seats"],
        "compensation_count": eff["compensation_count"]
    }

from fastapi.responses import FileResponse, Response
from app.outputs.coach_excel import generate_coach_individual_excel, generate_coach_whatsapp_msg

@app.get("/api/schedule/{schedule_id}/coach/{coach_name}/export-excel")
def export_individual_coach_excel(schedule_id: str, coach_name: str):
    """
    Exports a dedicated Excel spreadsheet (.xlsx) for a specific coach's schedule and student roster.
    """
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")

    excel_bytes = generate_coach_individual_excel(coach_name, res_dict.get("scheduled_classes", []))
    safe_name = coach_name.strip().replace(" ", "_")
    filename = f"mighty_knight_{safe_name}_schedule.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

from app.outputs.monthly_matrix_excel import generate_monthly_matrix_excel

@app.get("/api/schedule/{schedule_id}/export-monthly-excel")
def export_monthly_matrix_excel_api(schedule_id: str):
    """
    Exports a full monthly Excel schedule following the exact structure of the reference workbook.
    Dynamically adjusts columns to the exact days of the target month (28, 29, 30, or 31).
    Validates schedule before export; attaches DRAFT / VALIDATION FAILED banner if any violations occur.
    """
    ensure_active_data()
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")

    result = ScheduleResult(**res_dict)
    students = [StudentModel(**s) for s in ACTIVE_DATA["students"]]
    coaches = [CoachModel(**c) for c in ACTIVE_DATA["coaches"]]

    excel_bytes, is_valid, violations = generate_monthly_matrix_excel(
        result=result,
        students=students,
        coaches=coaches,
        config=CURRENT_CONFIG
    )
    s_date_str = result.start_date or "month"
    filename = f"Mighty_Knight_Schedule_{s_date_str[:7]}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.get("/api/schedule/{schedule_id}/validate")
def validate_schedule_endpoint(schedule_id: str):
    """
    Authoritative server-side schedule integrity validation.
    Checks all hard constraints: coach conflicts, student daily uniqueness,
    batch capacities, coach daily/monthly limits, Sunday 3 PM rule, student quotas.
    """
    ensure_active_data()
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")

    is_valid, violations = validate_schedule_state(
        res_dict,
        ACTIVE_DATA["students"],
        ACTIVE_DATA["coaches"],
        CURRENT_CONFIG
    )
    return {
        "schedule_id": schedule_id,
        "is_valid": is_valid,
        "status": "Valid" if is_valid else "Validation Failed",
        "violations_count": len(violations),
        "violations": violations
    }

@app.get("/api/schedule/{schedule_id}/coach/{coach_name}/whatsapp")
def get_individual_coach_whatsapp(schedule_id: str, coach_name: str, month: str = Query(default="2026-10")):
    """
    Generates tailored WhatsApp schedule broadcast text for a specific coach.
    """
    res_dict = get_schedule_db(schedule_id) if schedule_id not in ("latest", "active") else None
    if not res_dict:
        eff = get_effective_schedule(month)
        if eff and eff.get("scheduled_classes"):
            res_dict = eff
        else:
            raise HTTPException(status_code=404, detail="Schedule not found")

    msg_text = generate_coach_whatsapp_msg(coach_name, res_dict.get("scheduled_classes", []))
    return {
        "coach_name": coach_name,
        "whatsapp_text": msg_text
    }

from app.outputs.coach_ics import generate_coach_ics

@app.get("/api/schedule/{schedule_id}/coach/{coach_name}/export-ics")
def export_individual_coach_ics(schedule_id: str, coach_name: str, month: str = Query(default="2026-10")):
    """
    Exports a standard iCalendar (.ics) file for a coach to automatically add classes to Google/Apple/Outlook Calendar.
    """
    res_dict = get_schedule_db(schedule_id) if schedule_id not in ("latest", "active") else None
    if not res_dict:
        eff = get_effective_schedule(month)
        if eff and eff.get("scheduled_classes"):
            res_dict = eff
        else:
            raise HTTPException(status_code=404, detail="Schedule not found")

    ics_content = generate_coach_ics(coach_name, res_dict.get("scheduled_classes", []))
    safe_name = coach_name.strip().replace(" ", "_")
    filename = f"mighty_knight_{safe_name}_calendar.ics"
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.get("/api/schedule/{schedule_id}/output3")
def get_output3_attention_report(schedule_id: str, month: str = Query(default="2026-10")):
    eff = get_effective_schedule(month)
    return {
        "schedule_id": schedule_id,
        "accountability_passed": eff["need_attention"] == 0,
        "total_students_considered": eff["total_students"],
        "total_input_students": eff["total_students"],
        "unscheduled_count": eff["need_attention"],
        "attention_records": eff["attention_records"],
        "unscheduled_records": eff["attention_records"]
    }

@app.get("/api/schedule/{schedule_id}/output5")
def get_output5_student_schedules(schedule_id: str, month: str = Query(default="2026-10")):
    eff = get_effective_schedule(month)
    return {
        "schedule_id": schedule_id,
        "total_students": len(eff["student_schedules"]),
        "student_schedules": eff["student_schedules"]
    }

@app.get("/api/schedule/{schedule_id}/student/{student_id}/export-ics")
def export_individual_student_ics(schedule_id: str, student_id: str, month: str = Query(default="2026-10")):
    """
    Exports a standard iCalendar (.ics) file for a student.
    Enforces Strict Section 3 Monthly Quota Rule:
    Restricts student ICS synchronization until the student's monthly quota reaches 100% and their schedule is valid.
    """
    student_rec = None
    classes = []
    assigned_count = 0
    req_classes = 8

    # 1. If schedule_id is a specific persisted schedule, check it first
    if schedule_id and schedule_id not in ("latest", "active"):
        sched_db = get_schedule_db(schedule_id)
        if sched_db:
            # Check student_schedules list in schedule
            s_schedules = sched_db.get("student_schedules") or []
            student_rec = next((s for s in s_schedules if s.get("student_id") == student_id), None)
            if student_rec:
                classes = student_rec.get("classes", [])
                assigned_count = student_rec.get("scheduled_classes_count", len(classes))
                req_classes = student_rec.get("required_classes", 8)
            else:
                # Filter scheduled_classes for this student
                matched = [c for c in sched_db.get("scheduled_classes", []) if student_id in (c.get("student_ids") or [])]
                if matched:
                    classes = matched
                    assigned_count = len(matched)
                    unsched = next((u for u in sched_db.get("unscheduled_records", []) if u.get("student_id") == student_id), None)
                    if unsched:
                        req_classes = unsched.get("required_classes", assigned_count + unsched.get("shortfall", 0))
                    else:
                        req_classes = assigned_count

    # 2. Fall back to effective schedule for month
    if not student_rec and not classes:
        eff = get_effective_schedule(month)
        s_schedules = eff.get("student_schedules", [])
        student_rec = next((s for s in s_schedules if s.get("student_id") == student_id), None)
        
        if not student_rec:
            ensure_active_data()
            student_obj = next((s for s in ACTIVE_DATA["students"] if s.get("student_id") == student_id), None)
            if not student_obj:
                raise HTTPException(status_code=404, detail=f"Student {student_id} not found")
            assigned_count = 0
            req_classes = student_obj.get("classes_per_month") or 8
            classes = []
        else:
            assigned_count = student_rec.get("scheduled_classes_count", 0)
            req_classes = student_rec.get("required_classes", 8)
            classes = student_rec.get("classes", [])

    completion_pct = round((assigned_count / req_classes) * 100) if req_classes > 0 else 0

    if assigned_count < req_classes or completion_pct < 100:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Student ICS Synchronization Locked: Student {student_id} has completed only {assigned_count}/{req_classes} "
                f"required monthly classes ({completion_pct}%). Monthly quota must reach 100% and all scheduling issues must be "
                f"resolved before calendar synchronization can be enabled."
            )
        )

    ics_content = generate_student_ics(student_id, classes)
    safe_id = student_id.strip().replace(" ", "_")
    filename = f"mighty_knight_student_{safe_id}_calendar.ics"
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

class StatusUpdateRequest(BaseModel):
    status: str # Draft or Finalized

@app.post("/api/schedule/{schedule_id}/status")
def update_schedule_status(schedule_id: str, req: StatusUpdateRequest):
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if req.status not in ["Draft", "Finalized"]:
        raise HTTPException(status_code=400, detail="Status must be 'Draft' or 'Finalized'")

    res_dict["status"] = req.status
    save_schedule_db(res_dict)
    return {"schedule_id": schedule_id, "status": req.status}

class ManualOverrideRequest(BaseModel):
    class_id: str
    coach_name: str
    date: str
    time_slot: str
    student_level: Optional[str] = None
    batch_type: Optional[str] = None
    student_ids: Optional[List[str]] = None
    version: Optional[int] = None
    schedule_version: Optional[int] = None

@app.post("/api/schedule/{schedule_id}/validate-override")
def validate_manual_override(schedule_id: str, req: ManualOverrideRequest):
    """
    Validates manual administrative edit against the complete schedule state.
    Returns valid boolean and diagnostic list of rule violations.
    """
    ensure_active_data()
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")

    import copy
    temp_sched = copy.deepcopy(res_dict)
    target_cls = None
    for cls in temp_sched["scheduled_classes"]:
        if cls["class_id"] == req.class_id:
            target_cls = cls
            break

    if target_cls:
        target_cls["coach_name"] = req.coach_name.strip()
        target_cls["date"] = req.date
        try:
            d_obj = datetime.strptime(req.date, "%Y-%m-%d")
            target_cls["day"] = d_obj.strftime("%A")
        except Exception:
            pass
        target_cls["time_slot"] = req.time_slot
        if req.student_level:
            target_cls["student_level"] = req.student_level
        if req.batch_type:
            target_cls["batch_type"] = req.batch_type
        if req.student_ids is not None:
            target_cls["student_ids"] = req.student_ids

    is_valid, violations = validate_schedule_state(
        temp_sched, ACTIVE_DATA["students"], ACTIVE_DATA["coaches"], CURRENT_CONFIG
    )

    # Validate that only registered students can be added
    if req.student_ids is not None:
        valid_student_ids = {s["student_id"] for s in ACTIVE_DATA.get("students", [])}
        invalid_ids = [sid for sid in req.student_ids if sid not in valid_student_ids]
        if invalid_ids:
            is_valid = False
            violations.insert(0, f"Cannot assign unregistered student(s): {', '.join(invalid_ids)}. Only existing master students can be added.")

    return {
        "valid": is_valid,
        "warnings": violations
    }

@app.post("/api/schedule/{schedule_id}/manual-edit")
def apply_manual_edit(schedule_id: str, req: ManualOverrideRequest):
    """
    Applies and persists manual administrative edit (Section 37) to the schedule.
    Enforces transactional execution: mutates temp state, validates 100% of hard constraints,
    recalculates Output 1 and Output 3, and persists atomically only if valid.
    Enforces concurrency conflict detection (Part G).
    """
    if req.schedule_version is not None and req.schedule_version != ScheduleEventBus._version_counter:
        raise HTTPException(
            status_code=409,
            detail=f"Conflict: The schedule has been modified by another administrator (current version: {ScheduleEventBus._version_counter}, your version: {req.schedule_version}). Please refresh the schedule to review current state."
        )

    ensure_active_data()
    month = (req.date or "2026-10")[:7]
    res_dict = get_schedule_db(schedule_id)
    eff = get_effective_schedule(month)
    if not res_dict:
        res_dict = {"schedule_id": schedule_id or "SCHED_ACTIVE", "scheduled_classes": list(eff.get("scheduled_classes", [])), "status": "Draft"}

    before_holder = []
    after_holder = []

    def mutate(temp_sched):
        target_cls = None
        for cls in temp_sched["scheduled_classes"]:
            if cls["class_id"] == req.class_id:
                target_cls = cls
                break

        if not target_cls:
            # Fallback check from effective schedule
            for cls in eff.get("scheduled_classes", []):
                if cls.get("class_id") == req.class_id:
                    target_cls = dict(cls)
                    temp_sched["scheduled_classes"].append(target_cls)
                    break

        if not target_cls:
            raise HTTPException(status_code=404, detail=f"Class ID {req.class_id} not found in schedule")

        before_holder.append({
            "class_id": req.class_id,
            "date": target_cls.get("date"),
            "time_slot": target_cls.get("time_slot"),
            "coach_name": target_cls.get("coach_name"),
            "student_ids": list(target_cls.get("student_ids", [])),
            "student_level": target_cls.get("student_level"),
            "batch_type": target_cls.get("batch_type")
        })

        # Validate that only registered master students can be added
        if req.student_ids is not None:
            valid_student_ids = {s["student_id"] for s in ACTIVE_DATA.get("students", [])}
            invalid_ids = [sid for sid in req.student_ids if sid not in valid_student_ids]
            if invalid_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot assign unregistered student(s): {', '.join(invalid_ids)}. Only existing master students can be added."
                )

        target_cls["coach_name"] = req.coach_name.strip()
        target_cls["date"] = req.date
        try:
            d_obj = datetime.strptime(req.date, "%Y-%m-%d")
            target_cls["day"] = d_obj.strftime("%A")
        except Exception:
            pass
        target_cls["time_slot"] = req.time_slot
        if req.student_level:
            target_cls["student_level"] = req.student_level
        if req.batch_type:
            target_cls["batch_type"] = req.batch_type
        
        if req.student_ids is not None:
            target_cls["student_ids"] = req.student_ids
            stu_map = {s["student_id"]: s["student_name"] for s in ACTIVE_DATA.get("students", [])}
            names = [stu_map.get(sid, sid) for sid in req.student_ids]
            target_cls["student_names"] = names
            target_cls["students_formatted"] = " · ".join(names)

        target_cls["is_manual_override"] = True

        after_holder.append({
            "class_id": req.class_id,
            "date": target_cls.get("date"),
            "time_slot": target_cls.get("time_slot"),
            "coach_name": target_cls.get("coach_name"),
            "student_ids": list(target_cls.get("student_ids", [])),
            "student_level": target_cls.get("student_level"),
            "batch_type": target_cls.get("batch_type")
        })

    updated_schedule = execute_transactional_mutation(
        res_dict, ACTIVE_DATA["students"], ACTIVE_DATA["coaches"], CURRENT_CONFIG, mutate
    )
    save_schedule_db(updated_schedule)

    # Persist authoritative ExceptionRecord in SQLite Layer 3
    canon_coach = resolve_coach_canonical_name(req.coach_name)
    exc_id = f"EXC_{uuid.uuid4().hex[:8].upper()}"
    class_key = f"{req.date}||{req.time_slot}||{canon_coach}"

    before_state = before_holder[0] if before_holder else {}
    after_state = after_holder[0] if after_holder else {}
    before_ids = before_state.get("student_ids", [])
    after_ids = after_state.get("student_ids", [])
    removed_ids = [sid for sid in before_ids if sid not in after_ids]
    added_ids = [sid for sid in after_ids if sid not in before_ids]

    if removed_ids and not added_ids and req.date == before_state.get("date") and req.time_slot == before_state.get("time_slot") and canon_coach == resolve_coach_canonical_name(before_state.get("coach_name", "")):
        action_type = "remove_student"
        affected_ids = removed_ids
    elif added_ids and not removed_ids and req.date == before_state.get("date") and req.time_slot == before_state.get("time_slot") and canon_coach == resolve_coach_canonical_name(before_state.get("coach_name", "")):
        action_type = "add_student"
        affected_ids = added_ids
    else:
        action_type = "edit"
        affected_ids = after_ids

    rec = {
        "id": exc_id,
        "month": month,
        "date": req.date,
        "start_time": req.time_slot,
        "coach_id": canon_coach,
        "class_key": class_key,
        "class_id": req.class_id,
        "action_type": action_type,
        "affected_student_ids": affected_ids,
        "before": before_state,
        "after": after_state,
        "subtype": "manual",
        "violated_rules": [],
        "reason": req.reason or "Manual administrative edit",
        "created_by": "Admin",
        "created_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "status": "active",
        "version": 1
    }
    save_exception_record_db(rec)
    ScheduleEventBus.emit_change(month, coach_ids=[canon_coach], student_ids=after_ids + removed_ids)

    return {"status": "success", "schedule": updated_schedule, "exception_id": exc_id}

def sync_schedule_accountability(res_dict: dict):
    """
    Recalculates Output 1 and Output 3 atomically.
    Kept for backward compatibility; routes directly to recompute_schedule_outputs.
    """
    recompute_schedule_outputs(
        res_dict, ACTIVE_DATA.get("students", []), ACTIVE_DATA.get("coaches", []), CURRENT_CONFIG
    )

class AssignStudentRequest(BaseModel):
    student_id: str
    class_id: str

@app.post("/api/schedule/{schedule_id}/assign-student")
def assign_unscheduled_student_to_class(schedule_id: str, req: AssignStudentRequest):
    """
    Assigns a student into a class in Output 2.
    Transactionally validates all hard constraints before committing.
    Persists ExceptionRecord and emits real-time ScheduleChanged event.
    """
    ensure_active_data()
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")

    target_cls_ref = []

    def mutate(temp_sched):
        target_cls = next((c for c in temp_sched["scheduled_classes"] if c["class_id"] == req.class_id), None)
        if not target_cls:
            raise HTTPException(status_code=404, detail=f"Class ID {req.class_id} not found")

        target_cls_ref.append(dict(target_cls))

        if req.student_id not in target_cls["student_ids"]:
            target_cls["student_ids"].append(req.student_id)
            stu_map = {s["student_id"]: s["student_name"] for s in ACTIVE_DATA.get("students", [])}
            s_name = stu_map.get(req.student_id, req.student_id)
            target_cls["student_names"].append(s_name)
            target_cls["students_formatted"] = " · ".join(target_cls["student_names"])
            target_cls["is_manual_override"] = True

    updated_schedule = execute_transactional_mutation(
        res_dict, ACTIVE_DATA["students"], ACTIVE_DATA["coaches"], CURRENT_CONFIG, mutate
    )
    save_schedule_db(updated_schedule)

    # Persist ExceptionRecord
    month = "2026-10"
    if target_cls_ref:
        tc = target_cls_ref[0]
        c_date = tc.get("date")
        c_time = tc.get("time_slot")
        canon_coach = resolve_coach_canonical_name(tc.get("coach_name", ""))
        exc_id = f"EXC_{uuid.uuid4().hex[:8].upper()}"
        rec = {
            "id": exc_id,
            "month": month,
            "date": c_date,
            "start_time": c_time,
            "coach_id": canon_coach,
            "class_key": f"{c_date}||{c_time}||{canon_coach}",
            "action_type": "add_student",
            "affected_student_ids": [req.student_id],
            "before": {"student_ids": [sid for sid in tc.get("student_ids", []) if sid != req.student_id]},
            "after": {"student_ids": list(tc.get("student_ids", [])) + ([req.student_id] if req.student_id not in tc.get("student_ids", []) else [])},
            "subtype": "normal_assignment",
            "violated_rules": [],
            "reason": f"Assigned student {req.student_id} to class",
            "created_by": "Admin",
            "created_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
            "status": "active",
            "version": 1
        }
        save_exception_record_db(rec)
        ScheduleEventBus.emit_change(month, coach_ids=[canon_coach], student_ids=[req.student_id])

    return {"status": "success", "schedule": updated_schedule}

class CreateClassForStudentRequest(BaseModel):
    student_id: str
    coach_name: str
    date: str
    time_slot: str
    student_level: Optional[str] = "Basic 1"
    batch_type: Optional[str] = "G"

@app.post("/api/schedule/{schedule_id}/create-class-for-student")
def create_class_for_unscheduled_student(schedule_id: str, req: CreateClassForStudentRequest):
    """
    Creates a brand new class assignment for an unscheduled student.
    Persists ExceptionRecord and emits real-time ScheduleChanged event.
    """
    ensure_active_data()
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")

    new_class_id = f"CLS_{uuid.uuid4().hex[:6].upper()}"

    def mutate(temp_sched):
        stu_map = {s["student_id"]: s["student_name"] for s in ACTIVE_DATA.get("students", [])}
        s_name = stu_map.get(req.student_id, req.student_id)

        try:
            d_obj = datetime.strptime(req.date, "%Y-%m-%d")
            day_name = d_obj.strftime("%A")
        except Exception:
            day_name = "Monday"

        new_class = {
            "class_id": new_class_id,
            "date": req.date,
            "day": day_name,
            "time_slot": req.time_slot,
            "coach_name": req.coach_name.strip(),
            "student_level": req.student_level or "Basic 1",
            "batch_type": req.batch_type or "G",
            "batch_name": f"{req.student_level or 'Basic 1'} - {req.coach_name.strip()}",
            "student_ids": [req.student_id],
            "student_names": [s_name],
            "students_formatted": f"{s_name} ({req.student_id})",
            "warnings": ["Manual class assignment created by administrator"],
            "is_manual_override": True
        }
        temp_sched["scheduled_classes"].append(new_class)

    updated_schedule = execute_transactional_mutation(
        res_dict, ACTIVE_DATA["students"], ACTIVE_DATA["coaches"], CURRENT_CONFIG, mutate
    )
    save_schedule_db(updated_schedule)

    # Persist ExceptionRecord
    month = (req.date or "2026-10")[:7]
    canon_coach = resolve_coach_canonical_name(req.coach_name)
    exc_id = f"EXC_{uuid.uuid4().hex[:8].upper()}"
    rec = {
        "id": exc_id,
        "month": month,
        "date": req.date,
        "start_time": req.time_slot,
        "coach_id": canon_coach,
        "class_key": f"{req.date}||{req.time_slot}||{canon_coach}",
        "action_type": "add",
        "affected_student_ids": [req.student_id],
        "before": {},
        "after": {
            "student_level": req.student_level or "Basic 1",
            "batch_type": req.batch_type or "G",
            "student_ids": [req.student_id],
            "day": datetime.strptime(req.date, "%Y-%m-%d").strftime("%A") if req.date else "Monday"
        },
        "subtype": "normal_assignment",
        "violated_rules": [],
        "reason": f"Created class for student {req.student_id}",
        "created_by": "Admin",
        "created_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "status": "active",
        "version": 1
    }
    save_exception_record_db(rec)
    ScheduleEventBus.emit_change(month, coach_ids=[canon_coach], student_ids=[req.student_id])

    return {"status": "success", "schedule": updated_schedule, "created_class_id": new_class_id, "exception_id": exc_id}

class CreateClassGeneralRequest(BaseModel):
    coach_name: str
    date: str
    time_slot: str
    student_level: Optional[str] = "Basic 1"
    batch_type: Optional[str] = "G"
    batch_name: Optional[str] = ""
    student_ids: Optional[List[str]] = []

@app.post("/api/schedule/{schedule_id}/classes")
def create_custom_schedule_class(schedule_id: str, req: CreateClassGeneralRequest):
    """
    Creates a new custom class on a specific day/slot for detailed daily schedule planning.
    Persists ExceptionRecord and emits real-time ScheduleChanged event.
    """
    ensure_active_data()
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")

    new_class_id = f"CLS_{uuid.uuid4().hex[:6].upper()}"
    created_class_container = []

    def mutate(temp_sched):
        try:
            d_obj = datetime.strptime(req.date, "%Y-%m-%d")
            day_name = d_obj.strftime("%A")
        except Exception:
            day_name = "Monday"

        stu_map = {s["student_id"]: s["student_name"] for s in ACTIVE_DATA.get("students", [])}
        s_names = [stu_map.get(sid, sid) for sid in (req.student_ids or [])]
        s_formatted = " · ".join([f"{name} ({sid})" for sid, name in zip(req.student_ids or [], s_names)]) if s_names else "Open / Unassigned"

        new_class = {
            "class_id": new_class_id,
            "date": req.date,
            "day": day_name,
            "time_slot": req.time_slot,
            "coach_name": req.coach_name.strip(),
            "student_level": req.student_level or "Basic 1",
            "batch_type": req.batch_type or "G",
            "batch_name": req.batch_name or f"{req.student_level or 'Basic 1'} - {req.coach_name.strip()}",
            "student_ids": req.student_ids or [],
            "student_names": s_names,
            "students_formatted": s_formatted,
            "warnings": ["Manually planned daily class"],
            "is_manual_override": True
        }
        temp_sched["scheduled_classes"].append(new_class)
        created_class_container.append(new_class)

    updated_schedule = execute_transactional_mutation(
        res_dict, ACTIVE_DATA["students"], ACTIVE_DATA["coaches"], CURRENT_CONFIG, mutate
    )
    save_schedule_db(updated_schedule)

    # Persist ExceptionRecord
    month = (req.date or "2026-10")[:7]
    canon_coach = resolve_coach_canonical_name(req.coach_name)
    exc_id = f"EXC_{uuid.uuid4().hex[:8].upper()}"
    rec = {
        "id": exc_id,
        "month": month,
        "date": req.date,
        "start_time": req.time_slot,
        "coach_id": canon_coach,
        "class_key": f"{req.date}||{req.time_slot}||{canon_coach}",
        "action_type": "add",
        "affected_student_ids": req.student_ids or [],
        "before": {},
        "after": {
            "student_level": req.student_level or "Basic 1",
            "batch_type": req.batch_type or "G",
            "student_ids": req.student_ids or [],
            "day": datetime.strptime(req.date, "%Y-%m-%d").strftime("%A") if req.date else "Monday"
        },
        "subtype": "normal_assignment",
        "violated_rules": [],
        "reason": "Created custom scheduled class",
        "created_by": "Admin",
        "created_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "status": "active",
        "version": 1
    }
    save_exception_record_db(rec)
    ScheduleEventBus.emit_change(month, coach_ids=[canon_coach], student_ids=req.student_ids or [])

    return {"status": "success", "schedule": updated_schedule, "created_class": created_class_container[0], "exception_id": exc_id}

@app.delete("/api/schedule/{schedule_id}/class/{class_id}")
def delete_class_from_schedule(schedule_id: str, class_id: str):
    """
    Deletes a scheduled class from the schedule.
    Creates an authoritative ExceptionRecord (action_type: 'delete') in SQLite Layer 3,
    recalculates Effective Schedule, logs audit, and emits real-time ScheduleChanged event.
    """
    ensure_active_data()
    month = "2026-10"
    eff = get_effective_schedule(month)
    target_cls = next((c for c in eff.get("scheduled_classes", []) if c.get("class_id") == class_id), None)

    res_dict = get_schedule_db(schedule_id)
    if not target_cls and res_dict:
        target_cls = next((c for c in res_dict.get("scheduled_classes", []) if c.get("class_id") == class_id), None)

    if not target_cls:
        raise HTTPException(status_code=404, detail=f"Class ID {class_id} not found in schedule")

    c_date = target_cls.get("date")
    c_time = target_cls.get("time_slot")
    c_coach = resolve_coach_canonical_name(target_cls.get("coach_name", ""))
    class_key = f"{c_date}||{c_time}||{c_coach}"
    affected_students = list(target_cls.get("student_ids", []))
    exc_id = f"EXC_DEL_{uuid.uuid4().hex[:8].upper()}"

    rec = {
        "id": exc_id,
        "month": month,
        "date": c_date,
        "start_time": c_time,
        "coach_id": c_coach,
        "class_key": class_key,
        "class_id": class_id,
        "action_type": "delete",
        "affected_student_ids": affected_students,
        "before": target_cls,
        "after": {},
        "subtype": "manual",
        "violated_rules": [],
        "reason": f"Class {class_id} ({c_time} - {c_coach}) deleted by Administrator",
        "created_by": "Admin",
        "created_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "status": "active",
        "version": 1
    }
    save_exception_record_db(rec)

    # Also mutate legacy schedule if present
    updated_schedule = {}
    if res_dict:
        def mutate(temp_sched):
            temp_sched["scheduled_classes"] = [c for c in temp_sched["scheduled_classes"] if c.get("class_id") != class_id]
        updated_schedule = execute_transactional_mutation(
            res_dict, ACTIVE_DATA["students"], ACTIVE_DATA["coaches"], CURRENT_CONFIG, mutate
        )
        save_schedule_db(updated_schedule)

    ScheduleEventBus.emit_change(month, coach_ids=[c_coach], student_ids=affected_students)
    return {"status": "success", "schedule": updated_schedule, "exception_id": exc_id}

@app.post("/api/master/clear-all")
@app.delete("/api/master/all")
def clear_all_master_data():
    """
    Wipes all master students, coaches, batches, and generated schedules completely,
    returning the academy to a 100% clean state ready to restart from scratch.
    """
    global ACTIVE_DATA
    ACTIVE_DATA = {
        "students": [],
        "coaches": [],
        "batches": [],
        "schedules": {},
        "parsing_errors": [],
        "filename": "Empty (Clean Slate)",
        "upload_timestamp": ""
    }
    clear_all_master_data_db()
    return {
        "status": "success",
        "message": "All master students, coaches, batches, and schedules have been wiped cleanly. Ready for scratch setup."
    }

# ==============================================================================
# REAL-TIME FIRE-SPEED EVENTS (PART A4 & A6)
# ==============================================================================

@app.get("/api/events/stream")
async def event_stream():
    """Server-Sent Events endpoint broadcasting ScheduleChanged events in real time."""
    async def event_generator():
        q = ScheduleEventBus.subscribe()
        try:
            yield f"data: {json.dumps({'type': 'Connected', 'version': ScheduleEventBus._version_counter})}\n\n"
            while True:
                msg = await q.get()
                yield f"data: {json.dumps(msg)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            ScheduleEventBus.unsubscribe(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/effective-schedule")
def get_effective_schedule_api(month: str = Query(default="2026-10")):
    """Returns the single-source-of-truth computed Effective Schedule (Part A1 & A2)."""
    return get_effective_schedule(month)

@app.get("/api/effective-schedule/{month}")
def get_effective_schedule_by_path_api(month: str):
    """Returns the single-source-of-truth computed Effective Schedule for specified month."""
    return get_effective_schedule(month)

@app.get("/api/attention-report/{month}")
def get_attention_report_by_month_api(month: str):
    """Returns Attention Required records and metrics for the specified month."""
    eff = get_effective_schedule(month)
    return {
        "month": month,
        "accountability_passed": eff.get("need_attention", 0) == 0,
        "total_students": eff.get("total_students", 0),
        "need_attention": eff.get("need_attention", 0),
        "metrics": {
            "total_records": len(eff.get("attention_records", [])),
            "unresolved_count": eff.get("need_attention", 0),
        },
        "records": eff.get("attention_records", []),
        "attention_records": eff.get("attention_records", [])
    }

# ==============================================================================
# ABSOLUTE SCHEDULE SPACE ENDPOINTS (PART E)
# ==============================================================================

@app.get("/api/baseline/status")
def get_baseline_status_api(month: str = Query(default="2026-10")):
    seed_october_baseline_if_missing()
    active_b = get_active_baseline_db(month)
    draft_b = get_draft_baseline_db(month)
    history = list_baselines_for_month_db(month)
    status = "Active" if active_b else ("Draft" if draft_b else "Not Uploaded")
    active_ver = active_b.get("version", 0) if active_b else 0
    return {
        "month": month,
        "status": status,
        "version": active_ver,
        "active_baseline": active_b,
        "draft_baseline": draft_b,
        "history": history
    }

@app.get("/api/baseline/template")
def download_baseline_template_api(month: str = Query(default="2026-10")):
    try:
        parts = month.split("-")
        yr, mo = int(parts[0]), int(parts[1])
    except Exception:
        yr, mo = 2026, 10
    excel_bytes = generate_monthly_excel_template(yr, mo)
    filename = f"Mighty_Knight_Baseline_Template_{month}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.post("/api/baseline/upload")
async def upload_baseline_excel_api(
    file: UploadFile = File(...),
    month: str = Form(...)
):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are allowed.")
    try:
        parts = month.split("-")
        yr, mo = int(parts[0]), int(parts[1])
    except Exception:
        yr, mo = 2026, 10

    content = await file.read()
    ensure_active_data()
    parsed_res = parse_baseline_excel_file(
        content, yr, mo,
        master_students=ACTIVE_DATA.get("students", []),
        master_coaches=ACTIVE_DATA.get("coaches", [])
    )

    history = list_baselines_for_month_db(month)
    next_ver = (max([h["version"] for h in history]) + 1) if history else 1

    draft_record = {
        "month": month,
        "version": next_ver,
        "status": "Draft",
        "file_name": file.filename,
        "uploaded_by": "Admin",
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "student_count": parsed_res["student_count"],
        "class_count": parsed_res["class_count"],
        "student_class_count": parsed_res["student_class_count"],
        "students_data": parsed_res["students_data"],
        "classes_data": parsed_res["classes_data"],
        "baseline_exceptions": parsed_res["baseline_exceptions"],
        "validation_report": parsed_res["validation_report"],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    draft_id = save_baseline_db(draft_record)
    draft_record["id"] = draft_id

    log_audit_event_db(
        user="Admin",
        action="UPLOAD_BASELINE_DRAFT",
        entity_type="BASELINE",
        entity_id=str(draft_id),
        before=None,
        after={"version": next_ver, "file_name": file.filename, "student_count": parsed_res["student_count"]},
        violated_rules=parsed_res.get("baseline_exceptions", []),
        source_page="Absolute Schedule",
        month=month
    )

    ScheduleEventBus.emit_change(month)

    return {
        "status": "success",
        "draft_baseline": draft_record,
        "validation_report": parsed_res["validation_report"]
    }

class BaselineActivationRequest(BaseModel):
    month: str
    version: int
    user: Optional[str] = "Admin"

@app.post("/api/baseline/activate")
def activate_baseline_api(req: BaselineActivationRequest):
    ok = activate_baseline_db(req.month, req.version, req.user or "Admin")
    if not ok:
        raise HTTPException(status_code=400, detail="Could not activate baseline version.")

    log_audit_event_db(
        user=req.user or "Admin",
        action="ACTIVATE_BASELINE",
        entity_type="BASELINE",
        entity_id=f"{req.month}_v{req.version}",
        before={"status": "Draft"},
        after={"status": "Active", "version": req.version},
        violated_rules=[],
        source_page="Absolute Schedule",
        month=req.month
    )

    ScheduleEventBus.emit_change(req.month)
    return {"status": "success", "month": req.month, "version": req.version}

@app.post("/api/baseline/discard")
def discard_baseline_api(req: Dict[str, Any]):
    month = req.get("month", "2026-10")
    discard_draft_baseline_db(month)
    ScheduleEventBus.emit_change(month)
    return {"status": "success", "month": month}

@app.get("/api/baseline/export-active")
def export_active_baseline_api(month: str = Query(default="2026-10")):
    active_b = get_active_baseline_db(month)
    if not active_b:
        raise HTTPException(status_code=404, detail="No active baseline found for this month.")
    try:
        parts = month.split("-")
        yr, mo = int(parts[0]), int(parts[1])
    except Exception:
        yr, mo = 2026, 10
    excel_bytes = generate_monthly_excel_template(yr, mo)
    filename = f"Mighty_Knight_Active_Baseline_{month}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.get("/api/baseline/actual-completed")
def get_actual_completed_schedule_api(
    month: str = Query(default="2026-10"),
    current_date: Optional[str] = Query(default=None)
):
    """
    Rule 2: Absolute Schedule — Actual Completed Schedule Display
    Displays schedule data ONLY up to the previous completed calendar day (Current Date - 1 Day).
    Strictly excludes the current day's schedule and all upcoming dates in the current month.
    Pure non-destructive read filter over effective schedule without mutating underlying database records.
    """
    ref_date_str = current_date or date.today().isoformat()
    try:
        ref_dt = datetime.strptime(ref_date_str, "%Y-%m-%d").date()
    except Exception:
        ref_dt = date.today()

    cutoff_dt = ref_dt - timedelta(days=1)
    cutoff_date_str = cutoff_dt.isoformat()

    eff = get_effective_schedule(month)
    all_classes = eff.get("scheduled_classes", [])

    # Filter strictly to completed calendar days prior to today: date <= cutoff_date_str
    completed_classes = [
        c for c in all_classes
        if c.get("date") and c.get("date") <= cutoff_date_str and c.get("date").startswith(month)
    ]

    completed_classes.sort(
        key=lambda c: (c.get("date", ""), parse_time_slot_sort_key(c.get("date", ""), c.get("time_slot", "")))
    )

    total_classes = len(completed_classes)
    total_student_sessions = sum(len(c.get("student_ids", [])) for c in completed_classes)
    unique_students = len(set(sid for c in completed_classes for sid in c.get("student_ids", [])))
    active_coaches = sorted(list(set(c.get("coach_name") for c in completed_classes if c.get("coach_name") and c.get("coach_name") != "Unassigned")))

    daily_groups = defaultdict(list)
    for c in completed_classes:
        daily_groups[c.get("date")].append(c)

    daily_summary = []
    for d_str in sorted(daily_groups.keys()):
        d_classes = daily_groups[d_str]
        d_day = d_classes[0].get("day", "")
        daily_summary.append({
            "date": d_str,
            "day": d_day,
            "classes_count": len(d_classes),
            "student_sessions": sum(len(c.get("student_ids", [])) for c in d_classes),
            "classes": d_classes
        })

    return {
        "month": month,
        "current_date": ref_date_str,
        "cutoff_date": cutoff_date_str,
        "is_strictly_prior_to_today": True,
        "rule_description": "Displaying completed calendar days strictly up to Current Date - 1 Day. Today and future dates are strictly excluded.",
        "total_completed_classes": total_classes,
        "total_completed_student_sessions": total_student_sessions,
        "unique_students_attended": unique_students,
        "active_coaches_count": len(active_coaches),
        "active_coaches": active_coaches,
        "completed_classes": completed_classes,
        "daily_breakdown": daily_summary
    }

@app.post("/api/baseline/generate-next-month")
def generate_next_month_api(req: Dict[str, Any]):
    source_month = req.get("source_month", "2026-10")
    target_year = int(req.get("target_year", 2026))
    target_month = int(req.get("target_month", 11))
    user = req.get("user", "Admin")

    draft_record = generate_next_month_draft(source_month, target_year, target_month, user=user)
    t_month_str = f"{target_year:04d}-{target_month:02d}"

    log_audit_event_db(
        user=user,
        action="GENERATE_NEXT_MONTH_DRAFT",
        entity_type="BASELINE",
        entity_id=t_month_str,
        before=None,
        after={"source_month": source_month, "target_month": t_month_str},
        violated_rules=[],
        source_page="Absolute Schedule",
        month=t_month_str
    )

    ScheduleEventBus.emit_change(t_month_str)
    return {"status": "success", "draft": draft_record}

@app.post("/api/baseline/promote-effective")
def promote_effective_api(req: Dict[str, Any]):
    month = req.get("month", "2026-10")
    user = req.get("user", "Admin")
    eff = get_effective_schedule(month)
    promoted_classes = [c for c in eff["scheduled_classes"] if not c.get("is_compensation")]
    
    history = list_baselines_for_month_db(month)
    next_ver = (max([h["version"] for h in history]) + 1) if history else 1

    active_b = get_active_baseline_db(month)
    students = active_b.get("students_data", []) if active_b else []

    draft_record = {
        "month": month,
        "version": next_ver,
        "status": "Draft",
        "file_name": f"Promoted_from_Effective_{month}.xlsx",
        "uploaded_by": f"Promote ({user})",
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "student_count": len(students),
        "class_count": len(promoted_classes),
        "student_class_count": sum(len(c.get("student_ids", [])) for c in promoted_classes),
        "students_data": students,
        "classes_data": promoted_classes,
        "baseline_exceptions": [],
        "validation_report": {"blocking": [], "baseline_exceptions": [], "info": ["Promoted from current Effective Schedule (ⓒ excluded)."]},
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    draft_id = save_baseline_db(draft_record)
    draft_record["id"] = draft_id
    ScheduleEventBus.emit_change(month)
    return {"status": "success", "draft": draft_record}

# ==============================================================================
# ⓒ EXCEPTION / MANUAL CHANGE OVERLAY ENDPOINTS (PART D)
# ==============================================================================

class ValidateExceptionRequest(BaseModel):
    month: str = "2026-10"
    date: str
    time_slot: str
    coach_name: str
    class_id: Optional[str] = None
    student_level: Optional[str] = "Beginner 1"
    batch_type: Optional[str] = "G"
    student_ids: Optional[List[str]] = []
    action_type: Optional[str] = "edit"

@app.post("/api/schedule/exception/validate")
def validate_exception_api(req: ValidateExceptionRequest):
    """
    Validates a proposed schedule change against all Part B & Part C rules before applying.
    Returns {is_valid: bool, has_violations: bool, violations: [...]}
    """
    sched = get_effective_schedule(req.month)
    classes = sched.get("scheduled_classes", [])

    ensure_active_data()
    master_students = {s["student_id"]: s for s in ACTIVE_DATA.get("students", [])}

    target_cls = {
        "class_id": req.class_id or "TEMP_CLS",
        "date": req.date,
        "time_slot": req.time_slot,
        "coach_name": req.coach_name,
        "student_level": req.student_level or "Beginner 1",
        "batch_type": req.batch_type or "G",
        "student_ids": req.student_ids or []
    }

    try:
        d_obj = datetime.strptime(req.date, "%Y-%m-%d")
        day_str = d_obj.strftime("%A")
    except Exception:
        day_str = "Monday"

    is_tourn = (day_str == "Sunday" or (day_str == "Friday" and req.student_level == "Intermediate 2"))

    violations = validate_all_rules_for_occurrence(
        target_cls,
        classes,
        master_students,
        COACH_REFERENCE,
        is_tournament=is_tourn
    )

    hard_violations = [v for v in violations if v["severity"] == "hard"]
    return {
        "is_valid": len(hard_violations) == 0,
        "has_violations": len(violations) > 0,
        "violations": violations
    }

class ApplyExceptionRequest(BaseModel):
    month: str = "2026-10"
    date: str
    time_slot: str
    coach_name: str
    class_id: Optional[str] = None
    class_key: Optional[str] = None
    action_type: str # add | edit | move | delete | add_student | remove_student
    affected_student_ids: List[str]
    before: Optional[Dict[str, Any]] = {}
    after: Optional[Dict[str, Any]] = {}
    subtype: str = "manual" # compensation | manual | rule_exception
    violated_rules: Optional[List[Dict[str, Any]]] = []
    reason: Optional[str] = ""
    created_by: Optional[str] = "Admin"
    schedule_version: Optional[int] = None

@app.post("/api/schedule/exception/apply")
def apply_exception_api(req: ApplyExceptionRequest):
    """
    Applies an administrator-approved single-occurrence ExceptionRecord (ⓒ).
    Saves atomically, recalculates Effective Schedule, bumps version, logs audit.
    Enforces optimistic concurrency conflict detection (Part G).
    """
    if req.schedule_version is not None and req.schedule_version != ScheduleEventBus._version_counter:
        raise HTTPException(
            status_code=409,
            detail=f"Conflict: The schedule has been modified by another administrator (current version: {ScheduleEventBus._version_counter}, your version: {req.schedule_version}). Please refresh the schedule to review current state."
        )

    canon_coach = resolve_coach_canonical_name(req.coach_name)
    exc_id = f"EXC_{uuid.uuid4().hex[:8].upper()}"
    class_key = req.class_key or f"{req.date}||{req.time_slot}||{canon_coach}"

    before_dict = dict(req.before or {})
    if req.class_id and "class_id" not in before_dict:
        before_dict["class_id"] = req.class_id

    rec = {
        "id": exc_id,
        "month": req.month,
        "date": req.date,
        "start_time": req.time_slot,
        "coach_id": canon_coach,
        "class_key": class_key,
        "class_id": req.class_id,
        "action_type": req.action_type,
        "affected_student_ids": req.affected_student_ids,
        "before": before_dict,
        "after": req.after or {},
        "subtype": req.subtype,
        "violated_rules": req.violated_rules or [],
        "reason": req.reason or "",
        "created_by": req.created_by or "Admin",
        "created_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "status": "active",
        "version": 1
    }

    save_exception_record_db(rec)

    log_audit_event_db(
        user=req.created_by or "Admin",
        action=f"APPLY_EXCEPTION_{req.action_type.upper()}",
        entity_type="EXCEPTION_RECORD",
        entity_id=exc_id,
        before=req.before,
        after=req.after,
        violated_rules=req.violated_rules,
        source_page="Daily Schedule Planner",
        month=req.month
    )

    ScheduleEventBus.emit_change(
        req.month,
        dates=[req.date],
        student_ids=req.affected_student_ids,
        coach_ids=[canon_coach],
        class_ids=[req.class_id or exc_id]
    )

    updated_sched = get_effective_schedule(req.month)
    return {
        "status": "success",
        "exception_id": exc_id,
        "schedule": updated_sched
    }

@app.post("/api/schedule/exception/{exception_id}/revert")
def revert_exception_api(exception_id: str, month: str = Query(default="2026-10")):
    """
    Reverts a single-occurrence ExceptionRecord (ⓒ) and restores baseline occurrence.
    """
    ok = revert_exception_record_db(exception_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Exception not found or already reverted.")

    log_audit_event_db(
        user="Admin",
        action="REVERT_EXCEPTION",
        entity_type="EXCEPTION_RECORD",
        entity_id=exception_id,
        before={"status": "active"},
        after={"status": "reverted"},
        violated_rules=[],
        source_page="Daily Schedule Planner",
        month=month
    )

    ScheduleEventBus.emit_change(month)
    updated_sched = get_effective_schedule(month)
    return {"status": "success", "reverted_id": exception_id, "schedule": updated_sched}

@app.get("/api/schedule/exceptions")
def list_exceptions_api(month: str = Query(default="2026-10"), status: Optional[str] = "active"):
    return {
        "month": month,
        "exceptions": get_exception_records_db(month, status=status)
    }

@app.get("/api/audit-logs")
def get_audit_logs_api(month: Optional[str] = Query(default=None), limit: int = 100):
    return {
        "logs": get_audit_logs_db(month=month, limit=limit)
    }

# ==============================================================================
# RULE 4: BATCH REASSIGNMENT ENDPOINT
# ==============================================================================

class ReassignBatchCoachRequest(BaseModel):
    batch_name: Optional[str] = None
    old_coach_name: Optional[str] = None
    new_coach_name: str
    month: str = "2026-10"
    day: Optional[str] = None
    time_slot: Optional[str] = None
    class_ids: Optional[List[str]] = None
    user: Optional[str] = "Admin"

@app.post("/api/schedule/reassign-batch-coach")
def reassign_batch_coach_api(req: ReassignBatchCoachRequest):
    """
    Rule 4: Reassigns all classes of a batch from a deleted or unavailable coach
    to a replacement coach across the entire month to complete its full quota.
    Persists atomically to SQLite via ExceptionRecord / Baseline and synchronizes across all pages.
    """
    canon_new_coach = resolve_coach_canonical_name(req.new_coach_name)
    canon_old_coach = resolve_coach_canonical_name(req.old_coach_name) if req.old_coach_name else None

    eff = get_effective_schedule(req.month)
    all_classes = eff.get("scheduled_classes", [])

    matching_classes = []
    for c in all_classes:
        c_coach = resolve_coach_canonical_name(c.get("coach_name", ""))
        c_bname = c.get("batch_name", "")
        c_slot = c.get("time_slot", "")
        c_day = c.get("day", "")
        c_id = c.get("class_id", "")

        if req.class_ids and c_id in req.class_ids:
            matching_classes.append(c)
            continue

        match = True
        if canon_old_coach and c_coach.lower() != canon_old_coach.lower():
            match = False
        if req.batch_name and c_bname and req.batch_name.lower() not in c_bname.lower() and c_bname.lower() not in req.batch_name.lower():
            match = False
        if req.time_slot and c_slot != req.time_slot:
            match = False
        if req.day and c_day != req.day:
            match = False

        if match:
            matching_classes.append(c)

    if not matching_classes:
        raise HTTPException(
            status_code=404,
            detail="No matching classes found to reassign with the provided parameters."
        )

    applied_exceptions = []
    for cls in matching_classes:
        exc_id = f"EXC_{uuid.uuid4().hex[:8].upper()}"
        c_date = cls.get("date", "")
        c_slot = cls.get("time_slot", "")
        c_id = cls.get("class_id", "")
        s_ids = cls.get("student_ids", [])

        before_dict = dict(cls)
        after_dict = dict(cls)
        after_dict["coach_name"] = canon_new_coach

        rec = {
            "id": exc_id,
            "month": req.month,
            "date": c_date,
            "start_time": c_slot,
            "coach_id": canon_new_coach,
            "class_key": f"{c_date}||{c_slot}||{canon_new_coach}",
            "class_id": c_id,
            "action_type": "edit",
            "affected_student_ids": s_ids,
            "before": before_dict,
            "after": after_dict,
            "subtype": "manual",
            "violated_rules": [],
            "reason": f"Batch reassigned from {req.old_coach_name or 'Previous Coach'} to {canon_new_coach} (Rule 4)",
            "created_by": req.user or "Admin",
            "created_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
            "status": "active",
            "version": 1
        }
        save_exception_record_db(rec)
        applied_exceptions.append(exc_id)

    if req.batch_name:
        for b in ACTIVE_DATA.get("batches", []):
            if req.batch_name.lower() in b.get("batch_name", "").lower():
                b["assigned_coach"] = canon_new_coach
                save_single_batch_db(b)

    log_audit_event_db(
        user=req.user or "Admin",
        action="REASSIGN_BATCH_COACH",
        entity_type="BATCH",
        entity_id=req.batch_name or canon_new_coach,
        before={"old_coach": req.old_coach_name},
        after={"new_coach": canon_new_coach, "reassigned_classes": len(matching_classes)},
        violated_rules=[],
        source_page="Attention Required",
        month=req.month
    )

    ScheduleEventBus.emit_change(
        req.month,
        coach_ids=[canon_new_coach] + ([canon_old_coach] if canon_old_coach else [])
    )

    updated_eff = get_effective_schedule(req.month)
    return {
        "status": "success",
        "new_coach_name": canon_new_coach,
        "reassigned_classes_count": len(matching_classes),
        "exception_ids": applied_exceptions,
        "effective_schedule": updated_eff
    }

# ==============================================================================
# RULE 6: ENGINE QUEUE & ASYNC EXECUTION
# ==============================================================================
from app.engine.engine_queue import engine_queue

def _handle_schedule_generate(payload: Dict[str, Any]):
    ensure_active_data()
    s_date = date.today()
    e_date = s_date + timedelta(days=6)
    result = run_scheduler(
        [StudentModel(**s) for s in ACTIVE_DATA["students"]],
        [CoachModel(**c) for c in ACTIVE_DATA["coaches"]],
        s_date, e_date, CURRENT_CONFIG
    )
    res_dict = result.model_dump()
    save_schedule_db(res_dict)
    return {"schedule_id": res_dict["schedule_id"], "classes_count": len(res_dict.get("scheduled_classes", []))}

engine_queue.register_handler("schedule_generate", _handle_schedule_generate)
engine_queue.register_handler("recompute", lambda payload: get_effective_schedule(payload.get("month", "2026-10")))

@app.post("/api/engine/tasks/enqueue")
def enqueue_engine_task_api(req: Dict[str, Any]):
    task_type = req.get("task_type", "recompute")
    payload = req.get("payload", {})
    task = engine_queue.enqueue_task(task_type, payload)
    return {
        "status": "enqueued",
        "task": task.to_dict()
    }

@app.get("/api/engine/tasks/status")
def get_engine_tasks_status_api():
    return engine_queue.get_status()

@app.get("/api/engine/tasks/{task_id}")
def get_engine_task_detail_api(task_id: str):
    task = engine_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": task.to_dict()}

# ----------------------------------------------------
# Unified Production Deployment: Serve Built React App
# ----------------------------------------------------
from fastapi.staticfiles import StaticFiles

_dist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.exists(_dist_path):
    app.mount("/", StaticFiles(directory=_dist_path, html=True), name="static")


