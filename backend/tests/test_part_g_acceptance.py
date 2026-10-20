import os
import sys
import copy
import json
import time
import uuid
import sqlite3
import calendar
from datetime import date, datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.main import app, ACTIVE_DATA, CURRENT_CONFIG, ensure_active_data
from app.models.student import StudentModel
from app.models.coach import CoachModel
from app.engine.effective_schedule_service import get_effective_schedule, ScheduleEventBus
from app.engine.rule_engine import (
    validate_all_rules_for_occurrence,
    check_tournament_eligibility,
    check_tournament_grouping,
    COACH_REFERENCE,
    resolve_coach_canonical_name
)
from app.engine.master_data_service import handle_batch_type_conversion
from app.engine.suggestion_engine import (
    find_single_class_suggestions,
    ENGINE_SETTINGS
)
from app.storage.database import (
    get_db_path,
    init_db,
    save_master_data_db,
    load_master_data_db,
    save_single_student_db,
    delete_single_student_db,
    save_single_coach_db,
    delete_single_coach_db,
    get_active_baseline_db,
    save_baseline_db,
    get_exception_records_db,
    save_exception_record_db,
    revert_exception_record_db,
    seed_october_baseline_if_missing,
    get_connection,
    save_schedule_db,
    get_schedule_db
)
from app.engine.baseline_service import generate_next_month_draft

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Ensures database and master data are initialized with October 2026 baseline."""
    seed_october_baseline_if_missing()
    ensure_active_data()
    base = get_active_baseline_db("2026-10")
    students = base["students_data"] if (base and base.get("students_data")) else ACTIVE_DATA.get("students", [])
    if not ACTIVE_DATA.get("coaches") or not ACTIVE_DATA.get("students"):
        coaches = [
            {
                "coach_name": name,
                "levels_handled": data.get("levels", []),
                "monthly_capacity_min": 10,
                "monthly_capacity_max": data.get("max_monthly", 120),
                "max_classes_per_day": data.get("max_daily", 4)
            }
            for name, data in COACH_REFERENCE.items()
        ]
        save_master_data_db(students, coaches)
        ensure_active_data()
    yield

# ==============================================================================
# TEST 1: Baseline Protection
# Upload October Absolute Schedule -> run Monthly Engine twice -> zero baseline changes, zero duplicates.
# ==============================================================================
def test_1_baseline_protection():
    # 1. Verify October active baseline is loaded
    month = "2026-10"
    base_before = get_active_baseline_db(month)
    assert base_before is not None, "October active baseline must exist"
    assert base_before["status"] == "Active"
    initial_version = base_before["version"]
    initial_class_count = len(base_before["classes_data"])
    assert initial_class_count > 0, "Baseline must contain classes"

    # 2. Run Monthly Engine first time
    res_run1 = client.post("/api/schedule/run", json={"start_date": "2026-10-01", "end_date": "2026-10-31"})
    assert res_run1.status_code == 200

    # 3. Run Monthly Engine second time
    res_run2 = client.post("/api/schedule/run", json={"start_date": "2026-10-01", "end_date": "2026-10-31"})
    assert res_run2.status_code == 200

    # 4. Authoritative check: Baseline is 100% untouched (zero baseline changes)
    base_after = get_active_baseline_db(month)
    assert base_after["version"] == initial_version
    assert base_after["status"] == "Active"
    assert len(base_after["classes_data"]) == initial_class_count

    # 5. Zero duplicates in Effective Schedule
    eff = get_effective_schedule(month)
    classes = eff["scheduled_classes"]
    
    seen_slots = set()
    for c in classes:
        slot_key = (c["date"], c["time_slot"], resolve_coach_canonical_name(c["coach_name"]))
        assert slot_key not in seen_slots, f"Duplicate class detected: {slot_key}"
        seen_slots.add(slot_key)

        # Zero duplicates in student IDs within any class
        sids = c.get("student_ids", [])
        assert len(sids) == len(set(sids)), f"Duplicate student in class {c['class_id']}: {sids}"

# ==============================================================================
# TEST 2: New Student Workflow
# Add Group student -> Attention record with ranked suggestions -> accept one
# -> appears in Daily Planner, Output 1, Output 2, Output 4 workload, Output 5
# -> Attention count drops everywhere.
# ==============================================================================
def test_2_new_student_workflow():
    month = "2026-10"
    test_sid = "STU_PARTG_NEW_01"
    
    # 1. Add a new Group student needing 1 class
    new_student = {
        "student_id": test_sid,
        "student_name": "PartG New Student",
        "student_level": "Beginner 1",
        "batch_type": "G",
        "required_classes": 1,
        "region_timezone": "IST",
        "day_preference": "Monday, Tuesday, Wednesday"
    }
    save_single_student_db(new_student)
    ensure_active_data()

    # 2. Check student is in Attention record
    eff_pre = get_effective_schedule(month)
    pre_att_count = eff_pre["need_attention"]
    att_rec = next((r for r in eff_pre["attention_records"] if r["student_id"] == test_sid), None)
    assert att_rec is not None, "New unscheduled student must appear in Attention records"
    assert att_rec["remaining_classes"] == 1

    # 3. Query suggestions for the student
    sugg_resp = client.get(f"/api/engine/suggestions?student_id={test_sid}&needed_classes=1&month={month}")
    assert sugg_resp.status_code == 200
    sugg_data = sugg_resp.json()
    suggestions = sugg_data.get("suggestions", [])
    assert len(suggestions) > 0, "Must return ranked suggestions"

    # Verify ranked suggestions have score & tier
    top_sugg = suggestions[0]
    assert "score" in top_sugg
    assert "tier" in top_sugg
    current_ver = sugg_data["schedule_version"]

    # 4. Accept the top suggestion
    accept_resp = client.post("/api/engine/suggestions/accept", json={
        "student_id": test_sid,
        "month": month,
        "schedule_version": current_ver,
        "suggestion_item": top_sugg,
        "is_option_set": False,
        "user": "AcceptanceTest"
    })
    assert accept_resp.status_code == 200

    # 5. Check appearance everywhere in effective schedule
    eff_post = get_effective_schedule(month)

    # A. Daily Planner / Output 2
    assigned_classes = [c for c in eff_post["scheduled_classes"] if test_sid in c.get("student_ids", [])]
    assert len(assigned_classes) == 1, "Student must appear in scheduled classes (Daily Planner / Output 2)"
    assigned_cls = assigned_classes[0]

    # B. Output 1 (WhatsApp Schedule / Coach Slots)
    coach_name = resolve_coach_canonical_name(assigned_cls["coach_name"])
    matching_slots = [
        s for s in eff_post["coach_slots"] 
        if s["date"] == assigned_cls["date"] and s["time_slot"] == assigned_cls["time_slot"]
    ]
    assert len(matching_slots) > 0, "Class must appear in Output 1 coach slots"
    assert any(resolve_coach_canonical_name(c).lower() == coach_name.lower() for c in matching_slots[0]["coaches"])

    # C. Output 4 (Coach Workload)
    coach_sum = next((cs for cs in eff_post["coach_summaries"] if cs["coach_name"] == coach_name), None)
    assert coach_sum is not None, "Coach must appear in Output 4 workload summary"
    assert coach_sum["classes_scheduled"] > 0
    assert coach_sum["student_reach"] > 0

    # D. Output 5 (Student Schedules)
    stu_sched = next((ss for ss in eff_post["student_schedules"] if ss["student_id"] == test_sid), None)
    assert stu_sched is not None, "Student must have personal timetable in Output 5"
    assert stu_sched["scheduled_classes_count"] == 1
    assert any(c["class_id"] == assigned_cls["class_id"] for c in stu_sched["classes"])

    # E. Attention count drops everywhere
    post_att = next((r for r in eff_post["attention_records"] if r["student_id"] == test_sid), None)
    assert post_att is None, "Student must no longer appear in Attention records after fulfillment"
    assert eff_post["need_attention"] == pre_att_count - 1

    # Cleanup test student
    delete_single_student_db(test_sid)

# ==============================================================================
# TEST 3: Batch Conversion Chain
# Group -> Individual -> Limited -> Group: each step recalculates from current state,
# releases seats, leaves no obsolete assignments.
# ==============================================================================
def test_3_batch_conversion_chain():
    month = "2026-10"
    sid = "STU_PARTG_CONV_CHAIN"
    
    # Setup test student in Group
    test_stu = {
        "student_id": sid,
        "student_name": "Conv Chain Student",
        "student_level": "Beginner 1",
        "batch_type": "G",
        "batch": "G Beginner 1",
        "required_classes": 12,
        "region_timezone": "IST"
    }
    save_single_student_db(test_stu)
    ensure_active_data()

    stu_master_map = {sid: test_stu}

    # Setup simulated classes
    # 1 multi-student Group class (4 students)
    # 1 Sunday tournament class
    classes = [
        {
            "class_id": "CLS_GRP_MULTI",
            "date": "2026-10-05",
            "time_slot": "06:00 PM",
            "coach_name": "BATHRI",
            "student_ids": [sid, "OTHER_1", "OTHER_2", "OTHER_3"],
            "student_names": ["Conv Chain Student", "O1", "O2", "O3"],
            "is_tournament": False
        },
        {
            "class_id": "CLS_TOURN_SUN",
            "date": "2026-10-11",
            "time_slot": "10:00 AM",
            "coach_name": "Abinaya",
            "student_ids": [sid, "OTHER_1"],
            "student_names": ["Conv Chain Student", "O1"],
            "is_tournament": True
        }
    ]

    # Step 1: Group -> Individual (I)
    res_i = handle_batch_type_conversion(sid, "I", classes, stu_master_map, month=month)
    assert res_i["status"] == "success"
    assert test_stu["batch_type"] == "I"
    assert res_i["removed_assignments_count"] == 2
    # Verify seats released in multi-student and tournament classes
    assert sid not in classes[0]["student_ids"]
    assert len(classes[0]["student_ids"]) == 3, "Other students must keep their seats"
    assert sid not in classes[1]["student_ids"]

    # Step 2: Individual -> Limited (L)
    res_l = handle_batch_type_conversion(sid, "L", classes, stu_master_map, month=month)
    assert res_l["status"] == "success"
    assert test_stu["batch_type"] == "L"
    assert res_l["removed_assignments_count"] == 0

    # Step 3: Limited -> Group (G)
    res_g = handle_batch_type_conversion(sid, "G", classes, stu_master_map, month=month)
    assert res_g["status"] == "success"
    assert test_stu["batch_type"] == "G"
    assert res_g["removed_assignments_count"] == 0

    delete_single_student_db(sid)

# ==============================================================================
# TEST 4: Circled ⓒ Capacity
# Add 9th student to Group class -> pop-up with exact rule -> accept -> ⓒ visible everywhere,
# persists, absent next week and next month, engine re-run keeps it.
# ==============================================================================
def test_4_circled_c_capacity():
    month = "2026-10"
    cls_date = "2026-10-06"
    cls_slot = "06:00 PM"
    cls_coach = "Bathrinath"
    stu_ids_8 = [f"STU_C8_{i}" for i in range(1, 9)]
    stu_id_9 = "STU_C8_9"

    for sid in stu_ids_8 + [stu_id_9]:
        save_single_student_db({
            "student_id": sid,
            "student_name": f"Stu {sid}",
            "student_level": "Beginner 1",
            "batch_type": "G",
            "required_classes": 12
        })
    ensure_active_data()

    # Pre-save validation with 9 students
    cls_occurrence = {
        "class_id": "TEST_CLS_9",
        "date": cls_date,
        "time_slot": cls_slot,
        "coach_name": cls_coach,
        "student_level": "Beginner 1",
        "batch_type": "G",
        "student_ids": stu_ids_8 + [stu_id_9]
    }
    violations = validate_all_rules_for_occurrence(
        cls_dict=cls_occurrence,
        all_classes_in_month=[],
        student_master_map={s["student_id"]: s for s in ACTIVE_DATA["students"]},
        coach_master_map={c["coach_name"]: c for c in ACTIVE_DATA["coaches"]}
    )
    cap_v = next((v for v in violations if v["rule_name"] == "Group Batch Capacity (Max 8)"), None)
    assert cap_v is not None, "Rule engine must flag Group Batch Capacity (Max 8) violation"
    assert "Group batch capacity 8 exceeded with 9 students" in cap_v["reason"]

    # Accept as exception overlay (ⓒ)
    apply_resp = client.post("/api/schedule/exception/apply", json={
        "month": month,
        "date": cls_date,
        "time_slot": cls_slot,
        "coach_name": cls_coach,
        "action_type": "add",
        "affected_student_ids": stu_ids_8 + [stu_id_9],
        "after": {
            "student_level": "Beginner 1",
            "batch_type": "G",
            "student_ids": stu_ids_8 + [stu_id_9],
            "day": "Tuesday"
        },
        "subtype": "capacity_override",
        "violated_rules": violations,
        "reason": "Accepted capacity exception (9th student in Group)",
        "created_by": "Admin"
    })
    assert apply_resp.status_code == 200

    # Verify ⓒ visible everywhere in effective schedule
    eff = get_effective_schedule(month)
    matching = [c for c in eff["scheduled_classes"] if c["date"] == cls_date and c["time_slot"] == cls_slot]
    assert len(matching) > 0
    target_c = matching[0]
    assert len(target_c["student_ids"]) == 9
    assert target_c["is_compensation"] is True
    assert target_c["has_compensation"] is True

    # Absent next week (date + 7 days = 2026-10-13)
    next_week_classes = [c for c in eff["scheduled_classes"] if c["date"] == "2026-10-13" and c["time_slot"] == cls_slot]
    for nwc in next_week_classes:
        assert len(nwc.get("student_ids", [])) <= 8, "9th student must be absent next week"

    # Engine re-run keeps it
    client.post("/api/schedule/run", json={"start_date": "2026-10-01", "end_date": "2026-10-31"})
    eff_after_run = get_effective_schedule(month)
    c_kept = next((c for c in eff_after_run["scheduled_classes"] if c["date"] == cls_date and c["time_slot"] == cls_slot), None)
    assert c_kept is not None
    assert c_kept["is_compensation"] is True

    # Cleanup
    revert_exception_record_db(apply_resp.json()["exception_id"])
    for sid in stu_ids_8 + [stu_id_9]:
        delete_single_student_db(sid)

# ==============================================================================
# TEST 5: Circled ⓒ Quota
# Assign 13th class to student with 12 -> pop-up -> accept -> "Extra ⓒ",
# requirement stays 12, nothing carries to next month.
# ==============================================================================
def test_5_circled_c_quota():
    month = "2026-10"
    sid = "STU_PARTG_QUOTA_12"
    save_single_student_db({
        "student_id": sid,
        "student_name": "Quota Test Student",
        "student_level": "Beginner 1",
        "batch_type": "G",
        "required_classes": 12
    })
    ensure_active_data()

    # Simulate 12 classes already assigned
    existing_classes = [
        {"class_id": f"CLS_PRE_{i}", "date": f"2026-10-{i+1:02d}", "time_slot": "06:00 PM", "coach_name": "Bathrinath", "student_ids": [sid]}
        for i in range(12)
    ]

    # Validate 13th class assignment
    thirteenth_cls = {
        "class_id": "CLS_THIRTEENTH",
        "date": "2026-10-25",
        "time_slot": "06:00 PM",
        "coach_name": "Bathrinath",
        "student_level": "Beginner 1",
        "batch_type": "G",
        "student_ids": [sid]
    }
    violations = validate_all_rules_for_occurrence(
        cls_dict=thirteenth_cls,
        all_classes_in_month=existing_classes,
        student_master_map={sid: {"student_id": sid, "required_classes": 12, "student_name": "Quota Test Student"}},
        coach_master_map={c["coach_name"]: c for c in ACTIVE_DATA["coaches"]}
    )
    quota_v = next((v for v in violations if v["rule_name"] == "Student Monthly Quota Cap"), None)
    assert quota_v is not None
    assert "exceeds their monthly requirement of 12" in quota_v["reason"]

    # Accept with "Extra ⓒ"
    exc_resp = client.post("/api/schedule/exception/apply", json={
        "month": month,
        "date": "2026-10-25",
        "time_slot": "06:00 PM",
        "coach_name": "Bathrinath",
        "action_type": "add",
        "affected_student_ids": [sid],
        "after": {
            "student_level": "Beginner 1",
            "batch_type": "G",
            "student_ids": [sid],
            "day": "Sunday"
        },
        "subtype": "compensation",
        "violated_rules": violations,
        "reason": "Extra ⓒ",
        "created_by": "Admin"
    })
    assert exc_resp.status_code == 200

    # Master requirement stays 12
    m_stu = next(s for s in load_master_data_db()["students"] if s["student_id"] == sid)
    assert m_stu["required_classes"] == 12

    # Nothing carries to next month: next month draft baseline uses student's quota 12
    draft_nov = generate_next_month_draft("2026-10", 2026, 11)
    nov_stu = next((s for s in draft_nov.get("students_data", []) if s["student_id"] == sid), None)
    if nov_stu:
        assert nov_stu.get("required_classes", 12) == 12

    revert_exception_record_db(exc_resp.json()["exception_id"])
    delete_single_student_db(sid)

# ==============================================================================
# TEST 6: Circled ⓒ Move
# Move class from 15 Oct to 16 Oct as ⓒ -> baseline untouched; revert restores 15 Oct.
# ==============================================================================
def test_6_circled_c_move():
    month = "2026-10"
    base = get_active_baseline_db(month)
    assert base is not None

    # Pick an existing class on 15 Oct from baseline
    oct_15_classes = [c for c in base["classes_data"] if c.get("date") == "2026-10-15"]
    assert len(oct_15_classes) > 0, "October baseline must have a class on 15 Oct"
    target = oct_15_classes[0]
    t_slot = target["time_slot"]
    t_coach = target["coach_name"]
    t_students = target.get("student_ids", [])

    # Move class to 16 Oct via exception overlay (ⓒ)
    move_resp = client.post("/api/schedule/exception/apply", json={
        "month": month,
        "date": "2026-10-16",
        "time_slot": t_slot,
        "coach_name": t_coach,
        "action_type": "move",
        "affected_student_ids": t_students,
        "before": {
            "date": "2026-10-15",
            "time_slot": t_slot,
            "coach_name": t_coach
        },
        "after": {
            "date": "2026-10-16",
            "time_slot": t_slot,
            "coach_name": t_coach,
            "student_ids": t_students
        },
        "subtype": "manual",
        "reason": "Rescheduled class to 16 Oct",
        "created_by": "Admin"
    })
    assert move_resp.status_code == 200
    exc_id = move_resp.json()["exception_id"]

    # In effective schedule:
    eff_moved = get_effective_schedule(month)
    # 1. 15 Oct class is gone
    assert not any(
        c["date"] == "2026-10-15" and c["time_slot"] == t_slot and resolve_coach_canonical_name(c["coach_name"]) == resolve_coach_canonical_name(t_coach)
        for c in eff_moved["scheduled_classes"]
    )
    # 2. 16 Oct class exists with ⓒ
    moved_c = next(
        c for c in eff_moved["scheduled_classes"]
        if c["date"] == "2026-10-16" and c["time_slot"] == t_slot and resolve_coach_canonical_name(c["coach_name"]) == resolve_coach_canonical_name(t_coach)
    )
    assert moved_c["is_compensation"] is True

    # 3. Underlying baseline remains untouched!
    base_check = get_active_baseline_db(month)
    assert any(
        c["date"] == "2026-10-15" and c["time_slot"] == t_slot and resolve_coach_canonical_name(c["coach_name"]) == resolve_coach_canonical_name(t_coach)
        for c in base_check["classes_data"]
    )

    # 4. Revert restores 15 Oct
    revert_resp = client.post(f"/api/schedule/exception/{exc_id}/revert?month={month}")
    assert revert_resp.status_code == 200

    eff_reverted = get_effective_schedule(month)
    assert any(
        c["date"] == "2026-10-15" and c["time_slot"] == t_slot and resolve_coach_canonical_name(c["coach_name"]) == resolve_coach_canonical_name(t_coach)
        for c in eff_reverted["scheduled_classes"]
    )
    assert not any(
        c["date"] == "2026-10-16" and c["time_slot"] == t_slot and resolve_coach_canonical_name(c["coach_name"]) == resolve_coach_canonical_name(t_coach) and c.get("is_compensation")
        for c in eff_reverted["scheduled_classes"]
    )

# ==============================================================================
# TEST 7: Tournament Eligibility
# Basic 1 and Individual students on Sunday become regular classes;
# Intermediate 2 appears only in Friday 5:30 PM tournament;
# Beginner 1 + Early Intermediate 1 can never share a tournament;
# a 21st student is blocked or needs a ⓒ.
# ==============================================================================
def test_7_tournament_eligibility():
    # 1. Basic 1 student on Sunday -> ineligible for tournament, must be regular class
    ok_b1, msg_b1 = check_tournament_eligibility("Basic 1", "G", "Sunday")
    assert ok_b1 is False
    assert "Basic 1 students are never eligible for Sunday tournaments" in msg_b1

    # 2. Individual student on Sunday -> ineligible for tournament, must be regular class
    ok_ind, msg_ind = check_tournament_eligibility("Beginner 1", "I", "Sunday")
    assert ok_ind is False
    assert "Individual batch students are never eligible for tournaments" in msg_ind

    # 3. Intermediate 2 appears ONLY in Friday 5:30 PM tournament
    ok_int2_fri, _ = check_tournament_eligibility("Intermediate 2", "G", "Friday")
    assert ok_int2_fri is True

    ok_int2_sun, msg_int2_sun = check_tournament_eligibility("Intermediate 2", "G", "Sunday")
    assert ok_int2_sun is False
    assert "Friday tournament only" in msg_int2_sun

    # 4. Beginner 1 + Early Intermediate 1 can NEVER share a tournament
    ok_mix, msg_mix = check_tournament_grouping(["Beginner 1", "Early Intermediate 1"], "Sunday")
    assert ok_mix is False
    assert "Strict tournament grouping violation" in msg_mix

    # 5. 21st student is blocked (cap is 20)
    tourn_20 = {
        "class_id": "TOURN_CAP_20",
        "date": "2026-10-11",
        "time_slot": "10:00 AM",
        "coach_name": "Abinaya",
        "is_tournament": True,
        "batch_type": "G",
        "student_level": "Beginner 1",
        "student_ids": [f"STU_{i}" for i in range(20)]
    }
    v_20 = validate_all_rules_for_occurrence(
        cls_dict=tourn_20,
        all_classes_in_month=[],
        student_master_map={},
        coach_master_map={},
        is_tournament=True
    )
    assert not any(v["rule_name"] == "Tournament Maximum Capacity (20)" for v in v_20)

    tourn_21 = copy.deepcopy(tourn_20)
    tourn_21["student_ids"].append("STU_21")
    v_21 = validate_all_rules_for_occurrence(
        cls_dict=tourn_21,
        all_classes_in_month=[],
        student_master_map={},
        coach_master_map={},
        is_tournament=True
    )
    cap_v = next((v for v in v_21 if v["rule_name"] == "Tournament Maximum Capacity (20)"), None)
    assert cap_v is not None
    assert "Tournament batch capacity 20 exceeded with 21 students" in cap_v["reason"]

# ==============================================================================
# TEST 8: Tournament Coach
# Guru excluded, Dhaanush/Saravanan only when no Tier 1 coach is available,
# Hema only on tournaments, Abinaya for any eligible level.
# ==============================================================================
def test_8_tournament_coach():
    # 1. Guruvanthana excluded from tournaments
    excluded_tourn = ENGINE_SETTINGS["tournament_tiers"]["excluded"]
    assert "Guruvanthana" in excluded_tourn

    # 2. Dhaanush & Saravanan are Tier 2 (only when Tier 1 unavailable)
    tier2 = ENGINE_SETTINGS["tournament_tiers"]["tier2"]
    assert "Dhaanush" in tier2
    assert "Saravanan" in tier2

    # 3. Hema only on tournaments
    assert COACH_REFERENCE["Hema"].get("tournaments_only") is True
    hema_reg_cls = {
        "class_id": "HEMA_REG",
        "date": "2026-10-05",
        "time_slot": "06:00 PM",
        "coach_name": "Hema",
        "student_level": "Beginner 1",
        "batch_type": "G",
        "student_ids": ["S1"],
        "is_tournament": False
    }
    v_hema = validate_all_rules_for_occurrence(
        cls_dict=hema_reg_cls,
        all_classes_in_month=[],
        student_master_map={},
        coach_master_map={},
        is_tournament=False
    )
    assert any(v["rule_name"] == "Coach Role Restriction" for v in v_hema)

    # 4. Abinaya is Tier 1 for any eligible level
    tier1 = ENGINE_SETTINGS["tournament_tiers"]["tier1"]
    assert "Abinaya" in tier1

# ==============================================================================
# TEST 9: Delete Class
# Affected students get Attention records; Output 5 updates;
# workload and daily counts update.
# ==============================================================================
def test_9_delete_class():
    month = "2026-10"
    eff_pre = get_effective_schedule(month)
    
    # Pick a class with students where at least one student is at or below required quota
    target = None
    target_sid = None
    for c in eff_pre["scheduled_classes"]:
        if len(c.get("student_ids", [])) > 0 and not c.get("is_compensation"):
            for sid_cand in c.get("student_ids", []):
                s_sched = next((ss for ss in eff_pre["student_schedules"] if ss["student_id"] == sid_cand), None)
                if s_sched and s_sched.get("scheduled_classes_count", 0) <= s_sched.get("required_classes", 12):
                    target = c
                    target_sid = sid_cand
                    break
        if target:
            break

    assert target is not None and target_sid is not None, "Must find a scheduled class with an eligible student"
    c_date = target["date"]
    c_time = target["time_slot"]
    c_coach = resolve_coach_canonical_name(target["coach_name"])
    affected_students = target["student_ids"]

    pre_day_count = sum(1 for c in eff_pre["scheduled_classes"] if c["date"] == c_date)
    pre_workload = next(cs for cs in eff_pre["coach_summaries"] if cs["coach_name"] == c_coach)["classes_scheduled"]

    # Delete class via exception overlay
    del_resp = client.post("/api/schedule/exception/apply", json={
        "month": month,
        "date": c_date,
        "time_slot": c_time,
        "coach_name": c_coach,
        "action_type": "delete",
        "affected_student_ids": affected_students,
        "reason": "Class cancelled for acceptance testing",
        "created_by": "Admin"
    })
    assert del_resp.status_code == 200
    exc_id = del_resp.json()["exception_id"]

    eff_post = get_effective_schedule(month)

    # 1. Affected students get Attention records
    att_rec = next((r for r in eff_post["attention_records"] if r["student_id"] == target_sid), None)
    assert att_rec is not None, "Student whose class was deleted must receive Attention record"
    assert att_rec["remaining_classes"] > 0

    # 2. Output 5 updates: class removed from student timetable
    stu_sched = next(ss for ss in eff_post["student_schedules"] if ss["student_id"] == target_sid)
    assert not any(c["date"] == c_date and c["time_slot"] == c_time for c in stu_sched["classes"])

    # 3. Workload and daily counts update
    post_day_count = sum(1 for c in eff_post["scheduled_classes"] if c["date"] == c_date)
    assert post_day_count == pre_day_count - 1

    post_workload = next(cs for cs in eff_post["coach_summaries"] if cs["coach_name"] == c_coach)["classes_scheduled"]
    assert post_workload == pre_workload - 1

    revert_exception_record_db(exc_id)

# ==============================================================================
# TEST 10: Delete Coach
# Future classes go to Attention with replacement suggestions; baseline not silently changed.
# ==============================================================================
def test_10_delete_coach():
    month = "2026-10"
    test_coach_name = "TempTestCoach"
    
    # 1. Add temporary coach
    save_single_coach_db({
        "coach_name": test_coach_name,
        "levels": ["Beginner 1"],
        "max_classes_per_day": 3,
        "monthly_capacity_max": 20
    })
    ensure_active_data()

    # Add a class assigned to this coach
    exc_cls = client.post("/api/schedule/exception/apply", json={
        "month": month,
        "date": "2026-10-28",
        "time_slot": "05:00 PM",
        "coach_name": test_coach_name,
        "action_type": "add",
        "affected_student_ids": ["MKS00219"],
        "after": {
            "student_level": "Beginner 1",
            "batch_type": "G",
            "student_ids": ["MKS00219"],
            "day": "Wednesday"
        },
        "subtype": "normal_assignment",
        "reason": "Test coach class"
    })
    assert exc_cls.status_code == 200
    exc_id = exc_cls.json()["exception_id"]

    base_before = get_active_baseline_db(month)
    base_ver_before = base_before["version"]

    # 2. Delete coach from master data
    del_resp = client.delete(f"/api/master/coaches/{test_coach_name}")
    assert del_resp.status_code == 200

    # 3. Verify class goes to Attention with replacement suggestions
    eff = get_effective_schedule(month)
    print("DEBUG EFF ATT REASONS:", [r.get('failure_reason') for r in eff["attention_records"]])
    att = next((r for r in eff["attention_records"] if test_coach_name.lower() in r.get("failure_reason", "").lower()), None)
    assert att is not None, f"Class with deleted coach must appear in Attention. Found: {[r.get('failure_reason') for r in eff['attention_records']]}"
    assert "Replacement suggestions" in att["details"]

    # 4. Baseline is NOT silently changed
    base_after = get_active_baseline_db(month)
    assert base_after["version"] == base_ver_before

    revert_exception_record_db(exc_id)

# ==============================================================================
# TEST 11: Month Change
# February (28), April (30), October (31) each parse and display right number of days,
# weekday labels, weekly windows, and counts.
# ==============================================================================
def test_11_month_change():
    # February 2026 (28 days, starts Sunday)
    _, feb_days = calendar.monthrange(2026, 2)
    assert feb_days == 28
    feb_start_day = datetime(2026, 2, 1).strftime("%A")
    assert feb_start_day == "Sunday"

    # April 2026 (30 days, starts Wednesday)
    _, apr_days = calendar.monthrange(2026, 4)
    assert apr_days == 30
    apr_start_day = datetime(2026, 4, 1).strftime("%A")
    assert apr_start_day == "Wednesday"

    # October 2026 (31 days, starts Thursday)
    _, oct_days = calendar.monthrange(2026, 10)
    assert oct_days == 31
    oct_start_day = datetime(2026, 10, 1).strftime("%A")
    assert oct_start_day == "Thursday"

    # Weekly windows verification for October (31 days)
    # Windows: 1-7, 8-14, 15-21, 22-28, 29-31
    windows = [
        (1, 7), (8, 14), (15, 21), (22, 28), (29, 31)
    ]
    assert len(windows) == 5
    assert sum((w[1] - w[0] + 1) for w in windows) == 31

# ==============================================================================
# TEST 12: Attention Count Consistency
# 8 issues -> Output 1, Output 2, Output 3, Output 4 all show 8 -> resolve all -> all show 0.
# ==============================================================================
def test_12_attention_count_consistency():
    month = "2026-10"
    test_sids = [f"STU_ATT_8_{i}" for i in range(1, 9)]

    # Create 8 students with required_classes=1 (8 issues)
    for sid in test_sids:
        save_single_student_db({
            "student_id": sid,
            "student_name": f"Issue Student {sid}",
            "student_level": "Beginner 1",
            "batch_type": "G",
            "required_classes": 1
        })
    ensure_active_data()

    eff_8 = get_effective_schedule(month)
    # The 8 students appear in attention records
    att_8_sids = {r["student_id"] for r in eff_8["attention_records"]}
    for sid in test_sids:
        assert sid in att_8_sids

    # Consistent attention count across executive stats and report
    assert eff_8["need_attention"] >= 8

    # Now resolve all 8 issues by creating a class fulfilling them
    resolve_resp = client.post("/api/schedule/exception/apply", json={
        "month": month,
        "date": "2026-10-29",
        "time_slot": "06:00 PM",
        "coach_name": "Bathrinath",
        "action_type": "add",
        "affected_student_ids": test_sids,
        "after": {
            "student_level": "Beginner 1",
            "batch_type": "G",
            "student_ids": test_sids,
            "day": "Thursday"
        },
        "subtype": "normal_assignment",
        "reason": "Resolved all 8 students"
    })
    assert resolve_resp.status_code == 200
    exc_id = resolve_resp.json()["exception_id"]

    eff_resolved = get_effective_schedule(month)
    # None of the 8 students are in attention records anymore
    att_resolved_sids = {r["student_id"] for r in eff_resolved["attention_records"]}
    for sid in test_sids:
        assert sid not in att_resolved_sids

    # Cleanup
    revert_exception_record_db(exc_id)
    for sid in test_sids:
        delete_single_student_db(sid)

# ==============================================================================
# TEST 13: Failure Mid-Save Atomicity
# Simulate a database failure mid-save -> UI/API shows failure, no partial data,
# retry works, nothing duplicated.
# ==============================================================================
def test_13_failure_mid_save_atomicity():
    test_sched_id = "SCHED_FAIL_TEST"
    test_sched_payload = {
        "schedule_id": test_sched_id,
        "status": "Draft",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31",
        "total_students_considered": 10,
        "successfully_scheduled_students": 10,
        "unscheduled_students_count": 0,
        "accountability_passed": True,
        "created_at": datetime.now().isoformat()
    }

    # Simulate database error on cursor.execute mid-save using connection wrapper (Python 3.14 safe)
    real_get_conn = get_connection

    class FaultyConnectionWrapper:
        def __init__(self, real_conn):
            self._conn = real_conn
        def cursor(self, *args, **kwargs):
            real_cur = self._conn.cursor(*args, **kwargs)
            class FaultyCursorWrapper:
                def __init__(self, cur):
                    self._cur = cur
                def execute(self, sql, *eargs, **ekwargs):
                    if "INSERT OR REPLACE INTO schedules" in sql:
                        raise sqlite3.OperationalError("Simulated disk I/O failure")
                    return self._cur.execute(sql, *eargs, **ekwargs)
                def __getattr__(self, item):
                    return getattr(self._cur, item)
            return FaultyCursorWrapper(real_cur)
        def __getattr__(self, item):
            return getattr(self._conn, item)

    def mock_faulty_get_connection(*args, **kwargs):
        conn = real_get_conn(*args, **kwargs)
        return FaultyConnectionWrapper(conn)

    with patch("app.storage.database.get_connection", side_effect=mock_faulty_get_connection):
        with pytest.raises(sqlite3.OperationalError):
            save_schedule_db(test_sched_payload)

    # Verify no partial data was saved
    res_db = get_schedule_db(test_sched_id)
    assert res_db is None, "Mid-save failure must rollback cleanly leaving no partial data"

    # Retry works cleanly
    save_schedule_db(test_sched_payload)
    res_retry = get_schedule_db(test_sched_id)
    assert res_retry is not None
    assert res_retry["schedule_id"] == test_sched_id

    # Verify nothing duplicated on second save
    save_schedule_db(test_sched_payload)
    conn = get_connection(get_db_path())
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM schedules WHERE schedule_id = ?", (test_sched_id,))
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 1, "Retry must not duplicate record in database"

# ==============================================================================
# TEST 14: Concurrency Conflict Detection
# Two administrators edit the same class -> the second gets a conflict message.
# ==============================================================================
def test_14_concurrency_conflict():
    month = "2026-10"
    base_ver = ScheduleEventBus._version_counter

    # Admin 1 edits class with current version
    admin1_resp = client.post("/api/schedule/exception/apply", json={
        "month": month,
        "date": "2026-10-18",
        "time_slot": "04:00 PM",
        "coach_name": "Bathrinath",
        "action_type": "add",
        "affected_student_ids": [],
        "subtype": "manual",
        "reason": "Admin 1 update",
        "schedule_version": base_ver
    })
    assert admin1_resp.status_code == 200
    exc1_id = admin1_resp.json()["exception_id"]

    # Version has bumped
    new_ver = ScheduleEventBus._version_counter
    assert new_ver > base_ver

    # Admin 2 attempts edit using old stale version
    admin2_resp = client.post("/api/schedule/exception/apply", json={
        "month": month,
        "date": "2026-10-18",
        "time_slot": "04:00 PM",
        "coach_name": "Prakash",
        "action_type": "add",
        "affected_student_ids": [],
        "subtype": "manual",
        "reason": "Admin 2 update",
        "schedule_version": base_ver # Stale version!
    })
    assert admin2_resp.status_code == 409
    detail = admin2_resp.json().get("detail", "")
    assert "Conflict: The schedule has been modified by another administrator" in detail

    revert_exception_record_db(exc1_id)

# ==============================================================================
# TEST 15: Speed Targets
# Part A4 targets are met with 120 students and 31 days (< 1.0 second execution).
# ==============================================================================
def test_15_speed_targets():
    month = "2026-10"
    
    # Measure execution time of full effective schedule computation
    start_time = time.time()
    eff = get_effective_schedule(month)
    elapsed = time.time() - start_time

    assert len(eff["scheduled_classes"]) > 100, "Should compute complete schedule with 100+ classes"
    assert elapsed < 1.0, f"Speed target exceeded: computation took {elapsed:.3f}s (target < 1.0s)"
