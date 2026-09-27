import sqlite3
import json

conn = sqlite3.connect('backend/data/chess_scheduler.db')
cursor = conn.cursor()

# Get all students
students = cursor.execute("SELECT student_id, student_name, student_level, batch_type, data_json FROM students").fetchall()
print(f"Total students in DB: {len(students)}")

# Build student_id -> batch mapping from batches table
batch_mapping = {}
for b in cursor.execute("SELECT batch_id, batch_name, level, student_ids_json FROM batches").fetchall():
    b_id, b_name, b_level, sids_json = b
    sids = json.loads(sids_json) if sids_json else []
    for sid in sids:
        batch_mapping[sid] = (b_id, b_name, b_level)

print(f"Students mapped in batches table: {len(batch_mapping)}")

unmapped = []
for s in students:
    sid = s[0]
    if sid not in batch_mapping:
        unmapped.append((sid, s[1]))

print(f"Unmapped students in batches table: {len(unmapped)}")
if unmapped:
    print("Sample unmapped:", unmapped[:5])

conn.close()
