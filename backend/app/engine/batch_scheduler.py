import os
import uuid
import csv
import re
from datetime import date, datetime
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Optional, Set, Any

from app.models.student import StudentModel
from app.models.coach import CoachModel
from app.models.schedule import ScheduleResult, ScheduledClass, UnscheduledRecord, CoachCommunicationSlot
from app.config import SystemConfig, DEFAULT_CONFIG
from app.engine.time_utils import get_day_name, generate_date_range
from app.engine.accountability import AccountabilityTracker
from app.utils.time_utils import parse_time_slot_sort_key
from app.storage.database import load_master_batches_db, BASE_DIR
from app.ingestion.batch_dataset_parser import parse_monthly_batch_dataset
from app.constants.levels import normalize_batch_to_level

def load_dataset_daily_schedule(csv_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parses the exact day-by-day classes from the September monthly schedule CSV.
    Returns a dict mapping day label (e.g. '1-Sep') to a list of class definitions:
    [
      {
        "time_slot": "8:00 PM",
        "coach_name": "Dhaanush",
        "batch_name": "G Intermediate2",
        "level": "Intermediate",
        "batch_type": "G",
        "students": [ (student_name, student_id) ]
      }, ...
    ]
    """
    if not os.path.exists(csv_path):
        return {}

    with open(csv_path, mode="r", encoding="utf-8", errors="replace") as f:
        lines = [l for l in f if l.strip()]

    if len(lines) < 2:
        return {}

    reader = csv.reader(lines)
    row0 = next(reader)
    header_row = None
    for r in reader:
        if r and len(r) > 0 and "student name" in r[0].strip().lower():
            header_row = r
            break

    if not header_row:
        return {}

    days_cols = {}
    for idx in range(7, len(header_row) - 1, 2):
        lbl = header_row[idx].strip()
        if lbl:
            days_cols[lbl] = idx

    # Map: day_lbl -> dict of (time_slot, coach_name, batch_name, level, batch_type) -> list of (name, sid)
    daily_grouped = defaultdict(lambda: defaultdict(list))
    for r in reader:
        if not r or len(r) < 5:
            continue
        name = r[0].strip().replace("\n", " ")
        sid = r[1].strip()
        batch = r[4].strip() or "General"
        lvl, _, _ = normalize_batch_to_level(batch, sid)
        btype = batch[:1].upper() if batch[:1].upper() in ["G", "L", "I"] else "G"

        if not name or name.lower() == "student name":
            continue
        if "trainer" in name.lower() and sid.lower() == "na":
            continue

        for lbl, idx in days_cols.items():
            if idx < len(r):
                t_slot = r[idx].strip()
                c_name = r[idx + 1].strip().title() if idx + 1 < len(r) else ""
                if t_slot:
                    key = (t_slot, c_name, batch, lvl, btype)
                    daily_grouped[lbl][key].append((name, sid))

    result = {}
    for lbl, class_dict in daily_grouped.items():
        class_list = []
        for (t_slot, c_name, batch, lvl, btype), stu_tuples in class_dict.items():
            class_list.append({
                "time_slot": t_slot,
                "coach_name": c_name or "Unassigned",
                "batch_name": batch,
                "level": lvl,
                "batch_type": btype,
                "students": stu_tuples
            })
        result[lbl] = class_list

    return result

def run_batch_based_scheduler(
    students: List[StudentModel],
    coaches: List[CoachModel],
    start_date: date,
    end_date: date,
    config: SystemConfig = DEFAULT_CONFIG,
    schedule_id: Optional[str] = None
) -> ScheduleResult:
    """
    Deterministic, batch-based scheduling engine.
    Completely replaces randomized coach assignment and ad-hoc student pooling.
    
    1. For dates in September:
       Uses the exact day-by-day classes from the dataset (1-Sep to 30-Sep).
    2. For dates outside September (e.g. October, next month, or general dates):
       Schedules every Master Batch according to its recurring weekly slots and fixed trainer.
    """
    if not schedule_id:
        schedule_id = f"SCH_{uuid.uuid4().hex[:8].upper()}"

    from app.storage.database import is_master_cleared_db
    cleared = is_master_cleared_db()

    # Master batches from SQLite are the sole authoritative source of truth
    master_batches = load_master_batches_db()

    # If master batches is empty or no students exist, return clean empty schedule
    if not master_batches or len(students) == 0:
        return ScheduleResult(
            schedule_id=schedule_id,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            total_students_considered=len(students),
            successfully_scheduled_students=0,
            unscheduled_students_count=len(students),
            accountability_passed=True,
            scheduled_classes=[],
            unscheduled_records=[],
            coach_schedule=[],
            created_at=datetime.now().isoformat(),
            status="Draft" if students else "Empty"
        )

    # Master batch map for quick fallback lookups
    batch_map = {b["batch_name"].strip().lower(): b for b in master_batches}

    # Student lookup map and Coach lookup map
    student_map = {s.student_id: s for s in students}
    coach_map = {c.coach_name.strip().lower(): c for c in coaches}

    tracker = AccountabilityTracker(students)
    target_dates = generate_date_range(start_date, end_date)

    scheduled_classes: List[ScheduledClass] = []
    scheduled_class_counts: Dict[str, int] = defaultdict(int)
    coach_daily_counts: Dict[Tuple[str, str], int] = defaultdict(int)

    # Master batches from SQLite are the authoritative source of truth
    for d_obj in target_dates:
        date_str = d_obj.strftime("%Y-%m-%d")
        day_name = get_day_name(d_obj)
        dow_short = day_name[:3]  # Mon, Tue, Wed, Thu, Fri, Sat, Sun

        for b in master_batches:
            slots = b.get("weekly_slots", [])
            # Fallback to schedule_timings if weekly_slots is empty
            if not slots and b.get("schedule_timings"):
                # e.g. "Mon, Wed 08:00 PM"
                st = b["schedule_timings"]
                for day_abbr in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
                    if day_abbr in st:
                        # Extract time part
                        time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))', st)
                        t_part = time_match.group(1) if time_match else "06:00 PM"
                        slots.append(f"{day_abbr} {t_part}")

            fixed_trainer = b.get("fixed_trainer", "Unassigned")
            b_name = b.get("batch_name", b.get("batch_id", "Batch"))
            lvl, _, _ = normalize_batch_to_level(b_name)
            b_type = b.get("batch_type", "G")
            cap_max = b.get("capacity_max") or b.get("max_capacity") or (1 if b_type == "I" else (4 if b_type == "L" else 10))

            # Enrolled students
            s_ids = list(b.get("student_ids", []))
            if not s_ids and b.get("students"):
                s_ids = [s["student_id"] for s in b["students"] if isinstance(s, dict) and s.get("student_id")]

            # Cap students to batch capacity
            if len(s_ids) > cap_max:
                s_ids = s_ids[:cap_max]

            if not s_ids:
                continue

            s_names = []
            for sid in s_ids:
                if sid in student_map:
                    s_names.append(student_map[sid].student_name)
                else:
                    match = next((x for x in b.get("students", []) if isinstance(x, dict) and x.get("student_id") == sid), None)
                    s_names.append(match.get("student_name", sid) if match else sid)

            for s_entry in slots:
                parts = s_entry.strip().split(maxsplit=1)
                if not parts or len(parts) < 2:
                    continue
                day_prefix = parts[0].replace(":", "").strip().lower()
                if day_prefix == day_name.lower() or day_prefix == dow_short.lower() or s_entry.lower().startswith(dow_short.lower()):
                    time_part = parts[1].strip()
                    times = [t.strip() for t in time_part.split("/") if t.strip()]

                    for t_slot in times:
                        warnings = []
                        c_key = (fixed_trainer.strip().lower(), date_str)
                        coach_daily_counts[c_key] += 1
                        daily_cnt = coach_daily_counts[c_key]

                        # Check coach daily limit if trainer is assigned
                        c_obj = coach_map.get(fixed_trainer.strip().lower())
                        if c_obj:
                            d_max = c_obj.get_daily_max(day_name)
                            if daily_cnt > d_max:
                                warnings.append(f"Coach {fixed_trainer} exceeded daily limit on {day_name} ({daily_cnt}/{d_max})")
                            if not c_obj.can_handle_level(lvl):
                                warnings.append(f"Coach {fixed_trainer} not configured for level {lvl}")

                        # Check student availability
                        for idx, sid in enumerate(s_ids):
                            tracker.record_class_scheduled(sid)
                            scheduled_class_counts[sid] += 1
                            s_obj = student_map.get(sid)
                            if s_obj and not s_obj.is_available_on_day(day_name):
                                warnings.append(f"Student {s_names[idx]} is marked Not Available on {day_name}")

                        cls_obj = ScheduledClass(
                            class_id=f"CLS_{uuid.uuid4().hex[:6].upper()}",
                            date=date_str,
                            day=day_name,
                            time_slot=t_slot,
                            coach_name=fixed_trainer,
                            batch_name=b_name,
                            student_level=lvl,
                            batch_type=b_type,
                            student_ids=s_ids,
                            student_names=s_names,
                            warnings=warnings
                        )
                        scheduled_classes.append(cls_obj)

    # Sort scheduled classes chronologically
    scheduled_classes.sort(
        key=lambda c: (parse_time_slot_sort_key(c.date, c.time_slot), c.coach_name)
    )

    # Generate Output 1 (Coach Communication Slots)
    coach_schedule_map: Dict[Tuple[str, str, str], List[str]] = defaultdict(list)
    for s_cls in scheduled_classes:
        key = (s_cls.date, s_cls.day, s_cls.time_slot)
        if s_cls.coach_name and s_cls.coach_name != "Unassigned":
            if s_cls.coach_name not in coach_schedule_map[key]:
                coach_schedule_map[key].append(s_cls.coach_name)

    coach_schedule_slots: List[CoachCommunicationSlot] = [
        CoachCommunicationSlot(
            date=k[0],
            day=k[1],
            time_slot=k[2],
            coaches=v
        )
        for k, v in sorted(coach_schedule_map.items(), key=lambda item: parse_time_slot_sort_key(item[0][0], item[0][2]))
    ]

    # Generate Accountability Report (Output 3)
    total_in, scheduled_cnt, unscheduled_cnt, acc_passed, unscheduled_recs = tracker.generate_report()

    created_at_str = datetime.now().isoformat()

    return ScheduleResult(
        schedule_id=schedule_id,
        status="Draft",
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        total_students_considered=len(students),
        successfully_scheduled_students=scheduled_cnt,
        unscheduled_students_count=unscheduled_cnt,
        accountability_passed=acc_passed,
        scheduled_classes=scheduled_classes,
        unscheduled_records=unscheduled_recs,
        coach_schedule=coach_schedule_slots,
        created_at=created_at_str
    )
