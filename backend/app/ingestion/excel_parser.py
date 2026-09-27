import io
import re
import datetime
from typing import List, Dict, Tuple, Any, Union, Optional
from collections import defaultdict, Counter
import pandas as pd
import openpyxl

from app.models.student import StudentModel
from app.models.coach import CoachModel
from app.config import DEFAULT_CONFIG, SystemConfig
from app.storage.database import load_master_data_db, save_all_master_batches_db

COACH_ALIAS_MAP = {
    "bathri": "Bathrinath",
    "bathrinath": "Bathrinath",
    "guru": "Guruvanthana",
    "guruvanthana": "Guruvanthana",
    "dhaanush": "Dhaanush",
    "dhanush": "Dhaanush",
    "arshath": "Arshath",
    "saravanan": "Saravanan",
    "abinaya": "Abinaya",
    "prakash": "Prakash",
    "manikandan": "Manikandan",
    "hema": "Hema"
}

STANDARD_COACH_DEFAULTS = {
    "guruvanthana": {
        "coach_name": "Guruvanthana",
        "levels_handled": ["Basic 1", "Basic 2", "Beginner 1", "Beginner 2", "Beginner 3", "Early Intermediate 1"],
        "monthly_capacity_min": 35, "monthly_capacity_max": 40,
        "mon_max": 4, "tue_max": 4, "wed_max": 4, "thu_max": 4, "fri_max": 4, "sat_max": 5, "sun_max": 2,
        "sunday_pref": "Available", "preferred_timings": "Evening (4 PM - 9 PM)"
    },
    "dhaanush": {
        "coach_name": "Dhaanush",
        "levels_handled": ["Beginner 1", "Beginner 2", "Beginner 3", "Early Intermediate 1", "Early Intermediate 2", "Intermediate"],
        "monthly_capacity_min": 70, "monthly_capacity_max": 78,
        "mon_max": 4, "tue_max": 4, "wed_max": 4, "thu_max": 4, "fri_max": 4, "sat_max": 5, "sun_max": 0,
        "sunday_pref": "No Sunday Tournaments", "preferred_timings": "Midday & Evening"
    },
    "arshath": {
        "coach_name": "Arshath",
        "levels_handled": ["Early Intermediate 2", "Intermediate"],
        "monthly_capacity_min": 16, "monthly_capacity_max": 20,
        "mon_max": 3, "tue_max": 3, "wed_max": 3, "thu_max": 3, "fri_max": 3, "sat_max": 4, "sun_max": 2,
        "sunday_pref": "Available", "preferred_timings": "Evening (6 PM - 9 PM)"
    },
    "saravanan": {
        "coach_name": "Saravanan",
        "levels_handled": ["Beginner 2", "Beginner 3", "Early Intermediate 1", "Early Intermediate 2", "Intermediate"],
        "monthly_capacity_min": 0, "monthly_capacity_max": 8,
        "mon_max": 3, "tue_max": 3, "wed_max": 3, "thu_max": 3, "fri_max": 3, "sat_max": 4, "sun_max": 0,
        "sunday_pref": "No Sunday Tournaments", "preferred_timings": "Evening"
    },
    "bathrinath": {
        "coach_name": "Bathrinath",
        "levels_handled": ["Basic 1", "Basic 2", "Beginner 1", "Beginner 2"],
        "monthly_capacity_min": 30, "monthly_capacity_max": 60,
        "mon_max": 4, "tue_max": 4, "wed_max": 4, "thu_max": 4, "fri_max": 4, "sat_max": 5, "sun_max": 2,
        "sunday_pref": "Available", "preferred_timings": "Morning & Evening"
    },
    "abinaya": {
        "coach_name": "Abinaya",
        "levels_handled": ["Basic 1", "Basic 2", "Beginner 1"],
        "monthly_capacity_min": 30, "monthly_capacity_max": 60,
        "mon_max": 3, "tue_max": 3, "wed_max": 3, "thu_max": 3, "fri_max": 3, "sat_max": 4, "sun_max": 2,
        "sunday_pref": "Available", "preferred_timings": "Morning (6 AM - 8 AM) & Evening"
    },
    "prakash": {
        "coach_name": "Prakash",
        "levels_handled": ["Basic 1", "Basic 2", "Beginner 1", "Beginner 2", "Beginner 3", "Early Intermediate 1", "Early Intermediate 2", "Intermediate"],
        "monthly_capacity_min": 40, "monthly_capacity_max": 90,
        "mon_max": 4, "tue_max": 4, "wed_max": 4, "thu_max": 4, "fri_max": 4, "sat_max": 5, "sun_max": 2,
        "sunday_pref": "Available", "preferred_timings": "All Operating Hours"
    },
    "manikandan": {
        "coach_name": "Manikandan",
        "levels_handled": ["Basic 1", "Basic 2", "Beginner 1", "Beginner 2", "Early Intermediate 1"],
        "monthly_capacity_min": 20, "monthly_capacity_max": 60,
        "mon_max": 4, "tue_max": 4, "wed_max": 4, "thu_max": 4, "fri_max": 4, "sat_max": 5, "sun_max": 2,
        "sunday_pref": "Available", "preferred_timings": "Evening & Weekend"
    }
}

class ExcelParsingError:
    def __init__(self, sheet: str, row: int, column: str, message: str, severity: str = "ERROR"):
        self.sheet = sheet
        self.row = row
        self.column = column
        self.message = message
        self.severity = severity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sheet": self.sheet,
            "row": self.row,
            "column": self.column,
            "message": self.message,
            "severity": self.severity
        }

def normalize_header(header: str) -> str:
    if not isinstance(header, str):
        return ""
    h = header.strip().lower()
    h = re.sub(r'[\s_\-\/\.]+', '_', h)
    return h

def parse_capacity_range(val: Any) -> Tuple[int, int]:
    if pd.isna(val) or val is None:
        return (30, 60)
    val_str = str(val).strip()
    match = re.search(r'(\d+)\s*[\-–—:]\s*(\d+)', val_str)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    match_num = re.search(r'(\d+)', val_str)
    if match_num:
        num = int(match_num.group(1))
        return (num, num)
    return (30, 60)

def parse_levels_list(val: Any) -> List[str]:
    if pd.isna(val) or val is None:
        return []
    val_str = str(val).strip()
    if not val_str:
        return []
    parts = re.split(r'[,;|\n]+', val_str)
    return [p.strip() for p in parts if p.strip()]

def format_time_slot_str(time_val: Any) -> str:
    """Standardizes time format e.g. datetime.time(17, 30), '17:00:00', '6:00 AM' into '05:30 PM - 06:30 PM'."""
    if time_val is None:
        return ""
    if isinstance(time_val, datetime.time):
        hr, mn = time_val.hour, time_val.minute
    elif isinstance(time_val, datetime.datetime):
        hr, mn = time_val.hour, time_val.minute
    else:
        s = str(time_val).strip()
        m_time = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', s)
        if m_time:
            hr, mn = int(m_time.group(1)), int(m_time.group(2))
            if "pm" in s.lower() and hr < 12:
                hr += 12
            elif "am" in s.lower() and hr == 12:
                hr = 0
        else:
            return s

    end_hr = (hr + 1) % 24
    def to_12h(h, m):
        ampm = "AM" if h < 12 else "PM"
        h12 = h if (1 <= h <= 12) else (12 if h in [0, 12] else h - 12)
        return f"{h12:02d}:{m:02d} {ampm}"

    return f"{to_12h(hr, mn)} – {to_12h(end_hr, mn)}"

def normalize_student_level(raw_level: str, config: SystemConfig) -> str:
    if not raw_level:
        return "Beginner 1"
    raw_clean = re.sub(r'[\s_\-]+', '', raw_level.strip().lower())
    for cfg_level in config.student_levels:
        cfg_clean = re.sub(r'[\s_\-]+', '', cfg_level.lower())
        if raw_clean == cfg_clean or raw_clean in cfg_clean or cfg_clean in raw_clean:
            return cfg_level
    # Fallback mappings for broad levels
    if "early" in raw_clean and "intermediate" in raw_clean:
        return "Early Intermediate 1"
    if "intermediate" in raw_clean:
        return "Intermediate"
    if "basic" in raw_clean:
        return "Basic 1"
    if "beginner" in raw_clean:
        return "Beginner 1"
    return "Beginner 1"

def parse_monthly_schedule_workbook(
    file_bytes: bytes,
    config: SystemConfig
) -> Tuple[List[StudentModel], List[CoachModel], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Parses a monthly matrix Excel schedule workbook (like the reference September/October workbook).
    Extracts:
    1. Students with full batch identity (e.g. G Beginner1), level, rating, planned classes, and day preferences.
    2. Coaches that appear in the sheet, mapped to master configs/defaults.
    3. Learned recurring batch templates.
    """
    errors: List[ExcelParsingError] = []
    students: List[StudentModel] = []
    discovered_batches: List[Dict[str, Any]] = []

    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    except Exception as e:
        errors.append(ExcelParsingError("Workbook", 0, "File", f"Failed to open Excel: {e}"))
        return [], [], [e.to_dict() for e in errors], []

    ws = wb.active
    # Detect header row
    header_row_idx = None
    col_map = {}

    for r in range(1, 6):
        vals = [str(ws.cell(r, c).value or "").strip().lower() for c in range(1, min(ws.max_column + 1, 20))]
        if any("student name" in v for v in vals):
            header_row_idx = r
            break

    if not header_row_idx:
        errors.append(ExcelParsingError(ws.title, 1, "Header", "Could not locate 'Student Name' header row"))
        return [], [], [e.to_dict() for e in errors], []

    # Map column positions
    for c in range(1, ws.max_column + 1):
        v_h = str(ws.cell(header_row_idx, c).value or "").strip().lower()
        v_r1 = str(ws.cell(1, c).value or "").strip().lower()
        v_r2 = str(ws.cell(2, c).value or "").strip().lower()

        if "student name" in v_h:
            col_map["name"] = c
        elif "stud id" in v_h or "student id" in v_h:
            col_map["id"] = c
        elif "rating" in v_h or "mkca" in v_h:
            col_map["rating"] = c
        elif "level" in v_h:
            col_map["level"] = c
        elif "batch" in v_h:
            col_map["batch"] = c

        if "planned" in v_r1 or "planned" in v_r2 or "planned" in v_h:
            col_map["planned"] = c
        if "actual" in v_r1 or "actual" in v_r2 or "actual" in v_h:
            col_map["actual"] = c

    # Fallbacks if columns missing
    if "name" not in col_map:
        col_map["name"] = 1
    if "id" not in col_map:
        col_map["id"] = 2
    if "level" not in col_map:
        col_map["level"] = 4
    if "batch" not in col_map:
        col_map["batch"] = 5
    if "planned" not in col_map:
        col_map["planned"] = 6

    # Detect day columns
    # In reference format: alternating Time and Coach columns with day name in row 1
    date_cols: Dict[int, Tuple[str, str]] = {}
    for c in range(1, ws.max_column + 1):
        d_val = ws.cell(header_row_idx, c).value
        day_val = ws.cell(1, c).value
        if d_val is not None and (isinstance(d_val, (datetime.datetime, datetime.date)) or re.search(r'\d{4}-\d{2}-\d{2}', str(d_val))):
            d_str = str(d_val)[:10]
            # Infer day name from date if missing in row 1
            if not day_val:
                try:
                    dt = datetime.datetime.strptime(d_str, "%Y-%m-%d")
                    day_str = dt.strftime("%A")
                except Exception:
                    day_str = ""
            else:
                day_str = str(day_val).strip()
            date_cols[c] = (d_str, day_str)

    # Batch recurring patterns tracking
    batch_slots = defaultdict(lambda: {
        "level": "Beginner 1",
        "batch_type": "G",
        "slots": Counter(),
        "coaches": Counter(),
        "students": set()
    })

    coaches_found = set()

    for r in range(header_row_idx + 1, ws.max_row + 1):
        s_name = ws.cell(r, col_map["name"]).value
        s_id = ws.cell(r, col_map["id"]).value
        if not s_name or not s_id:
            continue
        s_name = str(s_name).strip().replace("\n", " ")
        s_id = str(s_id).strip()

        # Skip headers or notes
        if "student name" in s_name.lower() or "trainer" in s_name.lower():
            continue

        s_level_raw = str(ws.cell(r, col_map.get("level", 4)).value or "Beginner 1").strip()
        s_level = normalize_student_level(s_level_raw, config)

        s_batch_raw = str(ws.cell(r, col_map.get("batch", 5)).value or "G Beginner1").strip()
        prefix = s_batch_raw[:1].upper() if s_batch_raw else "G"
        b_type = prefix if prefix in ["G", "L", "I"] else "G"

        s_planned_raw = ws.cell(r, col_map.get("planned", 6)).value
        try:
            req_classes = int(s_planned_raw) if s_planned_raw is not None else 8
        except (ValueError, TypeError):
            req_classes = 8

        s_rating_raw = ws.cell(r, col_map.get("rating", 3)).value if "rating" in col_map else None
        mkca_rating = None
        try:
            if s_rating_raw is not None:
                mkca_rating = float(s_rating_raw)
        except (ValueError, TypeError):
            pass

        # Check student attendance across dates to discover preferences
        stu_day_times = defaultdict(list)
        for c, (d_str, day_name) in date_cols.items():
            t_val = ws.cell(r, c).value
            c_val = ws.cell(r, c + 1).value
            if t_val:
                t_formatted = format_time_slot_str(t_val)
                c_clean = str(c_val).strip() if c_val else ""
                if c_clean and c_clean.lower() != "none":
                    coaches_found.add(c_clean)
                    batch_slots[s_batch_raw]["coaches"][c_clean] += 1

                if day_name:
                    stu_day_times[day_name].append(t_formatted)
                    batch_slots[s_batch_raw]["slots"][(day_name, t_formatted)] += 1

        batch_slots[s_batch_raw]["students"].add(s_id)
        batch_slots[s_batch_raw]["level"] = s_level
        batch_slots[s_batch_raw]["batch_type"] = b_type

        # Build day preferences
        day_prefs = {}
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            times_list = stu_day_times.get(day, [])
            if times_list:
                top_time = Counter(times_list).most_common(1)[0][0]
                day_prefs[day] = top_time
            else:
                day_prefs[day] = "No Preference"

        student = StudentModel(
            student_id=s_id,
            student_name=s_name,
            student_level=s_level,
            batch_type=b_type,
            batch=s_batch_raw,
            mkca_rating=mkca_rating,
            required_classes=req_classes,
            mon_pref=day_prefs.get("Monday", "No Preference"),
            tue_pref=day_prefs.get("Tuesday", "No Preference"),
            wed_pref=day_prefs.get("Wednesday", "No Preference"),
            thu_pref=day_prefs.get("Thursday", "No Preference"),
            fri_pref=day_prefs.get("Friday", "No Preference"),
            sat_pref=day_prefs.get("Saturday", "No Preference"),
            sun_pref=day_prefs.get("Sunday", "No Preference"),
            tournament_pref="No",
            additional_comments=""
        )
        students.append(student)

    # Build Master Batches from discovered batch patterns
    batch_counter = 1
    for b_name, b_info in batch_slots.items():
        top_slots = [f"{day} {ts}" for (day, ts), cnt in b_info["slots"].most_common(5) if cnt >= 1]
        top_coach_tuple = b_info["coaches"].most_common(1)
        fixed_trainer = top_coach_tuple[0][0] if top_coach_tuple else "Unassigned"
        # Normalize coach name
        c_lower = fixed_trainer.lower()
        if c_lower in COACH_ALIAS_MAP:
            fixed_trainer = COACH_ALIAS_MAP[c_lower]

        b_type = b_info["batch_type"]
        lvl = b_info["level"]
        cap_min = 1 if b_type == "I" else (2 if b_type == "L" else 4)
        cap_max = 1 if b_type == "I" else (4 if b_type == "L" else 10)

        discovered_batches.append({
            "batch_id": f"MKB{str(batch_counter).zfill(3)}",
            "batch_name": b_name,
            "batch_type": b_type,
            "level": lvl,
            "capacity_min": cap_min,
            "capacity_max": cap_max,
            "fixed_trainer": fixed_trainer,
            "schedule_timings": " / ".join(top_slots[:4]),
            "weekly_slots": top_slots,
            "student_ids": list(b_info["students"]),
            "student_count": len(b_info["students"]),
            "notes": f"Learned from reference workbook schedule."
        })
        batch_counter += 1

    # Build Coaches list
    existing_data = load_master_data_db()
    existing_coaches_map = {c["coach_name"].strip().lower(): CoachModel(**c) for c in existing_data.get("coaches", [])}

    coaches: List[CoachModel] = []
    all_coach_keys = set(COACH_ALIAS_MAP.values())
    for raw_c in coaches_found:
        c_clean = raw_c.strip().lower()
        resolved = COACH_ALIAS_MAP.get(c_clean, raw_c.strip().title())
        all_coach_keys.add(resolved)

    for c_name in sorted(list(all_coach_keys)):
        c_key = c_name.lower()
        if c_key in existing_coaches_map:
            coaches.append(existing_coaches_map[c_key])
        elif c_key in STANDARD_COACH_DEFAULTS:
            coaches.append(CoachModel(**STANDARD_COACH_DEFAULTS[c_key]))
        else:
            coaches.append(CoachModel(
                coach_name=c_name,
                levels_handled=list(config.student_levels),
                monthly_capacity_min=20,
                monthly_capacity_max=60,
                mon_max=4, tue_max=4, wed_max=4, thu_max=4, fri_max=4, sat_max=5, sun_max=2,
                sunday_pref="Available",
                preferred_timings="No Preference"
            ))

    # Persist discovered master batches to DB if discovered
    if discovered_batches:
        try:
            save_all_master_batches_db(discovered_batches)
        except Exception:
            pass

    return students, coaches, [e.to_dict() for e in errors], discovered_batches


def parse_excel_file(
    file_contents: Union[str, bytes, io.BytesIO], 
    config: SystemConfig = DEFAULT_CONFIG
) -> Tuple[List[StudentModel], List[CoachModel], List[Dict[str, Any]]]:
    """
    Reads an uploaded Excel file, automatically detecting:
    1. Monthly Schedule Matrix format (reference schedule like September/October).
    2. Master Data format (sheets 'Students' and 'Coaches').
    Returns parsed students, coaches, and error dicts.
    """
    if isinstance(file_contents, str):
        with open(file_contents, "rb") as f:
            bytes_data = f.read()
    elif isinstance(file_contents, io.BytesIO):
        bytes_data = file_contents.getvalue()
    else:
        bytes_data = file_contents

    # Check if this is a Monthly Matrix sheet
    try:
        wb = openpyxl.load_workbook(io.BytesIO(bytes_data), data_only=True)
        sheet_names_lower = [s.strip().lower() for s in wb.sheetnames]
        has_coaches_sheet = any("coach" in s for s in sheet_names_lower)
        
        if not has_coaches_sheet:
            ws = wb.active
            # Look for monthly schedule signatures (Student Name + date columns)
            is_monthly = False
            for r in range(1, 6):
                row_vals = [str(ws.cell(r, c).value or "").strip().lower() for c in range(1, min(ws.max_column + 1, 25))]
                if any("student name" in v for v in row_vals) and any("stud id" in v or "batch" in v for v in row_vals):
                    # Check if there are date columns
                    has_date_cols = any(
                        isinstance(ws.cell(r, c).value, (datetime.datetime, datetime.date))
                        or re.search(r'\d{4}-\d{2}-\d{2}', str(ws.cell(r, c).value or ""))
                        for c in range(1, ws.max_column + 1)
                    )
                    if has_date_cols:
                        is_monthly = True
                        break

            if is_monthly:
                students, coaches, errors, _ = parse_monthly_schedule_workbook(bytes_data, config)
                if students:
                    return students, coaches, errors
    except Exception:
        pass

    # Standard Multi-Sheet Parser
    errors: List[ExcelParsingError] = []
    students: List[StudentModel] = []
    coaches: List[CoachModel] = []

    try:
        excel_file = pd.ExcelFile(io.BytesIO(bytes_data), engine="openpyxl")
    except Exception as e:
        errors.append(ExcelParsingError("Workbook", 0, "File", f"Failed to open Excel file: {str(e)}"))
        return [], [], [e.to_dict() for e in errors]

    sheet_names = excel_file.sheet_names
    sheet_map = {s.strip().lower(): s for s in sheet_names}

    student_sheet_name = None
    for k in ["students", "student", "student data", "students data"]:
        if k in sheet_map:
            student_sheet_name = sheet_map[k]
            break
    if not student_sheet_name and len(sheet_names) > 0:
        student_sheet_name = sheet_names[0]

    coach_sheet_name = None
    for k in ["coaches", "coach", "coach data", "coaches data"]:
        if k in sheet_map:
            coach_sheet_name = sheet_map[k]
            break
    if not coach_sheet_name and len(sheet_names) > 1:
        coach_sheet_name = sheet_names[1]

    # Parse Students Sheet
    if student_sheet_name:
        try:
            df_students = pd.read_excel(excel_file, sheet_name=student_sheet_name)
            df_students.columns = [normalize_header(c) for c in df_students.columns]

            col_map = {}
            for col in df_students.columns:
                c = col.strip().lower()
                if c in ["student_id", "id", "unique_student_id", "student id", "stud_id"] or c.endswith("_id"):
                    col_map["student_id"] = col
                elif c in ["student_name", "name", "student name", "fullname", "full name"]:
                    col_map["student_name"] = col
                elif c in ["student_level", "level", "student level"]:
                    col_map["student_level"] = col
                elif c in ["batch_type", "batch", "batch type", "symbol"]:
                    col_map["batch_type"] = col
                elif "rating" in c or "mkca" in c:
                    col_map["mkca_rating"] = col
                elif c in ["region_timezone", "region", "timezone", "zone"]:
                    col_map["region_timezone"] = col
                elif c in ["required_classes", "classes_required", "required number of classes", "classes", "planned_classes", "planned"]:
                    col_map["required_classes"] = col
                elif "mon" in c:
                    col_map["mon_pref"] = col
                elif "tue" in c:
                    col_map["tue_pref"] = col
                elif "wed" in c:
                    col_map["wed_pref"] = col
                elif "thu" in c:
                    col_map["thu_pref"] = col
                elif "fri" in c:
                    col_map["fri_pref"] = col
                elif "sat" in c:
                    col_map["sat_pref"] = col
                elif "sun" in c:
                    col_map["sun_pref"] = col
                elif "tournament" in c:
                    col_map["tournament_pref"] = col
                elif "comment" in c or "note" in c or "additional" in c:
                    col_map["additional_comments"] = col

            if "student_id" not in col_map and len(df_students.columns) > 0:
                col_map["student_id"] = df_students.columns[0]
            if "student_name" not in col_map and len(df_students.columns) > 1:
                col_map["student_name"] = df_students.columns[1]

            for idx, row in df_students.iterrows():
                row_num = idx + 2
                s_id = str(row.get(col_map.get("student_id", ""), "")).strip()
                s_name = str(row.get(col_map.get("student_name", ""), "")).strip()
                s_level = str(row.get(col_map.get("student_level", ""), "")).strip()
                s_batch_raw = str(row.get(col_map.get("batch_type", ""), "G")).strip()

                if not s_id or s_id.lower() == "nan":
                    s_id = f"STU_{idx+1:03d}"
                    errors.append(ExcelParsingError(student_sheet_name, row_num, "Student ID", "Missing Student ID; auto-assigned fallback ID", "WARNING"))

                if not s_name or s_name.lower() in ["nan", "none", "", "null"]:
                    continue

                if not s_level or s_level.lower() in ["nan", "none", "", "null"]:
                    continue

                matched_level = normalize_student_level(s_level, config)
                prefix = s_batch_raw[:1].upper() if s_batch_raw else "G"
                b_type = prefix if prefix in ["G", "L", "I"] else "G"

                req_classes_raw = row.get(col_map.get("required_classes", ""), 8)
                try:
                    req_classes = int(req_classes_raw) if not pd.isna(req_classes_raw) else 8
                except (ValueError, TypeError):
                    req_classes = 8

                rating_raw = row.get(col_map.get("mkca_rating", ""), None) if "mkca_rating" in col_map else None
                mkca_rating = None
                try:
                    if rating_raw is not None and not pd.isna(rating_raw):
                        mkca_rating = float(rating_raw)
                except Exception:
                    pass

                student = StudentModel(
                    student_id=s_id,
                    student_name=s_name,
                    student_level=matched_level,
                    batch_type=b_type,
                    batch=s_batch_raw,
                    mkca_rating=mkca_rating,
                    region_timezone=str(row.get(col_map.get("region_timezone", ""), "IST")),
                    required_classes=req_classes,
                    mon_pref=str(row.get(col_map.get("mon_pref", ""), "No Preference")),
                    tue_pref=str(row.get(col_map.get("tue_pref", ""), "No Preference")),
                    wed_pref=str(row.get(col_map.get("wed_pref", ""), "No Preference")),
                    thu_pref=str(row.get(col_map.get("thu_pref", ""), "No Preference")),
                    fri_pref=str(row.get(col_map.get("fri_pref", ""), "No Preference")),
                    sat_pref=str(row.get(col_map.get("sat_pref", ""), "No Preference")),
                    sun_pref=str(row.get(col_map.get("sun_pref", ""), "No Preference")),
                    tournament_pref=str(row.get(col_map.get("tournament_pref", ""), "No")),
                    additional_comments=str(row.get(col_map.get("additional_comments", ""), "")) if not pd.isna(row.get(col_map.get("additional_comments", ""), "")) else ""
                )
                students.append(student)

        except Exception as e:
            errors.append(ExcelParsingError(student_sheet_name or "Students", 0, "Sheet", f"Error parsing Students sheet: {str(e)}"))

    # Parse Coaches Sheet
    if coach_sheet_name:
        try:
            df_coaches = pd.read_excel(excel_file, sheet_name=coach_sheet_name)
            df_coaches.columns = [normalize_header(c) for c in df_coaches.columns]

            col_map = {}
            for col in df_coaches.columns:
                c = col.strip().lower()
                if c in ["coach_name", "coach name", "name", "coach", "coaches", "trainer", "faculty"]:
                    col_map["coach_name"] = col
                elif "level" in c or "capability" in c or "can_handle" in c or "handled" in c:
                    col_map["levels_handled"] = col
                elif "capacity" in c or "monthly" in c or "limit" in c or "target" in c:
                    col_map["monthly_capacity"] = col
                elif "mon" in c:
                    col_map["mon_max"] = col
                elif "tue" in c:
                    col_map["tue_max"] = col
                elif "wed" in c:
                    col_map["wed_max"] = col
                elif "thu" in c:
                    col_map["thu_max"] = col
                elif "fri" in c:
                    col_map["fri_max"] = col
                elif "sat" in c:
                    col_map["sat_max"] = col
                elif "sun" in c and "max" in c:
                    col_map["sun_max"] = col
                elif "sun" in c and ("pref" in c or "preference" in c):
                    col_map["sunday_pref"] = col
                elif "sun" in c:
                    col_map["sun_max"] = col
                elif "timing" in c or "preferred" in c:
                    col_map["preferred_timings"] = col
                elif "special" in c or "comment" in c:
                    col_map["special_comments"] = col
                elif "exception" in c:
                    col_map["temporary_exceptions"] = col

            if "coach_name" not in col_map and len(df_coaches.columns) > 0:
                col_map["coach_name"] = df_coaches.columns[0]

            for idx, row in df_coaches.iterrows():
                row_num = idx + 2
                c_name = str(row.get(col_map.get("coach_name", df_coaches.columns[0] if len(df_coaches.columns) > 0 else ""), "")).strip()

                if not c_name or c_name.lower() in ["nan", "none", "null", ""]:
                    continue

                raw_levels = row.get(col_map.get("levels_handled", ""), "")
                handled_levels = parse_levels_list(raw_levels)

                valid_handled = []
                for hl in handled_levels:
                    valid_handled.append(normalize_student_level(hl, config))

                if not valid_handled:
                    valid_handled = list(config.student_levels)

                raw_monthly = row.get(col_map.get("monthly_capacity", ""), "30-60")
                cap_min, cap_max = parse_capacity_range(raw_monthly)

                def get_int_col(col_key: str, default_val: int) -> int:
                    val = row.get(col_map.get(col_key, ""), default_val)
                    try:
                        return int(val) if not pd.isna(val) else default_val
                    except (ValueError, TypeError):
                        return default_val

                coach = CoachModel(
                    coach_name=c_name,
                    levels_handled=valid_handled,
                    monthly_capacity_min=cap_min,
                    monthly_capacity_max=cap_max,
                    mon_max=get_int_col("mon_max", 4),
                    tue_max=get_int_col("tue_max", 4),
                    wed_max=get_int_col("wed_max", 4),
                    thu_max=get_int_col("thu_max", 4),
                    fri_max=get_int_col("fri_max", 4),
                    sat_max=get_int_col("sat_max", 5),
                    sun_max=get_int_col("sun_max", 2),
                    preferred_timings=str(row.get(col_map.get("preferred_timings", ""), "No Preference")),
                    sunday_pref=str(row.get(col_map.get("sunday_pref", ""), "Available")),
                    sunday_max_classes=get_int_col("sun_max", 2),
                    special_comments=str(row.get(col_map.get("special_comments", ""), "")) if not pd.isna(row.get(col_map.get("special_comments", ""), "")) else "",
                    temporary_exceptions=str(row.get(col_map.get("temporary_exceptions", ""), "")) if not pd.isna(row.get(col_map.get("temporary_exceptions", ""), "")) else ""
                )
                coaches.append(coach)

        except Exception as e:
            errors.append(ExcelParsingError(coach_sheet_name or "Coaches", 0, "Sheet", f"Error parsing Coaches sheet: {str(e)}"))

    return students, coaches, [e.to_dict() for e in errors]
