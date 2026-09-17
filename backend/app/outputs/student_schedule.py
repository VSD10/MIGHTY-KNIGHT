from typing import List, Dict, Any
from datetime import datetime
from app.models.schedule import ScheduleResult
from app.utils.time_utils import parse_time_slot_sort_key
from app.outputs.coach_ics import parse_time_slot

def format_date_ddmmyyyy(date_str: str) -> str:
    """Formats a date string YYYY-MM-DD into DD/MM/YYYY format."""
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return date_str

def format_display_time(time_slot: str) -> str:
    """
    Formats '04:00 PM - 05:00 PM' into '4:00 PM' or clean display time string.
    """
    if not time_slot:
        return ""
    parts = time_slot.split('-')
    if len(parts) >= 1:
        start_time = parts[0].strip()
        # Remove leading zero in hour if present e.g. 04:00 PM -> 4:00 PM
        if start_time.startswith('0') and len(start_time) > 1 and start_time[1].isdigit():
            start_time = start_time[1:]
        return start_time
    return time_slot

def format_student_schedules(result: ScheduleResult, master_students: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Generates Output 5: Student-Wise Schedule Output.
    Groups assigned classes by student, sorted chronologically.
    Returns a list of student schedule objects with sessions formatted as:
    Date (DD/MM/YYYY), Day, Time, Coach, Session.
    """
    if master_students is None:
        master_students = []

    # Map student_id -> student_info
    student_meta: Dict[str, Dict[str, Any]] = {}
    for s in master_students:
        sid = s.get("student_id", "").strip()
        if sid:
            student_meta[sid] = {
                "student_id": sid,
                "student_name": s.get("student_name", "").strip(),
                "student_level": s.get("student_level", "Basic 1"),
                "batch_type": s.get("batch_type", "G")
            }

    # Group classes by student_id
    student_classes_map: Dict[str, List[Any]] = {}
    student_names_map: Dict[str, str] = {}

    for cls in result.scheduled_classes:
        s_ids = cls.student_ids or []
        s_names = cls.student_names or []

        for idx, sid in enumerate(s_ids):
            sid = sid.strip()
            if not sid:
                continue
            
            sname = s_names[idx] if idx < len(s_names) else sid
            student_names_map[sid] = sname
            
            if sid not in student_classes_map:
                student_classes_map[sid] = []
            
            student_classes_map[sid].append(cls)

            if sid not in student_meta:
                student_meta[sid] = {
                    "student_id": sid,
                    "student_name": sname,
                    "student_level": cls.student_level or "Basic 1",
                    "batch_type": cls.batch_type or "G"
                }

    # Gather all unique student IDs from master_students and scheduled classes
    all_student_ids = sorted(list(set(list(student_meta.keys()) + list(student_classes_map.keys()))))

    student_schedules = []

    for sid in all_student_ids:
        meta = student_meta.get(sid, {
            "student_id": sid,
            "student_name": student_names_map.get(sid, sid),
            "student_level": "Basic 1",
            "batch_type": "G"
        })

        classes = student_classes_map.get(sid, [])
        
        # Sort classes chronologically by Date -> Time
        sorted_classes = sorted(
            classes,
            key=lambda c: parse_time_slot_sort_key(c.date, c.time_slot)
        )

        formatted_sessions = []
        for cls in sorted_classes:
            formatted_sessions.append({
                "class_id": cls.class_id,
                "date": format_date_ddmmyyyy(cls.date),
                "raw_date": cls.date,
                "day": cls.day,
                "time": format_display_time(cls.time_slot),
                "full_time_slot": cls.time_slot,
                "coach": cls.coach_name,
                "session": "Chess",
                "student_level": cls.student_level,
                "batch_type": cls.batch_type
            })

        student_schedules.append({
            "student_id": meta["student_id"],
            "student_name": meta["student_name"],
            "student_level": meta["student_level"],
            "batch_type": meta["batch_type"],
            "total_sessions": len(formatted_sessions),
            "sessions": formatted_sessions
        })

    # Sort student list alphabetically by student name
    student_schedules.sort(key=lambda s: s["student_name"].lower())

    return student_schedules

def generate_student_ics(student_id_or_name: str, scheduled_classes: List[Dict[str, Any]]) -> str:
    """
    Generates a standard iCalendar (.ics) format file string for a student's scheduled classes.
    Allows one-click importing of all assigned classes into Google Calendar, Apple Calendar, or Outlook.
    """
    target = student_id_or_name.strip().lower()
    
    student_classes = []
    student_display_name = student_id_or_name

    for cls in scheduled_classes:
        s_ids = [str(s).strip().lower() for s in cls.get("student_ids", [])]
        s_names = [str(n).strip().lower() for n in cls.get("student_names", [])]
        
        if target in s_ids or target in s_names:
            student_classes.append(cls)
            if target in s_ids:
                idx = s_ids.index(target)
                if idx < len(cls.get("student_names", [])):
                    student_display_name = cls["student_names"][idx]
            elif target in s_names:
                idx = s_names.index(target)
                student_display_name = cls["student_names"][idx]

    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Mighty Knight Chess Academy//Student Engine v1.0//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:Mighty Knight - Student {student_display_name} Schedule",
        "X-WR-TIMEZONE:Asia/Kolkata"
    ]

    now_str = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    for cls in student_classes:
        date_str = cls.get("date", "2026-08-24")
        time_slot = cls.get("time_slot", "05:00 PM - 06:00 PM")
        class_id = cls.get("class_id", "CLS_UNKNOWN")
        level = cls.get("student_level", "Basic 1")
        batch_type = cls.get("batch_type", "G")
        coach_name = cls.get("coach_name", "Assigned Coach")

        start_dt, end_dt = parse_time_slot(date_str, time_slot)
        dtstart_str = start_dt.strftime("%Y%m%dT%H%M%S")
        dtend_str = end_dt.strftime("%Y%m%dT%H%M%S")

        ics_lines.extend([
            "BEGIN:VEVENT",
            f"UID:STU_{class_id}_{dtstart_str}@mightyknight.com",
            f"DTSTAMP:{now_str}",
            f"DTSTART:{dtstart_str}",
            f"DTEND:{dtend_str}",
            f"SUMMARY:♟️ Chess Class with Coach {coach_name} ({level})",
            f"DESCRIPTION:Student: {student_display_name}\\nCoach: {coach_name}\\nLevel: {level}\\nBatch Type: {batch_type}",
            "LOCATION:Mighty Knight Chess Academy",
            "STATUS:CONFIRMED",
            "END:VEVENT"
        ])

    ics_lines.append("END:VCALENDAR")
    return "\r\n".join(ics_lines)

