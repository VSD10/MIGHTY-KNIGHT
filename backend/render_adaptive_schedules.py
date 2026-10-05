"""
render_adaptive_schedules.py
============================
Adaptive Schedule Generator for Mighty Knight Chess Academy.
- Dynamically shrinks for students with 4, 6, 8, 10 classes (zero empty ghost rows).
- Dynamically expands for students with 13, 14, 16, 24 classes.
- Uses exact official brand assets: Logo, 3D Golden Knight, "Train your Brain", Profile Card, and Pills.
- Accurately maps real student data: Name, ID, Batch Level, Rating, Date, Day, Time.
"""

import os
import sys
import json
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
PUBLIC_DIR = os.path.join(PROJECT_ROOT, "frontend", "public")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "adaptive_schedules")
WEB_PUBLIC_DIR = os.path.join(PUBLIC_DIR, "adaptive_schedules")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(WEB_PUBLIC_DIR, exist_ok=True)

# Import RAW_SCHEDULE
sys.path.insert(0, BACKEND_DIR)
try:
    from import_oct26_schedule import RAW_SCHEDULE
except ImportError:
    RAW_SCHEDULE = []

# Windows TrueType Fonts
FONT_BOLD = "C:/Windows/Fonts/segoeuib.ttf"
FONT_REG = "C:/Windows/Fonts/segoeui.ttf"

def get_font(size, bold=True):
    try:
        path = FONT_BOLD if bold else FONT_REG
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

# Normalize Batch Levels
def normalize_batch_level(raw):
    if not raw:
        return "Basic 1"
    s = str(raw).strip().lower()
    if "basic 1" in s or "basic1" in s: return "Basic 1"
    if "basic 2" in s or "basic2" in s: return "Basic 2"
    if "early intermediate 1" in s or "early intrmediate1" in s or "early intermediate1" in s: return "Early Intermediate 1"
    if "early intermediate 2" in s or "early intrmediate2" in s or "early intermediate2" in s: return "Early Intermediate 2"
    if "beginner 1" in s or "beginner1" in s: return "Beginner 1"
    if "beginner 2" in s or "beginner2" in s: return "Beginner 2"
    if "intermediate 2" in s or "intermediate2" in s: return "Intermediate 2"
    if "intermediate 1" in s or "intermediate1" in s or s == "i intermediate": return "Intermediate 1"
    return "Basic 1"

# Load Master Slices
HEADER_SLICE = Image.open(os.path.join(PUBLIC_DIR, "slice_header.png")).convert("RGB")
FOOTER_SLICE = Image.open(os.path.join(PUBLIC_DIR, "slice_footer.png")).convert("RGB")
TABLE_BOTTOM = Image.open(os.path.join(PUBLIC_DIR, "slice_table_bottom.png")).convert("RGB")
ROW_SLICE = Image.open(os.path.join(PUBLIC_DIR, "slice_row.png")).convert("RGB")

# Map Student Name -> Classes from RAW_SCHEDULE
STUDENT_CLASSES_MAP = {}
for date_str, time_slot, coach, students in RAW_SCHEDULE:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day_str = dt.strftime("%A")
        formatted_date = dt.strftime("%d/%m/%Y")
    except Exception:
        day_str = "Friday"
        formatted_date = date_str

    for s in students:
        s_clean = s.strip()
        if s_clean not in STUDENT_CLASSES_MAP:
            STUDENT_CLASSES_MAP[s_clean] = []
        STUDENT_CLASSES_MAP[s_clean].append({
            "raw_date": date_str,
            "date": formatted_date,
            "day": day_str,
            "time": time_slot,
            "coach": coach
        })

for s in STUDENT_CLASSES_MAP:
    STUDENT_CLASSES_MAP[s].sort(key=lambda c: (c["raw_date"], c["time"]))

def draw_fit_text(draw, text, box, font_size_start, fill, bold=True, align="center"):
    box_w = box[2] - box[0]
    box_h = box[3] - box[1]

    current_size = font_size_start
    font = get_font(current_size, bold=bold)
    
    while current_size > 9:
        bbox = font.getbbox(text)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        if w <= box_w - 4 and h <= box_h - 2:
            break
        current_size -= 1
        font = get_font(current_size, bold=bold)

    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    y = box[1] + (box_h - th) // 2 - bbox[1]

    if align == "center":
        x = box[0] + (box_w - tw) // 2
    elif align == "left":
        x = box[0] + 4
    elif align == "right":
        x = box[2] - tw - 4
    else:
        x = box[0]

    draw.text((x, y), text, font=font, fill=fill)

def render_adaptive_schedule(student):
    """
    Renders an adaptive student schedule:
    - Shrinks naturally for 4, 6, 8, 10 classes with ZERO empty rows.
    - Expands naturally for 14, 16+ classes.
    - Width is fixed at 1536. Height adapts smoothly.
    """
    student_name = student["name"]
    student_id = student["id"]
    batch_level = normalize_batch_level(student.get("raw_level", "Basic 1"))
    rating = str(student.get("rating", "1.0"))
    classes = STUDENT_CLASSES_MAP.get(student_name, [])

    num_rows = len(classes)
    if num_rows == 0:
        num_rows = 1

    header_h = 416
    row_h = 40
    bottom_h = 30
    gap = 10
    footer_h = 94

    total_h = header_h + (num_rows * row_h) + bottom_h + gap + footer_h
    canvas = Image.new("RGB", (1536, total_h), (9, 6, 12))
    draw = ImageDraw.Draw(canvas)

    # 1. Paste Header Slice with Seamless Feathered Dynamic Masks
    header_copy = HEADER_SLICE.copy()

    # Feathered patch for Student Name
    p_name = Image.new('RGB', (310, 42), (22, 5, 14))
    m_name = Image.new('L', (310, 42), 0)
    d_name = ImageDraw.Draw(m_name)
    d_name.rectangle((6, 4, 304, 38), fill=255)
    m_name = m_name.filter(ImageFilter.GaussianBlur(3))
    header_copy.paste(p_name, (1120, 68), m_name)

    # Feathered patch for ID pill text (leaves copy icon at 1370)
    p_id = Image.new('RGB', (135, 34), (24, 16, 18))
    m_id = Image.new('L', (135, 34), 0)
    d_id = ImageDraw.Draw(m_id)
    d_id.rectangle((4, 3, 131, 31), fill=255)
    m_id = m_id.filter(ImageFilter.GaussianBlur(2))
    header_copy.paste(p_id, (1230, 114), m_id)

    # Feathered patch for Level text (leaves 'Batch Level' label above)
    p_lvl = Image.new('RGB', (145, 36), (10, 22, 38))
    m_lvl = Image.new('L', (145, 36), 0)
    d_lvl = ImageDraw.Draw(m_lvl)
    d_lvl.rectangle((4, 3, 141, 33), fill=255)
    m_lvl = m_lvl.filter(ImageFilter.GaussianBlur(2))
    header_copy.paste(p_lvl, (1112, 194), m_lvl)

    # Feathered patch for Rating text (leaves 'MKCIA Rating' label above)
    p_rat = Image.new('RGB', (125, 36), (12, 22, 38))
    m_rat = Image.new('L', (125, 36), 0)
    d_rat = ImageDraw.Draw(m_rat)
    d_rat.rectangle((4, 3, 121, 33), fill=255)
    m_rat = m_rat.filter(ImageFilter.GaussianBlur(2))
    header_copy.paste(p_rat, (1340, 194), m_rat)

    # Draw Student Profile Card info
    h_draw = ImageDraw.Draw(header_copy)
    draw_fit_text(h_draw, student_name, (1125, 72, 1420, 108), 24, (255, 255, 255), bold=True, align="left")
    draw_fit_text(h_draw, student_id, (1232, 115, 1360, 146), 18, (251, 191, 36), bold=True, align="center")
    draw_fit_text(h_draw, batch_level, (1112, 196, 1255, 228), 16, (52, 211, 153), bold=True, align="left")
    draw_fit_text(h_draw, rating, (1342, 196, 1465, 228), 19, (251, 191, 36), bold=True, align="left")

    canvas.paste(header_copy, (0, 0))

    # 2. Render Adaptive Rows with Real Authentic Pills
    row_y_start = 416
    for i in range(num_rows):
        cur_y = row_y_start + i * row_h
        is_even = (i % 2 == 0)
        bg_color = (7, 13, 26) if is_even else (12, 19, 35)

        row_copy = ROW_SLICE.copy()
        r_draw = ImageDraw.Draw(row_copy)

        # Clear text areas, keeping icons and pill borders authentic
        r_draw.rectangle((12, 5, 71, 35), fill=(180, 20, 20))       # inside red pill
        r_draw.rectangle((85, 3, 260, 37), fill=bg_color)           # date
        r_draw.rectangle((265, 3, 435, 37), fill=bg_color)          # day
        r_draw.rectangle((480, 5, 582, 35), fill=(14, 52, 125))    # inside blue pill (keeps clock)
        r_draw.rectangle((640, 3, 920, 37), fill=bg_color)          # name
        r_draw.rectangle((925, 3, 1050, 37), fill=bg_color)         # id
        r_draw.rectangle((1065, 5, 1200, 35), fill=(7, 50, 45))    # inside emerald pill
        r_draw.rectangle((1338, 3, 1440, 37), fill=bg_color)        # rating text (keeps gold star)

        if len(classes) == 0:
            draw_fit_text(r_draw, "NO UPCOMING SCHEDULED CLASSES", (100, 4, 1400, 36), 18, (148, 163, 184), bold=True, align="center")
            canvas.paste(row_copy, (43, cur_y))
            continue

        cls = classes[i]

        # Serial Number inside red pill
        draw_fit_text(r_draw, str(i + 1), (12, 5, 71, 35), 18, (255, 255, 255), bold=True, align="center")

        # DATE
        draw_fit_text(r_draw, cls["date"], (85, 4, 260, 36), 17, (248, 250, 252), bold=True, align="left")

        # DAY
        draw_fit_text(r_draw, cls["day"], (265, 4, 435, 36), 17, (226, 232, 240), bold=False, align="left")

        # TIME inside blue pill (clock icon preserved at left)
        draw_fit_text(r_draw, cls["time"], (480, 5, 582, 35), 16, (96, 165, 250), bold=True, align="center")

        # STUDENT NAME
        draw_fit_text(r_draw, student_name, (640, 4, 920, 36), 16, (248, 250, 252), bold=True, align="left")

        # STUDENT ID
        draw_fit_text(r_draw, student_id, (925, 4, 1050, 36), 16, (226, 232, 240), bold=False, align="left")

        # BATCH LEVEL inside emerald pill
        draw_fit_text(r_draw, batch_level, (1065, 5, 1200, 35), 15, (52, 211, 153), bold=True, align="center")

        # MKCIA RATING (star preserved at left)
        draw_fit_text(r_draw, rating, (1348, 4, 1440, 36), 17, (251, 191, 36), bold=True, align="left")

        canvas.paste(row_copy, (43, cur_y))

    # 3. Paste Table Bottom Rounded Border
    bottom_y = row_y_start + (num_rows * row_h)
    canvas.paste(TABLE_BOTTOM, (43, bottom_y))

    # 4. Paste Footer Slice with Feathered Verification Text
    footer_y = bottom_y + bottom_h + gap
    footer_copy = FOOTER_SLICE.copy()

    # Feathered patch for footer verification text
    p_foot = Image.new('RGB', (390, 32), (12, 10, 16))
    m_foot = Image.new('L', (390, 32), 0)
    d_foot = ImageDraw.Draw(m_foot)
    d_foot.rectangle((4, 3, 386, 29), fill=255)
    m_foot = m_foot.filter(ImageFilter.GaussianBlur(2))
    footer_copy.paste(p_foot, (1070, 38), m_foot)

    # Draw accurate verification text
    f_draw = ImageDraw.Draw(footer_copy)
    draw_fit_text(f_draw, f"Verified for {student_name} (ID: {student_id})", (1070, 38, 1455, 68), 14, (203, 213, 225), bold=False, align="right")

    canvas.paste(footer_copy, (0, footer_y))

    return canvas

if __name__ == "__main__":
    from render_master_schedules import STUDENT_DATA_LIST

    print(f"Generating Adaptive Schedules for all {len(STUDENT_DATA_LIST)} students...")
    adaptive_records = []

    for stu in STUDENT_DATA_LIST:
        img = render_adaptive_schedule(stu)
        safe_name = "".join(c for c in stu['name'] if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
        filename = f"Adaptive_Schedule_{safe_name}_{stu['id']}.png"
        
        p1 = os.path.join(OUTPUT_DIR, filename)
        p2 = os.path.join(WEB_PUBLIC_DIR, filename)
        img.save(p1, quality=95)
        img.save(p2, quality=95)

        classes_count = len(STUDENT_CLASSES_MAP.get(stu["name"], []))
        adaptive_records.append({
            "name": stu["name"],
            "id": stu["id"],
            "rating": stu["rating"],
            "level": normalize_batch_level(stu.get("raw_level", "Basic 1")),
            "classes_count": classes_count,
            "dimensions": f"{img.size[0]}x{img.size[1]}",
            "file": filename
        })

    # Save summary report
    report_path = os.path.join(OUTPUT_DIR, "ADAPTIVE_VALIDATION_REPORT.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "total_students": len(STUDENT_DATA_LIST),
            "students": adaptive_records
        }, f, indent=2)

    web_report_path = os.path.join(WEB_PUBLIC_DIR, "ADAPTIVE_VALIDATION_REPORT.json")
    with open(web_report_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "total_students": len(STUDENT_DATA_LIST),
            "students": adaptive_records
        }, f, indent=2)

    print(f"Adaptive generation complete for all {len(STUDENT_DATA_LIST)} students!")
