import uuid
from datetime import date, datetime
from typing import List, Dict, Tuple, Optional
from app.models.student import StudentModel
from app.models.coach import CoachModel
from app.models.schedule import ScheduleResult, ScheduledClass, UnscheduledRecord, CoachCommunicationSlot
from app.config import SystemConfig, DEFAULT_CONFIG
from app.engine.time_utils import get_day_name, generate_date_range, is_slot_in_preference, parse_slot_range
from app.engine.coach_selector import CoachSelector
from app.engine.batch_builder import group_students_for_slot, BatchGroup
from app.engine.accountability import AccountabilityTracker

def run_scheduler(
    students: List[StudentModel],
    coaches: List[CoachModel],
    start_date: date,
    end_date: date,
    config: SystemConfig = DEFAULT_CONFIG,
    schedule_id: Optional[str] = None
) -> ScheduleResult:
    """
    Main Mighty Knight scheduling engine running the Priority Order (Section 39)
    and Mandatory Accountability Rules (Section 28).
    """
    if not schedule_id:
        schedule_id = f"SCH_{uuid.uuid4().hex[:8].upper()}"

    tracker = AccountabilityTracker(students)
    selector = CoachSelector(coaches, config)

    target_dates = generate_date_range(start_date, end_date)

    # State tracking structures
    daily_coach_assignments: Dict[str, Dict[str, int]] = {} # date_str -> coach_name -> count
    monthly_coach_assignments: Dict[str, int] = {c.coach_name.strip(): 0 for c in coaches} # coach_name -> total count
    active_time_occupancy: Dict[str, Dict[str, List[str]]] = {} # date_str -> slot_str -> list[coach_name]

    scheduled_classes: List[ScheduledClass] = []

    # Group students by level and batch_type
    students_by_level_batch: Dict[Tuple[str, str], List[StudentModel]] = {}
    for student in students:
        key = (student.student_level.strip(), student.batch_type.strip().upper())
        if key not in students_by_level_batch:
            students_by_level_batch[key] = []
        students_by_level_batch[key].append(student)

    # Iterate through level priority (from basic to advanced or group sizes)
    for (level, batch_type), level_students in students_by_level_batch.items():
        
        # Determine target classes count for each student
        for student in level_students:
            already_scheduled = tracker.scheduled_class_counts[student.student_id]
            needed = student.required_classes - already_scheduled
            if needed <= 0:
                continue

            for class_num in range(needed):
                class_assigned = False

                # Search through target dates
                for d_obj in target_dates:
                    if class_assigned:
                        break

                    day_name = get_day_name(d_obj)
                    date_str = d_obj.strftime("%Y-%m-%d")

                    # Check student availability on day
                    if not student.is_available_on_day(day_name):
                        continue

                    # Select candidate slots for this day
                    if day_name == "Sunday":
                        candidate_slots = config.sunday_slots
                    else:
                        candidate_slots = config.weekday_slots

                    # Prioritize slots based on student's preferred timing
                    pref_str = student.get_day_preference(day_name)
                    
                    def slot_preference_rank(slot: str) -> int:
                        if is_slot_in_preference(slot, pref_str):
                            return 0
                        return 1 # Fallback nearest slot

                    sorted_slots = sorted(candidate_slots, key=slot_preference_rank)

                    for slot in sorted_slots:
                        if class_assigned:
                            break

                        # Check Sunday rules
                        is_sunday_tournament = False
                        if day_name == "Sunday":
                            # Check Sunday 3 PM max end time
                            _, end_min = parse_slot_range(slot)
                            if end_min and end_min > 15 * 60:
                                tracker.record_failure_reason(student.student_id, "Sunday classes must end by 3:00 PM")
                                continue
                            if student.tournament_pref and str(student.tournament_pref).strip().lower() in ["yes", "true", "1"]:
                                is_sunday_tournament = True

                        # Find other available students of same level and batch_type for co-batching
                        matching_peers = [
                            s for s in level_students
                            if s.is_available_on_day(day_name) and is_slot_in_preference(slot, s.get_day_preference(day_name))
                        ]
                        
                        # Ensure current student is included
                        if student not in matching_peers:
                            matching_peers.append(student)

                        # Create candidate batch group
                        batches = group_students_for_slot(matching_peers, level, batch_type, config)
                        target_batch = None
                        for b in batches:
                            if student in b.students:
                                target_batch = b
                                break

                        if not target_batch:
                            continue

                        # Select qualified coach using Section 17 5-step logic
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

                            # Record assignment
                            if date_str not in daily_coach_assignments:
                                daily_coach_assignments[date_str] = {}
                            daily_coach_assignments[date_str][c_name] = daily_coach_assignments[date_str].get(c_name, 0) + 1

                            monthly_coach_assignments[c_name] = monthly_coach_assignments.get(c_name, 0) + 1

                            if date_str not in active_time_occupancy:
                                active_time_occupancy[date_str] = {}
                            if slot not in active_time_occupancy[date_str]:
                                active_time_occupancy[date_str][slot] = []
                            active_time_occupancy[date_str][slot].append(c_name)

                            # Record scheduled students
                            batch_student_ids = [s.student_id for s in target_batch.students]
                            batch_student_names = [s.student_name for s in target_batch.students]

                            for s in target_batch.students:
                                tracker.record_class_scheduled(s.student_id)

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
                                warnings=target_batch.get_warnings()
                            )
                            scheduled_classes.append(s_class)
                            class_assigned = True
                        else:
                            tracker.record_failure_reason(student.student_id, failure_reason or "No eligible coach available")

    # Generate Accountability & Output 3
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

    return ScheduleResult(
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
