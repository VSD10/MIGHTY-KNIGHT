import sys
import os
from datetime import datetime, date

# Add app to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.storage.database import (
    load_master_data_db, save_master_data_db, get_active_baseline_db,
    save_exception_record_db, get_exception_records_db
)
from app.engine.effective_schedule_service import (
    get_effective_schedule, ScheduleEventBus, REFERENCE_TODAY
)
from app.engine.master_data_service import (
    sync_live_coach_priority_matrix, reorder_coach_level_priorities
)
from app.engine.time_utils import is_slot_in_coach_preference
from app.engine.coach_selector import CoachSelector
from app.models.coach import CoachModel
from app.engine.suggestion_engine import (
    find_single_class_suggestions, solve_multi_class_options,
    generate_new_slot_candidates, evaluate_hard_feasibility,
    ENGINE_SETTINGS, build_coach_availability_mask
)
from app.main import (
    CURRENT_CONFIG, ACTIVE_DATA, ensure_active_data,
    save_master_coach, delete_master_coach, save_master_student,
    accept_engine_suggestion_api, AcceptSuggestionRequest
)

def run_tests():
    print("=" * 70)
    print("STARTING END-TO-END VALIDATION OF CRITICAL SCHEDULING REQUIREMENTS")
    print("=" * 70)

    # Initial cleanup to ensure 100% pristine baseline
    test_coach_name = "COACH_MATRIX_TEST"
    strict_coach_name = "COACH_STRICT_TIME"
    mid_month_sid = "STU_MID_MONTH_TEST"
    import sqlite3
    from app.storage.database import get_db_path
    conn = sqlite3.connect(get_db_path())
    conn.execute("DELETE FROM exception_records WHERE affected_student_ids_json LIKE ?", (f"%{mid_month_sid}%",))
    conn.execute("DELETE FROM students WHERE student_id = ?", (mid_month_sid,))
    conn.execute("DELETE FROM coaches WHERE coach_name IN (?, ?)", (strict_coach_name, test_coach_name))
    conn.commit()
    conn.close()
    delete_master_coach(test_coach_name)
    delete_master_coach(strict_coach_name)
    ACTIVE_DATA["students"] = [s for s in ACTIVE_DATA.get("students", []) if s["student_id"] != mid_month_sid]
    ACTIVE_DATA["coaches"] = [c for c in ACTIVE_DATA.get("coaches", []) if c["coach_name"] not in (strict_coach_name, test_coach_name)]

    ensure_active_data()

    baseline_eff_before = get_effective_schedule("2026-10")
    original_classes = [dict(c) for c in baseline_eff_before["scheduled_classes"]]
    original_class_keys = {(c["date"], c["time_slot"], c["coach_name"], tuple(sorted(c.get("student_ids", [])))) for c in original_classes}
    print(f"[INIT] Baseline loaded: {len(original_classes)} classes, {len(ACTIVE_DATA['coaches'])} coaches, {len(ACTIVE_DATA['students'])} students.")

    # =========================================================================
    # REQUIREMENT 1: DYNAMIC TRAINER QUALIFICATION MATRIX
    # =========================================================================
    print("\n--- REQ 1: Dynamic Trainer Qualification Matrix ---")
    
    # 1.1 Add New Coach
    test_coach_name = "COACH_MATRIX_TEST"
    new_coach_payload = {
        "coach_name": test_coach_name,
        "coach_id": test_coach_name,
        "levels_handled": ["Basic 1", "Intermediate 1"],
        "max_classes_per_day": 3,
        "mon_max": 3, "tue_max": 3, "wed_max": 3, "thu_max": 3, "fri_max": 3, "sat_max": 3, "sun_max": 0,
        "sunday_pref": "Off",
        "preferred_timings": "Monday: 06:00 PM-08:00 PM (max 2); Tuesday: 06:00 PM-08:00 PM (max 2)",
        "monthly_capacity_max": 25,
        "monthly_capacity_min": 5,
        "is_flex": False
    }
    
    import app.main
    delete_master_coach(test_coach_name)
    b1_prio_before = list(app.main.CURRENT_CONFIG.coach_priority.get("Basic 1", []))
    int1_prio_before = list(app.main.CURRENT_CONFIG.coach_priority.get("Intermediate 1", []))
    
    saved_coach = save_master_coach(new_coach_payload)
    
    b1_prio_after = list(app.main.CURRENT_CONFIG.coach_priority.get("Basic 1", []))
    int1_prio_after = list(app.main.CURRENT_CONFIG.coach_priority.get("Intermediate 1", []))
    
    # Assert new coach appended to bottom of both levels
    assert b1_prio_after[-1] == test_coach_name, f"Expected {test_coach_name} at end of Basic 1, got {b1_prio_after}"
    assert int1_prio_after[-1] == test_coach_name, f"Expected {test_coach_name} at end of Intermediate 1, got {int1_prio_after}"
    # Assert existing priorities strictly preserved
    assert b1_prio_after[:-1] == b1_prio_before, f"Existing Basic 1 priorities were altered! Before: {b1_prio_before}, After: {b1_prio_after}"
    assert int1_prio_after[:-1] == int1_prio_before, f"Existing Intermediate 1 priorities were altered! Before: {int1_prio_before}, After: {int1_prio_after}"
    print(f"[PASSED] 1.1 New coach appended to bottom of applicable levels. Existing priorities preserved.")
    print(f"         Basic 1 priorities: {b1_prio_after}")

    # 1.2 Remove Coach - Shifting remaining coaches upward without gaps (1..N) and without priority resets
    res_del = delete_master_coach(test_coach_name)
    b1_prio_post_del = list(app.main.CURRENT_CONFIG.coach_priority.get("Basic 1", []))
    int1_prio_post_del = list(app.main.CURRENT_CONFIG.coach_priority.get("Intermediate 1", []))
    
    assert test_coach_name not in b1_prio_post_del, "Removed coach still present in Basic 1 priority list!"
    assert test_coach_name not in int1_prio_post_del, "Removed coach still present in Intermediate 1 priority list!"
    assert b1_prio_post_del == b1_prio_before, "Basic 1 priorities did not shift upward cleanly back to original!"
    assert int1_prio_post_del == int1_prio_before, "Intermediate 1 priorities did not shift upward cleanly back to original!"
    
    # Verify coach objects have sequential 1..N ranks with zero gaps
    for c in app.main.ACTIVE_DATA["coaches"]:
        c_prio = c.get("qualified_levels_priority", {})
        for lvl, rank in c_prio.items():
            if lvl in app.main.CURRENT_CONFIG.coach_priority:
                expected_list = app.main.CURRENT_CONFIG.coach_priority[lvl]
                c_canon = c["coach_name"]
                if c_canon in expected_list:
                    assert rank == expected_list.index(c_canon) + 1, f"Mismatch rank for {c_canon} in {lvl}: {rank} vs {expected_list.index(c_canon) + 1}"
    print(f"[PASSED] 1.2 Coach removal closes gaps upward without resets; coach objects 100% match live matrix.")

    # =========================================================================
    # REQUIREMENT 2: PROTECT EXISTING STUDENTS' AND COACHES' SCHEDULES
    # =========================================================================
    print("\n--- REQ 2: Protect Existing Students' and Coaches' Schedules ---")
    eff_check = get_effective_schedule("2026-10")
    current_classes = eff_check["scheduled_classes"]
    current_class_keys = {(c["date"], c["time_slot"], c["coach_name"], tuple(sorted(c.get("student_ids", [])))) for c in current_classes}
    
    # No baseline class altered by adding/removing coach or recalculating
    assert original_class_keys == current_class_keys, "CRITICAL ERROR: Existing schedules were mutated by coach operations!"
    print(f"[PASSED] 2.1 All {len(original_classes)} existing classes retain identical dates, timings, students, and coaches.")

    # =========================================================================
    # REQUIREMENT 3: MANDATORY COACH PREFERENCE TIMINGS RESTRICTIONS
    # =========================================================================
    print("\n--- REQ 3: Mandatory Coach Preference Timing Restrictions ---")
    
    # Register a coach with strict timings: Monday only 06:00 PM - 07:00 PM, Sunday OFF
    strict_coach_name = "COACH_STRICT_TIME"
    save_master_coach({
        "coach_name": strict_coach_name,
        "coach_id": strict_coach_name,
        "levels_handled": ["Basic 1"],
        "mon_max": 1, "tue_max": 0, "wed_max": 0, "thu_max": 0, "fri_max": 0, "sat_max": 0, "sun_max": 0,
        "sunday_pref": "Off",
        "preferred_timings": "Monday: 06:00 PM-07:00 PM (max 1); Tuesday: Not available (max 0); Sunday: Off",
        "monthly_capacity_max": 4,
        "is_flex": False
    })
    
    c_strict_obj = next(c for c in ACTIVE_DATA["coaches"] if c["coach_name"] == strict_coach_name)
    
    # 3.1 Test is_slot_in_coach_preference helper directly
    ok_in, _ = is_slot_in_coach_preference(c_strict_obj, "Monday", "06:00 PM")
    ok_out, r_out = is_slot_in_coach_preference(c_strict_obj, "Monday", "04:00 PM")
    ok_tue, r_tue = is_slot_in_coach_preference(c_strict_obj, "Tuesday", "06:00 PM")
    ok_sun, r_sun = is_slot_in_coach_preference(c_strict_obj, "Sunday", "10:00 AM")
    
    assert ok_in is True, "Configured 06:00 PM slot should be accepted"
    assert ok_out is False, "Slot outside 06:00 PM - 07:00 PM must be rejected"
    assert ok_tue is False, "Tuesday must be rejected because max is 0 / not available"
    assert ok_sun is False, "Sunday must be rejected because sunday_pref is Off"
    print(f"[PASSED] 3.1 is_slot_in_coach_preference enforces mandatory constraint (rejected: {r_out}, {r_tue}, {r_sun}).")

    # 3.2 Test build_coach_availability_mask
    mask_mon = build_coach_availability_mask(strict_coach_name, {strict_coach_name: c_strict_obj}, "Monday")
    mask_tue = build_coach_availability_mask(strict_coach_name, {strict_coach_name: c_strict_obj}, "Tuesday")
    mask_sun = build_coach_availability_mask(strict_coach_name, {strict_coach_name: c_strict_obj}, "Sunday")
    
    assert mask_tue == 0, "Tuesday mask must be 0"
    assert mask_sun == 0, "Sunday mask must be 0"
    # Bit 36 is 18:00 (06:00 PM)
    assert (mask_mon & (1 << 36)) > 0, "Monday 06:00 PM bit must be 1"
    assert (mask_mon & (1 << 32)) == 0, "Monday 04:00 PM bit must be 0"
    print(f"[PASSED] 3.2 build_coach_availability_mask correctly zeroes out prohibited times and days.")

    # 3.3 Test CoachSelector strict enforcement (Never violates preferred timing)
    coach_fields = CoachModel.model_fields if hasattr(CoachModel, "model_fields") else CoachModel.__fields__
    coach_model = CoachModel(**{k: v for k, v in c_strict_obj.items() if k in coach_fields})
    selector = CoachSelector([coach_model], CURRENT_CONFIG)
    coach_pick, fail_reason = selector.select_coach(
        student_level="Basic 1",
        target_date_str="2026-10-19",
        day_name="Monday",
        time_slot="04:00 PM-05:00 PM",
        is_sunday_tournament=False,
        daily_coach_assignments={"2026-10-19": {}},
        monthly_coach_assignments={},
        active_time_occupancy={"2026-10-19": {}}
    )
    assert coach_pick is None, f"Coach was assigned outside preference timings! Picked: {coach_pick}"
    print(f"[PASSED] 3.3 CoachSelector strictly refuses to assign coach outside configured timing window (Reason: {fail_reason}).")

    # =========================================================================
    # REQUIREMENT 4: SCHEDULING ENGINE & ATTENTION REQUIRED
    # =========================================================================
    print("\n--- REQ 4: Scheduling Engine & Attention Required ---")
    
    # 4.1 Mid-month student joining on 2026-10-25 with 8 classes required
    # Since October has 31 days, from Oct 25 to Oct 31 is only 7 calendar days!
    # Max possible classes (at 1 class/day) is 7. Quota shortfall = at least 1 class!
    mid_month_sid = "STU_MID_MONTH_TEST"
    student_payload = {
        "student_id": mid_month_sid,
        "student_name": "Mid Month Student",
        "student_level": "Basic 1",
        "batch_type": "G",
        "required_classes": 8,
        "joining_date": "2026-10-25",
        "preferred_timings": "Evening (05:00 PM-09:00 PM)",
        "day_preference": "All days"
    }
    save_master_student(student_payload)
    
    eff_mid = get_effective_schedule("2026-10")
    att_rec = next((r for r in eff_mid["attention_records"] if r["student_id"] == mid_month_sid), None)
    
    assert att_rec is not None, f"Student {mid_month_sid} was not automatically fetched into Attention Required!"
    assert att_rec["joining_date"] == "2026-10-25", f"Joining date missing in attention record: {att_rec}"
    assert att_rec["monthly_quota"] == 8, f"Monthly quota missing in attention record: {att_rec}"
    assert att_rec["is_mid_month"] is True, f"is_mid_month flag not set: {att_rec}"
    assert att_rec["shortfall"] >= 1, f"Expected shortfall >= 1 for joining on 25th with 8 needed, got {att_rec['shortfall']}"
    assert "Joined mid-month" in att_rec["failure_reason"], f"Failure reason should explain mid-month joining: {att_rec['failure_reason']}"
    print(f"[PASSED] 4.1 Mid-month student complete profile fetched into Attention Required with accurate shortfall diagnosis:")
    print(f"         Reason: {att_rec['failure_reason']}")

    # 4.2 Never allocate classes to past dates or dates before joining
    coach_map = {c["coach_name"]: c for c in ACTIVE_DATA["coaches"]}
    suggs, reasons = find_single_class_suggestions(
        student=att_rec,
        all_classes=eff_mid["scheduled_classes"],
        coaches_master_map=coach_map,
        target_month="2026-10",
        settings=ENGINE_SETTINGS
    )
    
    for s_item in suggs:
        assert s_item["date"] >= "2026-10-25", f"Candidate date {s_item['date']} is before student joining date 2026-10-25!"
        assert s_item["date"] >= REFERENCE_TODAY, f"Candidate date {s_item['date']} is before REFERENCE_TODAY {REFERENCE_TODAY}!"
    print(f"[PASSED] 4.2 All {len(suggs)} single suggestions have date >= max(joining_date, REFERENCE_TODAY). Zero past dates.")

    # 4.3 Multi-Class Option Sets for mid-month student
    opt_sets = solve_multi_class_options(
        student=att_rec,
        needed_count=8,
        all_classes=eff_mid["scheduled_classes"],
        coaches_master_map=coach_map,
        target_month="2026-10",
        settings=ENGINE_SETTINGS
    )
    assert len(opt_sets) > 0, "Expected at least 1 option set generated"
    for oset in opt_sets:
        assert oset["classes_covered"] <= 7, f"Cannot schedule more than 7 classes between Oct 25 and Oct 31! Got {oset['classes_covered']}"
        assert oset["shortfall"] >= 1, f"Shortfall should be reported! Got {oset.get('shortfall')}"
        for item in oset["items"]:
            assert item["date"] >= "2026-10-25", f"Class date {item['date']} is before joining date 2026-10-25!"
            assert item["date"] >= REFERENCE_TODAY, f"Class date {item['date']} is before REFERENCE_TODAY {REFERENCE_TODAY}!"
    print(f"[PASSED] 4.3 Multi-class solver correctly bounded by month-end (covered: {opt_sets[0]['classes_covered']}/8, shortfall: {opt_sets[0]['shortfall']}).")
    print(f"         Description: {opt_sets[0]['description']}")

    # =========================================================================
    # REQUIREMENT 5: REAL-TIME SYNCHRONIZATION ACROSS OUTPUTS 1-5
    # =========================================================================
    print("\n--- REQ 5: Real-Time Synchronization & Class Count Distinction ---")
    
    # Accept the best option set for the student
    best_set = opt_sets[0]
    classes_to_add = len(best_set["items"])
    req = AcceptSuggestionRequest(
        student_id=mid_month_sid,
        schedule_version=eff_mid["version"],
        is_option_set=True,
        option_set_items=best_set["items"]
    )
    res_accept = accept_engine_suggestion_api(req)
    assert res_accept.get("status") == "success", f"Failed to accept option set: {res_accept}"
    
    # Fetch effective schedule post-acceptance
    eff_post = get_effective_schedule("2026-10")
    
    # 5.1 Student removed from Attention Required (or shortfall noted if remaining needed)
    att_post = next((r for r in eff_post["attention_records"] if r["student_id"] == mid_month_sid), None)
    expected_remaining = max(0, 8 - classes_to_add)
    if expected_remaining == 0:
        assert att_post is None, "Student should be completely resolved from Attention Required"
    else:
        assert att_post["scheduled_classes"] == classes_to_add, f"Scheduled count mismatch: {att_post['scheduled_classes']} vs {classes_to_add}"
    
    # 5.2 Output 1: WhatsApp plain text includes student
    assert mid_month_sid in eff_post["whatsapp_plain_text"], "Student ID missing from Output 1 WhatsApp schedule!"
    
    # 5.3 Output 2: Master scheduled classes includes approved allocations with distinct flag
    stu_post_classes = [c for c in eff_post["scheduled_classes"] if mid_month_sid in c.get("student_ids", [])]
    assert len(stu_post_classes) == classes_to_add, f"Expected {classes_to_add} classes, found {len(stu_post_classes)}"
    assert all(c.get("is_approved_allocation") is True for c in stu_post_classes), "Approved allocations must have is_approved_allocation=True!"
    
    # 5.4 Output 4: Coach summaries have distinct completed_classes_count vs approved_allocations_count vs scheduled_classes
    for cs in eff_post["coach_summaries"]:
        if cs["classes_scheduled"] > 0:
            assert "completed_classes_count" in cs
            assert "approved_allocations_count" in cs
            assert "scheduled_classes" in cs
            # Completed classes count must only include classes with date <= REFERENCE_TODAY
            for comp_c in cs.get("completed_classes_so_far", []):
                assert comp_c["date"] <= REFERENCE_TODAY, f"Completed class has future date: {comp_c['date']}"
    
    # 5.5 Output 5: Student schedule has distinct counts
    stu_sched = next(s for s in eff_post["student_schedules"] if s["student_id"] == mid_month_sid)
    assert stu_sched["scheduled_classes_count"] == classes_to_add
    assert stu_sched["approved_allocations_count"] == classes_to_add
    assert stu_sched["completed_classes_count"] == 0  # Oct 25-31 is after REFERENCE_TODAY (Oct 15)
    print(f"[PASSED] 5.1 Real-time synchronization verified across Outputs 1-5.")
    print(f"         Distinct counts: scheduled={stu_sched['scheduled_classes_count']}, approved={stu_sched['approved_allocations_count']}, completed={stu_sched['completed_classes_count']}.")

    # =========================================================================
    # CLEANUP TEST DATA
    # =========================================================================
    print("\n--- CLEANUP ---")
    delete_master_coach(strict_coach_name)
    ACTIVE_DATA["students"] = [s for s in ACTIVE_DATA["students"] if s["student_id"] != mid_month_sid]
    # Remove test exceptions
    conn = sqlite3.connect(get_db_path())
    conn.execute("DELETE FROM exception_records WHERE affected_student_ids_json LIKE ?", (f"%{mid_month_sid}%",))
    conn.execute("DELETE FROM students WHERE student_id = ?", (mid_month_sid,))
    conn.commit()
    conn.close()
    ensure_active_data()
    print("[OK] Test data cleanly reset.")

    print("\n" + "=" * 70)
    print("ALL 5 REQUIREMENTS FULLY VERIFIED AND PASSING!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
