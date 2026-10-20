import sys
from app.storage.database import seed_october_baseline_if_missing, get_active_baseline_db
from app.engine.baseline_service import generate_next_month_draft

seed_october_baseline_if_missing()
oct_base = get_active_baseline_db("2026-10")
print("October active baseline:", bool(oct_base), "Students:", oct_base["student_count"], "Classes:", oct_base["class_count"])

nov_draft = generate_next_month_draft("2026-10", 2026, 11)
print("November draft:", nov_draft["month"], "Students:", nov_draft["student_count"], "Classes:", nov_draft["class_count"], "Seats:", nov_draft["student_class_count"])

# Simulate November active
from app.storage.database import save_baseline_db
nov_record = dict(nov_draft)
nov_record["status"] = "Active"
save_baseline_db(nov_record)

dec_draft = generate_next_month_draft("2026-11", 2026, 12)
print("December draft:", dec_draft["month"], "Students:", dec_draft["student_count"], "Classes:", dec_draft["class_count"], "Seats:", dec_draft["student_class_count"])
