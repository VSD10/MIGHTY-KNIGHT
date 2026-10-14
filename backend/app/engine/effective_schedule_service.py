import json
import asyncio
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict

from app.storage.database import (
    get_active_baseline_db, get_exception_records_db,
    seed_october_baseline_if_missing, load_master_data_db
)
from app.engine.rule_engine import (
    COACH_REFERENCE, resolve_coach_canonical_name, parse_time_to_minutes
)

# Real-time event bus for fire-speed delta updates (Part A4 & A6)
class ScheduleEventBus:
    _subscribers: List[asyncio.Queue] = []
    _version_counter: int = 1

    @classmethod
    def subscribe(cls) -> asyncio.Queue:
        q = asyncio.Queue()
        cls._subscribers.append(q)
        return q

    @classmethod
    def unsubscribe(cls, q: asyncio.Queue):
        if q in cls._subscribers:
            cls._subscribers.remove(q)

    @classmethod
    def emit_change(
        cls,
        month: str,
        dates: Optional[List[str]] = None,
        student_ids: Optional[List[str]] = None,
        coach_ids: Optional[List[str]] = None,
        class_ids: Optional[List[str]] = None
    ):
        cls._version_counter += 1
        payload = {
            "type": "ScheduleChanged",
            "month": month,
            "version": cls._version_counter,
            "dates": dates or [],
            "studentIds": student_ids or [],
            "coachIds": coach_ids or [],
            "classIds": class_ids or [],
            "timestamp": datetime.now().isoformat()
        }
        for q in list(cls._subscribers):
            try:
                q.put_nowait(payload)
            except Exception:
                pass

def get_effective_schedule(month: str = "2026-10") -> Dict[str, Any]:
    """
    Computes the Effective Schedule (Part A2):
    Effective Schedule = Baseline (Layer 1) + Assignments (Layer 2) + ⓒ Overlay (Layer 3).
    Every page, output, counter, and export reads from this computed state.
    """
    seed_october_baseline_if_missing()

    active_base = get_active_baseline_db(month)
    base_classes = []
    
    master_data = load_master_data_db()
    master_students_list = master_data.get("students", [])
    
    if master_students_list:
        base_students = [dict(s) for s in master_students_list]
    elif active_base:
        base_students = [dict(s) for s in active_base.get("students_data", [])]
    else:
        base_students = []

    master_student_ids = {s["student_id"] for s in base_students}
    student_name_map = {s["student_id"]: s.get("student_name", s["student_id"]) for s in base_students}
    student_quota_map = {s["student_id"]: s.get("required_classes", 12) for s in base_students}

    if active_base:
        base_classes = [dict(c) for c in active_base.get("classes_data", [])]

    # Load Active Exception Records (Layer 3 - ⓒ Overlay)
    active_exceptions = get_exception_records_db(month, status="active")

    # Apply ⓒ Overlay onto baseline classes
    # Index baseline classes by class_id and by class_key: (date, time_slot, coach_name)
    effective_classes_map = {}
    for c in base_classes:
        c_copy = dict(c)
        c_copy["student_ids"] = [sid for sid in c_copy.get("student_ids", []) if sid in master_student_ids]
        c_copy["student_names"] = [student_name_map.get(sid, sid) for sid in c_copy["student_ids"]]
        c_copy["is_baseline"] = True
        c_copy["is_compensation"] = False
        c_copy["has_compensation"] = False
        c_copy["exception_metadata"] = None
        c_st = (c_copy.get('time_slot') or '').split('-')[0].strip()
        c_co = resolve_coach_canonical_name(c_copy.get('coach_name', ''))
        key = f"{c_copy.get('date')}||{c_st}||{c_co}"
        effective_classes_map[key] = c_copy

    # Apply Exceptions
    for exc in active_exceptions:
        action = exc.get("action_type")
        key = exc.get("class_key")
        c_date = exc.get("date")
        s_time = exc.get("start_time")
        c_coach = resolve_coach_canonical_name(exc.get("coach_id"))
        s_time_clean = (s_time or "").split("-")[0].strip()
        full_key = f"{c_date}||{s_time_clean}||{c_coach}"

        before_cls_id = exc.get("class_id") or exc.get("before", {}).get("class_id")
        affected_sids = set(exc.get("affected_student_ids", []))

        def _matches(k, c):
            if k == full_key or k == key:
                return True
            if before_cls_id and c.get("class_id") == before_cls_id:
                return True
            c_st = (c.get("time_slot") or "").split("-")[0].strip()
            c_co = resolve_coach_canonical_name(c.get("coach_name", ""))
            if c.get("date") == c_date and c_co == c_coach and (not s_time_clean or c_st == s_time_clean):
                return True
            # Also match if same date, same coach, and contains the affected students
            if c.get("date") == c_date and c_co == c_coach and affected_sids and any(sid in c.get("student_ids", []) for sid in affected_sids):
                return True
            return False

        exc_meta = {
            "exception_id": exc["id"],
            "subtype": exc.get("subtype", "manual"),
            "reason": exc.get("reason", ""),
            "author": exc.get("created_by", "Admin"),
            "created_at": exc.get("created_at", ""),
            "violated_rules": exc.get("violated_rules", []),
            "before": exc.get("before", {}),
            "after": exc.get("after", {})
        }

        if action == "delete":
            # Suppress this class occurrence on this date
            del_keys = [k for k, c in list(effective_classes_map.items()) if _matches(k, c)]
            for dk in del_keys:
                del effective_classes_map[dk]

        elif action in ["edit", "move"]:
            b_date = exc.get("before", {}).get("date")
            b_time = (exc.get("before", {}).get("time_slot") or "").split("-")[0].strip()
            b_coach = resolve_coach_canonical_name(exc.get("before", {}).get("coach_name", ""))
            old_key = f"{b_date}||{b_time}||{b_coach}" if b_date else None

            match_k = None
            for k, c in list(effective_classes_map.items()):
                if old_key and k == old_key:
                    match_k = k
                    break
                if _matches(k, c):
                    match_k = k
                    break

            target_cls = effective_classes_map.pop(match_k) if match_k else None

            if not target_cls:
                target_cls = {
                    "class_id": before_cls_id or f"CLS_{exc['id']}",
                    "date": c_date,
                    "time_slot": s_time,
                    "coach_name": c_coach,
                    "student_ids": exc.get("affected_student_ids", []),
                    "student_names": [student_name_map.get(sid, sid) for sid in exc.get("affected_student_ids", [])],
                    "student_level": exc.get("after", {}).get("student_level", "Beginner 1"),
                    "batch_type": exc.get("after", {}).get("batch_type", "G"),
                    "batch_name": f"{exc.get('after', {}).get('student_level', 'Beginner 1')} - {c_coach}",
                    "warnings": []
                }

            # Apply after fields
            after_fields = exc.get("after", {})
            if "coach_name" in after_fields: target_cls["coach_name"] = resolve_coach_canonical_name(after_fields["coach_name"])
            if "date" in after_fields: target_cls["date"] = after_fields["date"]
            if "time_slot" in after_fields: target_cls["time_slot"] = after_fields["time_slot"]
            if "student_level" in after_fields: target_cls["student_level"] = after_fields["student_level"]
            if "batch_type" in after_fields: target_cls["batch_type"] = after_fields["batch_type"]
            if "student_ids" in after_fields:
                target_cls["student_ids"] = after_fields["student_ids"]
                target_cls["student_names"] = [student_name_map.get(sid, sid) for sid in after_fields["student_ids"]]

            target_cls["is_compensation"] = True
            target_cls["has_compensation"] = True
            target_cls["is_manual_override"] = True
            target_cls["exception_metadata"] = exc_meta

            t_st = (target_cls.get('time_slot') or '').split('-')[0].strip()
            new_key = f"{target_cls.get('date')}||{t_st}||{resolve_coach_canonical_name(target_cls.get('coach_name', ''))}"
            effective_classes_map[new_key] = target_cls

        elif action == "add":
            after_fields = exc.get("after", {})
            s_ids = exc.get("affected_student_ids") or after_fields.get("student_ids", [])
            s_names = [student_name_map.get(sid, sid) for sid in s_ids]
            lvl = after_fields.get("student_level", "Beginner 1")
            b_type = after_fields.get("batch_type", "G")
            is_comp = (exc.get("subtype") != "normal_assignment")
            new_cls = {
                "class_id": f"CLS_{exc['id']}",
                "date": c_date,
                "day": exc.get("after", {}).get("day", ""),
                "time_slot": s_time,
                "coach_name": c_coach,
                "student_level": lvl,
                "batch_type": b_type,
                "batch_name": f"{lvl} - {c_coach}",
                "student_ids": s_ids,
                "student_names": s_names,
                "warnings": ["Manual class (ⓒ)"] if is_comp else [],
                "is_baseline": False,
                "is_compensation": is_comp,
                "has_compensation": is_comp,
                "is_manual_override": is_comp,
                "exception_metadata": exc_meta
            }
            effective_classes_map[full_key] = new_cls

        elif action in ["add_student", "remove_student"]:
            target_cls = None
            for k, c in effective_classes_map.items():
                if _matches(k, c):
                    target_cls = c
                    break

            if target_cls:
                s_ids = list(target_cls.get("student_ids", []))
                for sid in exc.get("affected_student_ids", []):
                    if action == "add_student" and sid not in s_ids:
                        s_ids.append(sid)
                    elif action == "remove_student" and sid in s_ids:
                        s_ids.remove(sid)
                target_cls["student_ids"] = s_ids
                target_cls["student_names"] = [student_name_map.get(sid, sid) for sid in s_ids]
                is_comp = (exc.get("subtype") != "normal_assignment")
                if is_comp:
                    target_cls["is_compensation"] = True
                    target_cls["has_compensation"] = True
                    target_cls["is_manual_override"] = True
                target_cls["exception_metadata"] = exc_meta

    effective_classes = list(effective_classes_map.values())

    # Format students_formatted string and compute day name
    for c in effective_classes:
        c_date = c.get("date", "")
        if c_date and not c.get("day"):
            try:
                c["day"] = datetime.strptime(c_date, "%Y-%m-%d").strftime("%A")
            except Exception:
                c["day"] = "Monday"
                
        s_names = c.get("student_names", [])
        s_ids = c.get("student_ids", [])
        if s_names and s_ids:
            c["students_formatted"] = " · ".join([f"{name} ({sid})" for name, sid in zip(s_names, s_ids)])
        else:
            c["students_formatted"] = "Open / Unassigned"

        # Apply Tournament Labelling (Part C)
        day_name = c.get("day", "")
        lvl = c.get("student_level", "")
        b_type = c.get("batch_type", "G")
        is_tourn = False
        tourn_label = ""

        if day_name == "Sunday":
            # Eligible levels on Sunday: Basic 2, Beginner 1/2, Early Int 1/2, Int 1
            # Basic 1 and Int 2 and Individual are NOT tournaments!
            if b_type != "I" and lvl not in ["Basic 1", "Intermediate 2"]:
                is_tourn = True
                tourn_label = "Sunday Tournament"
        elif day_name == "Friday":
            # Friday Intermediate 2 Tournament (Part C1 & C2)
            if lvl == "Intermediate 2" and b_type != "I":
                is_tourn = True
                tourn_label = "Friday Tournament (Int 2)"

        c["is_tournament"] = is_tourn
        c["tournament_label"] = tourn_label

    # Sort chronologically by date and start time
    def _sort_key(cls_obj):
        dt = cls_obj.get("date", "9999-99-99")
        tm = parse_time_to_minutes(cls_obj.get("time_slot", "")) or 9999
        return (dt, tm, cls_obj.get("coach_name", ""))

    effective_classes.sort(key=_sort_key)

    # --------------------------------------------------------------------------
    # COMPUTE OUTPUTS & METRICS
    # --------------------------------------------------------------------------
    
    # Count scheduled classes per student
    student_scheduled_counts = defaultdict(int)
    for c in effective_classes:
        for sid in c.get("student_ids", []):
            student_scheduled_counts[sid] += 1

    # Output 3: Attention Report (Part A1 & A3)
    attention_records = []
    fully_scheduled_count = 0

    for s in base_students:
        sid = s["student_id"]
        sname = s.get("student_name", sid)
        req = s.get("required_classes", 12)
        sch = student_scheduled_counts.get(sid, 0)
        rem = max(0, req - sch)

        if rem > 0:
            if sch == 0:
                reason = f"Unscheduled. Needs {req} class assignments to meet monthly requirement."
            else:
                reason = f"Partially scheduled ({sch}/{req} classes). Shortfall of {rem} class session(s)."

            attention_records.append({
                "student_id": sid,
                "student_name": sname,
                "student_level": s.get("student_level", "Beginner 1"),
                "batch_type": s.get("batch_type", "G"),
                "required_classes": req,
                "scheduled_classes": sch,
                "remaining_classes": rem,
                "failure_reason": reason,
                "preferred_days": "Flexible",
                "preferred_time": "Flexible",
                "details": f"Needs {rem} more class(es) to complete monthly requirement"
            })
        else:
            fully_scheduled_count += 1

    # Check for tournaments below minimum capacity 2 (Part C4 & C8)
    for c in effective_classes:
        if c.get("is_tournament") and len(c.get("student_ids", [])) < 2:
            attention_records.append({
                "student_id": c.get("student_ids", ["N/A"])[0] if c.get("student_ids") else "N/A",
                "student_name": c.get("student_names", ["Class"])[0] if c.get("student_names") else "Class",
                "student_level": c.get("student_level", ""),
                "batch_type": "Tournament",
                "required_classes": 1,
                "scheduled_classes": 1,
                "remaining_classes": 0,
                "failure_reason": f"Tournament on {c.get('date')} at {c.get('time_slot')} is below minimum capacity (requires at least 2 students).",
                "preferred_days": c.get("day", ""),
                "preferred_time": c.get("time_slot", ""),
                "details": "Merge with a same-group tournament or convert to a regular class."
            })

    # Check for classes assigned to a deleted/unavailable coach (Part G - Scenario 10)
    master_coaches = master_data.get("coaches", [])
    active_coach_names = {resolve_coach_canonical_name(c.get("coach_name", "")).lower() for c in master_coaches} if master_coaches else {c.lower() for c in COACH_REFERENCE.keys()}
    for c in effective_classes:
        c_coach = resolve_coach_canonical_name(c.get("coach_name", ""))
        if c_coach and c_coach.lower() not in active_coach_names and c_coach.lower() != "unassigned":
            lvl = c.get("student_level", "Beginner 1")
            qual_coaches = [
                c_name for c_name, c_ref in COACH_REFERENCE.items()
                if lvl in c_ref.get("levels", []) and not c_ref.get("tournaments_only") and (not active_coach_names or c_name.lower() in active_coach_names)
            ]
            suggs = qual_coaches[:3] if qual_coaches else ["Any qualified coach"]
            attention_records.append({
                    "class_id": c.get("class_id"),
                    "student_id": c.get("student_ids", ["N/A"])[0] if c.get("student_ids") else "N/A",
                    "student_name": f"Batch: {c.get('batch_name', 'Class')}",
                    "student_level": lvl,
                    "batch_type": c.get("batch_type", "G"),
                    "required_classes": len(c.get("student_ids", [])),
                    "scheduled_classes": 0,
                    "remaining_classes": len(c.get("student_ids", [])),
                    "failure_reason": f"Coach {c_coach} was deleted/unavailable for class on {c.get('date')} at {c.get('time_slot')}. Replacement coach needed.",
                    "preferred_days": c.get("day", ""),
                    "preferred_time": c.get("time_slot", ""),
                    "details": f"Replacement suggestions: {', '.join(suggs)}"
                })

    # Output 1: Coach WhatsApp Communication Schedule
    coach_slot_map = defaultdict(lambda: defaultdict(list)) # (date, day, slot) -> coach -> [students]
    for c in effective_classes:
        c_name = c.get("coach_name", "")
        if c_name and c_name != "Unassigned":
            c_canon = resolve_coach_canonical_name(c_name)
            slot_key = (c.get("date"), c.get("day"), c.get("time_slot"))
            c_tag = " [ⓒ]" if c.get("is_compensation") else ""
            t_tag = " [Tournament]" if c.get("is_tournament") else ""
            summary_str = f"{c.get('batch_name', 'Batch')}{c_tag}{t_tag}: {c.get('students_formatted', '')}"
            coach_slot_map[slot_key][c_canon].append(summary_str)

    # Sort slots chronologically (date, then start minutes)
    sorted_slots = sorted(coach_slot_map.items(), key=lambda item: (item[0][0], parse_time_to_minutes(item[0][2]) or 9999))

    coach_slots = []
    lines = [f"*MIGHTY KNIGHT ACADEMY — SCHEDULE ({month})*", ""]
    current_date = None

    for (dt, dy, ts), coaches_dict in sorted_slots:
        is_tourn = any("[Tournament]" in b for batches in coaches_dict.values() for b in batches)
        has_comp = any("[ⓒ]" in b for batches in coaches_dict.values() for b in batches)
        coach_names_list = sorted(list(coaches_dict.keys()))

        coach_slots.append({
            "date": dt,
            "day": dy,
            "time_slot": ts,
            "coaches": coach_names_list,
            "is_tournament": is_tourn,
            "has_compensation": has_comp
        })

        if dt != current_date:
            current_date = dt
            lines.append(f"\n📅 *{dy}, {dt}*")
            lines.append("───────────────────────")
        
        tourn_tag = " (Tournament)" if is_tourn else ""
        comp_tag = " ⓒ" if has_comp else ""
        coaches_str = ", ".join(coach_names_list)
        lines.append(f"⏰ *{ts}* — {coaches_str}{tourn_tag}{comp_tag}")

    whatsapp_text = "\n".join(lines)

    # Output 4: Coach Workload & Summary
    coach_classes_count = defaultdict(int)
    coach_student_reach = defaultdict(int)
    coach_dates_map = defaultdict(lambda: defaultdict(int)) # coach -> date -> count

    for c in effective_classes:
        c_name = c.get("coach_name", "")
        if c_name and c_name != "Unassigned":
            c_canon = resolve_coach_canonical_name(c_name)
            coach_classes_count[c_canon] += 1
            coach_student_reach[c_canon] += len(c.get("student_ids", []))
            coach_dates_map[c_canon][c.get("date")] += 1

    coach_summaries = []
    for c_canon, c_ref in COACH_REFERENCE.items():
        actual_classes = coach_classes_count[c_canon]
        reach = coach_student_reach[c_canon]
        m_max = c_ref.get("monthly_max")
        is_flex = c_ref.get("is_flex", False)
        
        # Check workload exception flag for flex trainers (Part B6)
        is_workload_exception = False
        if is_flex and m_max and actual_classes > m_max:
            is_workload_exception = True

        status = "Optimal"
        status_color = "#10b981"
        if is_workload_exception or (m_max and actual_classes > m_max):
            status = "Capacity Exceeded"
            status_color = "#ef4444"
        elif actual_classes < c_ref.get("monthly_min", 0):
            status = "Under-Utilized"
            status_color = "#f59e0b"

        util_pct = min(100, round((actual_classes / (m_max or 100)) * 100)) if (m_max or 100) > 0 else 0

        coach_summaries.append({
            "coach_name": c_canon,
            "classes_scheduled": actual_classes,
            "assigned_classes": actual_classes,
            "total_hours": actual_classes * 1,
            "student_reach": reach,
            "total_student_reach": reach,
            "unique_students": reach,
            "levels_taught": c_ref.get("levels", []),
            "monthly_capacity_min": c_ref.get("monthly_min", 0),
            "monthly_capacity_max": m_max or (200 if is_flex else 100),
            "utilization_pct": util_pct,
            "status": status,
            "status_color": status_color,
            "is_flex": is_flex,
            "is_workload_exception": is_workload_exception,
            "active_dates_count": len(coach_dates_map[c_canon])
        })

    # Output 5: Student Schedules (Individual Timetable)
    student_classes_map = defaultdict(list)
    for c in effective_classes:
        for sid in c.get("student_ids", []):
            student_classes_map[sid].append(c)

    student_schedules = []
    for s in base_students:
        sid = s["student_id"]
        s_cls = student_classes_map.get(sid, [])
        student_schedules.append({
            "student_id": sid,
            "student_name": s.get("student_name", sid),
            "student_level": s.get("student_level", "Beginner 1"),
            "batch_type": s.get("batch_type", "G"),
            "required_classes": s.get("required_classes", 12),
            "scheduled_classes_count": len(s_cls),
            "classes": s_cls
        })

    # Executive Stats (Part A3 Vocabulary)
    total_classes = len(effective_classes)
    total_student_seats = sum(len(c.get("student_ids", [])) for c in effective_classes)
    total_required = sum(s.get("required_classes", 12) for s in base_students)
    quotas_completed = round(sum(min(student_scheduled_counts[s["student_id"]], s.get("required_classes", 12)) for s in base_students) / max(1, total_required) * 100, 1)
    need_attention = len(attention_records)
    compensation_count = sum(1 for c in effective_classes if c.get("is_compensation"))

    batches_data = master_data.get("batches", [])
    total_batches = len(batches_data) if batches_data else len(set(c.get("batch_name", "") for c in effective_classes))
    g_batches = sum(1 for b in batches_data if b.get("batch_type") == "G")
    l_batches = sum(1 for b in batches_data if b.get("batch_type") == "L")
    i_batches = sum(1 for b in batches_data if b.get("batch_type") == "I")

    return {
        "month": month,
        "version": ScheduleEventBus._version_counter,
        "total_classes": total_classes,
        "total_batches": total_batches,
        "g_batches": g_batches,
        "l_batches": l_batches,
        "i_batches": i_batches,
        "student_seats": total_student_seats,
        "quotas_completed": quotas_completed,
        "need_attention": need_attention,
        "total_students": len(base_students),
        "total_coaches": len([cs for cs in coach_summaries if cs["classes_scheduled"] > 0]),
        "compensation_count": compensation_count,
        "coach_slots": coach_slots,
        "scheduled_classes": effective_classes,
        "attention_records": attention_records,
        "coach_summaries": coach_summaries,
        "student_schedules": student_schedules,
        "whatsapp_plain_text": whatsapp_text
    }
