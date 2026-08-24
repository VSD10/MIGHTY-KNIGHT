import re
from datetime import datetime, timedelta
from typing import List, Dict, Any

def parse_time_slot(date_str: str, time_slot: str):
    """
    Parses date (YYYY-MM-DD) and time slot string (e.g. '05:00 PM - 06:00 PM') into DTSTART and DTEND datetime objects.
    """
    try:
        parts = time_slot.split("-")
        start_str = parts[0].strip()
        end_str = parts[1].strip() if len(parts) > 1 else start_str
        
        start_dt = datetime.strptime(f"{date_str} {start_str}", "%Y-%m-%d %I:%M %p")
        end_dt = datetime.strptime(f"{date_str} {end_str}", "%Y-%m-%d %I:%M %p")
        return start_dt, end_dt
    except Exception:
        # Fallback to 5 PM if parsing fails
        dt = datetime.strptime(f"{date_str} 17:00", "%Y-%m-%d %H:%M")
        return dt, dt + timedelta(hours=1)

def generate_coach_ics(coach_name: str, scheduled_classes: List[Dict[str, Any]]) -> str:
    """
    Generates a standard iCalendar (.ics) format file string for a coach's scheduled classes.
    Allows one-click importing of all assigned classes into Google Calendar, Apple Calendar, or Outlook.
    """
    c_lower = coach_name.strip().lower()
    coach_classes = [
        cls for cls in scheduled_classes 
        if cls.get("coach_name", "").strip().lower() == c_lower
    ]

    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Mighty Knight Chess Academy//Scheduler Engine v1.0//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:Mighty Knight - Coach {coach_name} Schedule",
        "X-WR-TIMEZONE:Asia/Kolkata"
    ]

    now_str = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    for cls in coach_classes:
        date_str = cls.get("date", "2026-08-24")
        time_slot = cls.get("time_slot", "05:00 PM - 06:00 PM")
        class_id = cls.get("class_id", "CLS_UNKNOWN")
        level = cls.get("student_level", "Chess Class")
        batch_type = cls.get("batch_type", "G")
        
        stu_names = cls.get("student_names", [])
        stu_ids = cls.get("student_ids", [])
        formatted_students = ", ".join([f"{n} ({sid})" for n, sid in zip(stu_names, stu_ids)])

        start_dt, end_dt = parse_time_slot(date_str, time_slot)
        dtstart_str = start_dt.strftime("%Y%m%dT%H%M%S")
        dtend_str = end_dt.strftime("%Y%m%dT%H%M%S")

        ics_lines.extend([
            "BEGIN:VEVENT",
            f"UID:{class_id}_{dtstart_str}@mightyknight.com",
            f"DTSTAMP:{now_str}",
            f"DTSTART:{dtstart_str}",
            f"DTEND:{dtend_str}",
            f"SUMMARY:♟️ Chess Class: {level} (Batch {batch_type})",
            f"DESCRIPTION:Coach: {coach_name}\\nLevel: {level}\\nBatch Type: {batch_type}\\nStudents ({len(stu_ids)}): {formatted_students}",
            "LOCATION:Mighty Knight Chess Academy / Online Session",
            "STATUS:CONFIRMED",
            "END:VEVENT"
        ])

    ics_lines.append("END:VCALENDAR")
    return "\r\n".join(ics_lines)
