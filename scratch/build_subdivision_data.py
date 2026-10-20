import json
from collections import defaultdict, Counter
import re

from app.constants.batch_naming import (
    BATCH_TYPES, SUBDIVISION_CAPACITIES, LEVEL_TO_CODE, CODE_TO_LEVEL,
    extract_source_suffix_tag, format_batch_subdivision_name,
    resolve_level_code, allocate_students_to_subdivisions
)

with open('backend/data/reference_oct_schedule.json', 'r', encoding='utf-8') as f:
    ref_data = json.load(f)

students_raw = ref_data.get('students_raw', [])
oct_exact_classes = ref_data.get('oct_exact_classes_by_date', {})

print(f"Loaded {len(students_raw)} raw students and {len(oct_exact_classes)} class dates.")

# Run allocate_students_to_subdivisions
subdivisions, warnings = allocate_students_to_subdivisions(students_raw)

print(f"Generated {len(subdivisions)} subdivisions:")
for sub in subdivisions:
    s_names = [st['student_name'] for st in sub['students'][:3]]
    tags = sub.get('source_tags', [])
    tag_str = f" Tags: {tags}" if tags else ""
    print(f"  {sub['batch_name']} ({sub['level']} - {sub['batch_type']}): {sub['student_count']}/{sub['capacity_max']} students.{tag_str} Ex: {s_names}")

if warnings:
    print(f"\nConflict Warnings ({len(warnings)}):")
    for w in warnings:
        print(f"  [{w['severity']}] {w['type']}: {w['message']}")
else:
    print("\nZero Conflict Warnings! All subdivisions adhere strictly to Rule 1 and capacity limits.")
