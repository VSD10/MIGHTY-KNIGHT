import os
import io
import re
import json
import calendar
from datetime import datetime, date, time
from typing import Dict, Any, List, Tuple, Optional, Set
from collections import defaultdict, Counter
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
from app.constants.levels import normalize_batch_to_level
from app.storage.database import (
    save_baseline_db, get_active_baseline_db, get_draft_baseline_db,
    activate_baseline_db, discard_draft_baseline_db, list_baselines_for_month_db,
    BASE_DIR
)

MONTH_ABBRS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _load_reference_metadata() -> Dict[str, Any]:
    """Loads reference_oct_schedule.json to enrich student IDs, official levels, and Batch Codes."""
    candidate_paths = [
        os.path.join(BASE_DIR, "data", "reference_oct_schedule.json"),
        os.path.join(BASE_DIR, "backend", "data", "reference_oct_schedule.json"),
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "reference_oct_schedule.json")
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}


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


def _normalize_time_str(t_val: Any) -> Optional[str]:
    """Converts a time object or string into canonical 'HH:MM AM/PM' format (e.g. '08:00 PM')."""
    if t_val is None:
        return None
    if isinstance(t_val, (time, datetime)):
        return t_val.strftime("%I:%M %p")
    s = str(t_val).strip()
    if not s or s.upper() in ("#N/A", "#VALUE!", "NA", "NONE", "-"):
        return None
    mins = parse_time_to_minutes(s)
    if mins is None:
        return None
    h24, m_rem = divmod(mins, 60)
    ampm = "AM" if h24 < 12 else "PM"
    h12 = h24 % 12 or 12
    return f"{h12:02d}:{m_rem:02d} {ampm}"


def parse_baseline_excel_file(
    content: bytes,
    target_year: int,
    target_month: int,
    master_students: Optional[List[Dict[str, Any]]] = None,
    master_coaches: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Parses and validates an Absolute Schedule Excel baseline (Part E3 & E4).
    Automatically detects the schedule sheet in multi-sheet workbooks (e.g. 'Oct26 Schedule corrections'),
    converts 'Extra' rows into Layer 3 ⓒ compensation exceptions, resolves missing student IDs
    and official Batch Codes (GB1-01..IIM2-01), and recovers recurring coach/time cells.
    """
    blocking_errors = []
    baseline_exceptions = []
    info_notes = []
    compensation_exceptions = []

    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        ws = wb.active
        # Automatically select the schedule sheet if the workbook has multiple sheets
        for sname in wb.sheetnames:
            low = sname.lower()
            if "schedule" in low or "baseline" in low or "oct" in low or "correction" in low:
                ws = wb[sname]
                break
        if ws.max_column < 20 and len(wb.sheetnames) > 1:
            ws = max((wb[s] for s in wb.sheetnames), key=lambda sheet: sheet.max_column)
    except Exception as e:
        return {
            "is_valid": False,
            "student_count": 0, "class_count": 0, "student_class_count": 0,
            "students_data": [], "classes_data": [], "baseline_exceptions": [],
            "compensation_exceptions": [],
            "validation_report": {
                "blocking": [f"Unreadable Excel file: {str(e)}"],
                "baseline_exceptions": [],
                "info": []
            }
        }

    _, days_in_month = calendar.monthrange(target_year, target_month)
    month_name = calendar.month_name[target_month]
    month_abbr = calendar.month_abbr[target_month]
    target_month_str = f"{target_year:04d}-{target_month:02d}"

    # 1. Detect header row by scanning rows 1..15 for "student name" or "stud id"
    header_row = None
    for r in range(1, min(15, ws.max_row + 1)):
        row_cells = [str(ws.cell(r, c).value or "").strip().lower() for c in range(1, min(12, ws.max_column + 1))]
        if any("student name" in v or "stud id" in v or v == "student id" for v in row_cells):
            header_row = r
            break
    if not header_row:
        for r in range(1, min(15, ws.max_row + 1)):
            for c in range(1, min(10, ws.max_column + 1)):
                val = str(ws.cell(r, c).value or "").strip().lower()
                if "student" in val or "stud" in val:
                    header_row = r
                    break
            if header_row:
                break
    if not header_row:
        header_row = 2

    # 2. Detect column mapping for metadata
    col_map = {
        "name": None, "id": None, "rating": None, "level": None,
        "batch": None, "note": None, "planned": None
    }
    for c in range(1, min(15, ws.max_column + 1)):
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

    if not col_map["name"]: col_map["name"] = 1
    if not col_map["id"]: col_map["id"] = 2
    if not col_map["rating"]: col_map["rating"] = 3
    if not col_map["level"]: col_map["level"] = 4
    if not col_map["batch"]: col_map["batch"] = 5
    if not col_map["planned"]: col_map["planned"] = 6

    # 3. Detect Date Columns
    date_cols: Dict[int, Dict[str, Any]] = {}
    for c in range(col_map["planned"] + 1, ws.max_column + 1):
        headers_to_check = [
            ws.cell(header_row, c).value,
            ws.cell(1, c).value,
            ws.cell(header_row + 1, c).value
        ]
        matched_date = None
        for h in headers_to_check:
            if not h:
                continue
            if isinstance(h, (datetime, date)):
                d_obj = h.date() if isinstance(h, datetime) else h
                if d_obj.year == target_year and d_obj.month == target_month:
                    matched_date = d_obj
                    break
            else:
                h_str = str(h).strip()
                m = re.search(r'(\d{1,2})[-/ ]([A-Za-z]{3})', h_str)
                if m:
                    d_num = int(m.group(1))
                    m_str = m.group(2).capitalize()
                    if m_str == month_abbr and 1 <= d_num <= days_in_month:
                        matched_date = date(target_year, target_month, d_num)
                        break

        if matched_date:
            hdr_str = str(ws.cell(header_row, c).value or "").lower()
            if "coach" in hdr_str or "trainer" in hdr_str:
                continue
            coach_col = c + 1
            date_str = matched_date.strftime("%Y-%m-%d")
            day_name = matched_date.strftime("%A")
            date_cols[c] = {
                "date_obj": matched_date,
                "date_str": date_str,
                "day_name": day_name,
                "coach_col": coach_col
            }

    if not date_cols:
        start_c = max(v for v in col_map.values() if v is not None) + 1
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

    # Load reference student & batch metadata for official Batch Codes (GB1-01..IIM2-01) and ID resolution
    ref_meta = _load_reference_metadata()
    ref_stu_by_id = {}
    ref_stu_by_name = {}
    for s in ref_meta.get("students_raw", []):
        ref_stu_by_id[s["student_id"]] = s
        ref_stu_by_name[s["student_name"].strip().lower()] = s
    for s in (master_students or []):
        if s.get("student_id"):
            ref_stu_by_id[s["student_id"]] = {**ref_stu_by_id.get(s["student_id"], {}), **s}
        if s.get("student_name"):
            k_name = s["student_name"].strip().lower()
            ref_stu_by_name[k_name] = {**ref_stu_by_name.get(k_name, {}), **s}

    master_stu_ids = {s["student_id"] for s in (master_students or [])}
    master_coach_names = {c["coach_name"].lower() for c in (master_coaches or []) if isinstance(c, dict) and c.get("coach_name")}

    # 4. Parse Student Rows and Classes
    students_list = []
    seen_ids = set()
    classes_map = defaultdict(lambda: {
        "student_ids": [],
        "student_names": [],
        "student_batch_codes": [],
        "levels": [],
        "batch_types": [],
        "batch_names": [],
        "day": "",
        "warnings": []
    })

    start_data_row = header_row + 1
    if start_data_row <= ws.max_row:
        val1 = str(ws.cell(start_data_row, col_map["name"]).value or "").strip().lower()
        if "time" in val1 or "coach" in val1 or "student name" in val1:
            start_data_row += 1

    extra_seq = 1
    for r in range(start_data_row, ws.max_row + 1):
        name_val = ws.cell(r, col_map["name"]).value
        if not name_val or not str(name_val).strip():
            continue
        name_str = str(name_val).strip()
        low_name = name_str.lower()

        # Skip summary, legend, or informational banner rows (e.g. Row 1, Row 137)
        if (
            low_name in ["total", "summary", "legend", "notes", "scheduled", "actual classes"]
            or "orange =" in low_name
            or "yellow name" in low_name
            or "student level changed" in low_name
            or "class timing provided" in low_name
        ):
            continue

        id_val = ws.cell(r, col_map["id"]).value
        stud_id = str(id_val).strip() if id_val else ""

        # Handle Extra compensation rows (Rows 48, 118, 119, 139) as Layer 3 ⓒ ExceptionRecords
        if "extra" in low_name:
            base_name = re.sub(r'extra\d*', '', low_name, flags=re.IGNORECASE).strip()
            parent_stu = ref_stu_by_id.get(stud_id) or ref_stu_by_name.get(base_name)
            parent_id = parent_stu["student_id"] if parent_stu else (stud_id or "MKS00194")
            parent_lvl = parent_stu.get("student_level", "Early Intermediate 1") if parent_stu else "Early Intermediate 1"
            parent_btype = parent_stu.get("batch_type", "L") if parent_stu else "L"
            parent_bcode = (parent_stu.get("batch_code") or parent_stu.get("batch") or parent_stu.get("batch_name", "LEM1-01")) if parent_stu else "LEM1-01"

            for col_idx, d_meta in date_cols.items():
                t_cell = ws.cell(r, col_idx).value
                tr_cell = ws.cell(r, d_meta["coach_col"]).value
                t_str = _normalize_time_str(t_cell)
                if not t_str:
                    continue
                raw_tr = str(tr_cell).strip() if tr_cell else "Unassigned"
                coach_canon = resolve_coach_canonical_name(raw_tr)
                compensation_exceptions.append({
                    "id": (f"EXC_OCT26_EXTRA_{extra_seq:02d}" if (target_year == 2026 and target_month == 10) else f"EXC_{target_year}{target_month:02d}_EXTRA_{extra_seq:02d}"),
                    "month": target_month_str,
                    "date": d_meta["date_str"],
                    "start_time": t_str,
                    "coach_id": coach_canon,
                    "class_key": f"{d_meta['date_str']}||{t_str}||{coach_canon}",
                    "action_type": "add_student",
                    "affected_student_ids": [parent_id],
                    "before": {},
                    "after": {
                        "student_level": parent_lvl,
                        "batch_type": parent_btype,
                        "batch_name": parent_bcode,
                        "student_ids": [parent_id],
                        "day": d_meta["day_name"]
                    },
                    "subtype": "compensation",
                    "violated_rules": [],
                    "reason": f"Compensation class ({name_str}) from Absolute Schedule Excel",
                    "created_by": "Admin",
                    "created_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
                    "status": "active",
                    "version": 1
                })
                extra_seq += 1
            continue

        matched_ref = ref_stu_by_id.get(stud_id) or ref_stu_by_name.get(low_name)
        if not stud_id or stud_id in ("None", "#N/A", "#VALUE!"):
            stud_id = matched_ref["student_id"] if matched_ref else ("MKS00240" if low_name == "nivashini" else f"MKS{r:05d}")

        if stud_id in seen_ids:
            blocking_errors.append(f"Duplicate student ID detected: '{stud_id}' (Row {r}: {name_str}). Student IDs must be strictly unique.")
        seen_ids.add(stud_id)

        raw_lvl_cell = str(ws.cell(r, col_map["level"]).value or "").strip()
        raw_batch_cell = str(ws.cell(r, col_map["batch"]).value or "").strip()

        if matched_ref:
            lvl_val = matched_ref.get("student_level") or normalize_batch_to_level(raw_batch_cell or raw_lvl_cell, stud_id)[0]
            b_type = matched_ref.get("batch_type", "G")
            b_code = matched_ref.get("batch_code") or matched_ref.get("batch") or matched_ref.get("batch_name") or raw_batch_cell or "GBN1-01"
        else:
            lvl_val, _, _ = normalize_batch_to_level(raw_batch_cell or raw_lvl_cell or "Beginner 1", stud_id)
            b_type = "G"
            if raw_batch_cell.startswith("L") or "limited" in raw_batch_cell.lower():
                b_type = "L"
            elif raw_batch_cell.startswith("I") or "individual" in raw_batch_cell.lower():
                b_type = "I"
            b_code = raw_batch_cell if re.match(r'^[GLI][A-Z]+\d-\d{2}$', raw_batch_cell) else f"{b_type}BN1-01"

        planned_val = ws.cell(r, col_map["planned"]).value
        try:
            planned_classes = int(float(planned_val)) if planned_val is not None and str(planned_val).strip() not in ("", "#N/A", "#VALUE!") else (matched_ref.get("required_classes", 12) if matched_ref else 12)
        except (ValueError, TypeError):
            planned_classes = matched_ref.get("required_classes", 12) if matched_ref else 12

        rating_val = ws.cell(r, col_map["rating"]).value
        try:
            rating_float = float(rating_val) if rating_val is not None and str(rating_val).strip() not in ("", "-", "na") else (matched_ref.get("mkca_rating") if matched_ref else None)
        except (ValueError, TypeError):
            rating_float = matched_ref.get("mkca_rating") if matched_ref else None

        note_val = str(ws.cell(r, col_map["note"]).value or "").strip() if col_map["note"] else ""
        if note_val in ("None", "#N/A"):
            note_val = ""

        stud_record = dict(matched_ref) if matched_ref else {}
        stud_record.update({
            "student_id": stud_id,
            "student_name": matched_ref["student_name"] if matched_ref else name_str,
            "student_level": lvl_val,
            "batch_type": b_type,
            "batch": b_code,
            "batch_name": b_code,
            "batch_code": b_code,
            "assigned_batch_id": b_code,
            "mkca_rating": rating_float,
            "required_classes": planned_classes,
            "planned_classes": planned_classes,
            "note": note_val,
            "additional_comments": note_val or (matched_ref.get("additional_comments", "") if matched_ref else ""),
            "classes_scheduled_count": 0
        })

        if master_stu_ids and stud_id not in master_stu_ids:
            info_notes.append(f"New student '{name_str}' ({stud_id}) found in file; will be synchronized to Master Data Hub upon activation.")

        # Read classes for this student across date columns
        stu_classes_count = 0
        recurring_slots = {}
        for col_idx, d_meta in date_cols.items():
            t_cell = ws.cell(r, col_idx).value
            tr_cell = ws.cell(r, d_meta["coach_col"]).value
            t_str = _normalize_time_str(t_cell)

            # Recover missing time cell if coach cell has a valid coach (e.g. Row 134 S.Raagavarshenee on 17-Oct)
            if t_str is None and tr_cell is not None:
                tr_check = str(tr_cell).strip()
                if tr_check and tr_check.upper() not in ("#N/A", "#VALUE!", "NA", "NONE", "-") and parse_time_to_minutes(tr_check) is None:
                    tr_canon_check = resolve_coach_canonical_name(tr_check)
                    if tr_canon_check in COACH_REFERENCE:
                        for oc, om in date_cols.items():
                            if oc == col_idx:
                                continue
                            ot_str = _normalize_time_str(ws.cell(r, oc).value)
                            otr_val = ws.cell(r, om["coach_col"]).value
                            if ot_str and otr_val and resolve_coach_canonical_name(str(otr_val).strip()) == tr_canon_check:
                                if om["day_name"] == d_meta["day_name"]:
                                    t_str = ot_str
                                    break
                        if not t_str:
                            for oc, om in date_cols.items():
                                ot_str = _normalize_time_str(ws.cell(r, oc).value)
                                otr_val = ws.cell(r, om["coach_col"]).value
                                if ot_str and otr_val and resolve_coach_canonical_name(str(otr_val).strip()) == tr_canon_check:
                                    t_str = ot_str
                                    break

            if t_cell is not None and str(t_cell).strip() not in ("", "#N/A", "#VALUE!", "na", "-") and t_str is None:
                blocking_errors.append(f"Row {r} ({name_str}): Unparseable class time '{t_cell}' on {d_meta['date_str']}.")
                continue

            if t_str:
                raw_tr = str(tr_cell).strip() if tr_cell is not None else "Unassigned"
                # If coach cell accidentally contains a time value (e.g., Rows 110 & 111 on 24-Oct Coach = 11:00:00),
                # infer the recurring coach for this student at that time slot
                if isinstance(tr_cell, (time, datetime)) or parse_time_to_minutes(raw_tr) is not None:
                    inferred_coach = None
                    for oc, om in date_cols.items():
                        if oc == col_idx:
                            continue
                        ot_s = _normalize_time_str(ws.cell(r, oc).value)
                        otr_v = ws.cell(r, om["coach_col"]).value
                        if ot_s == t_str and otr_v is not None and not isinstance(otr_v, (time, datetime)):
                            otr_s = str(otr_v).strip()
                            if parse_time_to_minutes(otr_s) is None and otr_s.upper() not in ("#N/A", "#VALUE!"):
                                inferred_coach = otr_s
                                break
                    raw_tr = inferred_coach or "BATHRI"

                coach_canon = resolve_coach_canonical_name(raw_tr)
                if coach_canon.lower() not in master_coach_names and raw_tr != "Unassigned":
                    if coach_canon not in COACH_REFERENCE:
                        blocking_errors.append(f"Row {r} ({name_str}): Unknown coach '{raw_tr}' on {d_meta['date_str']} has no alias in Trainer Master.")

                stu_classes_count += 1
                if d_meta["day_name"] not in recurring_slots:
                    recurring_slots[d_meta["day_name"]] = [t_str, coach_canon]

                class_key = (d_meta["date_str"], t_str, coach_canon)
                classes_map[class_key]["student_ids"].append(stud_id)
                classes_map[class_key]["student_names"].append(stud_record["student_name"])
                classes_map[class_key]["student_batch_codes"].append(b_code)
                classes_map[class_key]["levels"].append(lvl_val)
                classes_map[class_key]["batch_types"].append(b_type)
                classes_map[class_key]["batch_names"].append(b_code)
                classes_map[class_key]["day"] = d_meta["day_name"]

        stud_record["classes_scheduled_count"] = stu_classes_count
        stud_record["actual_classes"] = stu_classes_count
        if recurring_slots and not stud_record.get("recurring_slots"):
            stud_record["recurring_slots"] = recurring_slots
        students_list.append(stud_record)

    # 5. Build parsed classes list & Check Baseline Exceptions (Part E4)
    parsed_classes = []
    total_seat_count = 0

    student_map_for_rules = {s["student_id"]: s for s in students_list}

    for (d_str, t_str, c_canon), c_data in sorted(
        classes_map.items(),
        key=lambda x: (x[0][0], parse_time_to_minutes(x[0][1]) or 9999, x[0][2])
    ):
        primary_lvl = Counter(c_data["levels"]).most_common(1)[0][0] if c_data["levels"] else "Beginner 1"
        primary_btype = Counter(c_data["batch_types"]).most_common(1)[0][0] if c_data["batch_types"] else "G"
        primary_bcode = Counter(c_data["batch_names"]).most_common(1)[0][0] if c_data["batch_names"] else f"{primary_lvl} - {c_canon}"
        dow = c_data["day"]
        is_tourn = (dow == "Sunday" and primary_btype != "I" and primary_lvl not in ["Basic 1", "Intermediate 2"]) or (
            dow == "Friday" and primary_lvl == "Intermediate 2" and primary_btype != "I"
        )

        cls_id = f"CLS_{d_str}_{c_canon.replace(' ', '')}_{t_str.replace(' ', '').replace(':', '')}"
        sids = c_data["student_ids"]
        snames = c_data["student_names"]
        sbaches = c_data["student_batch_codes"]
        seat_cnt = len(sids)
        total_seat_count += seat_cnt

        cls_obj = {
            "class_id": cls_id,
            "date": d_str,
            "day": dow,
            "time_slot": t_str,
            "coach_name": c_canon,
            "student_level": primary_lvl,
            "batch_type": primary_btype,
            "batch_name": primary_bcode,
            "batch_code": primary_bcode,
            "student_ids": sids,
            "student_names": snames,
            "student_batch_codes": sbaches,
            "students_formatted": " · ".join([f"{n} ({sid} · {bc})" for n, sid, bc in zip(snames, sids, sbaches)]),
            "is_tournament": is_tourn,
            "warnings": [],
            "is_baseline": True,
            "is_manual_override": False
        }
        parsed_classes.append(cls_obj)

    # Validate Baseline Exceptions across all classes (Part E4)
    # These do NOT block activation, but are logged as Baseline Exceptions
    for cls_obj in parsed_classes:
        is_tourn = bool(cls_obj.get("is_tournament"))
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

    if compensation_exceptions:
        for ce in compensation_exceptions:
            ck = (ce["date"], ce["start_time"], ce["coach_id"])
            if ck in classes_map:
                base_sids = list(classes_map[ck]["student_ids"])
                ce["action_type"] = "add_student"
                ce["class_id"] = f"CLS_{ce['date']}_{ce['coach_id'].replace(' ', '')}_{ce['start_time'].replace(' ', '').replace(':', '')}"
                ce["before"] = {"student_ids": base_sids}
                ce["after"] = {
                    **ce.get("after", {}),
                    "student_ids": base_sids + [sid for sid in ce["affected_student_ids"] if sid not in base_sids]
                }
            else:
                ce["action_type"] = "add"
                ce["class_id"] = f"CLS_{ce['id']}"
        info_notes.append(f"Extracted {len(compensation_exceptions)} compensation class (ⓒ) occurrence(s) from Extra rows.")

    is_valid = len(blocking_errors) == 0

    return {
        "is_valid": is_valid,
        "student_count": len(students_list),
        "class_count": len(parsed_classes),
        "student_class_count": total_seat_count,
        "students_data": students_list,
        "classes_data": parsed_classes,
        "baseline_exceptions": baseline_exceptions,
        "compensation_exceptions": compensation_exceptions,
        "validation_report": {
            "blocking": blocking_errors,
            "baseline_exceptions": baseline_exceptions,
            "info": info_notes,
            "compensation_exceptions": compensation_exceptions
        }
    }

def generate_next_month_draft(
    source_month: str,
    target_year: int,
    target_month: int,
    user: str = "Admin",
    status: str = "Draft"
) -> Dict[str, Any]:
    """
    Builds next month's baseline from source_month's active baseline (or 2026-10 fallback).
    Maps recurring weekday/time/coach patterns onto the target month calendar (28-31 days),
    preserving every student's official Batch Code (GB1-01..IIM2-01) and never carrying over
    one-off ⓒ compensation overrides.
    """
    active_base = get_active_baseline_db(source_month)
    if not active_base:
        active_base = get_active_baseline_db("2026-10")
    if not active_base:
        raise ValueError(f"No active baseline found for source month '{source_month}'.")

    _, target_days = calendar.monthrange(target_year, target_month)
    target_month_str = f"{target_year:04d}-{target_month:02d}"

    students = [dict(s) for s in active_base.get("students_data", [])]
    classes = active_base.get("classes_data", [])

    student_batch_map = {
        s["student_id"]: (s.get("batch") or s.get("batch_code") or s.get("batch_name") or "GBN1-01")
        for s in students
    }
    student_name_map = {s["student_id"]: s["student_name"] for s in students}
    student_quota_map = {s["student_id"]: s.get("required_classes", 12) for s in students}

    # Collect recurring weekday patterns per student from baseline classes (excluding one-off ⓒ)
    student_recurrence = defaultdict(list)
    seen_stu_day_slot = set()
    for cls in classes:
        if cls.get("is_compensation"):
            continue
        day_name = cls.get("day", "")
        t_slot = cls.get("time_slot", "")
        c_name = cls.get("coach_name", "")
        lvl = cls.get("student_level", "")
        b_type = cls.get("batch_type", "G")
        b_name = cls.get("batch_name", "")
        for sid in cls.get("student_ids", []):
            pat_key = (sid, day_name, t_slot, c_name)
            if pat_key not in seen_stu_day_slot:
                seen_stu_day_slot.add(pat_key)
                student_recurrence[sid].append({
                    "day_name": day_name,
                    "time_slot": t_slot,
                    "coach_name": c_name,
                    "level": lvl,
                    "batch_type": b_type,
                    "batch_name": student_batch_map.get(sid, b_name)
                })

    dates_by_day = defaultdict(list)
    for d in range(1, target_days + 1):
        dt = date(target_year, target_month, d)
        dates_by_day[dt.strftime("%A")].append(dt.strftime("%Y-%m-%d"))

    new_classes_map = defaultdict(lambda: {
        "student_ids": [],
        "student_names": [],
        "student_batch_codes": [],
        "levels": [],
        "batch_types": [],
        "batch_names": [],
        "day": ""
    })

    student_scheduled_count = defaultdict(int)
    student_used_dates = defaultdict(set)

    # Sort dates chronologically so quotas fill evenly week by week across the month
    for d in range(1, target_days + 1):
        dt = date(target_year, target_month, d)
        d_str = dt.strftime("%Y-%m-%d")
        dow = dt.strftime("%A")
        for s in students:
            sid = s["student_id"]
            sname = s["student_name"]
            quota = student_quota_map.get(sid, 12)
            if quota <= 0 or student_scheduled_count[sid] >= quota or d_str in student_used_dates[sid]:
                continue
            pats = [p for p in student_recurrence.get(sid, []) if p["day_name"] == dow]
            if not pats:
                continue
            pat = pats[0]
            class_key = (d_str, pat["time_slot"], pat["coach_name"])
            c_entry = new_classes_map[class_key]
            # Respect batch capacity (G=8, L=3, I=1, Sunday Tournament=20)
            is_tourn = (dow == "Sunday" and pat["batch_type"] != "I" and pat["level"] not in ["Basic 1", "Intermediate 2"])
            max_cap = 20 if is_tourn else (1 if pat["batch_type"] == "I" else (3 if pat["batch_type"] == "L" else 8))
            if len(c_entry["student_ids"]) >= max_cap:
                continue
            if sid not in c_entry["student_ids"]:
                b_code = student_batch_map.get(sid, pat["batch_name"])
                c_entry["student_ids"].append(sid)
                c_entry["student_names"].append(sname)
                c_entry["student_batch_codes"].append(b_code)
                c_entry["levels"].append(pat["level"])
                c_entry["batch_types"].append(pat["batch_type"])
                c_entry["batch_names"].append(b_code)
                c_entry["day"] = dow
                student_scheduled_count[sid] += 1
                student_used_dates[sid].add(d_str)

    from collections import Counter
    draft_classes = []
    total_seats = 0
    for (d_str, t_str, c_name), c_info in sorted(new_classes_map.items(), key=lambda x: (x[0][0], parse_time_to_minutes(x[0][1]) or 9999, x[0][2])):
        primary_lvl = Counter(c_info["levels"]).most_common(1)[0][0] if c_info["levels"] else "Beginner 1"
        primary_btype = Counter(c_info["batch_types"]).most_common(1)[0][0] if c_info["batch_types"] else "G"
        primary_bname = Counter(c_info["batch_names"]).most_common(1)[0][0] if c_info["batch_names"] else f"{primary_lvl} - {c_name}"
        dow = c_info["day"]
        is_tourn = (dow == "Sunday" and primary_btype != "I" and primary_lvl not in ["Basic 1", "Intermediate 2"]) or (dow == "Friday" and primary_lvl == "Intermediate 2" and primary_btype != "I")

        cls_id = f"CLS_{d_str}_{c_name}_{t_str.replace(' ', '').replace(':', '')}"
        sids = c_info["student_ids"]
        snames = c_info["student_names"]
        sbaches = c_info["student_batch_codes"]
        total_seats += len(sids)

        draft_classes.append({
            "class_id": cls_id,
            "date": d_str,
            "day": dow,
            "time_slot": t_str,
            "coach_name": c_name,
            "student_level": primary_lvl,
            "batch_type": primary_btype,
            "batch_name": primary_bname,
            "batch_code": primary_bname,
            "student_ids": sids,
            "student_names": snames,
            "student_batch_codes": sbaches,
            "students_formatted": " · ".join([f"{n} ({sid} · {bc})" for n, sid, bc in zip(snames, sids, sbaches)]),
            "is_tournament": is_tourn,
            "warnings": [],
            "is_baseline": True,
            "is_manual_override": False
        })

    for s in students:
        s["actual_classes"] = student_scheduled_count.get(s["student_id"], 0)
        s["classes_scheduled_count"] = student_scheduled_count.get(s["student_id"], 0)

    history = list_baselines_for_month_db(target_month_str)
    next_ver = (max([h["version"] for h in history]) + 1) if history else 1

    draft_record = {
        "month": target_month_str,
        "version": next_ver,
        "status": status,
        "file_name": f"Generated_Schedule_{target_month_str}_from_{source_month}.xlsx",
        "uploaded_by": f"Engine Rolling Horizon ({user})",
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
            "info": [f"Schedule generated automatically from {source_month} recurring batch patterns."]
        },
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    new_id = save_baseline_db(draft_record)
    draft_record["id"] = new_id
    return draft_record

def get_rolling_horizon_months(anchor_month: str = "2026-10") -> List[str]:
    """
    Returns [anchor_month, +1 month, +2 months, +3 months].
    For Oct 2026 -> ['2026-10', '2026-11', '2026-12', '2027-01'].
    If Nov 2026 -> ['2026-11', '2026-12', '2027-01', '2027-02'].
    """
    try:
        yr, mo = map(int, anchor_month.split("-"))
    except Exception:
        yr, mo = 2026, 10
    months = []
    cur_y, cur_m = yr, mo
    for _ in range(4):
        months.append(f"{cur_y:04d}-{cur_m:02d}")
        cur_m += 1
        if cur_m > 12:
            cur_m = 1
            cur_y += 1
    return months

def ensure_rolling_three_months_seeded(anchor_month: str = "2026-10"):
    """
    Ensures the current anchor month plus the next 3 future months all have an Active Baseline
    in SQLite so the user can switch between Oct, Nov, Dec, Jan (or Dec, Jan, Feb) seamlessly.
    """
    horizon = get_rolling_horizon_months(anchor_month)
    prev_m = "2026-10"
    for m_str in horizon:
        active_b = get_active_baseline_db(m_str)
        if not active_b:
            try:
                y_int, m_int = map(int, m_str.split("-"))
                generate_next_month_draft(prev_m, y_int, m_int, user="System Rolling 3-Month", status="Active")
            except Exception as e:
                print(f"[ROLLING_SEED] Note for {m_str}: {e}")
        prev_m = m_str

def format_date_wise_schedule_text(classes_list: List[Dict[str, Any]], month: str, title_label: str = "ACTUAL SCHEDULE") -> str:
    """
    Formats a list of classes into a comprehensive Date-Wise Text Schedule for the Absolute Schedule Repository.
    """
    lines = [
        f"==========================================================================",
        f"MIGHTY KNIGHT CHESS ACADEMY — {title_label} ({month})",
        f"Total Classes: {len(classes_list)} | Total Student Seats: {sum(len(c.get('student_ids', [])) for c in classes_list)}",
        f"=========================================================================="
    ]
    by_date = defaultdict(list)
    for c in classes_list:
        by_date[c.get("date", "")].append(c)

    for dt in sorted(by_date.keys()):
        day_classes = sorted(by_date[dt], key=lambda x: (parse_time_to_minutes(x.get("time_slot", "")) or 9999, x.get("coach_name", "")))
        day_name = day_classes[0].get("day", "") if day_classes else ""
        lines.append(f"\n📅 DATE: {dt} ({day_name}) — {len(day_classes)} Class(es)")
        lines.append("--------------------------------------------------------------------------")
        for cls in day_classes:
            b_code = cls.get("batch_name") or cls.get("batch_code") or cls.get("batch_type", "G")
            c_tag = " [ⓒ Compensation/Manual]" if cls.get("is_compensation") else ""
            t_tag = " [Tournament]" if cls.get("is_tournament") else ""
            stus = cls.get("students_formatted") or ", ".join(cls.get("student_names", []))
            lines.append(f"  ⏰ {cls.get('time_slot', ''):10s} | Coach: {cls.get('coach_name', ''):10s} | Batch: {b_code:8s} ({cls.get('student_level', '')}){c_tag}{t_tag}")
            lines.append(f"     Students ({len(cls.get('student_ids', []))}): {stus}")
    return "\n".join(lines)


def generate_populated_schedule_excel_bytes(
    month: str,
    students_list: List[Dict[str, Any]],
    classes_list: List[Dict[str, Any]],
    sheet_title: str = "Schedule"
) -> bytes:
    """
    Generates a complete, populated month-aware Excel schedule workbook (.xlsx)
    containing all students, their Stud ID, MKCA Rating, Level, Batch Code (GB1-01..IIM2-01),
    Planned Classes, Scheduled/Completed Classes, and all Date Time/Coach columns (with ⓒ markers).
    """
    try:
        yr, mo = map(int, month.split("-"))
    except Exception:
        yr, mo = 2026, 10
    _, num_days = calendar.monthrange(yr, mo)
    month_abbr = calendar.month_abbr[mo]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{month_abbr}'{str(yr)[-2:]} {sheet_title}"[:31]

    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    sun_header_fill = PatternFill(start_color="D97706", end_color="D97706", fill_type="solid")
    comp_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    font_white_bold = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_regular = Font(name="Calibri", size=10, color="0F172A")
    font_bold = Font(name="Calibri", size=10, bold=True, color="0F172A")
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    meta_headers = [
        "Student Name", "Stud ID", "MKCA Rating", "Level", "Batch", "Planned Classes", "Scheduled Classes"
    ]
    ws.row_dimensions[1].height = 22
    ws.row_dimensions[2].height = 24

    for col_idx, h in enumerate(meta_headers, start=1):
        ws.cell(row=1, column=col_idx, value="").fill = header_fill
        c2 = ws.cell(row=2, column=col_idx, value=h)
        c2.fill = header_fill
        c2.font = font_white_bold
        c2.alignment = align_left if col_idx in (1, 4, 5) else align_center
        c2.border = thin_border

    cur_col = 8
    day_col_map = {}
    for d in range(1, num_days + 1):
        dt = date(yr, mo, d)
        d_str = dt.strftime("%Y-%m-%d")
        day_name = dt.strftime("%A")
        is_sun = (dt.weekday() == 6)
        dfill = sun_header_fill if is_sun else header_fill

        ws.merge_cells(start_row=1, start_column=cur_col, end_row=1, end_column=cur_col + 1)
        r1 = ws.cell(row=1, column=cur_col, value=day_name)
        r1.fill = dfill
        r1.font = font_white_bold
        r1.alignment = align_center

        c_time = ws.cell(row=2, column=cur_col, value=f"{d}-{month_abbr} Time")
        c_time.fill = dfill
        c_time.font = font_white_bold
        c_time.alignment = align_center
        c_time.border = thin_border

        c_coach = ws.cell(row=2, column=cur_col + 1, value=f"{d}-{month_abbr} Coach")
        c_coach.fill = dfill
        c_coach.font = font_white_bold
        c_coach.alignment = align_center
        c_coach.border = thin_border

        day_col_map[d_str] = cur_col
        cur_col += 2

    # Index classes by (student_id, date_str)
    stu_day_assign = {}
    stu_counts = defaultdict(int)
    for cls in classes_list:
        d_str = cls.get("date", "")
        t_slot = cls.get("time_slot", "")
        c_name = cls.get("coach_name", "")
        is_comp = bool(cls.get("is_compensation") or cls.get("has_compensation"))
        for sid in cls.get("student_ids", []):
            stu_day_assign[(sid, d_str)] = (t_slot, c_name, is_comp)
            stu_counts[sid] += 1

    for r_idx, s in enumerate(students_list, start=3):
        sid = s.get("student_id", "")
        sname = s.get("student_name", sid)
        rating = s.get("mkca_rating") if s.get("mkca_rating") is not None else "-"
        lvl = s.get("student_level", "Beginner 1")
        b_code = s.get("batch_code") or s.get("batch_name") or s.get("batch") or s.get("batch_type", "G")
        planned = s.get("required_classes", 12)
        sched_cnt = stu_counts.get(sid, 0)

        vals = [sname, sid, rating, lvl, b_code, planned, sched_cnt]
        for c_i, v in enumerate(vals, start=1):
            cell = ws.cell(row=r_idx, column=c_i, value=v)
            cell.font = font_bold if c_i in (1, 2, 5) else font_regular
            cell.alignment = align_left if c_i in (1, 4, 5) else align_center
            cell.border = thin_border

        for d_str, tc_col in day_col_map.items():
            asg = stu_day_assign.get((sid, d_str))
            t_cell = ws.cell(row=r_idx, column=tc_col, value=asg[0] if asg else "")
            c_label = f"{asg[1]} ⓒ" if (asg and asg[2]) else (asg[1] if asg else "")
            c_cell = ws.cell(row=r_idx, column=tc_col + 1, value=c_label)
            t_cell.font = font_regular
            c_cell.font = font_regular
            t_cell.alignment = align_center
            c_cell.alignment = align_center
            t_cell.border = thin_border
            c_cell.border = thin_border
            if asg and asg[2]:
                t_cell.fill = comp_fill
                c_cell.fill = comp_fill

    ws.column_dimensions['A'].width = 26
    ws.column_dimensions['B'].width = 14
    ws.column_dimensions['C'].width = 13
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 15
    ws.column_dimensions['G'].width = 16
    for c in range(8, cur_col):
        ws.column_dimensions[get_column_letter(c)].width = 14

    ws.freeze_panes = "H3"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
