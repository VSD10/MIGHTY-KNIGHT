import json
import asyncio
import calendar
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict, Counter

from app.storage.database import (
    get_active_baseline_db, get_exception_records_db,
    seed_october_baseline_if_missing, load_master_data_db
)
from app.engine.baseline_service import ensure_rolling_three_months_seeded
from app.engine.rule_engine import (
    COACH_REFERENCE, resolve_coach_canonical_name, parse_time_to_minutes
)

REFERENCE_TODAY = "2026-10-15"

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
        invalidate_effective_schedule_cache(month)
        try:
            from app.engine.suggestion_engine import invalidate_suggestion_cache
            invalidate_suggestion_cache()
        except Exception:
            pass
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

_EFFECTIVE_CACHE: Dict[str, Any] = {}

def invalidate_effective_schedule_cache(month: Optional[str] = None):
    if month:
        for k in list(_EFFECTIVE_CACHE.keys()):
            if k.startswith(month):
                _EFFECTIVE_CACHE.pop(k, None)
    else:
        _EFFECTIVE_CACHE.clear()

def get_effective_schedule(month: str = "2026-10", reference_today: str = REFERENCE_TODAY) -> Dict[str, Any]:
    """
    Computes the Effective Schedule:
    Effective Schedule = Baseline (Layer 1) + Assignments (Layer 2) + ⓒ Overlay (Layer 3).
    Cached in-memory to provide sub-second page loads and rapid state updates.
    """
    cache_key = f"{month}_{reference_today}"
    if cache_key in _EFFECTIVE_CACHE:
        return _EFFECTIVE_CACHE[cache_key]
    """
    Computes the Effective Schedule:
    Effective Schedule = Baseline (Layer 1) + Assignments (Layer 2) + ⓒ Overlay (Layer 3).
    Also computes:
    - Zero-partiality Attention Required records (including deleted class shortfalls)
    - Past/deleted class resolution queue (Options i, ii, iii)
    - Output 4 Coach Classes Taken So Far (up to reference_today)
    - Output 5 Student Actual Planned Schedule vs. Actual Attended Classes (with color diff summary)
    - Strict .ics Calendar eligibility gates for both students and coaches
    """
    from app.storage.database import init_db
    init_db()
    seed_october_baseline_if_missing()
    ensure_rolling_three_months_seeded("2026-10")

    active_base = get_active_baseline_db(month)
    if not active_base and month >= "2026-10":
        ensure_rolling_three_months_seeded(month)
        active_base = get_active_baseline_db(month)

    master_data = load_master_data_db()
    master_students_list = master_data.get("students", [])
    master_coaches = master_data.get("coaches", [])
    batches_data = master_data.get("batches", [])

    active_base_students = active_base.get("students_data", []) if active_base else []
    master_students_map = {s["student_id"]: dict(s) for s in master_students_list if s.get("student_id")}

    base_students_map = {}
    for s in active_base_students:
        sid = s.get("student_id")
        if not sid:
            continue
        # Exclude students explicitly removed/deleted from master data hub
        if master_students_map and sid not in master_students_map:
            continue
        s_merged = dict(s)
        if sid in master_students_map:
            ms = master_students_map[sid]
            for k in [
                "student_name", "student_level", "batch_type", "batch", "batch_name", "batch_code",
                "required_classes", "preferred_times", "preferred_coach", "availability",
                "is_morning_available", "mon_pref", "tue_pref", "wed_pref", "thu_pref",
                "fri_pref", "sat_pref", "sun_pref", "level_history", "requirement_exception",
                "notes", "is_active", "assigned_batch_id"
            ]:
                if k in ms and ms[k] is not None:
                    s_merged[k] = ms[k]
        if s_merged.get("is_active", True) is not False:
            base_students_map[sid] = s_merged

    # Unconditionally include all active students from Master Data Hub (single or bulk additions of 50-150 students)
    for ms in master_students_list:
        msid = ms.get("student_id")
        if msid and msid not in base_students_map and ms.get("is_active", True) is not False:
            base_students_map[msid] = dict(ms)

    base_students = list(base_students_map.values())

    # Discover batches from active baseline students if not present in batches_data
    known_batch_ids = {b.get("batch_id") or b.get("batch_name") for b in batches_data}
    discovered_batches = []
    for s in base_students:
        b_name = s.get("batch_code") or s.get("batch") or s.get("batch_name")
        if b_name and b_name not in known_batch_ids:
            known_batch_ids.add(b_name)
            discovered_batches.append({
                "batch_id": b_name,
                "batch_name": b_name,
                "batch_type": s.get("batch_type", "G"),
                "student_level": s.get("student_level", "Beginner 1"),
                "student_ids": [s["student_id"]]
            })
    if discovered_batches:
        batches_data = list(batches_data) + discovered_batches

    # Map every student to their official Batch Code (GB1-01..IIM2-01)
    student_batch_code_map = {}
    for b in batches_data:
        b_code = b.get("batch_id") or b.get("batch_name", "")
        for sid in b.get("student_ids", []):
            student_batch_code_map[sid] = b_code
    for s in base_students:
        sid = s["student_id"]
        b_code = student_batch_code_map.get(sid) or s.get("batch") or s.get("batch_code") or s.get("batch_name") or s.get("assigned_batch_id") or f"{s.get('batch_type', 'G')}B1-01"
        s["batch"] = b_code
        s["batch_name"] = b_code
        s["batch_code"] = b_code
        student_batch_code_map[sid] = b_code

    master_student_ids = {s["student_id"] for s in base_students}
    student_name_map = {s["student_id"]: s.get("student_name", s["student_id"]) for s in base_students}
    student_name_to_id_map = {str(s.get("student_name", "")).strip().lower(): s["student_id"] for s in base_students if s.get("student_name")}
    student_quota_map = {s["student_id"]: s.get("required_classes", 12) for s in base_students}
    student_rating_map = {s["student_id"]: (s.get("mkca_rating") if s.get("mkca_rating") is not None else "-") for s in base_students}

    base_classes = [dict(c) for c in active_base.get("classes_data", [])] if active_base else []

    # Track original baseline classes per student for Output 5 Actual Planned Schedule vs Attendance comparison
    planned_baseline_classes_by_student = defaultdict(list)

    effective_classes_map = {}
    for c in base_classes:
        c_copy = dict(c)
        resolved_sids = []
        for sid in c_copy.get("student_ids", []):
            if sid in master_student_ids:
                resolved_sids.append(sid)
            else:
                mapped = student_name_to_id_map.get(str(sid).strip().lower())
                if mapped and mapped in master_student_ids:
                    resolved_sids.append(mapped)
        if not resolved_sids and c_copy.get("student_names"):
            for sname in c_copy["student_names"]:
                mapped = student_name_to_id_map.get(str(sname).strip().lower())
                if mapped and mapped in master_student_ids and mapped not in resolved_sids:
                    resolved_sids.append(mapped)
        c_copy["student_ids"] = resolved_sids
        c_copy["student_names"] = [student_name_map.get(sid, sid) for sid in c_copy["student_ids"]]
        c_copy["student_batch_codes"] = [student_batch_code_map.get(sid, c_copy.get("batch_name", "")) for sid in c_copy["student_ids"]]
        if c_copy["student_batch_codes"]:
            c_copy["batch_name"] = Counter(c_copy["student_batch_codes"]).most_common(1)[0][0]
            c_copy["batch_code"] = c_copy["batch_name"]
        c_copy["is_baseline"] = True
        c_copy["is_compensation"] = False
        c_copy["has_compensation"] = False
        c_copy["is_approved_allocation"] = False
        c_copy["approved_student_ids"] = []
        c_copy["exception_metadata"] = None
        c_st = (c_copy.get("time_slot") or "").split("-")[0].strip()
        c_co = resolve_coach_canonical_name(c_copy.get("coach_name", ""))
        key = f"{c_copy.get('date')}||{c_st}||{c_co}"
        effective_classes_map[key] = c_copy
        for sid in c_copy["student_ids"]:
            planned_baseline_classes_by_student[sid].append(dict(c_copy))

    active_exceptions = get_exception_records_db(month, status="active")

    # Track deleted class records and zero-partiality student shortfalls
    deleted_past_classes = []
    deleted_sessions_owed = defaultdict(int)
    deleted_class_reasons = defaultdict(list)
    waived_attendance_only_sids = defaultdict(int)

    for exc in active_exceptions:
        action = exc.get("action_type")
        key = exc.get("class_key")
        c_date = exc.get("date")
        s_time = exc.get("start_time")
        c_coach = resolve_coach_canonical_name(exc.get("coach_id"))
        s_time_clean = (s_time or "").split("-")[0].strip()
        full_key = f"{c_date}||{s_time_clean}||{c_coach}"

        before_cls_id = exc.get("class_id") or exc.get("before", {}).get("class_id")
        affected_sids = [sid for sid in exc.get("affected_student_ids", []) if sid in master_student_ids]

        def _matches(k, c):
            if k == full_key or k == key:
                return True
            if before_cls_id and c.get("class_id") == before_cls_id:
                return True
            c_st = (c.get("time_slot") or "").split("-")[0].strip()
            c_co = resolve_coach_canonical_name(c.get("coach_name", ""))
            if c.get("date") == c_date and c_co == c_coach and (not s_time_clean or c_st == s_time_clean):
                return True
            if not s_time_clean and c.get("date") == c_date and c_co == c_coach and affected_sids and any(sid in c.get("student_ids", []) for sid in affected_sids):
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
            del_keys = [k for k, c in list(effective_classes_map.items()) if _matches(k, c)]
            removed_cls_snapshot = exc.get("before") or {}
            for dk in del_keys:
                popped = effective_classes_map.pop(dk, None)
                if popped and not removed_cls_snapshot:
                    removed_cls_snapshot = popped
            if not affected_sids and removed_cls_snapshot.get("student_ids"):
                affected_sids = [sid for sid in removed_cls_snapshot["student_ids"] if sid in master_student_ids]

            res_choice = (exc.get("after") or {}).get("resolution_choice", "pending")
            b_code = removed_cls_snapshot.get("batch_name") or (student_batch_code_map.get(affected_sids[0], "Batch") if affected_sids else "Batch")
            deleted_past_classes.append({
                "exception_id": exc["id"],
                "class_id": before_cls_id or removed_cls_snapshot.get("class_id", ""),
                "date": c_date,
                "day": removed_cls_snapshot.get("day") or (datetime.strptime(c_date, "%Y-%m-%d").strftime("%A") if c_date else ""),
                "time_slot": s_time,
                "coach_name": c_coach,
                "batch_name": b_code,
                "student_level": removed_cls_snapshot.get("student_level", "Beginner 1"),
                "batch_type": removed_cls_snapshot.get("batch_type", "G"),
                "affected_student_ids": affected_sids,
                "affected_student_names": [student_name_map.get(sid, sid) for sid in affected_sids],
                "is_past_date": bool(c_date and c_date <= reference_today),
                "resolution_choice": res_choice,
                "reason": exc.get("reason", "Class deleted by Administrator"),
                "created_at": exc.get("created_at", "")
            })

            # Zero-partiality rule: unless Admin explicitly waived make-up via Option (ii) or (iii),
            # every single student in the deleted class is flagged in Attention Required!
            if res_choice in ("pending", "compensate_future", None):
                for sid in affected_sids:
                    deleted_sessions_owed[sid] += 1
                    deleted_class_reasons[sid].append(f"{c_date} {s_time} ({c_coach} · {b_code})")
            else:
                for sid in affected_sids:
                    waived_attendance_only_sids[sid] += 1

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
                first_bcode = student_batch_code_map.get(affected_sids[0], "GBN1-01") if affected_sids else "GBN1-01"
                target_cls = {
                    "class_id": before_cls_id or f"CLS_{exc['id']}",
                    "date": c_date,
                    "time_slot": s_time,
                    "coach_name": c_coach,
                    "student_ids": affected_sids,
                    "student_names": [student_name_map.get(sid, sid) for sid in affected_sids],
                    "student_level": exc.get("after", {}).get("student_level", "Beginner 1"),
                    "batch_type": exc.get("after", {}).get("batch_type", "G"),
                    "batch_name": exc.get("after", {}).get("batch_name") or first_bcode,
                    "batch_code": exc.get("after", {}).get("batch_name") or first_bcode,
                    "warnings": []
                }

            after_fields = exc.get("after", {})
            if "coach_name" in after_fields: target_cls["coach_name"] = resolve_coach_canonical_name(after_fields["coach_name"])
            if "date" in after_fields: target_cls["date"] = after_fields["date"]
            if "time_slot" in after_fields: target_cls["time_slot"] = after_fields["time_slot"]
            if "student_level" in after_fields: target_cls["student_level"] = after_fields["student_level"]
            if "batch_type" in after_fields: target_cls["batch_type"] = after_fields["batch_type"]
            if "batch_name" in after_fields and after_fields["batch_name"]:
                target_cls["batch_name"] = after_fields["batch_name"]
                target_cls["batch_code"] = after_fields["batch_name"]
            if "student_ids" in after_fields:
                before_set = set(target_cls.get("student_ids", []))
                new_sids = [sid for sid in after_fields["student_ids"] if sid in master_student_ids]
                for r_sid in (before_set - set(new_sids)):
                    deleted_sessions_owed[r_sid] += 1
                    deleted_class_reasons[r_sid].append(f"Removed from {c_date} {s_time} ({c_coach})")
                target_cls["student_ids"] = new_sids
                target_cls["student_names"] = [student_name_map.get(sid, sid) for sid in new_sids]

            target_cls["is_compensation"] = True
            target_cls["has_compensation"] = True
            target_cls["is_manual_override"] = True
            target_cls["exception_metadata"] = exc_meta

            t_st = (target_cls.get("time_slot") or "").split("-")[0].strip()
            new_key = f"{target_cls.get('date')}||{t_st}||{resolve_coach_canonical_name(target_cls.get('coach_name', ''))}"
            effective_classes_map[new_key] = target_cls

        elif action == "add":
            after_fields = exc.get("after", {})
            s_ids = [sid for sid in (exc.get("affected_student_ids") or after_fields.get("student_ids", [])) if sid in master_student_ids]
            s_names = [student_name_map.get(sid, sid) for sid in s_ids]
            lvl = after_fields.get("student_level", "Beginner 1")
            b_type = after_fields.get("batch_type", "G")
            default_bcode = student_batch_code_map.get(s_ids[0], f"{b_type}B1-01") if s_ids else f"{b_type}B1-01"
            b_name = after_fields.get("batch_name") or default_bcode
            is_comp = (exc.get("subtype") != "normal_assignment")
            for sid in s_ids:
                if deleted_sessions_owed.get(sid, 0) > 0:
                    deleted_sessions_owed[sid] = max(0, deleted_sessions_owed[sid] - 1)
            new_cls = {
                "class_id": f"CLS_{exc['id']}",
                "date": c_date,
                "day": after_fields.get("day", ""),
                "time_slot": s_time,
                "coach_name": c_coach,
                "student_level": lvl,
                "batch_type": b_type,
                "batch_name": b_name,
                "batch_code": b_name,
                "student_ids": s_ids,
                "student_names": s_names,
                "warnings": ["Manual class (ⓒ)"] if is_comp else [],
                "is_baseline": False,
                "is_compensation": is_comp,
                "has_compensation": is_comp,
                "is_manual_override": is_comp,
                "is_approved_allocation": True,
                "approved_student_ids": list(s_ids),
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
                if "approved_student_ids" not in target_cls:
                    target_cls["approved_student_ids"] = []
                for sid in affected_sids:
                    if action == "add_student":
                        if sid not in s_ids:
                            s_ids.append(sid)
                        if sid not in target_cls["approved_student_ids"]:
                            target_cls["approved_student_ids"].append(sid)
                        target_cls["is_approved_allocation"] = True
                        if deleted_sessions_owed.get(sid, 0) > 0:
                            deleted_sessions_owed[sid] = max(0, deleted_sessions_owed[sid] - 1)
                    elif action == "remove_student" and sid in s_ids:
                        s_ids.remove(sid)
                        if sid in target_cls.get("approved_student_ids", []):
                            target_cls["approved_student_ids"].remove(sid)
                        res_choice = (exc.get("after") or {}).get("resolution_choice", "pending")
                        if res_choice in ("pending", "compensate_future", None):
                            deleted_sessions_owed[sid] += 1
                            deleted_class_reasons[sid].append(f"Removed from {c_date} {s_time} ({c_coach})")
                        else:
                            waived_attendance_only_sids[sid] += 1
                target_cls["student_ids"] = s_ids
                target_cls["student_names"] = [student_name_map.get(sid, sid) for sid in s_ids]
                is_comp = (exc.get("subtype") != "normal_assignment")
                if is_comp:
                    target_cls["is_compensation"] = True
                    target_cls["has_compensation"] = True
                    target_cls["is_manual_override"] = True
                target_cls["exception_metadata"] = exc_meta

    effective_classes = list(effective_classes_map.values())

    # Enrich every class with exact Batch Code (GB1-01..IIM2-01), student_batch_codes, and tournament flags
    for c in effective_classes:
        c_date = c.get("date", "")
        if c_date and not c.get("day"):
            try:
                c["day"] = datetime.strptime(c_date, "%Y-%m-%d").strftime("%A")
            except Exception:
                c["day"] = "Monday"

        s_ids = c.get("student_ids", [])
        s_names = [student_name_map.get(sid, sid) for sid in s_ids]
        c["student_names"] = s_names
        c["student_count"] = len(s_ids)
        s_bcodes = [student_batch_code_map.get(sid, c.get("batch_name", "GBN1-01")) for sid in s_ids]
        c["student_batch_codes"] = s_bcodes

        # Ensure batch_name is always the official Batch Code (e.g. IBN2-01 for Vedh Pabba)
        cur_bname = str(c.get("batch_name") or "")
        if s_bcodes and (not cur_bname or " - " in cur_bname or cur_bname in ("G", "L", "I", "Batch")):
            c["batch_name"] = Counter(s_bcodes).most_common(1)[0][0]
        c["batch_code"] = c.get("batch_name") or (s_bcodes[0] if s_bcodes else "GBN1-01")

        if s_names and s_ids:
            c["students_formatted"] = " · ".join([f"{name} ({sid} · {bc})" for name, sid, bc in zip(s_names, s_ids, s_bcodes)])
        else:
            c["students_formatted"] = "Open / Unassigned"

        day_name = c.get("day", "")
        lvl = c.get("student_level", "")
        b_type = c.get("batch_type", "G")
        is_tourn = False
        tourn_label = ""
        if day_name == "Sunday":
            if b_type != "I" and lvl not in ["Basic 1", "Intermediate 2"]:
                is_tourn = True
                tourn_label = "Sunday Tournament"
        elif day_name == "Friday":
            if lvl == "Intermediate 2" and b_type != "I":
                is_tourn = True
                tourn_label = "Friday Tournament (Int 2)"

        c["is_tournament"] = is_tourn
        c["tournament_label"] = tourn_label

    def _sort_key(cls_obj):
        dt = cls_obj.get("date", "9999-99-99")
        tm = parse_time_to_minutes(cls_obj.get("time_slot", "")) or 9999
        return (dt, tm, cls_obj.get("coach_name", ""))

    effective_classes.sort(key=_sort_key)

    # --------------------------------------------------------------------------
    # COMPUTE OUTPUTS, ZERO-PARTIALITY ATTENTION RECORDS & METRICS
    # --------------------------------------------------------------------------
    student_scheduled_counts = defaultdict(int)
    for c in effective_classes:
        for sid in c.get("student_ids", []):
            student_scheduled_counts[sid] += 1

    attention_records = []
    attention_student_ids = set()
    fully_scheduled_count = 0

    for s in base_students:
        sid = s["student_id"]
        sname = s.get("student_name", sid)
        b_code = student_batch_code_map.get(sid, s.get("batch", ""))
        raw_req = s.get("required_classes", 12)
        req = max(0, raw_req - waived_attendance_only_sids.get(sid, 0))
        sch = student_scheduled_counts.get(sid, 0)
        owed_from_deletion = deleted_sessions_owed.get(sid, 0)

        # ZERO PARTIALITY: If a class was deleted for this student, they MUST appear in Attention Required
        # even if they previously had an extra/compensation class!
        rem = max(0, req - sch, owed_from_deletion)

        # Check for mid-month joining date and calculate shortfall through end of month
        joining_date_val = str(s.get("joining_date") or s.get("start_date") or s.get("date_of_joining") or "").strip()
        is_mid_month = False
        mid_month_note = ""
        shortfall_val = 0
        if joining_date_val and joining_date_val.startswith(month):
            try:
                j_day = int(joining_date_val.split("-")[2])
                if j_day > 1:
                    is_mid_month = True
                    yr_v, mo_v = map(int, month.split("-"))
                    _, days_in_mo = calendar.monthrange(yr_v, mo_v)
                    days_remaining = max(0, days_in_mo - j_day + 1)
                    if rem > days_remaining:
                        shortfall_val = rem - days_remaining
                        mid_month_note = f"Joined mid-month ({joining_date_val}). Only {days_remaining} feasible day(s) remain in month (shortfall of {shortfall_val} vs {raw_req} monthly quota)."
            except Exception:
                pass

        if (raw_req > 0 and rem > 0) or owed_from_deletion > 0:
            attention_student_ids.add(sid)
            if owed_from_deletion > 0:
                del_info = ", ".join(deleted_class_reasons[sid][:2])
                reason = f"Class deleted/removed ({del_info}). Needs administrator action or make-up assignment ({sch}/{req} active classes)."
            elif sch == 0:
                if is_mid_month and mid_month_note:
                    reason = f"New mid-month joiner. Needs {rem} class assignments. {mid_month_note}"
                else:
                    reason = f"Unscheduled. Needs {rem} class assignments to meet monthly requirement."
            else:
                if is_mid_month and mid_month_note:
                    reason = f"Partially scheduled ({sch}/{req} classes). {mid_month_note}"
                else:
                    reason = f"Partially scheduled ({sch}/{req} classes). Shortfall of {rem} class session(s)."

            pref_days = [
                f"{d[:3]}"
                for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                if str(s.get(f"{d[:3].lower()}_pref", "No Preference")).lower() not in ["not available", "na", "no", "off"]
            ]

            lvl_val = s.get("student_level", "Beginner 1")
            btype_val = s.get("batch_type", "G")
            is_sunday_tourn_eligible = (btype_val != "I" and lvl_val not in ["Basic 1", "Intermediate 2"])
            if is_sunday_tourn_eligible:
                tourn_requirement = "Sunday Tournament Eligible: Basic 2 to Intermediate 1 (Group & Limited). Operating hours: 09:00 AM – 02:30 PM (cap 20)."
            elif btype_val == "I":
                tourn_requirement = "Individual Batch (Private 1-on-1): Ineligible for Sunday tournaments. Regular 1-on-1 class scheduling applies."
            elif lvl_val == "Basic 1":
                tourn_requirement = "Basic 1 Student: Ineligible for Sunday tournaments. Regular Basic 1 class scheduling applies (no mixing with Basic 2)."
            elif lvl_val == "Intermediate 2":
                tourn_requirement = "Intermediate 2 Student: Ineligible for Sunday tournaments (Friday Tournament only)."
            else:
                tourn_requirement = "Regular class scheduling."

            attention_records.append({
                "student_id": sid,
                "student_name": sname,
                "student_level": s.get("student_level", "Beginner 1"),
                "joining_date": joining_date_val,
                "date_of_joining": joining_date_val,
                "monthly_quota": raw_req,
                "quota": raw_req,
                "batch_eligibility": s.get("batch_type", "G"),
                "batch_type": s.get("batch_type", "G"),
                "batch_name": b_code,
                "batch_code": b_code,
                "required_classes": req,
                "scheduled_classes": sch,
                "remaining_classes": rem,
                "had_deleted_class": owed_from_deletion > 0,
                "deleted_class_details": deleted_class_reasons.get(sid, []),
                "is_mid_month": is_mid_month,
                "shortfall": shortfall_val,
                "shortfall_info": mid_month_note,
                "failure_reason": reason,
                "sunday_tournament_eligible": is_sunday_tourn_eligible,
                "tournament_requirement": tourn_requirement,
                "preferred_days": ", ".join(pref_days) if pref_days else "Flexible",
                "preferred_time": (s.get("preferred_times") or ["Flexible"])[0] if s.get("preferred_times") else "Flexible",
                "preferred_timings": s.get("preferred_timings") or (", ".join(s.get("preferred_times", [])) if s.get("preferred_times") else "Flexible"),
                "preferred_times": s.get("preferred_times") or [],
                "preferred_coach": s.get("preferred_coach") or "",
                "availability": s.get("availability") or {},
                "is_morning_available": bool(s.get("is_morning_available", False)),
                "details": f"Needs {rem} more class(es) in Batch {b_code}" + (f" ({mid_month_note})" if mid_month_note else "")
            })
        else:
            fully_scheduled_count += 1

    # Check for classes assigned to a deleted/unavailable coach (Rule 4)
    master_coaches = master_data.get("coaches", [])
    active_coach_names = {resolve_coach_canonical_name(c.get("coach_name", "")).lower() for c in master_coaches} if master_coaches else {c.lower() for c in COACH_REFERENCE.keys()}
    coaches_with_issues = set()

    from app.engine.time_utils import is_slot_in_coach_preference
    try:
        from app.main import CURRENT_CONFIG
        prio_matrix = getattr(CURRENT_CONFIG, "coach_priority", {}) or {}
    except Exception:
        prio_matrix = {}

    for c in effective_classes:
        c_coach = resolve_coach_canonical_name(c.get("coach_name", ""))
        c_date = c.get("date", "")
        # Preserve completed-class history and existing baseline schedules:
        # Never flag past classes (date <= reference_today) as issues requiring attention!
        if c_date and c_date <= reference_today:
            continue

        if c_coach and c_coach.lower() not in active_coach_names and c_coach.lower() != "unassigned":
            coaches_with_issues.add(c_coach)
            c["needs_coach_reassignment"] = True
            c["original_deleted_coach"] = c_coach
            lvl = c.get("student_level", "Beginner 1")
            b_name = c.get("batch_name") or c.get("batch_code", "Batch")
            b_type = c.get("batch_type", "G")
            t_slot = c.get("time_slot", "")
            day_name = c.get("day", "")
            c_sids = c.get("student_ids", [])
            c_snames = c.get("student_names", [])

            # Rule 4 Engine Suggestion: Match replacement coach meeting:
            # 1. Batch level teaching criteria
            # 2. Batch preference time
            # 3. Coach preference timing
            # 4. Zero schedule conflict at that date/slot
            # 5. Live priority matrix order
            ranked_replacements = []
            coach_rank_order = prio_matrix.get(lvl, [])

            for mc in master_coaches:
                mc_name = resolve_coach_canonical_name(mc.get("coach_name", ""))
                if not mc_name or mc_name.lower() in [c_coach.lower(), "unassigned"]:
                    continue
                mc_lvls = mc.get("levels_handled") or mc.get("levels") or []
                if lvl not in mc_lvls:
                    continue
                if mc.get("tournament_role") == "Tournament only" or mc.get("tournaments_only"):
                    continue
                if mc_name in ["BATHRI", "Bathri"] and "Early Intermediate" in lvl:
                    continue

                # Check coach preference timing
                slot_ok, _ = is_slot_in_coach_preference(mc, day_name, t_slot)
                if not slot_ok:
                    continue

                # Check coach overlap on same date and time slot
                has_conflict = False
                for other_c in effective_classes:
                    if other_c.get("class_id") == c.get("class_id"):
                        continue
                    if other_c.get("date") == c_date and other_c.get("time_slot") == t_slot:
                        if resolve_coach_canonical_name(other_c.get("coach_name", "")).lower() == mc_name.lower():
                            has_conflict = True
                            break
                if has_conflict:
                    continue

                rank = coach_rank_order.index(mc_name) + 1 if mc_name in coach_rank_order else 99
                ranked_replacements.append({
                    "coach_name": mc_name,
                    "priority_rank": rank,
                    "matches_timing": True,
                    "matches_level": True,
                    "is_recommended": False
                })

            ranked_replacements.sort(key=lambda x: (x["priority_rank"], x["coach_name"]))
            if ranked_replacements:
                ranked_replacements[0]["is_recommended"] = True

            rec_coach = ranked_replacements[0]["coach_name"] if ranked_replacements else "Any qualified coach"
            suggs = [r["coach_name"] for r in ranked_replacements[:3]]

            attention_records.append({
                "record_type": "coach_reassignment",
                "class_id": c.get("class_id"),
                "student_id": c_sids[0] if c_sids else "N/A",
                "student_ids": c_sids,
                "student_name": f"Batch: {b_name} ({len(c_sids)} Students)",
                "student_names": c_snames,
                "student_level": lvl,
                "batch_type": b_type,
                "batch_name": b_name,
                "batch_code": b_name,
                "date": c_date,
                "day": day_name,
                "time_slot": t_slot,
                "deleted_coach_name": c_coach,
                "needs_coach_reassignment": True,
                "required_classes": len(c_sids),
                "scheduled_classes": 0,
                "remaining_classes": len(c_sids),
                "failure_reason": f"Coach {c_coach} was deleted. Reassignment required for batch {b_name} on {c_date} ({day_name[:3]}) at {t_slot}.",
                "preferred_days": day_name,
                "preferred_time": t_slot,
                "suggested_coaches": ranked_replacements,
                "recommended_coach": rec_coach,
                "details": f"Engine Recommended Coach: {rec_coach} (Rank #{ranked_replacements[0]['priority_rank'] if ranked_replacements else 'N/A'}, qualified for {lvl}, free at {t_slot})." if ranked_replacements else "No conflict-free coach available at this exact slot."
            })

    # Output 1: Coach WhatsApp Communication Schedule
    coach_slot_map = defaultdict(lambda: defaultdict(list))
    for c in effective_classes:
        c_name = c.get("coach_name", "")
        if c_name and c_name != "Unassigned":
            c_canon = resolve_coach_canonical_name(c_name)
            slot_key = (c.get("date"), c.get("day"), c.get("time_slot"))
            c_tag = " [ⓒ]" if c.get("is_compensation") else ""
            t_tag = " [Tournament]" if c.get("is_tournament") else ""
            summary_str = f"{c.get('batch_name', 'Batch')}{c_tag}{t_tag}: {c.get('students_formatted', '')}"
            coach_slot_map[slot_key][c_canon].append(summary_str)

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
            "batches_summary": dict(coaches_dict),
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
        for c_canon in coach_names_list:
            for b_detail in coaches_dict[c_canon]:
                lines.append(f"   • {c_canon} [{b_detail}]")

    whatsapp_text = "\n".join(lines)

    # Output 4: Coach Workload & Classes Taken So Far Tracker
    coach_classes_count = defaultdict(int)
    coach_student_reach = defaultdict(int)
    coach_dates_map = defaultdict(lambda: defaultdict(int))
    coach_completed_classes_map = defaultdict(list)

    for c in effective_classes:
        c_name = c.get("coach_name", "")
        if c_name and c_name != "Unassigned":
            c_canon = resolve_coach_canonical_name(c_name)
            coach_classes_count[c_canon] += 1
            coach_student_reach[c_canon] += len(c.get("student_ids", []))
            coach_dates_map[c_canon][c.get("date")] += 1

            # Classes Taken So Far: only include classes whose date <= reference_today (never future dates/months)
            c_dt = c.get("date", "")
            if c_dt and c_dt <= reference_today:
                coach_completed_classes_map[c_canon].append({
                    "class_id": c.get("class_id"),
                    "date": c_dt,
                    "day": c.get("day", ""),
                    "time_slot": c.get("time_slot", ""),
                    "batch_name": c.get("batch_name") or c.get("batch_code", ""),
                    "batch_type": c.get("batch_type", "G"),
                    "student_level": c.get("student_level", ""),
                    "student_ids": c.get("student_ids", []),
                    "student_names": c.get("student_names", []),
                    "students_formatted": c.get("students_formatted", ""),
                    "is_compensation": bool(c.get("is_compensation")),
                    "is_tournament": bool(c.get("is_tournament"))
                })

    all_coaches_dict = {}
    for c_canon, c_ref in COACH_REFERENCE.items():
        all_coaches_dict[c_canon] = dict(c_ref)
    for mc in master_coaches:
        mc_canon = resolve_coach_canonical_name(mc.get("coach_name", ""))
        if mc_canon:
            base_c = dict(all_coaches_dict.get(mc_canon, {}))
            if mc.get("levels_handled") is not None:
                base_c["levels"] = mc["levels_handled"]
            if mc.get("monthly_capacity_max") is not None:
                base_c["monthly_max"] = mc["monthly_capacity_max"]
            if mc.get("monthly_capacity_min") is not None:
                base_c["monthly_min"] = mc["monthly_capacity_min"]
            if "is_flex" in mc:
                base_c["is_flex"] = bool(mc["is_flex"])
            base_c["joined_month"] = mc.get("joined_month", "2026-10")
            base_c["is_new_coach"] = (mc_canon not in COACH_REFERENCE)
            all_coaches_dict[mc_canon] = base_c

    # Preserve any coach who has scheduled or completed classes in effective_classes
    for c in effective_classes:
        c_co = resolve_coach_canonical_name(c.get("coach_name", ""))
        if c_co and c_co not in all_coaches_dict and c_co != "Unassigned":
            all_coaches_dict[c_co] = {
                "coach_name": c_co,
                "levels": [c.get("student_level", "Beginner 1")],
                "monthly_max": 100,
                "monthly_min": 0,
                "is_flex": False,
                "is_archived": True
            }

    # Check if any pending deleted past class belongs to a coach
    pending_deleted_coaches = {
        resolve_coach_canonical_name(dpc.get("coach_name", ""))
        for dpc in deleted_past_classes if dpc.get("resolution_choice") == "pending"
    }

    coach_summaries = []
    for c_canon, c_ref in all_coaches_dict.items():
        actual_classes = coach_classes_count[c_canon]
        reach = coach_student_reach[c_canon]
        m_max = c_ref.get("monthly_max")
        is_flex = c_ref.get("is_flex", False)
        
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
        comp_so_far = coach_completed_classes_map.get(c_canon, [])
        has_issue = (c_canon in coaches_with_issues) or (c_canon in pending_deleted_coaches) or (status == "Capacity Exceeded" and not is_flex)

        # Distinguish scheduled, approved, and completed classes:
        completed_cnt = len(comp_so_far)
        approved_cnt = sum(1 for c in effective_classes if resolve_coach_canonical_name(c.get("coach_name", "")) == c_canon and (c.get("is_approved_allocation") or c.get("is_compensation")))
        future_scheduled_cnt = sum(1 for c in effective_classes if resolve_coach_canonical_name(c.get("coach_name", "")) == c_canon and c.get("date", "") > reference_today and not (c.get("is_approved_allocation") or c.get("is_compensation")))

        coach_summaries.append({
            "coach_name": c_canon,
            "classes_scheduled": actual_classes,
            "assigned_classes": actual_classes,
            "scheduled_classes": actual_classes,
            "approved_allocations_count": approved_cnt,
            "completed_classes_count": completed_cnt,
            "future_scheduled_count": future_scheduled_cnt,
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
            "is_new_coach": bool(c_ref.get("is_new_coach", False)),
            "joined_month": c_ref.get("joined_month", "2026-10"),
            "is_workload_exception": is_workload_exception,
            "active_dates_count": len(coach_dates_map[c_canon]),
            "completed_classes_so_far": comp_so_far,
            "has_attention_issue": has_issue,
            "ics_unlocked": not has_issue
        })

    # Output 5: Student Schedules (1. Actual Planned Schedule vs 2. Actual Attended Classes So Far)
    student_classes_map = defaultdict(list)
    for c in effective_classes:
        for sid in c.get("student_ids", []):
            student_classes_map[sid].append(c)

    student_schedules = []
    for s in base_students:
        sid = s["student_id"]
        b_code = student_batch_code_map.get(sid, s.get("batch", ""))
        s_eff_cls = student_classes_map.get(sid, [])
        s_base_cls = planned_baseline_classes_by_student.get(sid, [])

        # 1. Actual Planned Schedule: baseline classes (or current effective regular classes if new student)
        planned_schedule_list = s_base_cls if s_base_cls else [c for c in s_eff_cls if not c.get("is_compensation")]

        # 2. Actual Attended Classes So Far: classes in effective_classes with date <= reference_today
        attended_so_far_list = [c for c in s_eff_cls if c.get("date", "") <= reference_today]
        attended_regular_cnt = sum(1 for c in attended_so_far_list if not c.get("is_compensation"))
        attended_comp_cnt = sum(1 for c in attended_so_far_list if c.get("is_compensation"))

        # Compute highlighted differences between Actual Planned Schedule and Actual Attended Classes
        differences = []
        eff_keys = {(c.get("date"), c.get("time_slot"), c.get("coach_name")) for c in s_eff_cls}
        for bc in s_base_cls:
            b_key = (bc.get("date"), bc.get("time_slot"), bc.get("coach_name"))
            if b_key not in eff_keys:
                differences.append({
                    "type": "missed_or_removed",
                    "badge": "Removed / Missed Planned Slot",
                    "date": bc.get("date"),
                    "day": bc.get("day"),
                    "time_slot": bc.get("time_slot"),
                    "coach_name": bc.get("coach_name"),
                    "batch_name": bc.get("batch_name", b_code),
                    "note": "Removed from original schedule"
                })
        for ec in s_eff_cls:
            if ec.get("is_compensation"):
                differences.append({
                    "type": "compensation_or_extra",
                    "badge": "ⓒ Compensation / Alternative Class",
                    "date": ec.get("date"),
                    "day": ec.get("day"),
                    "time_slot": ec.get("time_slot"),
                    "coach_name": ec.get("coach_name"),
                    "batch_name": ec.get("batch_name", b_code),
                    "note": (ec.get("exception_metadata") or {}).get("reason") or "Compensation / manual addition (ⓒ)"
                })

        has_stu_issue = (sid in attention_student_ids)
        approved_alloc_cnt = sum(1 for c in s_eff_cls if c.get("is_approved_allocation") or c.get("is_compensation"))
        completed_stu_cnt = len(attended_so_far_list)
        req_classes = s.get("required_classes", 12)
        rem_classes = max(0, req_classes - len(s_eff_cls))

        student_schedules.append({
            "student_id": sid,
            "student_name": s.get("student_name", sid),
            "student_level": s.get("student_level", "Beginner 1"),
            "batch_type": s.get("batch_type", "G"),
            "batch_name": b_code,
            "batch_code": b_code,
            "mkca_rating": student_rating_map.get(sid, "-"),
            "required_classes": req_classes,
            "monthly_quota": req_classes,
            "scheduled_classes_count": len(s_eff_cls),
            "completed_classes_count": completed_stu_cnt,
            "approved_allocations_count": approved_alloc_cnt,
            "remaining_quota": rem_classes,
            "classes": s_eff_cls,
            "actual_schedule_classes": planned_schedule_list,
            "actual_attended_classes": attended_so_far_list,
            "attendance_summary": {
                "reference_today": reference_today,
                "planned_total": req_classes,
                "scheduled_total": len(s_eff_cls),
                "total_attended_so_far": completed_stu_cnt,
                "attended_as_planned_count": attended_regular_cnt,
                "compensation_or_alt_count": attended_comp_cnt,
                "differences_count": len(differences),
                "differences": differences
            },
            "has_attention_issue": has_stu_issue,
            "ics_unlocked": not has_stu_issue
        })

    total_classes = len(effective_classes)
    total_student_seats = sum(len(c.get("student_ids", [])) for c in effective_classes)
    total_required = sum(s.get("required_classes", 12) for s in base_students if s.get("required_classes", 12) > 0)
    quotas_completed = round(sum(min(student_scheduled_counts[s["student_id"]], s.get("required_classes", 12)) for s in base_students if s.get("required_classes", 12) > 0) / max(1, total_required) * 100, 1)
    need_attention = len(attention_records)
    compensation_count = sum(1 for c in effective_classes if c.get("is_compensation"))

    total_batches = len(batches_data) if batches_data else len(set(c.get("batch_name", "") for c in effective_classes))
    g_batches = sum(1 for b in batches_data if b.get("batch_type") == "G")
    l_batches = sum(1 for b in batches_data if b.get("batch_type") == "L")
    i_batches = sum(1 for b in batches_data if b.get("batch_type") == "I")

    res = {
        "month": month,
        "reference_today": reference_today,
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
        "deleted_past_classes": deleted_past_classes,
        "coach_summaries": coach_summaries,
        "student_schedules": student_schedules,
        "whatsapp_plain_text": whatsapp_text
    }
    _EFFECTIVE_CACHE[cache_key] = res
    return res
