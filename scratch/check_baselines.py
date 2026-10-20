from app.storage.database import seed_october_baseline_if_missing, get_active_baseline_db

seed_october_baseline_if_missing()

for m in ['2026-09', '2026-10', '2026-11', '2026-12']:
    b = get_active_baseline_db(m)
    if b:
        print(f"{m}: Active v{b['version']} - Students: {b['student_count']}, Classes: {b['class_count']}, Seats: {b['student_class_count']}")
    else:
        print(f"{m}: Not found")
