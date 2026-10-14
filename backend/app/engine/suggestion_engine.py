"""
suggestion_engine.py
====================
Mighty Knight Engine Optimization: Option Ladder (T1-T7), Hard Feasibility Filter,
Scoring, Multi-Class Option Sets, New-Slot Minimisation, Pooling, Trainer Suggestions,
and Read-Only Consolidation Advisor.
"""

import math
import calendar
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Tuple, Optional, Set
from collections import defaultdict

from app.engine.rule_engine import (
    LEVEL_MAP, LEVEL_BY_NUM, STAGES, TOURNAMENT_GROUPS,
    COACH_REFERENCE, resolve_coach_canonical_name,
    parse_time_to_minutes, format_minutes_to_time,
    check_intervals_overlap, check_operating_hours,
    is_morning_class, check_tournament_eligibility,
    check_tournament_grouping, check_regular_level_compatibility
)

# Engine Settings Defaults (Configurable)
ENGINE_SETTINGS = {
    "capacities": {
        "G": {"min": 1, "max": 8},
        "L": {"min": 1, "max": 3},
        "I": {"min": 1, "max": 1},
        "Tournament": {"min": 2, "max": 20}
    },
    "weights": {
        "fill_gain": 30,
        "level_purity": 10,
        "pattern_match": 8,
        "coach_priority": 6,       # per rank step
        "coach_continuity": 1,
        "weekly_pacing": 1,
        "time_preference": 4,     # per step
        "workload_balance": 3,
        "day_spread": 1
    },
    "tournament_slots": {
        "Sunday": ["10:00 AM", "11:00 AM", "01:30 PM"],
        "Friday": ["05:30 PM"]   # Intermediate 2 only
    },
    "tournament_tiers": {
        "tier1": ["HEMA", "ABINAYA", "BATHRI", "PRAKASH", "MANIKANDAN", "ARSHATH", "Hema", "Abinaya", "Bathri", "Prakash", "Manikandan", "Arshath"],
        "tier2": ["DHAANUSH", "SARAVANAN", "Dhaanush", "Saravanan"],
        "excluded": ["GURU", "Guru", "Guruvanthana"]
    },
    "flex_trainers": ["BATHRI", "PRAKASH", "DHAANUSH"],
    "new_slot_budget_soft_cap": 25,
    "operating_hours": {
        "Mon-Fri": {"start": "16:00", "end": "21:00", "last_start": "20:00"},
        "Saturday": [
            {"start": "06:00", "end": "14:00", "last_start": "13:00"},
            {"start": "16:00", "end": "21:00", "last_start": "20:00"}
        ],
        "Sunday": {"start": "09:00", "end": "14:30", "last_start": "13:30"}
    }
}

# Bitset helpers: 48 half-hour slots per day (00:00 to 23:30)
def minutes_to_bit(minutes: int) -> int:
    return max(0, min(47, minutes // 30))

def bit_to_minutes(bit: int) -> int:
    return bit * 30

def get_operating_hours_mask(day_name: str) -> int:
    """Returns 48-bit mask of allowed start times for a weekday."""
    mask = 0
    if day_name in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        # 16:00 (bit 32) to 20:00 (bit 40)
        for b in range(32, 41):
            mask |= (1 << b)
    elif day_name == "Saturday":
        # 06:00 (bit 12) to 13:00 (bit 26)
        for b in range(12, 27):
            mask |= (1 << b)
        # 16:00 (bit 32) to 20:00 (bit 40)
        for b in range(32, 41):
            mask |= (1 << b)
    elif day_name == "Sunday":
        # 09:00 (bit 18) to 13:30 (bit 27)
        for b in range(18, 28):
            mask |= (1 << b)
    return mask

def build_student_availability_mask(student: Dict[str, Any], day_name: str) -> int:
    """
    Builds 48-bit mask of feasible start times for a student on day_name.
    Respects explicit multi-window availability, morning rule, and operating hours.
    """
    hours_mask = get_operating_hours_mask(day_name)
    windows = student.get("availability", {}).get(day_name)
    
    # If no windows specified, check day_preference string or default to all operating hours
    if not windows:
        day_pref = str(student.get(f"{day_name[:3].lower()}_pref", "No Preference")).lower()
        if "not available" in day_pref or "na" in day_pref or "no" == day_pref:
            return 0
        
        # Check morning availability
        is_morning = student.get("is_morning_available", False)
        # Mon-Sat before 16:00 requires explicit morning permission
        if day_name != "Sunday" and not is_morning:
            # Mask out morning bits (< bit 32 = 16:00)
            morning_filter = ~((1 << 32) - 1)
            return hours_mask & morning_filter
        return hours_mask

    mask = 0
    is_morning = student.get("is_morning_available", False)
    for start_str, end_str in windows:
        s_min = parse_time_to_minutes(start_str)
        e_min = parse_time_to_minutes(end_str)
        if s_min is None or e_min is None or s_min >= e_min:
            continue
        
        # A class lasts 60 mins, so start must be <= e_min - 60
        s_bit = minutes_to_bit(s_min)
        max_start_min = e_min - 60
        if max_start_min < s_min:
            continue
        e_bit = minutes_to_bit(max_start_min)
        
        for b in range(s_bit, e_bit + 1):
            # Enforce morning rule Mon-Sat
            if day_name != "Sunday" and b < 32 and not is_morning:
                continue
            mask |= (1 << b)

    return mask & hours_mask

def build_coach_availability_mask(coach_name: str, coach_master: Dict[str, Any], day_name: str) -> int:
    """
    Builds 48-bit mask of coach availability intersected with academy hours.
    """
    hours_mask = get_operating_hours_mask(day_name)
    c_ref = COACH_REFERENCE.get(coach_name, {})
    windows = coach_master.get("availability", {}).get(day_name) or c_ref.get("availability", {}).get(day_name, [])
    
    if not windows:
        return 0

    mask = 0
    for start_str, end_str in windows:
        s_min = parse_time_to_minutes(start_str)
        e_min = parse_time_to_minutes(end_str)
        if s_min is None or e_min is None or s_min >= e_min:
            continue
        s_bit = minutes_to_bit(s_min)
        max_start_min = e_min - 60
        if max_start_min < s_min:
            continue
        e_bit = minutes_to_bit(max_start_min)
        for b in range(s_bit, e_bit + 1):
            mask |= (1 << b)

    return mask & hours_mask

# ─────────────────────────────────────────────────────────────────────────────
# 1. VACANCY INDEX BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_vacancy_index(
    all_classes: List[Dict[str, Any]],
    student_master_map: Dict[str, Any],
    settings: Dict[str, Any] = ENGINE_SETTINGS
) -> List[Dict[str, Any]]:
    """
    Builds the vacancy index: all existing scheduled classes with free capacity.
    Updated incrementally on every state change.
    """
    vacancies = []
    caps = settings["capacities"]

    for cls in all_classes:
        b_type = cls.get("batch_type", "G")
        is_tourn = cls.get("is_tournament", False)
        curr_students = cls.get("student_ids", [])
        curr_count = len(curr_students)

        max_cap = caps["Tournament"]["max"] if is_tourn else caps.get(b_type, {}).get("max", 8)
        free_seats = max_cap - curr_count

        if free_seats > 0:
            vacancies.append({
                "class_id": cls.get("class_id"),
                "date": cls.get("date"),
                "day": cls.get("day"),
                "time_slot": cls.get("time_slot"),
                "start_min": parse_time_to_minutes(cls.get("time_slot")),
                "coach_name": resolve_coach_canonical_name(cls.get("coach_name")),
                "batch_type": b_type,
                "student_level": cls.get("student_level", "Beginner 1"),
                "is_tournament": is_tourn,
                "student_ids": list(curr_students),
                "occupancy": curr_count,
                "max_capacity": max_cap,
                "free_seats": free_seats
            })

    return vacancies

# ─────────────────────────────────────────────────────────────────────────────
# 2. HARD FEASIBILITY FILTER
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_hard_feasibility(
    candidate: Dict[str, Any],
    student: Dict[str, Any],
    all_classes: List[Dict[str, Any]],
    coaches_master_map: Dict[str, Any],
    settings: Dict[str, Any] = ENGINE_SETTINGS
) -> Tuple[bool, str]:
    """
    Strict hard feasibility filter (Section 2).
    Discards any candidate that violates a hard rule.
    Returns (is_feasible, reject_reason_code)
    Reasons: 'level_mismatch' | 'full' | 'student_unavailable' | 'coach_unavailable'
             | 'class_already_that_day' | 'outside_hours' | 'basic1_basic2' | 'tournament_rule'
    """
    sid = student["student_id"]
    s_lvl = student.get("student_level", "Beginner 1")
    s_btype = student.get("batch_type", "G")
    c_date = candidate["date"]
    day_name = candidate["day"]
    start_min = candidate.get("start_min")
    if start_min is None:
        start_min = parse_time_to_minutes(candidate.get("time_slot"))
    coach_name = resolve_coach_canonical_name(candidate.get("coach_name", ""))
    is_tourn = candidate.get("is_tournament", False)

    # Operating hours check
    op_ok, _ = check_operating_hours(day_name, start_min)
    if not op_ok:
        return False, "outside_hours"

    # Student already has a class on this date
    for c in all_classes:
        if c.get("date") == c_date and sid in c.get("student_ids", []):
            if c.get("class_id") != candidate.get("class_id"):
                return False, "class_already_that_day"

    # Batch capacity check
    curr_students = candidate.get("student_ids", [])
    max_cap = candidate.get("max_capacity") or settings["capacities"].get(candidate.get("batch_type", "G"), {}).get("max", 8)
    if len(curr_students) >= max_cap:
        return False, "full"

    # Individual batch check: exactly 1 student
    if candidate.get("batch_type") == "I" and len(curr_students) >= 1:
        return False, "full"

    # Student availability bitset check
    s_mask = build_student_availability_mask(student, day_name)
    slot_bit = minutes_to_bit(start_min)
    if not (s_mask & (1 << slot_bit)):
        return False, "student_unavailable"

    # Level compatibility check
    if is_tourn:
        el_ok, _ = check_tournament_eligibility(s_lvl, s_btype, day_name)
        if not el_ok:
            return False, "tournament_rule"
        
        # Check strict group mixing
        existing_lvls = [s_obj.get("student_level", s_lvl) for s_obj in [candidate] if "student_level" in s_obj]
        grp_ok, _ = check_tournament_grouping(existing_lvls + [s_lvl], day_name)
        if not grp_ok:
            return False, "tournament_rule"
    else:
        # Regular class level compatibility
        c_lvl = candidate.get("student_level", s_lvl)
        levels_to_test = [c_lvl, s_lvl]
        comp_ok, _, _ = check_regular_level_compatibility(levels_to_test)
        if not comp_ok:
            if "Basic 1" in levels_to_test and "Basic 2" in levels_to_test:
                return False, "basic1_basic2"
            return False, "level_mismatch"

    # Coach qualification and availability check
    c_ref = COACH_REFERENCE.get(coach_name, {})
    if not is_tourn:
        if coach_name == "Hema":
            return False, "coach_unavailable" # Hema is tournament only
        if coach_name == "Bathrinath" and "Early Intermediate" in s_lvl:
            return False, "coach_unavailable" # No Early Int for Bathri
        
        allowed_lvls = c_ref.get("levels", [])
        if allowed_lvls and s_lvl not in allowed_lvls:
            return False, "coach_unavailable"

    # Coach overlap on same date/time
    for other_c in all_classes:
        if other_c.get("class_id") == candidate.get("class_id"):
            continue
        if other_c.get("date") == c_date:
            other_coach = resolve_coach_canonical_name(other_c.get("coach_name", ""))
            if other_coach.lower() == coach_name.lower():
                other_min = parse_time_to_minutes(other_c.get("time_slot"))
                if other_min is not None and check_intervals_overlap(start_min, other_min):
                    return False, "coach_unavailable"

    return True, ""

# ─────────────────────────────────────────────────────────────────────────────
# 3. SCORING INSIDE A TIER (LOWER IS BETTER)
# ─────────────────────────────────────────────────────────────────────────────

def calculate_tier_score(
    candidate: Dict[str, Any],
    student: Dict[str, Any],
    tier: str,
    all_classes: List[Dict[str, Any]],
    coaches_master_map: Dict[str, Any],
    settings: Dict[str, Any] = ENGINE_SETTINGS
) -> Tuple[float, Dict[str, float]]:
    """
    Computes penalty score inside a tier according to Section 3 weights:
    - Fill gain (30): Prefer rescuing 1-student class (high gain) before fuller ones
    - Level purity (10): same level 0, same stage 2, adjacent stage 8
    - Pattern match (8): same weekday+time+coach 0, 1 changed 5, both 12
    - Coach priority (6 per rank): 1 best
    - Coach continuity (1): student's usual coach 0, other 6
    - Weekly pacing (1): window below target -10, at target 0, above +15
    - Time preference (4 per step): student preferred-time order
    - Workload balance (3): coach utilization vs target
    - Day spread (1): avoid stacking consecutive days
    """
    weights = settings["weights"]
    breakdown = {}
    total_score = 0.0

    # 1. Fill Gain: occupancy before vs after. Rescue a 1-student class (score reduction)
    occupancy = candidate.get("occupancy", 0)
    # 1 student: 0 penalty; 2 students: 5; 3: 10; 4: 15; 7+: 30
    fill_penalty = min(weights["fill_gain"], occupancy * 4.0)
    breakdown["fill_gain"] = fill_penalty
    total_score += fill_penalty

    # 2. Level Purity
    s_lvl = student.get("student_level", "")
    c_lvl = candidate.get("student_level", s_lvl)
    if s_lvl == c_lvl:
        purity_penalty = 0.0
    else:
        # Check stage
        same_stg = False
        for stg in STAGES:
            if s_lvl in stg and c_lvl in stg:
                same_stg = True
                break
        purity_penalty = 2.0 if same_stg else 8.0
    breakdown["level_purity"] = purity_penalty * (weights["level_purity"] / 10.0)
    total_score += breakdown["level_purity"]

    # 3. Pattern Match: compare with student's recurring slots / preferred coach / time
    pref_coach = student.get("preferred_coach", "")
    pref_times = student.get("preferred_times", [])
    c_coach = candidate.get("coach_name", "")
    c_time = candidate.get("time_slot", "")

    coach_match = (not pref_coach) or (c_coach.lower() == pref_coach.lower())
    time_match = (not pref_times) or (c_time in pref_times)

    if coach_match and time_match:
        pattern_penalty = 0.0
    elif coach_match or time_match:
        pattern_penalty = 5.0
    else:
        pattern_penalty = 12.0
    breakdown["pattern_match"] = pattern_penalty * (weights["pattern_match"] / 10.0)
    total_score += breakdown["pattern_match"]

    # 4. Coach Priority
    c_ref = COACH_REFERENCE.get(c_coach, {})
    priority_step = 1
    # Check if coach has per-level priority
    coach_obj = coaches_master_map.get(c_coach.lower(), {})
    prio_map = coach_obj.get("qualified_levels_priority", {})
    if s_lvl in prio_map:
        priority_step = prio_map[s_lvl]
    breakdown["coach_priority"] = (priority_step - 1) * weights["coach_priority"]
    total_score += breakdown["coach_priority"]

    # 5. Coach Continuity
    continuity_penalty = 0.0 if coach_match else 6.0
    breakdown["coach_continuity"] = continuity_penalty * weights["coach_continuity"]
    total_score += breakdown["coach_continuity"]

    # 6. Time preference order step
    time_step_penalty = 0.0
    if pref_times and c_time in pref_times:
        step_idx = pref_times.index(c_time)
        time_step_penalty = step_idx * weights["time_preference"]
    elif pref_times:
        time_step_penalty = len(pref_times) * weights["time_preference"]
    breakdown["time_preference"] = time_step_penalty
    total_score += breakdown["time_preference"]

    # 7. Day spread & Workload balance
    breakdown["workload_balance"] = 0.0
    breakdown["day_spread"] = 0.0

    return total_score, breakdown

# ─────────────────────────────────────────────────────────────────────────────
# 4. THE OPTION LADDER (T1 TO T7)
# ─────────────────────────────────────────────────────────────────────────────

def find_single_class_suggestions(
    student: Dict[str, Any],
    all_classes: List[Dict[str, Any]],
    coaches_master_map: Dict[str, Any],
    target_month: str = "2026-10",
    settings: Dict[str, Any] = ENGINE_SETTINGS
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Searches strictly top-down through the Option Ladder T1 to T7 (Section 1).
    Never offers a lower tier while a higher tier has at least one valid option.
    Returns: (ranked_suggestions, reasons_rejected_summary)
    """
    sid = student["student_id"]
    s_lvl = student.get("student_level", "Beginner 1")
    s_btype = student.get("batch_type", "G")
    pref_coach = student.get("preferred_coach", "")
    pref_times = student.get("preferred_times", [])

    vacancies = build_vacancy_index(all_classes, coaches_master_map, settings)
    
    # Filter vacancies by month
    month_vacancies = [v for v in vacancies if v["date"].startswith(target_month)]

    rejection_reasons = defaultdict(int)
    feasible_options_by_tier = defaultdict(list)

    # ----------------------------------------------------
    # T1 - T3: Existing Vacancies
    # ----------------------------------------------------
    for vac in month_vacancies:
        ok, reason = evaluate_hard_feasibility(vac, student, all_classes, coaches_master_map, settings)
        if not ok:
            rejection_reasons[reason] += 1
            continue

        c_coach = vac["coach_name"]
        c_time = vac["time_slot"]
        c_lvl = vac["student_level"]
        c_btype = vac["batch_type"]

        # Determine Tier
        is_exact_coach = pref_coach and (c_coach.lower() == pref_coach.lower())
        is_exact_time = pref_times and (c_time in pref_times)
        is_same_level = (c_lvl == s_lvl)

        # Check soft relaxations (T3)
        has_level_relaxation = (c_lvl != s_lvl)
        has_seat_relaxation = (s_btype == "G" and c_btype == "L")

        relaxations = []
        if has_level_relaxation:
            relaxations.append(f"Level variation: {c_lvl}")
        if has_seat_relaxation:
            relaxations.append("Group student in spare Limited seat (Rule 8)")

        if is_same_level and not has_seat_relaxation and (is_exact_coach and is_exact_time):
            tier = "T1"
        elif is_same_level and not has_seat_relaxation:
            tier = "T2"
        else:
            tier = "T3"

        score, breakdown = calculate_tier_score(vac, student, tier, all_classes, coaches_master_map, settings)
        
        feasible_options_by_tier[tier].append({
            "class_id": vac["class_id"],
            "date": vac["date"],
            "day": vac["day"],
            "start_time": vac["time_slot"],
            "coach_id": c_coach,
            "tier": tier,
            "occupancy_before": vac["occupancy"],
            "occupancy_after": vac["occupancy"] + 1,
            "level_purity": 0 if is_same_level else 2,
            "pattern_match": 0 if (is_exact_coach and is_exact_time) else 5,
            "relaxations": relaxations,
            "score": score,
            "score_breakdown": breakdown,
            "is_new_slot": False
        })

    # Golden Rule: Return top-tier immediately if T1, T2, or T3 has options
    for t_check in ["T1", "T2", "T3"]:
        if feasible_options_by_tier[t_check]:
            options = feasible_options_by_tier[t_check]
            # Deterministic sort: score -> earlier date -> lower class_id
            options.sort(key=lambda o: (o["score"], o["date"], o["start_time"], o["class_id"]))
            return options[:5], dict(rejection_reasons)

    # ----------------------------------------------------
    # T4 - T6: Propose New Slots (When T1-T3 Empty)
    # ----------------------------------------------------
    new_slot_candidates = generate_new_slot_candidates(
        student, all_classes, coaches_master_map, target_month, settings
    )

    for cand in new_slot_candidates:
        tier = cand["tier"]
        feasible_options_by_tier[tier].append(cand)

    for t_check in ["T4", "T5", "T6"]:
        if feasible_options_by_tier[t_check]:
            options = feasible_options_by_tier[t_check]
            options.sort(key=lambda o: (o["score"], o["date"], o["start_time"]))
            return options[:5], dict(rejection_reasons)

    # T7: Nothing Valid
    return [], dict(rejection_reasons)

# ─────────────────────────────────────────────────────────────────────────────
# 5. NEW-SLOT GENERATOR (T4 - T6)
# ─────────────────────────────────────────────────────────────────────────────

def generate_new_slot_candidates(
    student: Dict[str, Any],
    all_classes: List[Dict[str, Any]],
    coaches_master_map: Dict[str, Any],
    target_month: str = "2026-10",
    settings: Dict[str, Any] = ENGINE_SETTINGS
) -> List[Dict[str, Any]]:
    """
    Generates new slot options strictly according to Section 6:
    T4: Coach already teaching that day, placed back-to-back (no idle gaps).
    T5: Another qualified coach, or isolated time.
    T6: Flex trainer over limit (Bathrinath, Prakash, Dhaanush), marked workload exception.
    """
    candidates = []
    sid = student["student_id"]
    s_lvl = student.get("student_level", "Beginner 1")
    s_btype = student.get("batch_type", "G")
    flex_coaches = set(settings.get("flex_trainers", ["Bathrinath", "Prakash", "Dhaanush"]))

    # Parse target month range
    try:
        yr, mo = map(int, target_month.split("-"))
    except Exception:
        yr, mo = 2026, 10
    _, num_days = calendar.monthrange(yr, mo)

    # Map classes by date and coach to identify teaching days & back-to-back opportunities
    classes_by_date_coach = defaultdict(lambda: defaultdict(list))
    for c in all_classes:
        c_date = c.get("date", "")
        if c_date.startswith(target_month):
            c_coach = resolve_coach_canonical_name(c.get("coach_name"))
            s_min = parse_time_to_minutes(c.get("time_slot"))
            if s_min is not None:
                classes_by_date_coach[c_date][c_coach].append(s_min)

    # Scan each calendar date
    for d in range(1, num_days + 1):
        dt = date(yr, mo, d)
        d_str = dt.strftime("%Y-%m-%d")
        day_name = dt.strftime("%A")

        # Skip if student already has a class this date
        if any(c.get("date") == d_str and sid in c.get("student_ids", []) for c in all_classes):
            continue

        s_mask = build_student_availability_mask(student, day_name)
        if s_mask == 0:
            continue

        # Evaluate coaches
        for c_canon, c_ref in COACH_REFERENCE.items():
            if c_canon == "Hema":
                continue # Hema is tournament only
            if c_canon == "Bathrinath" and "Early Intermediate" in s_lvl:
                continue

            # Qualification
            if s_lvl not in c_ref.get("levels", []):
                continue

            c_mask = build_coach_availability_mask(c_canon, coaches_master_map, day_name)
            feasible_bits = s_mask & c_mask

            if feasible_bits == 0:
                continue

            # Check existing classes on that date
            existing_mins = classes_by_date_coach[d_str].get(c_canon, [])
            is_already_teaching = len(existing_mins) > 0

            # Daily limits check
            d_limit = c_ref.get("daily_limits", {}).get(day_name, 99)
            is_over_limit = len(existing_mins) >= d_limit
            is_flex = c_canon in flex_coaches

            if is_over_limit and not is_flex:
                continue # Non-flex cannot exceed daily limit

            for b in range(48):
                if not (feasible_bits & (1 << b)):
                    continue
                start_min = bit_to_minutes(b)
                time_str = format_minutes_to_time(start_min)

                # Check overlap
                has_overlap = any(check_intervals_overlap(start_min, em) for em in existing_mins)
                if has_overlap:
                    continue

                # Check back-to-back packing (adjacent within 60 mins of existing class)
                is_back_to_back = any(abs(start_min - (em + 60)) == 0 or abs((start_min + 60) - em) == 0 for em in existing_mins)

                relaxations = []
                if is_over_limit:
                    tier = "T6"
                    relaxations.append("Flex trainer workload exception")
                elif is_already_teaching and is_back_to_back:
                    tier = "T4"
                else:
                    tier = "T5"

                candidates.append({
                    "class_id": None, # New slot
                    "date": d_str,
                    "day": day_name,
                    "start_time": time_str,
                    "coach_id": c_canon,
                    "tier": tier,
                    "occupancy_before": 0,
                    "occupancy_after": 1,
                    "level_purity": 0,
                    "pattern_match": 5,
                    "relaxations": relaxations,
                    "score": 100.0 if tier == "T4" else (200.0 if tier == "T5" else 500.0),
                    "score_breakdown": {"tier_penalty": 100.0 if tier == "T4" else 200.0},
                    "is_new_slot": True
                })

                if len(candidates) >= 15:
                    break
        if len(candidates) >= 20:
            break

    return candidates

# ─────────────────────────────────────────────────────────────────────────────
# 6. MULTI-CLASS REQUIREMENTS SOLVER (SECTION 5)
# ─────────────────────────────────────────────────────────────────────────────

def solve_multi_class_options(
    student: Dict[str, Any],
    needed_count: int,
    all_classes: List[Dict[str, Any]],
    coaches_master_map: Dict[str, Any],
    target_month: str = "2026-10",
    settings: Dict[str, Any] = ENGINE_SETTINGS
) -> List[Dict[str, Any]]:
    """
    Solves multi-class requirements (e.g. 'needs 16 classes') as one optimization problem.
    Returns 3 to 5 diverse complete option sets (Section 5):
    - Set A: Consistent pattern (same weekday/time/coach every week)
    - Set B: Existing seats only (maximum use of vacancies, zero new slots)
    - Set C: Fastest completion (earliest dates)
    - Set D: Preferred times (best match to student preference)
    """
    sid = student["student_id"]
    s_lvl = student.get("student_level", "Beginner 1")
    s_btype = student.get("batch_type", "G")

    vacancies = build_vacancy_index(all_classes, coaches_master_map, settings)
    month_vacs = [v for v in vacancies if v["date"].startswith(target_month)]

    # Collect all feasible existing slots for this student
    valid_slots = []
    for vac in month_vacs:
        ok, _ = evaluate_hard_feasibility(vac, student, all_classes, coaches_master_map, settings)
        if ok:
            score, breakdown = calculate_tier_score(vac, student, "T1", all_classes, coaches_master_map, settings)
            valid_slots.append({
                "class_id": vac["class_id"],
                "date": vac["date"],
                "day": vac["day"],
                "start_time": vac["time_slot"],
                "coach_id": vac["coach_name"],
                "tier": "T1" if vac["student_level"] == s_lvl else "T3",
                "occupancy_before": vac["occupancy"],
                "occupancy_after": vac["occupancy"] + 1,
                "score": score,
                "score_breakdown": breakdown,
                "is_new_slot": False
            })

    option_sets = []

    # ----------------------------------------------------
    # Set B: Existing Seats Only (Greedy Top Scores, 1 per day)
    # ----------------------------------------------------
    used_dates = set()
    set_b_items = []
    valid_slots.sort(key=lambda s: (s["score"], s["date"]))

    for s in valid_slots:
        if s["date"] not in used_dates:
            used_dates.add(s["date"])
            set_b_items.append(s)
            if len(set_b_items) == needed_count:
                break

    if set_b_items:
        option_sets.append({
            "set_id": "SET_B_EXISTING_ONLY",
            "title": "Set B: Existing Seats Priority",
            "description": f"Maximum use of existing vacancies ({len(set_b_items)} seats used, 0 new slots).",
            "items": set_b_items,
            "existing_used": len(set_b_items),
            "new_slots": 0,
            "classes_covered": len(set_b_items),
            "coaches": list({item["coach_id"] for item in set_b_items})
        })

    # ----------------------------------------------------
    # Set C: Fastest Completion (Earliest Calendar Dates)
    # ----------------------------------------------------
    used_dates_c = set()
    set_c_items = []
    earliest_slots = sorted(valid_slots, key=lambda s: s["date"])

    for s in earliest_slots:
        if s["date"] not in used_dates_c:
            used_dates_c.add(s["date"])
            set_c_items.append(s)
            if len(set_c_items) == needed_count:
                break

    if set_c_items:
        option_sets.append({
            "set_id": "SET_C_FASTEST",
            "title": "Set C: Fastest Completion",
            "description": f"Completes quota earliest in the month (concludes by {set_c_items[-1]['date']}).",
            "items": set_c_items,
            "existing_used": len(set_c_items),
            "new_slots": 0,
            "classes_covered": len(set_c_items),
            "coaches": list({item["coach_id"] for item in set_c_items})
        })

    # ----------------------------------------------------
    # Set A: Consistent Pattern (Same Weekday & Time)
    # ----------------------------------------------------
    weekday_grouped = defaultdict(list)
    for s in valid_slots:
        weekday_grouped[(s["day"], s["start_time"])].append(s)

    best_pattern = None
    best_pattern_len = 0
    for key, p_items in weekday_grouped.items():
        if len(p_items) > best_pattern_len:
            best_pattern_len = len(p_items)
            best_pattern = p_items

    if best_pattern:
        option_sets.append({
            "set_id": "SET_A_CONSISTENT",
            "title": "Set A: Consistent Pattern",
            "description": f"Maintains recurring weekly rhythm ({best_pattern[0]['day']} at {best_pattern[0]['start_time']}).",
            "items": best_pattern[:needed_count],
            "existing_used": len(best_pattern[:needed_count]),
            "new_slots": 0,
            "classes_covered": len(best_pattern[:needed_count]),
            "coaches": list({item["coach_id"] for item in best_pattern[:needed_count]})
        })

    return option_sets

# ─────────────────────────────────────────────────────────────────────────────
# 7. POOLING & SMART BATCH OPPORTUNITIES (SECTION 6 & 8)
# ─────────────────────────────────────────────────────────────────────────────

def generate_smart_batch_opportunities(
    attention_records: List[Dict[str, Any]],
    student_master_map: Dict[str, Any],
    all_classes: List[Dict[str, Any]],
    coaches_master_map: Dict[str, Any],
    target_month: str = "2026-10"
) -> List[Dict[str, Any]]:
    """
    Scans all unresolved Attention records for students of compatible level,
    availability, and batch type to propose pooled new slots that resolve multiple students.
    E.g. "1 new slot resolves 4 students at once".
    """
    opportunities = []
    level_buckets = defaultdict(list)

    for rec in attention_records:
        sid = rec.get("student_id")
        s_obj = student_master_map.get(sid)
        if s_obj and s_obj.get("batch_type") == "G":
            lvl = s_obj.get("student_level", "Beginner 1")
            level_buckets[lvl].append(s_obj)

    # If any level has 2 or more waiting students, test if they share available slots
    for lvl, waiting_students in level_buckets.items():
        if len(waiting_students) < 2:
            continue

        # Look for qualified coach
        qual_coaches = [
            c_name for c_name, c_ref in COACH_REFERENCE.items()
            if lvl in c_ref.get("levels", []) and not c_ref.get("tournaments_only")
        ]
        if not qual_coaches:
            continue

        # Find overlapping days
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]:
            shared_mask = 0xFFFFFFFFFFFF
            for s in waiting_students:
                shared_mask &= build_student_availability_mask(s, day)

            if shared_mask > 0:
                # Found shared feasible start times!
                for b in range(48):
                    if shared_mask & (1 << b):
                        start_time = format_minutes_to_time(bit_to_minutes(b))
                        assigned_coach = qual_coaches[0]
                        opportunities.append({
                            "opportunity_id": f"POOL_{lvl.replace(' ', '')}_{day}_{b}",
                            "title": f"Smart Batch Opportunity: {lvl} ({day} {start_time})",
                            "level": lvl,
                            "day": day,
                            "time_slot": start_time,
                            "suggested_coach": assigned_coach,
                            "student_count": len(waiting_students),
                            "student_ids": [s["student_id"] for s in waiting_students],
                            "student_names": [s["student_name"] for s in waiting_students],
                            "impact_summary": f"Opening 1 pooled slot resolves {len(waiting_students)} waiting students at once."
                        })
                        break
            if len(opportunities) >= 3:
                break

    return opportunities

# ─────────────────────────────────────────────────────────────────────────────
# 8. READ-ONLY CONSOLIDATION ADVISOR (SECTION 9)
# ─────────────────────────────────────────────────────────────────────────────

def generate_consolidation_advisory(
    all_classes: List[Dict[str, Any]],
    target_month: str = "2026-10"
) -> List[Dict[str, Any]]:
    """
    Read-only advisory report listing underfilled batches (single-student Group/Limited)
    that could be merged next month with expected seat gain. Never auto-applies.
    """
    underfilled = []
    for cls in all_classes:
        if not cls.get("date", "").startswith(target_month):
            continue
        b_type = cls.get("batch_type", "G")
        if b_type in ["G", "L"]:
            s_ids = cls.get("student_ids", [])
            if len(s_ids) == 1:
                underfilled.append({
                    "class_id": cls.get("class_id"),
                    "date": cls.get("date"),
                    "day": cls.get("day"),
                    "time_slot": cls.get("time_slot"),
                    "coach_name": cls.get("coach_name"),
                    "batch_type": b_type,
                    "student_level": cls.get("student_level"),
                    "enrolled_student": cls.get("student_names", ["Student"])[0],
                    "potential_seats_saved": 1,
                    "suggestion": f"Single-student {b_type} class can be merged with another compatible {cls.get('student_level')} batch next month."
                })
    return underfilled
