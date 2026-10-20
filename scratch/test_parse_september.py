import os, sys, re, json
from collections import defaultdict, Counter
from datetime import datetime

base_dir = r"c:\Users\Bathrinath\Downloads\Mighty_Knight_Scheduler_Final (1)\Mighty_Knight_Scheduler\backend\data"
raw_file = os.path.join(base_dir, "september_raw.txt")
ref_json = os.path.join(base_dir, "reference_oct_schedule.json")

with open(ref_json, "r", encoding="utf-8") as f:
    oct_ref = json.load(f)

name_to_stu = {}
for s in oct_ref.get("students_raw", []):
    name = s.get("student_name", "").strip()
    sid = s.get("student_id", "")
    lvl = s.get("student_level", "Basic 1")
    btype = s.get("batch_type", "G")
    req = s.get("required_classes", 8)
    clean = name.lower()
    name_to_stu[clean] = {"student_id": sid, "student_name": name, "student_level": lvl, "batch_type": btype, "required_classes": req}
    clean_no_dot = re.sub(r'[\.\s]+', '', clean)
    name_to_stu[clean_no_dot] = name_to_stu[clean]

with open(raw_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

current_date = None
current_coach = None
current_time = None
schedule_records = []

date_pattern = re.compile(r'📅\s*DATE:\s*(\d{2}-[A-Za-z]{3})')
coach_pattern = re.compile(r'♟️\s*([A-Za-z\s]+)')
time_pattern = re.compile(r'^(\d{1,2}:\d{2}\s*(?:AM|PM)|\d{1,2}\s*(?:AM|PM)|TIME NOT PROVIDED|\d{1,2}\s*&\s*\d{1,2}\.\d{2}[a-z]+)', re.IGNORECASE)

for raw_line in lines:
    line = raw_line.strip()
    if not line or line.startswith("━"):
        continue
    m_date = date_pattern.match(line)
    if m_date:
        d_str = m_date.group(1)
        day_num, month_str = d_str.split("-")
        current_date = f"2026-09-{day_num.zfill(2)}"
        current_coach = None
        current_time = None
        continue
    m_coach = coach_pattern.match(line)
    if m_coach:
        c_raw = m_coach.group(1).strip()
        current_coach = c_raw.upper()
        current_time = None
        continue
    m_time = time_pattern.match(line)
    if m_time:
        current_time = m_time.group(1).strip()
        continue
    if line.startswith("-"):
        stu_str = line[1:].strip()
        if "CANCELLED" in stu_str or "~~" in stu_str:
            continue
        clean_name = stu_str.replace("Extra", "").replace("Individual", "").replace("Trainer", "").strip()
        if not clean_name:
            continue
        if current_date and current_coach and current_time:
            d_obj = datetime.strptime(current_date, "%Y-%m-%d")
            schedule_records.append({
                "date": current_date,
                "day": d_obj.strftime("%A"),
                "coach": current_coach,
                "time_slot": current_time,
                "student_name": clean_name
            })

class_groups = defaultdict(lambda: {"student_ids": [], "student_names": []})
student_counts = Counter()
student_objects = {}

for r in schedule_records:
    clean = r["student_name"].lower()
    clean_no_dot = re.sub(r'[\.\s]+', '', clean)
    matched = name_to_stu.get(clean) or name_to_stu.get(clean_no_dot)
    sid = matched["student_id"] if matched else f"STU_{abs(hash(r['student_name'])) % 10000}"
    sname = matched["student_name"] if matched else r["student_name"]
    slvl = matched["student_level"] if matched else "Basic 1"
    sbtype = matched["batch_type"] if matched else "G"
    k = (r["date"], r["day"], r["coach"], r["time_slot"])
    if sid not in class_groups[k]["student_ids"]:
        class_groups[k]["student_ids"].append(sid)
        class_groups[k]["student_names"].append(sname)
    student_counts[sid] += 1
    if sid not in student_objects:
        student_objects[sid] = {
            "student_id": sid,
            "student_name": sname,
            "student_level": slvl,
            "batch_type": sbtype,
            "required_classes": matched["required_classes"] if matched else 8,
            "scheduled_classes": 0
        }

for sid, cnt in student_counts.items():
    if sid in student_objects:
        student_objects[sid]["scheduled_classes"] = cnt

print(f"Parsed {len(schedule_records)} student sessions.")
print(f"Constructed {len(class_groups)} distinct classes.")
print(f"Constructed {len(student_objects)} distinct students.")
