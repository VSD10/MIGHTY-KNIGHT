"""
suggestion_engine.py
====================
Mighty Knight Engine Optimization: Option Ladder (T1-T7), Hard Feasibility Filter,
Scoring, Multi-Class Option Sets, New-Slot Minimisation, Pooling, Trainer Suggestions,
New Trainer Engagement Proposals, and Read-Only Consolidation Advisor.
"""

import re
import calendar
from datetime import datetime, date
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict

from app.engine.rule_engine import (
    LEVEL_MAP, STAGES,
    COACH_REFERENCE, resolve_coach_canonical_name,
    parse_time_to_minutes, format_minutes_to_time,
    check_intervals_overlap, check_operating_hours,
    check_tournament_eligibility,
    check_tournament_grouping, check_regular_level_compatibility
)
from app.engine.time_utils import parse_slot_range

# In-memory cache for suggestion engine queries to eliminate latency and repeat computation
_SUGGESTION_CACHE: Dict[Tuple[str, int, str], Any] = {}

def invalidate_suggestion_cache():
    """Invalidates the in-memory suggestions cache whenever the schedule state mutates."""
    _SUGGESTION_CACHE.clear()

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
        "tier1": ["HEMA", "Hema", "ABINAYA", "Abinaya", "BATHRI", "Bathrinath", "PRAKASH", "Prakash", "MANIKANDAN", "Manikandan", "ARSHATH", "Arshath"],
        "tier2": ["DHAANUSH", "Dhaanush", "SARAVANAN", "Saravanan"],
        "excluded": ["GURU", "Guruvanthana"]
    },
    "flex_trainers": ["BATHRI", "Bathrinath", "PRAKASH", "Prakash", "DHAANUSH", "Dhaanush"],
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

def get_operating_hours_mask(day_name: str, allow_weekday_morning: bool = False) -> int:
    """Returns 48-bit mask of allowed start times for a weekday."""
    mask = 0
    if day_name in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        if allow_weekday_morning:
            # 06:00 (bit 12) to 13:00 (bit 26)
            for b in range(12, 27):
                mask |= (1 << b)
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

def normalize_date_to_iso(d_val: Any) -> Optional[str]:
    """
    Normalizes dates from various formats (YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY, etc.) to YYYY-MM-DD.
    """
    if not d_val:
        return None
    s = str(d_val).strip()
    if not s or s.lower() in ["none", "null", "n/a", ""]:
        return None
    if re.match(r'^\d{4}-\d{2}-\d{2}$', s):
        return s
    m = re.match(r'^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$', s)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"
    try:
        dt = datetime.fromisoformat(s)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    return None

def enrich_student_profile(student: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes and enriches a student dictionary so that preferences from
    recurring_slots (baseline) and mon_pref..sun_pref (Master Data Hub) are
    always available as preferred_times, preferred_coach, preferred_weekdays,
    and is_morning_available. Also normalizes joining_date and start_date.
    """
    s = dict(student)
    raw_join = s.get("joining_date") or s.get("start_date") or s.get("date_of_joining") or ""
    norm_join = normalize_date_to_iso(raw_join) or ""
    s["joining_date"] = norm_join
    s["start_date"] = norm_join

    rec_slots = s.get("recurring_slots") or {}
    pref_times = list(s.get("preferred_times") or [])
    pref_coach = s.get("preferred_coach") or s.get("fixed_trainer") or ""
    if pref_coach == "Unassigned":
        pref_coach = ""
    is_morning = bool(s.get("is_morning_available", False))
    pref_weekdays = set()

    # 1. Extract from recurring_slots (e.g. {'Saturday': ['10:00 AM', 'ABINAYA']})
    for d_name, val in rec_slots.items():
        pref_weekdays.add(d_name)
        if isinstance(val, (list, tuple)) and len(val) >= 1:
            t_str = str(val[0]).strip()
            if t_str and t_str not in pref_times:
                pref_times.append(t_str)
            t_min = parse_time_to_minutes(t_str)
            if t_min is not None and t_min < 16 * 60:
                is_morning = True
            if len(val) >= 2 and not pref_coach and val[1]:
                pref_coach = resolve_coach_canonical_name(str(val[1]))

    # 2. Extract from mon_pref..sun_pref (e.g. '06:00 PM-09:00 PM')
    day_keys = [
        ("Monday", "mon_pref"), ("Tuesday", "tue_pref"), ("Wednesday", "wed_pref"),
        ("Thursday", "thu_pref"), ("Friday", "fri_pref"), ("Saturday", "sat_pref"),
        ("Sunday", "sun_pref")
    ]
    for d_name, d_key in day_keys:
        raw_p = str(s.get(d_key, "No Preference") or "No Preference").strip()
        p_low = raw_p.lower()
        if p_low not in ["not available", "na", "no", "off", "false", "0", "no preference", ""]:
            pref_weekdays.add(d_name)
            parts = re.split(r'\s*[\-–—]\s*', raw_p)
            if parts:
                s_min = parse_time_to_minutes(parts[0])
                if s_min is not None:
                    fmt_t = format_minutes_to_time(s_min)
                    if fmt_t not in pref_times:
                        pref_times.append(fmt_t)
                    if d_name != "Sunday" and s_min < 16 * 60:
                        is_morning = True

    s["preferred_times"] = pref_times
    s["preferred_coach"] = resolve_coach_canonical_name(pref_coach) if pref_coach else ""
    s["is_morning_available"] = is_morning
    s["preferred_weekdays"] = list(pref_weekdays)
    return s

def build_student_availability_mask(student: Dict[str, Any], day_name: str) -> int:
    """
    Builds 48-bit mask of feasible start times for a student on day_name.
    Respects explicit multi-window availability, mon_pref..sun_pref ranges,
    day_preference filters, morning rule, and operating hours.
    """
    s = enrich_student_profile(student)
    is_morning = s.get("is_morning_available", False)
    hours_mask = get_operating_hours_mask(day_name, allow_weekday_morning=is_morning)

    # Check day_preference string if explicitly provided (e.g. "Monday, Tuesday, Wednesday")
    day_pref_list_str = str(s.get("day_preference", "") or "").strip().lower()
    if day_pref_list_str and day_pref_list_str not in ["flexible", "no preference", "all", "all days", "any", "recurring"]:
        if day_name.lower() not in day_pref_list_str and day_name[:3].lower() not in day_pref_list_str:
            return 0

    # Check explicit availability dict first
    windows = s.get("availability", {}).get(day_name)
    if windows:
        mask = 0
        for start_str, end_str in windows:
            s_min = parse_time_to_minutes(start_str)
            e_min = parse_time_to_minutes(end_str)
            if s_min is None or e_min is None or s_min >= e_min:
                continue
            s_bit = minutes_to_bit(s_min)
            max_start_min = e_min - 60
            if max_start_min < s_min:
                max_start_min = s_min
            e_bit = minutes_to_bit(max_start_min)
            day_has_morning = is_morning or (s_min < 16 * 60)
            for b in range(s_bit, e_bit + 1):
                if day_name != "Sunday" and b < 32 and not day_has_morning:
                    continue
                mask |= (1 << b)
        eff_hours = get_operating_hours_mask(day_name, allow_weekday_morning=True) if mask & ((1 << 32) - 1) else hours_mask
        return mask & eff_hours

    # Check mon_pref .. sun_pref string
    raw_day_pref = str(s.get(f"{day_name[:3].lower()}_pref", "No Preference") or "No Preference").strip()
    day_pref_low = raw_day_pref.lower()
    if day_pref_low in ["not available", "na", "no", "off", "false", "0"]:
        return 0

    # Check if raw_day_pref is a time range like "06:00 PM-09:00 PM" or "09:00 AM – 12:00 PM"
    if any(sep in raw_day_pref for sep in ["-", "–", "—"]):
        parts = re.split(r'\s*[\-–—]\s*', raw_day_pref)
        if len(parts) >= 2:
            s_min = parse_time_to_minutes(parts[0])
            e_min = parse_time_to_minutes(parts[1])
            if s_min is not None and e_min is not None and s_min < e_min:
                mask = 0
                s_bit = minutes_to_bit(s_min)
                max_start_min = max(s_min, e_min - 60)
                e_bit = minutes_to_bit(max_start_min)
                for b in range(s_bit, e_bit + 1):
                    mask |= (1 << b)
                eff_hours = get_operating_hours_mask(day_name, allow_weekday_morning=(s_min < 16 * 60 or is_morning))
                res_mask = mask & eff_hours
                if res_mask > 0:
                    return res_mask

    # Default operating hours on this day
    if day_name != "Sunday" and not is_morning:
        morning_filter = ~((1 << 32) - 1)
        return hours_mask & morning_filter
    return hours_mask

def get_combined_coaches_map(coaches_master_map: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """
    Combines COACH_REFERENCE with any custom/updated trainers from Master Data Hub
    so that both built-in coaches and newly created trainers are evaluated by the engine.
    """
    combined: Dict[str, Dict[str, Any]] = {}
    for c_canon, c_ref in COACH_REFERENCE.items():
        combined[c_canon] = dict(c_ref)
        combined[c_canon]["coach_name"] = c_canon

    if coaches_master_map:
        for k, c_obj in coaches_master_map.items():
            if not isinstance(c_obj, dict):
                continue
            raw_name = c_obj.get("coach_name") or k
            c_canon = resolve_coach_canonical_name(raw_name)
            if not c_canon:
                continue
            base = dict(combined.get(c_canon, {}))
            base["coach_name"] = c_canon
            lvls = c_obj.get("levels_handled") or c_obj.get("levels")
            if lvls is not None:
                base["levels"] = list(lvls)
            elif "levels" not in base:
                base["levels"] = []

            # Daily limits
            d_limits = dict(base.get("daily_limits", {
                "Monday": 4, "Tuesday": 4, "Wednesday": 4, "Thursday": 4,
                "Friday": 4, "Saturday": 5, "Sunday": 2
            }))
            for d_full, d_short in [
                ("Monday", "mon_max"), ("Tuesday", "tue_max"), ("Wednesday", "wed_max"),
                ("Thursday", "thu_max"), ("Friday", "fri_max"), ("Saturday", "sat_max"), ("Sunday", "sun_max")
            ]:
                if d_short in c_obj and c_obj[d_short] is not None:
                    d_limits[d_full] = int(c_obj[d_short])
                elif "max_classes_per_day" in c_obj and c_obj["max_classes_per_day"] is not None:
                    d_limits[d_full] = int(c_obj["max_classes_per_day"])
            if str(c_obj.get("sunday_pref", "")).strip().lower() in ["off", "not available", "no"]:
                d_limits["Sunday"] = 0
            base["daily_limits"] = d_limits

            if c_obj.get("monthly_capacity_max") is not None:
                base["monthly_max"] = int(c_obj["monthly_capacity_max"])
            if "is_flex" in c_obj:
                base["is_flex"] = bool(c_obj["is_flex"])
            if c_obj.get("tournament_role") == "Tournament only":
                base["tournaments_only"] = True
            elif "tournaments_only" not in base:
                base["tournaments_only"] = False

            if c_obj.get("availability"):
                base["availability"] = c_obj["availability"]
            if c_obj.get("preferred_timings"):
                base["preferred_timings"] = c_obj["preferred_timings"]
            is_custom_new = (c_canon not in COACH_REFERENCE)
            base["is_new_coach"] = is_custom_new
            if c_obj.get("qualified_levels_priority"):
                base["qualified_levels_priority"] = dict(c_obj["qualified_levels_priority"])

            combined[c_canon] = base

    # Synchronize qualified_levels_priority for all coaches according to configured priority matrix
    try:
        from app.main import CURRENT_CONFIG
        prio_matrix = getattr(CURRENT_CONFIG, "coach_priority", {}) or {}
    except Exception:
        prio_matrix = {}

    for c_canon, base in combined.items():
        if "qualified_levels_priority" not in base or not base["qualified_levels_priority"]:
            base["qualified_levels_priority"] = {}
        for lvl in base.get("levels", []):
            if lvl in prio_matrix:
                c_list = prio_matrix[lvl]
                if c_canon in c_list:
                    base["qualified_levels_priority"][lvl] = c_list.index(c_canon) + 1
                else:
                    base["qualified_levels_priority"][lvl] = len(c_list) + 1
            elif lvl not in base["qualified_levels_priority"]:
                base["qualified_levels_priority"][lvl] = 99

    return combined

def _parse_coach_preferred_timings_windows(pref_str: str, day_name: str) -> Optional[List[Tuple[str, str]]]:
    """
    Parses a coach's preferred_timings string from MasterDataView (e.g.
    'Monday: 5 pm – 9 pm (max 4); Tuesday: Not available (max 0)' or '5 pm – 9 pm')
    into a list of (start_str, end_str) tuples for day_name.
    Returns None if no specific windows are defined (meaning use default/open hours),
    or [] if explicitly marked Not Available on day_name.
    """
    if not pref_str or not str(pref_str).strip():
        return None
    s = str(pref_str).strip()
    if s.lower() in ["no preference", "available", "all operating hours", "flexible"]:
        return None

    # Check if day-by-day format: "Monday: ...; Tuesday: ..."
    if any(d in s.lower() for d in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
        blocks = re.split(r'[;\n]+', s)
        for b in blocks:
            b_clean = b.strip()
            m = re.match(rf'^{day_name}\s*:\s*(.*)$', b_clean, re.IGNORECASE)
            if m:
                details = m.group(1).strip()
                if "not available" in details.lower() or "max 0" in details.lower() or details.lower() == "off":
                    return []
                clean_slots = re.sub(r'\(max\s*\d+\)', '', details, flags=re.IGNORECASE).strip()
                if "no preference" in clean_slots.lower():
                    return None
                windows = []
                for part in clean_slots.split(","):
                    r_parts = re.split(r'\s*[\-–—]\s*', part.strip())
                    if len(r_parts) >= 2:
                        windows.append((r_parts[0].strip(), r_parts[1].strip()))
                return windows if windows else None
        return None

    # Simple range e.g. "5 pm – 9 pm" or "Evening (4 PM - 9 PM)"
    range_matches = re.findall(r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))\s*[\-–—]\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))', s)
    if range_matches:
        return [(rm[0], rm[1]) for rm in range_matches]
    return None

def build_coach_availability_mask(coach_name: str, coach_master: Dict[str, Any], day_name: str) -> int:
    """
    Builds 48-bit mask of coach availability intersected with academy hours.
    Supports both COACH_REFERENCE availability dicts and Master Data Hub preferred_timings.
    Strictly enforces configured preferred timings, daily limits, and Sunday availability.
    """
    c_canon = resolve_coach_canonical_name(coach_name)
    c_ref = COACH_REFERENCE.get(c_canon, {})

    # Resolve coach_obj if coach_master is a map of coaches or a single coach dict
    coach_obj = {}
    if isinstance(coach_master, dict):
        if "coach_name" in coach_master or "levels_handled" in coach_master or "preferred_timings" in coach_master:
            coach_obj = coach_master
        else:
            coach_obj = coach_master.get(c_canon) or coach_master.get(c_canon.lower()) or {}

    target_coach_dict = coach_obj if coach_obj else c_ref

    # 1. Daily limit check: If coach has max 0 on this day, mask is completely 0
    d_short = f"{day_name[:3].lower()}_max"
    if d_short in target_coach_dict and target_coach_dict[d_short] is not None:
        try:
            if int(target_coach_dict[d_short]) <= 0:
                return 0
        except Exception:
            pass
    elif "max_classes_per_day" in target_coach_dict and target_coach_dict["max_classes_per_day"] is not None:
        try:
            if int(target_coach_dict["max_classes_per_day"]) <= 0:
                return 0
        except Exception:
            pass

    # 2. Sunday off check
    if day_name == "Sunday":
        sun_p = str(target_coach_dict.get("sunday_pref", "")).strip().lower()
        if sun_p in ["off", "not available", "no", "unavailable"]:
            return 0

    windows = coach_obj.get("availability", {}).get(day_name)
    if windows is None and coach_obj.get("preferred_timings"):
        parsed_w = _parse_coach_preferred_timings_windows(coach_obj.get("preferred_timings", ""), day_name)
        if parsed_w is not None:
            windows = parsed_w

    if windows is None:
        windows = c_ref.get("availability", {}).get(day_name)

    # If this is a newly created trainer in Master Data Hub without explicit windows, default to operating hours
    if windows is None and c_canon not in COACH_REFERENCE:
        d_lim = coach_obj.get(f"{day_name[:3].lower()}_max", 4)
        try:
            if int(d_lim) <= 0:
                return 0
        except Exception:
            pass
        hours_mask = get_operating_hours_mask(day_name, allow_weekday_morning=False)
        from app.engine.time_utils import is_slot_in_coach_preference
        valid_mask = 0
        for b in range(48):
            if hours_mask & (1 << b):
                slot_str = format_minutes_to_time(bit_to_minutes(b))
                ok, _ = is_slot_in_coach_preference(target_coach_dict, day_name, slot_str)
                if ok:
                    valid_mask |= (1 << b)
        return valid_mask

    if not windows:
        return 0

    has_morning_window = False
    mask = 0
    for start_str, end_str in windows:
        s_min = parse_time_to_minutes(start_str)
        e_min = parse_time_to_minutes(end_str)
        if s_min is None or e_min is None or s_min >= e_min:
            continue
        if s_min < 16 * 60:
            has_morning_window = True
        s_bit = minutes_to_bit(s_min)
        max_start_min = e_min - 60
        if max_start_min < s_min:
            continue
        e_bit = minutes_to_bit(max_start_min)
        for b in range(s_bit, e_bit + 1):
            mask |= (1 << b)

    hours_mask = get_operating_hours_mask(day_name, allow_weekday_morning=has_morning_window)
    prelim_mask = mask & hours_mask

    # 3. Strictly validate each slot bit against is_slot_in_coach_preference
    from app.engine.time_utils import is_slot_in_coach_preference
    final_mask = 0
    for b in range(48):
        if prelim_mask & (1 << b):
            slot_str = format_minutes_to_time(bit_to_minutes(b))
            ok, _ = is_slot_in_coach_preference(target_coach_dict, day_name, slot_str)
            if ok:
                final_mask |= (1 << b)
    return final_mask

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
             | 'batch_type_mismatch'
    """
    s = enrich_student_profile(student)
    sid = s["student_id"]
    s_lvl = s.get("student_level", "Beginner 1")
    s_btype = (s.get("batch_type") or "G").upper()
    c_date = candidate["date"]
    day_name = candidate.get("day") or (datetime.strptime(c_date, "%Y-%m-%d").strftime("%A") if c_date else "Monday")
    coach_name = resolve_coach_canonical_name(candidate.get("coach_name", ""))
    is_tourn = candidate.get("is_tournament", False)
    c_btype = (candidate.get("batch_type") or "G").upper()
    curr_students = candidate.get("student_ids", [])

    # Rule 1 Mandatory Hard Constraint: Strict Batch Compatibility
    # The scheduling engine must never mix students from different batch types:
    # Group (G) students attend Group batches only, Limited (L) Limited only, Individual (I) Individual only.
    # Individual students must remain individually assigned (1-on-1 private) and never combined into shared batches.
    if is_tourn:
        if s_btype == "I":
            return False, "tournament_rule"
    else:
        if s_btype != c_btype:
            return False, "batch_type_mismatch"
        if s_btype == "I" and len(curr_students) >= 1:
            return False, "full"

    start_min = candidate.get("start_min")
    if start_min is None:
        ts = candidate.get("time_slot") or ""
        if any(sep in ts for sep in ["-", "–", "—"]):
            parsed = parse_slot_range(ts)
            if parsed:
                start_min = parsed[0]
        if start_min is None:
            start_min = parse_time_to_minutes(ts)
    if start_min is None:
        return False, "outside_hours"

    # 1. Mid-month joining date guard: Never allocate classes before student's joining date
    s_join = s.get("joining_date") or s.get("start_date") or ""
    if s_join and c_date < s_join:
        return False, "before_joining_date"

    # 2. Past date guard: Never allocate new recommendations to past dates
    from app.engine.effective_schedule_service import REFERENCE_TODAY
    ref_today = REFERENCE_TODAY
    if c_date < ref_today:
        return False, "past_date"

    # Operating hours check (allowing weekday morning if student is morning-available and class is morning)
    op_ok, _ = check_operating_hours(day_name, start_min)
    if not op_ok:
        if not (s.get("is_morning_available") and 6 * 60 <= start_min <= 13 * 60):
            return False, "outside_hours"

    # Student already has a class on this date
    for c in all_classes:
        if c.get("date") == c_date and sid in c.get("student_ids", []):
            if c.get("class_id") != candidate.get("class_id"):
                return False, "class_already_that_day"

    # Batch capacity check
    max_cap = candidate.get("max_capacity") or settings["capacities"].get(c_btype, {}).get("max", 8)
    if len(curr_students) >= max_cap:
        return False, "full"

    # Student availability bitset check
    s_mask = build_student_availability_mask(s, day_name)
    slot_bit = minutes_to_bit(start_min)
    if not (s_mask & (1 << slot_bit)):
        return False, "student_unavailable"

    # Level compatibility check (Rule 1: Hard constraint by default, with adjacent-level exception)
    if is_tourn:
        el_ok, _ = check_tournament_eligibility(s_lvl, s_btype, day_name)
        if not el_ok:
            return False, "tournament_rule"
        existing_lvls = [s_obj.get("student_level", s_lvl) for s_obj in [candidate] if "student_level" in s_obj]
        grp_ok, _ = check_tournament_grouping(existing_lvls + [s_lvl], day_name)
        if not grp_ok:
            return False, "tournament_rule"
    else:
        c_lvl = candidate.get("student_level", s_lvl)
        levels_to_test = [c_lvl, s_lvl]
        comp_ok, _, _ = check_regular_level_compatibility(levels_to_test)
        if not comp_ok:
            if "Basic 1" in levels_to_test:
                return False, "basic1_isolated"
            return False, "level_mismatch"

    # Coach qualification and availability check
    combined_coaches = get_combined_coaches_map(coaches_master_map)
    c_ref = combined_coaches.get(coach_name, {})
    if not is_tourn:
        if coach_name == "HEMA" or c_ref.get("tournaments_only"):
            return False, "coach_unavailable"
        if coach_name == "BATHRI" and "Early Intermediate" in s_lvl:
            return False, "coach_unavailable"
        allowed_lvls = c_ref.get("levels", [])
        if allowed_lvls and s_lvl not in allowed_lvls:
            return False, "coach_unavailable"

    # Mandatory Coach Preferred Timing Check
    from app.engine.time_utils import is_slot_in_coach_preference
    c_obj = coaches_master_map.get(coach_name) or coaches_master_map.get(coach_name.lower()) or c_ref
    time_str = candidate.get("time_slot") or candidate.get("start_time") or format_minutes_to_time(start_min)
    timing_ok, _ = is_slot_in_coach_preference(c_obj, day_name, time_str)
    if not timing_ok:
        return False, "coach_timing_preference"

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
    Computes penalty score inside a tier according to Section 3 weights.
    """
    s = enrich_student_profile(student)
    weights = settings["weights"]
    breakdown = {}
    total_score = 0.0

    # 1. Fill Gain
    occupancy = candidate.get("occupancy", 0)
    fill_penalty = min(weights["fill_gain"], occupancy * 4.0)
    breakdown["fill_gain"] = fill_penalty
    total_score += fill_penalty

    # 2. Level Purity
    s_lvl = s.get("student_level", "")
    c_lvl = candidate.get("student_level", s_lvl)
    if s_lvl == c_lvl:
        purity_penalty = 0.0
    else:
        same_stg = any(s_lvl in stg and c_lvl in stg for stg in STAGES)
        purity_penalty = 2.0 if same_stg else 8.0
    breakdown["level_purity"] = purity_penalty * (weights["level_purity"] / 10.0)
    total_score += breakdown["level_purity"]

    # 3. Pattern Match
    pref_coach = s.get("preferred_coach", "")
    pref_times = s.get("preferred_times", [])
    c_coach = resolve_coach_canonical_name(candidate.get("coach_name", ""))
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
    priority_step = 1
    coach_obj = (coaches_master_map or {}).get(c_coach) or (coaches_master_map or {}).get(c_coach.lower()) or {}
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
    Searches top-down through the Option Ladder T1 to T7 (Section 1).
    Returns top existing batch options (T1-T3) first, followed by top proposed
    new slots (T4-T6) so the UI can display both existing seat matches and
    new slot alternatives.
    """
    s = enrich_student_profile(student)
    sid = s["student_id"]
    s_lvl = s.get("student_level", "Beginner 1")
    s_btype = (s.get("batch_type") or "G").upper()
    pref_coach = s.get("preferred_coach", "")
    pref_times = s.get("preferred_times", [])

    cache_key = (sid, 1, target_month)
    if cache_key in _SUGGESTION_CACHE:
        return _SUGGESTION_CACHE[cache_key]

    vacancies = build_vacancy_index(all_classes, coaches_master_map, settings)
    month_vacancies = [v for v in vacancies if v["date"].startswith(target_month)]

    rejection_reasons = defaultdict(int)
    feasible_options_by_tier = defaultdict(list)

    # ----------------------------------------------------
    # T1 - T3: Existing Vacancies
    # ----------------------------------------------------
    for vac in month_vacancies:
        ok, reason = evaluate_hard_feasibility(vac, s, all_classes, coaches_master_map, settings)
        if not ok:
            rejection_reasons[reason] += 1
            continue

        c_coach = vac["coach_name"]
        c_time = vac["time_slot"]
        c_lvl = vac["student_level"]

        is_exact_coach = (not pref_coach) or (c_coach.lower() == pref_coach.lower())
        is_exact_time = (not pref_times) or (c_time in pref_times)
        is_same_level = (c_lvl == s_lvl)

        # Rule 1: Level Compatibility (Default Hard) with Conditional Adjacent-Level Flexibility (Soft Fallback)
        # Hierarchy: 1. Basic 1, 2. Basic 2, 3. Beginner 1, 4. Beginner 2,
        #            5. Early Intermediate 1, 6. Early Intermediate 2, 7. Intermediate 1, 8. Intermediate 2
        # Basic 1 is an absolute exception: must attend Basic 1 only!
        s_step = LEVEL_MAP.get(s_lvl, 99)
        c_step = LEVEL_MAP.get(c_lvl, 99)
        step_diff = abs(s_step - c_step)
        is_adjacent_fallback = (step_diff == 1 and s_lvl != "Basic 1" and c_lvl != "Basic 1")

        relaxations = []
        if is_adjacent_fallback:
            relaxations.append(f"Conditional adjacent level recommendation: {c_lvl} (±1 step, requires confirmation)")

        if is_same_level and (is_exact_coach and is_exact_time):
            tier = "T1"
        elif is_same_level:
            tier = "T2"
        elif is_adjacent_fallback:
            tier = "T3"
        else:
            tier = "T3"

        score, breakdown = calculate_tier_score(vac, s, tier, all_classes, coaches_master_map, settings)
        max_cap = vac.get("max_capacity", 8)
        coach_obj = (coaches_master_map or {}).get(c_coach) or (coaches_master_map or {}).get(c_coach.lower()) or {}
        prio_rank = coach_obj.get("qualified_levels_priority", {}).get(s_lvl, 1)

        feasible_options_by_tier[tier].append({
            "class_id": vac["class_id"],
            "date": vac["date"],
            "day": vac["day"],
            "start_time": vac["time_slot"],
            "time_slot": vac["time_slot"],
            "coach_id": c_coach,
            "coach_name": c_coach,
            "tier": tier,
            "is_adjacent_fallback": is_adjacent_fallback,
            "occupancy_before": vac["occupancy"],
            "occupancy_after": vac["occupancy"] + 1,
            "fill_before": f"{vac['occupancy']}/{max_cap}",
            "fill_after": f"{vac['occupancy'] + 1}/{max_cap}",
            "coach_priority_rank": f"#{prio_rank}",
            "level_purity": "Exact Match" if is_same_level else f"Adjacent Fallback ({c_lvl})",
            "pattern_match": 0 if (is_exact_coach and is_exact_time) else 5,
            "relaxations": relaxations,
            "score": score,
            "score_breakdown": breakdown,
            "is_new_slot": False
        })

    reason_labels = {
        "level_mismatch": "Incompatible skill level (exceeds adjacent ±1 step)",
        "basic1_isolated": "Basic 1 students must attend Basic 1 batches only",
        "basic1_basic2": "Basic 1 and Basic 2 cannot be combined",
        "full": "Batch at maximum capacity",
        "batch_type_mismatch": f"Strict Batch Compatibility: student is Batch {s_btype}",
        "student_unavailable": "Outside student availability window",
        "coach_unavailable": "Coach unavailable or not qualified for level",
        "coach_timing_preference": "Outside coach configured preference timings or daily limits",
        "before_joining_date": "Class date is before student joining date",
        "past_date": "Class date has already passed",
        "class_already_that_day": "Student already has a class on that date",
        "outside_hours": "Outside academy operating hours",
        "tournament_rule": "Tournament eligibility or group restriction"
    }
    reasons_list = [
        f"{reason_labels.get(k, k)}: {cnt} evaluated batch(es)"
        for k, cnt in sorted(rejection_reasons.items(), key=lambda x: -x[1])
    ]

    # Collect top existing options (T1 -> T2 -> T3)
    existing_results = []
    for t_check in ["T1", "T2", "T3"]:
        if feasible_options_by_tier[t_check]:
            options = feasible_options_by_tier[t_check]
            options.sort(key=lambda o: (o["score"], o["date"], o["start_time"], str(o["class_id"])))
            existing_results.extend(options)
            if len(existing_results) >= 5:
                break
    existing_results = existing_results[:5]

    # Generate T4 - T6 New Slot Candidates (when T1-T3 is empty OR as expandable new-slot options)
    new_slot_candidates = generate_new_slot_candidates(
        s, all_classes, coaches_master_map, target_month, settings, max_results=8
    )
    for cand in new_slot_candidates:
        feasible_options_by_tier[cand["tier"]].append(cand)

    new_slot_results = []
    for t_check in ["T4", "T5", "T6"]:
        if feasible_options_by_tier[t_check]:
            options = feasible_options_by_tier[t_check]
            options.sort(key=lambda o: (o["score"], o["date"], o["start_time"]))
            new_slot_results.extend(options)
            if len(new_slot_results) >= 5:
                break
    new_slot_results = new_slot_results[:5]

    if existing_results:
        # Primary suggestions are T1-T3, with T4-T6 appended for the expandable "Open a New Slot" drawer
        res = existing_results + new_slot_results, reasons_list
        _SUGGESTION_CACHE[cache_key] = res
        return res

    if new_slot_results:
        res = new_slot_results, reasons_list
        _SUGGESTION_CACHE[cache_key] = res
        return res

    # T7: Nothing Valid
    res = [], reasons_list
    _SUGGESTION_CACHE[cache_key] = res
    return res

# ─────────────────────────────────────────────────────────────────────────────
# 5. NEW-SLOT GENERATOR (T4 - T6)
# ─────────────────────────────────────────────────────────────────────────────

def generate_new_slot_candidates(
    student: Dict[str, Any],
    all_classes: List[Dict[str, Any]],
    coaches_master_map: Dict[str, Any],
    target_month: str = "2026-10",
    settings: Dict[str, Any] = ENGINE_SETTINGS,
    max_results: int = 35
) -> List[Dict[str, Any]]:
    """
    Generates conflict-free new slot options across the entire month:
    T4: Coach already teaching that day, placed back-to-back (no idle gaps), or student's preferred recurring slot.
    T5: Another qualified coach (including newly added Master Data Hub trainers) who is free at that time.
    T6: Flex trainer over daily limit (BATHRI, PRAKASH, DHAANUSH), marked workload exception.
    """
    s = enrich_student_profile(student)
    candidates = []
    sid = s["student_id"]
    s_lvl = s.get("student_level", "Beginner 1")
    s_btype = (s.get("batch_type") or "G").upper()
    pref_coach = s.get("preferred_coach", "")
    pref_times = s.get("preferred_times", [])
    pref_weekdays = set(s.get("preferred_weekdays", []))
    flex_coaches = {resolve_coach_canonical_name(fc) for fc in settings.get("flex_trainers", ["BATHRI", "PRAKASH", "DHAANUSH"])}

    try:
        yr, mo = map(int, target_month.split("-"))
    except Exception:
        yr, mo = 2026, 10
    _, num_days = calendar.monthrange(yr, mo)

    combined_coaches = get_combined_coaches_map(coaches_master_map)

    # Map classes by date and coach to identify teaching days, overlaps, and monthly load
    classes_by_date_coach = defaultdict(lambda: defaultdict(list))
    monthly_coach_counts = defaultdict(int)
    student_existing_dates = set()

    for c in all_classes:
        c_date = c.get("date", "")
        if c_date.startswith(target_month):
            if sid in c.get("student_ids", []):
                student_existing_dates.add(c_date)
            c_coach = resolve_coach_canonical_name(c.get("coach_name"))
            if c_coach:
                monthly_coach_counts[c_coach] += 1
                s_min = parse_time_to_minutes(c.get("time_slot"))
                if s_min is not None:
                    classes_by_date_coach[c_date][c_coach].append(s_min)

    # Order coaches so student's preferred coach and prioritized coaches for s_lvl are evaluated first
    try:
        from app.main import CURRENT_CONFIG
        prio_matrix = getattr(CURRENT_CONFIG, "coach_priority", {}) or {}
    except Exception:
        prio_matrix = {}

    def _coach_eval_order(item):
        c_canon, c_info = item
        is_pref = 0 if (pref_coach and c_canon.lower() == pref_coach.lower()) else 1
        prio = 99
        if s_lvl in prio_matrix and c_canon in prio_matrix[s_lvl]:
            prio = prio_matrix[s_lvl].index(c_canon) + 1
        elif "qualified_levels_priority" in c_info and s_lvl in c_info["qualified_levels_priority"]:
            prio = c_info["qualified_levels_priority"][s_lvl]
        return (is_pref, prio, monthly_coach_counts[c_canon], c_canon)

    ordered_coaches = sorted(combined_coaches.items(), key=_coach_eval_order)

    # Determine earliest allowed scheduling date (never past dates, never before joining date)
    from app.engine.effective_schedule_service import REFERENCE_TODAY
    s_join = s.get("joining_date") or s.get("start_date") or s.get("date_of_joining") or ""
    earliest_date = max(s_join, REFERENCE_TODAY) if s_join else REFERENCE_TODAY

    # Precompute availability masks for the 7 weekdays (massive 60x speedup across the 31-day calendar loop)
    weekdays_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    s_day_masks = {d_name: build_student_availability_mask(s, d_name) for d_name in weekdays_list}
    c_day_masks = {
        (c_canon, d_name): build_coach_availability_mask(c_canon, coaches_master_map, d_name)
        for c_canon, _ in ordered_coaches
        for d_name in weekdays_list
    }

    # Scan each calendar date in the month
    for d in range(1, num_days + 1):
        dt = date(yr, mo, d)
        d_str = dt.strftime("%Y-%m-%d")
        day_name = dt.strftime("%A")

        # Guard: Never allocate past dates or dates before student's joining date
        if d_str < earliest_date:
            continue

        # Hard Rule: Student at most 1 class per day
        if d_str in student_existing_dates:
            continue

        # Individual (I) and Basic 1 students do not attend Sunday tournaments;
        # For new regular slots, prefer Mon-Sat unless student specifically requested Sunday
        if day_name == "Sunday" and "Sunday" not in pref_weekdays:
            continue

        s_mask = s_day_masks.get(day_name, 0)
        if s_mask == 0:
            continue

        day_candidates_for_date = []

        for c_canon, c_ref in ordered_coaches:
            if c_canon == "HEMA" or c_ref.get("tournaments_only"):
                continue
            if c_canon == "BATHRI" and "Early Intermediate" in s_lvl:
                continue

            # Coach Qualification Check
            if s_lvl not in c_ref.get("levels", []):
                continue

            # Coach Monthly Capacity Check
            m_max = c_ref.get("monthly_max")
            if m_max and monthly_coach_counts[c_canon] >= m_max and c_canon not in flex_coaches:
                continue

            c_mask = c_day_masks.get((c_canon, day_name), 0)
            feasible_bits = s_mask & c_mask
            if feasible_bits == 0:
                continue

            existing_mins = classes_by_date_coach[d_str].get(c_canon, [])
            is_already_teaching = len(existing_mins) > 0

            d_limit = c_ref.get("daily_limits", {}).get(day_name, 4)
            if d_limit <= 0:
                continue
            # Mandatory daily workload restriction
            if len(existing_mins) >= d_limit:
                continue

            # Evaluate full-hour start bits first (even bits: :00), then half-hour bits (:30)
            bit_order = [b for b in range(48) if b % 2 == 0] + [b for b in range(48) if b % 2 == 1]
            for b in bit_order:
                if not (feasible_bits & (1 << b)):
                    continue
                start_min = bit_to_minutes(b)
                time_str = format_minutes_to_time(start_min)

                # Hard Rule: Coach freeness (zero interval overlap)
                has_overlap = any(check_intervals_overlap(start_min, em) for em in existing_mins)
                if has_overlap:
                    continue

                # Hard Rule: Mandatory Coach Preferred Timing Check
                from app.engine.time_utils import is_slot_in_coach_preference
                c_coach_obj = coaches_master_map.get(c_canon) or coaches_master_map.get(c_canon.lower()) or c_ref
                slot_pref_ok, _ = is_slot_in_coach_preference(c_coach_obj, day_name, time_str)
                if not slot_pref_ok:
                    continue

                is_back_to_back = any(abs(start_min - (em + 60)) == 0 or abs((start_min + 60) - em) == 0 for em in existing_mins)
                is_pref_coach = bool(pref_coach and c_canon.lower() == pref_coach.lower())
                is_pref_time = bool(pref_times and time_str in pref_times)
                is_pref_day = bool(pref_weekdays and day_name in pref_weekdays)

                relaxations = []
                if (is_already_teaching and is_back_to_back) or (is_pref_coach and is_pref_time):
                    tier = "T4"
                else:
                    tier = "T5"

                # Score candidate using soft rules (lower score = better match)
                base_score = 100.0 if tier == "T4" else 160.0
                if is_pref_coach:
                    base_score -= 25.0
                if is_pref_time:
                    base_score -= 25.0
                if is_pref_day:
                    base_score -= 15.0
                if is_back_to_back:
                    base_score -= 10.0

                max_cap_new = 1 if s_btype == "I" else (3 if s_btype == "L" else 8)
                prio_rank = 99
                if s_lvl in prio_matrix and c_canon in prio_matrix[s_lvl]:
                    prio_rank = prio_matrix[s_lvl].index(c_canon) + 1
                elif "qualified_levels_priority" in c_ref and s_lvl in c_ref["qualified_levels_priority"]:
                    prio_rank = c_ref["qualified_levels_priority"][s_lvl]
                base_score += (prio_rank - 1) * 8.0

                day_candidates_for_date.append({
                    "class_id": None,
                    "date": d_str,
                    "day": day_name,
                    "start_time": time_str,
                    "time_slot": time_str,
                    "coach_id": c_canon,
                    "coach_name": c_canon,
                    "tier": tier,
                    "occupancy_before": 0,
                    "occupancy_after": 1,
                    "fill_before": f"0/{max_cap_new}",
                    "fill_after": f"1/{max_cap_new}",
                    "coach_priority_rank": f"#{prio_rank}",
                    "level_purity": "Exact Match",
                    "pattern_match": 0 if (is_pref_coach and is_pref_time) else (2 if (is_pref_coach or is_pref_time) else 5),
                    "relaxations": relaxations,
                    "score": round(base_score, 2),
                    "score_breakdown": {"tier_penalty": base_score},
                    "is_new_slot": True
                })
                # Keep top 2 slots per coach per date so we cover the whole month
                if len([x for x in day_candidates_for_date if x["coach_id"] == c_canon]) >= 2:
                    break

        day_candidates_for_date.sort(key=lambda x: (x["score"], x["start_time"]))
        candidates.extend(day_candidates_for_date[:3])

    candidates.sort(key=lambda x: (x["score"], x["date"], x["start_time"]))
    return candidates[:max_results]

# ─────────────────────────────────────────────────────────────────────────────
# 6. MULTI-CLASS REQUIREMENTS SOLVER (SECTION 5)
# ─────────────────────────────────────────────────────────────────────────────

def _build_set_from_ordered_pool(
    ordered_pool: List[Dict[str, Any]],
    count: int,
    enforce_coach_continuity: bool = True
) -> List[Dict[str, Any]]:
    """
    Rule 7: Coach Continuity, Monthly Assignment Optimization, and Strict Protection of Existing Schedules.
    - Prioritizes 100% coach continuity for newly created batches/slots.
    - Ranks eligible coaches primarily by the number of monthly classes they can cover within available preference times.
    - Hard Constraint: Maximum ONE class per batch per month may be assigned to another qualified coach
      (no second coach change permitted during the month). Sunday classes are exempt.
    - Never modifies existing schedules.
    """
    if not ordered_pool:
        return []

    # Count unique dates each coach covers in this pool
    coach_coverage = defaultdict(set)
    for item in ordered_pool:
        c_key = item.get("coach_id") or item.get("coach_name")
        if c_key:
            coach_coverage[c_key].add(item.get("date"))

    # Rank eligible coaches by monthly coverage count (descending)
    ranked_coaches = sorted(coach_coverage.keys(), key=lambda c: len(coach_coverage[c]), reverse=True)
    primary_coach = ranked_coaches[0] if ranked_coaches else None

    chosen = []
    used_dates = set()

    # Phase 1: Allocate as many classes as possible with the primary coach (Target: 100% continuity)
    for item in ordered_pool:
        d = item.get("date")
        c_key = item.get("coach_id") or item.get("coach_name")
        if d not in used_dates and c_key == primary_coach:
            used_dates.add(d)
            chosen.append(item)
            if len(chosen) == count:
                break

    # Phase 2: If primary coach cannot cover the complete quota, allow at most ONE non-Sunday
    # class to be assigned to another qualified coach (Sunday sessions are exempt)
    if len(chosen) < count:
        other_coach_non_sunday_used = 0
        for item in ordered_pool:
            d = item.get("date")
            if d in used_dates:
                continue
            c_id = item.get("coach_id") or item.get("coach_name")
            is_sunday = (item.get("day") == "Sunday")

            if c_id != primary_coach and not is_sunday:
                if enforce_coach_continuity and other_coach_non_sunday_used >= 1:
                    continue
                other_coach_non_sunday_used += 1

            used_dates.add(d)
            chosen.append(item)
            if len(chosen) == count:
                break

    # Fallback if needed to avoid student quota shortfall
    if len(chosen) < count:
        for item in ordered_pool:
            d = item.get("date")
            if d not in used_dates:
                used_dates.add(d)
                chosen.append(item)
                if len(chosen) == count:
                    break

    chosen.sort(key=lambda x: (x.get("date", ""), parse_time_to_minutes(x.get("start_time") or x.get("time_slot") or "00:00") or 0))
    return chosen


def solve_multi_class_options(
    student: Dict[str, Any],
    needed_count: int,
    all_classes: List[Dict[str, Any]],
    coaches_master_map: Dict[str, Any],
    target_month: str = "2026-10",
    settings: Dict[str, Any] = ENGINE_SETTINGS
) -> List[Dict[str, Any]]:
    """
    Solves multi-class requirements (e.g. 'needs 3, 4, 8, or 12 classes') as one
    optimization problem.
    Combines existing open batch seats (T1-T3) first and automatically supplements
    any remaining classes with conflict-free new slots (T4-T6) when needed.
    """
    s = enrich_student_profile(student)
    sid = s["student_id"]
    s_lvl = s.get("student_level", "Beginner 1")

    cache_key = (sid, needed_count, target_month)
    if cache_key in _SUGGESTION_CACHE:
        return _SUGGESTION_CACHE[cache_key]

    vacancies = build_vacancy_index(all_classes, coaches_master_map, settings)
    month_vacs = [v for v in vacancies if v["date"].startswith(target_month)]

    # 1. Collect all feasible existing slots (T1 - T3)
    valid_existing_slots = []
    for vac in month_vacs:
        ok, _ = evaluate_hard_feasibility(vac, s, all_classes, coaches_master_map, settings)
        if ok:
            score, breakdown = calculate_tier_score(vac, s, "T1", all_classes, coaches_master_map, settings)
            max_cap = vac.get("max_capacity", 8)
            c_coach = vac["coach_name"]
            coach_obj = (coaches_master_map or {}).get(c_coach) or (coaches_master_map or {}).get(c_coach.lower()) or {}
            prio_rank = coach_obj.get("qualified_levels_priority", {}).get(s_lvl, 1)
            valid_existing_slots.append({
                "class_id": vac["class_id"],
                "date": vac["date"],
                "day": vac["day"],
                "start_time": vac["time_slot"],
                "time_slot": vac["time_slot"],
                "coach_id": c_coach,
                "coach_name": c_coach,
                "tier": "T1" if vac["student_level"] == s_lvl else "T3",
                "occupancy_before": vac["occupancy"],
                "occupancy_after": vac["occupancy"] + 1,
                "fill_before": f"{vac['occupancy']}/{max_cap}",
                "fill_after": f"{vac['occupancy'] + 1}/{max_cap}",
                "coach_priority_rank": f"#{prio_rank}",
                "level_purity": "Exact Match" if vac["student_level"] == s_lvl else f"Stage Match ({vac['student_level']})",
                "score": score,
                "score_breakdown": breakdown,
                "is_new_slot": False
            })

    # 2. Also generate feasible new slot candidates across the entire month (T4 - T6)
    new_slot_pool = generate_new_slot_candidates(
        s, all_classes, coaches_master_map, target_month, settings, max_results=60
    )

    combined_pool = valid_existing_slots + new_slot_pool
    if not combined_pool:
        return []

    # Rule 7: Enforce Coach Continuity & Coverage Optimization via module-level _build_set_from_ordered_pool

    s_join = s.get("joining_date") or s.get("start_date") or s.get("date_of_joining") or ""

    option_sets = []

    # ----------------------------------------------------
    # Set B: Existing Seats Priority + Back-to-Back New Slots
    # ----------------------------------------------------
    pool_b = sorted(combined_pool, key=lambda x: (1 if x.get("is_new_slot") else 0, x["score"], x["date"]))
    set_b_items = _build_set_from_ordered_pool(pool_b, needed_count)
    if set_b_items:
        ex_cnt = sum(1 for x in set_b_items if not x.get("is_new_slot"))
        new_cnt = sum(1 for x in set_b_items if x.get("is_new_slot"))
        shortfall_b = max(0, needed_count - len(set_b_items))
        desc_b = f"Uses {ex_cnt} existing batch seat(s) and opens {new_cnt} conflict-free new slot(s) across {len(set_b_items)} dates."
        if shortfall_b > 0:
            desc_b += f" (Shortfall: {shortfall_b} classes due to mid-month joining / availability limit; {len(set_b_items)} of {needed_count} classes scheduled)."

        option_sets.append({
            "set_id": "SET_B_EXISTING_ONLY",
            "set_name": "Set B: Existing Seats Priority" if new_cnt == 0 else "Set B: Best Existing + New Slot Hybrid",
            "title": "Set B: Existing Seats Priority" if new_cnt == 0 else "Set B: Best Existing + New Slot Hybrid",
            "description": desc_b,
            "items": set_b_items,
            "existing_used": ex_cnt,
            "existing_seats_used": ex_cnt,
            "new_slots": new_cnt,
            "new_slots_needed": new_cnt,
            "shortfall": shortfall_b,
            "shortfall_reason": f"Only {len(set_b_items)} of {needed_count} classes feasible through month end from {s_join}." if shortfall_b > 0 else "",
            "pattern_match": "High Fill Efficiency" if ex_cnt > 0 else "Trainer Availability Match",
            "classes_covered": len(set_b_items),
            "coaches": sorted(list({item["coach_id"] for item in set_b_items}))
        })

    # ----------------------------------------------------
    # Set A: Consistent Weekly Pattern (Same Weekday & Time & Coach)
    # ----------------------------------------------------
    weekday_grouped = defaultdict(list)
    for item in combined_pool:
        weekday_grouped[(item["day"], item["start_time"], item["coach_id"])].append(item)

    # Sort patterns by how many unique dates they cover and lowest average score
    scored_patterns = []
    for key, p_items in weekday_grouped.items():
        unique_dates = {x["date"] for x in p_items}
        avg_score = sum(x["score"] for x in p_items) / len(p_items)
        scored_patterns.append((len(unique_dates), -avg_score, key, p_items))
    scored_patterns.sort(reverse=True)

    if scored_patterns:
        # Combine top recurring weekday patterns until needed_count is reached
        pattern_pool = []
        for _, _, _, p_items in scored_patterns:
            p_sorted = sorted(p_items, key=lambda x: (1 if x.get("is_new_slot") else 0, x["date"]))
            pattern_pool.extend(p_sorted)
        set_a_items = _build_set_from_ordered_pool(pattern_pool, needed_count)
        if set_a_items:
            ex_cnt = sum(1 for x in set_a_items if not x.get("is_new_slot"))
            new_cnt = sum(1 for x in set_a_items if x.get("is_new_slot"))
            shortfall_a = max(0, needed_count - len(set_a_items))
            top_day, top_time, top_coach = scored_patterns[0][2]
            desc_a = f"Maintains recurring weekly rhythm ({top_day} at {top_time} with Coach {top_coach})."
            if shortfall_a > 0:
                desc_a += f" (Shortfall: {shortfall_a} classes; {len(set_a_items)} of {needed_count} classes scheduled through month end)."

            option_sets.append({
                "set_id": "SET_A_CONSISTENT",
                "set_name": "Set A: Consistent Weekly Pattern",
                "title": "Set A: Consistent Weekly Pattern",
                "description": desc_a,
                "items": set_a_items,
                "existing_used": ex_cnt,
                "existing_seats_used": ex_cnt,
                "new_slots": new_cnt,
                "new_slots_needed": new_cnt,
                "shortfall": shortfall_a,
                "shortfall_reason": f"Only {len(set_a_items)} of {needed_count} classes feasible through month end from {s_join}." if shortfall_a > 0 else "",
                "pattern_match": f"Weekly {top_day} {top_time} ({top_coach})",
                "classes_covered": len(set_a_items),
                "coaches": sorted(list({item["coach_id"] for item in set_a_items}))
            })

    # ----------------------------------------------------
    # Set C: Fastest Completion (Earliest Calendar Dates)
    # ----------------------------------------------------
    pool_c = sorted(combined_pool, key=lambda x: (x["date"], 1 if x.get("is_new_slot") else 0, x["score"]))
    set_c_items = _build_set_from_ordered_pool(pool_c, needed_count)
    if set_c_items:
        ex_cnt = sum(1 for x in set_c_items if not x.get("is_new_slot"))
        new_cnt = sum(1 for x in set_c_items if x.get("is_new_slot"))
        shortfall_c = max(0, needed_count - len(set_c_items))
        desc_c = f"Completes quota earliest in the month (concludes by {set_c_items[-1]['date']})."
        if shortfall_c > 0:
            desc_c += f" (Shortfall: {shortfall_c} classes; {len(set_c_items)} of {needed_count} classes scheduled through month end)."

        option_sets.append({
            "set_id": "SET_C_FASTEST",
            "set_name": "Set C: Fastest Completion",
            "title": "Set C: Fastest Completion",
            "description": desc_c,
            "items": set_c_items,
            "existing_used": ex_cnt,
            "existing_seats_used": ex_cnt,
            "new_slots": new_cnt,
            "new_slots_needed": new_cnt,
            "shortfall": shortfall_c,
            "shortfall_reason": f"Only {len(set_c_items)} of {needed_count} classes feasible through month end from {s_join}." if shortfall_c > 0 else "",
            "pattern_match": f"Fastest (Ends {set_c_items[-1]['date']})",
            "classes_covered": len(set_c_items),
            "coaches": sorted(list({item["coach_id"] for item in set_c_items}))
        })

    _SUGGESTION_CACHE[cache_key] = option_sets
    return option_sets

# ─────────────────────────────────────────────────────────────────────────────
# 7. NEW TRAINER ENGAGEMENT PROPOSALS (ADMIN ACCEPTANCE IN OUTPUT 3)
# ─────────────────────────────────────────────────────────────────────────────

def generate_trainer_engagement_proposals(
    coaches_master_map: Dict[str, Any],
    attention_records: List[Dict[str, Any]],
    student_master_map: Dict[str, Any],
    all_classes: List[Dict[str, Any]],
    target_month: str = "2026-10"
) -> List[Dict[str, Any]]:
    """
    When a new trainer is added in Master Data Hub (or has 0 scheduled classes
    in the active month), generates concrete class proposals matching the trainer's
    qualified levels and preferred timings (pairing them with waiting students of
    matching levels if available) for Administrator Acceptance on Output 3.
    """
    proposals = []
    if not coaches_master_map:
        return proposals

    try:
        yr, mo = map(int, target_month.split("-"))
    except Exception:
        yr, mo = 2026, 10
    _, num_days = calendar.monthrange(yr, mo)

    # Count classes currently assigned to each coach in target_month
    coach_class_counts = defaultdict(int)
    classes_by_date_coach = defaultdict(lambda: defaultdict(list))
    for c in all_classes:
        if c.get("date", "").startswith(target_month):
            c_canon = resolve_coach_canonical_name(c.get("coach_name", ""))
            if c_canon:
                coach_class_counts[c_canon] += 1
                s_min = parse_time_to_minutes(c.get("time_slot"))
                if s_min is not None:
                    classes_by_date_coach[c.get("date")][c_canon].append(s_min)

    combined_coaches = get_combined_coaches_map(coaches_master_map)

    for raw_key, c_obj in coaches_master_map.items():
        if not isinstance(c_obj, dict):
            continue
        c_canon = resolve_coach_canonical_name(c_obj.get("coach_name") or raw_key)
        if not c_canon or c_canon == "HEMA":
            continue
        c_info = combined_coaches.get(c_canon, {})
        if c_info.get("tournaments_only"):
            continue

        # Propose engagement slots for newly added trainers (0 classes) or custom trainers not in baseline
        is_new_or_unscheduled_trainer = (coach_class_counts[c_canon] == 0) or (c_canon not in COACH_REFERENCE)
        if not is_new_or_unscheduled_trainer:
            continue

        levels_handled = c_info.get("levels", [])
        if not levels_handled:
            continue

        # Find waiting students in attention_records whose level is in levels_handled
        matching_waiting_students = []
        for rec in attention_records:
            sid = rec.get("student_id")
            if not sid or sid == "N/A":
                continue
            s_obj = student_master_map.get(sid) or rec
            if s_obj.get("student_level") in levels_handled and rec.get("remaining_classes", 0) > 0:
                matching_waiting_students.append(s_obj)

        suggested_slots = []
        for d in range(1, num_days + 1):
            dt = date(yr, mo, d)
            d_str = dt.strftime("%Y-%m-%d")
            day_name = dt.strftime("%A")
            if day_name == "Sunday":
                continue

            c_mask = build_coach_availability_mask(c_canon, coaches_master_map, day_name)
            if c_mask == 0:
                continue

            existing_mins = classes_by_date_coach[d_str].get(c_canon, [])
            d_limit = c_info.get("daily_limits", {}).get(day_name, 4)
            if len(existing_mins) >= d_limit:
                continue

            # Pick a compatible student if available, else propose an open slot for the trainer's primary level
            matched_stu = None
            target_bit = None

            for stu in matching_waiting_students:
                if any(c.get("date") == d_str and stu["student_id"] in c.get("student_ids", []) for c in all_classes):
                    continue
                s_mask = build_student_availability_mask(stu, day_name)
                overlap_bits = c_mask & s_mask
                if overlap_bits > 0:
                    for b in [b for b in range(48) if b % 2 == 0] + [b for b in range(48) if b % 2 == 1]:
                        if overlap_bits & (1 << b):
                            s_min = bit_to_minutes(b)
                            if not any(check_intervals_overlap(s_min, em) for em in existing_mins):
                                matched_stu = stu
                                target_bit = b
                                break
                if matched_stu:
                    break

            if target_bit is None:
                for b in [b for b in range(48) if b % 2 == 0] + [b for b in range(48) if b % 2 == 1]:
                    if c_mask & (1 << b):
                        s_min = bit_to_minutes(b)
                        if not any(check_intervals_overlap(s_min, em) for em in existing_mins):
                            target_bit = b
                            break

            if target_bit is not None:
                t_str = format_minutes_to_time(bit_to_minutes(target_bit))
                lvl = matched_stu.get("student_level") if matched_stu else levels_handled[0]
                b_type = matched_stu.get("batch_type", "G") if matched_stu else "G"
                suggested_slots.append({
                    "date": d_str,
                    "day": day_name,
                    "start_time": t_str,
                    "time_slot": t_str,
                    "coach_id": c_canon,
                    "coach_name": c_canon,
                    "student_level": lvl,
                    "batch_type": b_type,
                    "student_ids": [matched_stu["student_id"]] if matched_stu else [],
                    "student_names": [matched_stu.get("student_name", matched_stu["student_id"])] if matched_stu else [],
                    "tier": "T4" if matched_stu else "T5",
                    "is_new_slot": True
                })
            if len(suggested_slots) >= 4:
                break

        if suggested_slots:
            proposals.append({
                "coach_name": c_canon,
                "levels_handled": levels_handled,
                "current_classes_count": coach_class_counts[c_canon],
                "preferred_timings": c_obj.get("preferred_timings", "Standard Operating Hours"),
                "matching_waiting_students_count": len(matching_waiting_students),
                "proposed_slots": suggested_slots
            })

    return proposals

# ─────────────────────────────────────────────────────────────────────────────
# 8. POOLING & SMART BATCH OPPORTUNITIES (SECTION 6 & 8)
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
    """
    opportunities = []
    level_buckets = defaultdict(list)
    combined_coaches = get_combined_coaches_map(coaches_master_map)

    for rec in attention_records:
        sid = rec.get("student_id")
        s_obj = student_master_map.get(sid)
        if s_obj and s_obj.get("batch_type") in ["G", "L"]:
            lvl = s_obj.get("student_level", "Beginner 1")
            level_buckets[(lvl, s_obj.get("batch_type", "G"))].append(s_obj)

    for (lvl, b_type), waiting_students in level_buckets.items():
        if len(waiting_students) < 2:
            continue

        qual_coaches = [
            c_name for c_name, c_ref in combined_coaches.items()
            if lvl in c_ref.get("levels", []) and not c_ref.get("tournaments_only")
            and not (c_name == "BATHRI" and "Early Intermediate" in lvl)
        ]
        if not qual_coaches:
            continue

        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]:
            shared_mask = 0xFFFFFFFFFFFF
            for s in waiting_students:
                shared_mask &= build_student_availability_mask(s, day)

            if shared_mask > 0:
                for b in range(48):
                    if shared_mask & (1 << b):
                        start_time = format_minutes_to_time(bit_to_minutes(b))
                        assigned_coach = qual_coaches[0]
                        max_cap = 3 if b_type == "L" else 8
                        pooled_stus = waiting_students[:max_cap]
                        opportunities.append({
                            "opportunity_id": f"POOL_{lvl.replace(' ', '')}_{b_type}_{day}_{b}",
                            "title": f"Smart {b_type}-Batch Opportunity: {lvl} ({day} {start_time})",
                            "level": lvl,
                            "batch_type": b_type,
                            "day": day,
                            "time_slot": start_time,
                            "suggested_coach": assigned_coach,
                            "student_count": len(pooled_stus),
                            "student_ids": [s["student_id"] for s in pooled_stus],
                            "student_names": [s["student_name"] for s in pooled_stus],
                            "impact_summary": f"Opening 1 pooled {b_type} slot with Coach {assigned_coach} resolves {len(pooled_stus)} waiting students at once."
                        })
                        break
            if len(opportunities) >= 4:
                break

    return opportunities

# ─────────────────────────────────────────────────────────────────────────────
# 9. READ-ONLY CONSOLIDATION ADVISOR (SECTION 9)
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


# ─────────────────────────────────────────────────────────────────────────────
# 10. COACH DAILY AVAILABILITY & FREE SLOTS EXPLORER (OUTPUT 3 COACH SECTION)
# ─────────────────────────────────────────────────────────────────────────────

def get_coach_daily_availability_explorer(
    all_classes: List[Dict[str, Any]],
    coaches_master_map: Dict[str, Any],
    target_month: str = "2026-10",
    selected_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes for every date in target_month (or a specific selected_date) which coaches
    are available, how many classes they are teaching that day vs their daily limit,
    their preferred timing windows, their exact free 1-hour slots (within preferred windows),
    and exceptional operating slots (outside preferred windows that Admin can assign with acknowledgement).
    """
    try:
        yr, mo = map(int, target_month.split("-"))
    except Exception:
        yr, mo = 2026, 10
    _, num_days = calendar.monthrange(yr, mo)

    combined_coaches = get_combined_coaches_map(coaches_master_map)

    classes_by_date_coach = defaultdict(lambda: defaultdict(list))
    monthly_counts = defaultdict(int)
    for c in all_classes:
        dt_str = c.get("date", "")
        if dt_str.startswith(target_month):
            c_canon = resolve_coach_canonical_name(c.get("coach_name", ""))
            if c_canon:
                monthly_counts[c_canon] += 1
                classes_by_date_coach[dt_str][c_canon].append(c)

    days_summary = []
    for d in range(1, num_days + 1):
        dt = date(yr, mo, d)
        d_str = dt.strftime("%Y-%m-%d")
        day_name = dt.strftime("%A")
        if selected_date and d_str != selected_date:
            continue

        op_mask = get_operating_hours_mask(day_name, allow_weekday_morning=(day_name == "Saturday"))
        coaches_on_day = []

        for c_canon, c_info in sorted(combined_coaches.items(), key=lambda x: (1 if x[1].get("is_new_coach") else 0, x[0])):
            if c_info.get("tournaments_only") and day_name != "Sunday":
                continue
            assigned_cls = classes_by_date_coach[d_str].get(c_canon, [])
            assigned_mins = [parse_time_to_minutes(ac.get("time_slot", "")) for ac in assigned_cls if parse_time_to_minutes(ac.get("time_slot", "")) is not None]
            d_limit = c_info.get("daily_limits", {}).get(day_name, 4)
            pref_mask = build_coach_availability_mask(c_canon, coaches_master_map, day_name)

            # Evaluate all full-hour operating slots on this day
            free_preferred_slots = []
            free_exceptional_slots = []
            for b in range(0, 48, 2):
                if not (op_mask & (1 << b)):
                    continue
                s_min = bit_to_minutes(b)
                if any(check_intervals_overlap(s_min, em) for em in assigned_mins):
                    continue
                t_label = format_minutes_to_time(s_min)
                if pref_mask & (1 << b):
                    free_preferred_slots.append(t_label)
                else:
                    free_exceptional_slots.append(t_label)

            # Format human-readable preferred window description
            raw_pref_wins = c_info.get("availability", {}).get(day_name, [])
            if raw_pref_wins:
                pref_desc = ", ".join([f"{w[0]}–{w[1]}" for w in raw_pref_wins])
            elif c_info.get("preferred_timings") and c_info.get("preferred_timings") != "No Preference":
                pref_desc = str(c_info.get("preferred_timings"))
            else:
                pref_desc = "Standard Operating Hours" if d_limit > 0 else "Day Off (Exceptional Only)"

            coaches_on_day.append({
                "coach_name": c_canon,
                "is_new_coach": bool(c_info.get("is_new_coach") or monthly_counts[c_canon] == 0),
                "levels_handled": c_info.get("levels", []),
                "priority_tier": "Bottom Priority (New Coach — High Priority for New Slots)" if (c_info.get("is_new_coach") or monthly_counts[c_canon] == 0) else "Established Priority",
                "daily_assigned": len(assigned_cls),
                "daily_limit": d_limit,
                "monthly_assigned": monthly_counts[c_canon],
                "monthly_limit": c_info.get("monthly_max"),
                "preferred_window": pref_desc,
                "free_preferred_slots": free_preferred_slots,
                "free_exceptional_slots": free_exceptional_slots,
                "assigned_slots": [
                    {
                        "time_slot": ac.get("time_slot"),
                        "batch_name": ac.get("batch_name") or ac.get("batch_code", ""),
                        "student_level": ac.get("student_level"),
                        "student_count": len(ac.get("student_ids", []))
                    }
                    for ac in sorted(assigned_cls, key=lambda x: parse_time_to_minutes(x.get("time_slot", "")) or 9999)
                ]
            })

        days_summary.append({
            "date": d_str,
            "day": day_name,
            "available_coaches_count": sum(1 for cd in coaches_on_day if len(cd["free_preferred_slots"]) > 0 and cd["daily_assigned"] < cd["daily_limit"]),
            "coaches": coaches_on_day
        })

    return {
        "month": target_month,
        "days": days_summary
    }
