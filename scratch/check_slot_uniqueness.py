import openpyxl
import os
import datetime
from collections import defaultdict

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

# Check for each (date, time, trainer): how many students
slot_occupancy = defaultdict(lambda: defaultdict(list)) # date -> (time, trainer) -> list of students

for r in range(4, ws.max_row + 1):
    name = ws.cell(r, 1).value
    if not name:
        continue
    stud_id = ws.cell(r, 2).value
    for col, (d_obj, day_name, tr_col) in date_cols.items():
        t_val = ws.cell(r, col).value
        tr_val = ws.cell(r, tr_col).value
        if t_val is not None:
            t_str = t_val.strftime("%I:%M %p").lstrip('0') if isinstance(t_val, datetime.time) else str(t_val).strip()
            tr_str = str(tr_val).strip() if tr_val else "Unassigned"
            slot_occupancy[d_obj][(t_str, tr_str)].append(name)

print("Date check completed.")
# Check: on any date, does a trainer teach 2 DIFFERENT time slots that overlap?
# All time slots are 1-hour slots, e.g. 7:00 PM, 6:00 PM, 5:30 PM
for d_obj, slots in slot_occupancy.items():
    coach_times = defaultdict(list)
    for (t_str, tr_str), stus in slots.items():
        coach_times[tr_str].append(t_str)
    for tr, times in coach_times.items():
        if len(times) != len(set(times)):
            print(f"Coach {tr} has duplicate slot {times} on {d_obj}")
print("Slot uniqueness check done.")
