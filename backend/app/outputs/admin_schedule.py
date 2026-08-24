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

def generate_coach_summary(result: ScheduleResult, master_coaches: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Generates a coach capacity, assigned hours, and workload summary for Output 2.
    Calculates assigned classes, teaching hours, unique students, capacity utilization %, and status.
    """
    if master_coaches is None:
        master_coaches = []

    coach_master_map = {c["coach_name"].strip().lower(): c for c in master_coaches}

    # Gather all coach names (both from master data and scheduled classes)
    scheduled_coach_names = set(cls.coach_name.strip() for cls in result.scheduled_classes)
    all_coach_names = sorted(list(set(c["coach_name"].strip() for c in master_coaches).union(scheduled_coach_names)))

    summaries = []
    for c_name in all_coach_names:
        c_lower = c_name.lower()
        master_info = coach_master_map.get(c_lower, {})

        coach_classes = [cls for cls in result.scheduled_classes if cls.coach_name.strip().lower() == c_lower]
        assigned_count = len(coach_classes)
        total_hours = assigned_count * 1.0  # 1 hour per class slot

        unique_students = len(set(sid for cls in coach_classes for sid in cls.student_ids))
        levels_taught = sorted(list(set(cls.student_level for cls in coach_classes)))
        days_active = sorted(list(set(cls.day for cls in coach_classes)))

        min_cap = master_info.get("monthly_capacity_min", 0)
        max_cap = master_info.get("monthly_capacity_max", 20)

        util_pct = round((assigned_count / max_cap * 100), 1) if max_cap > 0 else 0

        if assigned_count < min_cap:
            status = "Under-Utilized"
            status_color = "#f59e0b"
        elif assigned_count > max_cap:
            status = "Capacity Exceeded"
            status_color = "#ef4444"
        else:
            status = "Optimal"
            status_color = "#10b981"

        summaries.append({
            "coach_name": c_name,
            "assigned_classes": assigned_count,
            "total_hours": total_hours,
            "unique_students": unique_students,
            "levels_taught": levels_taught,
            "days_active": days_active,
            "monthly_capacity_min": min_cap,
            "monthly_capacity_max": max_cap,
            "utilization_pct": util_pct,
            "status": status,
            "status_color": status_color
        })

    return summaries
