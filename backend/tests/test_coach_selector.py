import pytest
from app.models.coach import CoachModel
from app.config import DEFAULT_CONFIG
from app.engine.coach_selector import CoachSelector

def test_coach_priority_and_capability():
    coaches = [
        CoachModel(coach_name="GURU", levels_handled=["Basic 1", "Beginner 1"], mon_max=4),
        CoachModel(coach_name="BATHRI", levels_handled=["Basic 1", "Basic 2"], mon_max=4),
        CoachModel(coach_name="ABINAYA", levels_handled=["Basic 1"], mon_max=3)
    ]
    selector = CoachSelector(coaches, DEFAULT_CONFIG)

    # For Basic 1, priority in config is: BATHRI -> ABINAYA -> MANIKANDAN -> PRAKASH -> GURU
    # So BATHRI should be selected over GURU!
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
    assert coach.coach_name == "BATHRI"

def test_one_coach_one_class_conflict():
    coaches = [
        CoachModel(coach_name="BATHRI", levels_handled=["Basic 1"], mon_max=4),
        CoachModel(coach_name="ABINAYA", levels_handled=["Basic 1"], mon_max=3)
    ]
    selector = CoachSelector(coaches, DEFAULT_CONFIG)

    # BATHRI is already occupied at 6 PM - 7 PM
    occupancy = {"2026-08-24": {"06:00 PM – 07:00 PM": ["BATHRI"]}}

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
    # Next priority coach ABINAYA should be selected!
    assert coach is not None
    assert coach.coach_name == "ABINAYA"

def test_daily_coach_limit():
    coaches = [
        CoachModel(coach_name="BATHRI", levels_handled=["Basic 1"], mon_max=1) # Limit 1
    ]
    selector = CoachSelector(coaches, DEFAULT_CONFIG)

    daily_assignments = {"2026-08-24": {"BATHRI": 1}}

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

def test_coach_preferred_timings_soft_preference_and_max_caps():
    coaches = [
        CoachModel(
            coach_name="BATHRI",
            levels_handled=["Basic 1"],
            preferred_timings="Monday: 5 pm – 9 pm (max 1); Tuesday: Not available (max 0)"
        ),
        CoachModel(
            coach_name="ABINAYA",
            levels_handled=["Basic 1"],
            preferred_timings="Monday: 6 am – 9 am (max 3); Tuesday: 5 pm – 9 pm (max 2)"
        )
    ]
    selector = CoachSelector(coaches, DEFAULT_CONFIG)

    # 1. Monday morning slot (06:00 AM – 07:00 AM)
    # BATHRI priority 1 but prefers 5pm-9pm. ABINAYA prefers 6am-9am.
    # ABINAYA should be selected due to preferred timing match!
    coach1, _ = selector.select_coach(
        student_level="Basic 1",
        target_date_str="2026-08-24",
        day_name="Monday",
        time_slot="06:00 AM – 07:00 AM",
        is_sunday_tournament=False,
        daily_coach_assignments={},
        monthly_coach_assignments={},
        active_time_occupancy={}
    )
    assert coach1 is not None
    assert coach1.coach_name == "ABINAYA"

    # 2. Tuesday slot - BATHRI is marked "Not available" on Tuesday
    # BATHRI must be rejected; ABINAYA selected.
    coach2, _ = selector.select_coach(
        student_level="Basic 1",
        target_date_str="2026-08-25",
        day_name="Tuesday",
        time_slot="05:00 PM – 06:00 PM",
        is_sunday_tournament=False,
        daily_coach_assignments={},
        monthly_coach_assignments={},
        active_time_occupancy={}
    )
    assert coach2 is not None
    assert coach2.coach_name == "ABINAYA"

    # 3. Monday slot 5pm-6pm when BATHRI has preferred daily max = 1 and already taught 1
    # BATHRI limit reached (1/1); ABINAYA selected as fallback
    daily_assigned = {"2026-08-24": {"BATHRI": 1}}
    coach3, _ = selector.select_coach(
        student_level="Basic 1",
        target_date_str="2026-08-24",
        day_name="Monday",
        time_slot="05:00 PM – 06:00 PM",
        is_sunday_tournament=False,
        daily_coach_assignments=daily_assigned,
        monthly_coach_assignments={},
        active_time_occupancy={}
    )
    assert coach3 is not None
    assert coach3.coach_name == "ABINAYA"
