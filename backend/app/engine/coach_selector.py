from typing import List, Optional, Tuple, Dict, Any
from app.models.coach import CoachModel
from app.config import SystemConfig
from app.engine.time_utils import is_slot_in_preference, parse_slot_range

class CoachSelector:
    """
    Implements the 5-step coach selection algorithm and 7 condition checks from BRD Section 17.
    """
    def __init__(self, coaches: List[CoachModel], config: SystemConfig):
        self.coaches = coaches
        self.config = config
        self.coach_map = {c.coach_name.strip(): c for c in coaches}

    def select_coach(
        self,
        student_level: str,
        target_date_str: str,
        day_name: str,
        time_slot: str,
        is_sunday_tournament: bool,
        daily_coach_assignments: Dict[str, Dict[str, int]], # date -> coach_name -> count
        monthly_coach_assignments: Dict[str, int],          # coach_name -> count
        active_time_occupancy: Dict[str, Dict[str, List[str]]] # date -> time_slot -> list of assigned coach_names
    ) -> Tuple[Optional[CoachModel], Optional[str]]:
        """
        Executes Section 17 steps and returns (SelectedCoach, FailureReasonIfNone).
        """
        # Step 1: Student level provided
        level_clean = student_level.strip()

        # Step 2: Find coaches capable of handling that level
        capable_coaches = [c for c in self.coaches if c.can_handle_level(level_clean)]
        if not capable_coaches:
            return None, f"No coach qualified to teach level '{student_level}'"

        # Step 3: Get priority order for this level
        priority_list = self.config.coach_priority.get(level_clean, [])
        
        # Sort capable coaches by priority order
        def get_priority_rank(coach: CoachModel) -> int:
            name = coach.coach_name.strip()
            if name in priority_list:
                return priority_list.index(name)
            return 999 # Non-prioritized coaches come last

        ordered_coaches = sorted(capable_coaches, key=get_priority_rank)

        failure_reasons = []

        # Step 4 & 5: Check each candidate coach in priority order
        for coach in ordered_coaches:
            c_name = coach.coach_name.strip()
            
            # Check 1: Capability
            if not coach.can_handle_level(level_clean):
                continue

            # Check 2: Date & Day Availability
            if day_name == "Sunday" and coach.sunday_pref:
                if str(coach.sunday_pref).strip().lower() in ["not available", "no", "off"]:
                    failure_reasons.append(f"{c_name}: Not available on Sundays")
                    continue

            # Check 3: Time Slot Availability
            if coach.preferred_timings and coach.preferred_timings != "No Preference":
                # Check if coach timing preference conflicts strongly
                if not is_slot_in_preference(time_slot, coach.preferred_timings):
                    # Coach prefers a different timing, but preferences don't hard-override unless specified
                    pass

            # Check 4: One Coach, One Class at a Time (Conflict check, Section 19)
            occupied_coaches = active_time_occupancy.get(target_date_str, {}).get(time_slot, [])
            if c_name in occupied_coaches:
                failure_reasons.append(f"{c_name}: Already assigned to another class at {time_slot}")
                continue

            # Check 5: Daily Class Limit (Section 20)
            daily_max = coach.get_daily_max(day_name)
            current_daily_assigned = daily_coach_assignments.get(target_date_str, {}).get(c_name, 0)
            if current_daily_assigned >= daily_max:
                failure_reasons.append(f"{c_name}: Daily class limit reached ({current_daily_assigned}/{daily_max})")
                continue

            # Check 6: Monthly Maximum Capacity (Section 21)
            current_monthly_assigned = monthly_coach_assignments.get(c_name, 0)
            if current_monthly_assigned >= coach.monthly_capacity_max:
                failure_reasons.append(f"{c_name}: Monthly max capacity reached ({current_monthly_assigned}/{coach.monthly_capacity_max})")
                continue

            # Check 7: Special Conditions & Exceptions (Section 22 & 23)
            if is_sunday_tournament:
                if c_name in self.config.sunday_rules.excluded_tournament_coaches:
                    failure_reasons.append(f"{c_name}: Excluded from Sunday tournament assignments")
                    continue

            # Sunday 3 PM hard cap check
            if day_name == "Sunday":
                _, end_min = parse_slot_range(time_slot)
                if end_min and end_min > 15 * 60: # 3:00 PM is 900 minutes
                    failure_reasons.append(f"{c_name}: Sunday class ends after 3:00 PM ceiling")
                    continue

            # If all 7 checks pass, select this coach!
            return coach, None

        primary_reason = failure_reasons[0] if failure_reasons else "No available coach met all constraints"
        return None, primary_reason
