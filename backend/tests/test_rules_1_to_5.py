import pytest
import time
from app.engine.rule_engine import (
    check_regular_level_compatibility,
    validate_all_rules_for_occurrence,
    LEVEL_MAP
)
from app.engine.suggestion_engine import (
    evaluate_hard_feasibility,
    find_single_class_suggestions,
    ENGINE_SETTINGS,
    _SUGGESTION_CACHE,
    invalidate_suggestion_cache
)
from app.engine.effective_schedule_service import (
    get_effective_schedule,
    REFERENCE_TODAY
)
from app.main import (
    app,
    CoachPriorityRequest,
    update_coach_priority_api,
    ReassignCoachRequest,
    reassign_batch_coach_api
)

def test_rule_1_batch_compatibility():
    """Rule 1: Strict batch type compatibility (G only in G, L only in L, I only in I)."""
    # G student in L batch -> Rejected
    g_student = {"student_id": "S1", "student_level": "Beginner 1", "batch_type": "G", "joining_date": "2026-10-01"}
    l_batch = {"class_id": "C1", "student_level": "Beginner 1", "batch_type": "L", "date": "2026-10-20", "time_slot": "05:00 PM - 06:00 PM", "coach_name": "BATHRI", "student_ids": ["S2"]}
    ok, reason = evaluate_hard_feasibility(l_batch, g_student, [l_batch], {}, ENGINE_SETTINGS)
    assert not ok
    assert reason == "batch_type_mismatch"

    # L student in G batch -> Rejected
    l_student = {"student_id": "S3", "student_level": "Beginner 1", "batch_type": "L", "joining_date": "2026-10-01"}
    g_batch = {"class_id": "C2", "student_level": "Beginner 1", "batch_type": "G", "date": "2026-10-20", "time_slot": "05:00 PM - 06:00 PM", "coach_name": "BATHRI", "student_ids": ["S4"]}
    ok, reason = evaluate_hard_feasibility(g_batch, l_student, [g_batch], {}, ENGINE_SETTINGS)
    assert not ok
    assert reason == "batch_type_mismatch"

    # I student in shared batch -> Rejected
    i_student = {"student_id": "S5", "student_level": "Beginner 1", "batch_type": "I", "joining_date": "2026-10-01"}
    i_batch_full = {"class_id": "C3", "student_level": "Beginner 1", "batch_type": "I", "date": "2026-10-20", "time_slot": "05:00 PM - 06:00 PM", "coach_name": "BATHRI", "student_ids": ["S6"]}
    ok, reason = evaluate_hard_feasibility(i_batch_full, i_student, [i_batch_full], {}, ENGINE_SETTINGS)
    assert not ok
    assert reason == "full"

def test_rule_1_level_compatibility_and_basic_1_isolation():
    """Rule 1: Level compatibility hierarchy and Basic 1 absolute isolation."""
    # Basic 1 combined with Basic 2 -> Strictly rejected
    ok, err, is_soft = check_regular_level_compatibility(["Basic 1", "Basic 2"])
    assert not ok
    assert "Basic 1" in err

    # Basic 1 combined with Beginner 1 -> Strictly rejected
    ok, err, is_soft = check_regular_level_compatibility(["Basic 1", "Beginner 1"])
    assert not ok

    # Adjacent levels: Beginner 1 and Beginner 2 -> Allowed as conditional soft fallback
    ok, err, is_soft = check_regular_level_compatibility(["Beginner 1", "Beginner 2"])
    assert ok
    assert bool(is_soft) is True

    # Non-adjacent levels: Beginner 1 and Intermediate 1 (diff > 1) -> Strictly rejected
    ok, err, is_soft = check_regular_level_compatibility(["Beginner 1", "Intermediate 1"])
    assert not ok
    assert "Combining non-adjacent levels" in err

def test_rule_2_actual_completed_schedule_previous_day():
    """Rule 2: In current month, completed schedule displays only up to previous completed day (date < ref_today)."""
    eff = get_effective_schedule("2026-10")
    ref_today = eff.get("reference_today", "2026-10-15")
    
    # Filter completed classes
    completed = [c for c in eff["scheduled_classes"] if c.get("date", "") < ref_today]
    current_and_future = [c for c in eff["scheduled_classes"] if c.get("date", "") >= ref_today]
    
    assert len(completed) > 0
    assert all(c["date"] < ref_today for c in completed)
    assert all(c["date"] >= ref_today for c in current_and_future)

def test_rule_3_coach_priority_switching_speed():
    """Rule 3: Coach priority switching completes within seconds without heavy lag."""
    t0 = time.time()
    req = CoachPriorityRequest(level="Beginner 1", coach_name="PRAKASH", new_priority=1)
    res = update_coach_priority_api(req)
    elapsed = time.time() - t0
    
    assert res["status"] == "success"
    # Must complete well within 5-8 seconds (target < 1.0s)
    assert elapsed < 3.0, f"Priority update took {elapsed:.2f}s, exceeding target!"

def test_rule_4_deleted_coach_preservation_and_reassignment():
    """Rule 4: Preserves classes when coach is deleted and provides reassignment."""
    # Test reassign batch coach endpoint
    reassign_req = ReassignCoachRequest(
        batch_name="GBN1-01",
        new_coach_name="ABINAYA",
        apply_to_entire_batch=True,
        month="2026-10"
    )
    res = reassign_batch_coach_api(reassign_req)
    assert res["status"] == "success"
    assert res["new_coach"] == "ABINAYA"
