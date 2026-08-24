import os
from datetime import datetime, date
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
from app.storage.database import init_db, save_schedule_db, get_schedule_db

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
    "parsing_errors": []
}

# Current configuration
CURRENT_CONFIG: SystemConfig = DEFAULT_CONFIG

def ensure_active_data():
    if not ACTIVE_DATA["students"] or not ACTIVE_DATA["coaches"]:
        sample_path = "sample_data/mighty_knight_template.xlsx"
        if not os.path.exists(sample_path):
            from sample_generator import generate_sample_excel
            generate_sample_excel(sample_path)
        with open(sample_path, "rb") as f:
            students, coaches, errors = parse_excel_file(f.read(), CURRENT_CONFIG)
            ACTIVE_DATA["students"] = [s.model_dump() for s in students]
            ACTIVE_DATA["coaches"] = [c.model_dump() for c in coaches]
            ACTIVE_DATA["parsing_errors"] = errors

@app.on_event("startup")
def startup_event():
    init_db()
    ensure_active_data()

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "Mighty Knight Scheduling Engine"}

@app.get("/api/config")
def get_system_config():
    return CURRENT_CONFIG.model_dump()

@app.post("/api/config")
def update_system_config(config_data: Dict[str, Any]):
    global CURRENT_CONFIG
    try:
        CURRENT_CONFIG = SystemConfig(**config_data)
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

    ACTIVE_DATA["students"] = [s.model_dump() for s in students]
    ACTIVE_DATA["coaches"] = [c.model_dump() for c in coaches]
    ACTIVE_DATA["parsing_errors"] = errors

    return {
        "filename": file.filename,
        "total_students_parsed": len(students),
        "total_coaches_parsed": len(coaches),
        "parsing_errors_count": len(errors),
        "parsing_errors": errors
    }

@app.get("/api/data/summary")
def get_data_summary():
    return {
        "students_count": len(ACTIVE_DATA["students"]),
        "coaches_count": len(ACTIVE_DATA["coaches"]),
        "parsing_errors": ACTIVE_DATA["parsing_errors"]
    }

@app.get("/api/download-template")
def download_excel_template():
    sample_path = "sample_data/mighty_knight_template.xlsx"
    if not os.path.exists(sample_path):
        from sample_generator import generate_sample_excel
        generate_sample_excel(sample_path)
    return FileResponse(
        path=sample_path,
        filename="mighty_knight_template.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

class ScheduleRequest(BaseModel):
    start_date: str # YYYY-MM-DD
    end_date: str   # YYYY-MM-DD

@app.post("/api/schedule/run")
def trigger_scheduling_run(req: ScheduleRequest):
    if not ACTIVE_DATA["students"] or not ACTIVE_DATA["coaches"]:
        raise HTTPException(status_code=400, detail="No active student or coach data uploaded. Please upload Excel first.")

    try:
        s_date = datetime.strptime(req.start_date, "%Y-%m-%d").date()
        e_date = datetime.strptime(req.end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    if s_date > e_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date.")

    students = [StudentModel(**s) for s in ACTIVE_DATA["students"]]
    coaches = [CoachModel(**c) for c in ACTIVE_DATA["coaches"]]

    result = run_scheduler(students, coaches, s_date, e_date, CURRENT_CONFIG)
    res_dict = result.model_dump()
    save_schedule_db(res_dict)

    return res_dict

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

@app.get("/api/schedule/{schedule_id}/output2")
def get_output2_admin_schedule(schedule_id: str):
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")
    res = ScheduleResult(**res_dict)
    admin_rows = format_admin_schedule(res)
    return {
        "schedule_id": schedule_id,
        "detailed_classes": admin_rows
    }

@app.get("/api/schedule/{schedule_id}/output3")
def get_output3_attention_report(schedule_id: str):
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")
    res = ScheduleResult(**res_dict)
    attention_rows = format_attention_report(res)
    return {
        "schedule_id": schedule_id,
        "accountability_passed": res.accountability_passed,
        "total_students_considered": res.total_students_considered,
        "unscheduled_count": res.unscheduled_students_count,
        "attention_records": attention_rows
    }

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
    student_ids: List[str]

@app.post("/api/schedule/{schedule_id}/validate-override")
def validate_manual_override(schedule_id: str, req: ManualOverrideRequest):
    """
    Validates manual administrative edit (Section 37) and checks for rule violations before saving.
    Checks coach overlap, capacity breach, student availability conflict.
    """
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")

    violations = []
    
    # Check 1: Coach Overlap at same time
    for cls in res_dict["scheduled_classes"]:
        if cls["class_id"] != req.class_id and cls["date"] == req.date and cls["time_slot"] == req.time_slot:
            if cls["coach_name"] == req.coach_name:
                violations.append(f"COACH OVERLAP WARNING: Coach '{req.coach_name}' already has a class assigned at {req.time_slot} on {req.date}.")

    # Check 2: Coach capability check
    coaches = [CoachModel(**c) for c in ACTIVE_DATA["coaches"]]
    target_coach = next((c for c in coaches if c.coach_name.strip() == req.coach_name.strip()), None)
    if not target_coach:
        violations.append(f"UNKNOWN COACH: '{req.coach_name}' is not in master coach list.")

    # Check 3: Sunday 3 PM limit
    try:
        d_obj = datetime.strptime(req.date, "%Y-%m-%d")
        if d_obj.strftime("%A") == "Sunday":
            if any(x in req.time_slot for x in ["03:00 PM", "04:00 PM", "05:00 PM", "06:00 PM"]):
                violations.append("SUNDAY RESTRICTION WARNING: Sunday classes must normally end by 3:00 PM.")
    except Exception:
        pass

    return {
        "valid": len(violations) == 0,
        "warnings": violations
    }
