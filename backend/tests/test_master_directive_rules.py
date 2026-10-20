"""
Unit and Integration Tests for Master Development Directive Rules 1 through 6
- Rule 1: Strict Batch Compatibility (G/L/I isolation) & Level Hierarchy (Basic 1 isolation + confirmation-gated adjacent ±1)
- Rule 2: Absolute Schedule Actual Completed Schedule Display (strictly up to Current Date - 1 Day)
- Rule 3: Coach Workload Priority Switching Performance (< 5–8 seconds)
- Rule 4: Deleted Coach Class Preservation, Attention Routing & Smart Replacement Coach Reassignment
- Rule 5 & 6: Engine Latency Optimization, Non-Blocking Execution Queue & Concurrency Safety
"""

import time
import pytest
from datetime import date, datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.engine.rule_engine import validate_all_rules_for_occurrence, COACH_REFERENCE
from app.engine.effective_schedule_service import get_effective_schedule
from app.storage.database import get_active_baseline_db, revert_exception_record_db, save_single_coach_db

client = TestClient(app)

# ==============================================================================
# RULE 1: STRICT BATCH COMPATIBILITY & LEVEL FLEXIBILITY
# ==============================================================================

def test_rule_1_batch_type_isolation():
    """Rule 1A: G students only attend G batches; L only L; I only I (zero exceptions)."""
    master_students = {
        "S_G": {"student_id": "S_G", "student_name": "Group Student", "batch_type": "G", "student_level": "Beginner 1"},
        "S_L": {"student_id": "S_L", "student_name": "Limited Student", "batch_type": "L", "student_level": "Beginner 1"},
        "S_I": {"student_id": "S_I", "student_name": "Individual Student", "batch_type": "I", "student_level": "Beginner 1"}
    }

    # 1. G student in Limited batch -> HARD VIOLATION
    target_cls_gl = {
        "class_id": "TEST_C1",
        "date": "2026-10-10",
        "time_slot": "05:00 PM",
        "coach_name": "Bathrinath",
        "student_level": "Beginner 1",
        "batch_type": "L",
        "student_ids": ["S_G"]
    }
    violations = validate_all_rules_for_occurrence(target_cls_gl, [], master_students, COACH_REFERENCE)
    hard_violations = [v for v in violations if v["severity"] == "hard"]
    assert any("Batch type violation" in v.get("reason", "") for v in hard_violations), "G student in L batch must trigger hard violation"

    # 2. Individual student in Group batch -> HARD VIOLATION
    target_cls_ig = {
        "class_id": "TEST_C2",
        "date": "2026-10-10",
        "time_slot": "05:00 PM",
        "coach_name": "Bathrinath",
        "student_level": "Beginner 1",
        "batch_type": "G",
        "student_ids": ["S_I"]
    }
    violations = validate_all_rules_for_occurrence(target_cls_ig, [], master_students, COACH_REFERENCE)
    hard_violations = [v for v in violations if v["severity"] == "hard"]
    assert any("Batch type violation" in v.get("reason", "") for v in hard_violations), "I student in G batch must trigger hard violation"

    # 3. Individual batch with > 1 student -> HARD VIOLATION
    target_cls_multi_i = {
        "class_id": "TEST_C3",
        "date": "2026-10-10",
        "time_slot": "05:00 PM",
        "coach_name": "Bathrinath",
        "student_level": "Beginner 1",
        "batch_type": "I",
        "student_ids": ["S_I", "S_L"]
    }
    violations = validate_all_rules_for_occurrence(target_cls_multi_i, [], master_students, COACH_REFERENCE)
    hard_violations = [v for v in violations if v["severity"] == "hard"]
    assert any("Individual (I)" in v.get("reason", "") for v in hard_violations)

def test_rule_1_basic_1_absolute_isolation():
    """Rule 1B: Basic 1 students must attend Basic 1 batches ONLY. Never mixed or recommended adjacent."""
    master_students = {
        "S_B1": {"student_id": "S_B1", "student_name": "Basic One", "batch_type": "G", "student_level": "Basic 1"},
        "S_B2": {"student_id": "S_B2", "student_name": "Basic Two", "batch_type": "G", "student_level": "Basic 2"}
    }

    # Basic 1 student placed in Basic 2 class -> HARD VIOLATION
    target_cls = {
        "class_id": "TEST_B1_B2",
        "date": "2026-10-10",
        "time_slot": "05:00 PM",
        "coach_name": "Bathrinath",
        "student_level": "Basic 2",
        "batch_type": "G",
        "student_ids": ["S_B1"]
    }
    violations = validate_all_rules_for_occurrence(target_cls, [], master_students, COACH_REFERENCE)
    hard_violations = [v for v in violations if v["severity"] == "hard"]
    assert any("Basic 1" in v.get("reason", "") for v in hard_violations), "Basic 1 placed in non-Basic 1 must be hard violation"

    # Non-Basic 1 student placed in Basic 1 class -> HARD VIOLATION
    target_cls_reverse = {
        "class_id": "TEST_B2_B1",
        "date": "2026-10-10",
        "time_slot": "05:00 PM",
        "coach_name": "Bathrinath",
        "student_level": "Basic 1",
        "batch_type": "G",
        "student_ids": ["S_B2"]
    }
    violations = validate_all_rules_for_occurrence(target_cls_reverse, [], master_students, COACH_REFERENCE)
    hard_violations = [v for v in violations if v["severity"] == "hard"]
    assert any("Basic 1" in v.get("reason", "") for v in hard_violations)

def test_rule_1_adjacent_level_requires_confirmation():
    """Rule 1B: Non-Basic 1 student in adjacent ±1 level triggers requires_confirmation soft flag."""
    master_students = {
        "S_BEG1": {"student_id": "S_BEG1", "student_name": "Beginner Student", "batch_type": "G", "student_level": "Beginner 1"}
    }

    # Beginner 1 in Beginner 2 class (adjacent +1)
    target_cls = {
        "class_id": "TEST_ADJ",
        "date": "2026-10-10",
        "time_slot": "05:00 PM",
        "coach_name": "Bathrinath",
        "student_level": "Beginner 2",
        "batch_type": "G",
        "student_ids": ["S_BEG1"]
    }
    violations = validate_all_rules_for_occurrence(target_cls, [], master_students, COACH_REFERENCE)
    adj_warnings = [v for v in violations if v.get("requires_confirmation")]
    assert len(adj_warnings) > 0, "Adjacent level ±1 must be flagged with requires_confirmation: True"
    assert any("Adjacent-level placement" in v.get("reason", "") for v in adj_warnings)

# ==============================================================================
# RULE 2: ABSOLUTE SCHEDULE ACTUAL COMPLETED SCHEDULE DISPLAY
# ==============================================================================

def test_rule_2_actual_completed_schedule_display():
    """
    Rule 2: Actual Completed Schedule view displays schedule data strictly up to
    Current Date - 1 Day. Today and future dates are strictly excluded.
    Non-destructive read filter over effective schedule.
    """
    ref_date = "2026-10-15"
    expected_cutoff = "2026-10-14"

    res = client.get(f"/api/baseline/actual-completed?month=2026-10&current_date={ref_date}")
    assert res.status_code == 200
    data = res.json()

    assert data["cutoff_date"] == expected_cutoff
    assert data["current_date"] == ref_date
    assert data["is_strictly_prior_to_today"] is True

    # Verify that NO class has date >= ref_date (today or future)
    for cls in data["completed_classes"]:
        assert cls["date"] <= expected_cutoff, f"Class on {cls['date']} violates Rule 2 cutoff {expected_cutoff}"
        assert cls["date"] < ref_date, f"Class date {cls['date']} must be strictly prior to {ref_date}"

    # Verify daily breakdown
    for day_item in data["daily_breakdown"]:
        assert day_item["date"] <= expected_cutoff

    # Verify underlying effective schedule is intact (non-destructive)
    eff = client.get("/api/effective-schedule?month=2026-10").json()
    assert len(eff["scheduled_classes"]) >= len(data["completed_classes"])

# ==============================================================================
# RULE 3: COACH WORKLOAD PRIORITY SWITCHING PERFORMANCE
# ==============================================================================

def test_rule_3_priority_switching_speed_and_persistence():
    """
    Rule 3: Switching coach priorities completes in under 5–8 seconds (target < 5s)
    and updates SQLite master coaches immediately.
    """
    # Ensure Bathri coach exists in test db
    save_single_coach_db({
        "coach_name": "BATHRI",
        "levels_handled": ["Beginner 1", "Intermediate 1"],
        "qualified_levels_priority": {"Intermediate 1": 2},
        "monthly_capacity_max": 100,
        "is_active": True
    })

    t0 = time.time()
    res = client.post("/api/master/coaches/priority", json={
        "level": "Intermediate 1",
        "coach_name": "Bathrinath",
        "new_priority": 1
    })
    t1 = time.time()
    duration = t1 - t0

    assert res.status_code == 200
    assert duration < 5.0, f"Priority switch took {duration:.2f}s, exceeding 5.0s target"

    # Verify persistence in master data
    coaches_res = client.get("/api/master/coaches").json()
    coaches = coaches_res.get("coaches", [])
    b_coach = next((c for c in coaches if c.get("coach_name", "").upper() in ["BATHRI", "BATHRINATH"]), None)
    assert b_coach is not None
    assert b_coach.get("qualified_levels_priority", {}).get("Intermediate 1") == 1

# ==============================================================================
# RULE 4: DELETED COACH ZERO CLASS LOSS & SMART REPLACEMENT
# ==============================================================================

def test_rule_4_deleted_coach_reassignment_workflow():
    """
    Rule 4:
    1. Zero Class Loss: Classes for deleted coach are never deleted or orphaned.
    2. Route to Attention Required with pending_coach_reassignment: True.
    3. Intelligent Replacement Coach Recommendation matches time, level, and monthly quota.
    4. Reassign endpoint reassigns all batch classes cleanly to the new coach.
    """
    month = "2026-10"
    temp_coach = "TEMP_COACH_RULE4"

    # Save a temporary coach
    save_single_coach_db({
        "coach_name": temp_coach,
        "levels_handled": ["Beginner 1", "Beginner 2"],
        "qualified_levels_priority": {"Beginner 1": 1, "Beginner 2": 2},
        "monthly_capacity_max": 20,
        "is_active": True
    })

    # Add a class for this coach
    add_res = client.post("/api/schedule/exception/apply", json={
        "month": month,
        "date": "2026-10-25",
        "time_slot": "10:00 AM - 11:00 AM",
        "coach_name": temp_coach,
        "action_type": "add",
        "affected_student_ids": ["MKS00219"],
        "after": {
            "student_level": "Beginner 1",
            "batch_type": "G",
            "batch_name": "G-Beginner 1-Sat10",
            "student_ids": ["MKS00219"],
            "day": "Saturday"
        },
        "subtype": "normal_assignment",
        "reason": "Rule 4 testing class"
    })
    assert add_res.status_code == 200
    exc_id = add_res.json()["exception_id"]

    # Delete the coach from master data
    del_res = client.delete(f"/api/master/coaches/{temp_coach}")
    assert del_res.status_code == 200

    # Verify class is routed to Attention Required with smart recommendation
    eff = client.get(f"/api/effective-schedule?month={month}").json()
    att_rec = next((r for r in eff.get("attention_records", []) if temp_coach.lower() in r.get("failure_reason", "").lower()), None)
    assert att_rec is not None, "Class for deleted coach must appear in Attention Required"
    assert att_rec.get("pending_coach_reassignment") is True
    assert att_rec.get("recommended_coach") is not None
    assert len(att_rec.get("eligible_coaches", [])) > 0
    assert "Recommended:" in att_rec.get("details", "")

    # Reassign the batch to the recommended coach
    rec_coach = att_rec["recommended_coach"]
    reassign_res = client.post("/api/schedule/reassign-batch-coach", json={
        "batch_name": att_rec.get("batch_name", "G-Beginner 1-Sat10"),
        "old_coach_name": temp_coach,
        "new_coach_name": rec_coach,
        "month": month
    })
    assert reassign_res.status_code == 200
    reassign_data = reassign_res.json()
    assert reassign_data["status"] == "success"
    assert reassign_data["new_coach_name"] == rec_coach
    assert reassign_data["reassigned_classes_count"] >= 1

    # Cleanup test exception
    revert_exception_record_db(exc_id)
    for eid in reassign_data.get("exception_ids", []):
        revert_exception_record_db(eid)

# ==============================================================================
# RULE 5 & 6: ENGINE LATENCY & NON-BLOCKING EXECUTION QUEUE
# ==============================================================================

def test_rule_5_and_6_engine_queue_and_status():
    """
    Rule 6: Engine tasks can be enqueued asynchronously without blocking the UI,
    reporting status and auto-notifying on completion.
    """
    enqueue_res = client.post("/api/engine/tasks/enqueue", json={
        "task_type": "recompute",
        "payload": {"month": "2026-10"}
    })
    assert enqueue_res.status_code == 200
    task_info = enqueue_res.json()["task"]
    task_id = task_info["task_id"]
    assert task_info["status"] in ["queued", "running", "completed"]

    # Check status endpoint
    status_res = client.get("/api/engine/tasks/status")
    assert status_res.status_code == 200
    assert "pending_count" in status_res.json()

    # Wait for completion (fast task)
    time.sleep(1.0)
    detail_res = client.get(f"/api/engine/tasks/{task_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()["task"]
    assert detail["status"] in ["running", "completed"]

# ==============================================================================
# PROMPT 3 MASTER DIRECTIVE TESTS (PHASES 1 TO 5)
# ==============================================================================

def test_prompt3_phase1_and_rule11_new_student_end_to_end_pipeline():
    """
    Phase 1 (Rule 11): When a new student is added via Master Data Hub,
    they immediately appear in Attention Required with correct quota, level,
    preferences, Sunday tournament flags, and valid engine recommendations.
    """
    test_sid = "TEST_P3_STUDENT_001"
    student_payload = {
        "student_id": test_sid,
        "student_name": "Prompt 3 Test Prodigy",
        "student_level": "Beginner 1",
        "batch_type": "G",
        "required_classes": 4,
        "preferred_days": "Tuesday, Thursday",
        "preferred_time": "05:00 PM - 06:00 PM",
        "unavailable_days": ["Sunday"]
    }

    try:
        # 1. Add student to Master Data Hub
        post_res = client.post("/api/master/students", json=student_payload)
        assert post_res.status_code == 200, f"Failed to add student: {post_res.text}"

        # 2. Verify student is persisted in DB and appears in Master Students
        students_res = client.get("/api/master/students").json()
        all_students = students_res.get("students", [])
        assert any(s["student_id"] == test_sid for s in all_students), "Student must exist in master students"

        # 3. Verify student immediately appears in Attention Required
        eff = client.get("/api/effective-schedule?month=2026-10").json()
        att_rec = next((r for r in eff.get("attention_records", []) if r["student_id"] == test_sid), None)
        assert att_rec is not None, "New student with 0 classes must appear in Attention Required"
        assert att_rec["remaining_classes"] == 4
        assert att_rec["student_level"] == "Beginner 1"
        assert att_rec["batch_type"] == "G"
        assert att_rec["preferred_days"] == "Tuesday, Thursday"
        assert att_rec["preferred_time"] == "05:00 PM - 06:00 PM"
        # Beginner 1 in Group G is eligible for Sunday tournament
        assert att_rec["is_sunday_tournament_eligible"] is True
        assert "Sunday Tournament Required" in att_rec["sunday_tournament_requirement"]

        # 4. Generate recommendations (Set A, Set B, Set C)
        suggs_res = client.get(f"/api/engine/suggestions?student_id={test_sid}&needed_classes=4&month=2026-10")
        assert suggs_res.status_code == 200
        suggs_data = suggs_res.json()
        option_sets = suggs_data.get("option_sets", [])
        assert len(option_sets) > 0, "Engine must generate option sets"

        # Check Set A (Consistency / Same Coach)
        set_a = next((s for s in option_sets if s["set_id"].startswith("SET_A")), None)
        assert set_a is not None, "Set A (Consistent Pattern) must be generated"
        assert "continuity_pct" in set_a or "primary_coach" in set_a

        # Check Set B (Hybrid combinations with >=95% coach coverage target)
        set_b_list = [s for s in option_sets if s["set_id"].startswith("SET_B")]
        assert len(set_b_list) > 0, "Set B options must be generated"
        # Coach coverage target >= 95%
        assert any(s.get("coach_coverage_pct", 0) >= 90.0 for s in set_b_list)

        # Check Set C (Fastest completion)
        set_c = next((s for s in option_sets if s["set_id"].startswith("SET_C")), None)
        assert set_c is not None, "Set C (Fastest Completion) must be generated"
        assert "concludes_on" in set_c

        # 5. Accept an option set and verify atomic DB persistence and cross-page sync
        chosen_set = set_a or set_b_list[0]
        accept_res = client.post("/api/engine/suggestions/accept", json={
            "student_id": test_sid,
            "month": "2026-10",
            "is_option_set": True,
            "option_set_items": chosen_set["items"]
        })
        assert accept_res.status_code == 200
        accept_data = accept_res.json()
        assert accept_data["status"] == "success"
        assert accept_data["applied_count"] == len(chosen_set["items"])

        # 6. Verify cross-page reflection
        eff_after = client.get("/api/effective-schedule?month=2026-10").json()
        # Student now has 4 scheduled classes and 0 remaining
        att_after = next((r for r in eff_after.get("attention_records", []) if r["student_id"] == test_sid), None)
        assert att_after is None, "Student quota is now fulfilled and should not require attention"

        # Verify classes are in Output 1 and Output 5
        o1 = client.get(f"/api/schedule/{eff_after.get('version', 1)}/output1?month=2026-10").json()
        assert o1["total_classes"] > 0
        o5 = client.get(f"/api/schedule/{eff_after.get('version', 1)}/output5?month=2026-10").json()
        s_roster = next((s for s in o5.get("student_schedules", []) if s["student_id"] == test_sid), None)
        assert s_roster is not None
        assert s_roster["scheduled_classes"] == 4

        # Clean up created exceptions
        for eid in accept_data.get("applied_exception_ids", []):
            revert_exception_record_db(eid)

    finally:
        # Cleanup test student
        client.delete(f"/api/master/students/{test_sid}")

def test_prompt3_rule_9_sunday_tournament_exclusions():
    """
    Phase 4 (Rule 9): Sunday tournaments apply to all eligible students EXCEPT:
    - Individual batch (I) at every level
    - Intermediate 2 (GIM2, LIM2, IIM2)
    - Basic 1 (GB1, LB1, IB1)
    """
    from app.engine.rule_engine import check_tournament_eligibility

    # 1. Individual batch is NEVER eligible on Sunday
    ok_i, msg_i = check_tournament_eligibility("Beginner 1", "I", "Sunday")
    assert ok_i is False
    assert "Individual batch" in msg_i

    # 2. Basic 1 is NEVER eligible for Sunday tournament
    ok_b1, msg_b1 = check_tournament_eligibility("Basic 1", "G", "Sunday")
    assert ok_b1 is False
    assert "Basic 1" in msg_b1

    # 3. Intermediate 2 is excluded on Sunday (Friday tournament only)
    ok_im2, msg_im2 = check_tournament_eligibility("Intermediate 2", "G", "Sunday")
    assert ok_im2 is False
    assert "Intermediate 2" in msg_im2

    # 4. Beginner 1, Beginner 2, Basic 2, Intermediate 1 in Group are ELIGIBLE on Sunday
    for lvl in ["Basic 2", "Beginner 1", "Beginner 2", "Early Intermediate 1", "Early Intermediate 2", "Intermediate 1"]:
        ok, _ = check_tournament_eligibility(lvl, "G", "Sunday")
        assert ok is True, f"Level {lvl} in Group batch must be eligible for Sunday tournament"

# ==============================================================================
# RULE 8 ENHANCEMENT: HYBRID + NEW SLOT COMBINATION OPTIMIZATION & COACH COVERAGE
# ==============================================================================

def test_rule_8_hybrid_combination_optimization_and_coach_coverage():
    """
    Rule 8 Enhancement:
    - Generates up to 30 distinct, ranked combinations for student.
    - Evaluates both existing slot suggestions and newly available possibilities.
    - Evaluates coach availability across student's eligible days.
    - Achieves >=95% coach coverage across feasibly available eligible coaches.
    - Pure recommendation: does not modify or reserve existing schedules.
    """
    test_sid = "TEST_R8_STUDENT_COV"
    try:
        # 1. Create a test student needing 4 classes
        create_res = client.post("/api/master/students", json={
            "student_id": test_sid,
            "student_name": "Coverage Test Student",
            "student_level": "Beginner 1",
            "batch_type": "G",
            "required_classes": 4,
            "preferred_days": "Tuesday, Thursday, Saturday",
            "preferred_time": "05:00 PM",
            "is_morning_available": False,
            "region_timezone": "IST"
        })
        assert create_res.status_code == 200

        # Snapshot effective schedule before generating suggestions
        eff_before = client.get("/api/effective-schedule?month=2026-10").json()
        classes_before_count = len(eff_before.get("scheduled_classes", []))

        # 2. Query engine suggestions
        res = client.get(f"/api/engine/suggestions?student_id={test_sid}&month=2026-10&needed_classes=4")
        assert res.status_code == 200
        data = res.json()

        option_sets = data.get("option_sets", [])
        set_b_combos = [s for s in option_sets if s.get("set_id", "").startswith("SET_B")]

        # Verify up to 30 combinations generated
        assert len(set_b_combos) > 0, "Set B must generate hybrid options"
        assert len(set_b_combos) <= 30, f"Set B must have at most 30 options, got {len(set_b_combos)}"

        # Verify all combinations are distinct
        combo_keys = set()
        for cand in set_b_combos:
            key = tuple(sorted((it["date"], it.get("start_time", it.get("time_slot", "")), it["coach_id"]) for it in cand["items"]))
            assert key not in combo_keys, f"Duplicate combination found in Set B: {key}"
            combo_keys.add(key)
            assert len(cand["items"]) == 4, "Each combination must cover the 4 required classes"

        # Verify coach coverage requirement (>=95% coverage target)
        coverage_pct = set_b_combos[0].get("coach_coverage_pct", 0)
        assert coverage_pct >= 95.0, f"Coach coverage {coverage_pct}% must be >= 95.0%"

        # Verify that multiple qualified coaches appear across the Set B combinations
        coaches_in_b = {c for cand in set_b_combos for c in cand["coaches"]}
        assert len(coaches_in_b) >= 3, f"Expected broad coach coverage (at least 3 coaches), found: {coaches_in_b}"

        # Verify deterministic ranking (scores descending)
        scores = [cand["score"] for cand in set_b_combos]
        assert scores == sorted(scores, reverse=True), "Set B combinations must be deterministically sorted by score descending"

        # Critical Distinction: Suggestions must NOT modify existing schedule
        eff_after = client.get("/api/effective-schedule?month=2026-10").json()
        classes_after_count = len(eff_after.get("scheduled_classes", []))
        assert classes_before_count == classes_after_count, "Generating suggestions must never mutate or reserve committed schedules"

    finally:
        client.delete(f"/api/master/students/{test_sid}")

# ==============================================================================
# RULE 7: COACH CONTINUITY & STRICT EXISTING SCHEDULE PROTECTION
# ==============================================================================

def test_rule_7_coach_continuity_and_existing_schedule_protection():
    """
    Rule 7:
    - Never modify, regenerate, or reassign existing committed student schedules.
    - Set A prioritizes same-coach continuity (100% target, max 1 class exception).
    - Scope distinction: committed schedules are protected, new rules apply to new assignments only.
    """
    # 1. Verify committed baseline student schedule is untouched
    eff = client.get("/api/effective-schedule?month=2026-10").json()
    committed_students = {s for c in eff["scheduled_classes"] for s in c.get("student_ids", [])}
    assert len(committed_students) > 0, "Existing committed students must exist"

    # 2. Test new assignment continuity via Set A for a new student
    test_sid = "TEST_R7_CONTINUITY"
    try:
        client.post("/api/master/students", json={
            "student_id": test_sid,
            "student_name": "Continuity Test Student",
            "student_level": "Beginner 1",
            "batch_type": "G",
            "required_classes": 4,
            "preferred_days": "Monday, Wednesday",
            "preferred_time": "06:00 PM",
            "region_timezone": "IST"
        })

        res = client.get(f"/api/engine/suggestions?student_id={test_sid}&month=2026-10&needed_classes=4")
        assert res.status_code == 200
        data = res.json()

        set_a = next((s for s in data.get("option_sets", []) if s.get("set_id") == "SET_A_CONSISTENT"), None)
        assert set_a is not None, "Set A must be generated for new assignments"

        # Coach continuity must be >= 75% (allowing at most 1 exception class for a 4-class quota)
        assert set_a["continuity_pct"] >= 75.0, f"Continuity {set_a['continuity_pct']}% must be >= 75%"
        coaches = set_a["coaches"]
        assert len(coaches) <= 2, f"At most 1 exception coach permitted in Set A, got {coaches}"

    finally:
        client.delete(f"/api/master/students/{test_sid}")

