import sys
import os
import sqlite3
import json
from collections import Counter

sys.path.insert(0, os.path.abspath("backend"))
from app.constants.levels import OFFICIAL_LEVELS, normalize_batch_to_level

conn = sqlite3.connect('backend/data/chess_scheduler.db')
cursor = conn.cursor()

# Get student_id -> batch_name from batches table
batch_mapping = {}
for b in cursor.execute("SELECT batch_id, batch_name, level, student_ids_json FROM batches").fetchall():
    b_id, b_name, b_level, sids_json = b
    sids = json.loads(sids_json) if sids_json else []
    for sid in sids:
        batch_mapping[sid] = b_name

# Query all students
students = cursor.execute("SELECT student_id, student_name, student_level FROM students ORDER BY student_id ASC").fetchall()

report_rows = []
unresolved = []
counts = Counter()

for sid, sname, curr_level in students:
    batch = batch_mapping.get(sid, "")
    calc_level, is_unres, reason = normalize_batch_to_level(batch, sid)
    if is_unres:
        unresolved.append((sname, sid, batch, curr_level, reason))
    else:
        counts[calc_level] += 1
    report_rows.append((sname, sid, batch, curr_level, calc_level))

print(f"Total students: {len(students)}")
print()
for lvl in OFFICIAL_LEVELS:
    print(f"{lvl}: {counts[lvl]}")
print(f"Unresolved: {len(unresolved)}")

if unresolved:
    print("\nUNRESOLVED LEVEL MAPPING:")
    for u in unresolved:
        print(f"  Student: {u[0]}, ID: {u[1]}, Batch: {u[2]}, Current Level: {u[3]}, Reason: {u[4]}")

conn.close()
