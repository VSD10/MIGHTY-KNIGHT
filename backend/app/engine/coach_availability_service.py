"""
coach_availability_service.py
=============================
Authoritative Engine Service for Coach Availability, Preference Tracking & Intelligent Remaining Slot Calculation.
Calculates date-specific remaining available 1-hour slots:
Available slots = Valid preferred time slots - Occupied time slots - Unavailable periods - Ineligible slots.
Fully synchronized with SQLite database, Master Data coaches, effective schedule, and academy operating hours.
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict

from app.engine.rule_engine import (
    COACH_REFERENCE, resolve_coach_canonical_name,
    parse_time_to_minutes, format_minutes_to_time,
    check_intervals_overlap, check_operating_hours
)
from app.storage.database import load_master_data_db


def parse_time_window_to_minutes(time_str: str) -> Optional[Tuple[int, int]]:
    """Parses a time slot or window string like '05:00 PM - 06:00 PM' or '17:00-18:00' into (start_min, end_min)."""
    if not time_str:
        return None
    try:
        parts = time_str.split("-")
        if len(parts) != 2:
            return None
        s_min = parse_time_to_minutes(parts[0].strip())
        e_min = parse_time_to_minutes(parts[1].strip())
        if s_min is not None and e_min is not None and e_min > s_min:
            return (s_min, e_min)
    except Exception:
        pass
    return None


def get_academy_operating_windows(day_name: str) -> List[Tuple[int, int]]:
    """Returns valid operating start and end minutes for a given weekday."""
    if day_name in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        # Standard: 16:00 to 21:00 (last start 20:00)
        return [(16 * 60, 21 * 60)]
    elif day_name == "Saturday":
        # Morning 06:00 to 14:00 + Evening 16:00 to 21:00
        return [(6 * 60, 14 * 60), (16 * 60, 21 * 60)]
    elif day_name == "Sunday":
        # 09:00 to 14:30 (hard ceiling 15:00)
        return [(9 * 60, int(14.5 * 60))]
    return []


def get_unified_coaches_dict() -> Dict[str, Dict[str, Any]]:
    """
    Unifies COACH_REFERENCE with dynamically registered master coaches from SQLite.
    Guarantees that any newly registered coach is immediately recognized with their
    configured preferences, availability, qualified levels, and workload limits.
    """
    unified = {}
    
    # 1. Base from COACH_REFERENCE
    for c_canon, c_ref in COACH_REFERENCE.items():
        unified[c_canon.upper()] = {
            "coach_name": c_canon,
            "levels": list(c_ref.get("levels", [])),
            "monthly_max": c_ref.get("monthly_max") or 100,
            "monthly_min": c_ref.get("monthly_min", 0),
            "daily_limits": dict(c_ref.get("daily_limits", {})),
            "availability": dict(c_ref.get("availability", {})),
            "is_flex": c_ref.get("is_flex", False),
            "tournaments_only": c_ref.get("tournaments_only", False),
            "is_registered": False
        }
        
    # 2. Overlay / add from master data SQLite
    master_data = load_master_data_db()
    for mc in master_data.get("coaches", []):
        c_name = (mc.get("coach_name") or "").strip()
        if not c_name:
            continue
        canon = resolve_coach_canonical_name(c_name)
        key = canon.upper()
        
        existing = unified.get(key, {})
        removed = mc.get("removed_levels", [])
        if "levels_handled" in mc and mc["levels_handled"] is not None:
            levels = [l for l in mc["levels_handled"] if l not in removed]
        elif "levels" in mc and mc["levels"] is not None:
            levels = [l for l in mc["levels"] if l not in removed]
        else:
            levels = [l for l in existing.get("levels", []) if l not in removed]
        prio_map = mc.get("qualified_levels_priority") or existing.get("qualified_levels_priority", {})
        m_max = mc.get("monthly_capacity_max") or existing.get("monthly_max", 100)
        m_min = mc.get("monthly_capacity_min") or existing.get("monthly_min", 0)
        max_daily = mc.get("max_classes_per_day") or 4
        
        # Build availability dictionary
        avail = mc.get("availability")
        if not avail or not isinstance(avail, dict) or len(avail) == 0:
            if existing.get("availability"):
                avail = existing.get("availability")
            else:
                # Default availability for newly created coach across working days
                avail = {
                    "Sunday": [("09:00", "14:30")],
                    "Monday": [("16:00", "21:00")],
                    "Tuesday": [("16:00", "21:00")],
                    "Wednesday": [("16:00", "21:00")],
                    "Thursday": [("16:00", "21:00")],
                    "Friday": [("16:00", "21:00")],
                    "Saturday": [("16:00", "21:00")]
                }
                
        daily_limits = dict(existing.get("daily_limits", {}))
        for d in ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]:
            if d not in daily_limits or mc.get("max_classes_per_day"):
                daily_limits[d] = max_daily
                
        unified[key] = {
            "coach_name": canon,
            "levels": levels,
            "qualified_levels_priority": prio_map,
            "removed_levels": removed,
            "monthly_max": m_max,
            "monthly_min": m_min,
            "daily_limits": daily_limits,
            "availability": avail,
            "is_flex": mc.get("is_flex", existing.get("is_flex", False)),
            "tournaments_only": existing.get("tournaments_only", False),
            "is_registered": True
        }
        
    return unified


def calculate_coach_availability_records(
    month: str = "2026-10",
    filter_date: Optional[str] = None,
    filter_coach: Optional[str] = None,
    filter_level: Optional[str] = None,
    filter_day: Optional[str] = None,
    filter_status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Computes precise, date-specific coach availability and remaining slots
    by comparing recorded preferences against existing class engagements.
    """
    from app.engine.effective_schedule_service import get_effective_schedule
    
    eff = get_effective_schedule(month)
    scheduled_classes = eff.get("scheduled_classes", [])
    
    coaches_registry = get_unified_coaches_dict()
    
    # Pre-index scheduled classes by (coach_canonical_upper, date)
    classes_by_coach_date = defaultdict(list)
    coach_monthly_counts = defaultdict(int)
    
    for cls in scheduled_classes:
        c_name = cls.get("coach_name", "")
        if not c_name or c_name.lower() == "unassigned":
            continue
        canon_upper = resolve_coach_canonical_name(c_name).upper()
        c_date = cls.get("date", "")
        if c_date:
            classes_by_coach_date[(canon_upper, c_date)].append(cls)
            coach_monthly_counts[canon_upper] += 1

    # Determine date span to evaluate
    all_dates = set()
    if filter_date:
        all_dates.add(filter_date)
    else:
        # Month range
        try:
            y, m = [int(p) for p in month.split("-")]
            import calendar
            _, num_days = calendar.monthrange(y, m)
            for d in range(1, num_days + 1):
                d_str = f"{y:04d}-{m:02d}-{d:02d}"
                if start_date and d_str < start_date:
                    continue
                if end_date and d_str > end_date:
                    continue
                all_dates.add(d_str)
        except Exception:
            all_dates = {c.get("date") for c in scheduled_classes if c.get("date")}

    sorted_dates = sorted(list(all_dates))
    results = []

    for d_str in sorted_dates:
        try:
            d_obj = datetime.strptime(d_str, "%Y-%m-%d")
            day_name = d_obj.strftime("%A")
        except Exception:
            continue
            
        if filter_day and filter_day.upper() != "ALL" and day_name.lower() != filter_day.lower():
            continue

        operating_windows = get_academy_operating_windows(day_name)
        if not operating_windows:
            continue

        for coach_upper, coach_info in coaches_registry.items():
            coach_name = coach_info["coach_name"]
            
            if filter_coach and filter_coach.upper() != "ALL":
                if coach_name.lower() != filter_coach.lower() and coach_upper != filter_coach.upper():
                    continue

            qualified_levels = coach_info.get("levels", [])
            if filter_level and filter_level.upper() != "ALL":
                if filter_level not in qualified_levels:
                    continue

            # 1. Evaluate Coach Preferred Availability Windows for this Weekday
            pref_windows = coach_info.get("availability", {}).get(day_name, [])
            
            # Formatted preferred hours display string
            if pref_windows:
                pref_hours_str = ", ".join([f"{format_minutes_to_time(parse_time_to_minutes(s))} - {format_minutes_to_time(parse_time_to_minutes(e))}" for s, e in pref_windows])
            else:
                pref_hours_str = "Unavailable (Rest Day)"

            # 2. Existing Engagements on this date
            engaged_classes = classes_by_coach_date.get((coach_upper, d_str), [])
            occupied_intervals = []
            occupied_slots_display = []
            
            for ec in engaged_classes:
                t_slot = ec.get("time_slot", "")
                parsed = parse_time_window_to_minutes(t_slot)
                if parsed:
                    occupied_intervals.append(parsed)
                    occupied_slots_display.append(f"{t_slot} ({ec.get('batch_name', 'Class')})")
                else:
                    occupied_slots_display.append(t_slot)

            classes_count_today = len(engaged_classes)
            daily_limit = coach_info.get("daily_limits", {}).get(day_name, 4)
            monthly_classes = coach_monthly_counts[coach_upper]
            monthly_max = coach_info.get("monthly_max", 100)
            is_flex = coach_info.get("is_flex", False)

            # 3. Calculate Valid Available 1-Hour Slots
            available_slots = []
            has_conflict = False

            # Check if coach has rest day / no preference
            if not pref_windows:
                status = "Unavailable on Day"
            elif classes_count_today >= daily_limit:
                status = "Daily Limit Reached"
            elif not is_flex and monthly_classes >= monthly_max:
                status = "Monthly Quota Reached"
            else:
                # Scan candidate 1-hour slots inside coach's preferred availability
                for start_s, end_s in pref_windows:
                    w_start = parse_time_to_minutes(start_s)
                    w_end = parse_time_to_minutes(end_s)
                    if w_start is None or w_end is None or w_end <= w_start:
                        continue
                    
                    # 1-hour step slots starting on the hour or half-hour
                    current_start = w_start
                    while current_start + 60 <= w_end:
                        current_end = current_start + 60
                        
                        # Constraint A: Must fall within academy operating hours
                        inside_op = any(op_s <= current_start and current_end <= op_e for op_s, op_e in operating_windows)
                        if not inside_op:
                            current_start += 30
                            continue
                            
                        # Constraint B: No overlap with existing class engagements on this date
                        overlaps = False
                        for occ_s, occ_e in occupied_intervals:
                            if check_intervals_overlap(current_start, current_end, occ_s, occ_e):
                                overlaps = True
                                break
                                
                        if not overlaps:
                            slot_label = f"{format_minutes_to_time(current_start)} - {format_minutes_to_time(current_end)}"
                            if slot_label not in available_slots:
                                available_slots.append(slot_label)
                                
                        current_start += 60  # Non-overlapping 1-hour class blocks

                if len(available_slots) > 0:
                    status = "Available"
                elif classes_count_today > 0:
                    status = "Fully Booked"
                else:
                    status = "No Valid Slots"

            # Check for existing overlap conflict among assigned classes
            for i in range(len(occupied_intervals)):
                for j in range(i + 1, len(occupied_intervals)):
                    if check_intervals_overlap(occupied_intervals[i][0], occupied_intervals[i][1], occupied_intervals[j][0], occupied_intervals[j][1]):
                        has_conflict = True
                        break

            # Filter by status if requested
            if filter_status and filter_status.upper() != "ALL":
                if filter_status.upper() == "AVAILABLE" and status != "Available":
                    continue
                elif filter_status.upper() == "FULLY_BOOKED" and status != "Fully Booked":
                    continue
                elif filter_status.upper() == "UNAVAILABLE" and status not in ["Unavailable on Day", "Daily Limit Reached", "Monthly Quota Reached"]:
                    continue

            results.append({
                "date": d_str,
                "day": day_name,
                "coach_name": coach_name,
                "preferred_hours": pref_hours_str,
                "assigned_classes_count": classes_count_today,
                "assigned_classes": [
                    {
                        "class_id": c.get("class_id"),
                        "time_slot": c.get("time_slot"),
                        "batch_name": c.get("batch_name", "Batch"),
                        "student_level": c.get("student_level"),
                        "students_formatted": c.get("students_formatted", "")
                    }
                    for c in engaged_classes
                ],
                "occupied_slots": occupied_slots_display,
                "available_slots": available_slots,
                "available_slots_count": len(available_slots),
                "remaining_capacity": max(0, daily_limit - classes_count_today),
                "qualified_levels": qualified_levels,
                "daily_limit": daily_limit,
                "monthly_classes": monthly_classes,
                "monthly_max": monthly_max,
                "is_flex": is_flex,
                "has_conflict": has_conflict,
                "status": status,
                "is_registered": coach_info.get("is_registered", False)
            })

    return results
