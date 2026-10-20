import json
from collections import defaultdict

with open('backend/data/reference_oct_schedule.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

students = data.get('students_raw', [])
exact_classes = data.get('oct_exact_classes_by_date', {})

print(f'Total students: {len(students)}')

raw_batches = defaultdict(list)
for s in students:
    raw_batches[s.get('batch_name')].append(s)

for bname, slist in sorted(raw_batches.items(), key=lambda x: str(x[0])):
    print(f'Batch: {bname} -> {len(slist)} students')
    for st in slist[:2]:
        sid = st.get('student_id')
        sname = st.get('student_name')
        slevel = st.get('student_level')
        btype = st.get('batch_type')
        print(f'   {sid} | {sname} | level: {slevel} | type: {btype}')
