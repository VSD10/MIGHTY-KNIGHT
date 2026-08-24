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
from app.storage.database import (
    init_db, save_schedule_db, get_schedule_db, get_latest_schedule_db,
    save_master_data_db, load_master_data_db, has_master_data_db
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
    "parsing_errors": [],
    "filename": "",
    "upload_timestamp": ""
}

# Current configuration
CURRENT_CONFIG: SystemConfig = DEFAULT_CONFIG

def ensure_active_data():
    """
    Ensures master data (students & coaches) is loaded from SQLite.
    If SQLite contains previously saved master data, loads it directly.
    Only falls back to generating template data on a completely fresh database.
    """
    init_db()
    if has_master_data_db():
        data = load_master_data_db()
        ACTIVE_DATA["students"] = data["students"]
        ACTIVE_DATA["coaches"] = data["coaches"]
        ACTIVE_DATA["parsing_errors"] = data["parsing_errors"]
        ACTIVE_DATA["filename"] = data.get("last_filename", "Master Data")
        ACTIVE_DATA["upload_timestamp"] = data.get("last_upload_timestamp", "")
    else:
        sample_path = "sample_data/mighty_knight_template.xlsx"
        if not os.path.exists(sample_path):
            from sample_generator import generate_sample_excel
            generate_sample_excel(sample_path)
        with open(sample_path, "rb") as f:
            students, coaches, errors = parse_excel_file(f.read(), CURRENT_CONFIG)
            s_dicts = [s.model_dump() for s in students]
            c_dicts = [c.model_dump() for c in coaches]
            ACTIVE_DATA["students"] = s_dicts
            ACTIVE_DATA["coaches"] = c_dicts
            ACTIVE_DATA["parsing_errors"] = errors
            ACTIVE_DATA["filename"] = "mighty_knight_template.xlsx"
            now_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")
            ACTIVE_DATA["upload_timestamp"] = now_str
            save_master_data_db(s_dicts, c_dicts, errors, filename="mighty_knight_template.xlsx", upload_timestamp=now_str)

@app.on_event("startup")
def startup_event():
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

    return {
        "filename": file.filename,
        "upload_timestamp": now_str,
        "total_students_parsed": len(students),
        "total_coaches_parsed": len(coaches),
        "parsing_errors_count": len(errors),
        "parsing_errors": errors
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

@app.get("/api/schedule/latest/active")
def get_active_or_latest_schedule():
    """
    Retrieves the most recent active schedule saved in SQLite for 0-loss state recovery on app launch/refresh.
    """
    latest = get_latest_schedule_db()
    if not latest:
        ensure_active_data()
        s_date = date.today()
        e_date = s_date + timedelta(days=6)
        students = [StudentModel(**s) for s in ACTIVE_DATA["students"]]
        coaches = [CoachModel(**c) for c in ACTIVE_DATA["coaches"]]
        result = run_scheduler(students, coaches, s_date, e_date, CURRENT_CONFIG)
        latest = result.model_dump()
        save_schedule_db(latest)

    return {
        "schedule_id": latest["schedule_id"],
        "status": latest.get("status", "Draft"),
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
    student_level: Optional[str] = None
    batch_type: Optional[str] = None
    student_ids: Optional[List[str]] = None

@app.post("/api/schedule/{schedule_id}/validate-override")
def validate_manual_override(schedule_id: str, req: ManualOverrideRequest):
    """
    Validates manual administrative edit (Section 37) and checks for rule violations before saving.
    Checks coach overlap, capacity breach, coach capability, Sunday restrictions.
    """
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")

    violations = []
    
    # Check 1: Coach Overlap at same time
    for cls in res_dict["scheduled_classes"]:
        if cls["class_id"] != req.class_id and cls["date"] == req.date and cls["time_slot"] == req.time_slot:
            if cls["coach_name"].strip().lower() == req.coach_name.strip().lower():
                violations.append(f"COACH OVERLAP WARNING: Coach '{req.coach_name}' already has a class assigned at {req.time_slot} on {req.date}.")

    # Check 2: Coach capability check
    coaches = [CoachModel(**c) for c in ACTIVE_DATA["coaches"]]
    target_coach = next((c for c in coaches if c.coach_name.strip().lower() == req.coach_name.strip().lower()), None)
    if not target_coach:
        violations.append(f"UNKNOWN COACH: '{req.coach_name}' is not in master coach list.")
    elif req.student_level:
        if not target_coach.can_handle_level(req.student_level):
            violations.append(f"COACH CAPABILITY WARNING: Coach '{req.coach_name}' is not listed as qualified to teach '{req.student_level}'.")

    # Check 3: Batch capacity limits
    if req.batch_type and req.student_ids:
        cnt = len(req.student_ids)
        if req.batch_type == "G" and cnt > 10:
            violations.append(f"BATCH CAPACITY BREACH: Group Batch has {cnt} students (max 10 allowed).")
        elif req.batch_type == "L" and cnt > 3:
            violations.append(f"BATCH CAPACITY BREACH: Limited Batch has {cnt} students (max 3 allowed).")
        elif req.batch_type == "I" and cnt > 1:
            violations.append(f"BATCH CAPACITY BREACH: Individual Batch has {cnt} students (max 1 allowed).")

    # Check 4: Sunday 3 PM limit
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

@app.post("/api/schedule/{schedule_id}/manual-edit")
def apply_manual_edit(schedule_id: str, req: ManualOverrideRequest):
    """
    Applies and persists manual administrative edit (Section 37) to the schedule.
    Updates Output 1 and Output 2 automatically.
    """
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")

    target_cls = None
    for cls in res_dict["scheduled_classes"]:
        if cls["class_id"] == req.class_id:
            target_cls = cls
            break

    if not target_cls:
        raise HTTPException(status_code=404, detail=f"Class ID {req.class_id} not found in schedule")

    # Update class fields
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
        target_cls["students_formatted"] = " · ".join([f"{n} ({sid})" for sid, n in zip(req.student_ids, names)])

    target_cls["is_manual_override"] = True

    # Re-calculate Coach Communication Schedule (Output 1)
    coach_schedule_map = {}
    for s_cls in res_dict["scheduled_classes"]:
        key = f"{s_cls['date']}||{s_cls['day']}||{s_cls['time_slot']}"
        if key not in coach_schedule_map:
            coach_schedule_map[key] = []
        if s_cls["coach_name"] not in coach_schedule_map[key]:
            coach_schedule_map[key].append(s_cls["coach_name"])

    updated_coach_slots = []
    for k, coaches_list in sorted(coach_schedule_map.items()):
        dt, dy, ts = k.split("||")
        updated_coach_slots.append({
            "date": dt,
            "day": dy,
            "time_slot": ts,
            "coaches": coaches_list
        })

    res_dict["coach_schedule"] = updated_coach_slots

    save_schedule_db(res_dict)
    return {"status": "success", "schedule": res_dict}

class AssignStudentRequest(BaseModel):
    student_id: str
    class_id: str

@app.post("/api/schedule/{schedule_id}/assign-student")
def assign_unscheduled_student_to_class(schedule_id: str, req: AssignStudentRequest):
    """
    Drag-and-Drop Unscheduled Resolver: assigns an unscheduled student from Output 3 into a class in Output 2.
    Updates Output 1, Output 2, and Output 3 atomically.
    """
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")

    target_cls = next((c for c in res_dict["scheduled_classes"] if c["class_id"] == req.class_id), None)
    if not target_cls:
        raise HTTPException(status_code=404, detail=f"Class ID {req.class_id} not found")

    if req.student_id not in target_cls["student_ids"]:
        target_cls["student_ids"].append(req.student_id)
        stu_map = {s["student_id"]: s["student_name"] for s in ACTIVE_DATA.get("students", [])}
        s_name = stu_map.get(req.student_id, req.student_id)
        target_cls["student_names"].append(s_name)
        target_cls["students_formatted"] = " · ".join([f"{n} ({sid})" for sid, n in zip(target_cls["student_ids"], target_cls["student_names"])])
        target_cls["is_manual_override"] = True

    # Remove from unscheduled_records if present
    res_dict["unscheduled_records"] = [
        r for r in res_dict.get("unscheduled_records", []) if r["student_id"] != req.student_id
    ]
    res_dict["unscheduled_students_count"] = len(res_dict["unscheduled_records"])
    res_dict["successfully_scheduled_students"] = max(0, res_dict["total_students_considered"] - res_dict["unscheduled_students_count"])
    res_dict["accountability_passed"] = (res_dict["total_students_considered"] == res_dict["successfully_scheduled_students"] + res_dict["unscheduled_students_count"])

    # Re-calculate Coach Communication Schedule (Output 1)
    coach_schedule_map = {}
    for s_cls in res_dict["scheduled_classes"]:
        key = f"{s_cls['date']}||{s_cls['day']}||{s_cls['time_slot']}"
        if key not in coach_schedule_map:
            coach_schedule_map[key] = []
        if s_cls["coach_name"] not in coach_schedule_map[key]:
            coach_schedule_map[key].append(s_cls["coach_name"])

    updated_coach_slots = []
    for k, coaches_list in sorted(coach_schedule_map.items()):
        dt, dy, ts = k.split("||")
        updated_coach_slots.append({
            "date": dt,
            "day": dy,
            "time_slot": ts,
            "coaches": coaches_list
        })

    res_dict["coach_schedule"] = updated_coach_slots

    save_schedule_db(res_dict)
    return {"status": "success", "schedule": res_dict}

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
    Creates a brand new class assignment in Output 2 for an unscheduled student from Output 3.
    Instantly updates Output 1, Output 2, Output 3, and Output 4 (Coach Workload) atomically.
    """
    import uuid
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")

    stu_map = {s["student_id"]: s["student_name"] for s in ACTIVE_DATA.get("students", [])}
    s_name = stu_map.get(req.student_id, req.student_id)

    try:
        d_obj = datetime.strptime(req.date, "%Y-%m-%d")
        day_name = d_obj.strftime("%A")
    except Exception:
        day_name = "Monday"

    new_class_id = f"CLS_{uuid.uuid4().hex[:6].upper()}"
    new_class = {
        "class_id": new_class_id,
        "date": req.date,
        "day": day_name,
        "time_slot": req.time_slot,
        "coach_name": req.coach_name.strip(),
        "student_level": req.student_level or "Basic 1",
        "batch_type": req.batch_type or "G",
        "student_ids": [req.student_id],
        "student_names": [s_name],
        "students_formatted": f"{s_name} ({req.student_id})",
        "warnings": ["Manual emergency class assignment created by administrator"],
        "is_manual_override": True
    }

    res_dict["scheduled_classes"].append(new_class)

    # Remove from unscheduled_records if present
    res_dict["unscheduled_records"] = [
        r for r in res_dict.get("unscheduled_records", []) if r["student_id"] != req.student_id
    ]
    res_dict["unscheduled_students_count"] = len(res_dict["unscheduled_records"])
    res_dict["successfully_scheduled_students"] = max(0, res_dict["total_students_considered"] - res_dict["unscheduled_students_count"])
    res_dict["accountability_passed"] = (res_dict["total_students_considered"] == res_dict["successfully_scheduled_students"] + res_dict["unscheduled_students_count"])

    # Re-calculate Coach Communication Schedule (Output 1)
    coach_schedule_map = {}
    for s_cls in res_dict["scheduled_classes"]:
        key = f"{s_cls['date']}||{s_cls['day']}||{s_cls['time_slot']}"
        if key not in coach_schedule_map:
            coach_schedule_map[key] = []
        if s_cls["coach_name"] not in coach_schedule_map[key]:
            coach_schedule_map[key].append(s_cls["coach_name"])

    updated_coach_slots = []
    for k, coaches_list in sorted(coach_schedule_map.items()):
        dt, dy, ts = k.split("||")
        updated_coach_slots.append({
            "date": dt,
            "day": dy,
            "time_slot": ts,
            "coaches": coaches_list
        })

    res_dict["coach_schedule"] = updated_coach_slots

    save_schedule_db(res_dict)
    return {"status": "success", "schedule": res_dict, "created_class_id": new_class_id}

@app.delete("/api/schedule/{schedule_id}/class/{class_id}")
def delete_class_from_schedule(schedule_id: str, class_id: str):
    """
    Deletes a scheduled class from the schedule.
    Updates Output 1 and Output 2 automatically.
    """
    res_dict = get_schedule_db(schedule_id)
    if not res_dict:
        raise HTTPException(status_code=404, detail="Schedule not found")

    target_cls = next((c for c in res_dict["scheduled_classes"] if c["class_id"] == class_id), None)
    if not target_cls:
        raise HTTPException(status_code=404, detail=f"Class ID {class_id} not found")

    res_dict["scheduled_classes"] = [c for c in res_dict["scheduled_classes"] if c["class_id"] != class_id]

    # Re-calculate Coach Communication Schedule (Output 1)
    coach_schedule_map = {}
    for s_cls in res_dict["scheduled_classes"]:
        key = f"{s_cls['date']}||{s_cls['day']}||{s_cls['time_slot']}"
        if key not in coach_schedule_map:
            coach_schedule_map[key] = []
        if s_cls["coach_name"] not in coach_schedule_map[key]:
            coach_schedule_map[key].append(s_cls["coach_name"])

    updated_coach_slots = []
    for k, coaches_list in sorted(coach_schedule_map.items()):
        dt, dy, ts = k.split("||")
        updated_coach_slots.append({
            "date": dt,
            "day": dy,
            "time_slot": ts,
            "coaches": coaches_list
        })

    res_dict["coach_schedule"] = updated_coach_slots

    save_schedule_db(res_dict)
    return {"status": "success", "schedule": res_dict}
