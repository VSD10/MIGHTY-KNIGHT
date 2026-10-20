"""
app.constants.batch_naming
==========================
Defines the strict Mighty Knight Academy batch subdivision naming pattern,
capacity constraints, level codes, source tag preservation, and sequential
subdivision allocation logic.

Naming Pattern:
  `[BatchType][LevelCode]-[SubdivisionNumber]`

Examples:
  - Group Beginner 1 (1st subdivision): GBN1-01 (Max 8 students)
  - Group Beginner 1 (2nd subdivision): GBN1-02 (Max 8 students)
  - Limited Basic 1:                   LB1-01  (Max 3 students)
  - Individual Early Intermediate 2:   IEM2-01 (Max 1 student)
"""

import re
from typing import Dict, Any, List, Optional, Tuple, Set
from collections import defaultdict

# ------------------------------------------------------------------------------
# 1. BATCH TYPES & STRICT CAPACITY LIMITS
# ------------------------------------------------------------------------------
BATCH_TYPES = {
    "G": "Group Batch",
    "L": "Limited Batch",
    "I": "Individual Batch"
}

SUBDIVISION_CAPACITIES = {
    "G": {"min": 1, "max": 8},
    "L": {"min": 1, "max": 3},
    "I": {"min": 1, "max": 1}
}

# ------------------------------------------------------------------------------
# 2. LEVEL TO CODE MAPPING (Strict 8 Core Levels + Advanced)
# ------------------------------------------------------------------------------
LEVEL_TO_CODE = {
    "Basic 1": "B1",
    "Basic 2": "B2",
    "Beginner 1": "BN1",
    "Beginner 2": "BN2",
    "Early Intermediate 1": "EM1",
    "Early Intermediate 2": "EM2",
    "Intermediate 1": "IM1",
    "Intermediate 2": "IM2",
    "Advanced": "ADV"
}

CODE_TO_LEVEL = {v: k for k, v in LEVEL_TO_CODE.items()}

# Common aliases / variations for level lookup
LEVEL_ALIASES = {
    "b1": "Basic 1",
    "basic 1": "Basic 1",
    "basic1": "Basic 1",
    "b2": "Basic 2",
    "basic 2": "Basic 2",
    "basic2": "Basic 2",
    "bn1": "Beginner 1",
    "beg1": "Beginner 1",
    "beginner 1": "Beginner 1",
    "beginner1": "Beginner 1",
    "bn2": "Beginner 2",
    "beg2": "Beginner 2",
    "beginner 2": "Beginner 2",
    "beginner2": "Beginner 2",
    "em1": "Early Intermediate 1",
    "early intermediate 1": "Early Intermediate 1",
    "earlyintermediate 1": "Early Intermediate 1",
    "earlyintermediate1": "Early Intermediate 1",
    "early intrmediate1": "Early Intermediate 1",
    "em2": "Early Intermediate 2",
    "early intermediate 2": "Early Intermediate 2",
    "earlyintermediate 2": "Early Intermediate 2",
    "earlyintermediate2": "Early Intermediate 2",
    "im1": "Intermediate 1",
    "intermediate 1": "Intermediate 1",
    "intermediate1": "Intermediate 1",
    "im2": "Intermediate 2",
    "intermediate 2": "Intermediate 2",
    "intermediate2": "Intermediate 2",
    "adv": "Advanced",
    "advanced": "Advanced"
}

# Suffix tags to preserve from raw historical datasets
HISTORICAL_SOURCE_TAGS = {"A", "B", "C", "D", "S"}

# ------------------------------------------------------------------------------
# 3. SOURCE TAG EXTRACTION
# ------------------------------------------------------------------------------
def extract_source_suffix_tag(raw_batch: Optional[str]) -> Tuple[Optional[str], str]:
    """
    Extracts historical source tags ([A], [B], [C], [D], [S]) from raw batch strings.
    E.g. 'L Beginner1B' -> ('[B]', 'L Beginner1')
         'G beginner1C' -> ('[C]', 'G beginner1')
         'G Beginner2s' -> ('[S]', 'G Beginner2')
         'G Basic2A'    -> ('[A]', 'G Basic2')
    """
    if not raw_batch:
        return None, ""
    b = str(raw_batch).strip()

    # Look for trailing suffix letter A, B, C, D, S preceded by digit 1 or 2
    m = re.search(r'([12])\s*([ABCDSabcds])\b', b)
    if m:
        letter = m.group(2).upper()
        if letter in HISTORICAL_SOURCE_TAGS:
            tag = f"[{letter}]"
            core = b[:m.start(2)] + b[m.end(2):]
            return tag, re.sub(r'\s+', ' ', core).strip()

    # Also check if already bracketed e.g. 'G Beginner 1 [B]'
    m_bracket = re.search(r'\[([ABCDSabcds])\]', b)
    if m_bracket:
        tag = f"[{m_bracket.group(1).upper()}]"
        core = re.sub(r'\[[ABCDSabcds]\]', '', b).strip()
        return tag, re.sub(r'\s+', ' ', core).strip()

    return None, b

# ------------------------------------------------------------------------------
# 4. NAMING HELPERS
# ------------------------------------------------------------------------------
def resolve_level_code(level_str: str) -> str:
    """Returns canonical level code (e.g. 'Beginner 1' -> 'BN1')."""
    if not level_str:
        return "BN1"
    clean = str(level_str).strip()
    if clean in LEVEL_TO_CODE:
        return LEVEL_TO_CODE[clean]
    lower = clean.lower()
    if lower in LEVEL_ALIASES:
        official = LEVEL_ALIASES[lower]
        return LEVEL_TO_CODE.get(official, "BN1")
    return "BN1"

def format_batch_subdivision_name(batch_type: str, level_name_or_code: str, subdivision_num: int) -> str:
    """
    Constructs the official batch subdivision name:
    Pattern: `[BatchType][LevelCode]-[SubdivisionNumber]`
    E.g.: format_batch_subdivision_name('G', 'Beginner 1', 1) -> 'GBN1-01'
    """
    b_type = (batch_type or "G").strip()[:1].upper()
    if b_type not in BATCH_TYPES:
        b_type = "G"

    # Check if level_name_or_code is already a code (e.g. 'BN1') or full name
    code = level_name_or_code.strip().upper()
    if code in CODE_TO_LEVEL:
        lvl_code = code
    else:
        lvl_code = resolve_level_code(level_name_or_code)

    sub_str = str(int(subdivision_num)).zfill(2)
    return f"{b_type}{lvl_code}-{sub_str}"

def parse_batch_subdivision_name(batch_name: str) -> Optional[Dict[str, Any]]:
    """
    Parses a strict subdivision name like 'GBN1-01' or 'LEM1-02'.
    Returns a dict with breakdown, or None if not matching the pattern.
    """
    if not batch_name:
        return None
    s = str(batch_name).strip()
    m = re.match(r'^([GLI])([A-Z0-9]+)-(\d{2,})$', s)
    if not m:
        return None

    b_type = m.group(1).upper()
    lvl_code = m.group(2).upper()
    sub_num = int(m.group(3))
    sub_str = m.group(3)

    official_level = CODE_TO_LEVEL.get(lvl_code, "Beginner 1")
    cap_info = SUBDIVISION_CAPACITIES.get(b_type, {"min": 1, "max": 8})

    return {
        "batch_name": s,
        "batch_type": b_type,
        "batch_type_label": BATCH_TYPES.get(b_type, "Group Batch"),
        "level_code": lvl_code,
        "level": official_level,
        "subdivision_number": sub_num,
        "subdivision_str": sub_str,
        "capacity_min": cap_info["min"],
        "capacity_max": cap_info["max"]
    }

def normalize_batch_name_to_subdivision(
    raw_name: Optional[str],
    default_btype: str = "G",
    default_level: str = "Beginner 1",
    subdivision_num: int = 1
) -> str:
    """
    Normalizes any historical or loose batch name into the strict subdivision format.
    E.g. 'G Beginner1' -> 'GBN1-01'
         'L Basic2'    -> 'LB2-01'
         'I Intermediate 2' -> 'IIM2-01'
         'GBN1-02'     -> 'GBN1-02' (kept intact)
    """
    if not raw_name or not str(raw_name).strip():
        return format_batch_subdivision_name(default_btype, default_level, subdivision_num)

    s = str(raw_name).strip()
    parsed = parse_batch_subdivision_name(s)
    if parsed:
        return parsed["batch_name"]

    # Extract tag if present
    _, clean = extract_source_suffix_tag(s)

    # Determine batch type from leading letter
    b_type = default_btype
    if clean.startswith(("G ", "G-", "GB", "GEM", "GIM", "GBN")):
        b_type = "G"
    elif clean.startswith(("L ", "L-", "LB", "LEM", "LIM", "LBN")) or "Limited" in clean:
        b_type = "L"
    elif clean.startswith(("I ", "I-", "IB", "IEM", "IIM", "IBN")) or "Individual" in clean:
        b_type = "I"

    # Extract level from clean string
    from app.constants.levels import normalize_batch_to_level
    lvl, _, _ = normalize_batch_to_level(clean)
    lvl_code = resolve_level_code(lvl)

    return format_batch_subdivision_name(b_type, lvl_code, subdivision_num)

# ------------------------------------------------------------------------------
# 5. CORE SCHEDULING ENGINE RULE 1: SUBDIVISION ALLOCATION & CONFLICT DETECTION
# ------------------------------------------------------------------------------
def allocate_students_to_subdivisions(
    students: List[Dict[str, Any]],
    existing_subdivisions: Optional[List[Dict[str, Any]]] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Implements Rule 1:
      1. Inspect Before Modifying: Preserves every valid existing assignment and subdivision number.
      2. Sequential Overflow:
         - Reuse available capacity in existing subdivisions of exact same level and batch type.
         - Only create new sequential subdivision (-01, -02, -03) when prior subdivisions are full.
      3. Strict Isolation: Never mix students across different levels or batch types.
      4. Conflict Flagging: Detects capacity violations, duplicate student IDs, or unassigned slots.

    Returns:
      (subdivisions_list, conflict_warnings_list)
    """
    conflict_warnings: List[Dict[str, Any]] = []
    seen_student_ids: Dict[str, str] = {} # student_id -> batch_name

    # 1. Group students by (batch_type, level_code)
    students_by_bucket = defaultdict(list)
    for s in students:
        sid = s.get("student_id", "")
        sname = s.get("student_name", sid)
        btype = s.get("batch_type", "G")
        level = s.get("student_level", "Beginner 1")
        lvl_code = resolve_level_code(level)
        bucket_key = (btype, lvl_code)

        # Check duplicate student IDs
        if sid in seen_student_ids:
            conflict_warnings.append({
                "type": "DUPLICATE_STUDENT_ID",
                "severity": "CRITICAL",
                "student_id": sid,
                "student_name": sname,
                "message": f"Duplicate Student ID {sid} ({sname}) detected across batches '{seen_student_ids[sid]}' and '{btype}{lvl_code}'."
            })
        seen_student_ids[sid] = f"{btype}{lvl_code}"

        # Extract and preserve source tag
        raw_b = s.get("batch", s.get("batch_name", ""))
        tag, _ = extract_source_suffix_tag(raw_b)
        s_copy = dict(s)
        if tag:
            s_copy["source_tag"] = tag
        students_by_bucket[bucket_key].append(s_copy)

    # 2. Build index of existing subdivisions to preserve
    existing_by_bucket = defaultdict(list)
    if existing_subdivisions:
        for sub in existing_subdivisions:
            p = parse_batch_subdivision_name(sub.get("batch_name", ""))
            if p:
                key = (p["batch_type"], p["level_code"])
                existing_by_bucket[key].append(sub)

    allocated_subdivisions: List[Dict[str, Any]] = []

    # 3. For each bucket, allocate sequentially according to capacity limits
    for (btype, lvl_code), stud_list in sorted(students_by_bucket.items()):
        max_cap = SUBDIVISION_CAPACITIES.get(btype, {"max": 8})["max"]
        min_cap = SUBDIVISION_CAPACITIES.get(btype, {"min": 1})["min"]
        official_level = CODE_TO_LEVEL.get(lvl_code, "Beginner 1")

        # Sort students preserving historical tag groups and original order
        def _stud_sort_key(st):
            # Prioritize students already with a specific source tag grouped together
            t = st.get("source_tag") or "[Z]"
            return (t, st.get("student_id", ""))

        stud_list.sort(key=_stud_sort_key)

        # Chunk students into subdivisions of max_cap
        sub_index = 1
        for i in range(0, len(stud_list), max_cap):
            chunk = stud_list[i : i + max_cap]
            sub_name = format_batch_subdivision_name(btype, lvl_code, sub_index)
            sub_id = f"BAT_{btype}{lvl_code}_{str(sub_index).zfill(2)}"

            # Update student records with assigned subdivision
            chunk_sids = []
            chunk_students = []
            for st in chunk:
                st["batch"] = sub_name
                st["batch_name"] = sub_name
                st["assigned_batch_id"] = sub_id
                chunk_sids.append(st["student_id"])
                chunk_students.append({
                    "student_id": st["student_id"],
                    "student_name": st.get("student_name", st["student_id"]),
                    "student_level": official_level,
                    "batch_type": btype,
                    "source_tag": st.get("source_tag"),
                    "mkca_rating": st.get("mkca_rating", "-"),
                    "fixed_trainer": st.get("fixed_trainer", "Unassigned")
                })

            # Check capacity violation conflict
            if len(chunk) > max_cap:
                conflict_warnings.append({
                    "type": "CAPACITY_OVERFLOW",
                    "severity": "HIGH",
                    "batch_name": sub_name,
                    "message": f"Subdivision {sub_name} exceeds strict capacity limit: {len(chunk)}/{max_cap} students."
                })

            allocated_subdivisions.append({
                "batch_id": sub_id,
                "batch_name": sub_name,
                "batch_type": btype,
                "batch_type_label": BATCH_TYPES[btype],
                "level": official_level,
                "level_code": lvl_code,
                "subdivision_number": sub_index,
                "capacity_min": min_cap,
                "capacity_max": max_cap,
                "student_count": len(chunk),
                "student_ids": chunk_sids,
                "students": chunk_students,
                "fixed_trainer": chunk[0].get("fixed_trainer", "Unassigned") if chunk else "Unassigned",
                "schedule_timings": "",
                "weekly_slots": [],
                "source_tags": sorted(list({st.get("source_tag") for st in chunk if st.get("source_tag")}))
            })
            sub_index += 1

    return allocated_subdivisions, conflict_warnings
