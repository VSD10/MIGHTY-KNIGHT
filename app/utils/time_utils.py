import re
from datetime import datetime

def parse_time_slot_sort_key(date_str: str, time_slot: str) -> tuple:
    """
    Returns a sort key tuple (date_str, start_time_minutes) for strict chronological sorting.
    Example: '2026-08-24', '05:00 PM – 06:00 PM' -> ('2026-08-24', 1020)
    """
    try:
        match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)', time_slot or "", re.IGNORECASE)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            ampm = match.group(3).upper()
            if ampm == "PM" and hour < 12:
                hour += 12
            elif ampm == "AM" and hour == 12:
                hour = 0
            time_minutes = hour * 60 + minute
            return (date_str or "", time_minutes)
    except Exception:
        pass
    return (date_str or "", 0, time_slot or "")
