import re
from collections import defaultdict
import datetime

# Parse the data
with open('d:/CODESPACE/chess/scratch/sept_schedule.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

schedule = []
current_date = None
current_coach = None
current_time = None
current_class_students = []

def save_class():
    if current_coach and current_time and current_class_students:
        schedule.append({
            'date': current_date,
            'coach': current_coach,
            'time': current_time,
            'students': current_class_students.copy()
        })
        current_class_students.clear()

for line in lines:
    line = line.strip()
    if not line:
        continue
    
    if line.startswith('📅 DATE:'):
        save_class()
        current_date = line.replace('📅 DATE:', '').strip()
        current_coach = None
        current_time = None
    elif 'Total Classes This Day:' in line:
        continue
    elif line.startswith('━━━━━━━━━━━━━━━━━━━━'):
        continue
    elif line.startswith('♟️'):
        save_class()
        current_coach = line.replace('♟️', '').strip()
        current_time = None
    elif 'AM' in line or 'PM' in line or 'TIME NOT PROVIDED' in line:
        save_class()
        current_time = line.strip()
    elif line.startswith('- '):
        student = line.replace('- ', '').strip()
        current_class_students.append(student)

save_class()

# Analysis
student_classes = defaultdict(list)
for cls in schedule:
    for student in cls['students']:
        student_classes[student].append({
            'date': cls['date'],
            'coach': cls['coach'],
            'time': cls['time']
        })

print(f"Total students: {len(student_classes)}")
print(f"Total classes recorded: {len(schedule)}")

# Output summary to see what we're dealing with
print("Sample student data:")
for i, (student, classes) in enumerate(student_classes.items()):
    if i < 5:
        print(f"Student: {student}, Class count: {len(classes)}, Sample: {classes[0]}")

# Optimize based on rules
# Let's say we group students who appear at the same time and coach, but consolidate small classes
# Wait, let's write out a naive optimized schedule for October
# October starts on Thursday, Oct 1 (if 2026). Let's assume week 1 of October maps to week 1 of Sept.
