from typing import List, Dict, Any
from app.models.schedule import ScheduleResult, UnscheduledRecord

def format_attention_report(result: ScheduleResult) -> List[Dict[str, Any]]:
    """
    Formats Output 3: Unscheduled / Administrator Attention Report (BRD Section 29, 31).
    Generates smart assignment recommendations for each unscheduled student.
    """
    report_rows = []
    
    # Capacity maps per batch type
    batch_max_capacities = {"G": 10, "L": 3, "I": 1}

    for rec in result.unscheduled_records:
        recommendations = []

        # Find matching candidate classes in result.scheduled_classes
        for cls in result.scheduled_classes:
            # Check level match
            if cls.student_level.strip().lower() != rec.student_level.strip().lower():
                continue
            
            # Check batch type match
            b_type = cls.batch_type.strip().upper()
            if b_type != rec.batch_type.strip().upper():
                continue

            # Check capacity
            max_cap = batch_max_capacities.get(b_type, 10)
            current_cnt = len(cls.student_ids)
            if current_cnt >= max_cap:
                continue

            # Check student is not already in this class
            if rec.student_id in cls.student_ids:
                continue

            # Check day preference match score
            day_matched = cls.day.lower() in rec.preferred_days.lower() or rec.preferred_days.lower() in ["all", "any", "all days"]
            
            reason = f"Matches level ({cls.student_level}) and has {max_cap - current_cnt} open seats"
            if day_matched:
                reason = f"★ Preferred Day ({cls.day}) match & {max_cap - current_cnt} open seats"

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
                "day_matched": day_matched,
                "reason": reason
            })

        # Sort recommendations: day_matched first, then seats available
        recommendations.sort(key=lambda x: (not x["day_matched"], x["current_seats"]))

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
            "recommendations": recommendations[:3] # Top 3 smart recommendations
        }
        report_rows.append(row)
    return report_rows
