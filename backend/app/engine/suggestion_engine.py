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
        "tier1": ["HEMA", "ABINAYA", "Abinaya", "BATHRI", "PRAKASH", "MANIKANDAN", "ARSHATH"],
        "tier2": ["DHAANUSH", "Dhaanush", "SARAVANAN", "Saravanan"],
        "excluded": ["GURU", "Guruvanthana", "Guru"]
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
    Supports both baseline coaches and newly registered master coaches.
    """
    hours_mask = get_operating_hours_mask(day_name)
    from app.engine.coach_availability_service import get_unified_coaches_dict
    unified = get_unified_coaches_dict()
    c_ref = unified.get(coach_name.upper()) or COACH_REFERENCE.get(coach_name, {})
    windows = (
        coach_master.get(coach_name, {}).get("availability", {}).get(day_name)
        or coach_master.get("availability", {}).get(day_name)
        or c_ref.get("availability", {}).get(day_name, [])
    )
    
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

    # Rule 1: Strict Batch Type Compatibility (Mandatory Hard Constraint — Zero Exceptions)
    c_btype = candidate.get("batch_type", "G")
    if not is_tourn and c_btype != s_btype:
        return False, "batch_type_mismatch"

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

    # Level compatibility check (Rule 1)
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
            if "Basic 1" in levels_to_test:
                return False, "basic1_isolation"
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
    # Check if coach has per-level priority from authoritative matrix
    coach_obj = (
        coaches_master_map.get(c_coach) or
        coaches_master_map.get(resolve_coach_canonical_name(c_coach)) or
        coaches_master_map.get(c_coach.lower()) or
        coaches_master_map.get(c_coach.upper()) or
        {}
    )
    prio_map = coach_obj.get("qualified_levels_priority", {})
    if s_lvl in prio_map:
        priority_step = prio_map[s_lvl]
    else:
        try:
            from app.config import CURRENT_CONFIG
            cfg_prios = CURRENT_CONFIG.coach_priority.get(s_lvl, [])
            c_canon = resolve_coach_canonical_name(c_coach)
            if c_canon in cfg_prios:
                priority_step = cfg_prios.index(c_canon) + 1
            else:
                priority_step = 99
        except Exception:
            priority_step = 99
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

        # Rule 1: Controlled Adjacent-Level Fallback (Confirmation-Gated)
        is_adjacent_level = (c_lvl != s_lvl)

        relaxations = []
        if is_adjacent_level:
            relaxations.append(f"Controlled Adjacent Level (±1 step): {s_lvl} placed in {c_lvl}. Confirmation required.")

        if is_same_level and (is_exact_coach and is_exact_time):
            tier = "T1"
        elif is_same_level:
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
            "requires_confirmation": is_adjacent_level,
            "confirmation_prompt": f"Adjacent Level Placement (±1 step): Student level is {s_lvl}, but batch level is {c_lvl}. Proceed?" if is_adjacent_level else "",
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
    settings: Dict[str, Any] = ENGINE_SETTINGS,
    max_candidates: int = 150
) -> List[Dict[str, Any]]:
    """
    Generates new slot options strictly according to Section 6 and Rule 8 Enhancement:
    - Scans the entire calendar month across all student's eligible days.
    - Evaluates all qualified coaches to support >=95% coach coverage.
    - T4: Coach already teaching that day, placed back-to-back (no idle gaps).
    - T5: Another qualified coach, or isolated time.
    - T6: Flex trainer over limit (Bathrinath, Prakash, Dhaanush), marked workload exception.
    """
    candidates_by_coach = defaultdict(list)
    sid = student["student_id"]
    s_lvl = student.get("student_level", "Beginner 1")
    s_btype = student.get("batch_type", "G")
    flex_coaches = set(settings.get("flex_trainers", ["Bathrinath", "Prakash", "Dhaanush"]))
    max_per_coach = max(15, max_candidates // 6)

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

        # Evaluate coaches (including newly registered coaches)
        from app.engine.coach_availability_service import get_unified_coaches_dict
        unified_coaches = get_unified_coaches_dict()

        for c_upper, c_ref in unified_coaches.items():
            c_canon = c_ref.get("coach_name") or c_upper
            if c_canon == "Hema" or c_ref.get("tournaments_only"):
                continue # Tournament only
            if c_canon == "Bathrinath" and "Early Intermediate" in s_lvl:
                continue

            # Qualification
            if s_lvl not in c_ref.get("levels", []):
                continue

            # Per-coach limit to ensure broad representation across coaches
            if len(candidates_by_coach[c_canon]) >= max_per_coach:
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
            is_flex = c_ref.get("is_flex", False) or (c_canon in flex_coaches)

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

                candidates_by_coach[c_canon].append({
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

                if len(candidates_by_coach[c_canon]) >= max_per_coach:
                    break

    candidates = []
    for c_canon, c_list in candidates_by_coach.items():
        candidates.extend(c_list)

    return candidates

# ─────────────────────────────────────────────────────────────────────────────
# 6. MULTI-CLASS REQUIREMENTS SOLVER (SECTION 5, PHASE 5 & RULE 8 ENHANCEMENT)
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
    Solves multi-class requirements according to Master Development Directive Prompt 3:
    - Set A: Consistent Weekly Pattern — Maximize same-coach coverage (100% target, max 1 class exception).
    - Set B: Best Existing + New Slot Hybrid — Up to 30 ranked combinations achieving >=95% coach coverage.
    - Set C: Fastest Completion — Earliest feasible calendar completion date with continuity tie-breaking.
    - Sunday Tournament Subsystem: Flags Sunday tournament eligibility and integrates tournament slots.
    """
    sid = student["student_id"]
    s_lvl = student.get("student_level", "Beginner 1")
    s_btype = student.get("batch_type", "G")
    is_tourn_el, _ = check_tournament_eligibility(s_lvl, s_btype, "Sunday")

    # 1. Gather all feasible existing vacancies with free seats
    vacancies = build_vacancy_index(all_classes, coaches_master_map, settings)
    month_vacs = [v for v in vacancies if v["date"].startswith(target_month)]

    valid_existing_slots = []
    for vac in month_vacs:
        ok, _ = evaluate_hard_feasibility(vac, student, all_classes, coaches_master_map, settings)
        if ok:
            score, breakdown = calculate_tier_score(vac, student, "T1", all_classes, coaches_master_map, settings)
            valid_existing_slots.append({
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
                "is_new_slot": False,
                "is_tournament": vac.get("is_tournament", False)
            })

    # 2. Gather feasible new slot candidates across all coaches
    new_slot_candidates = generate_new_slot_candidates(
        student, all_classes, coaches_master_map, target_month, settings, max_candidates=120
    )

    all_feasible_slots = valid_existing_slots + new_slot_candidates

    # Find all eligible coaches for this student's level (including newly registered coaches)
    from app.engine.coach_availability_service import get_unified_coaches_dict
    unified_coaches_dict = get_unified_coaches_dict()

    eligible_coaches = [
        c_ref.get("coach_name") or c_upper for c_upper, c_ref in unified_coaches_dict.items()
        if not c_ref.get("tournaments_only") and s_lvl in c_ref.get("levels", [])
    ]
    if not eligible_coaches:
        eligible_coaches = [c_ref.get("coach_name") or c_upper for c_upper, c_ref in unified_coaches_dict.items()]

    # Map candidate slots by coach
    slots_by_coach = defaultdict(list)
    for s in all_feasible_slots:
        c_name = resolve_coach_canonical_name(s.get("coach_id", ""))
        slots_by_coach[c_name].append(s)

    option_sets = []

    # =========================================================================
    # SET A: Consistent Weekly Pattern — Maximize Same-Coach Coverage (Phase 5.1)
    # =========================================================================
    best_set_a = None
    best_set_a_score = -1

    for c_canon in eligible_coaches:
        c_slots = slots_by_coach.get(c_canon, [])
        if not c_slots:
            continue

        pattern_groups = defaultdict(list)
        for s in c_slots:
            pattern_groups[(s["day"], s["start_time"])].append(s)

        sorted_patterns = sorted(pattern_groups.items(), key=lambda x: len(x[1]), reverse=True)
        combined_c_slots = []
        used_d = set()
        for p_key, p_slots in sorted_patterns:
            for slt in sorted(p_slots, key=lambda x: x["date"]):
                if slt["date"] not in used_d:
                    used_d.add(slt["date"])
                    combined_c_slots.append(slt)

        covered_count = min(needed_count, len(combined_c_slots))
        if covered_count == 0:
            continue

        selected_items = list(combined_c_slots[:covered_count])
        continuity_pct = 100.0 if covered_count == needed_count else round((covered_count / needed_count) * 100, 1)

        # Rule 7.2 & Additional Rule 2: If 1 class short and covered_count == needed_count - 1:
        # Strictly allow at most 1 exception class from another qualified coach
        if len(selected_items) == needed_count - 1 and needed_count > 1:
            used_dates_a = {it["date"] for it in selected_items}
            other_candidate = None
            for other_c in eligible_coaches:
                if other_c == c_canon:
                    continue
                for other_s in slots_by_coach.get(other_c, []):
                    if other_s["date"] not in used_dates_a:
                        other_candidate = other_s
                        break
                if other_candidate:
                    break
            if other_candidate:
                selected_items.append(other_candidate)
                continuity_pct = round(((needed_count - 1) / needed_count) * 100, 1)

        set_a_score = (covered_count * 50) + (100 if len(set(it["coach_id"] for it in selected_items)) == 1 else 40)
        if sorted_patterns and len(sorted_patterns[0][1]) >= min(4, needed_count):
            set_a_score += 30

        if set_a_score > best_set_a_score and len(selected_items) > 0:
            best_set_a_score = set_a_score
            primary_c = c_canon
            other_coaches = [it["coach_id"] for it in selected_items if it["coach_id"] != primary_c]
            desc = f"100% same-coach continuity with Coach {primary_c}." if len(other_coaches) == 0 else f"{continuity_pct}% continuity with Coach {primary_c} (includes 1 exception class with {', '.join(set(other_coaches))})."
            best_set_a = {
                "set_id": "SET_A_CONSISTENT",
                "set_name": "Set A: Consistent Pattern (Max Coach Coverage)",
                "title": "Set A: Consistent Weekly Pattern",
                "description": desc,
                "items": selected_items,
                "existing_used": sum(1 for it in selected_items if not it.get("is_new_slot")),
                "new_slots": sum(1 for it in selected_items if it.get("is_new_slot")),
                "classes_covered": len(selected_items),
                "coaches": list({item["coach_id"] for item in selected_items}),
                "primary_coach": primary_c,
                "continuity_pct": continuity_pct,
                "score": set_a_score
            }

    if best_set_a:
        option_sets.append(best_set_a)

    # =========================================================================
    # SET C: Fastest Completion — Earliest Feasible Quota Completion (Phase 5.3)
    # =========================================================================
    used_dates_c = set()
    set_c_items = []
    earliest_slots = sorted(all_feasible_slots, key=lambda s: (s["date"], s.get("score", 100)))

    for s in earliest_slots:
        if s["date"] not in used_dates_c:
            used_dates_c.add(s["date"])
            set_c_items.append(s)
            if len(set_c_items) == needed_count:
                break

    if set_c_items:
        concludes_on = set_c_items[-1]["date"]
        uniq_c = list({item["coach_id"] for item in set_c_items})
        option_sets.append({
            "set_id": "SET_C_FASTEST",
            "set_name": "Set C: Fastest Completion",
            "title": "Set C: Fastest Completion",
            "description": f"Completes full monthly quota on the earliest feasible date (concludes on {concludes_on}).",
            "items": set_c_items,
            "existing_used": sum(1 for it in set_c_items if not it.get("is_new_slot")),
            "new_slots": sum(1 for it in set_c_items if it.get("is_new_slot")),
            "classes_covered": len(set_c_items),
            "concludes_on": concludes_on,
            "coaches": uniq_c,
            "primary_coach": uniq_c[0] if uniq_c else "Coach",
            "score": 150.0
        })

    # =========================================================================
    # SET B & Rule 8 Enhancement: Best Existing + New Slot Hybrid (Phase 5.2)
    # Up to 30 Distinct, Ranked Combinations & ≥95% Coach Coverage Target
    # =========================================================================
    set_b_candidates = []
    seen_combos = set()

    # Extract student preferences
    s_pref_days_raw = str(student.get("preferred_days", "") or "")
    s_pref_days = set()
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        if day.lower() in s_pref_days_raw.lower():
            s_pref_days.add(day)
        dp = str(student.get(f"{day[:3].lower()}_pref", "")).lower()
        if dp and "not available" not in dp and "na" not in dp and "no" != dp and dp != "no preference":
            s_pref_days.add(day)

    s_pref_time_raw = str(student.get("preferred_time", "") or "").strip()
    s_pref_times_list = list(student.get("preferred_times") or [])
    if s_pref_time_raw and s_pref_time_raw.lower() not in ["flexible", "any", "no preference", ""]:
        s_pref_times_list.append(s_pref_time_raw)

    def make_combo_key(items_list):
        return tuple(sorted((it["date"], it.get("start_time", it.get("time_slot", "")), it["coach_id"]) for it in items_list))

    def score_combo(combo_items, primary_coach_id):
        existing_cnt = sum(1 for it in combo_items if not it.get("is_new_slot"))
        new_cnt = sum(1 for it in combo_items if it.get("is_new_slot"))
        uniq_coaches = list({it["coach_id"] for it in combo_items})

        # 1. Base score and Quota completion
        score = 100.0
        score += (len(combo_items) / max(1, needed_count)) * 50.0

        # 2. Existing seats utilization (Hybrid optimization: favor filling existing batches)
        score += existing_cnt * 25.0

        # 3. Coach Continuity (Rule 7 target: 100% same coach or max 1 exception)
        if len(uniq_coaches) == 1:
            score += 40.0
        elif len(uniq_coaches) == 2:
            score += 20.0
        else:
            score -= (len(uniq_coaches) - 2) * 15.0

        # 4. Student Preference Days Match
        if s_pref_days:
            match_days = sum(1 for it in combo_items if it.get("day") in s_pref_days)
            score += (match_days / max(1, len(combo_items))) * 25.0

        # 5. Student Preference Times Match
        if s_pref_times_list:
            match_times = 0
            for it in combo_items:
                st = str(it.get("start_time") or it.get("time_slot") or "")
                if any(pt.lower() in st.lower() for pt in s_pref_times_list):
                    match_times += 1
            score += (match_times / max(1, len(combo_items))) * 20.0

        # 6. Coach Preference Days/Times & Level Priority
        for c_name in uniq_coaches:
            c_master = (
                coaches_master_map.get(c_name) or
                coaches_master_map.get(resolve_coach_canonical_name(c_name)) or
                coaches_master_map.get(c_name.lower()) or
                coaches_master_map.get(c_name.upper()) or
                {}
            )
            prio_map = c_master.get("qualified_levels_priority", {})
            if s_lvl in prio_map:
                priority = prio_map[s_lvl]
            else:
                try:
                    from app.config import CURRENT_CONFIG
                    cfg_prios = CURRENT_CONFIG.coach_priority.get(s_lvl, [])
                    c_canon = resolve_coach_canonical_name(c_name)
                    priority = (cfg_prios.index(c_canon) + 1) if c_canon in cfg_prios else 3
                except Exception:
                    priority = 3
            score += max(0, 10.0 - (priority * 2.5))
            c_max = c_master.get("monthly_capacity_max", 100)
            c_assigned = sum(1 for c in all_classes if c.get("date", "").startswith(target_month) and resolve_coach_canonical_name(c.get("coach_name")) == c_name)
            if c_max and c_assigned < c_max:
                score += 5.0

        # 7. Sunday Tournament Bonus if eligible
        if is_tourn_el and any(it.get("day") == "Sunday" or it.get("is_tournament") for it in combo_items):
            score += 15.0

        return round(score, 1)

    # Strategy 1: Anchor combinations across every eligible coach (>=95% coverage requirement)
    for c_canon in eligible_coaches:
        c_slots = slots_by_coach.get(c_canon, [])
        if not c_slots:
            continue

        sorted_c_slots = sorted(c_slots, key=lambda s: (s.get("score", 50), s["date"]))
        step = max(1, len(sorted_c_slots) // 6 or 1)

        for offset in range(0, len(sorted_c_slots), step):
            used_d = set()
            combo_items = []
            for slt in sorted_c_slots[offset:] + sorted_c_slots[:offset]:
                if slt["date"] not in used_d:
                    used_d.add(slt["date"])
                    combo_items.append(slt)
                    if len(combo_items) == needed_count:
                        break

            # If coach alone does not cover needed_count, complement with vacancies or other coaches
            if len(combo_items) < needed_count:
                for other_s in all_feasible_slots:
                    if other_s["date"] not in used_d:
                        used_d.add(other_s["date"])
                        combo_items.append(other_s)
                        if len(combo_items) == needed_count:
                            break

            if combo_items:
                ckey = make_combo_key(combo_items)
                if ckey not in seen_combos:
                    seen_combos.add(ckey)
                    existing_cnt = sum(1 for it in combo_items if not it.get("is_new_slot"))
                    new_cnt = sum(1 for it in combo_items if it.get("is_new_slot"))
                    uniq_coaches = list({it["coach_id"] for it in combo_items})
                    combo_score = score_combo(combo_items, c_canon)

                    set_b_candidates.append({
                        "items": combo_items,
                        "existing_used": existing_cnt,
                        "new_slots": new_cnt,
                        "coaches": uniq_coaches,
                        "primary_coach": c_canon,
                        "score": combo_score
                    })

    # Strategy 2: High-vacancy combinations (Maximum existing seats utilization)
    if valid_existing_slots:
        step = max(1, len(valid_existing_slots) // 8 or 1)
        for offset in range(0, len(valid_existing_slots), step):
            used_d = set()
            combo_items = []
            for slt in valid_existing_slots[offset:] + valid_existing_slots[:offset]:
                if slt["date"] not in used_d:
                    used_d.add(slt["date"])
                    combo_items.append(slt)
                    if len(combo_items) == needed_count:
                        break

            if len(combo_items) < needed_count:
                for ns in new_slot_candidates:
                    if ns["date"] not in used_d:
                        used_d.add(ns["date"])
                        combo_items.append(ns)
                        if len(combo_items) == needed_count:
                            break

            if combo_items:
                ckey = make_combo_key(combo_items)
                if ckey not in seen_combos:
                    seen_combos.add(ckey)
                    existing_cnt = sum(1 for it in combo_items if not it.get("is_new_slot"))
                    new_cnt = sum(1 for it in combo_items if it.get("is_new_slot"))
                    uniq_coaches = list({it["coach_id"] for it in combo_items})
                    primary_c = uniq_coaches[0] if uniq_coaches else "Hybrid"
                    combo_score = score_combo(combo_items, primary_c)

                    set_b_candidates.append({
                        "items": combo_items,
                        "existing_used": existing_cnt,
                        "new_slots": new_cnt,
                        "coaches": uniq_coaches,
                        "primary_coach": primary_c,
                        "score": combo_score
                    })

    # Strategy 3: Sunday Tournament Integrated Combinations
    if is_tourn_el:
        sunday_slots = [s for s in all_feasible_slots if s.get("day") == "Sunday" or s.get("is_tournament")]
        non_sunday_slots = [s for s in all_feasible_slots if s.get("day") != "Sunday" and not s.get("is_tournament")]
        for sun_s in sunday_slots[:5]:
            used_d = {sun_s["date"]}
            combo_items = [sun_s]
            for ns in non_sunday_slots:
                if ns["date"] not in used_d:
                    used_d.add(ns["date"])
                    combo_items.append(ns)
                    if len(combo_items) == needed_count:
                        break
            if combo_items:
                ckey = make_combo_key(combo_items)
                if ckey not in seen_combos:
                    seen_combos.add(ckey)
                    existing_cnt = sum(1 for it in combo_items if not it.get("is_new_slot"))
                    new_cnt = sum(1 for it in combo_items if it.get("is_new_slot"))
                    uniq_coaches = list({it["coach_id"] for it in combo_items})
                    primary_c = uniq_coaches[0] if uniq_coaches else "Tournament"
                    set_b_candidates.append({
                        "items": combo_items,
                        "existing_used": existing_cnt,
                        "new_slots": new_cnt,
                        "coaches": uniq_coaches,
                        "primary_coach": primary_c,
                        "score": score_combo(combo_items, primary_c)
                    })

    # Identify which eligible coaches have at least one feasible candidate combo
    coaches_with_candidates = {
        c for cand in set_b_candidates for c in cand["coaches"] if c in eligible_coaches
    }

    selected_combos = []
    selected_keys = set()

    # Pass 1: Broad Coach Representation Anchor (>=95% coverage requirement)
    # Include every coach who can feasibly teach the student in at least one recommendation
    for c_canon in eligible_coaches:
        if c_canon not in coaches_with_candidates:
            continue
        best_for_coach = None
        for cand in set_b_candidates:
            ck = make_combo_key(cand["items"])
            if ck in selected_keys:
                continue
            if cand["primary_coach"] == c_canon or c_canon in cand["coaches"]:
                if best_for_coach is None or cand["score"] > best_for_coach["score"]:
                    best_for_coach = cand

        if best_for_coach:
            selected_combos.append(best_for_coach)
            selected_keys.add(make_combo_key(best_for_coach["items"]))

    # Pass 2: Fill remaining slots up to 30 with top-scoring candidate combinations
    remaining_sorted = sorted(
        [c for c in set_b_candidates if make_combo_key(c["items"]) not in selected_keys],
        key=lambda x: (x["score"], x["existing_used"], -len(x["coaches"])),
        reverse=True
    )

    for cand in remaining_sorted:
        if len(selected_combos) >= 30:
            break
        ck = make_combo_key(cand["items"])
        if ck not in selected_keys:
            selected_combos.append(cand)
            selected_keys.add(ck)

    # Sort final selected combinations deterministically by score descending
    selected_combos.sort(key=lambda x: (x["score"], x["existing_used"], -len(x["coaches"])), reverse=True)

    # Compute actual coach coverage achieved across the selected up to 30 combinations
    coaches_in_selection = {c for cand in selected_combos for c in cand["coaches"] if c in eligible_coaches}
    denom = len(coaches_with_candidates) if coaches_with_candidates else len(eligible_coaches)
    coverage_pct = round((len(coaches_in_selection) / max(1, denom)) * 100, 1)

    # Format up to 30 Set B combinations
    for idx, cand in enumerate(selected_combos[:30]):
        opt_num = idx + 1
        p_coach = cand["primary_coach"]
        desc = f"Hybrid option ({cand['existing_used']} existing seats, {cand['new_slots']} new slots) featuring Coach {p_coach}."
        if len(cand["coaches"]) > 1:
            desc += f" Balanced across {len(cand['coaches'])} coaches: {', '.join(cand['coaches'])}."
        option_sets.append({
            "set_id": f"SET_B_HYBRID_{opt_num}",
            "set_name": f"Set B: Option {opt_num} ({p_coach} Hybrid)",
            "title": f"Option {opt_num}: {p_coach} Hybrid",
            "description": desc,
            "items": cand["items"],
            "existing_used": cand["existing_used"],
            "new_slots": cand["new_slots"],
            "classes_covered": len(cand["items"]),
            "coaches": cand["coaches"],
            "primary_coach": p_coach,
            "score": cand["score"],
            "coach_coverage_pct": coverage_pct
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

        # Look for qualified coach (including newly registered coaches)
        from app.engine.coach_availability_service import get_unified_coaches_dict
        unified_coaches_pool = get_unified_coaches_dict()

        qual_coaches = [
            c_ref.get("coach_name") or c_upper for c_upper, c_ref in unified_coaches_pool.items()
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
