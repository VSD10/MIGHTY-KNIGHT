from datetime import date
from app.ingestion.excel_parser import parse_excel_file
from app.config import DEFAULT_CONFIG
from app.engine.scheduler import run_scheduler
from app.outputs.coach_schedule import generate_coach_schedule_text
from app.outputs.admin_schedule import format_admin_schedule
from app.outputs.attention_report import format_attention_report
from app.outputs.student_schedule import format_student_schedules

def test_all_three_outputs():
    with open("sample_data/mighty_knight_template.xlsx", "rb") as f:
        students, coaches, errors = parse_excel_file(f.read(), DEFAULT_CONFIG)

    result = run_scheduler(students, coaches, date(2026, 8, 24), date(2026, 8, 30), DEFAULT_CONFIG)

    # Test Output 1: Coach Communication Schedule plain text
    whatsapp_text = generate_coach_schedule_text(result)
    assert "MIGHTY KNIGHT — COACH SCHEDULE" in whatsapp_text
    assert "Monday, August 24, 2026" in whatsapp_text or "2026-08-24" in whatsapp_text

    # Test Output 2: Detailed Administrative Schedule
    admin_rows = format_admin_schedule(result)
    assert len(admin_rows) == len(result.scheduled_classes)
    for r in admin_rows:
        assert "coach_name" in r
        assert "student_level" in r
        assert "students_formatted" in r

    # Test Output 3: Unscheduled / Attention Report
    attention_rows = format_attention_report(result)
    assert len(attention_rows) == len(result.unscheduled_records)
    for r in attention_rows:
        assert "student_id" in r
        assert "failure_reason" in r

    # Test Output 5: Student-Wise Schedules
    master_stu_dicts = [s.model_dump() for s in students]
    student_schedules = format_student_schedules(result, master_stu_dicts)
    assert len(student_schedules) > 0
    for s in student_schedules:
        assert "student_id" in s
        assert "student_name" in s
        assert "sessions" in s
        for sess in s["sessions"]:
            assert "date" in sess
            assert "day" in sess
            assert "time" in sess
            assert "coach" in sess
            assert "session" in sess

