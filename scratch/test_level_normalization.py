import re
import openpyxl
from collections import defaultdict, Counter

OFFICIAL_LEVELS = [
    "Basic 1",
    "Basic 2",
    "Beginner 1",
    "Beginner 2",
    "Early Intermediate 1",
    "Early Intermediate 2",
    "Intermediate 1",
    "Intermediate 2",
    "Advanced"
]

def normalize_batch_to_level(batch_str: str):
    """
    Derives the official level from the student's actual batch:
    Ignores G / I / L prefixes, case, extra whitespace, and minor suffixes like A, B, C, D, s.
    Returns (official_level, is_unresolved, reason)
    """
    if not batch_str or not str(batch_str).strip():
        return (None, True, "Batch name is empty or missing")

    b = str(batch_str).strip()
    
    # Strip leading prefix G, I, L (with optional dash or space)
    # e.g., 'G Basic1', 'L Early Intermediate2', 'I Beginner1', 'G-Basic1'
    core = re.sub(r'^[GILgil][\s\-_]*', '', b).strip()
    # Normalize multiple whitespace
    core_clean = re.sub(r'\s+', ' ', core).lower()

    # Rule checks based on official guidelines:
    # 1. Basic 1: basic 1, basic1
    if re.search(r'^basic\s*1\b', core_clean) or core_clean == 'basic1':
        return ("Basic 1", False, None)

    # 2. Basic 2: basic 2, basic2, basic2a, etc.
    if re.search(r'^basic\s*2', core_clean):
        return ("Basic 2", False, None)

    # 3. Beginner 1: beginner 1, beginner1, beginner1a, beginner1b, beginner1c, beginner1d, beginner1s
    if re.search(r'^beginner\s*1', core_clean):
        return ("Beginner 1", False, None)

    # 4. Beginner 2: beginner 2, beginner2, beginner2a, beginner2s
    if re.search(r'^beginner\s*2', core_clean):
        return ("Beginner 2", False, None)

    # 5. Early Intermediate 1: early intermediate 1, early intermediate1
    if re.search(r'^early\s*intermediate\s*1\b', core_clean) or core_clean == 'early intermediate1':
        return ("Early Intermediate 1", False, None)

    # 6. Early Intermediate 2: early intermediate 2, early intermediate2
    if re.search(r'^early\s*intermediate\s*2\b', core_clean) or core_clean == 'early intermediate2':
        return ("Early Intermediate 2", False, None)

    # 7. Intermediate 1: intermediate 1, intermediate1
    if re.search(r'^intermediate\s*1\b', core_clean) or core_clean == 'intermediate1':
        return ("Intermediate 1", False, None)

    # 8. Intermediate 2: intermediate 2, intermediate2
    if re.search(r'^intermediate\s*2\b', core_clean) or core_clean == 'intermediate2':
        return ("Intermediate 2", False, None)

    # 9. Advanced: advanced
    if core_clean.startswith('advanced'):
        return ("Advanced", False, None)

    # Unresolved
    return (None, True, f"Batch '{batch_str}' does not match any official 9 levels (Basic 1/2, Beginner 1/2, Early Intermediate 1/2, Intermediate 1/2, Advanced)")

wb = openpyxl.load_workbook(r"sample_data/Oct'26 Schedule_FRESH-1.xlsx", data_only=True)
ws = wb.active

results = []
unresolved = []
level_counts = Counter()

for r in range(4, ws.max_row + 1):
    name = ws.cell(r, 1).value
    if not name or not str(name).strip():
        continue
    name_str = str(name).strip()
    sid = str(ws.cell(r, 2).value or f"MKS{r:05d}").strip()
    curr_level = str(ws.cell(r, 4).value or "").strip()
    batch = str(ws.cell(r, 5).value or "").strip()

    calc_level, is_unres, reason = normalize_batch_to_level(batch)
    if is_unres:
        unresolved.append({
            "name": name_str,
            "student_id": sid,
            "batch": batch,
            "current_level": curr_level,
            "reason": reason
        })
    else:
        level_counts[calc_level] += 1
    
    results.append({
        "name": name_str,
        "student_id": sid,
        "batch": batch,
        "current_level": curr_level,
        "calculated_level": calc_level if not is_unres else "UNRESOLVED"
    })

print(f"Total students parsed: {len(results)}")
print(f"Resolved: {len(results) - len(unresolved)}")
print(f"Unresolved: {len(unresolved)}")
print("\nLevel Distribution:")
for lvl in OFFICIAL_LEVELS:
    print(f"  {lvl:<22}: {level_counts[lvl]}")

print("\nUnresolved Students:")
for u in unresolved:
    print(f"  Student: {u['name']} | ID: {u['student_id']} | Batch: {u['batch']} | Current Level: {u['current_level']} | Reason: {u['reason']}")
