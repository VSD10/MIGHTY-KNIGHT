import io
import re
from typing import List, Dict, Tuple, Any, Union
import pandas as pd
from app.models.student import StudentModel
from app.models.coach import CoachModel
from app.config import DEFAULT_CONFIG, SystemConfig

class ExcelParsingError:
    def __init__(self, sheet: str, row: int, column: str, message: str, severity: str = "ERROR"):
        self.sheet = sheet
        self.row = row
        self.column = column
        self.message = message
        self.severity = severity # ERROR or WARNING

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
    # Check if range format like "60-90" or "60–90"
    match = re.search(r'(\d+)\s*[\-–—:]\s*(\d+)', val_str)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    # Single number
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
    # Split by comma, semicolon, newline, or pipe
    parts = re.split(r'[,;|\n]+', val_str)
    return [p.strip() for p in parts if p.strip()]

def parse_excel_file(
    file_contents: Union[str, bytes, io.BytesIO], 
    config: SystemConfig = DEFAULT_CONFIG
) -> Tuple[List[StudentModel], List[CoachModel], List[Dict[str, Any]]]:
    """
    Reads an uploaded Excel file, maps columns to models, performs row-level validation,
    and returns parsed students, coaches, and a list of error/warning dicts.
    Never crashes on invalid rows.
    """
    errors: List[ExcelParsingError] = []
    students: List[StudentModel] = []
    coaches: List[CoachModel] = []

    try:
        if isinstance(file_contents, bytes):
            excel_file = pd.ExcelFile(io.BytesIO(file_contents), engine="openpyxl")
        else:
            excel_file = pd.ExcelFile(file_contents, engine="openpyxl")
    except Exception as e:
        errors.append(ExcelParsingError("Workbook", 0, "File", f"Failed to open Excel file: {str(e)}"))
        return [], [], [e.to_dict() for e in errors]

    sheet_names = excel_file.sheet_names
    sheet_map = {s.strip().lower(): s for s in sheet_names}

    # Find Students Sheet
    student_sheet_name = None
    for k in ["students", "student", "student data", "students data"]:
        if k in sheet_map:
            student_sheet_name = sheet_map[k]
            break
    if not student_sheet_name and len(sheet_names) > 0:
        student_sheet_name = sheet_names[0] # Fallback to first sheet

    # Find Coaches Sheet
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
                if c in ["student_id", "id", "unique_student_id", "student id"] or c.endswith("_id"):
                    col_map["student_id"] = col
                elif c in ["student_name", "name", "student name", "fullname", "full name"]:
                    col_map["student_name"] = col
                elif c in ["student_level", "level", "student level"]:
                    col_map["student_level"] = col
                elif c in ["batch_type", "batch", "batch type", "symbol"]:
                    col_map["batch_type"] = col
                elif c in ["region_timezone", "region", "timezone", "zone"]:
                    col_map["region_timezone"] = col
                elif c in ["required_classes", "classes_required", "required number of classes", "classes"]:
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

            # Fallbacks for student_id and student_name if missing
            if "student_id" not in col_map and len(df_students.columns) > 0:
                col_map["student_id"] = df_students.columns[0]
            if "student_name" not in col_map and len(df_students.columns) > 1:
                col_map["student_name"] = df_students.columns[1]

            for idx, row in df_students.iterrows():
                row_num = idx + 2 # Excel 1-indexed header is row 1
                
                # Check required fields
                s_id = str(row.get(col_map.get("student_id", ""), "")).strip()
                s_name = str(row.get(col_map.get("student_name", ""), "")).strip()
                s_level = str(row.get(col_map.get("student_level", ""), "")).strip()
                s_batch = str(row.get(col_map.get("batch_type", ""), "")).strip().upper()

                if not s_id or s_id.lower() == "nan":
                    s_id = f"STU_{idx+1:03d}" # Auto-generate ID if missing with warning
                    errors.append(ExcelParsingError(student_sheet_name, row_num, "Student ID", "Missing Student ID; auto-assigned fallback ID", "WARNING"))

                if not s_name or s_name.lower() in ["nan", "none", "", "null"]:
                    errors.append(ExcelParsingError(student_sheet_name, row_num, "Student Name", "Missing Student Name; row skipped", "WARNING"))
                    continue

                if not s_level or s_level.lower() in ["nan", "none", "", "null"]:
                    errors.append(ExcelParsingError(student_sheet_name, row_num, "Student Level", f"Missing Student Level for {s_name}; row skipped", "WARNING"))
                    continue

                # Normalize level matching
                matched_level = None
                for cfg_level in config.student_levels:
                    if cfg_level.lower() == s_level.lower():
                        matched_level = cfg_level
                        break
                if not matched_level:
                    # Fuzzy level match
                    for cfg_level in config.student_levels:
                        if re.sub(r'[\s_\-]+', '', s_level.lower()) == re.sub(r'[\s_\-]+', '', cfg_level.lower()):
                            matched_level = cfg_level
                            break
                if not matched_level:
                    errors.append(ExcelParsingError(student_sheet_name, row_num, "Student Level", f"Invalid Student Level '{s_level}' for {s_name}"))
                    continue

                if not s_batch or s_batch not in config.batch_types:
                    errors.append(ExcelParsingError(student_sheet_name, row_num, "Batch Type", f"Invalid Batch Type '{s_batch}' for {s_name}. Defaulting to 'G'", "WARNING"))
                    s_batch = "G"

                # Parse required classes
                req_classes_raw = row.get(col_map.get("required_classes", ""), 8)
                try:
                    req_classes = int(req_classes_raw) if not pd.isna(req_classes_raw) else 8
                except (ValueError, TypeError):
                    req_classes = 8
                    errors.append(ExcelParsingError(student_sheet_name, row_num, "Required Classes", f"Invalid Required Classes number for {s_name}; defaulting to 8", "WARNING"))

                student = StudentModel(
                    student_id=s_id,
                    student_name=s_name,
                    student_level=matched_level,
                    batch_type=s_batch,
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

            # Fallback if coach_name column wasn't matched explicitly
            if "coach_name" not in col_map and len(df_coaches.columns) > 0:
                col_map["coach_name"] = df_coaches.columns[0]

            for idx, row in df_coaches.iterrows():
                row_num = idx + 2
                c_name = str(row.get(col_map.get("coach_name", df_coaches.columns[0] if len(df_coaches.columns) > 0 else ""), "")).strip()

                if not c_name or c_name.lower() in ["nan", "none", "null", ""]:
                    errors.append(ExcelParsingError(coach_sheet_name, row_num, "Coach Name", "Missing Coach Name; row skipped", "WARNING"))
                    continue

                raw_levels = row.get(col_map.get("levels_handled", ""), "")
                handled_levels = parse_levels_list(raw_levels)

                # Validate handled levels against config
                valid_handled = []
                for hl in handled_levels:
                    match_found = False
                    for cfg_lvl in config.student_levels:
                        hl_clean = re.sub(r'[\s_\-]+', '', hl.lower())
                        cfg_clean = re.sub(r'[\s_\-]+', '', cfg_lvl.lower())
                        if hl_clean == cfg_clean or hl_clean in cfg_clean or cfg_clean in hl_clean:
                            valid_handled.append(cfg_lvl)
                            match_found = True
                            break
                    if not match_found:
                        valid_handled.append(hl) # preserve raw level

                # Fallback: If no levels specified, coach can handle all configured levels
                if not valid_handled:
                    valid_handled = list(config.student_levels)

                # Capacity parsing
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
