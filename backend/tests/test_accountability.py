from datetime import date
from app.models.student import StudentModel
from app.models.coach import CoachModel
from app.config import DEFAULT_CONFIG
from app.engine.scheduler import run_scheduler

def test_accountability_rule_no_silent_drops():
    students = [
        StudentModel(student_id="S1", student_name="Student 1", student_level="Basic 1", batch_type="G", required_classes=8),
        StudentModel(student_id="S2", student_name="Student 2", student_level="Intermediate", batch_type="I", required_classes=4),
        StudentModel(student_id="S3", student_name="Student 3", student_level="Beginner 1", batch_type="L", required_classes=8)
    ]
    coaches = [
        CoachModel(coach_name="Bathrinath", levels_handled=["Basic 1"], mon_max=4)
    ]

    # Run scheduler for a single date
    result = run_scheduler(
        students=students,
        coaches=coaches,
        start_date=date(2026, 8, 24),
        end_date=date(2026, 8, 24),
        config=DEFAULT_CONFIG
    )

    # Assert accountability rule holds: total_students == scheduled + unscheduled
    total_input = len(students)
    scheduled_ids = set()
    for c in result.scheduled_classes:
        for sid in c.student_ids:
            scheduled_ids.add(sid)

    unscheduled_ids = set(r.student_id for r in result.unscheduled_records)

    # Every student MUST be represented in either scheduled_ids or unscheduled_ids
    all_accounted_ids = scheduled_ids.union(unscheduled_ids)
    assert len(all_accounted_ids) == total_input, f"Mismatch: {len(all_accounted_ids)} accounted vs {total_input} total input"
    assert result.accountability_passed is True

    # Check that S2 (Intermediate) has an explicit failure reason since no Intermediate coach was passed!
    s2_record = next((r for r in result.unscheduled_records if r.student_id == "S2"), None)
    assert s2_record is not None
    assert "No coach qualified" in s2_record.failure_reason or "No eligible coach" in s2_record.failure_reason
