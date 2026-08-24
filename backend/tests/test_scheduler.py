import os
from datetime import date
from app.ingestion.excel_parser import parse_excel_file
from app.config import DEFAULT_CONFIG
from app.engine.scheduler import run_scheduler

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

    # Assert WhatsApp output data structure present
    for slot in result.coach_schedule:
        assert slot.date is not None
        assert slot.day is not None
        assert slot.time_slot is not None
        assert isinstance(slot.coaches, list)
