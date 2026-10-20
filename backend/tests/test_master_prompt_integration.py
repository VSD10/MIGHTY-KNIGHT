import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from app.main import app
from app.engine.master_data_service import (
    OFFICIAL_8_LEVELS,
    get_authoritative_priority_matrix,
    add_coach_to_level_priority,
    remove_coach_from_level_priority,
    move_coach_level_priority
)
from app.storage.database import (
    get_deleted_records_db,
    save_single_coach_db,
    delete_single_coach_db,
    save_single_student_db,
    delete_single_student_db
)

client = TestClient(app)

# ─────────────────────────────────────────────────────────────────────────────
# 1. PRIORITY MATRIX DYNAMIC QUALIFICATION & ADD/REMOVE/MOVE (Section 1)
# ─────────────────────────────────────────────────────────────────────────────

def test_priority_matrix_eight_levels_structure():
    """Verify all 8 official levels are present and prioritized 1..N with primary flags."""
    res = client.get("/api/master/coaches/priority-matrix")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    levels_returned = [lvl["level"] for lvl in data["levels"]]
    for expected_lvl in OFFICIAL_8_LEVELS:
        assert expected_lvl in levels_returned

    for lvl_info in data["levels"]:
        coaches = lvl_info["coaches"]
        for idx, c in enumerate(coaches, 1):
            assert c["priority"] == idx
            assert c["is_primary"] == (idx == 1)

def test_priority_matrix_add_and_remove_coach():
    """Verify adding coach to level updates priority order, and removal keeps coach active in academy."""
    test_level = "Intermediate 2"
    test_coach = "Prathamesh"

    # Step A: Add coach to level
    add_res = client.post("/api/master/coaches/priority/add", json={
        "level": test_level,
        "coach_name": test_coach
    })
    assert add_res.status_code == 200
    matrix = add_res.json()["matrix"]
    i2_coaches = [c["coach_name"] for c in matrix[test_level]]
    assert any(c.upper() == test_coach.upper() for c in i2_coaches)

    # Verify rank sequence has no gaps
    for idx, c in enumerate(matrix[test_level], 1):
        assert c["priority"] == idx

    # Step B: Remove coach from Intermediate 2
    del_res = client.delete(f"/api/master/coaches/priority?level={test_level}&coach_name={test_coach}")
    assert del_res.status_code == 200
    matrix_after = del_res.json()["matrix"]
    i2_after = [c["coach_name"] for c in matrix_after[test_level]]
    assert not any(c.upper() == test_coach.upper() for c in i2_after)

    # Step C: Confirm coach was NOT deleted globally from academy master list
    master_res = client.get("/api/master/coaches")
    assert master_res.status_code == 200
    all_coach_names = [c["coach_name"] for c in master_res.json().get("coaches", [])]
    assert any(c.upper() == test_coach.upper() for c in all_coach_names)

def test_priority_matrix_move_rank():
    """Verify moving priority swaps positions cleanly and maintains 1..N sequence."""
    lvl = "Beginner 1"
    matrix_res = client.get("/api/master/coaches/priority-matrix")
    b1_coaches = matrix_res.json()["matrix"][lvl]
    if len(b1_coaches) >= 2:
        first_coach = b1_coaches[0]["coach_name"]
        second_coach = b1_coaches[1]["coach_name"]

        # Move second coach UP
        move_res = client.post("/api/master/coaches/priority/move", json={
            "level": lvl,
            "coach_name": second_coach,
            "direction": "up"
        })
        assert move_res.status_code == 200
        new_b1 = move_res.json()["matrix"][lvl]
        assert new_b1[0]["coach_name"] == second_coach
        assert new_b1[0]["priority"] == 1
        assert new_b1[0]["is_primary"] is True
        assert new_b1[1]["coach_name"] == first_coach
        assert new_b1[1]["priority"] == 2

        # Move second coach back DOWN
        restore_res = client.post("/api/master/coaches/priority/move", json={
            "level": lvl,
            "coach_name": second_coach,
            "direction": "down"
        })
        assert restore_res.status_code == 200
        restored_b1 = restore_res.json()["matrix"][lvl]
        assert restored_b1[0]["coach_name"] == first_coach
        assert restored_b1[1]["coach_name"] == second_coach

# ─────────────────────────────────────────────────────────────────────────────
# 2. ABSOLUTE SCHEDULE MULTI-MONTH PERSISTENCE & LOADING (Section 5)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("month_key, min_classes, min_students", [
    ("2026-09", 400, 130),
    ("2026-10", 350, 110),
    ("2026-11", 350, 110),
    ("2026-12", 350, 110),
])
def test_absolute_schedule_loads_correct_month(month_key, min_classes, min_students):
    """Verify selecting Sep, Oct, Nov, Dec 2026 loads their actual persisted schedule."""
    res = client.get(f"/api/effective-schedule/{month_key}")
    assert res.status_code == 200
    data = res.json()
    assert data["month"] == month_key
    classes = data.get("scheduled_classes", [])
    assert len(classes) >= min_classes, f"Expected >={min_classes} classes for {month_key}, got {len(classes)}"
    
    # Verify dates in the schedule all belong to the requested month
    sample_dates = [c.get("date") for c in classes[:20] if c.get("date")]
    for d in sample_dates:
        assert d.startswith(month_key), f"Class date {d} does not start with {month_key}"

def test_absolute_schedule_unseeded_month_returns_empty_state():
    """Verify an unseeded month returns an empty or uninitialized response without crash."""
    res = client.get("/api/effective-schedule/2027-05")
    assert res.status_code == 200
    data = res.json()
    assert data["month"] == "2027-05"
    assert data.get("total_classes", 0) == 0

# ─────────────────────────────────────────────────────────────────────────────
# 3. STUDENT & BATCH DELETION ROUTING & AUDIT (Section 2 & 3)
# ─────────────────────────────────────────────────────────────────────────────

def test_student_deletion_remove_from_schedule():
    """Verify deleting student with remove_from_schedule unlinks future classes and logs audit."""
    test_stu_id = "STU_INT_TEST_01"
    # Create test student
    save_single_student_db({
        "student_id": test_stu_id,
        "student_name": "Integration Test Student",
        "student_level": "Beginner 1",
        "batch_type": "G",
        "required_classes": 8
    })

    # Delete with remove_from_schedule
    del_res = client.delete(f"/api/master/students/{test_stu_id}?scope=remove_from_schedule")
    assert del_res.status_code == 200
    res_data = del_res.json()
    assert res_data["status"] == "success"
    assert res_data["scope"] == "remove_from_schedule"

    # Verify audit record exists in deleted_records
    records = get_deleted_records_db()
    matching = [r for r in records if r.get("record_id") == test_stu_id or test_stu_id in str(r.get("record_name", ""))]
    assert len(matching) > 0
    assert matching[0]["deletion_scope"] == "remove_from_schedule"

    # Cleanup
    delete_single_student_db(test_stu_id)

def test_student_deletion_archive():
    """Verify archiving student preserves history and marks scope='archive'."""
    test_stu_id = "STU_INT_TEST_02"
    save_single_student_db({
        "student_id": test_stu_id,
        "student_name": "Archive Test Student",
        "student_level": "Basic 1",
        "batch_type": "G",
        "required_classes": 8
    })

    del_res = client.delete(f"/api/master/students/{test_stu_id}?scope=archive")
    assert del_res.status_code == 200
    res_data = del_res.json()
    assert res_data["status"] == "success"
    assert res_data["scope"] == "archive"

    records = get_deleted_records_db()
    matching = [r for r in records if r.get("record_id") == test_stu_id or test_stu_id in str(r.get("record_name", ""))]
    assert len(matching) > 0
    assert matching[0]["deletion_scope"] == "archive"

    delete_single_student_db(test_stu_id)

def test_batch_deletion_routing():
    """Verify deleting a batch routes future classes to Attention Required and logs audit record."""
    from app.storage.database import save_single_batch_db, delete_single_batch_db
    test_bid = "BAT_INT_TEST_01"
    save_single_batch_db({
        "batch_id": test_bid,
        "batch_name": "Integration Test Batch",
        "level": "Beginner 1",
        "batch_type": "G",
        "fixed_trainer": "ABINAYA",
        "student_ids": [],
        "students": []
    })

    del_res = client.delete(f"/api/master/batches/{test_bid}?scope=remove_from_schedule")
    assert del_res.status_code == 200
    res_data = del_res.json()
    assert res_data["status"] == "success"
    assert res_data["scope"] == "remove_from_schedule"

    records = get_deleted_records_db()
    matching = [r for r in records if test_bid in str(r.get("record_name", "")) or r.get("record_id") == test_bid]
    assert len(matching) > 0

    delete_single_batch_db(test_bid)

# ─────────────────────────────────────────────────────────────────────────────
# 4. ATTENTION REQUIRED ACCURACY & COMPLETE FIELDS (Section 2)
# ─────────────────────────────────────────────────────────────────────────────

def test_attention_required_detailed_fields():
    """Verify Attention Required cards have complete info: student, batch, coach, date, action."""
    res = client.get("/api/attention-report/2026-10")
    assert res.status_code == 200
    data = res.json()
    assert "records" in data
    assert "metrics" in data
    
    # If there are unresolved student issues, check required fields
    records = data.get("records", [])
    for rec in records[:15]:
        assert "student_id" in rec
        assert "student_name" in rec
        assert "reason" in rec
        assert "action_required" in rec
        assert "original_batch_name" in rec
        assert "original_coach" in rec
        assert "is_historical" in rec
        assert "is_upcoming" in rec

# ─────────────────────────────────────────────────────────────────────────────
# 5. COACH CREATION AND ASSIGNMENT INTEGRATION (Section 4)
# ─────────────────────────────────────────────────────────────────────────────

def test_coach_creation_and_priority_availability():
    """Verify a newly created coach is immediately available in the priority matrix."""
    test_coach_name = "GM New Trainer Test"
    
    # Create coach via API
    create_res = client.post("/api/master/coaches", json={
        "coach_name": test_coach_name,
        "levels_handled": ["Beginner 1", "Intermediate 1"],
        "monthly_capacity_max": 60,
        "mon_max": 4,
        "tue_max": 4,
        "wed_max": 4,
        "thu_max": 4,
        "fri_max": 4,
        "sat_max": 4,
        "sun_max": 2
    })
    assert create_res.status_code == 200

    # Verify coach appears in Priority Matrix for Beginner 1 and Intermediate 1
    matrix_res = client.get("/api/master/coaches/priority-matrix")
    assert matrix_res.status_code == 200
    matrix = matrix_res.json()["matrix"]
    b1_names = [c["coach_name"] for c in matrix["Beginner 1"]]
    i1_names = [c["coach_name"] for c in matrix["Intermediate 1"]]
    assert any(c.upper() == test_coach_name.upper() for c in b1_names)
    assert any(c.upper() == test_coach_name.upper() for c in i1_names)

    # Clean up test coach
    delete_single_coach_db(test_coach_name)
