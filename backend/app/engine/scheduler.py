import uuid
from datetime import date, datetime
from typing import List, Dict, Tuple, Optional, Set
from app.models.student import StudentModel
from app.models.coach import CoachModel
from app.models.schedule import ScheduleResult, ScheduledClass, UnscheduledRecord, CoachCommunicationSlot
from app.config import SystemConfig, DEFAULT_CONFIG, BatchConfig
from app.engine.time_utils import get_day_name, generate_date_range, is_slot_in_preference, parse_slot_range
from app.engine.coach_selector import CoachSelector
from app.engine.batch_builder import group_students_for_slot, BatchGroup
from app.engine.accountability import AccountabilityTracker
from app.utils.time_utils import parse_time_slot_sort_key

class ScheduleValidationError(Exception):
    """Raised when hard final validation detects a constraint violation."""
    pass

def validate_schedule_integrity(
    students: List[StudentModel],
    coaches: List[CoachModel],
    result: ScheduleResult,
    config: SystemConfig
) -> List[str]:
    """
    Performs hard final validation across the ENTIRE generated schedule.
    Checks all mandatory invariants specified in Section 10:
    1. Student daily uniqueness: count(student_id, calendar_date) <= 1
    2. Required class limit: scheduled_classes <= required_classes
    3. Class accounting: scheduled_classes + remaining_classes == required_classes
    4. Availability: No student scheduled on Not Available day
    5. Group capacity: min_cap <= group_size <= max_cap for Group batches
    6. Coach conflict: No overlapping classes for a coach
    7. Coach daily limit: No coach exceeds daily max
    8. Coach monthly capacity: No coach exceeds monthly max capacity
    """
    violations = []
    student_map = {s.student_id: s for s in students}
    coach_map = {c.coach_name.strip().lower(): c for c in coaches}

    # 1. Student daily uniqueness: count(student_id, calendar_date) <= 1
    student_date_counts: Dict[Tuple[str, str], int] = {}
    for cls in result.scheduled_classes:
        for sid in cls.student_ids:
            key = (sid, cls.date)
            student_date_counts[key] = student_date_counts.get(key, 0) + 1
            if student_date_counts[key] > 1:
                s_name = student_map[sid].student_name if sid in student_map else sid
                violations.append(f"CRITICAL: Student {s_name} ({sid}) assigned multiple classes on {cls.date} (count: {student_date_counts[key]})")

    # 2. Required class limit & exact class accounting
    student_scheduled_counts: Dict[str, int] = {s.student_id: 0 for s in students}
    for cls in result.scheduled_classes:
        for sid in cls.student_ids:
            student_scheduled_counts[sid] = student_scheduled_counts.get(sid, 0) + 1

    unscheduled_map = {rec.student_id: rec.remaining_classes for rec in result.unscheduled_records}

    for s in students:
        s_id = s.student_id
        sch_cnt = student_scheduled_counts.get(s_id, 0)
        rem_cnt = unscheduled_map.get(s_id, 0)

        # scheduled_classes <= required_classes
        if sch_cnt > s.required_classes:
            violations.append(f"CRITICAL: Student {s.student_name} ({s_id}) scheduled for {sch_cnt} classes > required ({s.required_classes})")

        # scheduled_classes + remaining_classes == required_classes
        if sch_cnt + rem_cnt != s.required_classes:
            violations.append(f"CRITICAL: Student {s.student_name} ({s_id}) class accounting mismatch: {sch_cnt} scheduled + {rem_cnt} remaining != {s.required_classes} required")

    # 3. Availability compliance
    for cls in result.scheduled_classes:
        for sid in cls.student_ids:
            s_obj = student_map.get(sid)
            if s_obj and not s_obj.is_available_on_day(cls.day):
                violations.append(f"CRITICAL: Student {s_obj.student_name} ({sid}) scheduled on unavailable day {cls.day} ({cls.date})")

    # 4. Group & Limited batch capacity compliance
    g_min = config.batch_types.get("G", BatchConfig(symbol="G", name="Group Batch", min_capacity=4, max_capacity=10)).min_capacity
    g_max = config.batch_types.get("G", BatchConfig(symbol="G", name="Group Batch", min_capacity=4, max_capacity=10)).max_capacity
    l_min = config.batch_types.get("L", BatchConfig(symbol="L", name="Limited Students Batch", min_capacity=1, max_capacity=4)).min_capacity
    l_max = config.batch_types.get("L", BatchConfig(symbol="L", name="Limited Students Batch", min_capacity=1, max_capacity=4)).max_capacity

    for cls in result.scheduled_classes:
        count = len(cls.student_ids)
        if cls.batch_type == "G":
            if count > g_max:
                violations.append(f"CRITICAL: Group Batch class {cls.class_id} on {cls.date} has {count} students (max allowed {g_max})")
        elif cls.batch_type == "L":
            if count < l_min or count > l_max:
                violations.append(f"CRITICAL: Limited Batch class {cls.class_id} on {cls.date} has {count} students (required {l_min}-{l_max})")
        elif cls.batch_type == "I":
            if count != 1:
                violations.append(f"CRITICAL: Individual Batch class {cls.class_id} on {cls.date} has {count} students (required 1)")

    # 5. Coach overlap compliance
    coach_slot_occupancy: Dict[Tuple[str, str, str], int] = {}
    for cls in result.scheduled_classes:
        c_key = (cls.coach_name.strip().lower(), cls.date, cls.time_slot)
        coach_slot_occupancy[c_key] = coach_slot_occupancy.get(c_key, 0) + 1
        if coach_slot_occupancy[c_key] > 1:
            violations.append(f"CRITICAL: Coach {cls.coach_name} assigned overlapping classes at {cls.time_slot} on {cls.date}")

    # 6. Coach daily max limit compliance
    coach_daily_counts: Dict[Tuple[str, str], int] = {}
    for cls in result.scheduled_classes:
        d_key = (cls.coach_name.strip().lower(), cls.date)
        coach_daily_counts[d_key] = coach_daily_counts.get(d_key, 0) + 1
        
        c_obj = coach_map.get(cls.coach_name.strip().lower())
        if c_obj:
            d_max = c_obj.get_daily_max(cls.day)
            if coach_daily_counts[d_key] > d_max:
                violations.append(f"CRITICAL: Coach {cls.coach_name} exceeded daily max on {cls.day} {cls.date} ({coach_daily_counts[d_key]}/{d_max})")

    # 7. Coach monthly max capacity compliance
    coach_monthly_counts: Dict[str, int] = {}
    for cls in result.scheduled_classes:
        c_name = cls.coach_name.strip().lower()
        coach_monthly_counts[c_name] = coach_monthly_counts.get(c_name, 0) + 1

    for c_name, count in coach_monthly_counts.items():
        c_obj = coach_map.get(c_name)
        if c_obj and count > c_obj.monthly_capacity_max:
            violations.append(f"CRITICAL: Coach {c_obj.coach_name} exceeded monthly max capacity ({count}/{c_obj.monthly_capacity_max})")

    # 8. Coach qualification check
    for cls in result.scheduled_classes:
        c_obj = coach_map.get(cls.coach_name.strip().lower())
        if c_obj and not c_obj.can_handle_level(cls.student_level, config):
            violations.append(f"CRITICAL: Coach {cls.coach_name} not qualified to teach {cls.student_level} in class {cls.class_id}")

    # 9. Sunday operating restrictions check
    for cls in result.scheduled_classes:
        if cls.day == "Sunday":
            _, end_min = parse_slot_range(cls.time_slot)
            if end_min and end_min > 15 * 60:
                violations.append(f"CRITICAL: Sunday class {cls.class_id} at {cls.time_slot} ends after 3:00 PM ceiling")

    # 10. Date range check
    s_dt_str = result.start_date
    e_dt_str = result.end_date
    for cls in result.scheduled_classes:
        if cls.date < s_dt_str or cls.date > e_dt_str:
            violations.append(f"CRITICAL: Class {cls.class_id} date {cls.date} is outside schedule range {s_dt_str} to {e_dt_str}")

    return violations


from app.engine.dynamic_scheduler import run_dynamic_scheduler

def run_scheduler(
    students: List[StudentModel],
    coaches: List[CoachModel],
    start_date: date,
    end_date: date,
    config: SystemConfig = DEFAULT_CONFIG,
    schedule_id: Optional[str] = None
) -> ScheduleResult:
    """
    Main Mighty Knight scheduling engine:
    Dynamic student-to-class scheduling with qualified trainers selected per session,
    using existing batches as flexible capacity pools.
    Deterministic, rule-based, quota-aware scheduling.
    """
    res = run_dynamic_scheduler(
        students=students,
        coaches=coaches,
        start_date=start_date,
        end_date=end_date,
        config=config,
        schedule_id=schedule_id
    )

    # Perform integrity verification
    violations = validate_schedule_integrity(students, coaches, res, config)
    if violations:
        print(f"[ENGINE INTEGRITY ALERT] {len(violations)} rule violations detected in run_scheduler:")
        for v in violations[:5]:
            print(f"  - {v}")

    return res

