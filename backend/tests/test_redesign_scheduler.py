import os
import pytest
from datetime import date
from fastapi.testclient import TestClient

from app.main import app, ACTIVE_DATA, CURRENT_CONFIG, ensure_active_data
from app.models.student import StudentModel
from app.models.coach import CoachModel
from app.config import DEFAULT_CONFIG, SystemConfig
from app.engine.scheduler import run_scheduler, validate_schedule_integrity
from app.storage.database import (
    save_schedule_db, get_schedule_db, compute_master_data_fingerprint,
    save_single_student_db, save_single_coach_db
)

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_context():
    ensure_active_data()

def test_1_16_class_monthly_student_quota_and_spread():
    """
    Test 1: A 16-class monthly student gets no more than 16 classes
    and their classes are spread across weeks (approx 4 per week).
    """
    students = [
        StudentModel(
            student_id="STU_16",
            student_name="Student Sixteen",
            student_level="Basic 1",
            batch_type="G",
            required_classes=16,
            mon_pref="06:00 PM – 07:00 PM",
            tue_pref="06:00 PM – 07:00 PM",
            wed_pref="06:00 PM – 07:00 PM",
            thu_pref="06:00 PM – 07:00 PM",
            fri_pref="06:00 PM – 07:00 PM",
            sat_pref="06:00 PM – 07:00 PM",
            sun_pref="Not Available"
        )
    ]
    coaches = [
        CoachModel(
            coach_name="TrainerAlpha",
            levels_handled=["Basic 1"],
            mon_max=3, tue_max=3, wed_max=3, thu_max=3, fri_max=3, sat_max=3,
            monthly_capacity_max=50,
            preferred_timings="Monday: 06:00 PM – 08:00 PM; Tuesday: 06:00 PM – 08:00 PM; Wednesday: 06:00 PM – 08:00 PM; Thursday: 06:00 PM – 08:00 PM; Friday: 06:00 PM – 08:00 PM; Saturday: 06:00 PM – 08:00 PM"
        )
    ]

    start_date = date(2026, 9, 1)  # Tuesday
    end_date = date(2026, 9, 30)   # Wednesday (30 days, ~4.3 weeks)

    result = run_scheduler(students, coaches, start_date, end_date, DEFAULT_CONFIG)

    # 1. Quota cap check: scheduled <= 16
    scheduled_classes_for_student = [
        c for c in result.scheduled_classes if "STU_16" in c.student_ids
    ]
    assert len(scheduled_classes_for_student) <= 16
    assert len(scheduled_classes_for_student) == 16, f"Expected 16 classes, got {len(scheduled_classes_for_student)}"

    # 2. Spread across weeks: count per 7-day window should be approximately 3-4, never all in week 1
    week_counts = [0, 0, 0, 0, 0]
    for c in scheduled_classes_for_student:
        c_date = date.fromisoformat(c.date)
        w_idx = (c_date - start_date).days // 7
        week_counts[min(4, w_idx)] += 1

    # Week 0 must not consume all 16 classes
    assert week_counts[0] <= 4, f"Week 0 had {week_counts[0]} classes, should be <= 4"
    # At least 4 different weeks have scheduled classes
    weeks_active = sum(1 for cnt in week_counts if cnt > 0)
    assert weeks_active >= 4, f"Sessions not spread across weeks: {week_counts}"


def test_2_4_class_monthly_student_spaced_roughly_weekly():
    """
    Test 2: A 4-class monthly student is normally spaced roughly weekly (approx 1/week),
    not exhausted in week one.
    """
    students = [
        StudentModel(
            student_id="STU_4",
            student_name="Student Four",
            student_level="Basic 1",
            batch_type="G",
            required_classes=4,
            mon_pref="06:00 PM – 07:00 PM",
            tue_pref="06:00 PM – 07:00 PM",
            wed_pref="06:00 PM – 07:00 PM",
            thu_pref="06:00 PM – 07:00 PM",
            fri_pref="06:00 PM – 07:00 PM",
            sat_pref="06:00 PM – 07:00 PM",
            sun_pref="Not Available"
        )
    ]
    coaches = [
        CoachModel(
            coach_name="TrainerAlpha",
            levels_handled=["Basic 1"],
            mon_max=3, tue_max=3, wed_max=3, thu_max=3, fri_max=3, sat_max=3,
            monthly_capacity_max=50,
            preferred_timings="Monday: 06:00 PM – 08:00 PM; Tuesday: 06:00 PM – 08:00 PM; Wednesday: 06:00 PM – 08:00 PM; Thursday: 06:00 PM – 08:00 PM; Friday: 06:00 PM – 08:00 PM; Saturday: 06:00 PM – 08:00 PM"
        )
    ]

    start_date = date(2026, 9, 1)
    end_date = date(2026, 9, 30)

    result = run_scheduler(students, coaches, start_date, end_date, DEFAULT_CONFIG)

    scheduled = [c for c in result.scheduled_classes if "STU_4" in c.student_ids]
    assert len(scheduled) == 4

    week_counts = [0, 0, 0, 0, 0]
    for c in scheduled:
        c_date = date.fromisoformat(c.date)
        w_idx = (c_date - start_date).days // 7
        week_counts[min(4, w_idx)] += 1

    # Student must NOT be exhausted in week 0
    assert week_counts[0] <= 1, f"Week 0 had {week_counts[0]} classes; expected at most 1 for 4-class student"
    # Classes should span at least 3 distinct weeks
    weeks_active = sum(1 for cnt in week_counts if cnt > 0)
    assert weeks_active >= 3, f"4-class student classes clustered in too few weeks: {week_counts}"


def test_3_student_never_two_classes_on_same_date():
    """
    Test 3: Every student is assigned at most one class per calendar day.
    """
    students = [
        StudentModel(student_id=f"S_{i}", student_name=f"Student {i}", student_level="Basic 1", batch_type="G", required_classes=8)
        for i in range(5)
    ]
    coaches = [
        CoachModel(coach_name="TrainerAlpha", levels_handled=["Basic 1"], mon_max=5, tue_max=5, wed_max=5, thu_max=5, fri_max=5, sat_max=5, monthly_capacity_max=100)
    ]

    result = run_scheduler(students, coaches, date(2026, 9, 1), date(2026, 9, 15), DEFAULT_CONFIG)

    student_date_seen = set()
    for cls in result.scheduled_classes:
        for sid in cls.student_ids:
            key = (sid, cls.date)
            assert key not in student_date_seen, f"Student {sid} assigned multiple classes on {cls.date}"
            student_date_seen.add(key)


def test_4_trainer_never_overlapping_classes():
    """
    Test 4: Trainer cannot teach two classes in the same time slot on the same date.
    """
    students = [
        StudentModel(student_id=f"S_{i}", student_name=f"Student {i}", student_level="Basic 1", batch_type="I", required_classes=4)
        for i in range(4)
    ]
    coaches = [
        CoachModel(coach_name="TrainerAlpha", levels_handled=["Basic 1"], mon_max=5, tue_max=5, wed_max=5, thu_max=5, fri_max=5, sat_max=5, monthly_capacity_max=50)
    ]

    result = run_scheduler(students, coaches, date(2026, 9, 1), date(2026, 9, 15), DEFAULT_CONFIG)

    coach_slot_seen = set()
    for cls in result.scheduled_classes:
        key = (cls.coach_name.strip().lower(), cls.date, cls.time_slot)
        assert key not in coach_slot_seen, f"Trainer {cls.coach_name} assigned overlapping classes at {cls.time_slot} on {cls.date}"
        coach_slot_seen.add(key)


def test_5_trainer_daily_and_monthly_limits_enforced():
    """
    Test 5: Trainer daily limits and monthly limits are strictly enforced.
    """
    # Create 20 individual students needing classes
    students = [
        StudentModel(student_id=f"S_{i}", student_name=f"Student {i}", student_level="Basic 1", batch_type="I", required_classes=2)
        for i in range(20)
    ]
    # Coach with daily max 2 and monthly max 6
    coaches = [
        CoachModel(
            coach_name="CappedTrainer",
            levels_handled=["Basic 1"],
            mon_max=2, tue_max=2, wed_max=2, thu_max=2, fri_max=2, sat_max=2, sun_max=0,
            monthly_capacity_max=6
        )
    ]

    result = run_scheduler(students, coaches, date(2026, 9, 1), date(2026, 9, 30), DEFAULT_CONFIG)

    # Monthly count for coach must not exceed 6
    coach_classes = [c for c in result.scheduled_classes if c.coach_name == "CappedTrainer"]
    assert len(coach_classes) <= 6, f"Trainer exceeded monthly limit: {len(coach_classes)} > 6"

    # Daily counts must not exceed 2
    from collections import Counter
    date_counts = Counter(c.date for c in coach_classes)
    for dt, cnt in date_counts.items():
        assert cnt <= 2, f"Trainer exceeded daily limit on {dt}: {cnt} > 2"


def test_6_student_and_trainer_availability_enforced():
    """
    Test 6: Student availability (not scheduled on Not Available days) and trainer availability are enforced.
    """
    students = [
        StudentModel(
            student_id="S_ONLY_MON_WED",
            student_name="Mon Wed Only",
            student_level="Basic 1",
            batch_type="G",
            required_classes=4,
            mon_pref="06:00 PM – 07:00 PM",
            tue_pref="Not Available",
            wed_pref="06:00 PM – 07:00 PM",
            thu_pref="Not Available",
            fri_pref="Not Available",
            sat_pref="Not Available",
            sun_pref="Not Available"
        )
    ]
    coaches = [
        CoachModel(
            coach_name="TrainerAlpha",
            levels_handled=["Basic 1"],
            mon_max=3, wed_max=3,
            monthly_capacity_max=50,
            preferred_timings="Monday: 06:00 PM – 08:00 PM; Wednesday: 06:00 PM – 08:00 PM; Tuesday: Not available; Thursday: Not available; Friday: Not available"
        )
    ]

    result = run_scheduler(students, coaches, date(2026, 9, 1), date(2026, 9, 20), DEFAULT_CONFIG)

    for cls in result.scheduled_classes:
        if "S_ONLY_MON_WED" in cls.student_ids:
            assert cls.day in ["Monday", "Wednesday"], f"Student scheduled on unavailable day {cls.day}"


def test_7_student_quota_accounting_exact_invariant():
    """
    Test 7: The key accountability invariant is exact:
    scheduled_classes + remaining_classes == required_classes for ALL students.
    total students == fully scheduled students + attention/deficit students.
    """
    students = [
        StudentModel(student_id="S_4", student_name="Student 4", student_level="Basic 1", batch_type="G", required_classes=4),
        StudentModel(student_id="S_8", student_name="Student 8", student_level="Basic 1", batch_type="G", required_classes=8),
        StudentModel(student_id="S_16", student_name="Student 16", student_level="Basic 1", batch_type="G", required_classes=16)
    ]
    coaches = [
        CoachModel(coach_name="TrainerAlpha", levels_handled=["Basic 1"], mon_max=4, tue_max=4, wed_max=4, thu_max=4, fri_max=4, sat_max=4, monthly_capacity_max=100)
    ]

    result = run_scheduler(students, coaches, date(2026, 9, 1), date(2026, 9, 30), DEFAULT_CONFIG)

    student_counts = {}
    for cls in result.scheduled_classes:
        for sid in cls.student_ids:
            student_counts[sid] = student_counts.get(sid, 0) + 1

    unscheduled_map = {r.student_id: r.remaining_classes for r in result.unscheduled_records}

    for s in students:
        sch = student_counts.get(s.student_id, 0)
        rem = unscheduled_map.get(s.student_id, 0)
        assert sch <= s.required_classes
        assert sch + rem == s.required_classes, f"Mismatch for {s.student_id}: {sch} + {rem} != {s.required_classes}"

    assert result.accountability_passed is True
    assert result.total_students_considered == len(students)
    assert result.total_students_considered == result.successfully_scheduled_students + result.unscheduled_students_count


def test_8_unfulfillable_students_appear_in_output_3_with_clear_reason():
    """
    Test 8: Students whose quotas cannot be met due to lack of qualified trainer
    appear in Output 3 with a clear reason.
    """
    students = [
        StudentModel(
            student_id="S_INTERMEDIATE",
            student_name="Advanced Student",
            student_level="Intermediate",
            batch_type="G",
            required_classes=8
        )
    ]
    # Coach only handles Basic 1, not Intermediate
    coaches = [
        CoachModel(coach_name="BasicTrainer", levels_handled=["Basic 1"], mon_max=4, monthly_capacity_max=50)
    ]

    result = run_scheduler(students, coaches, date(2026, 9, 1), date(2026, 9, 30), DEFAULT_CONFIG)

    assert len(result.scheduled_classes) == 0
    assert result.unscheduled_students_count == 1
    assert len(result.unscheduled_records) == 1
    unmet = result.unscheduled_records[0]
    assert unmet.student_id == "S_INTERMEDIATE"
    assert unmet.remaining_classes == 8
    assert "trainer" in unmet.failure_reason.lower() or "capacity" in unmet.failure_reason.lower()


def test_9_manual_operations_reject_hard_constraint_violations():
    """
    Test 9: Manual add/edit/assign/delete cannot bypass hard constraints.
    Server rejects with HTTP 400 and preserves schedule integrity.
    """
    # 1. Run a schedule
    students = [
        StudentModel(student_id="STU_A", student_name="Student A", student_level="Basic 1", batch_type="G", required_classes=1),
        StudentModel(student_id="STU_B", student_name="Student B", student_level="Basic 1", batch_type="G", required_classes=1)
    ]
    coaches = [
        CoachModel(coach_name="CoachAlpha", levels_handled=["Basic 1"], mon_max=1, monthly_capacity_max=10)
    ]
    ACTIVE_DATA["students"] = [s.model_dump() for s in students]
    ACTIVE_DATA["coaches"] = [c.model_dump() for c in coaches]

    res = run_scheduler(students, coaches, date(2026, 9, 7), date(2026, 9, 7), DEFAULT_CONFIG)
    sched_dict = res.model_dump()
    save_schedule_db(sched_dict)
    sched_id = sched_dict["schedule_id"]

    # Attempt 1: Assigning student who already reached required classes (STU_A needs 1, already has 1)
    # or assigning to create double booking on the same day
    if sched_dict["scheduled_classes"]:
        cls_id = sched_dict["scheduled_classes"][0]["class_id"]
        # Try to create a second class on the SAME date for STU_A -> Must fail with 400
        resp = client.post(f"/api/schedule/{sched_id}/classes", json={
            "coach_name": "CoachAlpha",
            "date": "2026-09-07",
            "time_slot": "07:00 PM – 08:00 PM",
            "student_level": "Basic 1",
            "batch_type": "G",
            "student_ids": ["STU_A"]
        })
        assert resp.status_code == 400, f"Expected 400 rejection, got {resp.status_code}: {resp.text}"
        assert "conflict" in resp.json()["detail"].lower() or "quota" in resp.json()["detail"].lower()

        # Try to assign an unknown coach
        resp2 = client.post(f"/api/schedule/{sched_id}/classes", json={
            "coach_name": "NonExistentCoach",
            "date": "2026-09-07",
            "time_slot": "08:00 PM – 09:00 PM",
            "student_level": "Basic 1",
            "batch_type": "G",
            "student_ids": []
        })
        assert resp2.status_code == 400
        assert "unknown" in resp2.json()["detail"].lower()


def test_10_master_data_fingerprint_invalidation_and_finalized_guard():
    """
    Test 10: Changing master data or config invalidates old schedule fingerprint.
    Draft schedule regenerates automatically; Finalized schedule is marked stale without silent replacement.
    """
    save_single_student_db(
        {"student_id": "STU_X", "student_name": "Student X", "student_level": "Basic 1", "batch_type": "G", "required_classes": 4}
    )
    save_single_coach_db(
        {"coach_name": "CoachZ", "levels_handled": ["Basic 1"], "monthly_capacity_min": 0, "monthly_capacity_max": 20}
    )

    # Get active schedule (Draft)
    resp = client.get("/api/schedule/latest/active")
    assert resp.status_code == 200
    sched_data = resp.json()
    sched_id = sched_data["schedule_id"]
    assert sched_data["status"] == "Draft"

    # Finalize the schedule
    status_resp = client.post(f"/api/schedule/{sched_id}/status", json={"status": "Finalized"})
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "Finalized"

    # Now modify master data by adding a new student to SQLite DB
    save_single_student_db(
        {"student_id": "STU_Y", "student_name": "Student Y", "student_level": "Basic 1", "batch_type": "G", "required_classes": 4}
    )

    # Fetch active schedule again: must NOT silently replace finalized schedule, must mark is_stale = True
    resp_after = client.get("/api/schedule/latest/active")
    assert resp_after.status_code == 200
    after_data = resp_after.json()
    assert after_data["schedule_id"] == sched_id
    assert after_data["status"] == "Finalized"
    assert after_data["is_stale"] is True
    assert "stale" in after_data["stale_reason"].lower()


def test_11_api_workflows_and_exports_work():
    """
    Test 11: Standard API workflows (get schedule by id, output 1, output 2, output 3, ics export) work.
    """
    students = [
        StudentModel(student_id="STU_EXP", student_name="Export Student", student_level="Basic 1", batch_type="G", required_classes=2)
    ]
    coaches = [
        CoachModel(coach_name="CoachExport", levels_handled=["Basic 1"], mon_max=2, monthly_capacity_max=10)
    ]
    res = run_scheduler(students, coaches, date(2026, 9, 1), date(2026, 9, 7), DEFAULT_CONFIG)
    save_schedule_db(res.model_dump())
    sched_id = res.schedule_id

    # 1. GET schedule by ID
    r1 = client.get(f"/api/schedule/{sched_id}")
    assert r1.status_code == 200

    # 2. GET Output 1
    r2 = client.get(f"/api/schedule/{sched_id}/output1")
    assert r2.status_code == 200

    # 3. GET Output 2
    r3 = client.get(f"/api/schedule/{sched_id}/output2")
    assert r3.status_code == 200

    # 4. GET Output 3
    r4 = client.get(f"/api/schedule/{sched_id}/output3")
    assert r4.status_code == 200
    assert "attention_records" in r4.json()

    # 5. GET Student ICS export
    r5 = client.get(f"/api/schedule/{sched_id}/student/STU_EXP/export-ics")
    assert r5.status_code == 200
    assert "BEGIN:VCALENDAR" in r5.text
