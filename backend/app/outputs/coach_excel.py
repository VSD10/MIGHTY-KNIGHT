import io
import pandas as pd
from typing import Dict, Any, List

def generate_coach_individual_excel(coach_name: str, scheduled_classes: List[Dict[str, Any]]) -> bytes:
    """
    Generates a dedicated Excel file (.xlsx) for a specific coach's timetable and student rosters.
    """
    c_lower = coach_name.strip().lower()
    coach_classes = [
        cls for cls in scheduled_classes 
        if cls.get("coach_name", "").strip().lower() == c_lower
    ]
    
    # Sort by date and time_slot
    coach_classes.sort(key=lambda x: (x.get("date", ""), x.get("time_slot", "")))

    timetable_rows = []
    roster_rows = []

    for cls in coach_classes:
        stu_names = cls.get("student_names", [])
        stu_ids = cls.get("student_ids", [])
        formatted_students = " · ".join([f"{n} ({sid})" for n, sid in zip(stu_names, stu_ids)])
        
        timetable_rows.append({
            "Class ID": cls.get("class_id"),
            "Date": cls.get("date"),
            "Day": cls.get("day"),
            "Time Slot": cls.get("time_slot"),
            "Student Level": cls.get("student_level"),
            "Batch Type": cls.get("batch_type"),
            "Total Students": len(stu_ids),
            "Assigned Students": formatted_students
        })

        for sid, name in zip(stu_ids, stu_names):
            roster_rows.append({
                "Student ID": sid,
                "Student Name": name,
                "Class Date": cls.get("date"),
                "Day": cls.get("day"),
                "Time Slot": cls.get("time_slot"),
                "Level": cls.get("student_level"),
                "Batch Type": cls.get("batch_type")
            })

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_timetable = pd.DataFrame(timetable_rows if timetable_rows else [{
            "Class ID": "-", "Date": "-", "Day": "-", "Time Slot": "-", "Student Level": "-", "Batch Type": "-", "Total Students": 0, "Assigned Students": "No classes assigned"
        }])
        df_timetable.to_excel(writer, sheet_name="Timetable Schedule", index=False)

        df_roster = pd.DataFrame(roster_rows if roster_rows else [{
            "Student ID": "-", "Student Name": "-", "Class Date": "-", "Day": "-", "Time Slot": "-", "Level": "-", "Batch Type": "-"
        }])
        df_roster.to_excel(writer, sheet_name="Student Rosters", index=False)

    return output.getvalue()

def generate_coach_whatsapp_msg(coach_name: str, scheduled_classes: List[Dict[str, Any]]) -> str:
    """
    Generates a personalized WhatsApp schedule broadcast text for an individual coach.
    """
    c_lower = coach_name.strip().lower()
    coach_classes = [
        cls for cls in scheduled_classes 
        if cls.get("coach_name", "").strip().lower() == c_lower
    ]
    coach_classes.sort(key=lambda x: (x.get("date", ""), x.get("time_slot", "")))

    lines = [
        f"🏆 *MIGHTY KNIGHT CHESS ACADEMY*",
        f"📋 *Weekly Schedule for Coach {coach_name.upper()}*",
        f"----------------------------------------",
        f"Total Classes Assigned: {len(coach_classes)} | Total Hours: {len(coach_classes)} hrs",
        ""
    ]

    if not coach_classes:
        lines.append("No classes scheduled for this week.")
    else:
        for idx, cls in enumerate(coach_classes, 1):
            stu_names = cls.get("student_names", [])
            stu_ids = cls.get("student_ids", [])
            formatted = ", ".join([f"{n} ({sid})" for n, sid in zip(stu_names, stu_ids)])
            lines.append(f"📌 *Class {idx}: {cls.get('day')} ({cls.get('date')})*")
            lines.append(f"⏰ *Time:* {cls.get('time_slot')}")
            lines.append(f"🎓 *Level:* {cls.get('student_level')} (Batch {cls.get('batch_type')})")
            lines.append(f"👥 *Students ({len(stu_ids)}):* {formatted}")
            lines.append("")

    lines.append("----------------------------------------")
    lines.append("Please confirm your schedule with management. Have a great teaching week! ♟️")
    return "\n".join(lines)
