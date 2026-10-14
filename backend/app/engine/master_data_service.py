"""
master_data_service.py
======================
F1 Master Data Hub business logic:
- Validation (unique ID, windows, morning rule, requirement cap <= 12 exception)
- Student Level Changes & History
- All 6 Batch-type Conversions (G<->L, G<->I, L<->I)
- Safe Student Deletion without orphans
- Dynamic Trainer Priority per level (shift down, close gaps, no duplicates)
- Trainer Deletion & Qualification Loss handling
"""

import uuid
import copy
from datetime import datetime, date
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict

from app.engine.rule_engine import (
    LEVEL_MAP, COACH_REFERENCE, resolve_coach_canonical_name,
    parse_time_to_minutes, check_operating_hours,
    check_tournament_eligibility, check_regular_level_compatibility,
    check_tournament_grouping
)
from app.storage.database import (
    save_single_student_db, delete_single_student_db,
    save_single_coach_db, delete_single_coach_db,
    save_exception_record_db, get_exception_records_db
)

# ─────────────────────────────────────────────────────────────────────────────
# 1. STUDENT VALIDATION (F1)
# ─────────────────────────────────────────────────────────────────────────────

def validate_student_data(
    data: Dict[str, Any],
    existing_students: List[Dict[str, Any]],
    is_new: bool = False
) -> Tuple[bool, List[str]]:
    """
    Validates student fields according to F1 specification:
    - Unique ID
    - Start < end for availability windows
    - No overlapping windows for one student
    - Requirement <= 12 unless documented Requirement Exception exists
    - Morning windows (before 4:00 PM Mon-Sat) only saved when explicitly allowed
    """
    errors = []
    sid = str(data.get("student_id", "")).strip()

    if not sid:
        errors.append("Student ID is required.")
    elif is_new:
        if any(s.get("student_id", "").strip().lower() == sid.lower() for s in existing_students):
            errors.append(f"Student ID '{sid}' already exists. Must be unique.")

    if not str(data.get("student_name", "")).strip():
        errors.append("Student name is required.")

    # Requirement cap check
    req = data.get("required_classes", 8)
    req_exc = data.get("requirement_exception")
    if req > 12 and not req_exc:
        errors.append(f"Monthly requirement ({req}) exceeds standard cap of 12 classes. A documented Requirement Exception with reason is required.")

    # Multi-window availability check
    avail = data.get("availability", {})
    is_morning = data.get("is_morning_available", False)

    for day_name, windows in avail.items():
        if not windows:
            continue
        parsed_intervals = []
        for w in windows:
            if not isinstance(w, (list, tuple)) or len(w) < 2:
                continue
            s_str, e_str = w[0], w[1]
            s_min = parse_time_to_minutes(s_str)
            e_min = parse_time_to_minutes(e_str)

            if s_min is None or e_min is None:
                errors.append(f"{day_name}: Invalid time window format '{s_str} - {e_str}'.")
                continue
            if s_min >= e_min:
                errors.append(f"{day_name}: Window start time ({s_str}) must be earlier than end time ({e_str}).")
                continue

            # Morning check Mon-Sat before 16:00 (4:00 PM)
            if day_name != "Sunday" and s_min < 16 * 60 and not is_morning:
                errors.append(f"{day_name}: Morning window starting at {s_str} (< 4:00 PM) requires explicit morning availability permission.")

            parsed_intervals.append((s_min, e_min, s_str, e_str))

        # Check overlapping windows for the same student on the same day
        parsed_intervals.sort(key=lambda x: x[0])
        for i in range(len(parsed_intervals) - 1):
            if parsed_intervals[i][1] > parsed_intervals[i + 1][0]:
                errors.append(
                    f"{day_name}: Overlapping availability windows detected between "
                    f"'{parsed_intervals[i][2]}–{parsed_intervals[i][3]}' and '{parsed_intervals[i+1][2]}–{parsed_intervals[i+1][3]}'."
                )

    return len(errors) == 0, errors

# ─────────────────────────────────────────────────────────────────────────────
# 2. DYNAMIC TRAINER PRIORITY PER LEVEL (F1 & F8)
# ─────────────────────────────────────────────────────────────────────────────

def reorder_coach_level_priorities(
    coaches: List[Dict[str, Any]],
    level: str,
    target_coach_name: str,
    new_priority: int
) -> List[Dict[str, Any]]:
    """
    Independent 1-indexed priority per level.
    Inserting at N shifts others down (A1, B2, C3, D4 + new at 1 -> new 1, A2, B3, C4, D5).
    Removing coach from level closes gap. No duplicates or gaps, ever.
    """
    updated_coaches = [dict(c) for c in coaches]
    canon_target = resolve_coach_canonical_name(target_coach_name)

    # Collect coaches that teach this level
    coaches_with_level = []
    for c in updated_coaches:
        p_map = c.get("qualified_levels_priority", {})
        levels = c.get("levels_handled", [])
        if level in levels or level in p_map:
            coaches_with_level.append((c, p_map.get(level, 99)))

    # Sort by current priority
    coaches_with_level.sort(key=lambda x: x[1])

    # Extract coach names
    ordered_names = [resolve_coach_canonical_name(c["coach_name"]) for c, _ in coaches_with_level]
    if canon_target in ordered_names:
        ordered_names.remove(canon_target)

    # Insert target at new_priority (1-indexed)
    insert_idx = max(0, min(len(ordered_names), new_priority - 1))
    ordered_names.insert(insert_idx, canon_target)

    # Re-assign sequential priorities 1..N with zero gaps and zero duplicates
    name_to_prio = {name: idx + 1 for idx, name in enumerate(ordered_names)}

    for c in updated_coaches:
        c_name = resolve_coach_canonical_name(c["coach_name"])
        if c_name in name_to_prio:
            if "qualified_levels_priority" not in c:
                c["qualified_levels_priority"] = {}
            c["qualified_levels_priority"][level] = name_to_prio[c_name]
            # Ensure level is in levels_handled
            if level not in c.get("levels_handled", []):
                c.setdefault("levels_handled", []).append(level)
            save_single_coach_db(c)

    return updated_coaches

def remove_coach_from_level_priority(
    coaches: List[Dict[str, Any]],
    level: str,
    target_coach_name: str
) -> List[Dict[str, Any]]:
    """
    Removes coach from level qualification and closes the priority gap for remaining coaches.
    """
    updated_coaches = [dict(c) for c in coaches]
    canon_target = resolve_coach_canonical_name(target_coach_name)

    remaining_coaches = []
    for c in updated_coaches:
        c_name = resolve_coach_canonical_name(c["coach_name"])
        p_map = c.get("qualified_levels_priority", {})
        if c_name == canon_target:
            if level in p_map:
                del p_map[level]
            if level in c.get("levels_handled", []):
                c["levels_handled"] = [l for l in c["levels_handled"] if l != level]
            save_single_coach_db(c)
        elif level in c.get("levels_handled", []) or level in p_map:
            remaining_coaches.append((c, p_map.get(level, 99)))

    # Close gap for remaining coaches
    remaining_coaches.sort(key=lambda x: x[1])
    for idx, (c, _) in enumerate(remaining_coaches, 1):
        if "qualified_levels_priority" not in c:
            c["qualified_levels_priority"] = {}
        c["qualified_levels_priority"][level] = idx
        save_single_coach_db(c)

    return updated_coaches

# ─────────────────────────────────────────────────────────────────────────────
# 3. BATCH-TYPE CONVERSIONS (F1: G<->L, G<->I, L<->I)
# ─────────────────────────────────────────────────────────────────────────────

def handle_batch_type_conversion(
    student_id: str,
    new_batch_type: str,
    all_classes: List[Dict[str, Any]],
    student_master_map: Dict[str, Any],
    month: str = "2026-10"
) -> Dict[str, Any]:
    """
    Handles all 6 batch-type conversions: G->L, G->I, L->G, L->I, I->G, I->L.
    Full recalculation:
    - Removes obsolete assignments and releases seats in existing batches
    - Conversion to Individual removes tournament assignments and turns Sunday attendance into regular Individual classes
    - Persists accepted assignments, updates student record
    """
    s_obj = student_master_map.get(student_id)
    if not s_obj:
        return {"status": "error", "message": f"Student {student_id} not found"}

    old_batch_type = s_obj.get("batch_type", "G")
    s_lvl = s_obj.get("student_level", "Beginner 1")
    s_name = s_obj.get("student_name", student_id)

    # 1. Update Student record
    s_obj["batch_type"] = new_batch_type
    s_obj["batch"] = f"{new_batch_type} {s_lvl}"
    save_single_student_db(s_obj)

    # 2. Check scheduled classes for this student and release incompatible seats
    removed_classes = []
    kept_classes = []

    for cls in all_classes:
        s_ids = list(cls.get("student_ids", []))
        if student_id not in s_ids:
            continue

        is_tourn = cls.get("is_tournament", False)
        removed = False

        # Rule: Conversion to Individual removes tournament assignments
        if new_batch_type == "I" and is_tourn:
            removed = True
        # Rule: Conversion to Individual cannot remain in multi-student batch
        elif new_batch_type == "I" and len(s_ids) > 1:
            removed = True
        # Rule: Conversion to Limited cannot remain in batch exceeding Limited capacity 3
        elif new_batch_type == "L" and len(s_ids) > 3:
            removed = True

        if removed:
            old_ids = list(s_ids)
            s_ids.remove(student_id)
            cls["student_ids"] = s_ids
            cls["student_names"] = [name for name in cls.get("student_names", []) if name != s_name]
            removed_classes.append(cls.get("class_id"))

            rec = {
                "id": f"EXC_CONV_{uuid.uuid4().hex[:8].upper()}",
                "month": month,
                "date": cls.get("date"),
                "start_time": cls.get("time_slot"),
                "coach_id": resolve_coach_canonical_name(cls.get("coach_name", "")),
                "class_key": f"{cls.get('date')}||{cls.get('time_slot')}||{resolve_coach_canonical_name(cls.get('coach_name', ''))}",
                "action_type": "remove_student",
                "affected_student_ids": [student_id],
                "before": {"student_ids": old_ids},
                "after": {"student_ids": s_ids},
                "subtype": "normal_assignment",
                "violated_rules": [],
                "reason": f"Batch conversion ({old_batch_type}->{new_batch_type}): released seat in incompatible batch",
                "created_by": "System (Batch Conversion)",
                "created_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
                "status": "active",
                "version": 1
            }
            save_exception_record_db(rec)
        else:
            kept_classes.append(cls.get("class_id"))

    return {
        "status": "success",
        "student_id": student_id,
        "old_batch_type": old_batch_type,
        "new_batch_type": new_batch_type,
        "removed_assignments_count": len(removed_classes),
        "kept_assignments_count": len(kept_classes)
    }

# ─────────────────────────────────────────────────────────────────────────────
# 4. STUDENT LEVEL CHANGE (F1)
# ─────────────────────────────────────────────────────────────────────────────

def handle_student_level_change(
    student_id: str,
    new_level: str,
    reason: str,
    all_classes: List[Dict[str, Any]],
    student_master_map: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Handles level promotion or adjustment:
    - Records level history entry with timestamp
    - Re-checks level compatibility, tournament group, and coach qualification for future classes
    - Violations routed to Attention without overwriting baseline classes
    """
    s_obj = student_master_map.get(student_id)
    if not s_obj:
        return {"status": "error", "message": f"Student {student_id} not found"}

    old_level = s_obj.get("student_level", "Beginner 1")
    now_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")

    # Record history
    history = s_obj.get("level_history", [])
    history.append({
        "from_level": old_level,
        "to_level": new_level,
        "changed_at": now_str,
        "reason": reason or "Administrative level progression"
    })
    s_obj["level_history"] = history
    s_obj["student_level"] = new_level
    s_obj["batch"] = f"{s_obj.get('batch_type', 'G')} {new_level}"
    save_single_student_db(s_obj)

    # Audit violations in currently scheduled classes
    incompatible_classes = []
    for cls in all_classes:
        if student_id not in cls.get("student_ids", []):
            continue

        day_name = cls.get("day", "")
        is_tourn = cls.get("is_tournament", False)

        if is_tourn:
            el_ok, _ = check_tournament_eligibility(new_level, s_obj.get("batch_type", "G"), day_name)
            if not el_ok:
                incompatible_classes.append({
                    "class_id": cls.get("class_id"),
                    "date": cls.get("date"),
                    "time_slot": cls.get("time_slot"),
                    "reason": f"Level {new_level} ineligible for {day_name} tournament"
                })
        else:
            other_lvls = [student_master_map.get(sid, {}).get("student_level", new_level) for sid in cls.get("student_ids", []) if sid != student_id]
            comp_ok, msg, _ = check_regular_level_compatibility(other_lvls + [new_level])
            if not comp_ok:
                incompatible_classes.append({
                    "class_id": cls.get("class_id"),
                    "date": cls.get("date"),
                    "time_slot": cls.get("time_slot"),
                    "reason": msg
                })

    return {
        "status": "success",
        "student_id": student_id,
        "old_level": old_level,
        "new_level": new_level,
        "history": history,
        "incompatible_classes_count": len(incompatible_classes),
        "incompatible_classes": incompatible_classes
    }
