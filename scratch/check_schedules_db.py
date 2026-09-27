import sqlite3
import json

conn = sqlite3.connect('backend/data/chess_scheduler.db')
cursor = conn.cursor()

schedules = cursor.execute("SELECT schedule_id, status, total_students, scheduled_students, data_json FROM schedules").fetchall()
print(f"Total schedules in DB: {len(schedules)}")
for sc in schedules:
    sid, status, tot, sched, dj_str = sc
    print(f"Schedule: {sid}, status={status}, total={tot}, sched={sched}")
    if dj_str:
        dj = json.loads(dj_str)
        print("  Keys:", list(dj.keys()))
        if 'classes' in dj:
            print("  Classes count:", len(dj['classes']))
            if len(dj['classes']) > 0:
                print("  Sample class:", dj['classes'][0])

conn.close()
