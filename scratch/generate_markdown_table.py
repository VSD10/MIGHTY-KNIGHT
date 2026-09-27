import sqlite3
import json

conn = sqlite3.connect('backend/data/chess_scheduler.db')
cursor = conn.cursor()

# Get batch names from batches table
batch_mapping = {}
for b in cursor.execute("SELECT batch_id, batch_name, level, student_ids_json FROM batches").fetchall():
    b_id, b_name, b_level, sids_json = b
    sids = json.loads(sids_json) if sids_json else []
    for sid in sids:
        batch_mapping[sid] = b_name

# Get all students
students = cursor.execute("SELECT student_id, student_name, student_level FROM students ORDER BY student_name ASC").fetchall()

print(f"| Student | Student ID | Batch | Level |")
print(f"|---|---|---|---|")
for sid, sname, level in students:
    batch = batch_mapping.get(sid, "-")
    print(f"| {sname} | {sid} | {batch} | **{level}** |")

conn.close()
