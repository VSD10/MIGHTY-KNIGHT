import pytest
from datetime import datetime
from app.engine.coach_availability_service import (
    calculate_coach_availability_records,
    get_unified_coaches_dict,
    parse_time_to_minutes,
    check_intervals_overlap
)
from app.storage.database import (
    save_deleted_record_db,
    get_deleted_records_db,
    update_deleted_record_scope_db,
    permanently_delete_record_db,
    save_single_coach_db,
    delete_single_coach_db
)
from app.engine.effective_schedule_service import get_effective_schedule

def test_output1_daily_whatsapp_format_and_batch_details():
    """Verify that Output 1 coach slots include batch details and student information for WhatsApp export."""
    eff = get_effective_schedule("2026-10")
    coach_slots = eff.get("coach_slots", [])
    assert len(coach_slots) > 0, "Expected coach slots in authoritative schedule"

    # Verify every slot has date, day, time_slot, coaches, and batches with summaries
    first_slot = coach_slots[0]
    assert "date" in first_slot
    assert "day" in first_slot
    assert "time_slot" in first_slot
    assert "coaches" in first_slot
    assert "batches" in first_slot
    assert len(first_slot["batches"]) > 0

    first_batch = first_slot["batches"][0]
    assert "summary" in first_batch
    assert len(first_batch["summary"]) > 0
    # Summary should contain coach and students or batch information
    assert ":" in first_batch["summary"] or len(first_batch["summary"]) > 5

def test_coach_availability_calculation():
    """Verify coach availability calculation compares preferred hours against occupied classes."""
    records = calculate_coach_availability_records()
    assert len(records) > 0

    # Ensure all required columns are present in each record
    for rec in records[:10]:
        assert "date" in rec
        assert "day" in rec
        assert "coach_name" in rec
        assert "preferred_hours" in rec
        assert "assigned_classes" in rec
        assert "occupied_slots" in rec
        assert "available_slots" in rec
        assert "qualified_levels" in rec
        assert "status" in rec

        # Check that remaining slots are explicit 1-hour strings or empty
        for slot in rec["available_slots"]:
            assert "-" in slot
            assert "AM" in slot or "PM" in slot

def test_intervals_overlap_helper():
    assert check_intervals_overlap(18 * 60, 18 * 60, 60) is True
    assert check_intervals_overlap(18 * 60, 19 * 60, 60) is False
    assert check_intervals_overlap(18 * 60, int(18.5 * 60), 60) is True

def test_unified_coaches_dict_includes_newly_registered():
    """Verify that newly registered master coaches appear in unified coaches dict without regeneration."""
    test_coach_name = "COACH AUTOMATED_TEST_NEW"
    try:
        save_single_coach_db({
            "coach_name": test_coach_name,
            "levels_handled": ["1", "2", "3"],
            "mon_max": 3,
            "tue_max": 3,
            "wed_max": 3,
            "thu_max": 3,
            "fri_max": 3,
            "monthly_capacity_max": 40,
            "availability": {
                "Monday": ["17:00-20:00"],
                "Tuesday": ["17:00-20:00"]
            }
        })

        unified = get_unified_coaches_dict()
        lookup_key = test_coach_name.upper()
        assert lookup_key in unified, f"Expected {lookup_key} in unified coaches"
        assert "1" in unified[lookup_key]["levels"]
        assert unified[lookup_key]["monthly_max"] == 40
        assert unified[lookup_key]["is_registered"] is True
    finally:
        delete_single_coach_db(test_coach_name)

def test_deleted_records_three_scopes_and_lifecycle():
    """Verify the 3 deletion scopes: remove_from_schedule, archive, permanently_delete, and restore."""
    record_id = "test_del_record_123"
    try:
        # 1. Save deleted record with scope 'remove_from_schedule'
        save_deleted_record_db({
            "record_id": record_id,
            "record_type": "coach",
            "record_name": "Test Deleted Coach",
            "deletion_scope": "remove_from_schedule",
            "deleted_at": datetime.now().isoformat(),
            "deleted_by": "Test Suite",
            "historical_classes_preserved": 5,
            "affected_future_classes": 2,
            "notes": "Testing deletion scopes"
        })

        records = get_deleted_records_db()
        matching = [r for r in records if r.get("record_id") == record_id]
        assert len(matching) == 1
        assert matching[0]["deletion_scope"] == "remove_from_schedule"
        assert matching[0]["historical_classes_preserved"] == 5
        assert matching[0]["affected_future_classes"] == 2

        # 2. Update scope to 'archive'
        update_deleted_record_scope_db(record_id, "archive")
        records = get_deleted_records_db()
        matching = [r for r in records if r.get("record_id") == record_id]
        assert matching[0]["deletion_scope"] == "archive"

        # 3. Restore to active
        update_deleted_record_scope_db(record_id, "restored_active")
        records = get_deleted_records_db()
        matching = [r for r in records if r.get("record_id") == record_id]
        assert matching[0]["deletion_scope"] == "restored_active"

        # 4. Permanently delete
        permanently_delete_record_db(record_id)
        records = get_deleted_records_db()
        matching = [r for r in records if r.get("record_id") == record_id]
        assert len(matching) == 0

    finally:
        permanently_delete_record_db(record_id)
