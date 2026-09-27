import os
import uuid
import re
from datetime import date, datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Tuple, Optional, Set, Any

from app.models.student import StudentModel
from app.models.coach import CoachModel
from app.models.schedule import ScheduleResult, ScheduledClass, UnscheduledRecord, CoachCommunicationSlot
from app.config import SystemConfig, DEFAULT_CONFIG, BatchConfig
from app.engine.time_utils import get_day_name, generate_date_range, is_slot_in_preference, parse_slot_range, eval_coach_timing_preference
from app.engine.coach_selector import CoachSelector
from app.engine.accountability import AccountabilityTracker
from app.utils.time_utils import parse_time_slot_sort_key
from app.storage.database import load_master_batches_db

COACH_ALIAS_MAP = {
    "bathri": "Bathrinath",
    "bathrinath": "Bathrinath",
    "guru": "Guruvanthana",
    "guruvanthana": "Guruvanthana",
    "dhaanush": "Dhaanush",
    "dhanush": "Dhaanush",
    "arshath": "Arshath",
    "saravanan": "Saravanan",
    "abinaya": "Abinaya",
    "prakash": "Prakash",
    "manikandan": "Manikandan",
    "hema": "Hema"
}

def resolve_coach_name(name: str) -> str:
    if not name:
        return "Unassigned"
    clean = name.strip().lower()
    return COACH_ALIAS_MAP.get(clean, name.strip())

def normalize_slot_string(slot_str: str) -> str:
    """Normalizes slots like '6:00 PM' or '18:00:00' to '06:00 PM – 07:00 PM'."""
    s = slot_str.strip()
    if "–" in s or "-" in s:
        return s
    start_min, end_min = parse_slot_range(s)
    if start_min is not None and end_min is not None:
        def m_to_12h(mins):
            h = (mins // 60) % 24
            m = mins % 60
            ampm = "AM" if h < 12 else "PM"
            h12 = h if (1 <= h <= 12) else (12 if h in [0, 12] else h - 12)
            return f"{h12:02d}:{m:02d} {ampm}"
        return f"{m_to_12h(start_min)} – {m_to_12h(end_min)}"
    return s

class CandidateSessionSlot:
    def __init__(
        self,
        date_str: str,
        day_name: str,
        time_slot: str,
        batch_name: str,
        student_level: str,
        batch_type: str,
        preferred_trainer: Optional[str] = None,
        roster_student_ids: Optional[Set[str]] = None,
        max_capacity: int = 10,
        min_capacity: int = 4
    ):
        self.date_str = date_str
        self.day_name = day_name
        self.time_slot = normalize_slot_string(time_slot)
        self.batch_name = batch_name
        self.student_level = student_level
        self.batch_type = batch_type
        self.preferred_trainer = resolve_coach_name(preferred_trainer) if preferred_trainer and preferred_trainer != "Unassigned" else None
        self.roster_student_ids = roster_student_ids or set()
        self.max_capacity = max_capacity
        self.min_capacity = min_capacity

def build_candidate_session_slots(
    target_dates: List[date],
    master_batches: List[Dict[str, Any]],
    students: List[StudentModel],
    config: SystemConfig
) -> List[CandidateSessionSlot]:
    """
    Builds candidate session slots across the date range:
    1. Expands master batches matching day of week into concrete session slots.
    2. Respects batch-specific student rosters and preferred trainers.
    3. Injects supplementary candidate slots from operating hours to satisfy student demand.
    """
    slots: List[CandidateSessionSlot] = []
    created_slot_keys = set()

    for d_obj in target_dates:
        date_str = d_obj.strftime("%Y-%m-%d")
        day_name = get_day_name(d_obj)
        dow_short = day_name[:3]

        # 1. Expand master batches matching this day of week
        for b in master_batches:
            weekly_slots = list(b.get("weekly_slots", []))
            if not weekly_slots and b.get("schedule_timings"):
                st = b["schedule_timings"]
                for day_abbr in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
                    if day_abbr in st:
                        time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))', st)
                        t_part = time_match.group(1) if time_match else "06:00 PM"
                        weekly_slots.append(f"{day_abbr} {t_part}")

            fixed_trainer = b.get("fixed_trainer", "Unassigned")
            b_name = b.get("batch_name", b.get("batch_id", "Batch"))
            lvl = b.get("level", "Beginner 1")
            b_type = b.get("batch_type", "G")

            # Determine capacity bounds
            if b_type == "I":
                max_cap, min_cap = 1, 1
            elif b_type == "L":
                max_cap = b.get("capacity_max") or 4
                min_cap = b.get("capacity_min") or 1
            else:
                max_cap = b.get("capacity_max") or 10
                min_cap = b.get("capacity_min") or 4

            s_ids = set(b.get("student_ids", []))
            if not s_ids and b.get("students"):
                s_ids = {s["student_id"] for s in b["students"] if isinstance(s, dict) and s.get("student_id")}

            for s_entry in weekly_slots:
                parts = s_entry.strip().split(maxsplit=1)
                if not parts or len(parts) < 2:
                    continue
                day_prefix = parts[0].replace(":", "").strip().lower()
                if day_prefix == day_name.lower() or day_prefix == dow_short.lower() or s_entry.lower().startswith(dow_short.lower()):
                    time_part = parts[1].strip()
                    times = [t.strip() for t in time_part.split("/") if t.strip()]

                    for t_slot in times:
                        normalized_slot = normalize_slot_string(t_slot)
                        # Sunday 3 PM rule check
                        if day_name == "Sunday":
                            _, end_min = parse_slot_range(normalized_slot)
                            if end_min and end_min > 15 * 60:
                                continue

                        key = (date_str, normalized_slot, b_name)
                        if key not in created_slot_keys:
                            created_slot_keys.add(key)
                            slots.append(CandidateSessionSlot(
                                date_str=date_str,
                                day_name=day_name,
                                time_slot=normalized_slot,
                                batch_name=b_name,
                                student_level=lvl,
                                batch_type=b_type,
                                preferred_trainer=fixed_trainer if fixed_trainer != "Unassigned" else None,
                                roster_student_ids=s_ids,
                                max_capacity=max_cap,
                                min_capacity=min_cap
                            ))

        # 2. Add supplementary candidate slots for batch identities or levels with demand
        needed_demands = set()
        for s in students:
            if s.is_available_on_day(day_name):
                needed_demands.add((s.get_batch_identity(), s.student_level, s.batch_type))

        op_slots = config.sunday_slots if day_name == "Sunday" else config.weekday_slots
        for b_name, lvl, b_type in needed_demands:
            for t_slot in op_slots:
                normalized_t = normalize_slot_string(t_slot)
                if day_name == "Sunday":
                    _, end_min = parse_slot_range(normalized_t)
                    if end_min and end_min > 15 * 60:
                        continue

                key = (date_str, normalized_t, b_name)
                if key not in created_slot_keys:
                    created_slot_keys.add(key)
                    max_cap = 1 if b_type == "I" else (4 if b_type == "L" else 10)
                    min_cap = 1 if b_type in ["I", "L"] else 4
                    slots.append(CandidateSessionSlot(
                        date_str=date_str,
                        day_name=day_name,
                        time_slot=normalized_t,
                        batch_name=b_name,
                        student_level=lvl,
                        batch_type=b_type,
                        preferred_trainer=None,
                        roster_student_ids=set(),
                        max_capacity=max_cap,
                        min_capacity=min_cap
                    ))

    slots.sort(key=lambda s: (s.date_str, parse_time_slot_sort_key(s.date_str, s.time_slot)))
    return slots

def run_dynamic_scheduler(
    students: List[StudentModel],
    coaches: List[CoachModel],
    start_date: date,
    end_date: date,
    config: SystemConfig = DEFAULT_CONFIG,
    schedule_id: Optional[str] = None,
    master_batches: Optional[List[Dict[str, Any]]] = None,
    random_seed: int = 42
) -> ScheduleResult:
    """
    Deterministic, behavioral reference-aware dynamic scheduler for Mighty Knight.
    - Zero-loss invariant: Required = Scheduled + Deficit.
    - Preserves batch identities (e.g. G Beginner1, G Intermediate2, I Beginner1).
    - Preserves batch capacity limits: Group (4-10, min 4 soft), Limited (1-4), Individual (1).
    - Dynamically partitions weeks across the month for smooth weekly pacing.
    - Pass 1: Preference & weekly pacing aware scheduling.
    - Pass 2: Deficit catch-up via open seat reuse and additional valid sessions.
    - Enforces hard constraints: 1 coach = 1 class, no student duplicates on same date,
      Sunday 3 PM ceiling, coach daily & monthly limits, coach capability.
    - Accountability: Full diagnostic reasons for any student with deficit.
    """
    if not schedule_id:
        schedule_id = f"SCH_{uuid.uuid4().hex[:8].upper()}"

    if not students:
        return ScheduleResult(
            schedule_id=schedule_id,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            total_students_considered=0,
            successfully_scheduled_students=0,
            unscheduled_students_count=0,
            accountability_passed=True,
            scheduled_classes=[],
            unscheduled_records=[],
            coach_schedule=[],
            created_at=datetime.now().isoformat(),
            status="Empty"
        )

    if master_batches is None:
        master_batches = load_master_batches_db()

    target_dates = generate_date_range(start_date, end_date)
    total_days = len(target_dates)

    # Dynamic weekly calendar partitioning
    # Groups dates into weeks (Sunday boundary or 7-day windows)
    date_to_week: Dict[str, int] = {}
    week_idx = 0
    for i, d_obj in enumerate(target_dates):
        date_to_week[d_obj.strftime("%Y-%m-%d")] = week_idx
        # If day is Sunday and not the last day, advance week index
        if get_day_name(d_obj) == "Sunday" and i < total_days - 1:
            week_idx += 1
    num_weeks = max(1, week_idx + 1)

    # Calculate weekly pacing target per student
    student_target_weekly: Dict[str, List[int]] = {}
    student_max_weekly_cap: Dict[str, int] = {}
    for s in students:
        R = s.required_classes
        base_per_week = R // num_weeks
        rem = R % num_weeks
        dist = [base_per_week] * num_weeks
        # Distribute remainder across middle weeks
        for w in range(rem):
            w_target = (w + (num_weeks // 4)) % num_weeks
            dist[w_target] += 1
        student_target_weekly[s.student_id] = dist
        student_max_weekly_cap[s.student_id] = max(1, (R + num_weeks - 1) // num_weeks + 1)

    tracker = AccountabilityTracker(students)
    coach_selector = CoachSelector(coaches, config)
    coach_map = {resolve_coach_name(c.coach_name).lower(): c for c in coaches}

    # Tracking state
    scheduled_classes: List[ScheduledClass] = []
    student_scheduled_counts: Dict[str, int] = defaultdict(int)
    student_scheduled_dates: Set[Tuple[str, str]] = set() # (student_id, date_str)
    student_week_counts: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
    student_coach_history: Dict[str, Set[str]] = defaultdict(set)

    daily_coach_assignments: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    monthly_coach_assignments: Dict[str, int] = defaultdict(int)
    active_time_occupancy: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))

    # Build candidate session slots
    candidate_slots = build_candidate_session_slots(target_dates, master_batches, students, config)

    def is_coach_available_for_slot(
        coach: CoachModel,
        date_str: str,
        day_name: str,
        time_slot: str,
        level: str
    ) -> Tuple[bool, Optional[str]]:
        c_name = resolve_coach_name(coach.coach_name)
        if not coach.can_handle_level(level, config):
            return False, f"Not qualified for {level}"
        if c_name in active_time_occupancy[date_str][time_slot]:
            return False, "Already teaching at this time"
        if day_name == "Sunday":
            if coach.sunday_pref and str(coach.sunday_pref).strip().lower() in ["not available", "no", "off"]:
                return False, "Not available on Sundays"
            _, end_min = parse_slot_range(time_slot)
            if end_min and end_min > 15 * 60:
                return False, "Sunday class ends after 3:00 PM"

        parsed_timings = coach.get_parsed_preferred_timings()
        is_day_avail, matches_window, pref_daily_max = eval_coach_timing_preference(parsed_timings, day_name, time_slot)
        if not is_day_avail:
            return False, f"Marked not available on {day_name}"

        std_daily_max = coach.get_daily_max(day_name)
        eff_daily_max = min(std_daily_max, pref_daily_max) if (pref_daily_max is not None and pref_daily_max >= 0) else std_daily_max
        if daily_coach_assignments[date_str][c_name] >= eff_daily_max:
            return False, f"Daily limit reached ({daily_coach_assignments[date_str][c_name]}/{eff_daily_max})"
        if monthly_coach_assignments[c_name] >= coach.monthly_capacity_max:
            return False, f"Monthly capacity reached ({monthly_coach_assignments[c_name]}/{coach.monthly_capacity_max})"
        return True, None

    def pick_trainer_for_session(slot: CandidateSessionSlot) -> Optional[CoachModel]:
        # 1. Check preferred trainer if specified
        if slot.preferred_trainer:
            pref_c = coach_map.get(resolve_coach_name(slot.preferred_trainer).lower())
            if pref_c:
                ok, _ = is_coach_available_for_slot(pref_c, slot.date_str, slot.day_name, slot.time_slot, slot.student_level)
                if ok:
                    return pref_c

        # 2. Dynamic coach selection using capability and priority order
        selected_coach, _ = coach_selector.select_coach(
            student_level=slot.student_level,
            target_date_str=slot.date_str,
            day_name=slot.day_name,
            time_slot=slot.time_slot,
            is_sunday_tournament=False,
            daily_coach_assignments=daily_coach_assignments,
            monthly_coach_assignments=monthly_coach_assignments,
            active_time_occupancy=active_time_occupancy
        )
        return selected_coach

    slots_by_date: Dict[str, List[CandidateSessionSlot]] = defaultdict(list)
    for cs in candidate_slots:
        slots_by_date[cs.date_str].append(cs)

    # -------------------------------------------------------------------------
    # PASS 1: PRIMARY SCHEDULING (PREFERENCE & PACING AWARE)
    # -------------------------------------------------------------------------
    for d_obj in target_dates:
        date_str = d_obj.strftime("%Y-%m-%d")
        day_name = get_day_name(d_obj)
        w_idx = date_to_week[date_str]
        day_slots = slots_by_date.get(date_str, [])

        for slot in day_slots:
            eligible_students = []
            for s in students:
                sid = s.student_id
                # Hard Constraint 1: student quota cap
                if student_scheduled_counts[sid] >= s.required_classes:
                    continue
                # Hard Constraint 2: student daily uniqueness (at most 1 class per calendar day)
                if (sid, date_str) in student_scheduled_dates:
                    continue
                # Hard Constraint 3: student availability on this day
                if not s.is_available_on_day(day_name):
                    continue
                # Hard Constraint 4: level compatibility
                if s.student_level != slot.student_level:
                    continue
                # Hard Constraint 5: batch type compatibility
                if s.batch_type != slot.batch_type:
                    continue
                # Soft Constraint: weekly target pacing in Pass 1
                weekly_target = student_target_weekly[sid][w_idx]
                if student_week_counts[sid][w_idx] >= weekly_target:
                    continue

                eligible_students.append(s)

            if not eligible_students:
                continue

            # Assign qualified coach
            assigned_coach = pick_trainer_for_session(slot)
            if not assigned_coach:
                continue

            coach_name = resolve_coach_name(assigned_coach.coach_name)

            # Score eligible candidates with multi-factor scoring
            scored_candidates = []
            for s in eligible_students:
                sid = s.student_id
                rem_needed = s.required_classes - student_scheduled_counts[sid]
                rel_deficit = rem_needed / max(1, s.required_classes)

                score = 0.0
                # Exact batch identity match (e.g. G Beginner1)
                if s.get_batch_identity() == slot.batch_name:
                    score += 120.0

                # Urgency / Fairness: avoid starving high deficit students
                score += rel_deficit * 180.0
                score += rem_needed * 10.0

                # Roster continuity: student in master batch roster
                if sid in slot.roster_student_ids:
                    score += 60.0

                # Preferred timing match on this day
                day_pref = s.get_day_preference(day_name)
                if is_slot_in_preference(slot.time_slot, day_pref):
                    score += 50.0
                elif day_pref and "no preference" in day_pref.lower():
                    score += 25.0

                # Coach history continuity
                if coach_name in student_coach_history[sid]:
                    score += 20.0

                scored_candidates.append((score, s))

            # Deterministic sort descending by score, then student_id for reproducibility
            scored_candidates.sort(key=lambda x: (x[0], x[1].student_id), reverse=True)

            # Cap to batch capacity
            chosen_students = [c[1] for c in scored_candidates[:slot.max_capacity]]
            if not chosen_students:
                continue

            chosen_ids = [s.student_id for s in chosen_students]
            chosen_names = [s.student_name for s in chosen_students]

            warnings = []
            if slot.batch_type == "G" and len(chosen_ids) < slot.min_capacity:
                warnings.append(
                    f"Soft notice: Group Batch size is {len(chosen_ids)} (recommended min {slot.min_capacity}). Scheduled to preserve student quota."
                )

            cls_obj = ScheduledClass(
                class_id=f"CLS_{uuid.uuid4().hex[:6].upper()}",
                date=date_str,
                day=day_name,
                time_slot=slot.time_slot,
                coach_name=coach_name,
                batch_name=slot.batch_name,
                student_level=slot.student_level,
                batch_type=slot.batch_type,
                student_ids=chosen_ids,
                student_names=chosen_names,
                warnings=warnings
            )
            scheduled_classes.append(cls_obj)

            # Update tracking states
            for s in chosen_students:
                sid = s.student_id
                student_scheduled_counts[sid] += 1
                student_scheduled_dates.add((sid, date_str))
                student_week_counts[sid][w_idx] += 1
                student_coach_history[sid].add(coach_name)
                tracker.record_class_scheduled(sid)

            daily_coach_assignments[date_str][coach_name] += 1
            monthly_coach_assignments[coach_name] += 1
            active_time_occupancy[date_str][slot.time_slot].append(coach_name)

    # -------------------------------------------------------------------------
    # PASS 2: DEFICIT CATCH-UP & CAPACITY REUSE
    # -------------------------------------------------------------------------
    deficit_students = [
        s for s in students if student_scheduled_counts[s.student_id] < s.required_classes
    ]
    # Sort deficit students with fairness: largest relative deficit first
    deficit_students.sort(
        key=lambda s: (
            (s.required_classes - student_scheduled_counts[s.student_id]) / max(1, s.required_classes),
            s.required_classes - student_scheduled_counts[s.student_id],
            s.student_id
        ),
        reverse=True
    )

    if deficit_students:
        # Step 2A: Existing Class Reuse (prefer adding compatible students to existing classes with open seats)
        for cls in scheduled_classes:
            max_cap = 1 if cls.batch_type == "I" else (4 if cls.batch_type == "L" else 10)
            if len(cls.student_ids) >= max_cap:
                continue

            available_seats = max_cap - len(cls.student_ids)
            for s in list(deficit_students):
                sid = s.student_id
                if student_scheduled_counts[sid] >= s.required_classes:
                    if s in deficit_students:
                        deficit_students.remove(s)
                    continue

                # Hard constraints
                if (sid, cls.date) in student_scheduled_dates:
                    continue
                if not s.is_available_on_day(cls.day):
                    continue
                if s.student_level != cls.student_level:
                    continue
                if s.batch_type != cls.batch_type:
                    continue

                w_idx = date_to_week.get(cls.date, 0)
                if student_week_counts[sid][w_idx] >= student_max_weekly_cap.get(sid, 4):
                    continue

                # Add student to existing class
                cls.student_ids.append(sid)
                cls.student_names.append(s.student_name)
                student_scheduled_counts[sid] += 1
                student_scheduled_dates.add((sid, cls.date))
                student_week_counts[sid][w_idx] += 1
                student_coach_history[sid].add(cls.coach_name)
                tracker.record_class_scheduled(sid)

                available_seats -= 1
                if student_scheduled_counts[sid] >= s.required_classes:
                    deficit_students.remove(s)
                if available_seats <= 0:
                    break

        # Step 2B: Additional Sessions for Remaining Deficit Students
        for d_obj in target_dates:
            if not deficit_students:
                break
            date_str = d_obj.strftime("%Y-%m-%d")
            day_name = get_day_name(d_obj)
            w_idx = date_to_week[date_str]
            day_slots = slots_by_date.get(date_str, [])

            for slot in day_slots:
                compatible_deficits = [
                    s for s in deficit_students
                    if student_scheduled_counts[s.student_id] < s.required_classes
                    and (s.student_id, date_str) not in student_scheduled_dates
                    and s.is_available_on_day(day_name)
                    and s.student_level == slot.student_level
                    and s.batch_type == slot.batch_type
                    and student_week_counts[s.student_id][w_idx] < student_max_weekly_cap.get(s.student_id, 4)
                ]
                if not compatible_deficits:
                    continue

                assigned_coach = pick_trainer_for_session(slot)
                if not assigned_coach:
                    continue

                coach_name = resolve_coach_name(assigned_coach.coach_name)
                # Sort deficits by batch identity match and urgency
                compatible_deficits.sort(
                    key=lambda s: (
                        1 if s.get_batch_identity() == slot.batch_name else 0,
                        (s.required_classes - student_scheduled_counts[s.student_id]) / max(1, s.required_classes)
                    ),
                    reverse=True
                )
                chosen_deficits = compatible_deficits[:slot.max_capacity]

                chosen_ids = [s.student_id for s in chosen_deficits]
                chosen_names = [s.student_name for s in chosen_deficits]

                warnings = []
                if slot.batch_type == "G" and len(chosen_ids) < slot.min_capacity:
                    warnings.append(
                        f"Soft notice: Group Batch size is {len(chosen_ids)} (recommended min {slot.min_capacity}). Scheduled during catch-up pass."
                    )

                new_cls = ScheduledClass(
                    class_id=f"CLS_{uuid.uuid4().hex[:6].upper()}",
                    date=date_str,
                    day=day_name,
                    time_slot=slot.time_slot,
                    coach_name=coach_name,
                    batch_name=slot.batch_name,
                    student_level=slot.student_level,
                    batch_type=slot.batch_type,
                    student_ids=chosen_ids,
                    student_names=chosen_names,
                    warnings=warnings
                )
                scheduled_classes.append(new_cls)

                for s in chosen_deficits:
                    sid = s.student_id
                    student_scheduled_counts[sid] += 1
                    student_scheduled_dates.add((sid, date_str))
                    student_week_counts[sid][w_idx] += 1
                    student_coach_history[sid].add(coach_name)
                    tracker.record_class_scheduled(sid)
                    if student_scheduled_counts[sid] >= s.required_classes:
                        if s in deficit_students:
                            deficit_students.remove(s)

                daily_coach_assignments[date_str][coach_name] += 1
                monthly_coach_assignments[coach_name] += 1
                active_time_occupancy[date_str][slot.time_slot].append(coach_name)

    # -------------------------------------------------------------------------
    # ACCOUNTABILITY & ROOT CAUSE DIAGNOSIS (OUTPUT 3)
    # -------------------------------------------------------------------------
    for s in students:
        sid = s.student_id
        sch_cnt = student_scheduled_counts[sid]
        req_cnt = s.required_classes
        rem_cnt = max(0, req_cnt - sch_cnt)

        if rem_cnt > 0:
            avail_days = [d for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"] if s.is_available_on_day(d)]
            if len(avail_days) <= 1:
                reason = f"STUDENT_UNAVAILABLE: Available on only {len(avail_days)} day(s) ({', '.join(avail_days) if avail_days else 'None'})."
            else:
                qualified = [c for c in coaches if c.can_handle_level(s.student_level, config)]
                if not qualified:
                    reason = f"NO_QUALIFIED_COACH: Insufficient compatible trainer capacity for level '{s.student_level}'."
                else:
                    all_capped = all(monthly_coach_assignments[resolve_coach_name(c.coach_name)] >= c.monthly_capacity_max for c in qualified)
                    if all_capped:
                        reason = f"COACH_MONTHLY_CAPACITY: Monthly limit reached for all coaches qualified for '{s.student_level}'."
                    else:
                        pref_time = s.get_day_preference("Monday")
                        reason = f"NO_VALID_STUDENT_SLOT: Operating slots or batch capacity exhausted for '{s.student_level}' on available days."

            tracker.record_failure_reason(sid, reason)

    # Sort scheduled classes strictly chronologically
    scheduled_classes.sort(
        key=lambda c: (parse_time_slot_sort_key(c.date, c.time_slot), c.coach_name)
    )

    # Generate Output 1 (Coach Communication Slots)
    coach_schedule_map: Dict[Tuple[str, str, str], List[str]] = defaultdict(list)
    for s_cls in scheduled_classes:
        key = (s_cls.date, s_cls.day, s_cls.time_slot)
        if s_cls.coach_name and s_cls.coach_name != "Unassigned":
            if s_cls.coach_name not in coach_schedule_map[key]:
                coach_schedule_map[key].append(s_cls.coach_name)

    coach_schedule_slots: List[CoachCommunicationSlot] = [
        CoachCommunicationSlot(
            date=k[0],
            day=k[1],
            time_slot=k[2],
            coaches=v
        )
        for k, v in sorted(coach_schedule_map.items(), key=lambda item: parse_time_slot_sort_key(item[0][0], item[0][2]))
    ]

    total_in, scheduled_cnt, unscheduled_cnt, acc_passed, unscheduled_recs = tracker.generate_report()

    return ScheduleResult(
        schedule_id=schedule_id,
        status="Draft",
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        total_students_considered=len(students),
        successfully_scheduled_students=scheduled_cnt,
        unscheduled_students_count=unscheduled_cnt,
        accountability_passed=acc_passed,
        scheduled_classes=scheduled_classes,
        unscheduled_records=unscheduled_recs,
        coach_schedule=coach_schedule_slots,
        created_at=datetime.now().isoformat()
    )
