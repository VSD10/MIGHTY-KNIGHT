import pytest
from app.models.coach import CoachModel
from app.config import DEFAULT_CONFIG
from app.engine.coach_selector import CoachSelector

def test_coach_priority_and_capability():
    coaches = [
        CoachModel(coach_name="Guruvanthana", levels_handled=["Basic 1", "Beginner 1"], mon_max=4),
        CoachModel(coach_name="Bathrinath", levels_handled=["Basic 1", "Basic 2"], mon_max=4),
        CoachModel(coach_name="Abinaya", levels_handled=["Basic 1"], mon_max=3)
    ]
    selector = CoachSelector(coaches, DEFAULT_CONFIG)

    # For Basic 1, priority in config is: Bathrinath -> Abinaya -> Manikandan -> Prakash -> Guruvanthana
    # So Bathrinath should be selected over Guruvanthana!
    coach, reason = selector.select_coach(
        student_level="Basic 1",
        target_date_str="2026-08-24",
        day_name="Monday",
        time_slot="06:00 PM – 07:00 PM",
        is_sunday_tournament=False,
        daily_coach_assignments={},
        monthly_coach_assignments={},
        active_time_occupancy={}
    )
    assert coach is not None
    assert coach.coach_name == "Bathrinath"

def test_one_coach_one_class_conflict():
    coaches = [
        CoachModel(coach_name="Bathrinath", levels_handled=["Basic 1"], mon_max=4),
        CoachModel(coach_name="Abinaya", levels_handled=["Basic 1"], mon_max=3)
    ]
    selector = CoachSelector(coaches, DEFAULT_CONFIG)

    # Bathrinath is already occupied at 6 PM - 7 PM
    occupancy = {"2026-08-24": {"06:00 PM – 07:00 PM": ["Bathrinath"]}}

    coach, reason = selector.select_coach(
        student_level="Basic 1",
        target_date_str="2026-08-24",
        day_name="Monday",
        time_slot="06:00 PM – 07:00 PM",
        is_sunday_tournament=False,
        daily_coach_assignments={},
        monthly_coach_assignments={},
        active_time_occupancy=occupancy
    )
    # Next priority coach Abinaya should be selected!
    assert coach is not None
    assert coach.coach_name == "Abinaya"

def test_daily_coach_limit():
    coaches = [
        CoachModel(coach_name="Bathrinath", levels_handled=["Basic 1"], mon_max=1) # Limit 1
    ]
    selector = CoachSelector(coaches, DEFAULT_CONFIG)

    daily_assignments = {"2026-08-24": {"Bathrinath": 1}}

    coach, reason = selector.select_coach(
        student_level="Basic 1",
        target_date_str="2026-08-24",
        day_name="Monday",
        time_slot="06:00 PM – 07:00 PM",
        is_sunday_tournament=False,
        daily_coach_assignments=daily_assignments,
        monthly_coach_assignments={},
        active_time_occupancy={}
    )
    assert coach is None
    assert "Daily class limit reached" in reason
