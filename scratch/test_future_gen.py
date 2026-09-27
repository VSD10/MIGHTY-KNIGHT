import openpyxl
import os
import datetime
import calendar
from collections import defaultdict

def test_future_generation(year=2026, month=11):
    path = os.path.join(os.path.dirname(__file__), '..', 'sample_data', "Oct'26 Schedule_FRESH-1.xlsx")
    wb = openpyxl.load_workbook(os.path.abspath(path), data_only=True)
    ws = wb.active
    
    date_cols = {}
    for col in range(8, ws.max_column, 2):
        d_val = ws.cell(3, col).value
        day_val = ws.cell(1, col).value
        if d_val:
            d_obj = d_val.date() if isinstance(d_val, datetime.datetime) else d_val
            date_cols[col] = (d_obj, str(day_val).strip() if day_val else d_obj.strftime("%A"), col + 1)
            
    # Extract recurring weekly patterns per student
    students = []
    # weekday_name -> list of {student_id, student_name, time, trainer, batch, level, batch_type}
    weekday_templates = defaultdict(list)
    
    for r in range(4, ws.max_row + 1):
        name = ws.cell(r, 1).value
        if not name or not str(name).strip():
            continue
        stud_id = ws.cell(r, 2).value or f"MKS{r:05d}"
        level = ws.cell(r, 4).value or "Basic"
        batch = ws.cell(r, 5).value or "G Basic1"
        planned = ws.cell(r, 6).value
        
        batch_str = str(batch).strip()
        b_type = "G"
        if batch_str.startswith("L ") or batch_str.startswith("L-") or "Limited" in batch_str:
            b_type = "L"
        elif batch_str.startswith("I ") or batch_str.startswith("I-") or "Individual" in batch_str:
            b_type = "I"
            
        student_obj = {
            "student_id": str(stud_id).strip(),
            "student_name": str(name).strip(),
            "student_level": str(level).strip(),
            "batch_type": b_type,
            "batch_name": batch_str,
            "planned_classes": int(planned) if (planned is not None and str(planned).strip().isdigit()) else 12,
            "recurring_slots": {}
        }
        
        # Read October classes
        for col, (d_obj, day_name, tr_col) in date_cols.items():
            t_val = ws.cell(r, col).value
            tr_val = ws.cell(r, tr_col).value
            if t_val is not None:
                if isinstance(t_val, datetime.time):
                    t_str = t_val.strftime("%I:%M %p").lstrip('0')
                else:
                    t_str = str(t_val).strip()
                tr_str = str(tr_val).strip() if tr_val else "Unassigned"
                
                if day_name not in student_obj["recurring_slots"]:
                    student_obj["recurring_slots"][day_name] = (t_str, tr_str)
                    weekday_templates[day_name].append({
                        "student": student_obj,
                        "time_slot": t_str,
                        "coach_name": tr_str,
                        "batch_name": batch_str,
                        "student_level": str(level).strip(),
                        "batch_type": b_type
                    })
        students.append(student_obj)
        
    print(f"Loaded {len(students)} students from reference.")
    
    # Generate for target month (e.g. November 2026)
    _, num_days = calendar.monthrange(year, month)
    target_dates = [datetime.date(year, month, d) for d in range(1, num_days + 1)]
    print(f"Target Month: {year}-{month:02d} ({len(target_dates)} days: {target_dates[0]} to {target_dates[-1]})")
    
    classes_by_date_slot = defaultdict(lambda: {
        "student_ids": [],
        "student_names": [],
        "batch_names": set(),
        "levels": set(),
        "batch_types": set()
    })
    
    total_student_assignments = 0
    
    for d_obj in target_dates:
        day_name = d_obj.strftime("%A")
        date_str = d_obj.strftime("%Y-%m-%d")
        
        # Look up all students with recurring slot on this weekday
        for entry in weekday_templates[day_name]:
            s = entry["student"]
            t_str = entry["time_slot"]
            tr_str = entry["coach_name"]
            
            key = (date_str, day_name, t_str, tr_str)
            classes_by_date_slot[key]["student_ids"].append(s["student_id"])
            classes_by_date_slot[key]["student_names"].append(s["student_name"])
            classes_by_date_slot[key]["batch_names"].add(entry["batch_name"])
            classes_by_date_slot[key]["levels"].add(entry["student_level"])
            classes_by_date_slot[key]["batch_types"].add(entry["batch_type"])
            total_student_assignments += 1
            
    print(f"Generated {len(classes_by_date_slot)} classes for November 2026.")
    print(f"Total student class assignments in November: {total_student_assignments}")
    
    # Print sample day
    nov_first_mon = next(d for d in target_dates if d.strftime("%A") == "Monday")
    mon_str = nov_first_mon.strftime("%Y-%m-%d")
    mon_classes = [k for k in classes_by_date_slot.keys() if k[0] == mon_str]
    print(f"\nMonday {mon_str} has {len(mon_classes)} classes:")
    for k in sorted(mon_classes, key=lambda x: (x[2], x[3]))[:5]:
        c_info = classes_by_date_slot[k]
        print(f"  {k[2]} | Coach: {k[3]} | Students ({len(c_info['student_ids'])}): {', '.join(c_info['student_names'])}")

if __name__ == "__main__":
    test_future_generation(2026, 11)
