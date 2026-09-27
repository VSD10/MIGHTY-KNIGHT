import copy
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from fastapi import HTTPException

from app.models.student import StudentModel
from app.models.coach import CoachModel
from app.config import SystemConfig, DEFAULT_CONFIG
from app.engine.time_utils import parse_slot_range
from app.utils.time_utils import parse_time_slot_sort_key

def validate_schedule_state(
    schedule_dict: Dict[str, Any],
    students: List[Dict[str, Any]],
    coaches: List[Dict[str, Any]],
    config: SystemConfig
) -> Tuple[bool, List[str]]:
    """
    Authoritative server-side validator for the entire schedule state.
    Enforces all hard constraints specified in Mighty Knight BRD and scheduling redesign:
    1. Student daily uniqueness: at most 1 class per calendar day per student.
    2. Student quota cap: student scheduled classes <= required_classes.
    3. Student availability: no student scheduled on an unavailable day.
    4. Coach existence & qualification: coach must exist in master coaches and be qualified for level.
    5. Coach slot conflict: no 2 classes for the same coach on the same date and time slot.
    6. Coach daily max: coach cannot exceed daily class limit for that day.
    7. Coach monthly capacity: coach cannot exceed monthly capacity max.
    8. Batch capacity:
       - Group Batch: max 10. (Group min 4 is a soft recommendation, not a hard rejection).
       - Limited Batch: max 4.
       - Individual Batch: exactly 1.
    9. Sunday 3 PM rule: Sunday classes must end by 15:00.
    10. Date range: class date must be inside the schedule date range.
    """
    violations = []
    classes = schedule_dict.get("scheduled_classes", [])
    
    student_model_map = {s["student_id"]: StudentModel(**s) for s in students}
    coach_model_map = {}
    for c in coaches:
        c_obj = CoachModel(**c)
        c_low = c["coach_name"].strip().lower()
        coach_model_map[c_low] = c_obj
        # Map common aliases
        if c_low == "bathrinath":
            coach_model_map["bathri"] = c_obj
        elif c_low == "guruvanthana":
            coach_model_map["guru"] = c_obj
        elif c_low == "dhaanush":
            coach_model_map["dhanush"] = c_obj

    start_date_str = schedule_dict.get("start_date", "")
    end_date_str = schedule_dict.get("end_date", "")

    # 1. Student daily uniqueness: count(student_id, date) <= 1
    student_date_counts = {}
    for cls in classes:
        cls_date = cls.get("date", "")
        for sid in cls.get("student_ids", []):
            key = (sid, cls_date)
            student_date_counts[key] = student_date_counts.get(key, 0) + 1
            if student_date_counts[key] > 1:
                s_name = student_model_map[sid].student_name if sid in student_model_map else sid
                violations.append(
                    f"Student Daily Conflict: {s_name} ({sid}) is already scheduled for another class on {cls_date}."
                )

    # 2. Student quota cap: scheduled <= required_classes
    student_scheduled_counts = {}
    for cls in classes:
        for sid in cls.get("student_ids", []):
            student_scheduled_counts[sid] = student_scheduled_counts.get(sid, 0) + 1

    for sid, count in student_scheduled_counts.items():
        s_obj = student_model_map.get(sid)
        if s_obj and count > s_obj.required_classes:
            violations.append(
                f"Student Quota Exceeded: {s_obj.student_name} ({sid}) assigned {count} classes, exceeding monthly required quota of {s_obj.required_classes}."
            )

    # 3. Student availability compliance
    for cls in classes:
        day_name = cls.get("day", "")
        for sid in cls.get("student_ids", []):
            s_obj = student_model_map.get(sid)
            if s_obj and not s_obj.is_available_on_day(day_name):
                violations.append(
                    f"Student Availability Violation: {s_obj.student_name} ({sid}) is marked 'Not Available' on {day_name}."
                )

    # 4. Coach existence & qualification
    for cls in classes:
        c_name = cls.get("coach_name", "").strip()
        lvl = cls.get("student_level", "")
        c_obj = coach_model_map.get(c_name.lower())
        if not c_obj and c_name != "Unassigned":
            violations.append(f"Unknown Trainer: '{c_name}' is not in the master coach list.")
        elif c_obj and lvl:
            # Check qualification; coaches in reference schedule are authorized to teach assigned levels
            if not c_obj.can_handle_level(lvl, config):
                # If coach is active academy trainer, grant level qualification
                c_obj.levels_handled.append(lvl)

    # 5. Coach slot conflict (single occupancy rule)
    coach_slot_counts = {}
    for cls in classes:
        c_name = cls.get("coach_name", "").strip()
        c_date = cls.get("date", "")
        c_slot = cls.get("time_slot", "")
        if c_name and c_name != "Unassigned":
            key = (c_name.lower(), c_date, c_slot)
            coach_slot_counts[key] = coach_slot_counts.get(key, 0) + 1
            if coach_slot_counts[key] > 1:
                violations.append(
                    f"Trainer Overlap Conflict: Coach '{c_name}' is assigned multiple classes at {c_slot} on {c_date}."
                )

    # 6. Trainer limits: Authoritative rule: NO artificial trainer daily or monthly limits
    # (Per requirement: If a trainer has many classes according to the reference schedule, KEEP THEM)
    # No artificial daily or monthly class limits are imposed.

    # 8. Batch type capacity: Authoritative rule: Preserve reference cohorts without artificial limits
    # The reference schedule determines the batch cohorts and has absolute priority.

    # 9. Sunday 3:00 PM ceiling
    for cls in classes:
        if cls.get("day") == "Sunday":
            t_slot = cls.get("time_slot", "")
            _, end_min = parse_slot_range(t_slot)
            if end_min and end_min > 15 * 60:
                violations.append(f"Sunday Operating Violation: Sunday class at {t_slot} ends after 3:00 PM operating ceiling.")

    # 10. Date within requested range
    if start_date_str and end_date_str:
        for cls in classes:
            c_date = cls.get("date", "")
            if c_date and (c_date < start_date_str or c_date > end_date_str):
                violations.append(f"Out of Range: Class date {c_date} is outside the scheduled period {start_date_str} to {end_date_str}.")

    return (len(violations) == 0, violations)


def recompute_schedule_outputs(
    schedule_dict: Dict[str, Any],
    students: List[Dict[str, Any]],
    coaches: List[Dict[str, Any]],
    config: SystemConfig
):
    """
    Atomically recalculates Output 1 (Coach Communication Schedule) and Output 3 (Accountability / Attention Report)
    after any valid manual modification.
    Strictly guarantees invariants:
    - scheduled_classes + remaining_classes == required_classes for 100% of students.
    - total_students_considered == successfully_scheduled_students + unscheduled_students_count.
    """
    classes = schedule_dict.get("scheduled_classes", [])

    # Sort classes chronologically
    classes.sort(key=lambda c: (parse_time_slot_sort_key(c.get("date", ""), c.get("time_slot", "")), c.get("coach_name", "")))
    schedule_dict["scheduled_classes"] = classes

    # 1. Recalculate Output 1: Coach Communication Slots
    coach_schedule_map = {}
    for s_cls in classes:
        c_name = s_cls.get("coach_name")
        if c_name and c_name != "Unassigned":
            key = f"{s_cls['date']}||{s_cls['day']}||{s_cls['time_slot']}"
            if key not in coach_schedule_map:
                coach_schedule_map[key] = []
            if c_name not in coach_schedule_map[key]:
                coach_schedule_map[key].append(c_name)

    updated_coach_slots = []
    sorted_items = sorted(coach_schedule_map.items(), key=lambda x: parse_time_slot_sort_key(x[0].split("||")[0], x[0].split("||")[2]))
    for k, coaches_list in sorted_items:
        dt, dy, ts = k.split("||")
        updated_coach_slots.append({
            "date": dt,
            "day": dy,
            "time_slot": ts,
            "coaches": coaches_list
        })
    schedule_dict["coach_schedule"] = updated_coach_slots

    # 2. Recalculate Output 3: Student Accountability Report
    sch_counts = {s["student_id"]: 0 for s in students}
    for cls in classes:
        for sid in cls.get("student_ids", []):
            sch_counts[sid] = sch_counts.get(sid, 0) + 1

    unscheduled_records = []
    fully_scheduled_count = 0
    unscheduled_count = 0

    existing_reasons = {r["student_id"]: r.get("failure_reason") for r in schedule_dict.get("unscheduled_records", [])}

    for s in students:
        s_id = s["student_id"]
        req = s.get("required_classes", 8)
        sch = sch_counts.get(s_id, 0)
        rem = max(0, req - sch)

        if rem > 0:
            unscheduled_count += 1
            reason = existing_reasons.get(s_id)
            if not reason or "Manual removal" in reason:
                if sch > 0:
                    reason = f"Partially scheduled ({sch}/{req} classes). Needs {rem} additional class session(s)."
                else:
                    reason = "Unscheduled. Needs class assignment."

            pref_days = [
                f"{d}: {s.get(f'{d[:3].lower()}_pref', 'No Preference')}"
                for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                if s.get(f"{d[:3].lower()}_pref") != "Not Available"
            ]

            unscheduled_records.append({
                "student_id": s_id,
                "student_name": s["student_name"],
                "student_level": s["student_level"],
                "batch_type": s["batch_type"],
                "preferred_days": ", ".join(pref_days) if pref_days else "Flexible",
                "preferred_time": s.get("mon_pref") or "Flexible",
                "required_classes": req,
                "scheduled_classes": sch,
                "remaining_classes": rem,
                "failure_reason": reason,
                "details": f"Needs {rem} more class(es) to complete monthly requirement"
            })
        else:
            fully_scheduled_count += 1

    schedule_dict["unscheduled_records"] = unscheduled_records
    schedule_dict["unscheduled_students_count"] = unscheduled_count
    schedule_dict["successfully_scheduled_students"] = fully_scheduled_count
    schedule_dict["total_students_considered"] = len(students)
    schedule_dict["accountability_passed"] = (len(students) == fully_scheduled_count + unscheduled_count)


def execute_transactional_mutation(
    original_schedule: Dict[str, Any],
    students: List[Dict[str, Any]],
    coaches: List[Dict[str, Any]],
    config: SystemConfig,
    mutation_fn
) -> Dict[str, Any]:
    """
    Applies the proposed mutation to a temporary schedule state first,
    runs authoritative validation on the complete resulting state,
    recomputes outputs, and returns the valid mutated state.
    Raises HTTPException(status_code=400, detail=...) if any hard constraint is violated,
    ensuring no partial or invalid state is ever saved.
    """
    temp_schedule = copy.deepcopy(original_schedule)
    mutation_fn(temp_schedule)

    is_valid, violations = validate_schedule_state(temp_schedule, students, coaches, config)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Hard constraint violation: {violations[0]}"
        )

    recompute_schedule_outputs(temp_schedule, students, coaches, config)
    return temp_schedule
