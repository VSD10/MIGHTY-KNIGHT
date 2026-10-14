import urllib.request
import json

endpoints = [
    ('Data Summary', '/api/data/summary'),
    ('Master Students', '/api/master/students'),
    ('Master Batches', '/api/master/batches'),
    ('Master Coaches', '/api/master/coaches'),
    ('Active Schedule', '/api/schedule/latest/active'),
    ('Output 1 (Coach Timetable)', '/api/schedule/SCH_OCT2026_FINAL/output1'),
    ('Output 2 (Admin Schedule)', '/api/schedule/SCH_OCT2026_FINAL/output2'),
    ('Output 3 (Attention Report)', '/api/schedule/SCH_OCT2026_FINAL/output3'),
    ('Output 5 (Student Schedules)', '/api/schedule/SCH_OCT2026_FINAL/output5')
]

for name, path in endpoints:
    url = f"http://127.0.0.1:8000{path}"
    try:
        res = urllib.request.urlopen(url)
        data = json.loads(res.read())
        if path == '/api/master/students':
            print(f"[OK] {name}: count = {data.get('count')}")
        elif path == '/api/master/batches':
            print(f"[OK] {name}: count = {data.get('count')}")
        elif path == '/api/master/coaches':
            print(f"[OK] {name}: count = {data.get('count')}")
        elif path == '/api/schedule/latest/active':
            print(f"[OK] {name}: id = {data.get('schedule_id')}, status = {data.get('status')}, total = {data.get('total_students_considered')}, scheduled = {data.get('successfully_scheduled_students')}, unscheduled = {data.get('unscheduled_students_count')}")
        elif path == '/api/schedule/SCH_OCT2026_FINAL/output2':
            cls_list = data.get('detailed_classes', [])
            print(f"[OK] {name}: total classes = {len(cls_list)}, first class = {cls_list[0]['date']} {cls_list[0]['time_slot']} ({cls_list[0]['coach_name']}), last class = {cls_list[-1]['date']} {cls_list[-1]['time_slot']} ({cls_list[-1]['coach_name']})")
        elif path == '/api/schedule/SCH_OCT2026_FINAL/output1':
            slots = data.get('coach_slots', [])
            print(f"[OK] {name}: total slots = {len(slots)}")
        elif path == '/api/schedule/SCH_OCT2026_FINAL/output3':
            recs = data.get('attention_records', [])
            print(f"[OK] {name}: attention records = {len(recs)}")
        elif path == '/api/schedule/SCH_OCT2026_FINAL/output5':
            s_scheds = data.get('student_schedules', [])
            print(f"[OK] {name}: student schedules = {len(s_scheds)}")
        else:
            print(f"[OK] {name}: {data}")
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
