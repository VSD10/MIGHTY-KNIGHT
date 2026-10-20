import pytest
import datetime
from app.constants.batch_naming import (
    BATCH_TYPES, SUBDIVISION_CAPACITIES, LEVEL_TO_CODE, CODE_TO_LEVEL,
    extract_source_suffix_tag, format_batch_subdivision_name,
    parse_batch_subdivision_name, allocate_students_to_subdivisions,
    normalize_batch_name_to_subdivision
)
from app.engine.reference_scheduler import generate_reference_schedule, get_reference_engine
from app.storage.database import load_master_batches_db, load_master_data_db

def test_level_codes_and_batch_types():
    # Basic 1 & 2
    assert format_batch_subdivision_name("G", "Basic 1", 1) == "GB1-01"
    assert format_batch_subdivision_name("L", "Basic 1", 1) == "LB1-01"
    assert format_batch_subdivision_name("I", "Basic 1", 1) == "IB1-01"
    assert format_batch_subdivision_name("G", "Basic 2", 1) == "GB2-01"
    assert format_batch_subdivision_name("L", "Basic 2", 1) == "LB2-01"
    assert format_batch_subdivision_name("I", "Basic 2", 1) == "IB2-01"

    # Beginner 1 & 2
    assert format_batch_subdivision_name("G", "Beginner 1", 1) == "GBN1-01"
    assert format_batch_subdivision_name("L", "Beginner 1", 1) == "LBN1-01"
    assert format_batch_subdivision_name("I", "Beginner 1", 1) == "IBN1-01"
    assert format_batch_subdivision_name("G", "Beginner 2", 1) == "GBN2-01"
    assert format_batch_subdivision_name("L", "Beginner 2", 1) == "LBN2-01"
    assert format_batch_subdivision_name("I", "Beginner 2", 1) == "IBN2-01"

    # Early Intermediate 1 & 2
    assert format_batch_subdivision_name("G", "Early Intermediate 1", 1) == "GEM1-01"
    assert format_batch_subdivision_name("L", "Early Intermediate 1", 1) == "LEM1-01"
    assert format_batch_subdivision_name("I", "Early Intermediate 1", 1) == "IEM1-01"
    assert format_batch_subdivision_name("G", "Early Intermediate 2", 1) == "GEM2-01"
    assert format_batch_subdivision_name("L", "Early Intermediate 2", 1) == "LEM2-01"
    assert format_batch_subdivision_name("I", "Early Intermediate 2", 1) == "IEM2-01"

    # Intermediate 1 & 2
    assert format_batch_subdivision_name("G", "Intermediate 1", 1) == "GIM1-01"
    assert format_batch_subdivision_name("L", "Intermediate 1", 1) == "LIM1-01"
    assert format_batch_subdivision_name("I", "Intermediate 1", 1) == "IIM1-01"
    assert format_batch_subdivision_name("G", "Intermediate 2", 1) == "GIM2-01"
    assert format_batch_subdivision_name("L", "Intermediate 2", 1) == "LIM2-01"
    assert format_batch_subdivision_name("I", "Intermediate 2", 1) == "IIM2-01"

def test_source_tag_extraction():
    # Historical source tags: [A], [B], [C], [D], [S]
    tag, core = extract_source_suffix_tag("L Beginner1B")
    assert tag == "[B]"
    assert "Beginner1" in core

    tag, core = extract_source_suffix_tag("G beginner1C")
    assert tag == "[C]"
    assert "beginner1" in core

    tag, core = extract_source_suffix_tag("G Basic2A")
    assert tag == "[A]"
    assert "Basic2" in core

    tag, core = extract_source_suffix_tag("G Beginner2s")
    assert tag == "[S]"
    assert "Beginner2" in core

    tag, core = extract_source_suffix_tag("G beginner1d")
    assert tag == "[D]"
    assert "beginner1" in core

def test_sequential_overflow_rule_1():
    # 19 students in GBN1 must be allocated as GBN1-01 (8), GBN1-02 (8), and GBN1-03 (3)
    sample_students = [
        {"student_id": f"TEST_{i:03d}", "student_name": f"Student {i}", "student_level": "Beginner 1", "batch_type": "G"}
        for i in range(1, 20)
    ]
    subdivisions, warnings = allocate_students_to_subdivisions(sample_students)
    assert len(subdivisions) == 3
    assert subdivisions[0]["batch_name"] == "GBN1-01"
    assert subdivisions[0]["student_count"] == 8
    assert subdivisions[1]["batch_name"] == "GBN1-02"
    assert subdivisions[1]["student_count"] == 8
    assert subdivisions[2]["batch_name"] == "GBN1-03"
    assert subdivisions[2]["student_count"] == 3
    assert len(warnings) == 0

def test_strict_capacities():
    assert SUBDIVISION_CAPACITIES["G"]["max"] == 8
    assert SUBDIVISION_CAPACITIES["L"]["max"] == 3
    assert SUBDIVISION_CAPACITIES["I"]["max"] == 1

def test_master_batches_in_db():
    from app.storage.database import seed_october_baseline_if_missing
    seed_october_baseline_if_missing()
    batches = load_master_batches_db()
    assert len(batches) >= 30
    for b in batches:
        # Every batch follows [BatchType][LevelCode]-[SubdivisionNumber]
        parsed = parse_batch_subdivision_name(b["batch_name"])
        assert parsed is not None, f"Batch name '{b['batch_name']}' does not match pattern"
        if b["batch_type"] == "G":
            assert b["capacity_max"] == 8
        elif b["batch_type"] == "L":
            assert b["capacity_max"] == 3
        elif b["batch_type"] == "I":
            assert b["capacity_max"] == 1

def test_future_month_dynamic_generation_rule_2():
    # Rule 2: Dynamically map learned patterns onto November 2026 calendar
    s_date = datetime.date(2026, 11, 1)
    e_date = datetime.date(2026, 11, 30)
    result = generate_reference_schedule(s_date, e_date)
    assert len(result.scheduled_classes) > 0
    # Dates must be in November
    for c in result.scheduled_classes:
        assert c.date.startswith("2026-11")
        assert c.batch_name is not None
