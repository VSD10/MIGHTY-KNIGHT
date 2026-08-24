from typing import List, Dict, Any
from app.models.schedule import ScheduleResult, UnscheduledRecord
from app.utils.time_utils import parse_time_slot_sort_key

def format_attention_report(result: ScheduleResult) -> List[Dict[str, Any]]:
    """
    Formats Output 3: Unscheduled / Administrator Attention Report (BRD Section 29, 31).
    Generates smart assignment recommendations & emergency overtime options for each unscheduled student.
    Includes coach's daily schedule load and emergency capacity extension flags, sorted chronologically.
    """
    report_rows = []
    
    # Capacity maps per batch type
    batch_max_capacities = {"G": 10, "L": 3, "I": 1}

    # Pre-calculate daily class counts per coach
    coach_daily_counts = {}
    for cls in result.scheduled_classes:
        key = (cls.coach_name.strip().lower(), cls.date)
        coach_daily_counts[key] = coach_daily_counts.get(key, 0) + 1

    for rec in result.unscheduled_records:
        recommendations = []

        # Find candidate classes in result.scheduled_classes
        for cls in result.scheduled_classes:
            # Check level match
            if cls.student_level.strip().lower() != rec.student_level.strip().lower():
                continue
            
            # Check batch type match
            b_type = cls.batch_type.strip().upper()
            if b_type != rec.batch_type.strip().upper():
                continue

            # Check student is not already in this class
            if rec.student_id in cls.student_ids:
                continue

            max_cap = batch_max_capacities.get(b_type, 10)
            current_cnt = len(cls.student_ids)
            c_day_count = coach_daily_counts.get((cls.coach_name.strip().lower(), cls.date), 0)

            # Check day preference match score
            day_matched = cls.day.lower() in rec.preferred_days.lower() or rec.preferred_days.lower() in ["all", "any", "all days"]
            
            is_overtime = current_cnt >= max_cap

            if not is_overtime:
                reason = f"Matches level ({cls.student_level}) & has {max_cap - current_cnt} open seats"
                if day_matched:
                    reason = f"★ Preferred Day ({cls.day}) match & {max_cap - current_cnt} open seats"
            else:
                reason = f"⚠️ Emergency Overtime (+1 beyond cap). Coach has {c_day_count} classes on {cls.day}"

            recommendations.append({
                "class_id": cls.class_id,
                "coach_name": cls.coach_name,
                "date": cls.date,
                "day": cls.day,
                "time_slot": cls.time_slot,
                "student_level": cls.student_level,
                "batch_type": cls.batch_type,
                "current_seats": current_cnt,
                "max_seats": max_cap,
                "coach_day_classes": c_day_count,
                "day_matched": day_matched,
                "is_overtime": is_overtime,
                "reason": reason
            })

        # Sort recommendations: non-overtime first, then day_matched, then chronologically by Date -> Time Slot
        recommendations.sort(key=lambda x: (x["is_overtime"], not x["day_matched"], parse_time_slot_sort_key(x["date"], x["time_slot"])))

        row = {
            "student_id": rec.student_id,
            "student_name": rec.student_name,
            "student_level": rec.student_level,
            "batch_type": rec.batch_type,
            "preferred_days": rec.preferred_days,
            "preferred_time": rec.preferred_time,
            "required_classes": rec.required_classes,
            "scheduled_classes": rec.scheduled_classes,
            "remaining_classes": rec.remaining_classes,
            "failure_reason": rec.failure_reason,
            "details": rec.details,
            "recommendations": recommendations[:5] # Top 5 recommendations
        }
        report_rows.append(row)

    # Sort unscheduled records by student name
    report_rows.sort(key=lambda x: x["student_name"])
    return report_rows
