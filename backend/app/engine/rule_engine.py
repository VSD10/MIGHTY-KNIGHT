import re
from typing import Dict, Any, List, Tuple, Optional, Set
from datetime import datetime, date, time

# Official 8 Academy Levels (Part B1)
LEVEL_MAP = {
    "Basic 1": 1,
    "Basic 2": 2,
    "Beginner 1": 3,
    "Beginner 2": 4,
    "Early Intermediate 1": 5,
    "Early Intermediate 2": 6,
    "Intermediate 1": 7,
    "Intermediate 2": 8
}

LEVEL_BY_NUM = {v: k for k, v in LEVEL_MAP.items()}

# Stage groupings for level compatibility (Part B3)
STAGES = [
    {"Basic 1"},
    {"Basic 2"},
    {"Beginner 1", "Beginner 2"},
    {"Early Intermediate 1", "Early Intermediate 2"},
    {"Intermediate 1", "Intermediate 2"}
]

# Tournament Allowed Groups (Part C3 - Strict, no mixing)
TOURNAMENT_GROUPS = [
    {"Basic 2"},
    {"Beginner 1", "Beginner 2"},
    {"Early Intermediate 1", "Early Intermediate 2"},
    {"Intermediate 1"},
    {"Intermediate 2"} # Friday tournament only
]

# Coach Reference Seed Data (Part B7)
class _CoachReferenceDict(dict):
    def _canon(self, key):
        if not isinstance(key, str):
            return key
        k_up = key.strip().upper()
        if super().__contains__(k_up):
            return k_up
        k_low = key.strip().lower()
        for canon, data in super().items():
            if k_low == canon.lower() or k_low in [a.lower() for a in data.get("aliases", [])]:
                return canon
        return k_up

    def __getitem__(self, key):
        return super().__getitem__(self._canon(key))

    def get(self, key, default=None):
        return super().get(self._canon(key), default)

    def __contains__(self, key):
        return super().__contains__(self._canon(key))

COACH_REFERENCE = _CoachReferenceDict({
    "GURU": {
        "aliases": ["guru", "guruvanthana"],
        "levels": ["Basic 1", "Basic 2", "Beginner 1", "Beginner 2"],
        "monthly_max": None,
        "daily_limits": {"Sunday": 2, "Monday": 1, "Tuesday": 0, "Wednesday": 1, "Thursday": 0, "Friday": 1, "Saturday": 1},
        "availability": {
            "Sunday": [("08:00", "15:00")],
            "Monday": [("18:00", "21:00")],
            "Tuesday": [],
            "Wednesday": [("18:00", "21:00")],
            "Thursday": [],
            "Friday": [("18:00", "21:00")],
            "Saturday": [("18:00", "21:00")]
        },
        "is_flex": False,
        "tournaments_only": False,
        "tournament_tier": None # Excluded by default
    },
    "DHAANUSH": {
        "aliases": ["dhaanush", "dhanush"],
        "levels": ["Beginner 2", "Early Intermediate 1", "Early Intermediate 2", "Intermediate 1", "Intermediate 2"],
        "monthly_max": 90,
        "daily_limits": {"Sunday": 3, "Monday": 3, "Tuesday": 4, "Wednesday": 4, "Thursday": 4, "Friday": 4, "Saturday": 4},
        "availability": {
            "Sunday": [("08:00", "15:00")],
            "Monday": [("16:00", "21:00")],
            "Tuesday": [("16:00", "21:00")],
            "Wednesday": [("16:00", "21:00")],
            "Thursday": [("16:00", "21:00")],
            "Friday": [("16:00", "21:00")],
            "Saturday": [("16:00", "21:00")] # Operating hours cap at 21:00 (last start 20:00)
        },
        "is_flex": True,
        "tournaments_only": False,
        "tournament_tier": 2
    },
    "ARSHATH": {
        "aliases": ["arshath"],
        "levels": ["Intermediate 1", "Intermediate 2"],
        "monthly_max": 20,
        "daily_limits": {"Sunday": 3, "Monday": 0, "Tuesday": 0, "Wednesday": 0, "Thursday": 2, "Friday": 2, "Saturday": 3},
        "availability": {
            "Sunday": [("08:00", "15:00")],
            "Monday": [],
            "Tuesday": [],
            "Wednesday": [],
            "Thursday": [("17:00", "19:00")],
            "Friday": [("17:00", "19:00")],
            "Saturday": [("17:00", "21:00")]
        },
        "is_flex": False,
        "tournaments_only": False,
        "tournament_tier": 1
    },
    "SARAVANAN": {
        "aliases": ["saravanan"],
        "levels": ["Early Intermediate 2", "Intermediate 1"],
        "monthly_max": 7,
        "daily_limits": {"Sunday": 2, "Monday": 1, "Tuesday": 1, "Wednesday": 1, "Thursday": 1, "Friday": 1, "Saturday": 2},
        "availability": {
            "Sunday": [("08:00", "15:00")],
            "Monday": [("19:00", "21:00")],
            "Tuesday": [("19:00", "21:00")],
            "Wednesday": [("19:00", "21:00")],
            "Thursday": [("19:00", "21:00")],
            "Friday": [("19:00", "21:00")],
            "Saturday": [("19:00", "21:00")]
        },
        "is_flex": False,
        "tournaments_only": False,
        "tournament_tier": 2
    },
    "BATHRI": {
        "aliases": ["bathri", "bathrinath", "bathrinath k", "bathrinath k trainer", "bathri trainer", "bathri k trainer"],
        "levels": ["Basic 1", "Basic 2", "Beginner 1", "Beginner 2"], # Level 1-4 regular (NO Early Intermediate regular)
        "monthly_max": None,
        "daily_limits": {"Sunday": 4, "Monday": 4, "Tuesday": 4, "Wednesday": 4, "Thursday": 4, "Friday": 4, "Saturday": 6},
        "availability": {
            "Sunday": [("08:00", "15:00")],
            "Monday": [("06:00", "08:00"), ("10:00", "14:00"), ("16:00", "21:00")],
            "Tuesday": [("06:00", "08:00"), ("10:00", "14:00"), ("16:00", "21:00")],
            "Wednesday": [("06:00", "08:00"), ("10:00", "14:00"), ("16:00", "21:00")],
            "Thursday": [("06:00", "08:00"), ("10:00", "14:00"), ("16:00", "21:00")],
            "Friday": [("06:00", "08:00"), ("10:00", "14:00"), ("16:00", "21:00")],
            "Saturday": [("06:00", "08:00"), ("10:00", "14:00"), ("16:00", "21:00")]
        },
        "is_flex": True,
        "tournaments_only": False,
        "tournament_tier": 1
    },
    "ABINAYA": {
        "aliases": ["abinaya"],
        "levels": ["Basic 1", "Basic 2", "Beginner 1"],
        "monthly_max": 60,
        "daily_limits": {"Sunday": 4, "Monday": 2, "Tuesday": 2, "Wednesday": 2, "Thursday": 2, "Friday": 2, "Saturday": 4},
        "availability": {
            "Sunday": [("08:00", "15:00")],
            "Monday": [("08:00", "11:00"), ("19:00", "21:00")],
            "Tuesday": [("08:00", "11:00"), ("19:00", "21:00")],
            "Wednesday": [("08:00", "11:00"), ("19:00", "21:00")],
            "Thursday": [("08:00", "11:00"), ("19:00", "21:00")],
            "Friday": [("08:00", "11:00"), ("19:00", "21:00")],
            "Saturday": [("08:00", "11:00"), ("19:00", "21:00")]
        },
        "is_flex": False,
        "tournaments_only": False,
        "tournament_tier": 1
    },
    "PRAKASH": {
        "aliases": ["prakash"],
        "levels": ["Basic 1", "Basic 2", "Beginner 1", "Beginner 2", "Early Intermediate 1", "Early Intermediate 2", "Intermediate 1", "Intermediate 2"],
        "monthly_max": None,
        "daily_limits": {"Sunday": 3, "Monday": 99, "Tuesday": 99, "Wednesday": 99, "Thursday": 99, "Friday": 99, "Saturday": 99},
        "availability": {
            "Sunday": [("08:00", "14:00")],
            "Monday": [("06:00", "13:00"), ("16:00", "21:00")],
            "Tuesday": [("06:00", "13:00"), ("16:00", "21:00")],
            "Wednesday": [("06:00", "13:00"), ("16:00", "21:00")],
            "Thursday": [("06:00", "13:00"), ("16:00", "21:00")],
            "Friday": [("06:00", "13:00"), ("16:00", "21:00")],
            "Saturday": [("06:00", "13:00"), ("16:00", "21:00")]
        },
        "is_flex": True,
        "tournaments_only": False,
        "tournament_tier": 1
    },
    "MANIKANDAN": {
        "aliases": ["manikandan"],
        "levels": ["Basic 1", "Basic 2", "Beginner 1"],
        "monthly_max": None,
        "daily_limits": {"Sunday": 3, "Monday": 99, "Tuesday": 99, "Wednesday": 99, "Thursday": 99, "Friday": 99, "Saturday": 99},
        "availability": {
            "Sunday": [("08:00", "15:00")],
            "Monday": [("06:00", "08:00"), ("20:00", "21:00")],
            "Tuesday": [("06:00", "08:00"), ("20:00", "21:00")],
            "Wednesday": [("06:00", "08:00"), ("20:00", "21:00")],
            "Thursday": [("06:00", "08:00"), ("20:00", "21:00")],
            "Friday": [("06:00", "08:00"), ("20:00", "21:00")],
            "Saturday": [("06:00", "08:00"), ("20:00", "21:00")]
        },
        "is_flex": False,
        "tournaments_only": False,
        "tournament_tier": 1
    },
    "HEMA": {
        "aliases": ["hema"],
        "levels": [],
        "monthly_max": None,
        "daily_limits": {"Sunday": 5, "Monday": 0, "Tuesday": 0, "Wednesday": 0, "Thursday": 0, "Friday": 0, "Saturday": 0},
        "availability": {
            "Sunday": [("09:00", "14:30")],
            "Monday": [], "Tuesday": [], "Wednesday": [], "Thursday": [], "Friday": [], "Saturday": []
        },
        "is_flex": False,
        "tournaments_only": True,
        "tournament_tier": 1
    },
    "VIGNESH": {
        "aliases": ["vignesh"],
        "levels": ["Basic 1", "Basic 2", "Beginner 1"],
        "monthly_max": None,
        "daily_limits": {"Sunday": 3, "Monday": 4, "Tuesday": 4, "Wednesday": 4, "Thursday": 4, "Friday": 4, "Saturday": 5},
        "availability": {
            "Sunday": [("09:00", "14:30")],
            "Monday": [("06:00", "08:00"), ("16:00", "21:00")],
            "Tuesday": [("06:00", "08:00"), ("16:00", "21:00")],
            "Wednesday": [("06:00", "08:00"), ("16:00", "21:00")],
            "Thursday": [("06:00", "08:00"), ("16:00", "21:00")],
            "Friday": [("06:00", "08:00"), ("16:00", "21:00")],
            "Saturday": [("06:00", "08:00"), ("16:00", "21:00")]
        },
        "is_flex": False,
        "tournaments_only": False,
        "tournament_tier": 1
    }
})

def resolve_coach_canonical_name(coach_name: str) -> str:
    """Resolves coach name or alias to authoritative canonical name in CAPITAL."""
    if not coach_name:
        return ""
    clean = str(coach_name or "").strip().lower()
    for canon, data in COACH_REFERENCE.items():
        if clean == canon.lower() or clean in [a.lower() for a in data["aliases"]]:
            return canon.upper()
    if "bathri" in clean:
        return "BATHRI"
    if "guru" in clean:
        return "GURU"
    return coach_name.strip().upper()

def parse_time_to_minutes(time_str: str) -> Optional[int]:
    """Parses '4:30 PM', '16:30', '7:00 PM', '7 pm' into minutes from midnight (0..1439)."""
    if not time_str:
        return None
    s = str(time_str).strip()
    # Normalize formats like 7pm, 7:30pm
    s = re.sub(r'(\d+)(am|pm)', r'\1 \2', s, flags=re.IGNORECASE)
    formats = ["%I:%M %p", "%I %p", "%H:%M", "%H:%M:%S"]
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.hour * 60 + dt.minute
        except ValueError:
            pass
    # Try custom regex matching
    m = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?$', s, re.IGNORECASE)
    if m:
        hr = int(m.group(1))
        mn = int(m.group(2) or 0)
        ampm = (m.group(3) or "").upper()
        if ampm == "PM" and hr < 12:
            hr += 12
        elif ampm == "AM" and hr == 12:
            hr = 0
        return hr * 60 + mn
    return None

def format_minutes_to_time(minutes: int) -> str:
    """Formats minutes to '4:30 PM' string."""
    hr = (minutes // 60) % 24
    mn = minutes % 60
    ampm = "AM" if hr < 12 else "PM"
    disp_hr = hr % 12
    if disp_hr == 0:
        disp_hr = 12
    return f"{disp_hr}:{mn:02d} {ampm}"

def check_intervals_overlap(start1_min: int, start2_min: int, duration_min: int = 60) -> bool:
    """Real 1-hour interval overlap check (Part B4)."""
    end1_min = start1_min + duration_min
    end2_min = start2_min + duration_min
    return max(start1_min, start2_min) < min(end1_min, end2_min)

def check_operating_hours(day_name: str, start_min: int) -> Tuple[bool, str]:
    """
    Validates operating hours according to Part B4:
    - Mon – Fri: 4:00 PM – 9:00 PM (last start 8:00 PM / 480 to 1200)
    - Saturday: 6:00 AM – 2:00 PM (last start 1:00 PM / 360 to 780) AND 4:00 PM – 9:00 PM (last start 8:00 PM / 960 to 1200)
    - Sunday: 9:00 AM – 2:30 PM (last start 1:30 PM / 540 to 810)
    """
    if day_name in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        if 16 * 60 <= start_min <= 20 * 60:
            return True, ""
        return False, f"Operating hours violation: Mon-Fri operating hours are 4:00 PM – 9:00 PM (last start 8:00 PM). Class starts at {format_minutes_to_time(start_min)}."
    elif day_name == "Saturday":
        w1_ok = (6 * 60 <= start_min <= 13 * 60)
        w2_ok = (16 * 60 <= start_min <= 20 * 60)
        if w1_ok or w2_ok:
            return True, ""
        return False, f"Operating hours violation: Saturday operating windows are 6:00 AM – 2:00 PM (last start 1:00 PM) and 4:00 PM – 9:00 PM (last start 8:00 PM). Class starts at {format_minutes_to_time(start_min)}."
    elif day_name == "Sunday":
        if 9 * 60 <= start_min <= 13 * 60 + 30:
            return True, ""
        return False, f"Operating hours violation: Sunday operating hours are 9:00 AM – 2:30 PM (last start 1:30 PM). Class starts at {format_minutes_to_time(start_min)}."
    return True, ""

def is_morning_class(day_name: str, start_min: int) -> bool:
    """Any class starting before 4:00 PM on Monday to Saturday is morning/daytime (Part B4)."""
    return day_name in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"] and start_min < 16 * 60

def check_tournament_eligibility(level: str, batch_type: str, day_name: str) -> Tuple[bool, str]:
    """Checks tournament eligibility matrix (Part C2)."""
    if batch_type == "I":
        return False, "Individual batch students are never eligible for tournaments."
    
    if day_name == "Sunday":
        if level == "Basic 1":
            return False, "Basic 1 students are never eligible for Sunday tournaments (must attend regular class)."
        elif level == "Intermediate 2":
            return False, "Intermediate 2 students are never eligible for Sunday tournaments (Friday tournament only)."
        elif level in ["Basic 2", "Beginner 1", "Beginner 2", "Early Intermediate 1", "Early Intermediate 2", "Intermediate 1"]:
            return True, ""
        return False, f"Level {level} is not recognized for Sunday tournaments."
    elif day_name == "Friday":
        if level == "Intermediate 2":
            return True, ""
        return False, f"Friday tournament is strictly reserved for Intermediate 2 only (student is {level})."
    return False, f"Tournaments only operate on Sunday (all eligible levels) and Friday (Intermediate 2). Not on {day_name}."

def check_tournament_grouping(levels: List[str], day_name: str) -> Tuple[bool, str]:
    """Strict tournament grouping (Part C3). No mixing groups."""
    lvl_set = set(levels)
    if not lvl_set:
        return True, ""
    
    if day_name == "Friday":
        if lvl_set == {"Intermediate 2"}:
            return True, ""
        return False, f"Friday tournament may only contain Intermediate 2 students. Found: {list(lvl_set)}."

    for group in TOURNAMENT_GROUPS:
        if lvl_set.issubset(group):
            return True, ""
    
    return False, f"Strict tournament grouping violation: Tournament contains incompatible mixed levels: {list(lvl_set)}. Allowed groups: Basic 2 alone, Beginner 1+2, Early Int 1+2, Intermediate 1 alone."

def check_regular_level_compatibility(levels: List[str]) -> Tuple[bool, str, str]:
    """
    Level compatibility inside one regular class (Rule 1):
    Hierarchy (1 to 8):
    1: Basic 1, 2: Basic 2, 3: Beginner 1, 4: Beginner 2,
    5: Early Intermediate 1, 6: Early Intermediate 2, 7: Intermediate 1, 8: Intermediate 2.

    Rules:
    - Default hard constraint: Exact same-level matching (Preferred).
    - Basic 1 is an ABSOLUTE EXCEPTION: Basic 1 students must attend Basic 1 batches only
      and must never be assigned to another level. No other level can be assigned to Basic 1.
    - Adjacent-level flexibility (±1 level step) is an optional soft fallback recommendation
      requiring authorized confirmation (except Basic 1 which cannot be combined with anything).
    - 2 or more levels apart: Hard violation (skipping levels or non-adjacent levels strictly prohibited).
    Returns (is_valid, reason, severity: 'hard'|'soft'|'ok')
    """
    distinct = list(set(levels))
    if len(distinct) <= 1:
        return True, "Same-level batch match (Preferred)", "ok"

    nums = [LEVEL_MAP.get(l, 0) for l in distinct if l in LEVEL_MAP]
    if not nums:
        return True, "Same-level batch match (Preferred)", "ok"

    # Absolute Exception: Basic 1 students must attend Basic 1 batches only and never mixed!
    if "Basic 1" in distinct:
        return False, "Level compatibility violation (Hard): Basic 1 is an absolute exception. Basic 1 students must attend Basic 1 batches only and must never be assigned to another level.", "hard"

    min_num, max_num = min(nums), max(nums)
    step_diff = max_num - min_num

    # Hard rejection: 2 or more steps apart
    if step_diff >= 2:
        return False, f"Level compatibility violation (Hard): Levels are {step_diff} steps apart ({LEVEL_BY_NUM.get(min_num)} vs {LEVEL_BY_NUM.get(max_num)}). Combining non-adjacent levels or skipping levels is strictly prohibited.", "hard"

    # Exactly 1 step apart: permitted as conditional adjacent-level soft fallback recommendation
    return True, f"Adjacent-level combination ({', '.join(distinct)}) is permitted as an optional fallback recommendation requiring authorized confirmation.", "soft"

def validate_all_rules_for_occurrence(
    cls_dict: Dict[str, Any],
    all_classes_in_month: List[Dict[str, Any]],
    student_master_map: Dict[str, Any],
    coach_master_map: Dict[str, Any],
    is_tournament: bool = False
) -> List[Dict[str, Any]]:
    """
    Comprehensive validator for a single class occurrence against all Part B and Part C rules.
    Returns list of violated rules:
    [{'rule_name': str, 'reason': str, 'exact_values': str, 'severity': 'hard'|'soft'}]
    """
    violations = []
    
    c_date = cls_dict.get("date", "")
    day_name = cls_dict.get("day", "")
    if not day_name and c_date:
        try:
            day_name = datetime.strptime(c_date, "%Y-%m-%d").strftime("%A")
        except Exception:
            day_name = "Monday"
            
    t_slot = cls_dict.get("time_slot", "")
    start_min = parse_time_to_minutes(t_slot)
    coach_name = resolve_coach_canonical_name(cls_dict.get("coach_name", ""))
    batch_type = cls_dict.get("batch_type", "G")
    student_ids = cls_dict.get("student_ids", [])
    
    # 1. Operating Hours Check (Part B4)
    if start_min is not None:
        op_ok, op_reason = check_operating_hours(day_name, start_min)
        if not op_ok:
            violations.append({
                "rule_name": "Academy Operating Hours",
                "reason": op_reason,
                "exact_values": f"Day: {day_name}, Start Time: {t_slot}",
                "severity": "hard"
            })
            
        # Morning / Daytime check (Part B4)
        if is_morning_class(day_name, start_min):
            for sid in student_ids:
                s_obj = student_master_map.get(sid, {})
                s_name = s_obj.get("student_name", sid)
                # Check if student explicitly lists morning available
                m_pref = str(s_obj.get("mon_pref", "")).lower()
                is_morning_avail = "morning" in m_pref or "am" in m_pref or "any" in m_pref or "no preference" in m_pref
                if not is_morning_avail and s_obj:
                    violations.append({
                        "rule_name": "Morning / Daytime Attendance Restriction",
                        "reason": f"Class starts before 4:00 PM ({t_slot}) but student {s_name} ({sid}) is not explicitly morning-available in Master Data.",
                        "exact_values": f"Student: {s_name}, Slot: {t_slot}",
                        "severity": "hard"
                    })
    else:
        violations.append({
            "rule_name": "Time Format Unparseable",
            "reason": f"Could not parse class start time '{t_slot}'.",
            "exact_values": f"Time: {t_slot}",
            "severity": "hard"
        })

    # 2. Batch Capacity (Part B2 & Part C4)
    seat_count = len(student_ids)
    if is_tournament:
        if seat_count > 20:
            violations.append({
                "rule_name": "Tournament Maximum Capacity (20)",
                "reason": f"Tournament batch capacity 20 exceeded with {seat_count} students.",
                "exact_values": f"Capacity 20 exceeded: {seat_count} students",
                "severity": "hard"
            })
        elif seat_count < 2:
            violations.append({
                "rule_name": "Tournament Minimum Capacity (2)",
                "reason": f"Tournament requires at least 2 students to run. Found {seat_count} student.",
                "exact_values": f"Capacity under minimum: {seat_count} student",
                "severity": "soft"
            })
    else:
        if batch_type == "G":
            if seat_count > 8:
                violations.append({
                    "rule_name": "Group Batch Capacity (Max 8)",
                    "reason": f"Group batch capacity 8 exceeded with {seat_count} students.",
                    "exact_values": f"Group capacity 8 exceeded: {seat_count} students",
                    "severity": "hard"
                })
        elif batch_type == "L":
            if seat_count > 3:
                violations.append({
                    "rule_name": "Limited Batch Capacity (Max 3)",
                    "reason": f"Limited batch capacity 3 exceeded with {seat_count} students. (Max is 3, older 4 cap is retired).",
                    "exact_values": f"Limited capacity 3 exceeded: {seat_count} students",
                    "severity": "hard"
                })
        elif batch_type == "I":
            if seat_count > 1:
                violations.append({
                    "rule_name": "Individual Batch Single Student Rule",
                    "reason": f"Individual batch must have exactly 1 student. Never combine another student.",
                    "exact_values": f"Individual capacity exceeded: {seat_count} students",
                    "severity": "hard"
                })

    # 2b. Strict Batch Type Compatibility (Rule 1 Mandatory Hard Constraint)
    cls_btype = (batch_type or "G").upper()
    for sid in student_ids:
        s_obj = student_master_map.get(sid, {})
        s_btype = (s_obj.get("batch_type") or cls_btype).upper()
        s_name = s_obj.get("student_name", sid)
        if s_btype != cls_btype:
            violations.append({
                "rule_name": "Strict Batch Type Compatibility",
                "reason": f"Batch type mismatch (Hard): Student {s_name} ({sid}) is enrolled as {s_btype} batch type, but is assigned to a {cls_btype} batch. Mixing students from different batch types is strictly prohibited.",
                "exact_values": f"Student Batch: {s_btype}, Class Batch: {cls_btype}",
                "severity": "hard"
            })
        if s_btype == "I" and seat_count > 1:
            violations.append({
                "rule_name": "Individual Batch Single Student Rule",
                "reason": f"Individual batch student {s_name} ({sid}) is in a shared class of {seat_count} students. Individual students must remain individually assigned and never combined into shared batches.",
                "exact_values": f"Individual student in batch of {seat_count}",
                "severity": "hard"
            })

    # 3. Student Levels & Compatibility (Part B3 & Part C)
    student_levels = []
    for sid in student_ids:
        s_obj = student_master_map.get(sid, {})
        lvl = s_obj.get("student_level", cls_dict.get("student_level", "Beginner 1"))
        student_levels.append(lvl)
        
    if is_tournament:
        # Tournament eligibility for each student
        for sid, lvl in zip(student_ids, student_levels):
            s_obj = student_master_map.get(sid, {})
            s_name = s_obj.get("student_name", sid)
            s_btype = s_obj.get("batch_type", batch_type)
            el_ok, el_msg = check_tournament_eligibility(lvl, s_btype, day_name)
            if not el_ok:
                violations.append({
                    "rule_name": "Tournament Ineligibility",
                    "reason": f"Student {s_name} ({sid}) is ineligible for {day_name} tournament: {el_msg}",
                    "exact_values": f"Level: {lvl}, Batch: {s_btype}",
                    "severity": "hard"
                })
        # Strict tournament grouping
        grp_ok, grp_msg = check_tournament_grouping(student_levels, day_name)
        if not grp_ok:
            violations.append({
                "rule_name": "Strict Tournament Grouping",
                "reason": grp_msg,
                "exact_values": f"Levels in batch: {student_levels}",
                "severity": "hard"
            })
    else:
        # Regular class level compatibility
        comp_ok, comp_msg, comp_sev = check_regular_level_compatibility(student_levels)
        if not comp_ok:
            violations.append({
                "rule_name": "Level Compatibility",
                "reason": comp_msg,
                "exact_values": f"Levels in class: {student_levels}",
                "severity": comp_sev
            })

    # 4. Coach Overlap & Limits (Part B6, B7 & Part C6)
    c_ref = COACH_REFERENCE.get(coach_name)
    if coach_name and coach_name != "Unassigned":
        # Check Hema tournament-only constraint
        if c_ref and c_ref.get("tournaments_only") and not is_tournament:
            violations.append({
                "rule_name": "Coach Role Restriction",
                "reason": f"Coach {coach_name} conducts tournaments only and must never be assigned regular classes.",
                "exact_values": f"Coach: {coach_name}, Class Type: Regular",
                "severity": "hard"
            })
            
        # Check BATHRI Early Intermediate regular class prohibition
        if coach_name in ["BATHRI", "Bathri", "Bathrinath"] and not is_tournament:
            for lvl in student_levels:
                if "Early Intermediate" in lvl:
                    violations.append({
                        "rule_name": "Coach Level Restriction",
                        "reason": f"BATHRI may not take Early Intermediate students in regular classes.",
                        "exact_values": f"Coach: BATHRI, Student Level: {lvl}",
                        "severity": "hard"
                    })
                    break

        # Check Regular Qualification (unless tournament)
        if not is_tournament and c_ref and c_ref.get("levels"):
            allowed_lvls = set(c_ref["levels"])
            for lvl in student_levels:
                if lvl not in allowed_lvls:
                    violations.append({
                        "rule_name": "Coach Qualification Mismatch",
                        "reason": f"Coach {coach_name} is only qualified for {c_ref['levels']}, but class includes {lvl}.",
                        "exact_values": f"Coach: {coach_name}, Level: {lvl}",
                        "severity": "hard"
                    })
                    break

        # Check Coach Overlap across other classes on same date
        if start_min is not None:
            for other_cls in all_classes_in_month:
                if other_cls.get("class_id") == cls_dict.get("class_id"):
                    continue
                if other_cls.get("date") != c_date:
                    continue
                other_coach = resolve_coach_canonical_name(other_cls.get("coach_name", ""))
                if other_coach.lower() == coach_name.lower():
                    other_min = parse_time_to_minutes(other_cls.get("time_slot", ""))
                    if other_min is not None and check_intervals_overlap(start_min, other_min):
                        violations.append({
                            "rule_name": "Coach Schedule Overlap",
                            "reason": f"Coach {coach_name} is already assigned to another overlapping class at {other_cls.get('time_slot')} on {c_date}.",
                            "exact_values": f"Conflict slot: {other_cls.get('time_slot')}",
                            "severity": "hard"
                        })
                        break

        # Check Coach Daily Class Maximum
        if c_ref and c_ref.get("daily_limits"):
            day_limit = c_ref["daily_limits"].get(day_name, 99)
            # Count existing classes on that date for this coach
            existing_count = sum(
                1 for oc in all_classes_in_month 
                if oc.get("date") == c_date and resolve_coach_canonical_name(oc.get("coach_name", "")).lower() == coach_name.lower()
                and oc.get("class_id") != cls_dict.get("class_id")
            ) + 1 # +1 for this class
            
            if existing_count > day_limit:
                is_flex = c_ref.get("is_flex", False)
                violations.append({
                    "rule_name": "Coach Daily Class Limit",
                    "reason": f"Coach {coach_name} daily maximum for {day_name} is {day_limit} classes. This change reaches {existing_count} classes." + (" (Flex trainer workload exception)." if is_flex else ""),
                    "exact_values": f"Limit: {day_limit}, Assigned: {existing_count}",
                    "severity": "soft" if is_flex else "hard"
                })

    # 5. Student Daily Uniqueness (Part B5: At most 1 class per calendar day)
    for sid in student_ids:
        s_obj = student_master_map.get(sid, {})
        s_name = s_obj.get("student_name", sid)
        # Check if student already has another class on this date
        other_same_day = [
            oc for oc in all_classes_in_month
            if oc.get("date") == c_date and oc.get("class_id") != cls_dict.get("class_id") and sid in oc.get("student_ids", [])
        ]
        if other_same_day:
            violations.append({
                "rule_name": "One Class Per Student Per Day",
                "reason": f"Student {s_name} ({sid}) is already scheduled for another class on {c_date} at {other_same_day[0].get('time_slot')}.",
                "exact_values": f"Duplicate date: {c_date}",
                "severity": "hard"
            })

    # 6. Student Monthly Quota (Part B5: Default 12, never scheduled beyond without ⓒ)
    for sid in student_ids:
        s_obj = student_master_map.get(sid, {})
        s_name = s_obj.get("student_name", sid)
        req = s_obj.get("required_classes", 12)
        # Count classes student is enrolled in across month
        m_count = sum(
            1 for oc in all_classes_in_month
            if oc.get("class_id") != cls_dict.get("class_id") and sid in oc.get("student_ids", [])
        ) + 1
        if m_count > req:
            violations.append({
                "rule_name": "Student Monthly Quota Cap",
                "reason": f"Student {s_name} ({sid}) assigned {m_count} classes, which exceeds their monthly requirement of {req}.",
                "exact_values": f"Requirement: {req}, Assigned: {m_count}",
                "severity": "soft" # Extra (ⓒ) allowed after acknowledgement
            })

    for v in violations:
        if "rule" not in v and "rule_name" in v:
            v["rule"] = v["rule_name"]
        if "message" not in v and "reason" in v:
            v["message"] = v["reason"]
    return violations
