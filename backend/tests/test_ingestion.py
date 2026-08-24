import os
import pytest
from app.ingestion.excel_parser import parse_excel_file
from app.config import DEFAULT_CONFIG

def test_parse_sample_template():
    sample_path = "sample_data/mighty_knight_template.xlsx"
    assert os.path.exists(sample_path), f"{sample_path} does not exist"

    with open(sample_path, "rb") as f:
        content = f.read()

    students, coaches, errors = parse_excel_file(content, DEFAULT_CONFIG)

    # Assert coaches parsed
    assert len(coaches) == 8, f"Expected 8 coaches, got {len(coaches)}"
    coach_names = [c.coach_name for c in coaches]
    expected_coaches = ["Guruvanthana", "Dhaanush", "Arshath", "Saravanan", "Bathrinath", "Abinaya", "Prakash", "Manikandan"]
    for ec in expected_coaches:
        assert ec in coach_names, f"Coach {ec} missing"

    # Assert students parsed
    assert len(students) >= 18, f"Expected at least 18 students, got {len(students)}"
    
    # Assert no severe errors
    fatal_errors = [e for e in errors if e.get("severity") == "ERROR"]
    assert len(fatal_errors) == 0, f"Fatal errors during ingestion: {fatal_errors}"

def test_parser_resilience_and_validation():
    # Test parsing invalid content or missing values does not crash
    from sample_generator import generate_sample_excel
    sample_path = "sample_data/mighty_knight_template.xlsx"
    generate_sample_excel(sample_path)
    
    with open(sample_path, "rb") as f:
        students, coaches, errors = parse_excel_file(f.read(), DEFAULT_CONFIG)
        
    assert len(students) > 0
    assert len(coaches) == 8
