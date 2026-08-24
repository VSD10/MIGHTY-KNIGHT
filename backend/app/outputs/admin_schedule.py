from typing import List, Dict, Any
from app.models.schedule import ScheduleResult, ScheduledClass
from app.utils.time_utils import parse_time_slot_sort_key

def format_admin_schedule(result: ScheduleResult) -> List[Dict[str, Any]]:
    """
    Formats Output 2: Detailed Administrative Schedule (BRD Section 35).
    Includes full class details sorted strictly chronologically by Date and Time Slot.
    """
    admin_rows = []

    # Sort classes chronologically by Date -> Time Slot -> Coach Name
    sorted_classes = sorted(
        result.scheduled_classes,
        key=lambda c: (parse_time_slot_sort_key(c.date, c.time_slot), c.coach_name)
    )

    for cls in sorted_classes:
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
    Generates a coach capacity, assigned hours, and workload summary for Output 4 / Output 2.
    Calculates assigned classes, teaching hours, unique students, capacity utilization %, and emergency overtime status.
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
        total_student_reach = sum(len(cls.student_ids) for cls in coach_classes)
        levels_taught = sorted(list(set(cls.student_level for cls in coach_classes)))
        days_active = sorted(list(set(cls.day for cls in coach_classes)))

        # Determine weekly capacity target
        mon_m = master_info.get("mon_max", 4)
        tue_m = master_info.get("tue_max", 4)
        wed_m = master_info.get("wed_max", 4)
        thu_m = master_info.get("thu_max", 4)
        fri_m = master_info.get("fri_max", 4)
        sat_m = master_info.get("sat_max", 5)
        sun_m = master_info.get("sun_max", 2)
        weekly_max = mon_m + tue_m + wed_m + thu_m + fri_m + sat_m + sun_m

        m_max = master_info.get("monthly_capacity_max", 0)
        if 0 < m_max < 50:
            target_cap = m_max
        else:
            target_cap = weekly_max if weekly_max > 0 else 20

        min_cap = master_info.get("monthly_capacity_min", 2)

        util_pct = round((assigned_count / target_cap * 100), 1) if target_cap > 0 else 0

        # Check for daily max overcapacity
        day_class_counts = {}
        for cls in coach_classes:
            day_class_counts[cls.day] = day_class_counts.get(cls.day, 0) + 1

        day_overtime = False
        day_map_limits = {
            "Monday": mon_m, "Tuesday": tue_m, "Wednesday": wed_m,
            "Thursday": thu_m, "Friday": fri_m, "Saturday": sat_m, "Sunday": sun_m
        }
        for dy, cnt in day_class_counts.items():
            if cnt > day_map_limits.get(dy, 4):
                day_overtime = True
                break

        if assigned_count > target_cap or day_overtime:
            status = "Capacity Exceeded (Overtime)"
            status_color = "#ef4444"
        elif assigned_count < min_cap:
            status = "Under-Utilized"
            status_color = "#f59e0b"
        else:
            status = "Optimal"
            status_color = "#10b981"

        summaries.append({
            "coach_name": c_name,
            "assigned_classes": assigned_count,
            "total_hours": total_hours,
            "unique_students": unique_students,
            "total_student_reach": total_student_reach,
            "levels_taught": levels_taught,
            "days_active": days_active,
            "monthly_capacity_min": min_cap,
            "monthly_capacity_max": target_cap,
            "utilization_pct": util_pct,
            "status": status,
            "status_color": status_color
        })

    return summaries
