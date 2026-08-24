from datetime import datetime

def parse_time_slot_sort_key(date_str: str, time_slot: str) -> tuple:
    """
    Returns a sort key tuple (date_str, start_time_minutes) for strict chronological sorting.
    Example: '2026-08-24', '05:00 PM - 06:00 PM' -> ('2026-08-24', 1020)
    """
    try:
        start_part = time_slot.split("-")[0].strip()
        dt = datetime.strptime(f"{date_str} {start_part}", "%Y-%m-%d %I:%M %p")
        time_minutes = dt.hour * 60 + dt.minute
        return (date_str, time_minutes)
    except Exception:
        return (date_str, 0, time_slot)
