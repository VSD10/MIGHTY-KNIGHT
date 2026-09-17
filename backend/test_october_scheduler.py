import json
from datetime import date
from app.storage.database import load_master_data_db, load_master_batches_db
from app.models.student import StudentModel
from app.models.coach import CoachModel
from app.engine.batch_scheduler import run_batch_based_scheduler

data = load_master_data_db()
batches = load_master_batches_db()
print(f"Loaded {len(data['students'])} students, {len(data['coaches'])} coaches, {len(batches)} batches")

students = [StudentModel(**s) for s in data['students']]
coaches = [CoachModel(**c) for c in data['coaches']]

res = run_batch_based_scheduler(students, coaches, date(2026, 10, 1), date(2026, 10, 31))
print(f"October Scheduled Classes Count: {len(res.scheduled_classes)}")
print(f"Successfully Scheduled Students: {res.successfully_scheduled_students}")
print(f"Unscheduled Students (Output 3): {res.unscheduled_students_count}")
if res.scheduled_classes:
    c0 = res.scheduled_classes[0]
    print(f"Sample Class: {c0.date} ({c0.day}) at {c0.time_slot} | Coach: {c0.coach_name} | Batch: {c0.batch_name} | Students: {c0.student_names[:3]}")
    c_mid = res.scheduled_classes[len(res.scheduled_classes)//2]
    print(f"Mid Class: {c_mid.date} ({c_mid.day}) at {c_mid.time_slot} | Coach: {c_mid.coach_name} | Batch: {c_mid.batch_name} | Students: {c_mid.student_names[:3]}")
