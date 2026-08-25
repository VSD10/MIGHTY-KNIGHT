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

    # 4. Group batch capacity compliance
    g_min = config.batch_types.get("G", BatchConfig(symbol="G", name="Group Batch", min_capacity=4, max_capacity=10)).min_capacity
    g_max = config.batch_types.get("G", BatchConfig(symbol="G", name="Group Batch", min_capacity=4, max_capacity=10)).max_capacity

    for cls in result.scheduled_classes:
        count = len(cls.student_ids)
        if cls.batch_type == "G":
            if count < g_min or count > g_max:
                violations.append(f"CRITICAL: Group Batch class {cls.class_id} on {cls.date} has {count} students (required {g_min}-{g_max})")
        elif cls.batch_type == "L":
            if count < 1 or count > 3:
                violations.append(f"CRITICAL: Limited Batch class {cls.class_id} on {cls.date} has {count} students (required 1-3)")
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

    return violations


def run_scheduler(
    students: List[StudentModel],
    coaches: List[CoachModel],
    start_date: date,
    end_date: date,
    config: SystemConfig = DEFAULT_CONFIG,
    schedule_id: Optional[str] = None
) -> ScheduleResult:
    """
    Main Mighty Knight scheduling engine enforcing hard constraints:
    1. Student daily limit: student_id + calendar_date = UNIQUE (max 1 class/day).
    2. Exact required classes: scheduled <= required, scheduled + remaining == required.
    3. Dynamic student day/time preferences (preferred slot first, available days only).
    4. Configurable Group Batch minimum (4-10 students).
    5. Coach capabilities, priority, daily max, monthly max, and Sunday rules.
    6. Hard final validation layer across the entire generated schedule.
    """
    if not schedule_id:
        schedule_id = f"SCH_{uuid.uuid4().hex[:8].upper()}"

    tracker = AccountabilityTracker(students)
    selector = CoachSelector(coaches, config)
    target_dates = generate_date_range(start_date, end_date)

    # State tracking structures
    daily_coach_assignments: Dict[str, Dict[str, int]] = {}
    monthly_coach_assignments: Dict[str, int] = {c.coach_name.strip(): 0 for c in coaches}
    active_time_occupancy: Dict[str, Dict[str, List[str]]] = {}

    student_time_occupancy: Dict[str, Set[Tuple[str, str]]] = {s.student_id: set() for s in students}
    student_daily_dates: Dict[str, Set[str]] = {s.student_id: set() for s in students}

    scheduled_classes: List[ScheduledClass] = []

    # Group students by level and batch_type
    students_by_level_batch: Dict[Tuple[str, str], List[StudentModel]] = {}
    for student in students:
        key = (student.student_level.strip(), student.batch_type.strip().upper())
        if key not in students_by_level_batch:
            students_by_level_batch[key] = []
        students_by_level_batch[key].append(student)

    # Pass 1 & Pass 2 Scheduling Pipeline:
    # Pass 1: Match preferred time slots on preferred days
    # Pass 2: Match fallback time slots on available days
    for pass_num in (1, 2):
        for (level, batch_type), level_students in students_by_level_batch.items():
            batch_cfg = config.batch_types.get(batch_type, config.batch_types["G"])

            for d_obj in target_dates:
                day_name = get_day_name(d_obj)
                date_str = d_obj.strftime("%Y-%m-%d")

                candidate_slots = config.sunday_slots if day_name == "Sunday" else config.weekday_slots

                for slot in candidate_slots:
                    # Filter eligible students for this candidate slot
                    # MUST MEET ALL HARD CONSTRAINTS:
                    # 1) Available on this day
                    # 2) Scheduled < Required (exact limit)
                    # 3) date_str not in student_daily_dates (UNIQUE DAILY DATE)
                    # 4) (date_str, slot) not in student_time_occupancy (NO OVERLAP)
                    # 5) Pass 1: slot is in student's preferred timing; Pass 2: fallback slots allowed
                    eligible_students = []
                    for s in level_students:
                        if not s.is_available_on_day(day_name):
                            continue
                        if tracker.scheduled_class_counts[s.student_id] >= s.required_classes:
                            continue
                        if date_str in student_daily_dates[s.student_id]:
                            continue
                        if (date_str, slot) in student_time_occupancy[s.student_id]:
                            continue
                        
                        pref_str = s.get_day_preference(day_name)
                        if pass_num == 1:
                            if not is_slot_in_preference(slot, pref_str):
                                continue
                        
                        eligible_students.append(s)

                    if not eligible_students:
                        continue

                    # Check Sunday tournament rules
                    is_sunday_tournament = False
                    if day_name == "Sunday":
                        _, end_min = parse_slot_range(slot)
                        if end_min and end_min > 15 * 60: # Sunday 3 PM hard cap
                            for s in eligible_students:
                                tracker.record_failure_reason(s.student_id, "Sunday classes must end by 3:00 PM")
                            continue

                    # Group eligible students into BatchGroup instances
                    batches = group_students_for_slot(eligible_students, level, batch_type, config)

                    for b in batches:
                        if not b.is_valid():
                            for s in b.students:
                                tracker.record_failure_reason(
                                    s.student_id,
                                    f"Group batch size ({len(b.students)}) below required minimum ({batch_cfg.min_capacity})"
                                )
                            continue

                        # Select qualified coach using 5-step logic
                        assigned_coach, failure_reason = selector.select_coach(
                            student_level=level,
                            target_date_str=date_str,
                            day_name=day_name,
                            time_slot=slot,
                            is_sunday_tournament=is_sunday_tournament,
                            daily_coach_assignments=daily_coach_assignments,
                            monthly_coach_assignments=monthly_coach_assignments,
                            active_time_occupancy=active_time_occupancy
                        )

                        if assigned_coach:
                            c_name = assigned_coach.coach_name.strip()

                            # Record coach assignment
                            if date_str not in daily_coach_assignments:
                                daily_coach_assignments[date_str] = {}
                            daily_coach_assignments[date_str][c_name] = daily_coach_assignments[date_str].get(c_name, 0) + 1
                            monthly_coach_assignments[c_name] = monthly_coach_assignments.get(c_name, 0) + 1

                            if date_str not in active_time_occupancy:
                                active_time_occupancy[date_str] = {}
                            if slot not in active_time_occupancy[date_str]:
                                active_time_occupancy[date_str][slot] = []
                            active_time_occupancy[date_str][slot].append(c_name)

                            # Record scheduled students, student_time_occupancy, and student_daily_dates
                            batch_student_ids = [s.student_id for s in b.students]
                            batch_student_names = [s.student_name for s in b.students]

                            for s in b.students:
                                tracker.record_class_scheduled(s.student_id)
                                student_time_occupancy[s.student_id].add((date_str, slot))
                                student_daily_dates[s.student_id].add(date_str)

                            s_class = ScheduledClass(
                                class_id=f"CLS_{uuid.uuid4().hex[:6].upper()}",
                                date=date_str,
                                day=day_name,
                                time_slot=slot,
                                coach_name=c_name,
                                student_level=level,
                                batch_type=batch_type,
                                student_ids=batch_student_ids,
                                student_names=batch_student_names,
                                warnings=b.get_warnings()
                            )
                            scheduled_classes.append(s_class)
                        else:
                            for s in b.students:
                                tracker.record_failure_reason(s.student_id, failure_reason or "No eligible coach available")

    # Generate Accountability Report & Output 3
    total_in, scheduled_cnt, unscheduled_cnt, acc_passed, unscheduled_recs = tracker.generate_report()

    # Generate Output 1 (Coach Communication Schedule)
    coach_schedule_map: Dict[Tuple[str, str, str], List[str]] = {}
    for s_cls in scheduled_classes:
        key = (s_cls.date, s_cls.day, s_cls.time_slot)
        if key not in coach_schedule_map:
            coach_schedule_map[key] = []
        if s_cls.coach_name not in coach_schedule_map[key]:
            coach_schedule_map[key].append(s_cls.coach_name)

    coach_schedule_slots: List[CoachCommunicationSlot] = [
        CoachCommunicationSlot(
            date=k[0],
            day=k[1],
            time_slot=k[2],
            coaches=v
        )
        for k, v in sorted(coach_schedule_map.items(), key=lambda x: (x[0][0], x[0][2]))
    ]

    result = ScheduleResult(
        schedule_id=schedule_id,
        status="Draft",
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        total_students_considered=total_in,
        successfully_scheduled_students=scheduled_cnt,
        unscheduled_students_count=unscheduled_cnt,
        accountability_passed=acc_passed,
        scheduled_classes=scheduled_classes,
        unscheduled_records=unscheduled_recs,
        coach_schedule=coach_schedule_slots,
        created_at=datetime.now().isoformat()
    )

    # HARD FINAL VALIDATION LAYER
    violations = validate_schedule_integrity(students, coaches, result, config)
    if violations:
        result.accountability_passed = False
        error_msg = f"Schedule generation failed hard validation with {len(violations)} violations:\n" + "\n".join(violations)
        raise ScheduleValidationError(error_msg)

    return result
