import sqlite3
import json

conn = sqlite3.connect("backend/data/chess_scheduler.db")
c = conn.cursor()
c.execute("SELECT schedule_id, start_date, end_date, is_active, status FROM schedules")
rows = c.fetchall()
print("All schedules in DB:")
for r in rows:
    print(r)

c.execute("SELECT schedule_id, start_date, end_date, is_active FROM schedules WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1")
active = c.fetchone()
print("\nActive schedule:", active)
if active:
    s_id = active[0]
    c.execute("SELECT coach_name, count(*) FROM scheduled_classes WHERE schedule_id = ? GROUP BY coach_name", (s_id,))
    coaches_in_classes = c.fetchall()
    print("Classes per coach in active schedule:", coaches_in_classes)
    
    c.execute("SELECT output1_data, output2_data FROM schedule_outputs WHERE schedule_id = ?", (s_id,))
    out_row = c.fetchone()
    if out_row:
        o1 = json.loads(out_row[0]) if out_row[0] else {}
        o2 = json.loads(out_row[1]) if out_row[1] else {}
        print("Output1 coach_slots total:", len(o1.get("coach_slots", [])))
        # Check coaches in output1
        o1_coaches = set()
        for slot in o1.get("coach_slots", []):
            for ch in slot.get("coaches", []):
                o1_coaches.add(ch)
        print("Output1 coaches:", o1_coaches)
        print("Output2 detailed_classes total:", len(o2.get("detailed_classes", [])))
        o2_coaches = set(cls.get("coach_name") for cls in o2.get("detailed_classes", []))
        print("Output2 coaches in detailed_classes:", o2_coaches)
        print("Output2 coach_summaries:", [cs.get("coach_name") for cs in o2.get("coach_summaries", [])])
conn.close()
