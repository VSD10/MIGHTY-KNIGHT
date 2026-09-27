import openpyxl
import os
import datetime
from collections import defaultdict

def test_parse():
    path = os.path.join(os.path.dirname(__file__), '..', 'sample_data', "Oct'26 Schedule_FRESH-1.xlsx")
    wb = openpyxl.load_workbook(os.path.abspath(path), data_only=True)
    ws = wb.active
    
    # 1. Identify date columns from Row 3 (dates) and Row 1 (weekdays)
    date_cols = {} # col_idx -> (date_obj, day_name, trainer_col_idx)
    for col in range(8, ws.max_column, 2):
        d_val = ws.cell(3, col).value
        day_val = ws.cell(1, col).value
        if d_val:
            d_obj = d_val.date() if isinstance(d_val, datetime.datetime) else d_val
            date_cols[col] = (d_obj, str(day_val).strip() if day_val else d_obj.strftime("%A"), col + 1)
            
    print(f"Total date columns identified: {len(date_cols)}")
    first_date = min(d for d, _, _ in date_cols.values())
    last_date = max(d for d, _, _ in date_cols.values())
    print(f"Date range in reference Excel: {first_date} to {last_date}")
    
    # 2. Parse students
    students = []
    # weekday -> list of assignments (student_dict, time_str, trainer_str)
    weekday_templates = defaultdict(list)
    
    # Oct exact classes: (date_str, time_str, trainer_str) -> list of students
    oct_exact_classes = defaultdict(list)
    
    for r in range(4, ws.max_row + 1):
        name = ws.cell(r, 1).value
        if not name or not str(name).strip():
            continue
        
        stud_id = ws.cell(r, 2).value or f"MKS{r:05d}"
        rating = ws.cell(r, 3).value
        level = ws.cell(r, 4).value or "Basic"
        batch = ws.cell(r, 5).value or "G Basic1"
        planned = ws.cell(r, 6).value
        comments = ws.cell(r, ws.max_column).value or ""
        
        batch_str = str(batch).strip()
        # determine batch_type (G, L, I)
        b_type = "G"
        if batch_str.startswith("L ") or batch_str.startswith("L-") or "Limited" in batch_str:
            b_type = "L"
        elif batch_str.startswith("I ") or batch_str.startswith("I-") or "Individual" in batch_str:
            b_type = "I"
            
        stud_dict = {
            "student_id": str(stud_id).strip(),
            "student_name": str(name).strip(),
            "student_level": str(level).strip(),
            "batch_type": b_type,
            "batch_name": batch_str,
            "rating": rating,
            "planned_classes": int(planned) if (planned is not None and str(planned).strip().isdigit()) else 12,
            "comments": str(comments).strip() if comments else "",
            "recurring_slots": {} # day_name -> (time_str, trainer_str)
        }
        
        # Read Oct entries
        oct_assigned_count = 0
        for col, (d_obj, day_name, tr_col) in date_cols.items():
            t_val = ws.cell(r, col).value
            tr_val = ws.cell(r, tr_col).value
            if t_val is not None:
                if isinstance(t_val, datetime.time):
                    time_str = t_val.strftime("%I:%M %p").lstrip('0')
                else:
                    time_str = str(t_val).strip()
                trainer_str = str(tr_val).strip() if tr_val else "Unassigned"
                
                # Normalize time_str e.g. 7:00 PM -> 07:00 PM – 08:00 PM or standard format
                oct_assigned_count += 1
                oct_exact_classes[(d_obj.strftime("%Y-%m-%d"), day_name, time_str, trainer_str, batch_str, str(level).strip(), b_type)].append(stud_dict)
                
                # Record in recurring slots for student
                if day_name not in stud_dict["recurring_slots"]:
                    stud_dict["recurring_slots"][day_name] = (time_str, trainer_str)
                    weekday_templates[day_name].append({
                        "student": stud_dict,
                        "time_slot": time_str,
                        "coach_name": trainer_str,
                        "batch_name": batch_str,
                        "student_level": str(level).strip(),
                        "batch_type": b_type
                    })
                    
        stud_dict["oct_actual_classes"] = oct_assigned_count
        students.append(stud_dict)

    print(f"Total students parsed: {len(students)}")
    print(f"Total Oct exact classes: {len(oct_exact_classes)}")
    total_oct_slots = sum(len(stus) for stus in oct_exact_classes.values())
    print(f"Total Oct student assignments: {total_oct_slots}")
    print("\nWeekday recurring template counts (students scheduled on that weekday):")
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        print(f"  {day}: {len(weekday_templates[day])} students")

if __name__ == "__main__":
    test_parse()
