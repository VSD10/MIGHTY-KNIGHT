import openpyxl
import os
import datetime
from collections import defaultdict, Counter

path = os.path.join(os.path.dirname(__file__), '..', 'sample_data', "Oct'26 Schedule_FRESH-1.xlsx")
wb = openpyxl.load_workbook(os.path.abspath(path), data_only=True)
ws = wb.active

date_cols = {}
for col in range(8, ws.max_column, 2):
    d_val = ws.cell(3, col).value
    day_val = ws.cell(1, col).value
    if d_val:
        d_obj = d_val.date() if isinstance(d_val, datetime.datetime) else d_val
        date_cols[col] = (d_obj, day_val, col + 1)

# Check per student weekday patterns
students_with_varying_weekday_slots = []
total_students = 0

for r in range(4, ws.max_row + 1):
    name = ws.cell(r, 1).value
    if not name or not str(name).strip():
        continue
    total_students += 1
    stud_id = ws.cell(r, 2).value
    
    # weekday -> list of (time, trainer)
    weekday_slots = defaultdict(list)
    for col, (d_obj, day_val, tr_col) in date_cols.items():
        t_val = ws.cell(r, col).value
        tr_val = ws.cell(r, tr_col).value
        if t_val is not None:
            t_str = t_val.strftime("%I:%M %p").lstrip('0') if isinstance(t_val, datetime.time) else str(t_val)
            tr_str = str(tr_val).strip() if tr_val else "Unassigned"
            weekday_slots[day_val].append((t_str, tr_str))
            
    for day, slots in weekday_slots.items():
        unique_slots = set(slots)
        if len(unique_slots) > 1:
            students_with_varying_weekday_slots.append((name, stud_id, day, Counter(slots)))

print(f"Total students: {total_students}")
print(f"Students with varying slots on same weekday: {len(students_with_varying_weekday_slots)}")
for item in students_with_varying_weekday_slots[:15]:
    print(item)
