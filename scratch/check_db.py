import sqlite3
import json

conn = sqlite3.connect('backend/data/chess_scheduler.db')
cursor = conn.cursor()

batches = cursor.execute("SELECT batch_id, batch_name, level, student_ids_json FROM batches").fetchall()
for b in batches:
    sids = json.loads(b[3]) if b[3] else []
    print(f"{b[0]}: {b[1]} | level={b[2]} | students count={len(sids)} | sample={sids[:3]}")

conn.close()
