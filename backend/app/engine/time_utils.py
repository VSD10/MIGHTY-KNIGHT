import re
from datetime import datetime, date, timedelta
from typing import List, Tuple, Optional

def parse_time_to_minutes(time_str: str) -> Optional[int]:
    """Converts strings like '6:00 AM', '5:00 PM', '17:00', '9 PM' into minutes from midnight."""
    if not time_str:
        return None
    s = time_str.strip().upper()
    
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

def parse_slot_range(slot_str: str) -> Tuple[Optional[int], Optional[int]]:
    """Parses a 1-hour slot string like '06:00 PM – 07:00 PM' into (start_min, end_min)."""
    parts = re.split(r'[\-–—to]+', slot_str)
    if len(parts) == 2:
        start_min = parse_time_to_minutes(parts[0])
        end_min = parse_time_to_minutes(parts[1])
        return (start_min, end_min)
    return (None, None)

def is_slot_in_preference(slot_str: str, preference_str: str) -> bool:
    """
    Checks if a time slot (e.g. '06:00 PM – 07:00 PM') satisfies a preference string.
    Preferences can be 'No Preference', 'Not Available', or a time range '5 PM - 9 PM'.
    """
    if not preference_str:
        return True
    pref = preference_str.strip().lower()
    if pref in ["no preference", "any", "all", "", "none", "nan"]:
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
        # Check if slot fits inside preference range
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
