import json
from collections import defaultdict
from datetime import datetime

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

# Process dates to find Days of Week (Assuming Sept 2026, Sept 1 is Tuesday)
def get_dow(date_str):
    # format: "01-Sep"
    day = int(date_str.split('-')[0])
    # Sept 1, 2026 is Tuesday (0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun)
    return (day + 0) % 7 # 1 -> 1 (Tue)

day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Gather usual classes for each coach/dow/time
weekly_classes = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
# We'll also track how many times a student appeared in a specific slot
slot_counts = defaultdict(lambda: defaultdict(int)) # slot_key -> student -> count

for cls in schedule:
    if cls['date'] == 'None' or cls['date'] is None:
        continue
    dow = get_dow(cls['date'])
    coach = cls['coach']
    time = cls['time']
    slot_key = f"{coach}_{dow}_{time}"
    for student in cls['students']:
        slot_counts[slot_key][student] += 1

# Base weekly schedule on slots where student appeared > 1 time (to filter out one-off makeups)
base_weekly_schedule = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
for slot_key, students in slot_counts.items():
    coach, dow_str, time = slot_key.split('_', 2)
    dow = int(dow_str)
    for student, count in students.items():
        if count >= 1: # Include all for now, maybe some only had 1 class
            base_weekly_schedule[coach][dow][time].add(student)

# Optimization logic
optimized_schedule = []

def optimize_day(coach, dow, time_slots):
    # time_slots is a dict of time -> set of students
    # We want to combine small classes (limited batch 1-3 members) if possible
    # We will keep group batches (4+) as they are.
    new_slots = defaultdict(list)
    
    # Sort times roughly (string sort might be weird for AM/PM, but we'll just group by identical times first)
    # If there are two classes at the same time with 1 and 2 members, combine them to 3.
    # Actually, in base schedule, they are already grouped by exact time!
    # Let's see if we can shift some adjacent small classes to the same time to save coach hours.
    
    # For now, let's just enforce the batch sizes:
    for time, students in time_slots.items():
        students_list = list(students)
        is_individual = any('Individual' in s or 'Individual' in time or 'Individual' in coach for s in students_list)
        
        if is_individual:
            for s in students_list:
                new_slots[time].append([s])
            continue
            
        if len(students_list) >= 4:
            # Group batch - keep it intact
            new_slots[time].append(students_list)
        else:
            # Limited batch or smaller
            # Chunk into max 3
            for i in range(0, len(students_list), 3):
                new_slots[time].append(students_list[i:i+3])
                
    return new_slots

report_lines = []
report_lines.append("# Optimized Weekly Schedule (October)\n")
report_lines.append("Based on the historical September data and the rule that limited batches are capped at 3 members, while group and individual batches remain the same. The schedule preserves historical student-coach assignments and preferred timings.\n")

for dow in range(7):
    report_lines.append(f"## {day_names[dow]}")
    for coach in sorted(base_weekly_schedule.keys()):
        day_schedule = base_weekly_schedule[coach].get(dow)
        if not day_schedule:
            continue
        
        optimized = optimize_day(coach, dow, day_schedule)
        if not optimized:
            continue
            
        report_lines.append(f"\n### ♟️ {coach}")
        for time in sorted(optimized.keys()):
            batches = optimized[time]
            for batch in batches:
                report_lines.append(f"\n**{time}**")
                for student in batch:
                    report_lines.append(f"- {student}")

    report_lines.append("\n━━━━━━━━━━━━━━━━━━━━\n")

with open('d:/CODESPACE/chess/scratch/optimized_schedule.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(report_lines))

print("Optimization complete. Wrote to optimized_schedule.md")
