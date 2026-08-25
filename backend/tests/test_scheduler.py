import os
from datetime import date
from app.ingestion.excel_parser import parse_excel_file
from app.config import DEFAULT_CONFIG
from app.engine.scheduler import run_scheduler, validate_schedule_integrity

def test_full_scheduler_end_to_end():
    sample_path = "sample_data/mighty_knight_template.xlsx"
    assert os.path.exists(sample_path)

    with open(sample_path, "rb") as f:
        students, coaches, errors = parse_excel_file(f.read(), DEFAULT_CONFIG)

    assert len(students) > 0
    assert len(coaches) == 8

    start_date = date(2026, 8, 24) # Monday
    end_date = date(2026, 8, 30)   # Sunday

    result = run_scheduler(
        students=students,
        coaches=coaches,
        start_date=start_date,
        end_date=end_date,
        config=DEFAULT_CONFIG
    )

    assert result is not None
    assert result.total_students_considered == len(students)
    assert result.accountability_passed is True
    assert len(result.scheduled_classes) > 0
    assert len(result.coach_schedule) > 0

    # Hard final validation assertion
    violations = validate_schedule_integrity(students, coaches, result, DEFAULT_CONFIG)
    assert len(violations) == 0, f"Validation violations: {violations}"

def test_group_batch_minimum_and_one_class_per_day():
    sample_path = "sample_data/mighty_knight_template.xlsx"
    with open(sample_path, "rb") as f:
        students, coaches, errors = parse_excel_file(f.read(), DEFAULT_CONFIG)

    result = run_scheduler(
        students=students,
        coaches=coaches,
        start_date=date(2026, 8, 24),
        end_date=date(2026, 8, 30),
        config=DEFAULT_CONFIG
    )

    # 1. Assert no group batch has fewer than min_capacity (4) students or more than max_capacity (10)
    min_group_cap = DEFAULT_CONFIG.batch_types["G"].min_capacity
    max_group_cap = DEFAULT_CONFIG.batch_types["G"].max_capacity
    for cls in result.scheduled_classes:
        if cls.batch_type == "G":
            assert len(cls.student_ids) >= min_group_cap, f"Class {cls.class_id} had {len(cls.student_ids)} students, below min {min_group_cap}"
            assert len(cls.student_ids) <= max_group_cap, f"Class {cls.class_id} had {len(cls.student_ids)} students, above max {max_group_cap}"

    # 2. Assert no student has more than 1 class per day
    student_date_counts = {}
    for cls in result.scheduled_classes:
        for sid in cls.student_ids:
            key = (sid, cls.date)
            student_date_counts[key] = student_date_counts.get(key, 0) + 1
            assert student_date_counts[key] == 1, f"Student {sid} assigned multiple classes on {cls.date}"

def test_exact_required_classes_accounting():
    sample_path = "sample_data/mighty_knight_template.xlsx"
    with open(sample_path, "rb") as f:
        students, coaches, errors = parse_excel_file(f.read(), DEFAULT_CONFIG)

    result = run_scheduler(
        students=students,
        coaches=coaches,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 31),
        config=DEFAULT_CONFIG
    )

    student_scheduled_counts = {}
    for cls in result.scheduled_classes:
        for sid in cls.student_ids:
            student_scheduled_counts[sid] = student_scheduled_counts.get(sid, 0) + 1

    unscheduled_map = {rec.student_id: rec.remaining_classes for rec in result.unscheduled_records}

    for s in students:
        s_id = s.student_id
        sch_cnt = student_scheduled_counts.get(s_id, 0)
        rem_cnt = unscheduled_map.get(s_id, 0)

        # 1. scheduled <= required
        assert sch_cnt <= s.required_classes, f"Student {s.student_id} over-scheduled ({sch_cnt} > {s.required_classes})"

        # 2. scheduled + remaining == required
        assert sch_cnt + rem_cnt == s.required_classes, f"Student {s.student_id} accounting error: {sch_cnt} + {rem_cnt} != {s.required_classes}"

def test_not_available_days_never_scheduled():
    sample_path = "sample_data/mighty_knight_template.xlsx"
    with open(sample_path, "rb") as f:
        students, coaches, errors = parse_excel_file(f.read(), DEFAULT_CONFIG)

    result = run_scheduler(
        students=students,
        coaches=coaches,
        start_date=date(2026, 8, 24),
        end_date=date(2026, 8, 30),
        config=DEFAULT_CONFIG
    )

    student_map = {s.student_id: s for s in students}
    for cls in result.scheduled_classes:
        for sid in cls.student_ids:
            s_obj = student_map[sid]
            assert s_obj.is_available_on_day(cls.day) is True, f"Student {sid} scheduled on unavailable day {cls.day}"
