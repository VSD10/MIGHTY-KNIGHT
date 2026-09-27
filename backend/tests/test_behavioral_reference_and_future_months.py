import os
import calendar
from datetime import date, datetime
import pytest

from app.models.student import StudentModel
from app.models.coach import CoachModel
from app.config import DEFAULT_CONFIG, SystemConfig
from app.engine.dynamic_scheduler import run_dynamic_scheduler
from app.engine.scheduler import run_scheduler, validate_schedule_integrity
from app.engine.validator import validate_schedule_state
from app.ingestion.excel_parser import parse_excel_file
from app.outputs.monthly_matrix_excel import generate_monthly_matrix_excel

BASE_TEST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REFERENCE_EXCEL_PATH = os.path.join(BASE_TEST_DIR, "sample_data", "Oct'26 Schedule_FRESH-1.xlsx")

@pytest.fixture
def reference_data():
    assert os.path.exists(REFERENCE_EXCEL_PATH), f"File {REFERENCE_EXCEL_PATH} not found"
    with open(REFERENCE_EXCEL_PATH, "rb") as f:
        students, coaches, errors = parse_excel_file(f.read(), DEFAULT_CONFIG)
    return students, coaches

# -----------------------------------------------------------------------------
# Test 1: September / Reference Excel Behavioral Simulation & October 2026
# -----------------------------------------------------------------------------
def test_1_reference_data_october_generation(reference_data):
    students, coaches = reference_data
    assert len(students) >= 100, f"Expected 100+ students, got {len(students)}"
    assert len(coaches) >= 7, f"Expected 7+ coaches, got {len(coaches)}"

    start_date = date(2026, 10, 1)
    end_date = date(2026, 10, 31)

    result = run_scheduler(students, coaches, start_date, end_date, DEFAULT_CONFIG)

    # 1. Zero-loss invariant
    total_required = sum(s.required_classes for s in students)
    total_scheduled = sum(len(c.student_ids) for c in result.scheduled_classes)
    total_deficit = sum(u.remaining_classes for u in result.unscheduled_records)
    assert total_required == total_scheduled + total_deficit, (
        f"Zero-loss invariant breach: Required {total_required} != Scheduled {total_scheduled} + Deficit {total_deficit}"
    )

    # 2. Hard integrity validation
    violations = validate_schedule_integrity(students, coaches, result, DEFAULT_CONFIG)
    assert len(violations) == 0, f"Integrity violations found in October schedule: {violations[:5]}"

    # 3. Monthly Excel Export
    excel_bytes, is_valid, export_violations = generate_monthly_matrix_excel(
        result=result,
        students=students,
        coaches=coaches,
        config=DEFAULT_CONFIG
    )
    assert len(excel_bytes) > 5000, "Generated Excel byte stream is unexpectedly small"
    assert is_valid is True, f"Excel validation failed: {export_violations[:3]}"

# -----------------------------------------------------------------------------
# Test 2: November 2026 (30 Days) - Future Month without code changes
# -----------------------------------------------------------------------------
def test_2_future_month_november_2026(reference_data):
    students, coaches = reference_data
    start_date = date(2026, 11, 1)
    end_date = date(2026, 11, 30)

    result = run_scheduler(students, coaches, start_date, end_date, DEFAULT_CONFIG)
    assert result.start_date == "2026-11-01"
    assert result.end_date == "2026-11-30"

    violations = validate_schedule_integrity(students, coaches, result, DEFAULT_CONFIG)
    assert len(violations) == 0, f"Violations in November schedule: {violations[:5]}"

    excel_bytes, is_valid, _ = generate_monthly_matrix_excel(result, students, coaches, DEFAULT_CONFIG)
    assert len(excel_bytes) > 5000

# -----------------------------------------------------------------------------
# Test 3: December 2026 & January 2027
# -----------------------------------------------------------------------------
def test_3_december_and_january_future_months(reference_data):
    students, coaches = reference_data
    # December 2026 (31 days)
    res_dec = run_scheduler(students[:30], coaches, date(2026, 12, 1), date(2026, 12, 31), DEFAULT_CONFIG)
    v_dec = validate_schedule_integrity(students[:30], coaches, res_dec, DEFAULT_CONFIG)
    assert len(v_dec) == 0

    # January 2027 (31 days)
    res_jan = run_scheduler(students[:30], coaches, date(2027, 1, 1), date(2027, 1, 31), DEFAULT_CONFIG)
    v_jan = validate_schedule_integrity(students[:30], coaches, res_jan, DEFAULT_CONFIG)
    assert len(v_jan) == 0

# -----------------------------------------------------------------------------
# Test 4: Different number of students (Small scale vs Large scale)
# -----------------------------------------------------------------------------
def test_4_different_student_counts(reference_data):
    all_students, coaches = reference_data
    # 5 students
    res_5 = run_scheduler(all_students[:5], coaches, date(2026, 10, 1), date(2026, 10, 31), DEFAULT_CONFIG)
    assert res_5.total_students_considered == 5
    assert len(validate_schedule_integrity(all_students[:5], coaches, res_5, DEFAULT_CONFIG)) == 0

    # 40 students
    res_40 = run_scheduler(all_students[:40], coaches, date(2026, 10, 1), date(2026, 10, 31), DEFAULT_CONFIG)
    assert res_40.total_students_considered == 40
    assert len(validate_schedule_integrity(all_students[:40], coaches, res_40, DEFAULT_CONFIG)) == 0

# -----------------------------------------------------------------------------
# Test 5: New Coach Added
# -----------------------------------------------------------------------------
def test_5_new_coach_added(reference_data):
    students, coaches = reference_data
    new_coach = CoachModel(
        coach_name="MasterGrandmaster",
        levels_handled=["Beginner 1", "Beginner 2", "Intermediate"],
        monthly_capacity_min=20,
        monthly_capacity_max=60,
        mon_max=4, tue_max=4, wed_max=4, thu_max=4, fri_max=4, sat_max=5, sun_max=2
    )
    expanded_coaches = list(coaches) + [new_coach]

    res = run_scheduler(students[:20], expanded_coaches, date(2026, 10, 1), date(2026, 10, 31), DEFAULT_CONFIG)
    violations = validate_schedule_integrity(students[:20], expanded_coaches, res, DEFAULT_CONFIG)
    assert len(violations) == 0

# -----------------------------------------------------------------------------
# Test 6: Coach Removed
# -----------------------------------------------------------------------------
def test_6_coach_removed(reference_data):
    students, coaches = reference_data
    # Remove Dhaanush
    reduced_coaches = [c for c in coaches if "dhaanush" not in c.coach_name.lower()]
    assert len(reduced_coaches) == len(coaches) - 1

    res = run_scheduler(students[:25], reduced_coaches, date(2026, 10, 1), date(2026, 10, 31), DEFAULT_CONFIG)
    violations = validate_schedule_integrity(students[:25], reduced_coaches, res, DEFAULT_CONFIG)
    assert len(violations) == 0

# -----------------------------------------------------------------------------
# Test 7: Changed Coach Capability
# -----------------------------------------------------------------------------
def test_7_changed_coach_capability(reference_data):
    students, coaches = reference_data
    # Restrict Prakash to only Basic 1
    modified_coaches = []
    for c in coaches:
        if c.coach_name.strip().lower() == "prakash":
            modified_coaches.append(CoachModel(
                coach_name=c.coach_name,
                levels_handled=["Basic 1"],
                monthly_capacity_min=10,
                monthly_capacity_max=50,
                mon_max=4, tue_max=4, wed_max=4, thu_max=4, fri_max=4, sat_max=5, sun_max=2
            ))
        else:
            modified_coaches.append(c)

    res = run_scheduler(students[:20], modified_coaches, date(2026, 10, 1), date(2026, 10, 31), DEFAULT_CONFIG)
    violations = validate_schedule_integrity(students[:20], modified_coaches, res, DEFAULT_CONFIG)
    assert len(violations) == 0

# -----------------------------------------------------------------------------
# Test 8: Changed Student Availability
# -----------------------------------------------------------------------------
def test_8_changed_student_availability():
    stu = StudentModel(
        student_id="STU_MON_ONLY",
        student_name="Monday Student",
        student_level="Basic 1",
        batch_type="G",
        required_classes=4,
        mon_pref="06:00 PM – 07:00 PM",
        tue_pref="Not Available",
        wed_pref="Not Available",
        thu_pref="Not Available",
        fri_pref="Not Available",
        sat_pref="Not Available",
        sun_pref="Not Available"
    )
    coach = CoachModel(
        coach_name="CoachMon",
        levels_handled=["Basic 1"],
        monthly_capacity_min=10,
        monthly_capacity_max=40,
        mon_max=4
    )
    res = run_scheduler([stu], [coach], date(2026, 10, 1), date(2026, 10, 31), DEFAULT_CONFIG)

    # Student must only be scheduled on Mondays
    for cls in res.scheduled_classes:
        assert cls.day == "Monday", f"Student scheduled on non-Monday: {cls.day}"
    assert len(validate_schedule_integrity([stu], [coach], res, DEFAULT_CONFIG)) == 0

# -----------------------------------------------------------------------------
# Test 9: Different Required Class Counts (4, 8, 12, 16, 24)
# -----------------------------------------------------------------------------
def test_9_different_class_quotas(reference_data):
    _, coaches = reference_data
    test_students = [
        StudentModel(student_id="S4", student_name="Stu 4", student_level="Beginner 1", batch_type="G", required_classes=4),
        StudentModel(student_id="S8", student_name="Stu 8", student_level="Beginner 1", batch_type="G", required_classes=8),
        StudentModel(student_id="S12", student_name="Stu 12", student_level="Beginner 1", batch_type="G", required_classes=12),
        StudentModel(student_id="S16", student_name="Stu 16", student_level="Beginner 1", batch_type="G", required_classes=16),
    ]
    res = run_scheduler(test_students, coaches, date(2026, 10, 1), date(2026, 10, 31), DEFAULT_CONFIG)

    # Verify no student exceeds their exact required quota
    sch_counts = {s.student_id: 0 for s in test_students}
    for cls in res.scheduled_classes:
        for sid in cls.student_ids:
            sch_counts[sid] += 1

    for s in test_students:
        assert sch_counts[s.student_id] <= s.required_classes
    assert len(validate_schedule_integrity(test_students, coaches, res, DEFAULT_CONFIG)) == 0

# -----------------------------------------------------------------------------
# Test 10: February with 28 and 29 days (Leap Year vs Non-Leap Year)
# -----------------------------------------------------------------------------
def test_10_february_28_and_29_days(reference_data):
    students, coaches = reference_data

    # Non-leap year February 2027 (28 days)
    res_feb27 = run_scheduler(students[:15], coaches, date(2027, 2, 1), date(2027, 2, 28), DEFAULT_CONFIG)
    assert res_feb27.start_date == "2027-02-01"
    assert res_feb27.end_date == "2027-02-28"
    assert len(validate_schedule_integrity(students[:15], coaches, res_feb27, DEFAULT_CONFIG)) == 0

    # Leap year February 2028 (29 days)
    res_feb28 = run_scheduler(students[:15], coaches, date(2028, 2, 1), date(2028, 2, 29), DEFAULT_CONFIG)
    assert res_feb28.start_date == "2028-02-01"
    assert res_feb28.end_date == "2028-02-29"
    assert len(validate_schedule_integrity(students[:15], coaches, res_feb28, DEFAULT_CONFIG)) == 0

# -----------------------------------------------------------------------------
# Test 11: Coach Capacity Exhaustion
# -----------------------------------------------------------------------------
def test_11_coach_capacity_exhaustion():
    # 2 students needing 10 classes = 20 classes total, but coach capped at 5
    students = [
        StudentModel(student_id="S_CAP1", student_name="Cap 1", student_level="Basic 1", batch_type="G", required_classes=10),
        StudentModel(student_id="S_CAP2", student_name="Cap 2", student_level="Basic 1", batch_type="G", required_classes=10)
    ]
    coaches = [
        CoachModel(coach_name="LimitedCoach", levels_handled=["Basic 1"], monthly_capacity_max=5, mon_max=2)
    ]
    res = run_scheduler(students, coaches, date(2026, 10, 1), date(2026, 10, 31), DEFAULT_CONFIG)

    # Total classes assigned to LimitedCoach cannot exceed 5
    coach_classes = [c for c in res.scheduled_classes if c.coach_name == "LimitedCoach"]
    assert len(coach_classes) <= 5

    # At least one student must have unscheduled deficit
    assert res.unscheduled_students_count > 0
    assert any("COACH_MONTHLY_CAPACITY" in u.failure_reason or "capacity" in u.failure_reason.lower() for u in res.unscheduled_records)

# -----------------------------------------------------------------------------
# Test 12: Impossible Student (Available 0 days) -> Must appear in Attention Required
# -----------------------------------------------------------------------------
def test_12_impossible_student_appears_in_attention_required():
    impossible_student = StudentModel(
        student_id="IMPOSSIBLE_01",
        student_name="Never Available",
        student_level="Basic 1",
        batch_type="G",
        required_classes=12,
        mon_pref="Not Available",
        tue_pref="Not Available",
        wed_pref="Not Available",
        thu_pref="Not Available",
        fri_pref="Not Available",
        sat_pref="Not Available",
        sun_pref="Not Available"
    )
    coach = CoachModel(coach_name="AnyCoach", levels_handled=["Basic 1"], monthly_capacity_max=100)

    res = run_scheduler([impossible_student], [coach], date(2026, 10, 1), date(2026, 10, 31), DEFAULT_CONFIG)

    assert res.unscheduled_students_count == 1
    assert len(res.unscheduled_records) == 1
    unmet = res.unscheduled_records[0]
    assert unmet.student_id == "IMPOSSIBLE_01"
    assert unmet.remaining_classes == 12
    assert "STUDENT_UNAVAILABLE" in unmet.failure_reason

# -----------------------------------------------------------------------------
# Test 13: Determinism Guarantee (Same inputs + seed = Same output)
# -----------------------------------------------------------------------------
def test_13_determinism_guarantee(reference_data):
    students, coaches = reference_data
    sub_students = students[:25]

    res1 = run_dynamic_scheduler(sub_students, coaches, date(2026, 10, 1), date(2026, 10, 31), DEFAULT_CONFIG, random_seed=42)
    res2 = run_dynamic_scheduler(sub_students, coaches, date(2026, 10, 1), date(2026, 10, 31), DEFAULT_CONFIG, random_seed=42)

    assert len(res1.scheduled_classes) == len(res2.scheduled_classes)
    for c1, c2 in zip(res1.scheduled_classes, res2.scheduled_classes):
        assert c1.date == c2.date
        assert c1.time_slot == c2.time_slot
        assert c1.coach_name == c2.coach_name
        assert c1.batch_name == c2.batch_name
        assert c1.student_ids == c2.student_ids
