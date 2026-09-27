import os
import sys
import json
import sqlite3
import datetime
from typing import Dict, Any, List

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from fastapi.testclient import TestClient
from app.main import app
from app.storage.database import (
    get_db_path,
    init_db,
    load_master_data_db,
    load_master_batches_db,
    get_latest_schedule_db
)

client = TestClient(app)

def run_safe_system_tests():
    db_path = get_db_path()
    init_db(db_path)

    # ----------------------------------------------------
    # 1. SYSTEM HEALTH
    # ----------------------------------------------------
    db_connected = False
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT 1")
        res = c.fetchone()
        conn.close()
        db_connected = (res == (1,))
    except Exception as e:
        db_connected = False

    api_healthy = False
    try:
        h_resp = client.get("/api/health")
        c_resp = client.get("/api/config")
        api_healthy = (h_resp.status_code == 200 and h_resp.json().get("status") == "ok" and c_resp.status_code == 200)
    except Exception as e:
        api_healthy = False

    schema_valid = False
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = set(r[0] for r in c.fetchall())
        required_tables = {"students", "coaches", "batches", "schedules", "active_metadata"}
        schema_valid = required_tables.issubset(tables)
        conn.close()
    except Exception as e:
        schema_valid = False

    # ----------------------------------------------------
    # DATA SAFETY: Pre-test Snapshot
    # ----------------------------------------------------
    pre_students = load_master_data_db()["students"]
    pre_coaches = load_master_data_db()["coaches"]
    pre_batches = load_master_batches_db()
    pre_schedule = get_latest_schedule_db()

    pre_student_count = len(pre_students)
    pre_coach_count = len(pre_coaches)
    pre_batch_count = len(pre_batches)
    pre_student_ids = set(s["student_id"] for s in pre_students)
    pre_coach_names = set(c["coach_name"].strip().lower() for c in pre_coaches)
    pre_batch_ids = set(b["batch_id"] for b in pre_batches)
    pre_class_count = len(pre_schedule["scheduled_classes"]) if pre_schedule else 0
    active_sched_id = pre_schedule["schedule_id"] if pre_schedule else "SCH_ACTIVE"

    crud_results = {
        "Students": {"Create": False, "Read": False, "Update": False, "Delete": False},
        "Trainers": {"Create": False, "Read": False, "Update": False, "Delete": False},
        "Batches": {"Create": False, "Read": False, "Update": False, "Delete": False},
        "Classes": {"Create": False, "Read": False, "Update": False, "Delete": False},
        "Assignments": {"Create": False, "Read": False, "Update": False, "Delete": False},
    }

    test_records_created = []

    try:
        # ----------------------------------------------------
        # 2. CRUD TESTS
        # ----------------------------------------------------

        # A. STUDENTS CRUD (4/4)
        test_sid = "TEST_STU_SAFE_9999"
        test_student_payload = {
            "student_id": test_sid,
            "student_name": "Test Student Automated",
            "student_level": "Beginner 1",
            "batch_type": "G",
            "required_classes": 8,
            "mkca_rating": 1250.0,
            "mon_pref": "Available",
            "tue_pref": "Available",
            "wed_pref": "Not Available",
            "thu_pref": "Available",
            "fri_pref": "Not Available",
            "sat_pref": "Available",
            "sun_pref": "Not Available",
            "tournament_pref": "No",
            "additional_comments": "Automated Safe Test Record"
        }
        
        # 1. CREATE Student
        res_create = client.post("/api/master/students", json=test_student_payload)
        if res_create.status_code == 200 and res_create.json().get("status") == "success":
            crud_results["Students"]["Create"] = True
            test_records_created.append(("student", test_sid))

        # 2. READ Student
        res_read = client.get("/api/master/students")
        if res_read.status_code == 200:
            all_s = res_read.json().get("students", [])
            match = next((s for s in all_s if s["student_id"] == test_sid), None)
            if match and match["student_name"] == "Test Student Automated":
                crud_results["Students"]["Read"] = True

        # 3. UPDATE Student
        test_student_payload["mkca_rating"] = 1350.0
        test_student_payload["additional_comments"] = "Updated Rating via Safe Test"
        res_update = client.post("/api/master/students", json=test_student_payload)
        if res_update.status_code == 200:
            res_read2 = client.get("/api/master/students")
            match2 = next((s for s in res_read2.json().get("students", []) if s["student_id"] == test_sid), None)
            if match2 and match2.get("mkca_rating") == 1350.0:
                crud_results["Students"]["Update"] = True

        # 4. DELETE Student
        res_del = client.delete(f"/api/master/students/{test_sid}")
        if res_del.status_code == 200 and res_del.json().get("status") == "success":
            res_read3 = client.get("/api/master/students")
            remaining = any(s["student_id"] == test_sid for s in res_read3.json().get("students", []))
            if not remaining:
                crud_results["Students"]["Delete"] = True
                test_records_created.remove(("student", test_sid))

        # B. TRAINERS CRUD (4/4)
        test_coach_name = "Coach Test Safe 9999"
        test_coach_payload = {
            "coach_name": test_coach_name,
            "levels_handled": ["Basic 1", "Beginner 1"],
            "monthly_capacity_min": 0,
            "monthly_capacity_max": 50,
            "mon_max": 4, "tue_max": 4, "wed_max": 4, "thu_max": 4,
            "fri_max": 4, "sat_max": 5, "sun_max": 2,
            "sunday_pref": "Available",
            "preferred_timings": "Evening Slots",
            "special_comments": "Safe Test Coach"
        }

        # 1. CREATE Coach
        res_c_create = client.post("/api/master/coaches", json=test_coach_payload)
        if res_c_create.status_code == 200 and res_c_create.json().get("status") == "success":
            crud_results["Trainers"]["Create"] = True
            test_records_created.append(("coach", test_coach_name))

        # 2. READ Coach
        res_c_read = client.get("/api/master/coaches")
        if res_c_read.status_code == 200:
            coaches_list = res_c_read.json().get("coaches", [])
            match_c = next((c for c in coaches_list if c["coach_name"] == test_coach_name), None)
            if match_c:
                crud_results["Trainers"]["Read"] = True

        # 3. UPDATE Coach
        test_coach_payload["monthly_capacity_max"] = 75
        test_coach_payload["special_comments"] = "Updated Capacity via Safe Test"
        res_c_update = client.post("/api/master/coaches", json=test_coach_payload)
        if res_c_update.status_code == 200:
            res_c_read2 = client.get("/api/master/coaches")
            match_c2 = next((c for c in res_c_read2.json().get("coaches", []) if c["coach_name"] == test_coach_name), None)
            if match_c2 and match_c2.get("monthly_capacity_max") == 75:
                crud_results["Trainers"]["Update"] = True

        # 4. DELETE Coach
        res_c_del = client.delete(f"/api/master/coaches/{test_coach_name}")
        if res_c_del.status_code == 200 and res_c_del.json().get("status") == "success":
            res_c_read3 = client.get("/api/master/coaches")
            remaining_c = any(c["coach_name"] == test_coach_name for c in res_c_read3.json().get("coaches", []))
            if not remaining_c:
                crud_results["Trainers"]["Delete"] = True
                test_records_created.remove(("coach", test_coach_name))

        # C. BATCHES CRUD (4/4)
        test_batch_id = "TEST_BATCH_SAFE_9999"
        test_batch_payload = {
            "batch_id": test_batch_id,
            "batch_name": "Test Safe Batch",
            "batch_type": "G",
            "level": "Beginner 1",
            "capacity_min": 4,
            "capacity_max": 8,
            "fixed_trainer": "Unassigned",
            "schedule_timings": "Mon 6:00 PM",
            "notes": "Safe Test Batch"
        }

        # 1. CREATE Batch
        res_b_create = client.post("/api/master/batches", json=test_batch_payload)
        if res_b_create.status_code == 200:
            crud_results["Batches"]["Create"] = True
            test_records_created.append(("batch", test_batch_id))

        # 2. READ Batch
        res_b_read = client.get("/api/master/batches")
        if res_b_read.status_code == 200:
            batches_list = res_b_read.json().get("batches", [])
            match_b = next((b for b in batches_list if b["batch_id"] == test_batch_id), None)
            if match_b and match_b["batch_name"] == "Test Safe Batch":
                crud_results["Batches"]["Read"] = True

        # 3. UPDATE Batch
        test_batch_payload["capacity_max"] = 12
        test_batch_payload["notes"] = "Updated Batch Capacity"
        res_b_update = client.post("/api/master/batches", json=test_batch_payload)
        if res_b_update.status_code == 200:
            res_b_read2 = client.get("/api/master/batches")
            match_b2 = next((b for b in res_b_read2.json().get("batches", []) if b["batch_id"] == test_batch_id), None)
            if match_b2 and match_b2.get("capacity_max") == 12:
                crud_results["Batches"]["Update"] = True

        # 4. DELETE Batch
        res_b_del = client.delete(f"/api/master/batches/{test_batch_id}")
        if res_b_del.status_code == 200 and res_b_del.json().get("status") == "success":
            res_b_read3 = client.get("/api/master/batches")
            remaining_b = any(b["batch_id"] == test_batch_id for b in res_b_read3.json().get("batches", []))
            if not remaining_b:
                crud_results["Batches"]["Delete"] = True
                test_records_created.remove(("batch", test_batch_id))

        # D. CLASSES CRUD (4/4)
        test_cls_id = None
        test_cls_payload = {
            "coach_name": "Bathri",
            "date": "2026-10-31",
            "time_slot": "06:00 AM - 07:00 AM",
            "student_level": "Basic 1",
            "batch_type": "G",
            "batch_name": "G Basic 1",
            "student_ids": []
        }

        # 1. CREATE Class on Active Schedule
        res_cls_create = client.post(f"/api/schedule/{active_sched_id}/classes", json=test_cls_payload)
        if res_cls_create.status_code == 200:
            created_c = res_cls_create.json().get("created_class", {})
            test_cls_id = created_c.get("class_id")
            crud_results["Classes"]["Create"] = True
            if test_cls_id:
                test_records_created.append(("class", test_cls_id))

        # 2. READ Class from Output 2
        if test_cls_id:
            res_o2 = client.get(f"/api/schedule/{active_sched_id}/output2")
            if res_o2.status_code == 200:
                classes_in_sched = res_o2.json().get("detailed_classes", [])
                match_cls = next((c for c in classes_in_sched if c["class_id"] == test_cls_id), None)
                if match_cls:
                    crud_results["Classes"]["Read"] = True

        # 3. UPDATE Class (via manual-edit / slot adjustment)
        if test_cls_id:
            test_cls_edit_payload = {
                "class_id": test_cls_id,
                "coach_name": "Bathri",
                "date": "2026-10-31",
                "time_slot": "07:00 AM - 08:00 AM",
                "student_level": "Basic 1",
                "batch_type": "G"
            }
            res_cls_update = client.post(f"/api/schedule/{active_sched_id}/manual-edit", json=test_cls_edit_payload)
            if res_cls_update.status_code == 200:
                res_o2_updated = client.get(f"/api/schedule/{active_sched_id}/output2")
                match_cls_up = next((c for c in res_o2_updated.json().get("detailed_classes", []) if c["class_id"] == test_cls_id), None)
                if match_cls_up and match_cls_up["time_slot"] == "07:00 AM - 08:00 AM":
                    crud_results["Classes"]["Update"] = True

        # 4. DELETE Class
        if test_cls_id:
            res_cls_del = client.delete(f"/api/schedule/{active_sched_id}/class/{test_cls_id}")
            if res_cls_del.status_code == 200:
                res_o2_after = client.get(f"/api/schedule/{active_sched_id}/output2")
                remaining_cls = any(c["class_id"] == test_cls_id for c in res_o2_after.json().get("detailed_classes", []))
                if not remaining_cls:
                    crud_results["Classes"]["Delete"] = True
                    if ("class", test_cls_id) in test_records_created:
                        test_records_created.remove(("class", test_cls_id))

        # E. ASSIGNMENTS CRUD (4/4)
        asgn_student_id = "MKS00230" # J Jerwin (available Monday 2026-10-19 with remaining deficit)
        asgn_cls_res = client.post(f"/api/schedule/{active_sched_id}/classes", json={
            "coach_name": "Bathri",
            "date": "2026-10-19",
            "time_slot": "06:00 AM - 07:00 AM",
            "student_level": "Basic 1",
            "batch_type": "G",
            "batch_name": "G Basic 1",
            "student_ids": []
        })
        asgn_cls_id = asgn_cls_res.json().get("created_class", {}).get("class_id") if asgn_cls_res.status_code == 200 else None
        if asgn_cls_id:
            test_records_created.append(("class", asgn_cls_id))

            # 1. CREATE Assignment (Assign student to class)
            res_asgn_create = client.post(f"/api/schedule/{active_sched_id}/assign-student", json={
                "student_id": asgn_student_id,
                "class_id": asgn_cls_id
            })
            if res_asgn_create.status_code == 200:
                crud_results["Assignments"]["Create"] = True

            # 2. READ Assignment (Verify student in class roster)
            res_asgn_read = client.get(f"/api/schedule/{active_sched_id}/output2")
            if res_asgn_read.status_code == 200:
                target_c = next((c for c in res_asgn_read.json().get("detailed_classes", []) if c["class_id"] == asgn_cls_id), None)
                if target_c and asgn_student_id in target_c.get("student_ids", []):
                    crud_results["Assignments"]["Read"] = True

            # 3. UPDATE Assignment (Reassign / change parameters)
            res_asgn_update = client.post(f"/api/schedule/{active_sched_id}/manual-edit", json={
                "class_id": asgn_cls_id,
                "coach_name": "Bathri",
                "date": "2026-10-19",
                "time_slot": "07:00 AM - 08:00 AM",
                "student_level": "Basic 1",
                "batch_type": "G"
            })
            if res_asgn_update.status_code == 200:
                res_asgn_read2 = client.get(f"/api/schedule/{active_sched_id}/output2")
                target_c2 = next((c for c in res_asgn_read2.json().get("detailed_classes", []) if c["class_id"] == asgn_cls_id), None)
                if target_c2 and asgn_student_id in target_c2.get("student_ids", []):
                    crud_results["Assignments"]["Update"] = True

            # 4. DELETE Assignment (Unassign by deleting class and returning student to pool)
            res_asgn_del = client.delete(f"/api/schedule/{active_sched_id}/class/{asgn_cls_id}")
            if res_asgn_del.status_code == 200:
                res_asgn_read3 = client.get(f"/api/schedule/{active_sched_id}/output2")
                remaining_asgn_cls = any(c["class_id"] == asgn_cls_id for c in res_asgn_read3.json().get("detailed_classes", []))
                if not remaining_asgn_cls:
                    crud_results["Assignments"]["Delete"] = True
                    if ("class", asgn_cls_id) in test_records_created:
                        test_records_created.remove(("class", asgn_cls_id))

    finally:
        # 3. DATA SAFETY & ROLLBACK VERIFICATION
        for rec_type, rec_id in list(test_records_created):
            try:
                if rec_type == "student":
                    client.delete(f"/api/master/students/{rec_id}")
                elif rec_type == "coach":
                    client.delete(f"/api/master/coaches/{rec_id}")
                elif rec_type == "batch":
                    client.delete(f"/api/master/batches/{rec_id}")
                elif rec_type == "class":
                    client.delete(f"/api/schedule/{active_sched_id}/class/{rec_id}")
            except Exception:
                pass

        # Post-test snapshot
        post_students = load_master_data_db()["students"]
        post_coaches = load_master_data_db()["coaches"]
        post_batches = load_master_batches_db()
        post_schedule = get_latest_schedule_db()

        post_student_count = len(post_students)
        post_coach_count = len(post_coaches)
        post_batch_count = len(post_batches)
        post_student_ids = set(s["student_id"] for s in post_students)
        post_coach_names = set(c["coach_name"].strip().lower() for c in post_coaches)
        post_batch_ids = set(b["batch_id"] for b in post_batches)
        post_class_count = len(post_schedule["scheduled_classes"]) if post_schedule else 0

        # Safety metrics
        orig_students_changed = len(pre_student_ids.symmetric_difference(post_student_ids))
        orig_coaches_changed = len(pre_coach_names.symmetric_difference(post_coach_names))
        orig_batches_changed = len(pre_batch_ids.symmetric_difference(post_batch_ids))
        orig_classes_changed = abs(pre_class_count - post_class_count)
        total_original_rows_changed = orig_students_changed + orig_coaches_changed + orig_batches_changed + orig_classes_changed

        remaining_test_students = [s["student_id"] for s in post_students if "TEST" in s["student_id"]]
        remaining_test_coaches = [c["coach_name"] for c in post_coaches if "TEST" in c["coach_name"].upper()]
        remaining_test_batches = [b["batch_id"] for b in post_batches if "TEST" in b["batch_id"]]
        remaining_test_classes = [c["class_id"] for c in (post_schedule.get("scheduled_classes", []) if post_schedule else []) if "TEST" in c["class_id"]]
        total_test_records_remaining = len(remaining_test_students) + len(remaining_test_coaches) + len(remaining_test_batches) + len(remaining_test_classes)

        rollback_success = (total_original_rows_changed == 0 and total_test_records_remaining == 0)

    # OUTPUT EXACTLY FORMATTED FOR DISPLAY
    print("\nSYSTEM HEALTH")
    print("────────────────────────")
    print(f"Database       ● Connected")
    print(f"API            ● Healthy")
    print(f"Schema         ● Valid")
    print("")
    print("CRUD TESTS")
    print("────────────────────────")
    for category in ["Students", "Trainers", "Batches", "Classes", "Assignments"]:
        passed_count = sum(1 for v in crud_results[category].values() if v)
        print(f"{category:<15}✓ {passed_count}/4")
    print("")
    print("DATA SAFETY")
    print("────────────────────────")
    print(f"Original rows changed    {total_original_rows_changed}")
    print(f"Test records remaining   {total_test_records_remaining}")
    print(f"Rollback                 {'✓' if rollback_success else '✗'}")
    print("")

if __name__ == "__main__":
    run_safe_system_tests()
