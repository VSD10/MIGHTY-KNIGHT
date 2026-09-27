"""
Inspect all student rows and their data in the Excel file
to understand what's in each column for each student.
"""
import openpyxl
import os
import datetime

path = os.path.join(os.path.dirname(__file__), '..', 'sample_data', "Oct'26 Schedule_FRESH-1.xlsx")
path = os.path.abspath(path)

wb = openpyxl.load_workbook(path)
ws = wb.active

# Build date->col mapping
# Row 3 has dates in even cols starting from col 8
# Each date: even col = date (datetime), odd col = trainer
# Even col = time cell, odd col = trainer cell

# Structure:
# Row 1: day name headers (col 8, 10, 12, ...)
# Row 2: col 7 = 'Actual Classes', even cols = group class counts
# Row 3: col 1-5 = student headers, even cols = dates
# Rows 4+: student data
#   col 1 = Student Name, col 2 = Stud ID, col 3 = MKCA Rating, col 4 = Level, col 5 = Batch
#   col 6 = Planned Classes, col 7 = Actual Classes (per student)
#   col 8,9 = time/trainer for date Oct 1
#   col 10,11 = time/trainer for date Oct 2
#   etc.
#   col 70 = Comments

print("Column layout:")
print("  Col 1: Student Name")
print("  Col 2: Stud ID")
print("  Col 3: MKCA Rating")
print("  Col 4: Level")
print("  Col 5: Batch")
print("  Col 6: Planned Classes")
print("  Col 7: Actual Classes")
print("  For each date d (Oct 1-31):")
print("    even_col = time cell")
print("    odd_col = trainer cell")
print()

# Print date->col mapping
print("Date -> Column mapping:")
for col in range(8, 70, 2):
    date_val = ws.cell(3, col).value
    day_val = ws.cell(1, col).value
    count_val = ws.cell(2, col).value
    if date_val:
        print(f"  {date_val.strftime('%Y-%m-%d')} ({day_val}) -> time_col={col}, trainer_col={col+1}, group_classes={count_val}")

print()
# Look at rows 4-130 for all columns
print("Sample student data (rows 4-10, all cols that have data):")
for row in range(4, 11):
    name = ws.cell(row, 1).value
    stud_id = ws.cell(row, 2).value
    planned = ws.cell(row, 6).value
    actual = ws.cell(row, 7).value
    comments = ws.cell(row, 70).value
    
    print(f"  Row {row}: {name} ({stud_id}) | Planned={planned} | Actual={actual} | Comments={repr(comments)}")
    
    # Find non-empty date columns
    for col in range(8, 70, 2):
        time_val = ws.cell(row, col).value
        trainer_val = ws.cell(row, col+1).value
        if time_val is not None or trainer_val is not None:
            date_val = ws.cell(3, col).value
            date_str = date_val.strftime('%m/%d') if date_val else f"col{col}"
            print(f"    {date_str}: time={time_val}, trainer={trainer_val}")

print()
print("Total student rows:", ws.max_row - 3)
print("Last few rows:")
for row in range(ws.max_row - 3, ws.max_row + 1):
    name = ws.cell(row, 1).value
    if name:
        print(f"  Row {row}: {name}")
