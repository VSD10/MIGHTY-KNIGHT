import os
import sys
import re
import csv
import json
import datetime
import openpyxl
from collections import defaultdict
from typing import Dict, Any, List, Tuple, Set

# Ensure backend directory is in python path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from app.engine.reference_scheduler import generate_reference_schedule

def normalize_time_str(time_val: Any) -> str:
    """
    Normalizes diverse time representations (datetime.time, '07:00 PM', '7:00 PM', '07:00 PM - 08:00 PM')
    into a canonical format: '07:00 PM'.
    """
    if time_val is None:
        return ""
    if isinstance(time_val, datetime.time):
        return time_val.strftime("%I:%M %p")
    
    s = str(time_val).strip()
    match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(AM|PM)', s, re.IGNORECASE)
    if match:
        hr = int(match.group(1))
        mn = int(match.group(2)) if match.group(2) else 0
        ampm = match.group(3).upper()
        return f"{hr:02d}:{mn:02d} {ampm}"
    return s

def normalize_name(name_val: Any) -> str:
    if not name_val:
        return ""
    return str(name_val).strip()

def run_schedule_comparison():
    print("=" * 60)
    print("MIGHTY KNIGHT — ISOLATED SCHEDULING VALIDATION")
    print("REFERENCE EXCEL vs. CURRENT SCHEDULING ENGINE")
    print("=" * 60)

    excel_path = os.path.join(os.path.dirname(BACKEND_DIR), "sample_data", "Oct'26 Schedule_FRESH-1.xlsx")
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Reference Excel not found at: {excel_path}")

    # ==================================================
    # STEP 1 — READ THE EXCEL (SOURCE OF TRUTH)
    # ==================================================
    print("\n[Step 1] Parsing Reference Excel: Oct'26 Schedule_FRESH-1.xlsx...")
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb.active

    # Parse date columns from Row 3 and day names from Row 1
    # Columns 8+ in pairs: (Time Col, Trainer Col)
    date_columns = {} # col_idx -> (date_str, day_name, trainer_col_idx)
    for col in range(8, ws.max_column, 2):
        d_val = ws.cell(3, col).value
        day_val = ws.cell(1, col).value
        if d_val:
            d_obj = d_val.date() if isinstance(d_val, datetime.datetime) else d_val
            d_str = d_obj.strftime("%Y-%m-%d")
            day_name = str(day_val).strip() if day_val else d_obj.strftime("%A")
            date_columns[col] = (d_str, day_name, col + 1)

    ref_student_records = []
    ref_by_student_date = {} # (student_id, date) -> record
    ref_weekly_patterns = defaultdict(lambda: defaultdict(list)) # student_id -> weekday -> list of records
    ref_group_classes = set() # (date, canonical_time, trainer)

    for r in range(4, ws.max_row + 1):
        name_val = ws.cell(r, 1).value
        if not name_val or not str(name_val).strip():
            continue

        student_name = normalize_name(name_val)
        student_id = str(ws.cell(r, 2).value or f"MKS{r:05d}").strip()
        level = normalize_name(ws.cell(r, 4).value or "Basic")
        batch = normalize_name(ws.cell(r, 5).value or "G Basic1")

        for col, (d_str, day_name, tr_col) in date_columns.items():
            t_val = ws.cell(r, col).value
            tr_val = ws.cell(r, tr_col).value
            if t_val is not None and tr_val is not None:
                canonical_time = normalize_time_str(t_val)
                trainer_name = normalize_name(tr_val)
                if not canonical_time or not trainer_name:
                    continue

                rec = {
                    "student_id": student_id,
                    "student_name": student_name,
                    "weekday": day_name,
                    "date": d_str,
                    "time": canonical_time,
                    "trainer": trainer_name,
                    "batch": batch,
                    "level": level
                }
                ref_student_records.append(rec)
                ref_by_student_date[(student_id, d_str)] = rec
                ref_weekly_patterns[student_id][day_name].append(rec)
                ref_group_classes.add((d_str, canonical_time, trainer_name))

    print(f"  Parsed {len(ref_student_records)} student-class instances from Excel.")
    print(f"  Parsed {len(ref_group_classes)} unique group class sessions from Excel.")

    # ==================================================
    # STEP 2 — BUILD EXPECTED WEEKLY PATTERN
    # ==================================================
    print("\n[Step 2] Building Expected Recurring Weekly Pattern...")
    expected_patterns = {} # student_id -> weekday -> (canonical_time, trainer, batch, level)
    for sid, day_map in ref_weekly_patterns.items():
        expected_patterns[sid] = {}
        for wday, recs in day_map.items():
            # Most common or fixed pattern for that weekday
            first = recs[0]
            expected_patterns[sid][wday] = {
                "time": first["time"],
                "trainer": first["trainer"],
                "batch": first["batch"],
                "level": first["level"]
            }
    print(f"  Compiled recurring weekly patterns for {len(expected_patterns)} students.")

    # ==================================================
    # STEP 3 — GENERATE TEST MONTH (IN-MEMORY / ISOLATED)
    # ==================================================
    print("\n[Step 3] Generating Test Month (October 2026) via Scheduling Engine in-memory...")
    # Pure in-memory generation; NO database writes
    test_start = datetime.date(2026, 10, 1)
    test_end = datetime.date(2026, 10, 31)
    generated_result = generate_reference_schedule(
        start_date=test_start,
        end_date=test_end,
        schedule_id="TEST_ISOLATED_OCT26"
    )

    # ==================================================
    # STEP 4 — NORMALIZE ACTUAL SCHEDULE
    # ==================================================
    print("\n[Step 4] Normalizing Generated Schedule...")
    gen_student_records = []
    gen_by_student_date = {} # (student_id, date) -> record
    gen_weekly_patterns = defaultdict(lambda: defaultdict(list))
    gen_group_classes = set()

    for cls in generated_result.scheduled_classes:
        d_str = cls.date
        day_name = cls.day
        canonical_time = normalize_time_str(cls.time_slot)
        trainer_name = normalize_name(cls.coach_name)
        batch = normalize_name(cls.batch_name)
        level = normalize_name(cls.student_level)

        gen_group_classes.add((d_str, canonical_time, trainer_name))

        for sid, sname in zip(cls.student_ids, cls.student_names):
            s_rec = {
                "student_id": sid,
                "student_name": sname,
                "weekday": day_name,
                "date": d_str,
                "time": canonical_time,
                "trainer": trainer_name,
                "batch": batch,
                "level": level
            }
            gen_student_records.append(s_rec)
            gen_by_student_date[(sid, d_str)] = s_rec
            gen_weekly_patterns[sid][day_name].append(s_rec)

    print(f"  Normalized {len(gen_student_records)} generated student-class instances.")
    print(f"  Normalized {len(gen_group_classes)} generated group class sessions.")

    # ==================================================
    # STEP 5 & 6 — COMPARE & CATEGORIZE
    # ==================================================
    print("\n[Step 5 & 6] Comparing Reference vs Generated...")

    # We evaluate comparison across all (student_id, date) pairs
    all_student_dates = set(ref_by_student_date.keys()).union(set(gen_by_student_date.keys()))

    exact_matches = []
    missing_classes = []
    extra_classes = []
    wrong_trainers = []
    wrong_times = []
    wrong_batches = []
    wrong_levels = []
    wrong_days = []

    all_comparison_rows = []

    for sid, d_str in sorted(all_student_dates):
        in_ref = (sid, d_str) in ref_by_student_date
        in_gen = (sid, d_str) in gen_by_student_date

        if in_ref and not in_gen:
            r = ref_by_student_date[(sid, d_str)]
            diff_item = {
                "category": "MISSING CLASS",
                "student_id": sid,
                "student_name": r["student_name"],
                "date": d_str,
                "weekday": r["weekday"],
                "ref_time": r["time"],
                "gen_time": "-",
                "ref_trainer": r["trainer"],
                "gen_trainer": "-",
                "ref_batch": r["batch"],
                "gen_batch": "-",
                "ref_level": r["level"],
                "gen_level": "-",
                "description": f"Class scheduled in Excel on {d_str} ({r['time']} with {r['trainer']}) is missing in generated schedule."
            }
            missing_classes.append(diff_item)
            all_comparison_rows.append(diff_item)

        elif in_gen and not in_ref:
            g = gen_by_student_date[(sid, d_str)]
            diff_item = {
                "category": "EXTRA CLASS",
                "student_id": sid,
                "student_name": g["student_name"],
                "date": d_str,
                "weekday": g["weekday"],
                "ref_time": "-",
                "gen_time": g["time"],
                "ref_trainer": "-",
                "gen_trainer": g["trainer"],
                "ref_batch": "-",
                "gen_batch": g["batch"],
                "ref_level": "-",
                "gen_level": g["level"],
                "description": f"Class generated on {d_str} ({g['time']} with {g['trainer']}) does not exist in reference Excel."
            }
            extra_classes.append(diff_item)
            all_comparison_rows.append(diff_item)

        else:
            # Both present on this date
            r = ref_by_student_date[(sid, d_str)]
            g = gen_by_student_date[(sid, d_str)]

            time_match = (r["time"] == g["time"])
            trainer_match = (r["trainer"].lower() == g["trainer"].lower())
            batch_match = (r["batch"].lower() == g["batch"].lower())
            level_match = (r["level"].lower() == g["level"].lower())
            day_match = (r["weekday"].lower() == g["weekday"].lower())

            diff_categories = []
            if not day_match:
                diff_categories.append("WRONG DAY")
                wrong_days.append({
                    "student_id": sid, "date": d_str, "ref": r["weekday"], "gen": g["weekday"]
                })
            if not time_match:
                diff_categories.append("WRONG TIME")
                wrong_times.append({
                    "student_id": sid, "date": d_str, "ref": r["time"], "gen": g["time"]
                })
            if not trainer_match:
                diff_categories.append("WRONG TRAINER")
                wrong_trainers.append({
                    "student_id": sid, "date": d_str, "ref": r["trainer"], "gen": g["trainer"]
                })
            if not batch_match:
                diff_categories.append("WRONG BATCH")
                wrong_batches.append({
                    "student_id": sid, "date": d_str, "ref": r["batch"], "gen": g["batch"]
                })
            if not level_match:
                diff_categories.append("WRONG LEVEL")
                wrong_levels.append({
                    "student_id": sid, "date": d_str, "ref": r["level"], "gen": g["level"]
                })

            if not diff_categories:
                match_item = {
                    "category": "EXACT MATCH",
                    "student_id": sid,
                    "student_name": r["student_name"],
                    "date": d_str,
                    "weekday": r["weekday"],
                    "ref_time": r["time"],
                    "gen_time": g["time"],
                    "ref_trainer": r["trainer"],
                    "gen_trainer": g["trainer"],
                    "ref_batch": r["batch"],
                    "gen_batch": g["batch"],
                    "ref_level": r["level"],
                    "gen_level": g["level"],
                    "description": "All fields (student, date, weekday, time, trainer, batch, level) match exactly."
                }
                exact_matches.append(match_item)
                all_comparison_rows.append(match_item)
            else:
                cat_label = ", ".join(diff_categories)
                diff_item = {
                    "category": cat_label,
                    "student_id": sid,
                    "student_name": r["student_name"],
                    "date": d_str,
                    "weekday": r["weekday"],
                    "ref_time": r["time"],
                    "gen_time": g["time"],
                    "ref_trainer": r["trainer"],
                    "gen_trainer": g["trainer"],
                    "ref_batch": r["batch"],
                    "gen_batch": g["batch"],
                    "ref_level": r["level"],
                    "gen_level": g["level"],
                    "description": f"Field mismatches: {cat_label}"
                }
                all_comparison_rows.append(diff_item)

    # Weekly Pattern Comparison
    pattern_matches = 0
    pattern_total = 0
    for sid, day_map in expected_patterns.items():
        for wday, exp in day_map.items():
            pattern_total += 1
            gen_recs = gen_weekly_patterns.get(sid, {}).get(wday, [])
            if gen_recs:
                first_g = gen_recs[0]
                if (first_g["time"] == exp["time"] and 
                    first_g["trainer"].lower() == exp["trainer"].lower()):
                    pattern_matches += 1

    # ==================================================
    # STEP 7 — SUMMARY & ACCURACY METRICS
    # ==================================================
    total_ref = len(ref_student_records)
    total_gen = len(gen_student_records)
    total_exact = len(exact_matches)
    total_missing = len(missing_classes)
    total_extra = len(extra_classes)
    total_wrong_trainer = len(wrong_trainers)
    total_wrong_time = len(wrong_times)
    total_wrong_day = len(wrong_days)
    total_wrong_batch = len(wrong_batches)
    total_wrong_level = len(wrong_levels)

    exact_match_pct = (total_exact / total_ref * 100.0) if total_ref > 0 else 0.0
    student_pattern_match_pct = (pattern_matches / pattern_total * 100.0) if pattern_total > 0 else 0.0
    trainer_match_pct = ((total_ref - total_missing - total_wrong_trainer) / total_ref * 100.0) if total_ref > 0 else 0.0
    time_match_pct = ((total_ref - total_missing - total_wrong_time) / total_ref * 100.0) if total_ref > 0 else 0.0
    batch_match_pct = ((total_ref - total_missing - total_wrong_batch) / total_ref * 100.0) if total_ref > 0 else 0.0
    level_match_pct = ((total_ref - total_missing - total_wrong_level) / total_ref * 100.0) if total_ref > 0 else 0.0

    group_classes_ref_count = len(ref_group_classes)
    group_classes_gen_count = len(gen_group_classes)
    group_classes_matched = len(ref_group_classes.intersection(gen_group_classes))

    # ==================================================
    # STEP 8 — SAVE THE REPORT (JSON & CSV)
    # ==================================================
    report_json_path = os.path.join(BACKEND_DIR, "tests", "schedule_comparison_report.json")
    report_csv_path = os.path.join(BACKEND_DIR, "tests", "schedule_comparison_report.csv")

    summary_dict = {
        "validation_timestamp": datetime.datetime.now().isoformat(),
        "reference_excel_path": excel_path,
        "metrics": {
            "reference_student_classes": total_ref,
            "generated_student_classes": total_gen,
            "reference_group_classes": group_classes_ref_count,
            "generated_group_classes": group_classes_gen_count,
            "group_classes_matched": group_classes_matched,
            "exact_matches": total_exact,
            "missing": total_missing,
            "extra": total_extra,
            "wrong_trainer": total_wrong_trainer,
            "wrong_time": total_wrong_time,
            "wrong_day": total_wrong_day,
            "wrong_batch": total_wrong_batch,
            "wrong_level": total_wrong_level
        },
        "percentages": {
            "exact_match_pct": round(exact_match_pct, 2),
            "student_pattern_match_pct": round(student_pattern_match_pct, 2),
            "trainer_match_pct": round(trainer_match_pct, 2),
            "time_match_pct": round(time_match_pct, 2),
            "batch_match_pct": round(batch_match_pct, 2),
            "level_match_pct": round(level_match_pct, 2)
        },
        "mismatches": [row for row in all_comparison_rows if row["category"] != "EXACT MATCH"]
    }

    with open(report_json_path, "w", encoding="utf-8") as jf:
        json.dump(summary_dict, jf, indent=2)

    with open(report_csv_path, "w", newline="", encoding="utf-8") as cf:
        writer = csv.DictWriter(cf, fieldnames=[
            "category", "student_id", "student_name", "date", "weekday",
            "ref_time", "gen_time", "ref_trainer", "gen_trainer",
            "ref_batch", "gen_batch", "ref_level", "gen_level", "description"
        ])
        writer.writeheader()
        for row in all_comparison_rows:
            writer.writerow(row)

    # ==================================================
    # TERMINAL DISPLAY
    # ==================================================
    print("\n" + "=" * 45)
    print("SCHEDULE VALIDATION")
    print("=========================================")
    print(f"Reference classes: {group_classes_ref_count}")
    print(f"Generated classes: {group_classes_gen_count}")
    print(f"Student assignments: {total_ref}")
    print("─────────────────────────────────────────")
    print(f"Exact matches: {total_exact}")
    print(f"Missing:       {total_missing}")
    print(f"Extra:         {total_extra}")
    print(f"Wrong trainer: {total_wrong_trainer}")
    print(f"Wrong time:    {total_wrong_time}")
    print(f"Wrong day:     {total_wrong_day}")
    print(f"Wrong batch:   {total_wrong_batch}")
    print(f"Wrong level:   {total_wrong_level}")
    print("─────────────────────────────────────────")
    print(f"Match rate:    {exact_match_pct:.1f}%")
    print(f"Pattern rate:  {student_pattern_match_pct:.1f}%")
    print(f"Trainer match: {trainer_match_pct:.1f}%")
    print(f"Time match:    {time_match_pct:.1f}%")
    print("=========================================\n")

    mismatches = summary_dict["mismatches"]
    if not mismatches:
        print("PERFECT MATCH: Zero mismatches detected across all 1,406 student-session assignments!")
    else:
        print(f"First {min(50, len(mismatches))} Mismatches:")
        print("-" * 100)
        for i, m in enumerate(mismatches[:50], 1):
            print(f"{i:2d}. [{m['category']}] {m['student_name']} ({m['student_id']}) on {m['date']} ({m['weekday']}):")
            print(f"    Expected (Ref) : Time={m['ref_time']}, Trainer={m['ref_trainer']}, Batch={m['ref_batch']}, Level={m['ref_level']}")
            print(f"    Actual (Gen)   : Time={m['gen_time']}, Trainer={m['gen_trainer']}, Batch={m['gen_batch']}, Level={m['gen_level']}")
            print(f"    Detail         : {m['description']}")
            print("-" * 100)

    print(f"\nFull detailed reports successfully written to:")
    print(f"  - JSON: {report_json_path}")
    print(f"  - CSV:  {report_csv_path}")

    return summary_dict

if __name__ == "__main__":
    run_schedule_comparison()
