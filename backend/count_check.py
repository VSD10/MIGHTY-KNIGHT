"""
count_check.py - just counts without writing to DB
"""
import sys
sys.path.insert(0, '.')
from collections import Counter
from import_oct26_schedule import build_classes, build_students, RAW_SCHEDULE

classes  = build_classes(RAW_SCHEDULE)
students = build_students(RAW_SCHEDULE)

coach_counts = Counter(c['coach_name'] for c in classes)

print('=== Total classes:', len(classes))
print('=== Total students:', len(students))
print()
print('=== Per coach class counts:')
for coach, cnt in sorted(coach_counts.items()):
    print(f'  {coach}: {cnt}')

expected = {'BATHRI':105,'DHAANUSH':75,'PRAKASH':67,'ABINAYA':58,'MANIKANDAN':38,'ARSHATH':18,'GURU':13,'SARAVANAN':8,'HEMA':4}
print()
print('=== MISSING per coach:')
for coach, exp in sorted(expected.items()):
    got = coach_counts.get(coach, 0)
    diff = exp - got
    if diff != 0:
        print(f'  {coach}: got {got}, expected {exp}, MISSING {diff} class(es)')
    else:
        print(f'  {coach}: OK ({got})')
