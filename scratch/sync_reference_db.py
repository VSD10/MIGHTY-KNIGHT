from app.engine.reference_scheduler import get_reference_engine
from app.storage.database import save_master_data_db, load_master_data_db

engine = get_reference_engine()
s_dicts = [s.model_dump() for s in engine.student_models]
c_dicts = [c.model_dump() for c in engine.coach_models]

print(f"Syncing {len(s_dicts)} students and {len(c_dicts)} coaches from reference Excel...")
save_master_data_db(s_dicts, c_dicts, [], filename="Oct'26 Schedule_FRESH-1.xlsx", upload_timestamp="Reference Master")

loaded = load_master_data_db()
print(f"Loaded back from SQLite: {len(loaded.get('students', []))} students, {len(loaded.get('coaches', []))} coaches")
print("First student:", loaded['students'][0]['student_name'], f"({loaded['students'][0]['student_id']})")
