import os
import sys
import json
import sqlite3
from collections import defaultdict

# Add backend directory to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.constants.batch_naming import (
    BATCH_TYPES, SUBDIVISION_CAPACITIES, LEVEL_TO_CODE, CODE_TO_LEVEL,
    extract_source_suffix_tag, format_batch_subdivision_name,
    resolve_level_code, allocate_students_to_subdivisions
)
from app.storage.database import (
    get_connection, get_db_path, save_all_master_batches_db,
    save_master_data_db, save_baseline_db, get_latest_schedule_db,
    save_schedule_db, compute_master_data_fingerprint
)
from app.config import DEFAULT_CONFIG

REF_JSON_PATH = os.path.join(BACKEND_DIR, "data", "reference_oct_schedule.json")

def apply_subdivisions():
    print(f"Loading reference data from: {REF_JSON_PATH}")
    with open(REF_JSON_PATH, "r", encoding="utf-8") as f:
        ref_data = json.load(f)

    students_raw = ref_data.get("students_raw", [])
    classes_by_date = ref_data.get("oct_exact_classes_by_date", {})
    coaches_list = ref_data.get("coaches_list", [])

    print(f"Allocating {len(students_raw)} students into strict subdivisions...")
    subdivisions, warnings = allocate_students_to_subdivisions(students_raw)

    print(f"Generated {len(subdivisions)} subdivisions:")
    student_id_to_sub = {}
    for sub in subdivisions:
        for sid in sub["student_ids"]:
            student_id_to_sub[sid] = sub

    # 1. Update students_raw with subdivision batch and source_tag
    updated_students = []
    for st in students_raw:
        sid = st["student_id"]
        sub = student_id_to_sub.get(sid)
        if sub:
            st["batch"] = sub["batch_name"]
            st["batch_name"] = sub["batch_name"]
            st["assigned_batch_id"] = sub["batch_id"]
            st["batch_type"] = sub["batch_type"]
            st["student_level"] = sub["level"]
        else:
            btype = st.get("batch_type", "G")
            lvl = st.get("student_level", "Beginner 1")
            code = resolve_level_code(lvl)
            st["batch"] = f"{btype}{code}-01"
            st["batch_name"] = f"{btype}{code}-01"
            st["assigned_batch_id"] = f"BAT_{btype}{code}_01"

        # Preserve source tag
        if "source_tag" not in st or not st["source_tag"]:
            tag, _ = extract_source_suffix_tag(st.get("additional_comments", "") + " " + st.get("batch_name", ""))
            if tag:
                st["source_tag"] = tag

        updated_students.append(st)

    # 2. Update classes_by_date with strict subdivision batch names
    updated_classes_by_date = {}
    for dt, clist in classes_by_date.items():
        updated_clist = []
        for c in clist:
            c_copy = dict(c)
            s_ids = c_copy.get("student_ids", [])
            subs = {student_id_to_sub[sid]["batch_name"] for sid in s_ids if sid in student_id_to_sub}

            if len(subs) == 1:
                c_copy["batch_name"] = list(subs)[0]
                first_sub = student_id_to_sub[s_ids[0]]
                c_copy["student_level"] = first_sub["level"]
                c_copy["batch_type"] = first_sub["batch_type"]
            elif len(subs) > 1:
                # Check if all share same prefix (e.g. GBN1)
                prefixes = {s.split("-")[0] for s in subs}
                if len(prefixes) == 1:
                    pref = list(prefixes)[0]
                    # Format as primary subdivision e.g. GBN1-01
                    first_sid = s_ids[0]
                    c_copy["batch_name"] = student_id_to_sub[first_sid]["batch_name"]
                else:
                    c_copy["batch_name"] = "MIXED"
            else:
                c_copy["batch_name"] = "GB1-01"

            updated_clist.append(c_copy)
        updated_classes_by_date[dt] = updated_clist

    # 3. Update weekday_templates
    updated_weekday_templates = defaultdict(list)
    for dy, t_list in ref_data.get("weekday_templates", {}).items():
        for t_entry in t_list:
            t_copy = dict(t_entry)
            sid = t_copy.get("student_id")
            if sid in student_id_to_sub:
                sub = student_id_to_sub[sid]
                t_copy["batch_name"] = sub["batch_name"]
                t_copy["student_level"] = sub["level"]
                t_copy["batch_type"] = sub["batch_type"]
            updated_weekday_templates[dy].append(t_copy)

    # 4. Save updated reference_oct_schedule.json
    ref_data["students_raw"] = updated_students
    ref_data["oct_exact_classes_by_date"] = updated_classes_by_date
    ref_data["weekday_templates"] = dict(updated_weekday_templates)

    with open(REF_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(ref_data, f, indent=2, ensure_ascii=False)
    print(f"Saved updated reference JSON to {REF_JSON_PATH}")

    # 5. Populate Master Batches in SQLite
    print(f"Persisting {len(subdivisions)} Master Batches into SQLite database...")
    save_all_master_batches_db(subdivisions)

    # 6. Populate Master Students & Baseline in SQLite
    db_path = get_db_path()
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Clear and repopulate students table
    cursor.execute("DELETE FROM students")
    for s in updated_students:
        cursor.execute("""
            INSERT OR REPLACE INTO students (
                student_id, student_name, student_level, batch_type, region_timezone, required_classes, data_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            s["student_id"],
            s["student_name"],
            s["student_level"],
            s["batch_type"],
            s.get("region_timezone", "IST"),
            s.get("required_classes", 12),
            json.dumps(s)
        ))
    conn.commit()
    conn.close()
    print(f"Updated {len(updated_students)} master students in SQLite.")

    # 7. Update Absolute Baseline (v1) in SQLite
    all_classes = []
    seat_count = 0
    for dt, cls_list in updated_classes_by_date.items():
        for c in cls_list:
            all_classes.append(c)
            seat_count += len(c.get("student_ids", []))

    save_baseline_db({
        "month": "2026-10",
        "version": 1,
        "status": "Active",
        "file_name": "Oct'26 Schedule_FRESH-1.xlsx",
        "uploaded_by": "System Batch Subdivision Update",
        "uploaded_at": "2026-10-01 12:00 PM",
        "student_count": len(updated_students),
        "class_count": len(all_classes),
        "student_class_count": seat_count,
        "students_data": updated_students,
        "classes_data": all_classes,
        "baseline_exceptions": [],
        "validation_report": {"blocking": [], "baseline_exceptions": [], "info": []},
        "created_at": "2026-10-01 12:00:00"
    })
    print(f"Saved updated Active Baseline for 2026-10: {len(all_classes)} classes, {seat_count} seats.")

    # 8. Update Active Schedule in SQLite
    fp = compute_master_data_fingerprint(config_dict=DEFAULT_CONFIG.model_dump())
    sched_obj = {
        "schedule_id": "SCHED_202610",
        "status": "Active",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31",
        "total_students_considered": len(updated_students),
        "successfully_scheduled_students": len(updated_students),
        "unscheduled_students_count": 0,
        "accountability_passed": True,
        "scheduled_classes": all_classes,
        "unscheduled_records": [],
        "coach_schedule": [],
        "created_at": "2026-10-01 12:00:00",
        "master_data_fingerprint": fp,
        "is_stale": False
    }
    save_schedule_db(sched_obj)
    print("Successfully synchronized active schedule with strict subdivision naming!")

if __name__ == "__main__":
    apply_subdivisions()
