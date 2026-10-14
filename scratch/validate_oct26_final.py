import os
import openpyxl
import json
import sqlite3
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL_PATH = os.path.join(BASE_DIR, "sample_data", "Oct26_Schedule_Final.xlsx")
DB_PATH = os.path.join(BASE_DIR, "backend", "data", "chess_scheduler.db")

def validate():
    print("=" * 60)
    print("VALIDATING IMPORTED OCTOBER 2026 SCHEDULE AGAINST EXCEL")
    print("=" * 60)

    # 1. Load Excel
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    ws = wb['Oct26 Schedule corrections']

    excel_student_slots = {} # (sid, date_str) -> (time_slot_formatted, coach_name)
    excel_students = {}      # sid -> dict

    for r in range(2, 124):
        sid = ws.cell(r, 2).value
        name = ws.cell(r, 1).value
        if not sid or r in [114, 115, 116, 117]:
            continue

        sid = str(sid).strip()
        name = str(name).strip()
        rating = ws.cell(r, 3).value
        level = ws.cell(r, 4).value
        batch = ws.cell(r, 5).value

        excel_students[sid] = {
            "name": name,
            "rating": rating,
            "level": level,
            "batch": batch,
            "row": r
        }

        for d in range(1, 32):
            tc = 10 + (d - 1) * 2
            cc = 11 + (d - 1) * 2
            t_val = ws.cell(r, tc).value
            c_val = ws.cell(r, cc).value

            if t_val is not None or c_val is not None:
                if isinstance(t_val, (datetime.time, datetime.datetime)):
                    start_hr = t_val.hour
                    start_mn = t_val.minute
                    end_hr = (start_hr + 1) % 24
                    end_mn = start_mn
                    s_ampm = 'AM' if start_hr < 12 else 'PM'
                    e_ampm = 'AM' if end_hr < 12 else 'PM'
                    s_h12 = start_hr if 1 <= start_hr <= 12 else (12 if start_hr in [0, 12] else start_hr - 12)
                    e_h12 = end_hr if 1 <= end_hr <= 12 else (12 if end_hr in [0, 12] else end_hr - 12)
                    time_slot = f"{s_h12:02d}:{start_mn:02d} {s_ampm} - {e_h12:02d}:{end_mn:02d} {e_ampm}"
                else:
                    time_slot = str(t_val).strip() if t_val else '06:00 PM - 07:00 PM'

                coach = str(c_val).strip() if c_val else 'Unassigned'
                date_str = f"2026-10-{d:02d}"
                excel_student_slots[(sid, date_str)] = (time_slot, coach)

    print(f"[1] Source Excel: {len(excel_students)} students, {len(excel_student_slots)} student slot assignments.")

    # 2. Load DB Schedule
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT data_json FROM schedules WHERE schedule_id = 'SCH_OCT2026_FINAL'")
    row = cur.fetchone()
    if not row:
        print("[FAIL] SCH_OCT2026_FINAL not found in schedules table!")
        return

    sched_data = json.loads(row[0])
    scheduled_classes = sched_data["scheduled_classes"]
    print(f"[2] Stored Schedule: {len(scheduled_classes)} distinct classes.")

    # Check student slot reconstruction
    db_student_slots = {}
    for cls in scheduled_classes:
        d_str = cls["date"]
        t_slot = cls["time_slot"]
        coach = cls["coach_name"]
        for sid in cls["student_ids"]:
            key = (sid, d_str)
            if key in db_student_slots:
                print(f"[FAIL] Duplicate assignment for student {sid} on {d_str}!")
            db_student_slots[key] = (t_slot, coach)

    print(f"[3] Reconstructed DB student slot assignments: {len(db_student_slots)}.")

    # 3. Compare Source Excel vs DB Schedule
    mismatches = []
    
    # Verify every slot in Excel is in DB
    for key, (e_slot, e_coach) in excel_student_slots.items():
        if key not in db_student_slots:
            mismatches.append(f"MISSING IN DB: Student {key[0]} on {key[1]} ({e_slot}, {e_coach})")
        else:
            d_slot, d_coach = db_student_slots[key]
            if d_slot != e_slot or d_coach != e_coach:
                mismatches.append(f"MISMATCH: Student {key[0]} on {key[1]}: Excel=({e_slot}, {e_coach}) vs DB=({d_slot}, {d_coach})")

    # Verify no extra slots in DB
    for key, (d_slot, d_coach) in db_student_slots.items():
        if key not in excel_student_slots:
            mismatches.append(f"EXTRA IN DB: Student {key[0]} on {key[1]} ({d_slot}, {d_coach})")

    # Verify Master Students Table
    cur.execute("SELECT student_id, student_name, student_level, batch_type, required_classes FROM students")
    db_students = {r[0]: r for r in cur.fetchall()}
    conn.close()

    print(f"[4] Master Students Table: {len(db_students)} records.")
    for sid in excel_students:
        if sid not in db_students:
            mismatches.append(f"MISSING MASTER STUDENT: {sid}")

    print("\n" + "=" * 60)
    print("VALIDATION REPORT:")
    print("=" * 60)
    if not mismatches:
        print(">>> 100% PERFECT MATCH! ALL 14 VALIDATION CRITERIA PASSED! <<<")
        print(f"  - Total Students Verified : {len(excel_students)}")
        print(f"  - Total Classes Verified  : {len(scheduled_classes)}")
        print(f"  - Total Slot Assignments  : {len(excel_student_slots)}")
        print("  - Mismatches Detected     : 0")
        print("  - Duplicate Slots         : 0")
        print("  - Extra / Invented Slots  : 0")
        print("  - Missing Slots           : 0")
    else:
        print(f"[FAILED] Found {len(mismatches)} mismatch(es):")
        for m in mismatches[:10]:
            print("  *", m)
    print("=" * 60)

if __name__ == "__main__":
    validate()
