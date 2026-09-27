import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import FileResponse
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
    log_db_status, BASE_DIR
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
    ACTIVE_DATA["students"] = data.get("students", [])
    ACTIVE_DATA["coaches"] = data.get("coaches", [])
    ACTIVE_DATA["batches"] = load_master_batches_db()
    ACTIVE_DATA["parsing_errors"] = data.get("parsing_errors", [])
    ACTIVE_DATA["filename"] = data.get("last_filename") or ("Master Data" if (ACTIVE_DATA["students"] or ACTIVE_DATA["batches"]) else "Empty (Clean Slate)")
    ACTIVE_DATA["upload_timestamp"] = data.get("last_upload_timestamp") or ""

@app.on_event("startup")
def startup_event():
    ensure_active_data()
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
    capacity_min: Optional[int] = 4
    capacity_max: Optional[int] = 10
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
        b_dict["capacity_min"] = 1 if b_dict["batch_type"] in ["I", "L"] else 4
    if not b_dict.get("capacity_max"):
        b_dict["capacity_max"] = 1 if b_dict["batch_type"] == "I" else (4 if b_dict["batch_type"] == "L" else 10)
    
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
    return {"status": "success", "batch": b_dict}

@app.delete("/api/master/batches/{batch_id:path}")
def delete_master_batch(batch_id: str):
    ensure_active_data()
    ACTIVE_DATA["batches"] = [b for b in ACTIVE_DATA.get("batches", []) if b["batch_id"] != batch_id]
    delete_single_batch_db(batch_id)
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

@app.post("/api/master/students")
def save_master_student(req: MasterStudentRequest):
    ensure_active_data()
    s_dict = req.model_dump()
    ACTIVE_DATA["students"] = [s for s in ACTIVE_DATA["students"] if s["student_id"] != req.student_id]
    ACTIVE_DATA["students"].append(s_dict)
    from app.storage.database import save_single_student_db
    save_single_student_db(s_dict)

    # If assigned_batch_id is provided, sync batch enrollment
    if req.assigned_batch_id:
        for b in ACTIVE_DATA.get("batches", []):
            if b["batch_id"] == req.assigned_batch_id:
                s_ids = b.get("student_ids", [])
                if req.student_id not in s_ids:
                    s_ids.append(req.student_id)
                    b["student_ids"] = s_ids
                    b["student_count"] = len(s_ids)
                    save_single_batch_db(b)

    # Synchronize the active schedule in SQLite so newly added students immediately reflect in Output 3
    latest_sched = get_latest_schedule_db()
    if latest_sched:
        recompute_schedule_outputs(
            latest_sched,
            ACTIVE_DATA["students"],
            ACTIVE_DATA.get("coaches", []),
            CURRENT_CONFIG
        )
        save_schedule_db(latest_sched)

    return {"status": "success", "student": s_dict}

@app.delete("/api/master/students/{student_id}")
def delete_master_student(student_id: str):
    ensure_active_data()
    ACTIVE_DATA["students"] = [s for s in ACTIVE_DATA["students"] if s["student_id"] != student_id]
    from app.storage.database import delete_single_student_db
    delete_single_student_db(student_id)

    # Synchronize the active schedule in SQLite
    latest_sched = get_latest_schedule_db()
    if latest_sched:
        recompute_schedule_outputs(
            latest_sched,
            ACTIVE_DATA["students"],
            ACTIVE_DATA.get("coaches", []),
            CURRENT_CONFIG
        )
        save_schedule_db(latest_sched)

    return {"status": "success", "deleted_student_id": student_id}

class MasterCoachRequest(BaseModel):
    coach_name: str
    levels_handled: List[str]
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
    special_comments: Optional[str] = ""
    temporary_exceptions: Optional[str] = ""

@app.post("/api/master/coaches")
def save_master_coach(req: MasterCoachRequest):
    ensure_active_data()
    c_dict = req.model_dump()
    ACTIVE_DATA["coaches"] = [c for c in ACTIVE_DATA["coaches"] if c["coach_name"].strip().lower() != req.coach_name.strip().lower()]
    ACTIVE_DATA["coaches"].append(c_dict)
    from app.storage.database import save_single_coach_db
    save_single_coach_db(c_dict)
    return {"status": "success", "coach": c_dict}

@app.delete("/api/master/coaches/{coach_name}")
def delete_master_coach(coach_name: str):
    ensure_active_data()
    ACTIVE_DATA["coaches"] = [c for c in ACTIVE_DATA["coaches"] if c["coach_name"].strip().lower() != coach_name.strip().lower()]
    from app.storage.database import delete_single_coach_db
    delete_single_coach_db(coach_name)
    return {"status": "success", "deleted_coach_name": coach_name}

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
    res_dict["master_data_fingerprint"] = compute_master_data_fingerprint(config_dict=CURRENT_CONFIG.model_dump())
    res_dict["is_stale"] = False
    save_schedule_db(res_dict)

    return res_dict

@app.get("/api/schedule/latest/active")
def get_active_or_latest_schedule():
    """
    Retrieves the most recent active schedule saved in SQLite for 0-loss state recovery on app launch/refresh.
    Fingerprint invalidation rules:
    - If master data or config changed and latest schedule is Finalized, marks it as stale with a clear reason
      and requires an explicit new scheduling run (never silently replaces Finalized schedule).
    - If latest schedule is Draft (or no schedule exists), automatically regenerates with current master data and config.
    """
    ensure_active_data()
    current_student_count = len(ACTIVE_DATA["students"])
    current_batch_count = len(ACTIVE_DATA.get("batches", []))

    if is_master_cleared_db() or (current_student_count == 0 and current_batch_count == 0):
        return {
            "schedule_id": None,
            "status": "Empty",
            "start_date": "",
            "end_date": "",
            "total_students_considered": 0,
            "successfully_scheduled_students": 0,
            "unscheduled_students_count": 0,
            "accountability_passed": True
        }

    current_fingerprint = compute_master_data_fingerprint(config_dict=CURRENT_CONFIG.model_dump())
    latest = get_latest_schedule_db()

    needs_regeneration = False
    if not latest:
        needs_regeneration = True
    elif latest.get("master_data_fingerprint") != current_fingerprint:
        if latest.get("status") == "Finalized":
            latest["is_stale"] = True
            latest["stale_reason"] = "Schedule is stale: master data or system configuration has changed since schedule was finalized. Please trigger an explicit new scheduling run."
            save_schedule_db(latest)
            return {
                "schedule_id": latest["schedule_id"],
                "status": "Finalized",
                "is_stale": True,
                "stale_reason": latest["stale_reason"],
                "start_date": latest.get("start_date", ""),
                "end_date": latest.get("end_date", ""),
                "total_students_considered": latest.get("total_students_considered", 0),
                "successfully_scheduled_students": latest.get("successfully_scheduled_students", 0),
                "unscheduled_students_count": latest.get("unscheduled_students_count", 0),
                "accountability_passed": latest.get("accountability_passed", True)
            }
        else:
            needs_regeneration = True

    if needs_regeneration:
        # Default to October 2026 reference month
        s_date = date(2026, 10, 1)
        e_date = date(2026, 10, 31)

        if latest and latest.get("start_date") and latest.get("end_date"):
            try:
                s_date = datetime.strptime(latest["start_date"], "%Y-%m-%d").date()
                e_date = datetime.strptime(latest["end_date"], "%Y-%m-%d").date()
            except Exception:
                pass

        students = [StudentModel(**s) for s in ACTIVE_DATA["students"]]
        coaches = [CoachModel(**c) for c in ACTIVE_DATA["coaches"]]
        result = run_scheduler(students, coaches, s_date, e_date, CURRENT_CONFIG)
        latest = result.model_dump()
        latest["master_data_fingerprint"] = current_fingerprint
        latest["is_stale"] = False
        save_schedule_db(latest)

    return {
        "schedule_id": latest["schedule_id"],
        "status": latest.get("status", "Draft"),
        "is_stale": latest.get("is_stale", False),
        "stale_reason": latest.get("stale_reason", ""),
        "start_date": latest.get("start_date", ""),
        "end_date": latest.get("end_date", ""),
        "total_students_considered": latest.get("total_students_considered", 0),
        "successfully_scheduled_students": latest.get("successfully_scheduled_students", 0),
        "unscheduled_students_count": latest.get("unscheduled_students_count", 0),
        "accountability_passed": latest.get("accountability_passed", True)
    }

@app.get("/api/schedule/{schedule_id}")
def get_schedule_by_id(schedule_id: str):
    res = get_schedule_db(schedule_id)
    if not res:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return res

@app.get("/api/schedule/{schedule_id}/output1")
def get_output1_coach_schedule(schedule_id: str):
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")
    res = ScheduleResult(**res_dict)
    whatsapp_text = generate_coach_schedule_text(res)
    return {
        "schedule_id": schedule_id,
        "coach_slots": [slot.model_dump() for slot in res.coach_schedule],
        "whatsapp_plain_text": whatsapp_text
    }

from app.outputs.admin_schedule import format_admin_schedule, generate_coach_summary

@app.get("/api/schedule/{schedule_id}/output2")
def get_output2_admin_schedule(schedule_id: str):
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")
    res = ScheduleResult(**res_dict)
    admin_rows = format_admin_schedule(res)
    coach_summaries = generate_coach_summary(res, ACTIVE_DATA.get("coaches", []))
    return {
        "schedule_id": schedule_id,
        "detailed_classes": admin_rows,
        "coach_summaries": coach_summaries
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
def get_individual_coach_whatsapp(schedule_id: str, coach_name: str):
    """
    Generates tailored WhatsApp schedule broadcast text for a specific coach.
    """
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")

    msg_text = generate_coach_whatsapp_msg(coach_name, res_dict.get("scheduled_classes", []))
    return {
        "coach_name": coach_name,
        "whatsapp_text": msg_text
    }

from app.outputs.coach_ics import generate_coach_ics

@app.get("/api/schedule/{schedule_id}/coach/{coach_name}/export-ics")
def export_individual_coach_ics(schedule_id: str, coach_name: str):
    """
    Exports a standard iCalendar (.ics) file for a coach to automatically add classes to Google/Apple/Outlook Calendar.
    """
    res_dict = get_schedule_db(schedule_id)
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
def get_output3_attention_report(schedule_id: str):
    ensure_active_data()
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Automatically synchronize accountability with all current master students
    recompute_schedule_outputs(
        res_dict,
        ACTIVE_DATA.get("students", []),
        ACTIVE_DATA.get("coaches", []),
        CURRENT_CONFIG
    )
    save_schedule_db(res_dict)

    res = ScheduleResult(**res_dict)
    attention_rows = format_attention_report(res)
    return {
        "schedule_id": schedule_id,
        "accountability_passed": res.accountability_passed,
        "total_students_considered": res.total_students_considered,
        "unscheduled_count": len(attention_rows),
        "attention_records": attention_rows,
        "unscheduled_records": attention_rows
    }

@app.get("/api/schedule/{schedule_id}/output5")
def get_output5_student_schedules(schedule_id: str):
    """
    Returns Output 5: Student-Wise Schedules (individual timetables per student).
    """
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")
    res = ScheduleResult(**res_dict)
    master_students = ACTIVE_DATA.get("students", [])
    student_schedules = format_student_schedules(res, master_students)
    return {
        "schedule_id": schedule_id,
        "total_students": len(student_schedules),
        "student_schedules": student_schedules
    }

@app.get("/api/schedule/{schedule_id}/student/{student_id}/export-ics")
def export_individual_student_ics(schedule_id: str, student_id: str):
    """
    Exports a standard iCalendar (.ics) file for a student to automatically add assigned classes to Google/Apple/Outlook Calendar.
    """
    res_dict = get_schedule_db(schedule_id)
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
    """
    ensure_active_data()
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")

    def mutate(temp_sched):
        target_cls = None
        for cls in temp_sched["scheduled_classes"]:
            if cls["class_id"] == req.class_id:
                target_cls = cls
                break

        if not target_cls:
            raise HTTPException(status_code=404, detail=f"Class ID {req.class_id} not found in schedule")

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

    updated_schedule = execute_transactional_mutation(
        res_dict, ACTIVE_DATA["students"], ACTIVE_DATA["coaches"], CURRENT_CONFIG, mutate
    )
    save_schedule_db(updated_schedule)
    return {"status": "success", "schedule": updated_schedule}

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
    Transactionally validates all hard constraints (daily uniqueness, quota cap, availability,
    level, and batch capacity) before committing. Updates Output 1, 2, and 3 atomically.
    """
    ensure_active_data()
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")

    def mutate(temp_sched):
        target_cls = next((c for c in temp_sched["scheduled_classes"] if c["class_id"] == req.class_id), None)
        if not target_cls:
            raise HTTPException(status_code=404, detail=f"Class ID {req.class_id} not found")

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
    Creates a brand new class assignment in Output 2 for an unscheduled student.
    Enforces server-side hard validation before committing.
    """
    import uuid
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
    return {"status": "success", "schedule": updated_schedule, "created_class_id": new_class_id}

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
    Transactionally validates that trainer qualification, trainer limits, student limits,
    availability, and batch capacity are strictly respected.
    """
    import uuid
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
    return {"status": "success", "schedule": updated_schedule, "created_class": created_class_container[0]}

@app.delete("/api/schedule/{schedule_id}/class/{class_id}")
def delete_class_from_schedule(schedule_id: str, class_id: str):
    """
    Deletes a scheduled class from the schedule.
    Updates Output 1 and Output 3 accountability automatically in one transaction.
    """
    ensure_active_data()
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")

    def mutate(temp_sched):
        target_cls = next((c for c in temp_sched["scheduled_classes"] if c["class_id"] == class_id), None)
        if not target_cls:
            raise HTTPException(status_code=404, detail=f"Class ID {class_id} not found")
        temp_sched["scheduled_classes"] = [c for c in temp_sched["scheduled_classes"] if c["class_id"] != class_id]

    updated_schedule = execute_transactional_mutation(
        res_dict, ACTIVE_DATA["students"], ACTIVE_DATA["coaches"], CURRENT_CONFIG, mutate
    )
    save_schedule_db(updated_schedule)
    return {"status": "success", "schedule": updated_schedule}

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

# ----------------------------------------------------
# Unified Production Deployment: Serve Built React App
# ----------------------------------------------------
from fastapi.staticfiles import StaticFiles

_dist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.exists(_dist_path):
    app.mount("/", StaticFiles(directory=_dist_path, html=True), name="static")


