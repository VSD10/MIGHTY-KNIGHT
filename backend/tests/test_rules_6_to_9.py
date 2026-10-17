import pytest
import time
import threading
from app.engine.queue_manager import EngineQueueManager
from app.engine.suggestion_engine import (
    _build_set_from_ordered_pool,
    ENGINE_SETTINGS
)
from app.engine.effective_schedule_service import get_effective_schedule
from app.main import (
    app,
    accept_engine_suggestion_api,
    AcceptSuggestionRequest
)
from fastapi import HTTPException

def test_rule_6_non_blocking_and_request_queuing():
    """Rule 6: Engine execution does not block UI; mutations while running are queued and drained in FIFO order."""
    qm = EngineQueueManager()
    
    # 1. State initially idle
    status = qm.get_status()
    assert not status["is_running"]
    assert status["queued_count"] == 0

    executed_log = []
    finish_event = threading.Event()

    def mock_engine_task():
        # Simulates long engine task
        finish_event.wait(timeout=2.0)
        executed_log.append("engine_finished")

    # 2. Submit async engine job
    try:
        res = qm.submit_engine_job(mock_engine_task, month="2026-10")
        assert res["status"] == "started"
        assert qm.is_engine_running

        # 3. Submit mutation while engine is running -> must be queued without blocking!
        t0 = time.time()
        def mock_mutation_1(payload=None):
            executed_log.append("mutation_1")
            return {"status": "ok_1"}

        def mock_mutation_2(payload=None):
            executed_log.append("mutation_2")
            return {"status": "ok_2"}

        q_res1 = qm.queue_or_execute("mutation_1", {}, mock_mutation_1)
        q_res2 = qm.queue_or_execute("mutation_2", {}, mock_mutation_2)
        elapsed = time.time() - t0

        assert elapsed < 0.1, "Queueing mutations must return immediately without blocking"
        assert q_res1["status"] == "queued"
        assert q_res2["status"] == "queued"
        assert qm.get_queued_count() == 2

        # 4. Release engine execution
        finish_event.set()
        time.sleep(0.5) # Allow worker thread to drain queue

        # 5. After engine finishes, queue must be drained and mutations executed in FIFO order
        assert not qm.is_engine_running
        assert qm.get_queued_count() == 0
        assert executed_log == ["engine_finished", "mutation_1", "mutation_2"]
    finally:
        finish_event.set()
        qm.reset_state()

def test_rule_7_coach_continuity_and_ranking():
    """Rule 7: Rank coaches by monthly coverage and enforce 100% continuity or max 1 non-Sunday coach change."""
    # Setup candidate slots for 4 dates in a month
    # Coach A can cover all 4 dates (100% coverage)
    # Coach B can cover only 2 dates (50% coverage)
    # Coach C can cover 3 dates (75% coverage)
    
    candidate_slots = [
        {"class_id": "C1", "date": "2026-10-05", "day": "Monday", "coach_name": "COACH_A"},
        {"class_id": "C2", "date": "2026-10-12", "day": "Monday", "coach_name": "COACH_A"},
        {"class_id": "C3", "date": "2026-10-19", "day": "Monday", "coach_name": "COACH_A"},
        {"class_id": "C4", "date": "2026-10-26", "day": "Monday", "coach_name": "COACH_A"},
        
        {"class_id": "C1_B", "date": "2026-10-05", "day": "Monday", "coach_name": "COACH_B"},
        {"class_id": "C2_B", "date": "2026-10-12", "day": "Monday", "coach_name": "COACH_B"},

        {"class_id": "C1_C", "date": "2026-10-05", "day": "Monday", "coach_name": "COACH_C"},
        {"class_id": "C2_C", "date": "2026-10-12", "day": "Monday", "coach_name": "COACH_C"},
        {"class_id": "C3_C", "date": "2026-10-19", "day": "Monday", "coach_name": "COACH_C"},
    ]

    # Target 4 classes: COACH_A should be chosen as primary coach with 100% continuity
    assigned = _build_set_from_ordered_pool(candidate_slots, count=4)
    assert len(assigned) == 4
    assigned_coaches = [c["coach_name"] for c in assigned]
    assert all(c == "COACH_A" for c in assigned_coaches), "Should achieve 100% coach continuity with COACH_A"

    # Now simulate case where COACH_C is preferred/highest coverage (3/4 dates), and only COACH_B is available on date 4
    candidate_slots_partial = [
        {"class_id": "C1_C", "date": "2026-10-05", "day": "Monday", "coach_name": "COACH_C"},
        {"class_id": "C2_C", "date": "2026-10-12", "day": "Monday", "coach_name": "COACH_C"},
        {"class_id": "C3_C", "date": "2026-10-19", "day": "Monday", "coach_name": "COACH_C"},
        {"class_id": "C4_B", "date": "2026-10-26", "day": "Monday", "coach_name": "COACH_B"},
    ]
    assigned_partial = _build_set_from_ordered_pool(candidate_slots_partial, count=4)
    assert len(assigned_partial) == 4
    assigned_coaches_partial = [c["coach_name"] for c in assigned_partial]
    # Primary COACH_C gets 3, substitute COACH_B gets 1 (max 1 exception allowed)
    assert assigned_coaches_partial.count("COACH_C") == 3
    assert assigned_coaches_partial.count("COACH_B") == 1

def test_rule_8_real_time_availability_validation_and_conflict_rejection():
    """Rule 8: Real-time availability validation prevents overbooking a coach on existing committed slots."""
    # Try accepting an assignment that conflicts with an already booked coach slot
    # Look up an existing class in effective schedule
    eff = get_effective_schedule("2026-10")
    existing_class = eff["scheduled_classes"][0]
    coach = existing_class["coach_name"]
    date = existing_class["date"]
    time_slot = existing_class["time_slot"]

    # Attempt to accept a new slot for that coach on that exact same date and time_slot
    conflict_req = AcceptSuggestionRequest(
        student_id="TRAINER_PROPOSAL",
        month="2026-10",
        schedule_version=1,
        suggestion_item={
            "date": date,
            "time_slot": time_slot,
            "coach_name": coach,
            "tier": "T4"
        }
    )

    # Must raise HTTPException 409 Conflict
    with pytest.raises(HTTPException) as exc_info:
        accept_engine_suggestion_api(conflict_req)
    
    assert exc_info.value.status_code == 409
    assert f"Coach {coach} is now unavailable" in exc_info.value.detail


def test_rule_9_sunday_tournament_eligibility():
    """Rule 9: Sunday tournament eligibility matrix and Attention Required requirements."""
    eff = get_effective_schedule("2026-10")
    attention_records = eff.get("attention_records", [])
    assert len(attention_records) > 0

    for rec in attention_records:
        lvl = rec.get("student_level", "")
        btype = rec.get("batch_type", "")
        is_eligible = rec.get("sunday_tournament_eligible", False)
        req_text = rec.get("tournament_requirement", "")

        # Check Rule 9 exact logic
        if btype == "I" or lvl in ["Basic 1", "Intermediate 2"]:
            assert not is_eligible, f"Student {rec['student_name']} ({btype}, {lvl}) must NOT be tournament eligible"
            assert ("Non-Tournament" in req_text or "Ineligible" in req_text)
        else:
            assert is_eligible, f"Student {rec['student_name']} ({btype}, {lvl}) MUST be tournament eligible"
            assert "Sunday Tournament Eligible" in req_text

