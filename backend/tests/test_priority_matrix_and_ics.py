import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.storage.database import load_all_coaches_db, save_single_coach_db, get_db_connection

client = TestClient(app)

def test_priority_matrix_endpoint_returns_8_levels():
    """Verify GET /api/master/coaches/priority-matrix returns all 8 academy levels with dynamic data."""
    response = client.get("/api/master/coaches/priority-matrix")
    assert response.status_code == 200
    data = response.json()
    assert "levels" in data
    assert "total_coaches" in data
    assert len(data["levels"]) == 8

    expected_levels = [
        "Basic 1", "Basic 2",
        "Beginner 1", "Beginner 2",
        "Early Intermediate 1", "Early Intermediate 2",
        "Intermediate 1", "Intermediate 2"
    ]
    level_names = [lvl["level"] for lvl in data["levels"]]
    assert level_names == expected_levels

    for lvl in data["levels"]:
        assert "qualified_count" in lvl
        assert "coaches" in lvl
        assert len(lvl["coaches"]) == lvl["qualified_count"]
        # If coaches exist, verify 1..N order and is_primary
        for idx, coach in enumerate(lvl["coaches"]):
            assert coach["priority"] == idx + 1
            if idx == 0:
                assert coach["is_primary"] is True
            else:
                assert coach["is_primary"] is False

def test_priority_matrix_move_swaps_adjacent_and_persists():
    """Verify POST /api/master/coaches/priority/move swaps adjacent ranks and persists."""
    # Get initial matrix
    res1 = client.get("/api/master/coaches/priority-matrix")
    matrix1 = res1.json()["levels"]
    
    # Pick a level with at least 2 coaches
    target_lvl = None
    for lvl in matrix1:
        if len(lvl["coaches"]) >= 2:
            target_lvl = lvl
            break
    assert target_lvl is not None, "Need at least one level with 2 coaches"

    level_name = target_lvl["level"]
    first_coach = target_lvl["coaches"][0]["coach_name"]
    second_coach = target_lvl["coaches"][1]["coach_name"]

    # Moving first coach 'up' should fail or be boundary-restricted
    res_up_bound = client.post("/api/master/coaches/priority/move", json={
        "level": level_name,
        "coach_name": first_coach,
        "direction": "up"
    })
    assert res_up_bound.status_code == 400

    # Move first coach 'down' -> second coach should now become primary
    res_move_down = client.post("/api/master/coaches/priority/move", json={
        "level": level_name,
        "coach_name": first_coach,
        "direction": "down"
    })
    assert res_move_down.status_code == 200
    updated_matrix = res_move_down.json()["levels"]
    updated_lvl = next(l for l in updated_matrix if l["level"] == level_name)

    assert updated_lvl["coaches"][0]["coach_name"] == second_coach
    assert updated_lvl["coaches"][0]["priority"] == 1
    assert updated_lvl["coaches"][0]["is_primary"] is True

    assert updated_lvl["coaches"][1]["coach_name"] == first_coach
    assert updated_lvl["coaches"][1]["priority"] == 2
    assert updated_lvl["coaches"][1]["is_primary"] is False

    # Move second_coach down (or first_coach up) to restore original order
    res_restore = client.post("/api/master/coaches/priority/move", json={
        "level": level_name,
        "coach_name": first_coach,
        "direction": "up"
    })
    assert res_restore.status_code == 200
    restored_matrix = res_restore.json()["levels"]
    restored_lvl = next(l for l in restored_matrix if l["level"] == level_name)
    assert restored_lvl["coaches"][0]["coach_name"] == first_coach

def test_priority_matrix_level_independence():
    """Verify changing priority in one level does not change coach order in another level."""
    res = client.get("/api/master/coaches/priority-matrix")
    matrix = res.json()["levels"]

    basic1 = next(l for l in matrix if l["level"] == "Basic 1")
    basic2 = next(l for l in matrix if l["level"] == "Basic 2")

    basic2_order_before = [c["coach_name"] for c in basic2["coaches"]]

    if len(basic1["coaches"]) >= 2:
        c1 = basic1["coaches"][0]["coach_name"]
        # Move in basic 1
        client.post("/api/master/coaches/priority/move", json={
            "level": "Basic 1",
            "coach_name": c1,
            "direction": "down"
        })
        # Check basic 2 is untouched
        res_after = client.get("/api/master/coaches/priority-matrix")
        basic2_after = next(l for l in res_after.json()["levels"] if l["level"] == "Basic 2")
        basic2_order_after = [c["coach_name"] for c in basic2_after["coaches"]]
        assert basic2_order_before == basic2_order_after

        # Restore basic 1
        client.post("/api/master/coaches/priority/move", json={
            "level": "Basic 1",
            "coach_name": c1,
            "direction": "up"
        })

def test_student_ics_restricted_when_quota_under_100():
    """Verify Student ICS export rejects with 400 and explanation when student quota < 100%."""
    # Fetch active latest schedule output 5 to find a student with < 100% quota
    sched_res = client.get("/api/schedule/latest/active")
    assert sched_res.status_code == 200
    sched = sched_res.json()
    schedule_id = sched.get("schedule_id", "SCHED_202610")

    out5_res = client.get(f"/api/schedule/{schedule_id}/output5")
    assert out5_res.status_code == 200
    students = out5_res.json().get("students", [])

    under_quota_student = None
    for s in students:
        assigned = s.get("scheduled_classes_count", 0)
        req = s.get("required_classes", 8)
        if assigned < req:
            under_quota_student = s
            break

    if under_quota_student:
        sid = under_quota_student["student_id"]
        ics_res = client.get(f"/api/schedule/{schedule_id}/student/{sid}/export-ics")
        assert ics_res.status_code == 400
        detail = ics_res.json()["detail"]
        assert "quota" in detail.lower() or "restricted" in detail.lower()
        assert "100%" in detail

def test_coach_ics_not_restricted():
    """Verify Coach ICS export remains available and unrestricted."""
    sched_res = client.get("/api/schedule/latest/active")
    schedule_id = sched_res.json().get("schedule_id", "SCHED_202610")

    # Fetch coaches
    coaches_res = client.get("/api/master/coaches")
    assert coaches_res.status_code == 200
    res_data = coaches_res.json()
    coaches = res_data.get("coaches", res_data if isinstance(res_data, list) else [])
    if coaches:
        coach_name = coaches[0].get("coach_name") or coaches[0].get("name")
        coach_ics = client.get(f"/api/schedule/{schedule_id}/coach/{coach_name}/export-ics")
        assert coach_ics.status_code == 200
        assert "BEGIN:VCALENDAR" in coach_ics.text
