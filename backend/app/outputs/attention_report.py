from typing import List, Dict, Any
from app.models.schedule import ScheduleResult, UnscheduledRecord
from app.utils.time_utils import parse_time_slot_sort_key

def format_attention_report(result: ScheduleResult, master_students: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Formats Output 3: Unscheduled / Administrator Attention Report (BRD Section 29, 31).
    Generates smart assignment recommendations & emergency overtime options for each unscheduled student.
    Includes coach's daily schedule load and emergency capacity extension flags, sorted chronologically.
    Filters out dates where student is already scheduled and days where student is not available.
    """
    report_rows = []
    
    # Capacity maps per batch type
    batch_max_capacities = {"G": 10, "L": 4, "I": 1}

    # Pre-calculate daily class counts per coach
    coach_daily_counts = {}
    # Track dates student is already scheduled on (to avoid daily conflict)
    student_scheduled_dates = {}
    for cls in result.scheduled_classes:
        key = (cls.coach_name.strip().lower(), cls.date)
        coach_daily_counts[key] = coach_daily_counts.get(key, 0) + 1
        for sid in cls.student_ids:
            student_scheduled_dates.setdefault(sid, set()).add(cls.date)

    student_model_map = {}
    if master_students:
        from app.models.student import StudentModel
        for s in master_students:
            try:
                s_obj = s if isinstance(s, StudentModel) else StudentModel(**s)
                student_model_map[s_obj.student_id] = s_obj
            except Exception:
                pass

    for rec in result.unscheduled_records:
        recommendations = []

        rec_level_clean = (rec.student_level or "").strip().lower()
        rec_btype_clean = (rec.batch_type or "G").strip().upper()
        rec_pref_days = (rec.preferred_days or "").lower()
        s_obj = student_model_map.get(rec.student_id)

        # Find candidate classes in result.scheduled_classes
        for cls in result.scheduled_classes:
            # Check student is not already in this class
            if rec.student_id in cls.student_ids:
                continue

            # Check student is not already scheduled on this date (Daily uniqueness constraint)
            if cls.date in student_scheduled_dates.get(rec.student_id, set()):
                continue

            # Check student availability on this day
            if s_obj and not s_obj.is_available_on_day(cls.day):
                continue

            cls_level_clean = (cls.student_level or "").strip().lower()
            # Check level match (exact or level normalization)
            if cls_level_clean != rec_level_clean:
                # Also check normalized core level
                from app.constants.levels import normalize_batch_to_level
                cls_norm = normalize_batch_to_level(cls.student_level)[0].lower() if cls.student_level else ""
                rec_norm = normalize_batch_to_level(rec.student_level)[0].lower() if rec.student_level else ""
                if not (cls_norm and rec_norm and cls_norm == rec_norm):
                    continue
            
            # Check batch type match
            b_type = (cls.batch_type or "G").strip().upper()
            if b_type != rec_btype_clean:
                continue

            max_cap = batch_max_capacities.get(b_type, 10)
            current_cnt = len(cls.student_ids)
            c_day_count = coach_daily_counts.get(((cls.coach_name or "").strip().lower(), cls.date), 0)

            # Check day preference match score
            day_matched = (
                cls.day.lower() in rec_pref_days or
                any(p in rec_pref_days for p in ["all", "any", "all days", "flexible", "recurring", "no preference", ""]) or
                not rec_pref_days
            )
            
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
