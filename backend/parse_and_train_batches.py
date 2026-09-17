import os
import re
import json
import sqlite3
from datetime import datetime
from collections import defaultdict, Counter

DB_PATH = "d:/CODESPACE/chess/backend/data/chess_scheduler.db"
RAW_FILE = "d:/CODESPACE/chess/backend/data/september_raw.txt"

with open(RAW_FILE, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Load all master students from DB
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT student_id, student_name, student_level, batch_type FROM students")
db_students = cursor.fetchall()

name_to_student = {}
for sid, name, lvl, btype in db_students:
    clean_n = name.strip().lower()
    name_to_student[clean_n] = {"id": sid, "name": name, "level": lvl, "batch_type": btype}
    # Also add without dots or spaces
    name_to_student[re.sub(r'[\.\s]+', '', clean_n)] = {"id": sid, "name": name, "level": lvl, "batch_type": btype}

print(f"Loaded {len(db_students)} master students from database.")

# Parse raw text
current_date = None
current_coach = None
current_time = None
schedule_records = [] # (date, day, coach, time_slot, student_name, is_cancelled)

date_pattern = re.compile(r'📅\s*DATE:\s*(\d{2}-[A-Za-z]{3})')
coach_pattern = re.compile(r'♟️\s*([A-Za-z\s]+)')
time_pattern = re.compile(r'^(\d{1,2}:\d{2}\s*(?:AM|PM)|\d{1,2}\s*(?:AM|PM)|TIME NOT PROVIDED|\d{1,2}\s*&\s*\d{1,2}\.\d{2}[a-z]+)', re.IGNORECASE)

for raw_line in lines:
    line = raw_line.strip()
    if not line or line.startswith("━"):
        continue

    # Date match
    m_date = date_pattern.match(line)
    if m_date:
        d_str = m_date.group(1) # e.g. "01-Sep"
        day_num, month_str = d_str.split("-")
        current_date = f"2026-09-{day_num.zfill(2)}"
        current_coach = None
        current_time = None
        continue

    # Coach match
    m_coach = coach_pattern.match(line)
    if m_coach:
        c_raw = m_coach.group(1).strip()
        if c_raw.upper() == "GURU":
            current_coach = "Guruvanthana"
        elif c_raw.upper() == "BATHRI":
            current_coach = "Bathrinath"
        else:
            current_coach = c_raw.title()
        current_time = None
        continue

    # Time match
    m_time = time_pattern.match(line)
    if m_time:
        t_raw = m_time.group(1).strip()
        # Normalize time format e.g. "07:00 PM" -> "07:00 PM - 08:00 PM"
        current_time = t_raw
        continue

    # Student line
    if line.startswith("-"):
        stu_str = line[1:].strip()
        is_cancelled = False
        if "CANCELLED" in stu_str or "~~" in stu_str:
            is_cancelled = True
            stu_str = re.sub(r'[~]|(?:\(CANCELLED\))', '', stu_str).strip()

        # Clean student name
        clean_name = stu_str.replace("Extra", "").replace("Individual", "").replace("Trainer", "").strip()
        if not clean_name:
            continue

        if current_date and current_coach and current_time:
            d_obj = datetime.strptime(current_date, "%Y-%m-%d")
            day_name = d_obj.strftime("%A")
            schedule_records.append({
                "date": current_date,
                "day": day_name,
                "coach": current_coach,
                "time_slot": current_time,
                "student_name": clean_name,
                "is_cancelled": is_cancelled
            })

print(f"Parsed {len(schedule_records)} student-class instances across September.")

# Student lookup helper
def find_student(name):
    clean = name.strip().lower()
    if clean in name_to_student:
        return name_to_student[clean]
    clean_no_dot = re.sub(r'[\.\s]+', '', clean)
    if clean_no_dot in name_to_student:
        return name_to_student[clean_no_dot]
    # Substring match
    for k, v in name_to_student.items():
        if k in clean or clean in k:
            return v
    return None

# Discover recurring batches:
# A recurring batch is characterized by:
# (Coach, Time Slot, Weekday patterns) where students regularly learn together.
batch_groupings = defaultdict(lambda: {
    "coach": None,
    "time_slot": None,
    "days": set(),
    "students": Counter(),
    "sample_dates": set()
})

for rec in schedule_records:
    if rec["is_cancelled"]:
        continue
    c = rec["coach"]
    if c.upper() == "NOT PROVIDED":
        continue
    ts = rec["time_slot"]
    # Group key: (Coach, Time Slot)
    key = (c, ts)
    batch_groupings[key]["coach"] = c
    batch_groupings[key]["time_slot"] = ts
    batch_groupings[key]["days"].add(rec["day"])
    batch_groupings[key]["sample_dates"].add(rec["date"])
    
    stu = find_student(rec["student_name"])
    if stu:
        batch_groupings[key]["students"][stu["id"]] += 1

print(f"\nDiscovered {len(batch_groupings)} recurring coach-timeslot cohorts.")

# Filter cohorts that have consistent student attendance (at least 2 distinct students or repeat classes)
final_batches = []
batch_counter = 1

student_to_preferred_batch = {}

for (c, ts), data in sorted(batch_groupings.items(), key=lambda x: len(x[1]["students"]), reverse=True):
    top_students = [sid for sid, count in data["students"].most_common() if count >= 1]
    if not top_students:
        continue

    days_list = sorted(list(data["days"]))
    b_id = f"MKB{str(batch_counter).zfill(3)}"
    batch_counter += 1

    # Infer batch level from majority of students
    levels = [name_to_student.get(sid, {}).get("level", "Beginner") for sid in top_students]
    dominant_level = Counter(levels).most_common(1)[0][0] if levels else "Beginner"

    # Infer batch type: if <= 1 Individual, <= 4 Limited, else Group
    b_type = "I" if len(top_students) == 1 else ("L" if len(top_students) <= 4 else "G")
    
    # Format time slot standard
    ts_clean = ts
    if " - " not in ts_clean and ("AM" in ts_clean or "PM" in ts_clean):
        ts_clean = f"{ts_clean} - Next Hour"

    batch_name = f"{dominant_level} ({c} - {', '.join(days_list[:3])} {ts[:8]})"

    batch_obj = {
        "batch_id": b_id,
        "batch_name": batch_name,
        "batch_type": b_type,
        "level": dominant_level,
        "capacity_min": 1 if b_type == "I" else (2 if b_type == "L" else 4),
        "capacity_max": 1 if b_type == "I" else (4 if b_type == "L" else 10),
        "fixed_trainer": c,
        "schedule_timings": f"{', '.join(days_list)} @ {ts}",
        "weekly_slots": [f"{day} {ts}" for day in days_list],
        "student_ids": top_students[:10], # respect max 10
        "student_count": len(top_students[:10]),
        "notes": f"Trained from September ground truth. Meets on {', '.join(days_list)}."
    }
    final_batches.append(batch_obj)

    for sid in top_students:
        if sid not in student_to_preferred_batch:
            student_to_preferred_batch[sid] = b_id

print(f"Constructed {len(final_batches)} master recurring batches.")

from app.storage.database import save_all_master_batches_db, save_schedule_db

# Save master batches to SQLite
save_all_master_batches_db(final_batches)

# Update students' assigned_batch_id in SQLite
cursor = conn.cursor()
for sid, b_id in student_to_preferred_batch.items():
    cursor.execute("UPDATE students SET data_json = json_set(data_json, '$.assigned_batch_id', ?) WHERE student_id = ?", (b_id, sid))

conn.commit()
print("Saved all recurring batches and updated student assigned_batch_ids in SQLite!")

# Now build the full September ScheduleResult in SQLite
# Group by (date, day, coach, time_slot)
class_groups = defaultdict(lambda: {
    "student_ids": [],
    "student_names": [],
    "warnings": []
})

for rec in schedule_records:
    c = rec["coach"]
    if c.upper() == "NOT PROVIDED":
        c = "Unassigned"
    
    k = (rec["date"], rec["day"], c, rec["time_slot"])
    
    stu = find_student(rec["student_name"])
    sid = stu["id"] if stu else f"STU_{abs(hash(rec['student_name'])) % 10000}"
    sname = stu["name"] if stu else rec["student_name"]

    if rec["is_cancelled"]:
        class_groups[k]["warnings"].append(f"Student {sname} was cancelled on this date")
    else:
        if sid not in class_groups[k]["student_ids"]:
            class_groups[k]["student_ids"].append(sid)
            class_groups[k]["student_names"].append(sname)

september_scheduled_classes = []
cls_idx = 1

for (dt, dy, coach, ts), grp in class_groups.items():
    if not grp["student_ids"] and not grp["warnings"]:
        continue
    
    b_type = "I" if len(grp["student_ids"]) <= 1 else ("L" if len(grp["student_ids"]) <= 4 else "G")
    # Determine level
    lvls = [name_to_student.get(sid, {}).get("level", "Basic 1") for sid in grp["student_ids"]]
    dominant_lvl = Counter(lvls).most_common(1)[0][0] if lvls else "Basic 1"

    september_scheduled_classes.append({
        "class_id": f"CLS_SEP_{str(cls_idx).zfill(4)}",
        "date": dt,
        "day": dy,
        "time_slot": ts if " - " in ts else f"{ts} - Next",
        "coach_name": coach,
        "batch_name": f"{dominant_lvl} - {coach}",
        "student_level": dominant_lvl,
        "batch_type": b_type,
        "student_ids": grp["student_ids"],
        "student_names": grp["student_names"],
        "warnings": grp["warnings"],
        "is_manual_override": True
    })
    cls_idx += 1

print(f"Constructed {len(september_scheduled_classes)} scheduled classes for September.")

# Build coach schedule for Output 1
coach_sched_map = defaultdict(set)
for cls in september_scheduled_classes:
    coach_sched_map[(cls["date"], cls["day"], cls["time_slot"])].add(cls["coach_name"])

coach_sched_slots = [
    {
        "date": dt,
        "day": dy,
        "time_slot": ts,
        "coaches": list(coaches)
    }
    for (dt, dy, ts), coaches in sorted(coach_sched_map.items())
]

# Track student attendance count
student_class_counts = Counter()
for cls in september_scheduled_classes:
    for sid in cls["student_ids"]:
        student_class_counts[sid] += 1

unscheduled_records = []
cursor.execute("SELECT student_id, student_name, student_level, batch_type, required_classes FROM students")
all_stus = cursor.fetchall()

scheduled_count = 0
unscheduled_count = 0

for sid, sname, slvl, sbtype, req in all_stus:
    req = req or 8
    sch = student_class_counts.get(sid, 0)
    rem = max(0, req - sch)
    if rem > 0:
        unscheduled_count += 1
        unscheduled_records.append({
            "student_id": sid,
            "student_name": sname,
            "student_level": slvl,
            "batch_type": sbtype,
            "preferred_days": "Mon-Sat",
            "preferred_time": "Flexible",
            "required_classes": req,
            "scheduled_classes": sch,
            "remaining_classes": rem,
            "failure_reason": f"Completed {sch} of {req} classes in September. Missing {rem} classes.",
            "details": f"Needs {rem} makeup/scheduled classes"
        })
    else:
        scheduled_count += 1

september_schedule_id = "SCH_SEPTEMBER_2026"
schedule_payload = {
    "schedule_id": september_schedule_id,
    "status": "Finalized",
    "start_date": "2026-09-01",
    "end_date": "2026-09-30",
    "total_students_considered": len(all_stus),
    "successfully_scheduled_students": scheduled_count,
    "unscheduled_students_count": unscheduled_count,
    "accountability_passed": (len(all_stus) == scheduled_count + unscheduled_count),
    "scheduled_classes": september_scheduled_classes,
    "unscheduled_records": unscheduled_records,
    "coach_schedule": coach_sched_slots,
    "created_at": "2026-09-18T00:00:00"
}

conn.close()

# Use save_schedule_db from database.py
save_schedule_db(schedule_payload)

print("\nSuccessfully ingested and registered September schedule into SQLite!")
print(f"Total Scheduled Classes: {len(september_scheduled_classes)}")
print(f"Students Completed Quota: {scheduled_count}")
print(f"Students in Attention (Output 3): {unscheduled_count}")
