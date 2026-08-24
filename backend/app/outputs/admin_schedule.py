from typing import List, Dict, Any
from app.models.schedule import ScheduleResult, ScheduledClass

def format_admin_schedule(result: ScheduleResult) -> List[Dict[str, Any]]:
    """
    Formats Output 2: Detailed Administrative Schedule (BRD Section 35).
    Includes full class details: Date, Day, Time, Coach, Level, Batch Type, Student List, Warnings.
    """
    admin_rows = []
    for cls in result.scheduled_classes:
        students_formatted = " · ".join(
            [f"{name} ({sid})" for sid, name in zip(cls.student_ids, cls.student_names)]
        )
        row = {
            "class_id": cls.class_id,
            "date": cls.date,
            "day": cls.day,
            "time_slot": cls.time_slot,
            "coach_name": cls.coach_name,
            "student_level": cls.student_level,
            "batch_type": cls.batch_type,
            "student_count": len(cls.student_ids),
            "students_formatted": students_formatted,
            "student_ids": cls.student_ids,
            "student_names": cls.student_names,
            "warnings": cls.warnings,
            "is_manual_override": cls.is_manual_override
        }
        admin_rows.append(row)
    return admin_rows
