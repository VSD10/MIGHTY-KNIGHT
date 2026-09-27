import os
import csv
from collections import defaultdict, Counter
from typing import Dict, List, Any, Tuple
from app.constants.levels import normalize_batch_to_level

def parse_monthly_batch_dataset(csv_file_path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Parses the MKCA monthly batch attendance & schedule CSV file.
    Extracts:
    1. Batches (Group G, Limited L, Individual I):
       - Group & Limited batches group students under their batch code.
       - Individual (I) 1-on-1 students are each considered as their own batch with their fixed trainer.
    2. Students with their batch, rating, level, planned classes, and fixed trainer.
    3. Trainers found with their assigned batches and student counts.
    """
    if not os.path.exists(csv_file_path):
        return [], [], []

    with open(csv_file_path, mode="r", encoding="utf-8", errors="replace") as f:
        lines = [l for l in f if l.strip()]

    if len(lines) < 2:
        return [], [], []

    reader = csv.reader(lines)
    row0 = next(reader)  # Row 0 contains Day names (Tuesday, Wednesday, ...)
    header_row = None

    for r in reader:
        if r and len(r) > 0 and "student name" in r[0].strip().lower():
            header_row = r
            break

    if not header_row:
        return [], [], []

    # Identify date and day-of-week pairs
    days_cols = []
    for idx in range(7, len(header_row) - 1, 2):
        day_lbl = header_row[idx].strip()
        dow = row0[idx].strip() if idx < len(row0) else ""
        if day_lbl:
            days_cols.append((idx, day_lbl, dow))

    group_students_map = defaultdict(list)
    group_slots_map = defaultdict(lambda: defaultdict(Counter))
    individual_students_list = []
    all_students_list = []
    trainer_student_counts = defaultdict(int)

    for r in reader:
        if not r or len(r) < 5:
            continue
        student_name = r[0].strip().replace("\n", " ")
        student_id = r[1].strip()
        rating_str = r[2].strip()
        level_str = r[3].strip()
        batch_name = r[4].strip()
        planned_classes_str = r[5].strip() if len(r) > 5 else "12"
        comments_str = r[-3].strip() if len(r) >= 3 else ""

        if not student_name or student_name.lower() == "student name":
            continue
        if "trainer" in student_name.lower() and student_id.lower() == "na":
            continue

        try:
            planned_classes = int(float(planned_classes_str)) if planned_classes_str and planned_classes_str.lower() != "na" else 12
        except ValueError:
            planned_classes = 12

        # Extract trainer occurrences and time patterns
        trainer_counts = Counter()
        student_slots = []
        student_dow_slots = defaultdict(Counter)

        for col_idx, day_lbl, dow in days_cols:
            if col_idx < len(r):
                time_slot = r[col_idx].strip()
                coach_name = r[col_idx + 1].strip().title() if col_idx + 1 < len(r) else ""
                if time_slot:
                    if coach_name and coach_name.lower() != "na":
                        trainer_counts[coach_name] += 1
                        trainer_student_counts[coach_name] += 1
                    student_slots.append((dow, time_slot, coach_name))
                    student_dow_slots[dow][time_slot] += 1

        primary_trainer = trainer_counts.most_common(1)[0][0] if trainer_counts else "Unassigned"

        batch_type = batch_name[:1].upper() if batch_name and batch_name[:1].upper() in ["G", "L", "I"] else "G"
        
        # Derive official level from batch name per Section 3
        if batch_name:
            official_lvl, _, _ = normalize_batch_to_level(batch_name, student_id)
        else:
            official_lvl = "Beginner 1"

        student_dict = {
            "student_id": student_id or f"MKS_{abs(hash(student_name)) % 100000:05d}",
            "student_name": student_name,
            "student_level": official_lvl,
            "batch_type": batch_type,
            "batch_name": batch_name or "Unassigned Batch",
            "mkca_rating": rating_str if rating_str and rating_str.lower() != "na" else "-",
            "required_classes": planned_classes,
            "fixed_trainer": primary_trainer,
            "comments": comments_str,
            "region_timezone": "IST",
            "preferred_days": ", ".join(sorted(list(set(s[0] for s in student_slots if s[0])))) or "Flexible",
            "preferred_time": (student_slots[0][1] if student_slots else "06:00 PM"),
            "dow_slots": dict(student_dow_slots)
        }
        all_students_list.append(student_dict)

        if batch_type == "I":
            individual_students_list.append(student_dict)
        else:
            group_students_map[batch_name].append(student_dict)
            for dow, time_slot, coach_name in student_slots:
                group_slots_map[batch_name][dow][(time_slot, coach_name)] += 1

    batches_list = []

    # 1. Process Group (G) and Limited (L) Batches
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for b_name, s_list in group_students_map.items():
        if not b_name:
            continue
        first_s = s_list[0]
        batch_type = b_name[:1].upper() if b_name[:1].upper() in ["G", "L", "I"] else first_s["batch_type"]
        level = first_s["student_level"]

        # Primary Trainer for the batch
        batch_trainers = Counter(s["fixed_trainer"] for s in s_list if s["fixed_trainer"] != "Unassigned")
        primary_batch_trainer = batch_trainers.most_common(1)[0][0] if batch_trainers else first_s["fixed_trainer"]

        # Compile weekly timetable
        schedule_slots_summary = []
        dow_slots = group_slots_map[b_name]
        for dow in day_order:
            if dow in dow_slots:
                time_counts = Counter()
                for (t_slot, _c_name), count in dow_slots[dow].items():
                    if t_slot:
                        time_counts[t_slot] += count
                top_times = time_counts.most_common(2)
                if top_times:
                    time_strs = "/".join(t[0] for t in top_times)
                    schedule_slots_summary.append(f"{dow[:3]} {time_strs}")

        if not schedule_slots_summary:
            schedule_slots_summary = ["Flexible Schedule"]

        max_cap = 10 if batch_type == "G" else 4

        batches_list.append({
            "batch_id": b_name.strip(),
            "batch_name": b_name.strip(),
            "batch_code": b_name.strip(),
            "level": level,
            "batch_type": batch_type,
            "fixed_trainer": primary_batch_trainer,
            "schedule_timings": "; ".join(schedule_slots_summary),
            "weekly_slots": schedule_slots_summary,
            "max_capacity": max_cap,
            "student_count": len(s_list),
            "student_ids": [s["student_id"] for s in s_list],
            "students": [
                {
                    "student_id": s["student_id"],
                    "student_name": s["student_name"],
                    "student_level": s["student_level"],
                    "mkca_rating": s["mkca_rating"],
                    "fixed_trainer": s["fixed_trainer"],
                    "planned_classes": s["required_classes"]
                }
                for s in s_list
            ]
        })

    # 2. Process Individual (I) Batches: Each student is a 1-on-1 batch with their fixed trainer
    for s in individual_students_list:
        batch_code = s["batch_name"]
        batch_id = f"{batch_code} - {s['student_name']}"
        
        # Build weekly slots for this individual student
        sched_slots = []
        dow_slots = s.get("dow_slots", {})
        for dow in day_order:
            if dow in dow_slots and dow_slots[dow]:
                top_t = list(dow_slots[dow].keys())[0]
                sched_slots.append(f"{dow[:3]} {top_t}")
        if not sched_slots:
            sched_slots = [f"{s['preferred_days']} {s['preferred_time']}"]

        batches_list.append({
            "batch_id": batch_id,
            "batch_name": f"{batch_code} ({s['student_name']})",
            "batch_code": batch_code,
            "level": s["student_level"],
            "batch_type": "I",
            "fixed_trainer": s["fixed_trainer"],
            "schedule_timings": "; ".join(sched_slots),
            "weekly_slots": sched_slots,
            "max_capacity": 1,
            "student_count": 1,
            "student_ids": [s["student_id"]],
            "students": [
                {
                    "student_id": s["student_id"],
                    "student_name": s["student_name"],
                    "student_level": s["student_level"],
                    "mkca_rating": s["mkca_rating"],
                    "fixed_trainer": s["fixed_trainer"],
                    "planned_classes": s["required_classes"]
                }
            ]
        })

    # Sort batches nicely: Group G first, Limited L second, Individual I third
    batches_list.sort(key=lambda b: ({"G": 1, "L": 2, "I": 3}.get(b["batch_type"], 4), b["level"], b["batch_name"]))

    trainers_list = [{"coach_name": t, "student_count": c} for t, c in sorted(trainer_student_counts.items(), key=lambda x: -x[1])]
    return batches_list, all_students_list, trainers_list
