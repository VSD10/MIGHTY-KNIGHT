import re
from functools import lru_cache
from datetime import datetime, date, timedelta
from typing import List, Tuple, Optional

@lru_cache(maxsize=2048)
def parse_time_to_minutes(time_str: str) -> Optional[int]:
    """Converts strings like '6:00 AM', '5:00 PM', '17:00', '9 PM' into minutes from midnight."""
    if not time_str:
        return None
    s = str(time_str).strip().upper()
    
    # Check 12-hour format e.g. "6:00 AM", "05:00 PM", "9 PM"
    match12 = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(AM|PM)', s)
    if match12:
        hr = int(match12.group(1))
        mn = int(match12.group(2)) if match12.group(2) else 0
        ampm = match12.group(3)
        if ampm == "PM" and hr < 12:
            hr += 12
        elif ampm == "AM" and hr == 12:
            hr = 0
        return hr * 60 + mn

    # Check 24-hour format e.g. "17:00", "09:00"
    match24 = re.search(r'(\d{1,2}):(\d{2})', s)
    if match24:
        hr = int(match24.group(1))
        mn = int(match24.group(2))
        return hr * 60 + mn

    return None

@lru_cache(maxsize=2048)
def parse_slot_range(slot_str: str) -> Tuple[Optional[int], Optional[int]]:
    """Parses a slot string like '06:00 PM – 07:00 PM' or range '5 PM - 9 PM' into (start_min, end_min)."""
    if not slot_str:
        return (None, None)
    parts = re.split(r'[\-–—\ufffd]+|\s+to\s+|\s+till\s+', str(slot_str))
    if len(parts) >= 2:
        start_min = parse_time_to_minutes(parts[0])
        end_min = parse_time_to_minutes(parts[1])
        if start_min is not None and end_min is not None:
            if "PM" in parts[1].upper() and "AM" not in parts[0].upper() and start_min < 12 * 60 and start_min < 7 * 60:
                start_min += 12 * 60
            return (start_min, end_min)
    single = parse_time_to_minutes(slot_str)
    if single is not None:
        return (single, single + 60)
    return (None, None)

def is_slot_in_preference(slot_str: str, preference_str: str) -> bool:
    """
    Checks if a time slot (e.g. '06:00 PM – 07:00 PM') satisfies a preference string.
    Preferences can be 'No Preference', 'Not Available', a single time '05:00 PM', or a range '5 PM - 9 PM'.
    """
    if not preference_str:
        return True
    pref = preference_str.strip().lower()
    if pref in ["no preference", "any", "all", "", "none", "nan", "null"]:
        return True
    if pref in ["not available", "na", "no", "off"]:
        return False

    # Keywords matching
    slot_lower = slot_str.lower()
    if "morning" in pref and any(x in slot_lower for x in ["am", "06:", "07:", "09:", "10:", "11:"]):
        return True
    if "evening" in pref and any(x in slot_lower for x in ["pm", "04:", "05:", "06:", "07:", "08:", "09:"]):
        return True

    # Range parsing
    slot_start, slot_end = parse_slot_range(slot_str)
    pref_start, pref_end = parse_slot_range(preference_str)

    if slot_start is not None and slot_end is not None and pref_start is not None and pref_end is not None:
        if not re.search(r'[\-–—to]', preference_str):
            # Single time requested e.g. "05:00 PM"
            return slot_start == pref_start or abs(slot_start - pref_start) <= 60
        return slot_start >= pref_start and slot_end <= pref_end

    return True

def get_day_name(date_obj: date) -> str:
    return date_obj.strftime("%A")

def generate_date_range(start_date: date, end_date: date) -> List[date]:
    dates = []
    curr = start_date
    while curr <= end_date:
        dates.append(curr)
        curr += timedelta(days=1)
    return dates

DAY_NAME_MAP = {
    "mon": "Monday", "monday": "Monday",
    "tue": "Tuesday", "tues": "Tuesday", "tuesday": "Tuesday",
    "wed": "Wednesday", "wednesday": "Wednesday",
    "thu": "Thursday", "thur": "Thursday", "thurs": "Thursday", "thursday": "Thursday",
    "fri": "Friday", "friday": "Friday",
    "sat": "Saturday", "saturday": "Saturday",
    "sun": "Sunday", "sunday": "Sunday"
}

@lru_cache(maxsize=1024)
def parse_coach_preferred_timings(pref_str: Optional[str]) -> dict:
    """
    Parses a coach's Preferred Timings string into a structured day-wise dictionary.
    
    Examples:
      - "Monday: 5 pm – 9 pm (max 3); Tuesday: 5 pm – 6 pm, 7 pm – 8 pm (max 1)"
      - "Monday: Not available (max 0); Tuesday: Not available (max 0)"
      - "Monday: 6 am – 8 am, 6 pm – 9 pm (max 2)"
    """
    if not pref_str or not isinstance(pref_str, str):
        return {}
    s = pref_str.strip()
    if s.lower() in ["no preference", "any", "all", "none", "nan", ""]:
        return {}

    parsed_days = {}
    blocks = re.split(r'[;\n|]+', s)
    
    for block in blocks:
        b = block.strip()
        if not b:
            continue
            
        day_key = None
        details = b
        
        if ":" in b:
            parts = b.split(":", 1)
            raw_day = parts[0].strip().lower()
            day_key = DAY_NAME_MAP.get(raw_day)
            details = parts[1].strip()
        else:
            match = re.match(r'^(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)\b', b, re.IGNORECASE)
            if match:
                raw_day = match.group(1).lower()
                day_key = DAY_NAME_MAP.get(raw_day)
                details = b[match.end():].strip()

        if not day_key:
            continue

        max_classes = None
        max_match = re.search(r'\(?\s*max\s*[:=]?\s*(\d+)\s*\)?', details, re.IGNORECASE)
        if max_match:
            max_classes = int(max_match.group(1))
            details = details[:max_match.start()] + details[max_match.end():]
            details = details.strip()

        det_clean = details.lower()
        if "not available" in det_clean or det_clean in ["na", "no", "off", "unavailable"]:
            parsed_days[day_key] = {
                "is_available": False,
                "max_classes": 0,
                "windows": []
            }
            continue

        if max_classes == 0:
            parsed_days[day_key] = {
                "is_available": False,
                "max_classes": 0,
                "windows": []
            }
            continue

        windows = []
        w_parts = [w.strip() for w in re.split(r',', details) if w.strip()]
        for wp in w_parts:
            w_start, w_end = parse_slot_range(wp)
            if w_start is not None and w_end is not None:
                windows.append((w_start, w_end))

        parsed_days[day_key] = {
            "is_available": True,
            "max_classes": max_classes,
            "windows": windows
        }

    return parsed_days

def eval_coach_timing_preference(
    parsed_days: dict, 
    day_name: str, 
    time_slot: str
) -> Tuple[bool, bool, Optional[int]]:
    """
    Evaluates a time_slot against parsed preferred timings for day_name.
    
    Returns:
      (is_available_on_day, matches_window, preferred_max_classes)
    """
    if not parsed_days or day_name not in parsed_days:
        return (True, True, None)

    info = parsed_days[day_name]
    if not info.get("is_available", True) or info.get("max_classes") == 0:
        return (False, False, 0)

    windows = info.get("windows", [])
    pref_max = info.get("max_classes")

    if not windows:
        return (True, True, pref_max)

    slot_start, slot_end = parse_slot_range(time_slot)
    if slot_start is None or slot_end is None:
        return (True, True, pref_max)

    matches = False
    for w_start, w_end in windows:
        if slot_start >= w_start and slot_end <= w_end:
            matches = True
            break

    return (True, matches, pref_max)

def is_slot_in_coach_preference(coach_obj: Any, day_name: str, time_slot: str) -> Tuple[bool, str]:
    """
    Mandatory eligibility constraint: Never recommend or assign a new class to a coach
    outside their configured preference timings or daily limits.
    Validates teaching availability, daily class caps, Sunday rules, and timing windows.
    Returns: (is_valid, failure_reason)
    """
    if not coach_obj:
        return (False, "Coach record is missing or invalid")

    c_dict = coach_obj.model_dump() if hasattr(coach_obj, "model_dump") else (coach_obj if isinstance(coach_obj, dict) else {})
    c_name = c_dict.get("coach_name") or getattr(coach_obj, "coach_name", "Coach")

    # 1. Daily limit check (mon_max..sun_max)
    day_map = {
        "Monday": "mon_max", "Tuesday": "tue_max", "Wednesday": "wed_max",
        "Thursday": "thu_max", "Friday": "fri_max", "Saturday": "sat_max", "Sunday": "sun_max"
    }
    field_key = day_map.get(day_name, "mon_max")
    d_max = None
    if hasattr(coach_obj, "get_daily_max"):
        d_max = coach_obj.get_daily_max(day_name)
    elif field_key in c_dict and c_dict[field_key] is not None:
        d_max = c_dict[field_key]
    elif "daily_limits" in c_dict and day_name in c_dict["daily_limits"]:
        d_max = c_dict["daily_limits"][day_name]

    if d_max is not None and d_max <= 0:
        return (False, f"{c_name}: Configured daily class limit is 0 on {day_name} (Not Available)")

    # 2. Sunday Preference & Maximum check
    if day_name == "Sunday":
        sun_pref = str(c_dict.get("sunday_pref") or getattr(coach_obj, "sunday_pref", "Available")).strip().lower()
        if sun_pref in ["not available", "no", "off", "na", "unavailable"]:
            return (False, f"{c_name}: Marked 'Not Available' on Sundays")
        sun_max = c_dict.get("sun_max") if c_dict.get("sunday_max_classes") is None else c_dict.get("sunday_max_classes")
        if sun_max is not None and sun_max <= 0:
            return (False, f"{c_name}: Sunday max classes configured as 0")

    slot_start, slot_end = parse_slot_range(time_slot)
    if slot_start is None or slot_end is None:
        return (False, f"Invalid time slot '{time_slot}'")

    # 3. Multi-window availability dictionary check
    avail = c_dict.get("availability") or getattr(coach_obj, "availability", {}) or {}
    if isinstance(avail, dict) and day_name in avail:
        day_windows = avail[day_name]
        if isinstance(day_windows, list):
            if len(day_windows) == 0:
                return (False, f"{c_name}: No availability windows configured on {day_name}")
            matched_avail = False
            for w in day_windows:
                if isinstance(w, (list, tuple)) and len(w) >= 2:
                    ws = parse_time_to_minutes(w[0]) if isinstance(w[0], str) else w[0]
                    we = parse_time_to_minutes(w[1]) if isinstance(w[1], str) else w[1]
                    if ws is not None and we is not None and slot_start >= ws and slot_end <= we:
                        matched_avail = True
                        break
            if not matched_avail:
                return (False, f"{c_name}: Slot {time_slot} is outside configured availability windows for {day_name}")

    # 4. Preferred timings string check
    pref_str = str(c_dict.get("preferred_timings") or getattr(coach_obj, "preferred_timings", "") or "").strip()
    if pref_str and pref_str.lower() not in ["no preference", "available", "any", "all", "none", "", "nan", "null"]:
        parsed_days = parse_coach_preferred_timings(pref_str)
        if parsed_days and day_name in parsed_days:
            is_avail, matches_w, pref_dmax = eval_coach_timing_preference(parsed_days, day_name, time_slot)
            if not is_avail:
                return (False, f"{c_name}: Marked Not Available on {day_name} in Preferred Timings")
            if pref_dmax is not None and pref_dmax <= 0:
                return (False, f"{c_name}: Daily limit is 0 on {day_name} in Preferred Timings")
            if not matches_w:
                return (False, f"{c_name}: Slot {time_slot} is outside configured preference timing window for {day_name}")
        elif not parsed_days:
            # Single range without day name (e.g. "5 PM - 9 PM")
            if not is_slot_in_preference(time_slot, pref_str):
                return (False, f"{c_name}: Slot {time_slot} is outside preferred timings ({pref_str})")

    return (True, "")
