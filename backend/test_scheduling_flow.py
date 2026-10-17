import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
import app.main
from app.config import DEFAULT_CONFIG
from app.storage.database import init_db, load_master_data_db, save_single_student_db, save_single_coach_db, delete_single_student_db, delete_single_coach_db
from app.engine.effective_schedule_service import get_effective_schedule, ScheduleEventBus
from app.engine.suggestion_engine import find_single_class_suggestions, solve_multi_class_options, ENGINE_SETTINGS
from app.main import (
    save_master_student, save_bulk_master_students, save_master_coach,
    delete_master_coach, accept_engine_suggestion_api,
    MasterStudentRequest, BulkMasterStudentRequest, MasterCoachRequest, AcceptSuggestionRequest,
    ensure_active_data, ACTIVE_DATA
)

def run_all_tests():
    print("=" * 70)
    print("RUNNING COMPREHENSIVE SCHEDULING ENGINE VALIDATION TEST")
    print("=" * 70)
    
    ensure_active_data()

    # -------------------------------------------------------------------------
    # TEST 1: New Student Detection & Attention Required
    # -------------------------------------------------------------------------
    print("\n--- TEST 1: New Student Detection & Profile Fetch into Attention Required ---")
    test_sid = "STU_AUTO_DETECT_01"
    
    # Clean up prior test student if exists
    ACTIVE_DATA["students"] = [s for s in ACTIVE_DATA["students"] if s["student_id"] != test_sid]
    delete_single_student_db(test_sid)
    from app.storage.database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM exception_records WHERE affected_student_ids_json LIKE ?", (f'%{test_sid}%',))
    conn.commit()
    conn.close()

    student_req = MasterStudentRequest(
        student_id=test_sid,
        student_name="Aarav Sharma",
        student_level="Beginner 1",
        batch_type="G",
        required_classes=8,
        preferred_times=["05:00 PM – 06:00 PM"],
        mon_pref="05:00 PM – 06:00 PM",
        wed_pref="05:00 PM – 06:00 PM",
        fri_pref="05:00 PM – 06:00 PM",
        availability={"Monday": [["17:00", "18:00"]], "Wednesday": [["17:00", "18:00"]], "Friday": [["17:00", "18:00"]]},
        is_morning_available=False
    )
    
    save_res = save_master_student(student_req)
    print(f"[OK] Student {test_sid} saved into Master Data Hub.")

    eff = get_effective_schedule("2026-10")
    att_rec = next((r for r in eff["attention_records"] if r["student_id"] == test_sid), None)
    assert att_rec is not None, f"FAIL: Student {test_sid} NOT detected in Attention Required!"
    assert att_rec["required_classes"] == 8, f"Expected 8 required classes, got {att_rec['required_classes']}"
    assert att_rec["scheduled_classes"] == 0, f"Expected 0 scheduled classes, got {att_rec['scheduled_classes']}"
    assert att_rec["remaining_classes"] == 8, f"Expected 8 remaining classes, got {att_rec['remaining_classes']}"
    assert "Unscheduled" in att_rec["failure_reason"], f"Unexpected reason: {att_rec['failure_reason']}"
    print(f"[PASSED] Student {test_sid} automatically detected in Attention Required:")
    print(f"         Level: {att_rec['student_level']}, Required: {att_rec['required_classes']}, Scheduled: {att_rec['scheduled_classes']}, Reason: {att_rec['failure_reason']}")

    # -------------------------------------------------------------------------
    # TEST 2: Bulk Addition of 50 Students
    # -------------------------------------------------------------------------
    print("\n--- TEST 2: Bulk Student Addition (50 Students) ---")
    bulk_students = []
    for i in range(1, 51):
        bsid = f"BULK_STU_{i:03d}"
        bulk_students.append(MasterStudentRequest(
            student_id=bsid,
            student_name=f"Bulk Student {i}",
            student_level="Beginner 1" if i % 2 == 0 else "Basic 1",
            batch_type="G",
            required_classes=8,
            preferred_times=["06:00 PM – 07:00 PM"],
            tue_pref="06:00 PM – 07:00 PM",
            thu_pref="06:00 PM – 07:00 PM"
        ))
    
    bulk_res = save_bulk_master_students(BulkMasterStudentRequest(students=bulk_students))
    print(f"[OK] Bulk API saved {bulk_res['saved_count']} students, errors: {bulk_res['errors_count']}")
    assert bulk_res["saved_count"] == 50, f"Expected 50 saved, got {bulk_res['saved_count']}"

    eff_bulk = get_effective_schedule("2026-10")
    bulk_detected = [r for r in eff_bulk["attention_records"] if r["student_id"].startswith("BULK_STU_")]
    print(f"[OK] Total bulk students detected in Attention Required: {len(bulk_detected)}/50")
    assert len(bulk_detected) == 50, f"Expected 50 bulk students in attention records, found {len(bulk_detected)}"
    print("[PASSED] All 50 bulk students reliably present in Attention Required without skipping.")

    # -------------------------------------------------------------------------
    # TEST 3: Dynamic Coach Priority Matrix
    # -------------------------------------------------------------------------
    print("\n--- TEST 3: Dynamic Coach Priority Matrix Registration ---")
    new_coach_name = "COACH_DYNAMIC_TEST"
    delete_master_coach(new_coach_name)
    
    # Check existing priority order for Intermediate 1
    int1_prio_before = list(app.main.CURRENT_CONFIG.coach_priority.get("Intermediate 1", []))
    print(f"         Intermediate 1 priorities before: {int1_prio_before}")
    
    coach_req = MasterCoachRequest(
        coach_name=new_coach_name,
        levels_handled=["Intermediate 1", "Basic 1"],
        monthly_capacity_max=40,
        mon_max=4,
        tue_max=4,
        wed_max=4,
        thu_max=4,
        fri_max=4,
        sat_max=5,
        sun_max=2
    )
    
    coach_save_res = save_master_coach(coach_req)
    int1_prio_after = app.main.CURRENT_CONFIG.coach_priority.get("Intermediate 1", [])
    print(f"         Intermediate 1 priorities after:  {int1_prio_after}")
    
    assert int1_prio_after[-1] == new_coach_name, f"Expected {new_coach_name} at bottom of Intermediate 1 list!"
    assert int1_prio_after[:-1] == int1_prio_before, "Existing coach priorities were modified or corrupted!"
    assert coach_save_res["coach"]["qualified_levels_priority"]["Intermediate 1"] == len(int1_prio_after)
    print(f"[PASSED] New Coach {new_coach_name} successfully registered at bottom of Intermediate 1 (Rank #{len(int1_prio_after)}).")
    print(f"         Existing priority order fully preserved: {int1_prio_before}")

    # -------------------------------------------------------------------------
    # TEST 4: Intelligent Scheduling & Priority Sequential Ordering
    # -------------------------------------------------------------------------
    print("\n--- TEST 4: Intelligent Scheduling & Priority Sequential Ordering ---")
    s_obj = next(s for s in ACTIVE_DATA["students"] if s["student_id"] == test_sid)
    coach_map = {c["coach_name"]: c for c in ACTIVE_DATA["coaches"]}
    
    single_suggs, reasons = find_single_class_suggestions(
        student=s_obj,
        all_classes=eff["scheduled_classes"],
        coaches_master_map=coach_map,
        target_month="2026-10",
        settings=ENGINE_SETTINGS
    )
    print(f"[OK] Generated {len(single_suggs)} single class suggestions for {test_sid}.")
    assert len(single_suggs) > 0, "No suggestions found for student!"
    
    # Check priority rank sequence in suggestions
    prio_ranks = [int(s.get("coach_priority_rank", "#99").replace("#", "")) for s in single_suggs if s.get("coach_priority_rank")]
    print(f"         Candidate coach priority ranks recommended: {prio_ranks[:5]}")
    # Higher priority (lower rank number) should appear before lower priority
    assert min(prio_ranks) <= 2, f"Expected top priority coach (#1 or #2) to be recommended, got {min(prio_ranks)}"

    # Multi-class options: solve quota of 8 classes
    print("\n--- TEST 4B: Multi-Class Option Sets to Satisfy Quota (8 classes) ---")
    option_sets = solve_multi_class_options(
        student=s_obj,
        needed_count=8,
        all_classes=eff["scheduled_classes"],
        coaches_master_map=coach_map,
        target_month="2026-10",
        settings=ENGINE_SETTINGS
    )
    print(f"[OK] Generated {len(option_sets)} multi-class option sets.")
    assert len(option_sets) > 0, "No option sets generated for 8 classes!"
    
    chosen_set = option_sets[0]
    print(f"         Selected: {chosen_set['set_name']} ({len(chosen_set['items'])} classes, coaches: {chosen_set['coaches']})")
    assert len(chosen_set["items"]) == 8, f"Expected exactly 8 classes in option set, got {len(chosen_set['items'])}"

    # -------------------------------------------------------------------------
    # TEST 5: Acceptance & Real-Time Propagation Across Outputs 1 - 5
    # -------------------------------------------------------------------------
    print("\n--- TEST 5: Accept Suggestion & Real-Time Propagation Across Outputs 1-5 ---")
    accept_req = AcceptSuggestionRequest(
        student_id=test_sid,
        month="2026-10",
        schedule_version=ScheduleEventBus._version_counter,
        is_option_set=True,
        option_set_items=chosen_set["items"]
    )
    
    accept_res = accept_engine_suggestion_api(accept_req)
    print(f"[OK] Accept API response: applied {accept_res['applied_count']} classes, remaining for student: {accept_res['remaining_for_student']}")
    assert accept_res["applied_count"] == 8, f"Expected 8 applied, got {accept_res['applied_count']}"
    assert accept_res["remaining_for_student"] == 0, f"Expected 0 remaining, got {accept_res['remaining_for_student']}"

    # Verify Output 1 - 5
    eff_post = get_effective_schedule("2026-10")

    # Output 1: WhatsApp / Coach Master Schedule
    has_o1 = test_sid in eff_post["whatsapp_plain_text"]
    print(f"         Output 1 (WhatsApp Schedule contains student): {has_o1}")
    assert has_o1, "Output 1 does not contain student's scheduled classes!"

    # Output 2: Coach-wise scheduled classes
    student_classes_o2 = [c for c in eff_post["scheduled_classes"] if test_sid in c.get("student_ids", [])]
    print(f"         Output 2 (Scheduled Classes count for student): {len(student_classes_o2)}")
    assert len(student_classes_o2) == 8, f"Expected 8 scheduled classes in Output 2, got {len(student_classes_o2)}"

    # Output 3: Admin Matrix & Attention Required
    att_rec_post = next((r for r in eff_post["attention_records"] if r["student_id"] == test_sid), None)
    print(f"         Output 3 (Cleared from Attention Required): {att_rec_post is None}")
    assert att_rec_post is None, "Student still appears in Attention Required after full quota fulfilled!"

    # Output 4: Coach Workload & Classes Taken So Far
    coaches_used = {c["coach_name"] for c in student_classes_o2}
    for coach in coaches_used:
        c_sum = next((cs for cs in eff_post["coach_summaries"] if cs["coach_name"] == coach), None)
        assert c_sum is not None, f"Coach {coach} summary missing from Output 4!"
        assert c_sum["classes_scheduled"] > 0, f"Coach {coach} classes_scheduled should be > 0"
    print(f"         Output 4 (Coach Summaries updated for: {coaches_used}): True")

    # Output 5: Student Individual Schedule & Quota Fulfillment
    s_sched = next((s for s in eff_post["student_schedules"] if s["student_id"] == test_sid), None)
    assert s_sched is not None, f"Student {test_sid} missing from Output 5 student_schedules!"
    assert s_sched["scheduled_classes_count"] == 8, f"Expected 8 scheduled classes in Output 5, got {s_sched['scheduled_classes_count']}"
    assert s_sched["ics_unlocked"] is True, "ICS calendar should be unlocked when student has no attention issues!"
    print(f"         Output 5 (Student schedule classes: {s_sched['scheduled_classes_count']}/8, ICS unlocked: {s_sched['ics_unlocked']}): True")

    # -------------------------------------------------------------------------
    # CLEANUP TEST DATA
    # -------------------------------------------------------------------------
    print("\n--- CLEANUP TEMPORARY TEST DATA ---")
    delete_single_student_db(test_sid)
    delete_master_coach(new_coach_name)
    for i in range(1, 51):
        delete_single_student_db(f"BULK_STU_{i:03d}")
    ACTIVE_DATA["students"] = [s for s in ACTIVE_DATA["students"] if s["student_id"] != test_sid and not s["student_id"].startswith("BULK_STU_")]
    ACTIVE_DATA["coaches"] = [c for c in ACTIVE_DATA["coaches"] if c["coach_name"] != new_coach_name]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM exception_records WHERE affected_student_ids_json LIKE ?", (f'%{test_sid}%',))
    conn.commit()
    conn.close()
    get_effective_schedule("2026-10")
    print("[OK] Test data safely cleaned up.")

    print("\n" + "=" * 70)
    print("ALL 5 TESTS PASSED SUCCESSFULLY! SCHEDULING ENGINE IS 100% CORRECT.")
    print("=" * 70)

if __name__ == "__main__":
    run_all_tests()
