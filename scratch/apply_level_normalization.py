import sys
import os
import sqlite3
import json

sys.path.insert(0, os.path.abspath("backend"))
from app.constants.levels import OFFICIAL_LEVELS, normalize_batch_to_level

db_path = 'backend/data/chess_scheduler.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Map student_id -> batch_name from batches table
batch_mapping = {}
for b in cursor.execute("SELECT batch_id, batch_name, level, student_ids_json FROM batches").fetchall():
    b_id, b_name, b_level, sids_json = b
    sids = json.loads(sids_json) if sids_json else []
    for sid in sids:
        batch_mapping[sid] = b_name

# 2. Update students table
students = cursor.execute("SELECT student_id, student_name, student_level, batch_type, data_json FROM students").fetchall()
print(f"Total students to process: {len(students)}")

updated_students = 0
for s in students:
    sid, sname, curr_level, btype, dj_str = s
    batch_name = batch_mapping.get(sid, "")
    calc_level, is_unres, reason = normalize_batch_to_level(batch_name, sid)
    if is_unres:
        raise ValueError(f"Cannot update student {sname} ({sid}): unresolved level for batch '{batch_name}' ({reason})")

    # Update data_json
    dj = json.loads(dj_str) if dj_str else {}
    dj["student_level"] = calc_level

    cursor.execute("""
        UPDATE students
        SET student_level = ?, data_json = ?
        WHERE student_id = ?
    """, (calc_level, json.dumps(dj), sid))
    updated_students += 1

print(f"Updated {updated_students} students.")

# 3. Update batches table level field
batches = cursor.execute("SELECT batch_id, batch_name, level, data_json FROM batches").fetchall()
updated_batches = 0
for b in batches:
    bid, bname, curr_b_level, dj_str = b
    norm_level, is_unres, _ = normalize_batch_to_level(bname)
    dj = json.loads(dj_str) if dj_str else {}
    dj["level"] = norm_level

    cursor.execute("""
        UPDATE batches
        SET level = ?, data_json = ?
        WHERE batch_id = ?
    """, (norm_level, json.dumps(dj), bid))
    updated_batches += 1

print(f"Updated {updated_batches} batches.")

# 4. Update coaches levels_handled_json
coaches = cursor.execute("SELECT coach_name, levels_handled_json, data_json FROM coaches").fetchall()
updated_coaches = 0
for c in coaches:
    cname, levels_json, dj_str = c
    current_handled = json.loads(levels_json) if levels_json else []
    # Retain official levels only
    valid_handled = [lvl for lvl in OFFICIAL_LEVELS if any(lvl.lower() == ch.lower() for ch in current_handled)]
    if not valid_handled:
        # Default all coaches to official levels
        valid_handled = list(OFFICIAL_LEVELS)
    
    dj = json.loads(dj_str) if dj_str else {}
    dj["levels_handled"] = valid_handled

    cursor.execute("""
        UPDATE coaches
        SET levels_handled_json = ?, data_json = ?
        WHERE coach_name = ?
    """, (json.dumps(valid_handled), json.dumps(dj), cname))
    updated_coaches += 1

print(f"Updated {updated_coaches} coaches.")

conn.commit()

# ================= VALIDATION =================
print("\n--- VALIDATING DATABASE INTEGRITY ---")
distinct_student_levels = [row[0] for row in cursor.execute("SELECT DISTINCT student_level FROM students").fetchall()]
print(f"Distinct student levels: {distinct_student_levels}")

for lvl in distinct_student_levels:
    assert lvl in OFFICIAL_LEVELS, f"Invalid level in DB: {lvl}"

assert "Beginner" not in distinct_student_levels, "Found generic 'Beginner' in students!"
assert "Beginner 3" not in distinct_student_levels, "Found 'Beginner 3' in students!"
assert "Intermediate" not in distinct_student_levels, "Found generic 'Intermediate' in students!"

distinct_batch_levels = [row[0] for row in cursor.execute("SELECT DISTINCT level FROM batches").fetchall()]
print(f"Distinct batch levels: {distinct_batch_levels}")
for lvl in distinct_batch_levels:
    assert lvl in OFFICIAL_LEVELS, f"Invalid batch level in DB: {lvl}"

total_stu = cursor.execute("SELECT COUNT(*) FROM students").fetchone()[0]
assert total_stu == 127, f"Expected 127 students, got {total_stu}"

total_b = cursor.execute("SELECT COUNT(*) FROM batches").fetchone()[0]
assert total_b == 35, f"Expected 35 batches, got {total_b}"

conn.close()
print("\nAll database level validations passed successfully!")
