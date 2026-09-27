import io
import re
import calendar
from datetime import datetime, date
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.models.schedule import ScheduleResult, ScheduledClass
from app.models.student import StudentModel
from app.models.coach import CoachModel
from app.config import SystemConfig, DEFAULT_CONFIG
from app.engine.validator import validate_schedule_state
from app.engine.time_utils import generate_date_range, get_day_name

def generate_monthly_matrix_excel(
    result: ScheduleResult,
    students: List[StudentModel],
    coaches: List[CoachModel],
    config: SystemConfig = DEFAULT_CONFIG
) -> Tuple[bytes, bool, List[str]]:
    """
    Generates a full monthly Excel schedule following the exact structure of the reference workbook.
    - Matches selected month dynamically (28, 29, 30, or 31 days).
    - Preserves columns: Student Name, Stud ID, MKCA Rating, Level, Batch, Planned Classes,
      Actual Classes, Date columns (Time and Coach alternating), Comments.
    - Automatically validates the schedule state before finalizing.
    - If validation fails, marks output as DRAFT / VALIDATION FAILED and lists errors.
    """
    # 1. Server-side integrity validation
    schedule_dict = result.model_dump()
    student_dicts = [s.model_dump() for s in students]
    coach_dicts = [c.model_dump() for c in coaches]
    is_valid, violations = validate_schedule_state(schedule_dict, student_dicts, coach_dicts, config)

    # 2. Parse dates
    start_date = datetime.strptime(result.start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(result.end_date, "%Y-%m-%d").date()
    target_dates = generate_date_range(start_date, end_date)
    num_days = len(target_dates)

    wb = openpyxl.Workbook()
    # Sheet name e.g. Oct26, Nov26
    sheet_name = f"{start_date.strftime('%b%y')}"
    ws = wb.active
    ws.title = sheet_name

    # Styles
    font_family = "Segoe UI"
    header_fill_dark = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid") # Dark slate
    header_fill_gold = PatternFill(start_color="D97706", end_color="D97706", fill_type="solid") # Amber gold
    header_fill_blue = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid") # Sky blue
    zebra_even = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    alert_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid") # Light red
    success_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid") # Light green

    font_header = Font(name=font_family, size=10, bold=True, color="FFFFFF")
    font_gold_header = Font(name=font_family, size=10, bold=True, color="FFFFFF")
    font_bold = Font(name=font_family, size=9, bold=True, color="0F172A")
    font_regular = Font(name=font_family, size=9, color="1E293B")
    font_alert = Font(name=font_family, size=9, bold=True, color="B91C1C")
    font_success = Font(name=font_family, size=9, bold=True, color="15803D")

    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center")

    # Map student scheduled classes: (student_id, date_str) -> (time_slot, coach_name)
    student_date_classes: Dict[Tuple[str, str], Tuple[str, str]] = {}
    student_scheduled_totals: Dict[str, int] = defaultdict(int)

    for cls in result.scheduled_classes:
        for sid in cls.student_ids:
            student_date_classes[(sid, cls.date)] = (cls.time_slot, cls.coach_name)
            student_scheduled_totals[sid] += 1

    # Map unscheduled diagnostics
    unscheduled_map = {u.student_id: u for u in result.unscheduled_records}

    # 3. Write Headers
    # Row 1: Planned Classes header & Day of week names
    ws.cell(row=1, column=6, value="Planned Classes").fill = header_fill_gold
    ws.cell(row=1, column=6).font = font_gold_header
    ws.cell(row=1, column=6).alignment = align_center

    # Row 2: Actual Classes header
    ws.cell(row=2, column=7, value="Actual Classes").fill = header_fill_gold
    ws.cell(row=2, column=7).font = font_gold_header
    ws.cell(row=2, column=7).alignment = align_center

    # Row 3: Standard column titles
    fixed_headers = [
        (1, "Student Name"),
        (2, "Stud ID"),
        (3, "MKCA Rating"),
        (4, "Level"),
        (5, "Batch")
    ]
    for col_idx, text in fixed_headers:
        c_cell = ws.cell(row=3, column=col_idx, value=text)
        c_cell.fill = header_fill_dark
        c_cell.font = font_header
        c_cell.alignment = align_center
        c_cell.border = thin_border

    # Date columns starting at column 8
    cur_col = 8
    date_col_map: Dict[str, int] = {} # date_str -> time_col_idx

    for d_obj in target_dates:
        d_str = d_obj.strftime("%Y-%m-%d")
        day_name = get_day_name(d_obj)
        date_col_map[d_str] = cur_col

        # Row 1: Day of week (e.g. Thursday)
        c_r1 = ws.cell(row=1, column=cur_col, value=day_name)
        c_r1.fill = header_fill_dark
        c_r1.font = font_header
        c_r1.alignment = align_center
        c_r1.border = thin_border

        # Row 3: Date (YYYY-MM-DD)
        c_r3_time = ws.cell(row=3, column=cur_col, value=d_str)
        c_r3_time.fill = header_fill_dark
        c_r3_time.font = font_header
        c_r3_time.alignment = align_center
        c_r3_time.border = thin_border

        # Row 3: Coach column header
        c_r3_coach = ws.cell(row=3, column=cur_col + 1, value="Coach")
        c_r3_coach.fill = header_fill_dark
        c_r3_coach.font = font_header
        c_r3_coach.alignment = align_center
        c_r3_coach.border = thin_border

        cur_col += 2

    # Comments column
    comments_col = cur_col
    c_comm = ws.cell(row=1, column=comments_col, value="Comments")
    c_comm.fill = header_fill_dark
    c_comm.font = font_header
    c_comm.alignment = align_center
    c_comm.border = thin_border

    c_comm3 = ws.cell(row=3, column=comments_col, value="Comments")
    c_comm3.fill = header_fill_dark
    c_comm3.font = font_header
    c_comm3.alignment = align_center
    c_comm3.border = thin_border

    # 4. Write Student Rows
    cur_row = 4
    for idx, s in enumerate(students):
        sid = s.student_id
        is_even = (idx % 2 == 0)
        row_fill = zebra_even if is_even else None

        actual_cnt = student_scheduled_totals[sid]
        deficit_cnt = max(0, s.required_classes - actual_cnt)
        is_fully_scheduled = (deficit_cnt == 0)

        # Col 1: Name
        c1 = ws.cell(row=cur_row, column=1, value=s.student_name)
        c1.font = font_bold
        c1.alignment = align_left
        c1.border = thin_border

        # Col 2: Stud ID
        c2 = ws.cell(row=cur_row, column=2, value=sid)
        c2.font = font_regular
        c2.alignment = align_center
        c2.border = thin_border

        # Col 3: MKCA Rating
        c3 = ws.cell(row=cur_row, column=3, value=s.mkca_rating if s.mkca_rating is not None else "-")
        c3.font = font_regular
        c3.alignment = align_center
        c3.border = thin_border

        # Col 4: Level
        c4 = ws.cell(row=cur_row, column=4, value=s.student_level)
        c4.font = font_regular
        c4.alignment = align_left
        c4.border = thin_border

        # Col 5: Batch
        c5 = ws.cell(row=cur_row, column=5, value=s.get_batch_identity())
        c5.font = font_regular
        c5.alignment = align_left
        c5.border = thin_border

        # Col 6: Planned Classes
        c6 = ws.cell(row=cur_row, column=6, value=s.required_classes)
        c6.font = font_bold
        c6.alignment = align_center
        c6.border = thin_border

        # Col 7: Actual Classes
        c7 = ws.cell(row=cur_row, column=7, value=actual_cnt)
        c7.font = font_success if is_fully_scheduled else font_alert
        c7.fill = success_fill if is_fully_scheduled else alert_fill
        c7.alignment = align_center
        c7.border = thin_border

        # Date columns
        for d_obj in target_dates:
            d_str = d_obj.strftime("%Y-%m-%d")
            c_idx = date_col_map[d_str]

            if (sid, d_str) in student_date_classes:
                t_slot, c_name = student_date_classes[(sid, d_str)]
                time_cell = ws.cell(row=cur_row, column=c_idx, value=t_slot)
                time_cell.font = font_regular
                time_cell.alignment = align_center
                time_cell.border = thin_border

                coach_cell = ws.cell(row=cur_row, column=c_idx + 1, value=c_name)
                coach_cell.font = font_regular
                coach_cell.alignment = align_center
                coach_cell.border = thin_border
            else:
                ws.cell(row=cur_row, column=c_idx, value=None).border = thin_border
                ws.cell(row=cur_row, column=c_idx + 1, value=None).border = thin_border

        # Comments column
        if is_fully_scheduled:
            comment_text = "Scheduled"
            comment_font = font_success
        else:
            u_rec = unscheduled_map.get(sid)
            reason = getattr(u_rec, "failure_reason", "Quota deficit") if u_rec else "Quota deficit"
            comment_text = f"ATTENTION REQUIRED: {deficit_cnt} class deficit ({reason})"
            comment_font = font_alert

        comm_cell = ws.cell(row=cur_row, column=comments_col, value=comment_text)
        comm_cell.font = comment_font
        comm_cell.alignment = align_left
        comm_cell.border = thin_border

        cur_row += 1

    # 5. Add Validation Summary Banner / Sheet if violations exist
    if not is_valid:
        ws_banner = wb.create_sheet(title="VALIDATION ALERTS", index=0)
        ws_banner.cell(row=1, column=1, value="⚠️ SCHEDULE VALIDATION FAILED - DRAFT STATUS").font = Font(name=font_family, size=14, bold=True, color="DC2626")
        ws_banner.cell(row=2, column=1, value=f"Total Constraint Violations Detected: {len(violations)}").font = Font(name=font_family, size=11, bold=True)
        ws_banner.cell(row=3, column=1, value="The schedule cannot be marked Finalized until all hard constraint violations are resolved.").font = Font(name=font_family, size=10, italic=True)

        ws_banner.cell(row=5, column=1, value="Violation #").font = font_bold
        ws_banner.cell(row=5, column=2, value="Error Details").font = font_bold

        for v_idx, v_msg in enumerate(violations, 1):
            ws_banner.cell(row=5 + v_idx, column=1, value=v_idx).font = font_alert
            ws_banner.cell(row=5 + v_idx, column=2, value=v_msg).font = font_regular

        ws_banner.column_dimensions["A"].width = 14
        ws_banner.column_dimensions["B"].width = 100

    # Auto-fit column widths
    ws.column_dimensions["A"].width = 24 # Student Name
    ws.column_dimensions["B"].width = 14 # ID
    ws.column_dimensions["C"].width = 14 # Rating
    ws.column_dimensions["D"].width = 20 # Level
    ws.column_dimensions["E"].width = 22 # Batch
    ws.column_dimensions["F"].width = 16 # Planned
    ws.column_dimensions["G"].width = 16 # Actual

    for d_obj in target_dates:
        d_str = d_obj.strftime("%Y-%m-%d")
        c_idx = date_col_map[d_str]
        col_letter_time = get_column_letter(c_idx)
        col_letter_coach = get_column_letter(c_idx + 1)
        ws.column_dimensions[col_letter_time].width = 20
        ws.column_dimensions[col_letter_coach].width = 14

    ws.column_dimensions[get_column_letter(comments_col)].width = 45

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue(), is_valid, violations
