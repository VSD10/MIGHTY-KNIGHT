from app.engine.reference_scheduler import get_reference_engine

engine = get_reference_engine()
print("Students count:", len(engine.students_raw))

total_req = sum(s.get("required_classes", 12) for s in engine.students_raw)
print("Total required from raw:", total_req)

total_actual = sum(s.get("actual_classes", 0) for s in engine.students_raw)
print("Total actual in October:", total_actual)

deficits = []
for s in engine.students_raw:
    req = s.get("required_classes", 12)
    act = s.get("actual_classes", 0)
    if act < req:
        deficits.append((s["student_name"], s["student_id"], req, act, req - act))
    elif act > req:
        print(f"OVER: {s['student_name']} req={req} act={act}")

print("Total students with deficit:", len(deficits))
total_def = sum(d[4] for d in deficits)
print("Total deficit sum:", total_def)
print("total_actual + total_def:", total_actual + total_def)

for d in deficits:
    print(f"  {d[0]} ({d[1]}): required={d[2]}, actual={d[3]}, deficit={d[4]}")
