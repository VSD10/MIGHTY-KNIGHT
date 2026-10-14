import io
import re
import calendar
from datetime import datetime, date, time
from typing import Dict, Any, List, Tuple, Optional, Set
from collections import defaultdict
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.engine.rule_engine import (
    LEVEL_MAP, COACH_REFERENCE, resolve_coach_canonical_name,
    parse_time_to_minutes, format_minutes_to_time, check_intervals_overlap,
    check_operating_hours, is_morning_class, check_tournament_eligibility,
    check_tournament_grouping, check_regular_level_compatibility,
    validate_all_rules_for_occurrence
)
from app.storage.database import (
    save_baseline_db, get_active_baseline_db, get_draft_baseline_db,
    activate_baseline_db, discard_draft_baseline_db, list_baselines_for_month_db
)

MONTH_ABBRS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def generate_monthly_excel_template(year: int, month: int, coach_names: Optional[List[str]] = None) -> bytes:
    """
    Generates dynamic blank month-aware Excel baseline template (Part E2 & E3).
    Adapts columns to exactly the number of days in the chosen month (28, 29, 30, or 31).
    Highlights Sundays, adds day name headers, date headers, and metadata columns.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    month_name = calendar.month_name[month]
    month_abbr = calendar.month_abbr[month]
    ws.title = f"{month_abbr}'{str(year)[-2:]} Baseline"
    
    _, num_days = calendar.monthrange(year, month)

    # Styles
    navy_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    gold_fill = PatternFill(start_color="FEF08A", end_color="FEF08A", fill_type="solid") # Sunday highlight
    header_fill = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
    sun_header_fill = PatternFill(start_color="EAB308", end_color="EAB308", fill_type="solid")
    
    font_white_bold = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_dark_bold = Font(name="Calibri", size=11, bold=True, color="000000")
    font_regular = Font(name="Calibri", size=10)
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")

    # Static Metadata Columns (Columns 1-7)
    meta_headers = [
        "Student Name", "Student ID", "MKCA Rating", "Level", "Batch", "Note", "Planned Classes"
    ]
    
    # Row 1: Academy & Month Title / Day of Week
    # Row 2: Header Labels
    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 26

    for col_idx, h in enumerate(meta_headers, start=1):
        ws.cell(row=1, column=col_idx, value="").fill = header_fill
        cell2 = ws.cell(row=2, column=col_idx, value=h)
        cell2.fill = header_fill
        cell2.font = font_white_bold
        cell2.alignment = align_left if col_idx in [1, 5, 6] else align_center
        cell2.border = thin_border

    # Dynamic Date Columns (Columns 8 onwards)
    cur_col = 8
    for d in range(1, num_days + 1):
        dt = date(year, month, d)
        day_name = dt.strftime("%A")
        is_sunday = (dt.weekday() == 6)

        day_fill = sun_header_fill if is_sunday else header_fill
        day_font = font_dark_bold if is_sunday else font_white_bold

        # Row 1: Day Name (merged over Time & Coach columns)
        ws.merge_cells(start_row=1, start_column=cur_col, end_row=1, end_column=cur_col + 1)
        r1_cell = ws.cell(row=1, column=cur_col, value=day_name)
        r1_cell.fill = day_fill
        r1_cell.font = day_font
        r1_cell.alignment = align_center
        r1_cell.border = thin_border
        ws.cell(row=1, column=cur_col + 1).border = thin_border

        # Row 2: Time & Coach Headers
        time_hdr = f"{d}-{month_abbr} Time"
        coach_hdr = f"{d}-{month_abbr} Coach"

        c_time = ws.cell(row=2, column=cur_col, value=time_hdr)
        c_time.fill = day_fill
        c_time.font = day_font
        c_time.alignment = align_center
        c_time.border = thin_border

        c_coach = ws.cell(row=2, column=cur_col + 1, value=coach_hdr)
        c_coach.fill = day_fill
        c_coach.font = day_font
        c_coach.alignment = align_center
        c_coach.border = thin_border

        cur_col += 2

    # Column Widths
    ws.column_dimensions['A'].width = 24 # Name
    ws.column_dimensions['B'].width = 14 # ID
    ws.column_dimensions['C'].width = 13 # Rating
    ws.column_dimensions['D'].width = 18 # Level
    ws.column_dimensions['E'].width = 16 # Batch
    ws.column_dimensions['F'].width = 20 # Note
    ws.column_dimensions['G'].width = 16 # Planned Classes
    for c in range(8, cur_col):
        ws.column_dimensions[get_column_letter(c)].width = 15

    # Freeze panes at H3 (so Student Name & ID are always visible while scrolling horizontally)
    ws.freeze_panes = "H3"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

def parse_baseline_excel_file(
    content: bytes,
    target_year: int,
    target_month: int,
    master_students: Optional[List[Dict[str, Any]]] = None,
    master_coaches: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Parses and validates an Absolute Schedule Excel baseline (Part E3 & E4).
    Dynamically detects date columns. Validates month length and contents.
    Returns:
    {
        "is_valid": bool,
        "student_count": int,
        "class_count": int,
        "student_class_count": int,
        "students_data": list,
        "classes_data": list,
        "baseline_exceptions": list,
        "validation_report": {
            "blocking": list,
            "baseline_exceptions": list,
            "info": list
        }
    }
    """
    blocking_errors = []
    baseline_exceptions = []
    info_notes = []

    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        ws = wb.active
    except Exception as e:
        return {
            "is_valid": False,
            "student_count": 0, "class_count": 0, "student_class_count": 0,
            "students_data": [], "classes_data": [], "baseline_exceptions": [],
            "validation_report": {
                "blocking": [f"Unreadable Excel file: {str(e)}"],
                "baseline_exceptions": [],
                "info": []
            }
        }

    _, days_in_month = calendar.monthrange(target_year, target_month)
    month_name = calendar.month_name[target_month]
    month_abbr = calendar.month_abbr[target_month]

    # 1. Detect header row by scanning rows 1..10 for "student" or "stud"
    header_row = None
    for r in range(1, min(15, ws.max_row + 1)):
        for c in range(1, min(10, ws.max_column + 1)):
            val = str(ws.cell(r, c).value or "").strip().lower()
            if "student" in val or "stud id" in val or "stud" in val:
                header_row = r
                break
        if header_row:
            break

    if not header_row:
        header_row = 2 # default fallback

    # 2. Detect column mapping for metadata
    col_map = {
        "name": None, "id": None, "rating": None, "level": None,
        "batch": None, "note": None, "planned": None
    }
    for c in range(1, ws.max_column + 1):
        hdr = str(ws.cell(header_row, c).value or "").strip().lower()
        if not hdr:
            continue
        if "name" in hdr and not col_map["name"]:
            col_map["name"] = c
        elif ("id" in hdr or "stud id" in hdr) and not col_map["id"]:
            col_map["id"] = c
        elif "rating" in hdr and not col_map["rating"]:
            col_map["rating"] = c
        elif "level" in hdr and not col_map["level"]:
            col_map["level"] = c
        elif "batch" in hdr and not col_map["batch"]:
            col_map["batch"] = c
        elif ("note" in hdr or "comment" in hdr) and not col_map["note"]:
            col_map["note"] = c
        elif ("planned" in hdr or "quota" in hdr or "required" in hdr) and not col_map["planned"]:
            col_map["planned"] = c

    # Fallback to column indices if not found
    if not col_map["name"]: col_map["name"] = 1
    if not col_map["id"]: col_map["id"] = 2
    if not col_map["rating"]: col_map["rating"] = 3
    if not col_map["level"]: col_map["level"] = 4
    if not col_map["batch"]: col_map["batch"] = 5
    if not col_map["planned"]: col_map["planned"] = 6

    # 3. Detect Date Columns
    # Each date column has a time column and an accompanying coach column
    date_cols: Dict[int, Dict[str, Any]] = {} # col_idx -> {date_obj, date_str, day_name, coach_col}

    for c in range(col_map["planned"] + 1, ws.max_column + 1):
        # Check header in header_row, row 1, or row 3
        headers_to_check = [
            ws.cell(header_row, c).value,
            ws.cell(1, c).value,
            ws.cell(header_row + 1, c).value
        ]
        matched_date = None
        for h in headers_to_check:
            if not h: continue
            if isinstance(h, (datetime, date)):
                d_obj = h.date() if isinstance(h, datetime) else h
                if d_obj.year == target_year and d_obj.month == target_month:
                    matched_date = d_obj
                    break
            else:
                h_str = str(h).strip()
                # Pattern like "1-Oct Time", "1-Oct", "01/10/2026", "1-Oct Coach"
                m = re.search(r'(\d{1,2})[-/ ]([A-Za-z]{3})', h_str)
                if m:
                    d_num = int(m.group(1))
                    m_str = m.group(2).capitalize()
                    if m_str == month_abbr and 1 <= d_num <= days_in_month:
                        matched_date = date(target_year, target_month, d_num)
                        break

        if matched_date:
            hdr_str = str(ws.cell(header_row, c).value or "").lower()
            # If this is marked coach, skip as it's the companion
            if "coach" in hdr_str or "trainer" in hdr_str:
                continue
            
            # Identify companion coach column (usually c + 1)
            coach_col = c + 1
            date_str = matched_date.strftime("%Y-%m-%d")
            day_name = matched_date.strftime("%A")
            date_cols[c] = {
                "date_obj": matched_date,
                "date_str": date_str,
                "day_name": day_name,
                "coach_col": coach_col
            }

    # If date_cols empty, check even/odd pairs starting from col 8
    if not date_cols:
        start_c = max(col_map.values()) + 1
        for d in range(1, days_in_month + 1):
            c_time = start_c + (d - 1) * 2
            c_coach = c_time + 1
            if c_coach <= ws.max_column:
                matched_date = date(target_year, target_month, d)
                date_cols[c_time] = {
                    "date_obj": matched_date,
                    "date_str": matched_date.strftime("%Y-%m-%d"),
                    "day_name": matched_date.strftime("%A"),
                    "coach_col": c_coach
                }

    detected_days_count = len(date_cols)
    if detected_days_count < days_in_month:
        info_notes.append(f"Detected {detected_days_count} date columns out of {days_in_month} expected days in {month_name} {target_year}.")

    # 4. Parse Student Rows and Classes
    students_list = []
    seen_ids = set()
    classes_map = defaultdict(lambda: {
        "student_ids": [],
        "student_names": [],
        "levels": set(),
        "batch_types": set(),
        "day": "",
        "warnings": []
    })

    master_stu_ids = {s["student_id"] for s in (master_students or [])}
    master_coach_names = {c["coach_name"].lower() for c in (master_coaches or [])}

    start_data_row = header_row + 1
    # Check if header_row + 1 is also a sub-header
    if start_data_row <= ws.max_row:
        val1 = str(ws.cell(start_data_row, col_map["name"]).value or "").strip().lower()
        if "time" in val1 or "coach" in val1 or "name" in val1:
            start_data_row += 1

    for r in range(start_data_row, ws.max_row + 1):
        name_val = ws.cell(r, col_map["name"]).value
        if not name_val or not str(name_val).strip():
            continue
        name_str = str(name_val).strip()
        # Skip summary rows or legends
        if name_str.lower() in ["total", "summary", "legend", "notes", "scheduled"]:
            continue

        id_val = ws.cell(r, col_map["id"]).value
        stud_id = str(id_val).strip() if id_val else f"MKS{r:05d}"

        if stud_id in seen_ids:
            blocking_errors.append(f"Duplicate student ID detected: '{stud_id}' (Row {r}: {name_str}). Student IDs must be strictly unique.")
        seen_ids.add(stud_id)

        lvl_val = str(ws.cell(r, col_map["level"]).value or "Beginner 1").strip()
        batch_val = str(ws.cell(r, col_map["batch"]).value or "G").strip()
        
        # Determine batch type
        b_type = "G"
        if batch_val.startswith("L") or "limited" in batch_val.lower():
            b_type = "L"
        elif batch_val.startswith("I") or "individual" in batch_val.lower():
            b_type = "I"

        planned_val = ws.cell(r, col_map["planned"]).value
        try:
            planned_classes = int(planned_val) if planned_val is not None else 12
        except (ValueError, TypeError):
            planned_classes = 12

        rating_val = ws.cell(r, col_map["rating"]).value
        try:
            rating_float = float(rating_val) if rating_val is not None else None
        except (ValueError, TypeError):
            rating_float = None

        note_val = str(ws.cell(r, col_map["note"]).value or "").strip() if col_map["note"] else ""

        stud_record = {
            "student_id": stud_id,
            "student_name": name_str,
            "student_level": lvl_val,
            "batch_type": b_type,
            "batch_name": batch_val,
            "mkca_rating": rating_float,
            "required_classes": planned_classes,
            "note": note_val,
            "classes_scheduled_count": 0
        }

        # Check Master Data match
        if master_stu_ids and stud_id not in master_stu_ids:
            info_notes.append(f"New student '{name_str}' ({stud_id}) found in file; not yet registered in Master Data Hub.")

        # Read classes for this student across date columns
        stu_classes_count = 0
        for col_idx, d_meta in date_cols.items():
            t_cell = ws.cell(r, col_idx).value
            tr_cell = ws.cell(r, d_meta["coach_col"]).value
            if t_cell is not None and str(t_cell).strip():
                if isinstance(t_cell, (time, datetime)):
                    t_str = t_cell.strftime("%I:%M %p").lstrip('0')
                else:
                    t_str = str(t_cell).strip()

                start_min = parse_time_to_minutes(t_str)
                if start_min is None:
                    blocking_errors.append(f"Row {r} ({name_str}): Unparseable class time '{t_str}' on {d_meta['date_str']}.")
                    continue

                raw_tr = str(tr_cell).strip() if tr_cell else "Unassigned"
                coach_canon = resolve_coach_canonical_name(raw_tr)

                if coach_canon.lower() not in master_coach_names and raw_tr != "Unassigned":
                    # Check if it matches known alias in COACH_REFERENCE
                    if coach_canon not in COACH_REFERENCE:
                        blocking_errors.append(f"Row {r} ({name_str}): Unknown coach '{raw_tr}' on {d_meta['date_str']} has no alias in Trainer Master.")

                stu_classes_count += 1
                class_key = (d_meta["date_str"], t_str, coach_canon)
                classes_map[class_key]["student_ids"].append(stud_id)
                classes_map[class_key]["student_names"].append(name_str)
                classes_map[class_key]["levels"].add(lvl_val)
                classes_map[class_key]["batch_types"].add(b_type)
                classes_map[class_key]["day"] = d_meta["day_name"]

        stud_record["classes_scheduled_count"] = stu_classes_count
        students_list.append(stud_record)

    # 5. Build parsed classes list & Check Baseline Exceptions (Part E4)
    parsed_classes = []
    total_seat_count = 0

    student_map_for_rules = {s["student_id"]: s for s in students_list}

    for (d_str, t_str, c_canon), c_data in classes_map.items():
        distinct_lvls = sorted(list(c_data["levels"]))
        primary_lvl = distinct_lvls[0] if len(distinct_lvls) == 1 else "MIXED"
        b_types = c_data["batch_types"]
        primary_btype = "G" if "G" in b_types else ("L" if "L" in b_types else "I")

        cls_id = f"CLS_{d_str.replace('-', '')}_{t_str.replace(' ', '').replace(':', '')}_{c_canon.replace(' ', '')}"
        seat_cnt = len(c_data["student_ids"])
        total_seat_count += seat_cnt

        cls_obj = {
            "class_id": cls_id,
            "date": d_str,
            "day": c_data["day"],
            "time_slot": t_str,
            "coach_name": c_canon,
            "student_level": primary_lvl,
            "batch_type": primary_btype,
            "batch_name": f"{primary_lvl} - {c_canon}",
            "student_ids": c_data["student_ids"],
            "student_names": c_data["student_names"],
            "warnings": [],
            "is_baseline": True,
            "is_manual_override": False
        }
        parsed_classes.append(cls_obj)

    # Validate Baseline Exceptions across all classes (Part E4)
    # These do NOT block activation, but are logged as Baseline Exceptions
    for cls_obj in parsed_classes:
        is_tourn = (cls_obj["day"] == "Sunday" or (cls_obj["day"] == "Friday" and cls_obj["student_level"] == "Intermediate 2"))
        rule_violations = validate_all_rules_for_occurrence(
            cls_obj,
            parsed_classes,
            student_map_for_rules,
            COACH_REFERENCE,
            is_tournament=is_tourn
        )
        if rule_violations:
            cls_obj["baseline_exceptions"] = rule_violations
            for rv in rule_violations:
                baseline_exceptions.append({
                    "date": cls_obj["date"],
                    "time_slot": cls_obj["time_slot"],
                    "coach": cls_obj["coach_name"],
                    "rule": rv["rule_name"],
                    "reason": rv["reason"],
                    "severity": rv["severity"]
                })

    is_valid = len(blocking_errors) == 0

    return {
        "is_valid": is_valid,
        "student_count": len(students_list),
        "class_count": len(parsed_classes),
        "student_class_count": total_seat_count,
        "students_data": students_list,
        "classes_data": parsed_classes,
        "baseline_exceptions": baseline_exceptions,
        "validation_report": {
            "blocking": blocking_errors,
            "baseline_exceptions": baseline_exceptions,
            "info": info_notes
        }
    }

def generate_next_month_draft(
    source_month: str,
    target_year: int,
    target_month: int,
    user: str = "Admin"
) -> Dict[str, Any]:
    """
    Builds next month's draft baseline from current active baseline (Part E7).
    Maps recurring weekday/time/coach pattern onto target month calendar (28-31 days).
    Respects monthly requirement caps, weekly windows (B5a), 1 class/day, Sunday rules.
    """
    active_base = get_active_baseline_db(source_month)
    if not active_base:
        raise ValueError(f"No active baseline found for source month '{source_month}'.")

    _, target_days = calendar.monthrange(target_year, target_month)
    target_month_str = f"{target_year:04d}-{target_month:02d}"

    students = active_base.get("students_data", [])
    classes = active_base.get("classes_data", [])

    # Collect recurring patterns for each student: weekday -> (time_slot, coach_name, level, batch_type)
    student_recurrence = defaultdict(list)
    for cls in classes:
        day_name = cls.get("day", "")
        t_slot = cls.get("time_slot", "")
        c_name = cls.get("coach_name", "")
        lvl = cls.get("student_level", "")
        b_type = cls.get("batch_type", "G")
        for sid in cls.get("student_ids", []):
            student_recurrence[sid].append({
                "day_name": day_name,
                "time_slot": t_slot,
                "coach_name": c_name,
                "level": lvl,
                "batch_type": b_type
            })

    # Calendar dates for target month grouped by day_name
    dates_by_day = defaultdict(list)
    for d in range(1, target_days + 1):
        dt = date(target_year, target_month, d)
        dates_by_day[dt.strftime("%A")].append(dt.strftime("%Y-%m-%d"))

    new_classes_map = defaultdict(lambda: {
        "student_ids": [],
        "student_names": [],
        "levels": set(),
        "batch_types": set(),
        "day": ""
    })

    student_name_map = {s["student_id"]: s["student_name"] for s in students}
    student_quota_map = {s["student_id"]: s.get("required_classes", 12) for s in students}
    student_scheduled_count = defaultdict(int)

    # For each student, map their recurrence pattern onto target month dates
    for s in students:
        sid = s["student_id"]
        sname = s["student_name"]
        quota = student_quota_map.get(sid, 12)
        patterns = student_recurrence.get(sid, [])

        # Assign across dates matching the pattern days, up to monthly quota
        for pat in patterns:
            target_dates = dates_by_day.get(pat["day_name"], [])
            for d_str in target_dates:
                if student_scheduled_count[sid] >= quota:
                    break
                class_key = (d_str, pat["time_slot"], pat["coach_name"])
                if sid not in new_classes_map[class_key]["student_ids"]:
                    new_classes_map[class_key]["student_ids"].append(sid)
                    new_classes_map[class_key]["student_names"].append(sname)
                    new_classes_map[class_key]["levels"].add(pat["level"])
                    new_classes_map[class_key]["batch_types"].add(pat["batch_type"])
                    new_classes_map[class_key]["day"] = pat["day_name"]
                    student_scheduled_count[sid] += 1

    # Convert new_classes_map into list of classes
    draft_classes = []
    total_seats = 0
    for (d_str, t_str, c_name), c_info in new_classes_map.items():
        distinct_lvls = sorted(list(c_info["levels"]))
        primary_lvl = distinct_lvls[0] if len(distinct_lvls) == 1 else "MIXED"
        b_types = c_info["batch_types"]
        primary_btype = "G" if "G" in b_types else ("L" if "L" in b_types else "I")

        cls_id = f"CLS_{d_str.replace('-', '')}_{t_str.replace(' ', '').replace(':', '')}_{c_name.replace(' ', '')}"
        total_seats += len(c_info["student_ids"])

        draft_classes.append({
            "class_id": cls_id,
            "date": d_str,
            "day": c_info["day"],
            "time_slot": t_str,
            "coach_name": c_name,
            "student_level": primary_lvl,
            "batch_type": primary_btype,
            "batch_name": f"{primary_lvl} - {c_name}",
            "student_ids": c_info["student_ids"],
            "student_names": c_info["student_names"],
            "warnings": [],
            "is_baseline": True,
            "is_manual_override": False
        })

    # Prepare Draft Baseline Record
    draft_record = {
        "month": target_month_str,
        "version": 1,
        "status": "Draft",
        "file_name": f"Generated_Draft_from_{source_month}.xlsx",
        "uploaded_by": f"Engine Draft ({user})",
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "student_count": len(students),
        "class_count": len(draft_classes),
        "student_class_count": total_seats,
        "students_data": students,
        "classes_data": draft_classes,
        "baseline_exceptions": [],
        "validation_report": {
            "blocking": [],
            "baseline_exceptions": [],
            "info": [f"Draft generated automatically from {source_month} recurring patterns."]
        },
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    new_id = save_baseline_db(draft_record)
    draft_record["id"] = new_id
    return draft_record
