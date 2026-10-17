from typing import List, Optional, Tuple, Dict, Any
from app.models.coach import CoachModel
from app.config import SystemConfig
from app.engine.time_utils import is_slot_in_preference, parse_slot_range, eval_coach_timing_preference, is_slot_in_coach_preference

class CoachSelector:
    """
    Implements the coach selection algorithm, hard constraint checks, and mandatory RULE_COACH_PREFERRED_TIMING.
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
        Executes selection sequence and returns (SelectedCoach, FailureReasonIfNone).
        Strictly enforces mandatory coach preference timings, daily caps, and monthly caps.
        """
        level_clean = student_level.strip()

        # Find coaches capable of handling that level
        capable_coaches = [c for c in self.coaches if c.can_handle_level(level_clean, self.config)]
        if not capable_coaches:
            return None, f"No coach qualified to teach level '{student_level}'"

        # Get priority order for this level (case-insensitive)
        priority_list = [p.strip().lower() for p in self.config.coach_priority.get(level_clean, [])]
        
        def is_substitute_coach(coach: CoachModel) -> bool:
            comments_lower = f"{(coach.special_comments or '')} {(coach.temporary_exceptions or '')}".lower()
            return ("substitute" in comments_lower or "makeup" in comments_lower or "special classes only" in comments_lower)

        def get_priority_rank(coach: CoachModel) -> Tuple[int, int, int]:
            name_lower = coach.coach_name.strip().lower()
            sub_flag = 1 if is_substitute_coach(coach) else 0
            curr_m = monthly_coach_assignments.get(coach.coach_name.strip(), 0)
            target_flag = 0 if curr_m < coach.monthly_capacity_min else 1
            rank = priority_list.index(name_lower) if name_lower in priority_list else 999
            return (sub_flag, target_flag, rank)

        ordered_coaches = sorted(capable_coaches, key=get_priority_rank)

        # Mandatory Hard Constraint: Never recommend or assign a coach outside their configured preference timings
        pref_rule = next((r for r in self.config.rules_registry if r.rule_id == "RULE_COACH_PREFERRED_TIMING"), None)
        is_pref_hard = True if (pref_rule is None or (pref_rule.enabled and pref_rule.constraint_type == "HARD_CONSTRAINT")) else False

        failure_reasons = []
        valid_candidates: List[Tuple[CoachModel, bool, bool]] = [] # (coach, matches_preferred_window, is_substitute)

        for coach in ordered_coaches:
            c_name = coach.coach_name.strip()
            
            # Check 1: Capability
            if not coach.can_handle_level(level_clean, self.config):
                continue

            # Check 2 & 3: Mandatory Coach Preferred Timings, Working Hours & Day Availability
            timing_ok, timing_reason = is_slot_in_coach_preference(coach, day_name, time_slot)
            if not timing_ok:
                failure_reasons.append(timing_reason)
                continue

            # Check 4: Effective Daily Class Limit
            parsed_timings = coach.get_parsed_preferred_timings()
            _, matches_window, pref_daily_max = eval_coach_timing_preference(
                parsed_timings, day_name, time_slot
            )
            std_daily_max = coach.get_daily_max(day_name)
            effective_daily_max = min(std_daily_max, pref_daily_max) if (pref_daily_max is not None and pref_daily_max >= 0) else std_daily_max

            current_daily_assigned = daily_coach_assignments.get(target_date_str, {}).get(c_name, 0)
            if current_daily_assigned >= effective_daily_max:
                failure_reasons.append(f"{c_name}: Daily class limit reached ({current_daily_assigned}/{effective_daily_max})")
                continue

            # Check 5: Slot Occupancy Guard (1 Coach = 1 Class at a time)
            occupied_coaches = active_time_occupancy.get(target_date_str, {}).get(time_slot, [])
            if c_name in occupied_coaches:
                failure_reasons.append(f"{c_name}: Already assigned to another class at {time_slot}")
                continue

            # Check 6: Monthly Maximum Capacity
            current_monthly_assigned = monthly_coach_assignments.get(c_name, 0)
            if current_monthly_assigned >= coach.monthly_capacity_max:
                failure_reasons.append(f"{c_name}: Monthly max capacity reached ({current_monthly_assigned}/{coach.monthly_capacity_max})")
                continue

            # Check 7: Special Sunday Conditions & 3 PM Ceiling
            if is_sunday_tournament:
                if c_name in self.config.sunday_rules.excluded_tournament_coaches:
                    failure_reasons.append(f"{c_name}: Excluded from Sunday tournament assignments")
                    continue

            # Candidate meets all mandatory hard rules!
            valid_candidates.append((coach, matches_window, is_substitute_coach(coach)))

        if not valid_candidates:
            primary_reason = failure_reasons[0] if failure_reasons else "No available coach met all constraints"
            return None, primary_reason

        # Selection hierarchy in strict priority order:
        regular_candidates = [(c, match) for c, match, sub in valid_candidates if not sub]
        substitute_candidates = [(c, match) for c, match, sub in valid_candidates if sub]

        reg_matches = [c for c, match in regular_candidates if match]
        if reg_matches:
            return reg_matches[0], None
        sub_matches = [c for c, match in substitute_candidates if match]
        if sub_matches:
            return sub_matches[0], None

        if not is_pref_hard:
            if regular_candidates:
                return regular_candidates[0][0], None
            if substitute_candidates:
                return substitute_candidates[0][0], None

        return None, f"No coach available within preferred timing window for {day_name} ({time_slot})"

