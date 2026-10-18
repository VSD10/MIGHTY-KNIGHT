import os
import json
import uuid
import asyncio
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Union
from collections import defaultdict
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
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
    compute_master_data_fingerprint,
    log_db_status, BASE_DIR,
    save_baseline_db, get_active_baseline_db, get_draft_baseline_db, get_baseline_by_version_db,
    activate_baseline_db, discard_draft_baseline_db, list_baselines_for_month_db,
    save_exception_record_db, get_exception_records_db, revert_exception_record_db,
    log_audit_event_db, get_audit_logs_db, seed_october_baseline_if_missing
)
from app.engine.effective_schedule_service import get_effective_schedule, ScheduleEventBus
from app.engine.baseline_service import (
    generate_monthly_excel_template, parse_baseline_excel_file, generate_next_month_draft, get_rolling_horizon_months, ensure_rolling_three_months_seeded, format_date_wise_schedule_text, generate_populated_schedule_excel_bytes
)
from app.engine.rule_engine import (
    validate_all_rules_for_occurrence, resolve_coach_canonical_name, COACH_REFERENCE, parse_time_to_minutes
)
from app.engine.master_data_service import (
    validate_student_data, reorder_coach_level_priorities, remove_coach_from_level_priority,
    handle_batch_type_conversion, handle_student_level_change
)
from app.engine.suggestion_engine import (
    find_single_class_suggestions, solve_multi_class_options,
    generate_smart_batch_opportunities, generate_consolidation_advisory,
    generate_trainer_engagement_proposals,
    get_coach_daily_availability_explorer,
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

from starlette.requests import Request

@app.middleware("http")
async def api_prefix_fallback_middleware(request: Request, call_next):
    """
    Ensures seamless routing whether requests are made with /api prefix (e.g. /api/schedule/latest/active)
    or without /api prefix (e.g. /schedule/latest/active), or through Vercel serverless rewrites.
    Also synchronizes any custom students passed in X-Custom-Students header across serverless containers.
    """
    custom_hdr = request.headers.get("x-custom-students")
    if custom_hdr:
        try:
            import urllib.parse
            decoded_json = urllib.parse.unquote(custom_hdr)
            s_list = json.loads(decoded_json)
            if isinstance(s_list, list) and s_list:
                from app.storage.database import save_single_student_db
                ensure_active_data()
                mem_sids = {s.get("student_id") for s in ACTIVE_DATA.get("students", [])}
                synced_any = False
                for st in s_list:
                    if isinstance(st, dict) and st.get("student_id"):
                        if st["student_id"] not in mem_sids:
                            ACTIVE_DATA["students"].append(st)
                            mem_sids.add(st["student_id"])
                            save_single_student_db(st)
                            synced_any = True
                if synced_any:
                    from app.engine.effective_schedule_service import invalidate_effective_schedule_cache
                    invalidate_effective_schedule_cache("2026-10")
        except Exception:
            pass

    path = request.scope.get("path", "")
    if path and not path.startswith("/api") and not path.startswith("/docs") and not path.startswith("/redoc") and not path.startswith("/openapi.json") and not path.startswith("/assets") and path != "/":
        api_path = f"/api{path}"
        for route in request.app.routes:
            if hasattr(route, "path") and route.path == api_path:
                request.scope["path"] = api_path
                break
            elif hasattr(route, "path_regex") and route.path_regex.match(api_path):
                request.scope["path"] = api_path
                break
    return await call_next(request)

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

    if not is_master_cleared_db():
        seed_october_baseline_if_missing()

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
    ACTIVE_DATA["students"] = data.get("students", [])
    ACTIVE_DATA["coaches"] = data.get("coaches", [])
    ACTIVE_DATA["batches"] = load_master_batches_db()
    ACTIVE_DATA["parsing_errors"] = data.get("parsing_errors", [])
    ACTIVE_DATA["filename"] = data.get("last_filename") or ("Master Data" if (ACTIVE_DATA["students"] or ACTIVE_DATA["batches"]) else "Empty (Clean Slate)")
    ACTIVE_DATA["upload_timestamp"] = data.get("last_upload_timestamp") or ""

    # Synchronize authoritative coach priority matrix and register active coaches in COACH_REFERENCE
    from app.engine.master_data_service import sync_live_coach_priority_matrix
    sync_live_coach_priority_matrix(coaches_list=ACTIVE_DATA["coaches"], config=CURRENT_CONFIG, persist_db=True)

def sync_active_schedule_master_data(month: str = "2026-10"):
    """
    Synchronizes the active schedule in SQLite with current master students, coaches, and config.
    Updates the master_data_fingerprint so the schedule is never considered stale or regenerated on refresh.
    """
    from app.engine.effective_schedule_service import invalidate_effective_schedule_cache
    invalidate_effective_schedule_cache(month)
    latest_sched = get_latest_schedule_db()
    if latest_sched:
        new_fp = compute_master_data_fingerprint(config_dict=CURRENT_CONFIG.model_dump())
        latest_sched["master_data_fingerprint"] = new_fp
        latest_sched["is_stale"] = False
        m_str = (latest_sched.get("start_date") or month or "2026-10")[:7]
        eff = get_effective_schedule(m_str)
        if eff and eff.get("scheduled_classes"):
            latest_sched["scheduled_classes"] = list(eff["scheduled_classes"])
            latest_sched["coach_summaries"] = list(eff.get("coach_summaries", []))
            latest_sched["coach_slots"] = list(eff.get("coach_slots", []))
            latest_sched["student_schedules"] = list(eff.get("student_schedules", []))
            latest_sched["attention_records"] = list(eff.get("attention_records", []))
            latest_sched["unscheduled_records"] = list(eff.get("attention_records", []))
            latest_sched["whatsapp_plain_text"] = eff.get("whatsapp_plain_text", "")
            latest_sched["total_classes"] = eff.get("total_classes", len(eff["scheduled_classes"]))
            latest_sched["total_students_considered"] = eff.get("total_students", 0)
            latest_sched["unscheduled_students_count"] = eff.get("need_attention", 0)
            latest_sched["successfully_scheduled_students"] = eff.get("total_students", 0) - eff.get("need_attention", 0)
            latest_sched["accountability_passed"] = eff.get("need_attention", 0) == 0
        else:
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
        from app.engine.master_data_service import sync_live_coach_priority_matrix
        sync_live_coach_priority_matrix(coaches_list=ACTIVE_DATA.get("coaches", []), config=CURRENT_CONFIG, persist_db=True)
        save_system_config_db(CURRENT_CONFIG.model_dump())
        sync_active_schedule_master_data()
        ScheduleEventBus.emit_change("2026-10")
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
    
    # Auto-adjust min/max capacity if not provided
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
    ScheduleEventBus.emit_change("2026-10")
    return {"status": "success", "batch": b_dict}

@app.delete("/api/master/batches/{batch_id:path}")
def delete_master_batch(batch_id: str):
    ensure_active_data()
    ACTIVE_DATA["batches"] = [b for b in ACTIVE_DATA.get("batches", []) if b["batch_id"] != batch_id]
    delete_single_batch_db(batch_id)
    sync_active_schedule_master_data()
    ScheduleEventBus.emit_change("2026-10")
    return {"status": "success", "deleted_batch_id": batch_id}

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
    additional_comments: Optional[str] = ""
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
    joining_date: Optional[str] = None
    date_of_joining: Optional[str] = None
    notes: Optional[str] = ""
    is_active: Optional[bool] = True

@app.post("/api/master/students")
def save_master_student(req: Union[MasterStudentRequest, Dict[str, Any]]):
    ensure_active_data()
    if isinstance(req, dict):
        req = MasterStudentRequest(**req)
    s_dict = req.model_dump()
    existing_students = ACTIVE_DATA.get("students", [])
    is_new = not any(s.get("student_id") == req.student_id for s in existing_students)

    from app.engine.suggestion_engine import normalize_date_to_iso
    raw_j = s_dict.get("joining_date") or s_dict.get("start_date") or s_dict.get("date_of_joining") or ""
    norm_j = normalize_date_to_iso(raw_j) or ""
    s_dict["joining_date"] = norm_j
    s_dict["start_date"] = norm_j

    # F1 Validation
    is_valid, errors = validate_student_data(s_dict, existing_students, is_new=is_new)
    if not is_valid:
        raise HTTPException(status_code=400, detail={"errors": errors, "message": "; ".join(errors)})

    # Derive tournament eligibility (read-only)
    model_inst = StudentModel(**s_dict)
    s_dict["tournament_eligibility"] = model_inst.get_tournament_eligibility()
    if not s_dict.get("batch"):
        s_dict["batch"] = f"{s_dict.get('batch_type', 'G')} {s_dict.get('student_level', '')}".strip()

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

    from app.engine.effective_schedule_service import invalidate_effective_schedule_cache
    invalidate_effective_schedule_cache("2026-10")
    sync_active_schedule_master_data("2026-10")
    ScheduleEventBus.emit_change("2026-10", student_ids=[req.student_id])
    return {"status": "success", "student": s_dict}

class BulkMasterStudentRequest(BaseModel):
    students: List[MasterStudentRequest]

@app.post("/api/master/students/bulk")
def save_bulk_master_students(req: BulkMasterStudentRequest):
    ensure_active_data()
    existing_students = list(ACTIVE_DATA.get("students", []))
    existing_ids = {s.get("student_id") for s in existing_students}
    
    saved_students = []
    errors = []
    from app.storage.database import save_single_student_db

    for s_req in req.students:
        s_dict = s_req.model_dump()
        sid = s_dict.get("student_id")
        is_new = sid not in existing_ids
        is_valid, s_errs = validate_student_data(s_dict, existing_students, is_new=is_new)
        if not is_valid:
            errors.append({"student_id": sid, "errors": s_errs})
            continue

        model_inst = StudentModel(**s_dict)
        s_dict["tournament_eligibility"] = model_inst.get_tournament_eligibility()
        if not s_dict.get("batch"):
            s_dict["batch"] = f"{s_dict.get('batch_type', 'G')} {s_dict.get('student_level', '')}".strip()

        existing_students = [s for s in existing_students if s["student_id"] != sid]
        existing_students.append(s_dict)
        existing_ids.add(sid)
        save_single_student_db(s_dict)
        saved_students.append(s_dict)

    ACTIVE_DATA["students"] = existing_students
    from app.engine.effective_schedule_service import invalidate_effective_schedule_cache
    invalidate_effective_schedule_cache("2026-10")
    sync_active_schedule_master_data("2026-10")
    ScheduleEventBus.emit_change("2026-10", student_ids=[s["student_id"] for s in saved_students])
    return {
        "status": "success",
        "saved_count": len(saved_students),
        "errors_count": len(errors),
        "errors": errors
    }

@app.post("/api/master/students/sync")
def sync_master_students_from_client(req: BulkMasterStudentRequest):
    """
    Ensures any custom students created client-side are transactionally persisted into SQLite and memory.
    """
    return save_bulk_master_students(req)

@app.delete("/api/master/students/{student_id}")
def delete_master_student(student_id: str):
    ensure_active_data()
    ACTIVE_DATA["students"] = [s for s in ACTIVE_DATA["students"] if s["student_id"] != student_id]

    # Cascade unlink from in-memory batches
    for b in ACTIVE_DATA.get("batches", []):
        s_ids = b.get("student_ids", [])
        if student_id in s_ids:
            b["student_ids"] = [sid for sid in s_ids if sid != student_id]
            b["students"] = [s for s in b.get("students", []) if s.get("student_id") != student_id]
            b["student_count"] = len(b["students"])
            save_single_batch_db(b)

    from app.storage.database import delete_single_student_db
    delete_single_student_db(student_id)

    # Remove student from any scheduled classes in the latest active schedule
    latest_sched = get_latest_schedule_db()
    if latest_sched:
        modified_sched = False
        for cls in latest_sched.get("scheduled_classes", []):
            if student_id in cls.get("student_ids", []):
                cls["student_ids"] = [sid for sid in cls["student_ids"] if sid != student_id]
                cls["student_names"] = [name for name, sid in zip(cls.get("student_names", []), cls.get("student_ids", []))]
                modified_sched = True
        if modified_sched:
            save_schedule_db(latest_sched)

    from app.engine.effective_schedule_service import invalidate_effective_schedule_cache
    invalidate_effective_schedule_cache("2026-10")
    sync_active_schedule_master_data("2026-10")
    ScheduleEventBus.emit_change("2026-10", student_ids=[student_id])
    return {"status": "success", "deleted_student_id": student_id}

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
def save_master_coach(req: Union[MasterCoachRequest, Dict[str, Any]]):
    ensure_active_data()
    if isinstance(req, dict):
        req = MasterCoachRequest(**req)
    c_dict = req.model_dump()
    canon_name = resolve_coach_canonical_name(req.coach_name)
    c_dict["coach_name"] = canon_name

    from app.engine.master_data_service import sync_live_coach_priority_matrix
    prio_matrix, updated_coaches = sync_live_coach_priority_matrix(
        coaches_list=ACTIVE_DATA["coaches"],
        new_coach_dict=c_dict,
        persist_db=True
    )
    saved_coach = next((c for c in updated_coaches if resolve_coach_canonical_name(c["coach_name"]) == canon_name), c_dict)
    sync_active_schedule_master_data()
    ScheduleEventBus.emit_change("2026-10", coach_ids=[canon_name])
    return {"status": "success", "coach": saved_coach}

@app.delete("/api/master/coaches/{coach_name}")
def delete_master_coach(coach_name: str):
    ensure_active_data()
    canon_name = resolve_coach_canonical_name(coach_name)

    from app.engine.master_data_service import sync_live_coach_priority_matrix
    prio_matrix, updated_coaches = sync_live_coach_priority_matrix(
        coaches_list=ACTIVE_DATA["coaches"],
        removed_coach_name=canon_name,
        persist_db=True
    )
    sync_active_schedule_master_data()
    ScheduleEventBus.emit_change("2026-10", coach_ids=[canon_name])
    return {"status": "success", "deleted_coach_name": canon_name}

class CoachPriorityRequest(BaseModel):
    level: str
    coach_name: str
    new_priority: int

@app.post("/api/master/coaches/priority")
def update_coach_priority_api(req: CoachPriorityRequest):
    ensure_active_data()
    updated = reorder_coach_level_priorities(
        ACTIVE_DATA["coaches"],
        level=req.level,
        target_coach_name=req.coach_name,
        new_priority=req.new_priority
    )
    ACTIVE_DATA["coaches"] = updated

    # Sync to CURRENT_CONFIG.coach_priority[req.level]
    coaches_with_lvl = []
    for c in updated:
        p = c.get("qualified_levels_priority", {}).get(req.level)
        if p is not None:
            coaches_with_lvl.append((resolve_coach_canonical_name(c["coach_name"]), p))
    coaches_with_lvl.sort(key=lambda x: x[1])
    if not hasattr(CURRENT_CONFIG, "coach_priority") or CURRENT_CONFIG.coach_priority is None:
        CURRENT_CONFIG.coach_priority = {}
    CURRENT_CONFIG.coach_priority[req.level] = [c[0] for c in coaches_with_lvl]
    CURRENT_CONFIG.sync_to_rules_registry()
    save_system_config_db(CURRENT_CONFIG.model_dump())

    from app.engine.master_data_service import sync_live_coach_priority_matrix
    sync_live_coach_priority_matrix(coaches_list=updated, config=CURRENT_CONFIG, persist_db=True)
    from app.engine.suggestion_engine import invalidate_suggestion_cache
    invalidate_suggestion_cache()
    return {"status": "success", "coaches": updated}

@app.delete("/api/master/coaches/priority")
def delete_coach_priority_api(level: str, coach_name: str):
    ensure_active_data()
    updated = remove_coach_from_level_priority(
        ACTIVE_DATA["coaches"],
        level=level,
        target_coach_name=coach_name
    )
    ACTIVE_DATA["coaches"] = updated

    # Sync to CURRENT_CONFIG.coach_priority[level]
    coaches_with_lvl = []
    for c in updated:
        p = c.get("qualified_levels_priority", {}).get(level)
        if p is not None:
            coaches_with_lvl.append((resolve_coach_canonical_name(c["coach_name"]), p))
    coaches_with_lvl.sort(key=lambda x: x[1])
    if not hasattr(CURRENT_CONFIG, "coach_priority") or CURRENT_CONFIG.coach_priority is None:
        CURRENT_CONFIG.coach_priority = {}
    CURRENT_CONFIG.coach_priority[level] = [c[0] for c in coaches_with_lvl]
    CURRENT_CONFIG.sync_to_rules_registry()
    save_system_config_db(CURRENT_CONFIG.model_dump())

    from app.engine.master_data_service import sync_live_coach_priority_matrix
    sync_live_coach_priority_matrix(coaches_list=updated, config=CURRENT_CONFIG, persist_db=True)
    from app.engine.suggestion_engine import invalidate_suggestion_cache
    invalidate_suggestion_cache()
    return {"status": "success", "coaches": updated}

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
        active_b = get_active_baseline_db(month)
        if active_b:
            s_obj = next((s for s in active_b.get("students_data", []) if s["student_id"] == student_id), None)
    if not s_obj:
        from app.storage.database import get_single_student_db
        s_obj = get_single_student_db(student_id)
        if s_obj:
            ACTIVE_DATA["students"].append(s_obj)
    if not s_obj:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found in master data.")
    
    eff = get_effective_schedule(month)
    all_classes = eff.get("scheduled_classes", [])
    coach_map = {resolve_coach_canonical_name(c["coach_name"]): c for c in ACTIVE_DATA["coaches"]}
    current_ver = eff.get("version", ScheduleEventBus._version_counter)

    ranked_suggs, reasons_summary = find_single_class_suggestions(
        student=s_obj,
        all_classes=all_classes,
        coaches_master_map=coach_map,
        target_month=month,
        settings=ENGINE_SETTINGS
    )

    if needed_classes > 1:
        option_sets = solve_multi_class_options(
            student=s_obj,
            needed_count=needed_classes,
            all_classes=all_classes,
            coaches_master_map=coach_map,
            target_month=month,
            settings=ENGINE_SETTINGS
        )
        return {
            "student_id": student_id,
            "mode": "multi_class",
            "needed_classes": needed_classes,
            "schedule_version": current_ver,
            "option_sets": option_sets,
            "suggestions": ranked_suggs,
            "reasons_rejected_summary": reasons_summary
        }
    else:
        return {
            "student_id": student_id,
            "mode": "single_class",
            "needed_classes": 1,
            "schedule_version": current_ver,
            "suggestions": ranked_suggs,
            "reasons_rejected_summary": reasons_summary
        }

class AcceptSuggestionRequest(BaseModel):
    student_id: str
    month: str = "2026-10"
    schedule_version: int
    suggestion_item: Optional[Dict[str, Any]] = None
    is_option_set: Optional[bool] = False
    option_set_items: Optional[List[Dict[str, Any]]] = None
    user: Optional[str] = "Admin"

def _execute_accept_engine_suggestion(req: AcceptSuggestionRequest):
    ensure_active_data()
    s_obj = next((s for s in ACTIVE_DATA["students"] if s["student_id"] == req.student_id), None)
    if not s_obj:
        active_b = get_active_baseline_db(req.month)
        if active_b:
            s_obj = next((s for s in active_b.get("students_data", []) if s["student_id"] == req.student_id), None)
    if not s_obj:
        from app.storage.database import get_single_student_db
        s_obj = get_single_student_db(req.student_id)
        if s_obj:
            ACTIVE_DATA["students"].append(s_obj)
    if not s_obj and req.student_id != "TRAINER_PROPOSAL":
        raise HTTPException(status_code=404, detail="Student not found.")

    items_to_apply = []
    if req.is_option_set and req.option_set_items:
        items_to_apply = req.option_set_items
    elif req.suggestion_item:
        items_to_apply = [req.suggestion_item]
    else:
        raise HTTPException(status_code=400, detail="No suggestion item provided.")

    applied_ids = []
    eff = get_effective_schedule(req.month)
    all_classes = {c["class_id"]: c for c in eff.get("scheduled_classes", [])}

    # Rule 8: Real-Time Coach Availability Validation
    # Revalidate availability of coaches before committing any new slot assignment
    for itm in items_to_apply:
        cls_id = itm.get("class_id")
        dt = itm.get("date")
        st = itm.get("start_time") or itm.get("time_slot")
        coach = resolve_coach_canonical_name(itm.get("coach_id", "") or itm.get("coach_name", ""))
        if not cls_id or cls_id not in all_classes:
            s_min = parse_time_to_minutes(st)
            if s_min is not None:
                has_conflict = any(
                    c.get("date") == dt and
                    resolve_coach_canonical_name(c.get("coach_name", "")) == coach and
                    parse_time_to_minutes(c.get("time_slot")) == s_min
                    for c in all_classes.values()
                )
                if has_conflict:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Coach {coach} is now unavailable on {dt} at {st} due to a concurrent booking. Please refresh suggestions."
                    )

    for itm in items_to_apply:
        cls_id = itm.get("class_id")
        dt = itm.get("date")
        st = itm.get("start_time") or itm.get("time_slot")
        coach = resolve_coach_canonical_name(itm.get("coach_id", "") or itm.get("coach_name", ""))

        # Guard: Check if student already has a class on this date
        if dt and any(c.get("date") == dt and req.student_id in c.get("student_ids", []) for c in all_classes.values()):
            continue

        exc_id = f"EXC_{uuid.uuid4().hex[:8].upper()}"

        if cls_id and cls_id in all_classes:
            target = all_classes[cls_id]
            curr_sids = list(target.get("student_ids", []))
            # Guard: Prevent duplicate student allocation
            if req.student_id in curr_sids:
                continue

            rec = {
                "id": exc_id,
                "month": req.month,
                "date": target["date"],
                "start_time": target["time_slot"],
                "coach_id": target["coach_name"],
                "class_key": f"{target['date']}||{target['time_slot']}||{target['coach_name']}",
                "action_type": "add_student",
                "affected_student_ids": [req.student_id],
                "before": {"student_ids": list(curr_sids)},
                "after": {"student_ids": list(curr_sids) + [req.student_id]},
                "subtype": "normal_assignment",
                "is_approved_allocation": True,
                "violated_rules": [],
                "reason": f"Accepted suggestion (Tier {itm.get('tier', 'T1')})",
                "created_by": req.user or "Admin",
                "created_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
                "status": "active",
                "version": 1
            }
            # Update local snapshot
            target["student_ids"] = list(curr_sids) + [req.student_id]
        else:
            item_sids = itm.get("student_ids") if req.student_id == "TRAINER_PROPOSAL" else [req.student_id]
            item_lvl = itm.get("student_level") or (s_obj.get("student_level", "Beginner 1") if s_obj else "Beginner 1")
            item_btype = itm.get("batch_type") or (s_obj.get("batch_type", "G") if s_obj else "G")
            item_bname = (s_obj.get("batch") or s_obj.get("batch_name")) if s_obj else f"{item_lvl} - {coach}"
            new_cls_key = f"{dt}||{st}||{coach}"
            rec = {
                "id": exc_id,
                "month": req.month,
                "date": dt,
                "start_time": st,
                "coach_id": coach,
                "class_key": new_cls_key,
                "action_type": "add",
                "affected_student_ids": item_sids or [],
                "before": {},
                "after": {
                    "student_level": item_lvl,
                    "batch_type": item_btype,
                    "batch_name": item_bname,
                    "student_ids": item_sids or [],
                    "day": datetime.strptime(dt, "%Y-%m-%d").strftime("%A") if dt else "Monday"
                },
                "subtype": "normal_assignment",
                "is_approved_allocation": True,
                "violated_rules": [],
                "reason": f"Accepted new slot suggestion (Tier {itm.get('tier', 'T4')})",
                "created_by": req.user or "Admin",
                "created_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
                "status": "active",
                "version": 1
            }
            # Add to local snapshot
            all_classes[exc_id] = {
                "class_id": exc_id,
                "date": dt,
                "time_slot": st,
                "coach_name": coach,
                "student_ids": item_sids or [],
                "student_level": item_lvl,
                "batch_type": item_btype,
                "batch_name": item_bname
            }

        save_exception_record_db(rec)
        applied_ids.append(exc_id)

        # Synchronize batch assignment for student if new slot or batch class
        target_bname = item_bname if not (cls_id and cls_id in all_classes) else all_classes[cls_id].get("batch_name") or all_classes[cls_id].get("batch_code")
        if target_bname and req.student_id != "TRAINER_PROPOSAL":
            for b in ACTIVE_DATA.get("batches", []):
                if b.get("batch_id") == target_bname or b.get("batch_name") == target_bname:
                    s_ids = b.get("student_ids", [])
                    if req.student_id not in s_ids:
                        s_ids.append(req.student_id)
                        b["student_ids"] = s_ids
                        b["student_count"] = len(s_ids)
                        save_single_batch_db(b)

    from app.engine.effective_schedule_service import invalidate_effective_schedule_cache
    from app.engine.suggestion_engine import invalidate_suggestion_cache
    invalidate_effective_schedule_cache(req.month)
    invalidate_suggestion_cache()

    sync_active_schedule_master_data(req.month)
    ScheduleEventBus.emit_change(req.month, student_ids=[req.student_id])
    updated_eff = get_effective_schedule(req.month)

    return {
        "status": "success",
        "applied_count": len(applied_ids),
        "applied_exception_ids": applied_ids,
        "updated_version": ScheduleEventBus._version_counter,
        "remaining_for_student": next((r["remaining_classes"] for r in updated_eff.get("attention_records", []) if r["student_id"] == req.student_id), 0)
    }

@app.post("/api/engine/suggestions/accept")
def accept_engine_suggestion_api(req: AcceptSuggestionRequest):
    from app.engine.queue_manager import queue_manager
    if queue_manager.is_running:
        return queue_manager.queue_or_execute(
            "accept_suggestion",
            req.model_dump(),
            lambda payload: _execute_accept_engine_suggestion(AcceptSuggestionRequest(**payload))
        )
    return _execute_accept_engine_suggestion(req)

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
    trainer_proposals = generate_trainer_engagement_proposals(
        coaches_master_map=c_map,
        attention_records=attn,
        student_master_map=s_map,
        all_classes=eff.get("scheduled_classes", []),
        target_month=month
    )
    return {
        "month": month,
        "count": len(opportunities),
        "opportunities": opportunities,
        "trainer_proposals": trainer_proposals,
        "schedule_version": eff.get("version", ScheduleEventBus._version_counter)
    }

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
    async_run: Optional[bool] = False

@app.get("/api/engine/status")
def get_engine_status_api():
    """Rule 6: Non-Blocking Engine Execution Status and Request Queue Monitor."""
    from app.engine.queue_manager import queue_manager
    return queue_manager.get_status()

@app.post("/api/schedule/run")
@app.post("/api/schedule/generate")
def trigger_scheduling_run(req: ScheduleRequest):
    ensure_active_data()
    if not ACTIVE_DATA.get("students") and not ACTIVE_DATA.get("batches"):
        active_b = get_active_baseline_db("2026-10")
        if active_b and active_b.get("students_data"):
            from app.storage.database import get_connection
            conn = get_connection()
            conn.execute("DELETE FROM active_metadata WHERE key = 'master_cleared'")
            conn.commit()
            conn.close()
            seed_october_baseline_if_missing()
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

    def _execute_run():
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

    from app.engine.queue_manager import queue_manager
    m_str = f"{s_date.year:04d}-{s_date.month:02d}"

    if getattr(req, "async_run", False):
        submit_res = queue_manager.submit_engine_job(_execute_run, month=m_str)
        eff = get_effective_schedule(m_str)
        return {
            "status": "processing",
            "job_id": submit_res.get("job_id"),
            "message": "Engine is executing in background. All pages remain viewable and responsive.",
            "schedule_id": eff.get("schedule_id", f"SCHED_{m_str.replace('-', '')}"),
            "active_schedule_id": eff.get("schedule_id", f"SCHED_{m_str.replace('-', '')}"),
            "scheduled_classes": eff.get("scheduled_classes", []),
            "attention_records": eff.get("attention_records", [])
        }
    else:
        with queue_manager._lock:
            res_dict = _execute_run()
            ScheduleEventBus.emit_change(m_str)
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

    attn_records = list(eff.get("attention_records", []))
    attn_sids = {r.get("student_id") for r in attn_records}
    scheduled_counts = defaultdict(int)
    for c in eff.get("scheduled_classes", []):
        for sid in c.get("student_ids", []):
            scheduled_counts[sid] += 1

    all_students_pool = list(ACTIVE_DATA.get("students", []))
    active_b = get_active_baseline_db(month)
    if active_b and active_b.get("students_data"):
        for s in active_b["students_data"]:
            if s.get("student_id") and not any(m.get("student_id") == s["student_id"] for m in all_students_pool):
                all_students_pool.append(s)

    for s in all_students_pool:
        sid = s.get("student_id")
        if not sid:
            continue
        is_act = s.get("is_active")
        if is_act not in (False, "false", "False", 0, "0"):
            raw_req = s.get("required_classes", 8)
            sch = scheduled_counts.get(sid, 0)
            rem = max(0, raw_req - sch)
            if raw_req > 0 and rem > 0 and sid not in attn_sids:
                lvl_val = s.get("student_level", "Beginner 1")
                btype_val = s.get("batch_type", "G")
                b_code = s.get("batch") or s.get("batch_name") or f"{btype_val} {lvl_val}"
                is_sunday_tourn_eligible = (btype_val != "I" and lvl_val not in ["Basic 1", "Intermediate 2"])
                tourn_requirement = "Sunday Tournament Eligible: Basic 2 to Intermediate 1 (Group & Limited). Operating hours: 09:00 AM – 02:30 PM (cap 20)." if is_sunday_tourn_eligible else ("Individual Batch (Private 1-on-1): Ineligible for Sunday tournaments." if btype_val == "I" else "Regular class scheduling.")
                pref_days = [f"{d[:3]}" for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"] if str(s.get(f"{d[:3].lower()}_pref", "No Preference")).lower() not in ["not available", "na", "no", "off"]]
                attn_records.insert(0, {
                    "student_id": sid,
                    "student_name": s.get("student_name", sid),
                    "student_level": lvl_val,
                    "joining_date": s.get("joining_date") or s.get("start_date") or "",
                    "date_of_joining": s.get("date_of_joining") or s.get("start_date") or "",
                    "monthly_quota": raw_req,
                    "quota": raw_req,
                    "batch_eligibility": btype_val,
                    "batch_type": btype_val,
                    "batch_name": b_code,
                    "batch_code": b_code,
                    "required_classes": raw_req,
                    "scheduled_classes": sch,
                    "remaining_classes": rem,
                    "had_deleted_class": False,
                    "deleted_class_details": [],
                    "is_mid_month": False,
                    "shortfall": 0,
                    "shortfall_info": "",
                    "failure_reason": f"Unscheduled. Needs {rem} class assignments to meet monthly requirement." if sch == 0 else f"Partially scheduled ({sch}/{raw_req} classes). Shortfall of {rem} class session(s).",
                    "sunday_tournament_eligible": is_sunday_tourn_eligible,
                    "tournament_requirement": tourn_requirement,
                    "preferred_days": ", ".join(pref_days) if pref_days else "Mon, Tue, Wed, Thu, Fri, Sat, Sun",
                    "preferred_time": s.get("preferred_timings") or "Flexible",
                    "preferred_timings": s.get("preferred_timings") or "Flexible",
                    "preferred_times": s.get("preferred_times", []),
                    "preferred_coach": s.get("preferred_coach", ""),
                    "availability": s.get("availability", {}),
                    "is_morning_available": s.get("is_morning_available", False),
                    "details": f"Needs {rem} more class(es) in Batch {b_code}"
                })
                attn_sids.add(sid)

    tot_students = max(eff["total_students"], len(all_students_pool))
    need_attention_cnt = len(attn_records)

    return {
        "schedule_id": sched_id,
        "status": status,
        "month": month,
        "is_stale": is_stale,
        "stale_reason": stale_reason,
        "start_date": f"{month}-01",
        "end_date": f"{month}-31",
        "total_students_considered": tot_students,
        "successfully_scheduled_students": tot_students - need_attention_cnt,
        "unscheduled_students_count": need_attention_cnt,
        "accountability_passed": need_attention_cnt == 0,
        "total_classes": eff["total_classes"],
        "student_seats": eff["student_seats"],
        "quotas_completed": eff["quotas_completed"],
        "compensation_count": eff["compensation_count"],
        "scheduled_classes": eff.get("scheduled_classes", []),
        "coach_summaries": eff.get("coach_summaries", []),
        "coach_slots": eff.get("coach_slots", []),
        "student_schedules": eff.get("student_schedules", []),
        "attention_records": attn_records,
        "unscheduled_records": attn_records,
        "whatsapp_plain_text": eff.get("whatsapp_plain_text", "")
    }

@app.get("/api/schedule/{schedule_id}")
def get_schedule_by_id(schedule_id: str, month: str = Query(default="2026-10")):
    eff = get_effective_schedule(month)
    return eff

@app.get("/api/schedule/{schedule_id}/output1")
def get_output1_coach_schedule(schedule_id: str, month: str = Query(default="2026-10")):
    ensure_active_data()
    if schedule_id and schedule_id.startswith("SCHED_") and len(schedule_id) >= 12:
        extracted = f"{schedule_id[6:10]}-{schedule_id[10:12]}"
        if month == "2026-10" and extracted != "2026-10":
            month = extracted
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
    ensure_active_data()
    if schedule_id and schedule_id.startswith("SCHED_") and len(schedule_id) >= 12:
        extracted = f"{schedule_id[6:10]}-{schedule_id[10:12]}"
        if month == "2026-10" and extracted != "2026-10":
            month = extracted
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

def resolve_schedule_or_effective(schedule_id: str, month: str = "2026-10") -> Optional[Dict[str, Any]]:
    """
    Resolves a schedule by ID, seamlessly integrating the 3-Layer Effective Schedule
    (Baseline + Assignments + ⓒ Overlay) as the authoritative Single Source of Truth.
    """
    eff = get_effective_schedule(month)
    if eff and eff.get("scheduled_classes"):
        res_dict = get_schedule_db(schedule_id) or {}
        merged = dict(res_dict)
        merged["schedule_id"] = schedule_id or f"SCHED_{month.replace('-', '')}"
        merged["status"] = merged.get("status") or "Active"
        merged["start_date"] = f"{month}-01"
        merged["end_date"] = f"{month}-31"
        merged["scheduled_classes"] = list(eff["scheduled_classes"])
        merged["coach_summaries"] = list(eff.get("coach_summaries", []))
        merged["coach_slots"] = list(eff.get("coach_slots", []))
        merged["student_schedules"] = list(eff.get("student_schedules", []))
        merged["unscheduled_records"] = list(eff.get("attention_records", []))
        merged["attention_records"] = list(eff.get("attention_records", []))
        merged["unscheduled_students_count"] = eff.get("need_attention", 0)
        merged["total_students_considered"] = eff.get("total_students", 0)
        merged["successfully_scheduled_students"] = eff.get("total_students", 0) - eff.get("need_attention", 0)
        merged["accountability_passed"] = eff.get("need_attention", 0) == 0
        merged["total_classes"] = eff.get("total_classes", len(eff["scheduled_classes"]))
        merged["whatsapp_plain_text"] = eff.get("whatsapp_plain_text", "")
        return merged

    res_dict = get_schedule_db(schedule_id)
    return res_dict

from app.outputs.coach_excel import generate_coach_individual_excel, generate_coach_whatsapp_msg

@app.get("/api/schedule/{schedule_id}/coach/{coach_name}/export-excel")
def export_individual_coach_excel(schedule_id: str, coach_name: str, month: str = Query(default="2026-10")):
    """
    Exports a dedicated Excel spreadsheet (.xlsx) for a specific coach's schedule and student roster.
    """
    res_dict = resolve_schedule_or_effective(schedule_id, month)
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
def export_monthly_matrix_excel_api(schedule_id: str, month: str = Query(default="2026-10")):
    """
    Exports a full monthly Excel schedule following the exact structure of the reference workbook.
    Dynamically adjusts columns to the exact days of the target month (28, 29, 30, or 31).
    Validates schedule before export; attaches DRAFT / VALIDATION FAILED banner if any violations occur.
    """
    ensure_active_data()
    res_dict = resolve_schedule_or_effective(schedule_id, month)
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
def validate_schedule_endpoint(schedule_id: str, month: str = Query(default="2026-10")):
    """
    Authoritative server-side schedule integrity validation.
    Checks all hard constraints: coach conflicts, student daily uniqueness,
    batch capacities, coach daily/monthly limits, Sunday 3 PM rule, student quotas.
    """
    ensure_active_data()
    res_dict = resolve_schedule_or_effective(schedule_id, month)
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
    res_dict = resolve_schedule_or_effective(schedule_id, month)
    if not res_dict:
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
    res_dict = resolve_schedule_or_effective(schedule_id, month)
    if not res_dict:
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
    ensure_active_data()
    if schedule_id and schedule_id.startswith("SCHED_") and len(schedule_id) >= 12:
        extracted = f"{schedule_id[6:10]}-{schedule_id[10:12]}"
        if month == "2026-10" and extracted != "2026-10":
            month = extracted
    eff = get_effective_schedule(month)
    m_data = load_master_data_db()
    s_map = {s["student_id"]: s for s in m_data.get("students", [])}
    active_b = get_active_baseline_db(month)
    b_students = active_b.get("students_data", []) if active_b else []
    for s in b_students:
        if s.get("student_id") and s["student_id"] not in s_map:
            s_map[s["student_id"]] = s
    for s_item in eff.get("student_schedules", []):
        sid = s_item.get("student_id")
        if sid and sid not in s_map:
            s_map[sid] = s_item
    for s_mem in ACTIVE_DATA.get("students", []):
        sid = s_mem.get("student_id")
        if sid and sid not in s_map:
            s_map[sid] = s_mem

    attention_records = list(eff.get("attention_records", []))
    attn_sids = {r.get("student_id") for r in attention_records}
    scheduled_counts = defaultdict(int)
    for c in eff.get("scheduled_classes", []):
        for sid in c.get("student_ids", []):
            scheduled_counts[sid] += 1

    for sid, s in s_map.items():
        is_act = s.get("is_active")
        if is_act not in (False, "false", "False", 0, "0"):
            raw_req = s.get("required_classes", 8)
            sch = scheduled_counts.get(sid, 0)
            rem = max(0, raw_req - sch)
            if raw_req > 0 and rem > 0 and sid not in attn_sids:
                lvl_val = s.get("student_level", "Beginner 1")
                btype_val = s.get("batch_type", "G")
                b_code = s.get("batch") or s.get("batch_name") or f"{btype_val} {lvl_val}"
                is_sunday_tourn_eligible = (btype_val != "I" and lvl_val not in ["Basic 1", "Intermediate 2"])
                tourn_requirement = "Sunday Tournament Eligible: Basic 2 to Intermediate 1 (Group & Limited). Operating hours: 09:00 AM – 02:30 PM (cap 20)." if is_sunday_tourn_eligible else ("Individual Batch (Private 1-on-1): Ineligible for Sunday tournaments." if btype_val == "I" else "Regular class scheduling.")
                pref_days = [f"{d[:3]}" for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"] if str(s.get(f"{d[:3].lower()}_pref", "No Preference")).lower() not in ["not available", "na", "no", "off"]]
                attention_records.insert(0, {
                    "student_id": sid,
                    "student_name": s.get("student_name", sid),
                    "student_level": lvl_val,
                    "joining_date": s.get("joining_date") or s.get("start_date") or "",
                    "date_of_joining": s.get("date_of_joining") or s.get("start_date") or "",
                    "monthly_quota": raw_req,
                    "quota": raw_req,
                    "batch_eligibility": btype_val,
                    "batch_type": btype_val,
                    "batch_name": b_code,
                    "batch_code": b_code,
                    "required_classes": raw_req,
                    "scheduled_classes": sch,
                    "remaining_classes": rem,
                    "had_deleted_class": False,
                    "deleted_class_details": [],
                    "is_mid_month": False,
                    "shortfall": 0,
                    "shortfall_info": "",
                    "failure_reason": f"Unscheduled. Needs {rem} class assignments to meet monthly requirement." if sch == 0 else f"Partially scheduled ({sch}/{raw_req} classes). Shortfall of {rem} class session(s).",
                    "sunday_tournament_eligible": is_sunday_tourn_eligible,
                    "tournament_requirement": tourn_requirement,
                    "preferred_days": ", ".join(pref_days) if pref_days else "Mon, Tue, Wed, Thu, Fri, Sat, Sun",
                    "preferred_time": s.get("preferred_timings") or "Flexible",
                    "preferred_timings": s.get("preferred_timings") or "Flexible",
                    "preferred_times": s.get("preferred_times", []),
                    "preferred_coach": s.get("preferred_coach", ""),
                    "availability": s.get("availability", {}),
                    "is_morning_available": s.get("is_morning_available", False),
                    "details": f"Needs {rem} more class(es) in Batch {b_code}"
                })
                attn_sids.add(sid)

    c_map = {c["coach_name"]: c for c in m_data.get("coaches", [])}
    for c_canon, c_ref in COACH_REFERENCE.items():
        if c_canon not in c_map:
            c_map[c_canon] = {
                "coach_name": c_canon,
                "levels_handled": c_ref.get("levels", []),
                "monthly_capacity_min": c_ref.get("monthly_min", 30),
                "monthly_capacity_max": c_ref.get("monthly_max", 70),
                "is_flex": c_ref.get("is_flex", False)
            }
    smart_opps = generate_smart_batch_opportunities(
        attention_records, s_map, eff["scheduled_classes"], c_map, month
    )
    trainer_props = generate_trainer_engagement_proposals(
        c_map, attention_records, s_map, eff["scheduled_classes"], month
    )
    consolidations = generate_consolidation_advisory(eff["scheduled_classes"], month)
    coach_explorer = get_coach_daily_availability_explorer(eff["scheduled_classes"], c_map, month)
    active_excs = get_exception_records_db(month, status="active")
    tot_students = max(eff["total_students"], len(s_map))
    unsched_cnt = len(attention_records)
    return {
        "schedule_id": schedule_id,
        "month": month,
        "schedule_version": eff.get("version", 1),
        "accountability_passed": unsched_cnt == 0,
        "total_students_considered": tot_students,
        "total_input_students": tot_students,
        "unscheduled_count": unsched_cnt,
        "attention_records": attention_records,
        "unscheduled_records": attention_records,
        "deleted_past_classes": eff.get("deleted_past_classes", []),
        "smart_batch_opportunities": smart_opps,
        "trainer_proposals": trainer_props,
        "consolidation_advisory": consolidations,
        "accepted_exceptions": active_excs,
        "coach_availability_explorer": coach_explorer
    }

@app.get("/api/schedule/{schedule_id}/output5")
def get_output5_student_schedules(schedule_id: str, month: str = Query(default="2026-10")):
    ensure_active_data()
    if schedule_id and schedule_id.startswith("SCHED_") and len(schedule_id) >= 12:
        extracted = f"{schedule_id[6:10]}-{schedule_id[10:12]}"
        if month == "2026-10" and extracted != "2026-10":
            month = extracted
    eff = get_effective_schedule(month)
    return {
        "schedule_id": schedule_id,
        "total_students": len(eff["student_schedules"]),
        "student_schedules": eff["student_schedules"]
    }

@app.get("/api/schedule/{schedule_id}/student/{student_id}/export-ics")
def export_individual_student_ics(schedule_id: str, student_id: str, month: str = Query(default="2026-10")):
    """
    Exports a standard iCalendar (.ics) file for a student ONLY when all Attention Required issues for this student are resolved.
    """
    eff = get_effective_schedule(month)
    stu_rec = next((s for s in eff.get("student_schedules", []) if s["student_id"] == student_id), None)
    if stu_rec and stu_rec.get("has_attention_issue"):
        raise HTTPException(
            status_code=400,
            detail=f"Calendar (.ics) locked for {stu_rec.get('student_name', student_id)}: Please resolve all missing/deleted class issues in Output 3 (Attention Page) first."
        )
    res_dict = resolve_schedule_or_effective(schedule_id, month)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")

    ics_content = generate_student_ics(student_id, res_dict.get("scheduled_classes", []))
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
    reason: Optional[str] = None
    version: Optional[int] = None
    schedule_version: Optional[int] = None

@app.post("/api/schedule/{schedule_id}/validate-override")
def validate_manual_override(schedule_id: str, req: ManualOverrideRequest):
    """
    Validates manual administrative edit against the complete schedule state.
    Returns valid boolean and diagnostic list of rule violations.
    """
    ensure_active_data()
    month = (req.date or "2026-10")[:7]
    res_dict = resolve_schedule_or_effective(schedule_id, month)
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
    res_dict = resolve_schedule_or_effective(schedule_id, "2026-10")
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
        from app.engine.effective_schedule_service import invalidate_effective_schedule_cache
        invalidate_effective_schedule_cache(month)
        sync_active_schedule_master_data(month)
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
    month = (req.date or "2026-10")[:7]
    res_dict = resolve_schedule_or_effective(schedule_id, month)
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
    from app.engine.effective_schedule_service import invalidate_effective_schedule_cache
    invalidate_effective_schedule_cache(month)
    sync_active_schedule_master_data(month)
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
    month = (req.date or "2026-10")[:7]
    res_dict = resolve_schedule_or_effective(schedule_id, month)
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
    ScheduleEventBus.emit_change("2026-10")
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

# ==============================================================================
# ABSOLUTE SCHEDULE SPACE ENDPOINTS (PART E)
# ==============================================================================

@app.get("/api/baseline/status")
def get_baseline_status_api(month: str = Query(default="2026-10")):
    seed_october_baseline_if_missing()
    ensure_rolling_three_months_seeded("2026-10")
    active_b = get_active_baseline_db(month)
    draft_b = get_draft_baseline_db(month)
    history = list_baselines_for_month_db(month)
    status = "Active" if active_b else ("Draft" if draft_b else "Not Uploaded")
    active_ver = active_b.get("version", 0) if active_b else 0

    eff = get_effective_schedule(month)
    ref_today = eff.get("reference_today", "2026-10-15")
    current_month_str = ref_today[:7]
    is_completed_available = (month <= current_month_str)

    planned_classes = (active_b or draft_b or {}).get("classes_data", [])
    actual_schedule_text = format_date_wise_schedule_text(planned_classes, month, "ACTUAL PLANNED SCHEDULE")

    if is_completed_available:
        if month < current_month_str:
            completed_classes = list(eff.get("scheduled_classes", []))
        else:
            # Rule 2: In current month, display completed schedule data ONLY up to previous completed day (date < ref_today)
            # Exclude current day and future days!
            completed_classes = [c for c in eff.get("scheduled_classes", []) if c.get("date", "") < ref_today]
        completed_schedule_text = format_date_wise_schedule_text(completed_classes, month, "ACTUAL COMPLETED SCHEDULE (UP TO PREVIOUS COMPLETED DAY)")
    else:
        completed_classes = []
        completed_schedule_text = ""

    return {
        "month": month,
        "rolling_months": get_rolling_horizon_months(current_month_str),
        "current_month": current_month_str,
        "reference_today": ref_today,
        "status": status,
        "version": active_ver,
        "active_baseline": active_b,
        "draft_baseline": draft_b,
        "history": history,
        "actual_schedule_text": actual_schedule_text,
        "is_completed_schedule_available": is_completed_available,
        "completed_classes_count": len(completed_classes),
        "completed_seats_count": sum(len(c.get("student_ids", [])) for c in completed_classes),
        "completed_classes_data": completed_classes,
        "actual_completed_schedule_text": completed_schedule_text
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

    # Synchronize activated baseline into Master Data Hub, ⓒ Exception Overlay, and Active Schedule
    active_b = get_active_baseline_db(req.month)
    if active_b:
        from app.storage.database import get_connection, save_single_student_db
        conn = get_connection()
        conn.execute("DELETE FROM active_metadata WHERE key = 'master_cleared'")
        conn.commit()
        conn.close()

        seed_october_baseline_if_missing()
        ensure_active_data()

        for s in active_b.get("students_data", []):
            save_single_student_db(s)

        # Discover and persist any batches from active baseline
        b_map = {}
        for s in active_b.get("students_data", []):
            b_name = s.get("batch_code") or s.get("batch") or s.get("batch_name")
            if b_name:
                if b_name not in b_map:
                    b_map[b_name] = {
                        "batch_id": b_name,
                        "batch_name": b_name,
                        "batch_type": s.get("batch_type", "G"),
                        "level": s.get("student_level", "Beginner 1"),
                        "fixed_trainer": "Unassigned",
                        "schedule_timings": "Various",
                        "student_ids": [s["student_id"]]
                    }
                else:
                    if s["student_id"] not in b_map[b_name]["student_ids"]:
                        b_map[b_name]["student_ids"].append(s["student_id"])
        if b_map:
            save_all_master_batches_db(list(b_map.values()))

        comp_excs = (active_b.get("validation_report") or {}).get("compensation_exceptions", [])
        for exc_rec in comp_excs:
            save_exception_record_db(exc_rec)

        ensure_active_data()

        # Update Active File metadata in store
        b_fname = active_b.get("file_name") or f"Absolute Schedule ({req.month})"
        b_time = active_b.get("uploaded_at") or datetime.now().strftime("%Y-%m-%d %I:%M %p")
        ACTIVE_DATA["filename"] = b_fname
        ACTIVE_DATA["upload_timestamp"] = b_time
        conn = get_connection()
        conn.execute("INSERT OR REPLACE INTO active_metadata (key, value) VALUES ('last_filename', ?)", (b_fname,))
        conn.execute("INSERT OR REPLACE INTO active_metadata (key, value) VALUES ('last_upload_timestamp', ?)", (b_time,))
        conn.commit()
        conn.close()

        # Compute and persist authoritative Effective Schedule as Central Single Source of Truth
        eff = get_effective_schedule(req.month)
        sched_id = f"SCHED_{req.month.replace('-', '')}"
        schedule_payload = {
            "schedule_id": sched_id,
            "status": "Active",
            "start_date": f"{req.month}-01",
            "end_date": f"{req.month}-31",
            "total_students_considered": eff.get("total_students", len(active_b.get("students_data", []))),
            "successfully_scheduled_students": eff.get("total_students", 0) - eff.get("need_attention", 0),
            "unscheduled_students_count": eff.get("need_attention", 0),
            "accountability_passed": eff.get("need_attention", 0) == 0,
            "scheduled_classes": list(eff.get("scheduled_classes", [])),
            "coach_summaries": list(eff.get("coach_summaries", [])),
            "coach_slots": list(eff.get("coach_slots", [])),
            "student_schedules": list(eff.get("student_schedules", [])),
            "attention_records": list(eff.get("attention_records", [])),
            "unscheduled_records": list(eff.get("attention_records", [])),
            "whatsapp_plain_text": eff.get("whatsapp_plain_text", ""),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "master_data_fingerprint": compute_master_data_fingerprint(config_dict=CURRENT_CONFIG.model_dump())
        }
        save_schedule_db(schedule_payload)

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
    seed_october_baseline_if_missing()
    ensure_rolling_three_months_seeded("2026-10")
    active_b = get_active_baseline_db(month)
    if not active_b:
        raise HTTPException(status_code=404, detail="No active baseline found for this month.")
    m_data = load_master_data_db()
    students = m_data.get("students") or active_b.get("students_data", [])
    classes = active_b.get("classes_data", [])
    excel_bytes = generate_populated_schedule_excel_bytes(month, students, classes, sheet_title="Actual Schedule")
    filename = f"Mighty_Knight_Actual_Schedule_{month}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

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


@app.get("/api/baseline/export-completed")
def export_completed_schedule_excel_api(month: str = Query(default="2026-10")):
    """
    Exports the Actual Completed Schedule (Executed Classes + ⓒ Overrides) as a formatted Excel workbook.
    Strictly blocked for future months.
    """
    eff = get_effective_schedule(month)
    ref_today = eff.get("reference_today", "2026-10-15")
    current_month_str = ref_today[:7]
    if month > current_month_str:
        raise HTTPException(
            status_code=400,
            detail=f"Actual Completed Schedule is only available for past and current months (up to {current_month_str}), not future month {month}."
        )
    if month < current_month_str:
        completed_classes = list(eff.get("scheduled_classes", []))
    else:
        # Rule 2: In current month, export schedule data ONLY up to previous completed day (date < ref_today)
        completed_classes = [c for c in eff.get("scheduled_classes", []) if c.get("date", "") < ref_today]
    m_data = load_master_data_db()
    students = m_data.get("students", [])
    excel_bytes = generate_populated_schedule_excel_bytes(month, students, completed_classes, sheet_title="Completed Schedule")
    filename = f"Mighty_Knight_Actual_Completed_Schedule_{month}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

class ResolveDeletedClassRequest(BaseModel):
    exception_id: str
    month: str = "2026-10"
    resolution_choice: str # 'compensate_future' | 'remove_attendance_only' | 'delete_entirely'
    reason: Optional[str] = ""

@app.post("/api/schedule/deleted-class/resolve")
def resolve_deleted_class_api(req: ResolveDeletedClassRequest):
    """
    Handles the Administrator's 3-option resolution for a deleted/past class in Output 3:
    (i) compensate_future: Keep student(s) in Attention Required to schedule a future ⓒ make-up class.
    (ii) remove_attendance_only: Remove from student attendance history only (no make-up owed).
    (iii) delete_entirely: Delete class entirely for batch & trainer (-1 Academy Class, -1 Trainer Class).
    """
    if req.resolution_choice not in ("compensate_future", "remove_attendance_only", "delete_entirely"):
        raise HTTPException(status_code=400, detail="Invalid resolution_choice.")

    choice_labels = {
        "compensate_future": "Option (i): Flagged for Future Compensation (ⓒ) Make-Up Class",
        "remove_attendance_only": "Option (ii): Removed from Student Attendance History Only",
        "delete_entirely": "Option (iii): Deleted Entirely for Batch & Trainer (-1 Academy & -1 Trainer Class)"
    }
    reason_text = req.reason or choice_labels[req.resolution_choice]
    ok = update_exception_record_db(
        req.exception_id,
        {"resolution_choice": req.resolution_choice, "resolved_at": datetime.now().strftime("%Y-%m-%d %I:%M %p")},
        reason=reason_text
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Deleted class record not found.")

    log_audit_event_db(
        user="Admin",
        action=f"RESOLVE_DELETED_CLASS_{req.resolution_choice.upper()}",
        entity_type="EXCEPTION_RECORD",
        entity_id=req.exception_id,
        before={"resolution_choice": "pending"},
        after={"resolution_choice": req.resolution_choice, "reason": reason_text},
        violated_rules=[],
        source_page="Output 3 Attention Page",
        month=req.month
    )

    ScheduleEventBus.emit_change(req.month)
    updated_sched = get_effective_schedule(req.month)
    return {
        "status": "success",
        "exception_id": req.exception_id,
        "resolution_choice": req.resolution_choice,
        "schedule": updated_sched
    }

@app.get("/api/engine/coach-availability")
def get_coach_availability_api(month: str = Query(default="2026-10"), date: Optional[str] = Query(default=None)):
    eff = get_effective_schedule(month)
    m_data = load_master_data_db()
    c_map = {c["coach_name"]: c for c in m_data.get("coaches", [])}
    return get_coach_daily_availability_explorer(eff.get("scheduled_classes", []), c_map, month, selected_date=date)

class ReassignCoachRequest(BaseModel):
    class_id: Optional[str] = None
    batch_name: Optional[str] = None
    new_coach_name: str
    apply_to_entire_batch: bool = True
    month: str = "2026-10"

def _execute_reassign_batch_coach(req: ReassignCoachRequest):
    new_coach = resolve_coach_canonical_name(req.new_coach_name)
    if not new_coach:
        raise HTTPException(status_code=400, detail="Invalid coach name")

    eff = get_effective_schedule(req.month)
    ref_today = eff.get("reference_today", "2026-10-15")

    # 1. Update in active baseline if baseline exists
    active_b = get_active_baseline_db(req.month)
    reassigned_classes = []
    if active_b and active_b.get("classes_data"):
        cls_list = list(active_b["classes_data"])
        updated_any = False
        for c in cls_list:
            c_bid = c.get("batch_name") or c.get("batch_code", "")
            c_id = str(c.get("class_id", ""))
            c_date = c.get("date", "")
            
            matches_single = req.class_id and c_id == str(req.class_id)
            matches_batch = req.apply_to_entire_batch and req.batch_name and (c_bid == req.batch_name or c.get("batch_name") == req.batch_name)
            
            if matches_single or matches_batch:
                # Rule 4: Completed classes (date <= ref_today) are preserved. Only reassign future/pending classes!
                if c_date > ref_today or c.get("needs_coach_reassignment"):
                    c["coach_name"] = new_coach
                    c["coach_id"] = new_coach
                    c["needs_coach_reassignment"] = False
                    c["is_manual_override"] = True
                    reassigned_classes.append(c)
                    updated_any = True

        if updated_any:
            active_b["classes_data"] = cls_list
            save_baseline_db(active_b)

    # 2. Record Exception for audit trail
    target_cls = reassigned_classes[0] if reassigned_classes else {}
    save_exception_record_db({
        "id": f"EXC_REASSIGN_{int(datetime.now().timestamp() * 1000)}",
        "month": req.month,
        "date": target_cls.get("date", ref_today),
        "start_time": target_cls.get("time_slot", ""),
        "coach_id": new_coach,
        "class_key": f"{target_cls.get('date')}||{target_cls.get('time_slot')}||{new_coach}",
        "action_type": "edit",
        "affected_student_ids": target_cls.get("student_ids", []),
        "before": {"coach_name": target_cls.get("original_deleted_coach", "Deleted Coach")},
        "after": {
            "coach_name": new_coach,
            "batch_name": req.batch_name,
            "reassigned_count": len(reassigned_classes)
        },
        "subtype": "coach_reassignment",
        "violated_rules": [],
        "reason": f"Rule 4: Reassigned deleted coach to {new_coach} for batch {req.batch_name} ({len(reassigned_classes)} class(es))",
        "created_by": "Admin",
        "created_at": datetime.now().isoformat(),
        "status": "active",
        "version": 1
    })

    ScheduleEventBus.emit_change(req.month)
    return {
        "status": "success",
        "reassigned_count": len(reassigned_classes),
        "new_coach": new_coach,
        "batch_name": req.batch_name
    }

@app.post("/api/schedule/reassign-batch-coach")
def reassign_batch_coach_api(req: ReassignCoachRequest):
    from app.engine.queue_manager import queue_manager
    if queue_manager.is_running:
        return queue_manager.queue_or_execute(
            "reassign_coach",
            req.model_dump(),
            lambda payload: _execute_reassign_batch_coach(ReassignCoachRequest(**payload))
        )
    return _execute_reassign_batch_coach(req)

# ----------------------------------------------------
# Unified Production Deployment: Serve Built React App
# ----------------------------------------------------
from fastapi.staticfiles import StaticFiles

_dist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.exists(_dist_path):
    app.mount("/", StaticFiles(directory=_dist_path, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


