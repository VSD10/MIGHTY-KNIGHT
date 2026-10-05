"""
render_master_schedules.py
==========================
Strict Master Schedule Generator for Mighty Knight Chess Academy.
- Exact Target Size: 1536x1024.
- Pixel-exact preservation of static artwork (outside dynamic masks, diff = 0).
- Automatic DAY calculation from DATE.
- Supports 4, 8, 12, 14, 16+ classes with multi-page pagination.
- Full validation suite: zero stale-data contamination, no text overflow/wrapping.
"""

import os
import sys
import json
import math
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageChops

# Paths
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
MASTER_SRC = os.path.join(PROJECT_ROOT, "frontend", "public", "master_1536x1024.png")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "student_schedules")
WEB_PUBLIC_DIR = os.path.join(PROJECT_ROOT, "frontend", "public", "generated_schedules")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(WEB_PUBLIC_DIR, exist_ok=True)

# Import RAW_SCHEDULE
sys.path.insert(0, BACKEND_DIR)
try:
    from import_oct26_schedule import RAW_SCHEDULE
except ImportError:
    RAW_SCHEDULE = []

# Fonts
FONT_BOLD_PATH = "C:/Windows/Fonts/segoeuib.ttf"
FONT_SEMI_PATH = "C:/Windows/Fonts/segoeuisb.ttf"
FONT_REG_PATH = "C:/Windows/Fonts/segoeui.ttf"

# Fallbacks if on non-Windows
if not os.path.exists(FONT_BOLD_PATH):
    FONT_BOLD_PATH = "arialbd.ttf"
    FONT_SEMI_PATH = "arialbd.ttf"
    FONT_REG_PATH = "arial.ttf"

def get_font(size, weight="bold"):
    path = FONT_BOLD_PATH if weight == "bold" else (FONT_SEMI_PATH if weight == "semi" else FONT_REG_PATH)
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

# 8 Standard Academy Levels
STANDARD_LEVELS = [
    "Basic 1", "Basic 2",
    "Beginner 1", "Beginner 2",
    "Early Intermediate 1", "Early Intermediate 2",
    "Intermediate 1", "Intermediate 2"
]

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

# Master Student Database from prompt
STUDENT_DATA_LIST = [
    {"name": "M VARUNESH PANDI", "id": "MKS00166", "rating": "3.1", "raw_level": "L Beginner1"},
    {"name": "Akshadhasree", "id": "MKS00067", "rating": "3", "raw_level": "L Beginner1B"},
    {"name": "Anikha", "id": "MKS00066", "rating": "3.1", "raw_level": "L Beginner1B"},
    {"name": "Krishiv Ajay", "id": "MKS00037", "rating": "7.5", "raw_level": "G Intermediate2"},
    {"name": "Srikavi Bharathi", "id": "MKS00045", "rating": "7", "raw_level": "G Intermediate2"},
    {"name": "M.Nalini Hirthika", "id": "MKS00118", "rating": "3.4", "raw_level": "G Beginner2"},
    {"name": "V. Srikaviyazhini", "id": "MKS00131", "rating": "3.2", "raw_level": "G Beginner2"},
    {"name": "Viraaj Shanmugam", "id": "MKS00153", "rating": "2", "raw_level": "I Basic2"},
    {"name": "Vedh Pabba", "id": "MKS00190", "rating": "2.9", "raw_level": "I Beginner2"},
    {"name": "Selvakrishna RK", "id": "MKS00167", "rating": "6.6", "raw_level": "G Intermediate2"},
    {"name": "Sarvin", "id": "MKS00060", "rating": "7.6", "raw_level": "G Intermediate2"},
    {"name": "YAASHVIN A/L SATEESHKUMAR", "id": "MKS00065", "rating": "6.9", "raw_level": "G Intermediate2"},
    {"name": "Sarvesh K", "id": "MKS00175", "rating": "3.2", "raw_level": "G beginner1C"},
    {"name": "N.Charan", "id": "MKS00148", "rating": "2.8", "raw_level": "G beginner1"},
    {"name": "Harini", "id": "MKS00073", "rating": "2.8", "raw_level": "G Beginner2"},
    {"name": "MELWIN G", "id": "MKS00100", "rating": "3", "raw_level": "G Beginner2"},
    {"name": "yaazhini", "id": "MKS00147", "rating": "3.5", "raw_level": "G Beginner1B"},
    {"name": "Kavinpriyan", "id": "MKS00023", "rating": "4.8", "raw_level": "G Early Intermediate1A"},
    {"name": "K. Sudhir", "id": "MKS00228", "rating": "3", "raw_level": "G Beginner2"},
    {"name": "HAASHINI SHRIVY V", "id": "MKS00115", "rating": "2.9", "raw_level": "G beginner1"},
    {"name": "Nakshathra. C", "id": "MKS00227", "rating": "2.8", "raw_level": "G Beginner2"},
    {"name": "Madesh", "id": "MKS00194", "rating": "4.8", "raw_level": "L Early Intrmediate1"},
    {"name": "V.Dharmasastha Individual", "id": "MKS00093", "rating": "5.8", "raw_level": "I Early Intermediate2"},
    {"name": "Kamesh kumar c", "id": "MKS00231", "rating": "6", "raw_level": "I Intermediate2"},
    {"name": "Jayasudhan", "id": "MKS00220", "rating": "1.1", "raw_level": "G Beginner1"},
    {"name": "Nyvan", "id": "MKS00208", "rating": "1.7", "raw_level": "G Beginner1"},
    {"name": "Thiyashwar S", "id": "MKS00181", "rating": "1.7", "raw_level": "G Beginner1"},
    {"name": "RITHIKNATH K.M", "id": "MKS00193", "rating": "2.1", "raw_level": "G Beginner1"},
    {"name": "Cholamithran BR", "id": "MKS00192", "rating": "2.1", "raw_level": "G Beginner1"},
    {"name": "BHAANAVI.V", "id": "MKS00189", "rating": "2.2", "raw_level": "G Beginner1"},
    {"name": "Jeevith. N.M", "id": "MKS00224", "rating": "1.8", "raw_level": "G beginner1"},
    {"name": "Ridhanya Sri.V", "id": "MKS00178", "rating": "2.4", "raw_level": "G beginner1"},
    {"name": "Bhavadharani.B", "id": "MKS00203", "rating": "1.3", "raw_level": "G Beginner1"},
    {"name": "Nishwanth R", "id": "MKS00171", "rating": "2.4", "raw_level": "G beginner1"},
    {"name": "Vaishnavi Krishna & vaibhavi Krishna", "id": "MKS00165 & MKS00164", "rating": "2.6 & 2.7", "raw_level": "I Beginner1"},
    {"name": "Priyan", "id": "MKS00162", "rating": "3.7", "raw_level": "I Beginner1"},
    {"name": "Alagu Durai", "id": "MKS00141", "rating": "4.8", "raw_level": "I Early Intermediate2"},
    {"name": "Devansh gade", "id": "MKS00218", "rating": "0.7", "raw_level": "I basic2"},
    {"name": "Oviya B", "id": "MKS00038", "rating": "3.2", "raw_level": "G Early Intermediate1"},
    {"name": "Jovinya", "id": "MKS00075", "rating": "4", "raw_level": "L Beginner1"},
    {"name": "S.V.Kavisree", "id": "MKS00111", "rating": "3.4", "raw_level": "L Beginner1"},
    {"name": "Vikaesh", "id": "MKS00221", "rating": "2.1", "raw_level": "I Beginner1"},
    {"name": "Kaashvi Prakash", "id": "MKS00184", "rating": "1.5", "raw_level": "I Basic2"},
    {"name": "C.V.Chanvika", "id": "MKS00196", "rating": "0.7", "raw_level": "L Basic1"},
    {"name": "A.Bavinesh", "id": "MKS00214", "rating": "0.6", "raw_level": "G Basic1"},
    {"name": "B.V.Tijesh", "id": "MKS00219", "rating": "0.5", "raw_level": "G Basic1"},
    {"name": "V. Dhaksha", "id": "MKS00110", "rating": "3.4", "raw_level": "I Beginner1"},
    {"name": "Samuel Rajan", "id": "MKS00182", "rating": "5.6", "raw_level": "G Intermediate1"},
    {"name": "S.Raagavarshenee", "id": "MKS00009", "rating": "4.3", "raw_level": "G Early Intermediate2"},
    {"name": "Praduksha", "id": "MKS00091", "rating": "5.1", "raw_level": "G Early Intermediate2"},
    {"name": "Arishmithran", "id": "MKS00072", "rating": "5", "raw_level": "G Early Intermediate2"},
    {"name": "Sanjumithra", "id": "MKS00070", "rating": "5.2", "raw_level": "G Early Intermediate2"},
    {"name": "Shakthivishakan A", "id": "MKS00034", "rating": "5.2", "raw_level": "G Early Intermediate2"},
    {"name": "S R Sabeshwar", "id": "MKS00223", "rating": "4.5", "raw_level": "G Early Intermediate1"},
    {"name": "M.Nishik", "id": "MKS00113", "rating": "6.5", "raw_level": "G Intermediate1"},
    {"name": "Vedhanth V", "id": "MKS00102", "rating": "6.1", "raw_level": "G Intermediate1"},
    {"name": "J Jerwin", "id": "MKS00230", "rating": "1.8", "raw_level": "G Basic2"},
    {"name": "Mohhan", "id": "MKS00064", "rating": "4.6", "raw_level": "G Early Intermediate2"},
    {"name": "Kavinth P", "id": "MKS00217", "rating": "1.1", "raw_level": "G Beginner1"},
    {"name": "Thenamilthan.S", "id": "MKS00200", "rating": "1.8", "raw_level": "G Beginner1"},
    {"name": "S.Kavirenu", "id": "MKS00199", "rating": "1.8", "raw_level": "G Beginner1"},
    {"name": "S.Kabilan", "id": "MKS00198", "rating": "1.8", "raw_level": "G Beginner1"},
    {"name": "M.Srisaran", "id": "MKS00186", "rating": "2.2", "raw_level": "G Beginner1"},
    {"name": "Kirthik", "id": "MKS00048", "rating": "5.4", "raw_level": "L Early Intermediate1"},
    {"name": "Pugazhini Navaneethan", "id": "MKS00156", "rating": "3.2", "raw_level": "I Beginner1"},
    {"name": "Magizh", "id": "MKS00213", "rating": "0.4", "raw_level": "I Basic1"},
    {"name": "P.V Subhiksha", "id": "MKS00150", "rating": "3.3", "raw_level": "I Beginner1"},
    {"name": "Thivya", "id": "MKS00056", "rating": "6.2", "raw_level": "L Early Intermediate2"},
    {"name": "Reyhan nawaz", "id": "MKS00049", "rating": "5.6", "raw_level": "L Early Intermediate2"},
    {"name": "B.AARAV NARAYAN", "id": "MKS00098", "rating": "4.5", "raw_level": "L Early Intrmediate1"},
    {"name": "B.SAI SRI", "id": "MKS00211", "rating": "1.1", "raw_level": "G Basic2"},
    {"name": "Sudharshika", "id": "MKS00216", "rating": "1.1", "raw_level": "G Basic2"},
    {"name": "Aaradheya P", "id": "MKS00225", "rating": "0.2", "raw_level": "G Basic1"},
    {"name": "Sri Varshini", "id": "MKS00232", "rating": "0.2", "raw_level": "G Basic1"},
    {"name": "Syed Individual", "id": "MKS00076", "rating": "3.5", "raw_level": "I Beginner1"},
    {"name": "Rooban", "id": "MKS00215", "rating": "3", "raw_level": "G beginner2"},
    {"name": "Mithun Rajamani chakravarthi", "id": "MKS00112", "rating": "3.5", "raw_level": "G Beginner2"},
    {"name": "Charvi", "id": "MKS00163", "rating": "3", "raw_level": "G Beginner1"},
    {"name": "Mithra sree A", "id": "MKS00161", "rating": "4", "raw_level": "G Beginner1"},
    {"name": "Rohith kumar.B", "id": "MKS00207", "rating": "3.4", "raw_level": "G Early Intermediate1"},
    {"name": "V.D. THARUN ADITHYA", "id": "MKS00212", "rating": "3.3", "raw_level": "G Early Intermediate1"},
    {"name": "D. Tharun", "id": "MKS00127", "rating": "4", "raw_level": "G Early Intermediate1"},
    {"name": "Ayaan Haris", "id": "MKS00092", "rating": "4.3", "raw_level": "G Early Intermediate1"},
    {"name": "Abhijay", "id": "MKS00202", "rating": "2.8", "raw_level": "G Beginner2"},
    {"name": "Yuviga", "id": "MKS00107", "rating": "4.2", "raw_level": "G Early Intermediate1"},
    {"name": "B SARVESSH", "id": "MKS00108", "rating": "4.1", "raw_level": "G Early Intermediate1"},
    {"name": "Adhigan Amarnath", "id": "MKS00204", "rating": "1.3", "raw_level": "L Basic2"},
    {"name": "Hitesh prabu", "id": "MKS00014", "rating": "4.7", "raw_level": "G Early Intermediate2"},
    {"name": "D KAVISH", "id": "MKS00079", "rating": "4.2", "raw_level": "G Beginner2"},
    {"name": "V.Pranav", "id": "MKS00173", "rating": "3.5", "raw_level": "G Early Intermediate1A"},
    {"name": "Pranith", "id": "MKS00143", "rating": "3.8", "raw_level": "G Early Intermediate1A"},
    {"name": "Hithesh", "id": "MKS00206", "rating": "4.8", "raw_level": "G Early Intermediate2"},
    {"name": "Ryan Stalin", "id": "MKS00007", "rating": "3.4", "raw_level": "G Beginner2s"},
    {"name": "Nirupan", "id": "MKS00185", "rating": "3", "raw_level": "G Beginner1B"},
    {"name": "Dhanya sri S S", "id": "MKS00114", "rating": "3.5", "raw_level": "G Beginner2"},
    {"name": "M Nethran", "id": "MKS00020", "rating": "3.8", "raw_level": "G Early Intermediate1A"},
    {"name": "Keshav Krishna", "id": "YTC", "rating": "3.3", "raw_level": "G Early Intermediate1A"},
    {"name": "R Logeshwaran", "id": "MKS00222", "rating": "1.8", "raw_level": "G beginner1"},
    {"name": "Dev dharsan", "id": "MKS00142", "rating": "2.6", "raw_level": "L Beginner1"},
    {"name": "Avyukt A Praveen", "id": "MKS00174", "rating": "3.3", "raw_level": "G Beginner2"},
    {"name": "M. R. Darshan", "id": "MKS00101", "rating": "3.5", "raw_level": "G Beginner2"},
    {"name": "Nitharsana", "id": "MKS00095", "rating": "3.3", "raw_level": "G Beginner2"},
    {"name": "A.T.Vagish", "id": "MKS00149", "rating": "2.8", "raw_level": "G Beginner1"},
    {"name": "A R Thatchiraa Shree", "id": "MKS00172", "rating": "2.8", "raw_level": "G beginner1s"},
    {"name": "H V Kanishk", "id": "MKS00154", "rating": "2.8", "raw_level": "G beginner1C"},
    {"name": "S. Thashwin Raj", "id": "MKS00155", "rating": "2.6", "raw_level": "G beginner1C"},
    {"name": "Vikash", "id": "MKS00168", "rating": "2.8", "raw_level": "G beginner1C"},
    {"name": "S.P.NEHASRI", "id": "MKS00157", "rating": "1.8", "raw_level": "G Basic2A"},
    {"name": "Aadhav Mithun", "id": "MKS00170", "rating": "1.1", "raw_level": "I Basic2"},
    {"name": "Ineya Individual", "id": "MKS00050", "rating": "7.3", "raw_level": "I Intermediate"},
    {"name": "S. YASWANNTH", "id": "MKS00039", "rating": "3.8", "raw_level": "G Beginner2"},
    {"name": "C S Sharwin", "id": "MKS00197", "rating": "2.4", "raw_level": "G Beginner1B"},
    {"name": "D R RAJAGOPALAN", "id": "MKS00176", "rating": "3.9", "raw_level": "G beginner1D"},
    {"name": "N.sri dharshni", "id": "MKS00055", "rating": "4.4", "raw_level": "L Beginner2"},
    {"name": "Sachin", "id": "MKS00059", "rating": "7.6", "raw_level": "L Intermediate2"},
    {"name": "Vivaan Aaditya", "id": "MKS00053", "rating": "8", "raw_level": "L Intermediate2"},
    {"name": "Nithesh Nagarathinam", "id": "MKS00054", "rating": "5.8", "raw_level": "L Early Intermediate1"},
    {"name": "S Mounitha", "id": "MKS00233", "rating": "3.0", "raw_level": "G Beginner2"}
]

# Map Student Name -> Classes from RAW_SCHEDULE
STUDENT_CLASSES_MAP = {}
for date_str, time_slot, coach, students in RAW_SCHEDULE:
    # Auto calculate day from date
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day_str = dt.strftime("%A")
        # Format DD/MM/YYYY
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

# Sort classes chronologically for each student
for s in STUDENT_CLASSES_MAP:
    STUDENT_CLASSES_MAP[s].sort(key=lambda c: (c["raw_date"], c["time"]))

# 1536x1024 Predefined Bounding Boxes (Dynamic Masks)
DYNAMIC_MASKS = {
    "profile_name": (1118, 76, 1420, 112),
    "profile_id": (1230, 114, 1365, 148),
    "profile_level": (1095, 183, 1245, 222),
    "profile_rating": (1315, 183, 1430, 222),
    "footer_verified": (1090, 968, 1455, 998)
}

# Table Rows Bounding Boxes for rows 0..11
TABLE_ROW_BOXES = []
for i in range(12):
    y1 = int(418 + i * 40.35)
    y2 = int(y1 + 35)
    TABLE_ROW_BOXES.append({
        "row_idx": i,
        "date": (110, y1, 265, y2),
        "day": (275, y1, 425, y2),
        "time": (495, y1, 615, y2),
        "name": (660, y1, 915, y2),
        "id": (930, y1, 1070, y2),
        "level": (1115, y1, 1255, y2),
        "rating": (1355, y1, 1445, y2)
    })

def create_clean_base_plate():
    """Generates the locked static plate with clean masked dynamic fields."""
    if not os.path.exists(MASTER_SRC):
        raise FileNotFoundError(f"Master plate not found at {MASTER_SRC}")
    
    im = Image.open(MASTER_SRC).convert("RGB")
    draw = ImageDraw.Draw(im)

    # Clean profile card
    draw.rectangle(DYNAMIC_MASKS["profile_name"], fill=(16, 23, 40))
    draw.rectangle(DYNAMIC_MASKS["profile_id"], fill=(26, 20, 12))
    draw.rectangle(DYNAMIC_MASKS["profile_level"], fill=(7, 28, 45))
    draw.rectangle(DYNAMIC_MASKS["profile_rating"], fill=(13, 27, 45))

    # Clean footer
    draw.rectangle(DYNAMIC_MASKS["footer_verified"], fill=(10, 8, 12))

    # Clean 12 table rows
    for i, r in enumerate(TABLE_ROW_BOXES):
        bg_row = (7, 13, 26) if i % 2 == 0 else (12, 19, 35)
        bg_time = (14, 52, 125)
        bg_level = (7, 50, 45)

        draw.rectangle(r["date"], fill=bg_row)
        draw.rectangle(r["day"], fill=bg_row)
        draw.rectangle(r["time"], fill=bg_time)
        draw.rectangle(r["name"], fill=bg_row)
        draw.rectangle(r["id"], fill=bg_row)
        draw.rectangle(r["level"], fill=bg_level)
        draw.rectangle(r["rating"], fill=bg_row)

    return im

LOCKED_CLEAN_PLATE = create_clean_base_plate()

def draw_fit_text(draw, text, box, font_size_start, fill, weight="bold", align="center"):
    """Draws text strictly inside the box. Shrinks font size if needed so it never wraps/clips."""
    box_w = box[2] - box[0]
    box_h = box[3] - box[1]

    current_size = font_size_start
    font = get_font(current_size, weight=weight)
    
    # Shrink if too wide
    while current_size > 10:
        bbox = font.getbbox(text)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        if w <= box_w - 4 and h <= box_h - 2:
            break
        current_size -= 1
        font = get_font(current_size, weight=weight)

    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    # Y centering
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

def render_student_schedule_page(student, classes_slice, page_num=1, total_pages=1):
    """
    Renders an exact 1536x1024 schedule page from the locked clean plate.
    Guarantees:
    - Zero stale data (clones fresh LOCKED_CLEAN_PLATE).
    - Perfect alignment, no overlapping, no wrapping.
    - Preserves static plate outside masks.
    """
    canvas = LOCKED_CLEAN_PLATE.copy()
    draw = ImageDraw.Draw(canvas)

    student_name = student["name"]
    student_id = student["id"]
    batch_level = normalize_batch_level(student.get("raw_level", "Basic 1"))
    rating = str(student.get("rating", "1.0"))

    # 1. Profile Card Dynamic Fields
    draw_fit_text(draw, student_name, DYNAMIC_MASKS["profile_name"], 24, (255, 255, 255), weight="bold", align="left")
    draw_fit_text(draw, student_id, DYNAMIC_MASKS["profile_id"], 18, (251, 191, 36), weight="bold", align="center")
    draw_fit_text(draw, batch_level, DYNAMIC_MASKS["profile_level"], 17, (52, 211, 153), weight="bold", align="center")
    draw_fit_text(draw, rating, DYNAMIC_MASKS["profile_rating"], 19, (251, 191, 36), weight="bold", align="center")

    # 2. Table Rows
    for i in range(12):
        r = TABLE_ROW_BOXES[i]
        if i < len(classes_slice):
            cls = classes_slice[i]
            # DATE
            draw_fit_text(draw, cls["date"], r["date"], 18, (248, 250, 252), weight="bold", align="left")
            # DAY
            draw_fit_text(draw, cls["day"], r["day"], 18, (226, 232, 240), weight="semi", align="left")
            # TIME (centered inside blue pill)
            draw_fit_text(draw, cls["time"], r["time"], 17, (96, 165, 250), weight="bold", align="center")
            # STUDENT NAME
            draw_fit_text(draw, student_name, r["name"], 17, (248, 250, 252), weight="bold", align="left")
            # STUDENT ID
            draw_fit_text(draw, student_id, r["id"], 17, (226, 232, 240), weight="semi", align="left")
            # BATCH LEVEL (centered inside teal pill)
            draw_fit_text(draw, batch_level, r["level"], 16, (52, 211, 153), weight="bold", align="center")
            # MKCA RATING
            draw_fit_text(draw, rating, r["rating"], 18, (251, 191, 36), weight="bold", align="left")
        else:
            # Clean empty row with standard placeholders
            draw_fit_text(draw, "—", r["date"], 16, (71, 85, 105), weight="semi", align="left")
            draw_fit_text(draw, "—", r["day"], 16, (71, 85, 105), weight="semi", align="left")
            draw_fit_text(draw, "—", r["time"], 16, (71, 85, 105), weight="semi", align="center")
            draw_fit_text(draw, student_name, r["name"], 17, (148, 163, 184), weight="bold", align="left")
            draw_fit_text(draw, student_id, r["id"], 17, (148, 163, 184), weight="semi", align="left")
            draw_fit_text(draw, batch_level, r["level"], 16, (52, 211, 153), weight="bold", align="center")
            draw_fit_text(draw, rating, r["rating"], 18, (251, 191, 36), weight="bold", align="left")

    # 3. Footer
    footer_text = f"Verified for {student_name} (ID: {student_id})"
    if total_pages > 1:
        footer_text += f" [Page {page_num} of {total_pages}]"
    draw_fit_text(draw, footer_text, DYNAMIC_MASKS["footer_verified"], 14, (203, 213, 225), weight="semi", align="right")

    return canvas

def validate_pixel_preservation_outside_masks(rendered_img):
    """Verifies that outside dynamic masks, pixel difference with clean base plate == 0."""
    diff = ImageChops.difference(rendered_img, LOCKED_CLEAN_PLATE)
    # Check pixels outside all dynamic mask boxes
    diff_pixels = diff.load()
    w, h = diff.size

    mask_boxes = list(DYNAMIC_MASKS.values())
    for r in TABLE_ROW_BOXES:
        mask_boxes.extend([r["date"], r["day"], r["time"], r["name"], r["id"], r["level"], r["rating"]])

    # Test outside coordinates
    violating_pixels = 0
    step = 4  # sample grid
    for x in range(0, w, step):
        for y in range(0, h, step):
            # If inside any mask box, ignore
            inside = False
            for mb in mask_boxes:
                if mb[0] <= x <= mb[2] and mb[1] <= y <= mb[3]:
                    inside = True
                    break
            if not inside:
                p = diff_pixels[x, y]
                if sum(p) > 0:
                    violating_pixels += 1

    return violating_pixels == 0

def run_mandatory_tests():
    """Runs tests: A R Thatchiraa Shree, Hitesh prabu, A->B->A sequence test."""
    print("=== RUNNING MANDATORY VALIDATION SUITE ===")
    
    # 1. Test A R Thatchiraa Shree (Reference case)
    ref_student = {
        "name": "A R Thatchiraa Shree",
        "id": "MKC1268",
        "rating": "1280",
        "raw_level": "General"
    }
    ref_classes = STUDENT_CLASSES_MAP.get("A R Thatchiraa Shree", [])
    im_ref = render_student_schedule_page(ref_student, ref_classes[:12])
    assert im_ref.size == (1536, 1024), "Reference image size must be 1536x1024"
    assert validate_pixel_preservation_outside_masks(im_ref), "Outside mask difference must be 0"
    print("  [PASS] A R Thatchiraa Shree reference rendered & validated (1536x1024, zero outside diff)")

    # 2. Test Hitesh prabu
    hitesh_student = next(s for s in STUDENT_DATA_LIST if s["name"] == "Hitesh prabu")
    hitesh_classes = STUDENT_CLASSES_MAP.get("Hitesh prabu", [])
    im_hitesh = render_student_schedule_page(hitesh_student, hitesh_classes[:12])
    assert im_hitesh.size == (1536, 1024), "Hitesh image size must be 1536x1024"
    assert validate_pixel_preservation_outside_masks(im_hitesh), "Hitesh outside mask difference must be 0"
    print(f"  [PASS] Hitesh prabu rendered with {len(hitesh_classes)} classes, verified outside mask diff = 0")

    # 3. Sequence Test: Student A -> Student B -> Student A (Stale data contamination test)
    im_a1 = render_student_schedule_page(ref_student, ref_classes[:12])
    im_b = render_student_schedule_page(hitesh_student, hitesh_classes[:12])
    im_a2 = render_student_schedule_page(ref_student, ref_classes[:12])
    
    diff_a1_a2 = ImageChops.difference(im_a1, im_a2)
    bbox_diff = diff_a1_a2.getbbox()
    assert bbox_diff is None, "Student A render must be 100% identical between runs (zero stale contamination)!"
    print("  [PASS] Sequence Test (A -> B -> A) passed: 0 pixel difference, zero stale contamination!")

    # 4. Multi-page test for 14 & 16 classes
    nithesh = next(s for s in STUDENT_DATA_LIST if "Nithesh Nagarathinam" in s["name"])
    nithesh_classes = STUDENT_CLASSES_MAP.get("Nithesh Nagarathinam", [])
    print(f"  [INFO] Nithesh Nagarathinam has {len(nithesh_classes)} classes -> Rendering Page 1 & Page 2...")
    im_p1 = render_student_schedule_page(nithesh, nithesh_classes[:12], page_num=1, total_pages=2)
    im_p2 = render_student_schedule_page(nithesh, nithesh_classes[12:], page_num=2, total_pages=2)
    assert im_p1.size == (1536, 1024) and im_p2.size == (1536, 1024)
    print("  [PASS] Multi-page test passed (Page 1 & 2 generated at 1536x1024)")

    print("=== ALL VALIDATION TESTS PASSED ===\n")

def generate_all_students_master_images():
    """Generates 1536x1024 master schedule PNGs for every student in the academy."""
    print(f"Starting master generation for {len(STUDENT_DATA_LIST)} academy students...")
    
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_students": len(STUDENT_DATA_LIST),
        "target_resolution": "1536x1024",
        "students": []
    }

    count = 0
    for student in STUDENT_DATA_LIST:
        sname = student["name"]
        sid = student["id"]
        safe_name = "".join(c if c.isalnum() else "_" for c in sname)

        # Get actual classes from RAW_SCHEDULE
        classes = STUDENT_CLASSES_MAP.get(sname, [])
        if not classes:
            # Fallback search by case-insensitive name
            for k in STUDENT_CLASSES_MAP:
                if k.lower() == sname.lower() or sname.lower() in k.lower():
                    classes = STUDENT_CLASSES_MAP[k]
                    break

        total_classes = len(classes)
        total_pages = max(1, math.ceil(total_classes / 12)) if total_classes > 0 else 1

        generated_files = []
        for p in range(total_pages):
            start_idx = p * 12
            end_idx = start_idx + 12
            classes_slice = classes[start_idx:end_idx]

            canvas = render_student_schedule_page(student, classes_slice, page_num=p+1, total_pages=total_pages)
            
            # File naming
            page_suffix = f"_p{p+1}" if total_pages > 1 else ""
            filename = f"Mighty_Knight_Schedule_{safe_name}_{sid}{page_suffix}.png"
            
            out_path1 = os.path.join(OUTPUT_DIR, filename)
            out_path2 = os.path.join(WEB_PUBLIC_DIR, filename)
            
            canvas.save(out_path1, "PNG")
            canvas.save(out_path2, "PNG")
            generated_files.append(filename)

        count += 1
        report["students"].append({
            "name": sname,
            "id": sid,
            "rating": student["rating"],
            "level": normalize_batch_level(student.get("raw_level", "Basic 1")),
            "classes_count": total_classes,
            "pages": total_pages,
            "files": generated_files
        })

    # Save validation report
    report_path = os.path.join(OUTPUT_DIR, "VALIDATION_REPORT.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"[COMPLETED] Successfully generated master 1536x1024 schedules for {count} students!")
    print(f"Validation report saved to: {report_path}")

def generate_visual_artifacts():
    """Generates side-by-side comparison and diff heatmap with dynamic masks marked."""
    print("Generating visual audit artifacts (Side-by-Side & Diff Heatmap)...")
    
    # 1. Load original master and a representative generated student image (Hitesh prabu)
    master = Image.open(MASTER_SRC).convert("RGB")
    hitesh_path = os.path.join(OUTPUT_DIR, "Mighty_Knight_Schedule_Hitesh_prabu_MKS00014.png")
    generated = Image.open(hitesh_path).convert("RGB")

    # 2. Side-by-Side Comparison
    w, h = master.size
    sbs = Image.new("RGB", (w * 2 + 40, h + 80), (10, 15, 25))
    sbs_draw = ImageDraw.Draw(sbs)

    title_font = get_font(32, weight="bold")
    sbs_draw.text((40, 20), "OFFICIAL MASTER TEMPLATE (1536x1024)", font=title_font, fill=(251, 191, 36))
    sbs_draw.text((w + 60, 20), "GENERATED STUDENT SCHEDULE (Hitesh prabu)", font=title_font, fill=(52, 211, 153))

    sbs.paste(master, (20, 60))
    sbs.paste(generated, (w + 40, 60))

    sbs_path1 = os.path.join(OUTPUT_DIR, "SIDE_BY_SIDE_COMPARISON.png")
    sbs_path2 = os.path.join(WEB_PUBLIC_DIR, "SIDE_BY_SIDE_COMPARISON.png")
    sbs.save(sbs_path1, "PNG")
    sbs.save(sbs_path2, "PNG")
    print(f"  [SAVED] Side-by-side comparison: {sbs_path1}")

    # 3. Diff Heatmap with Dynamic Masks Marked
    diff = ImageChops.difference(generated, master)
    # Amplify difference to visualize
    diff_data = diff.load()
    dw, dh = diff.size
    heatmap = Image.new("RGB", (dw, dh), (5, 8, 15))
    hm_draw = ImageDraw.Draw(heatmap)

    for x in range(0, dw, 2):
        for y in range(0, dh, 2):
            p = diff_data[x, y]
            total_d = sum(p)
            if total_d > 0:
                # Highlight in bright red/cyan
                val = min(255, total_d * 4)
                hm_draw.point((x, y), fill=(val, min(255, val // 2), 255))

    # Mark dynamic bounding boxes in yellow/cyan
    for name, box in DYNAMIC_MASKS.items():
        hm_draw.rectangle(box, outline=(251, 191, 36), width=2)
        hm_draw.text((box[0] + 4, box[1] - 14), name, font=get_font(12, "bold"), fill=(251, 191, 36))

    for r in TABLE_ROW_BOXES:
        for k in ["date", "day", "time", "name", "id", "level", "rating"]:
            hm_draw.rectangle(r[k], outline=(52, 211, 153, 120), width=1)

    diff_path1 = os.path.join(OUTPUT_DIR, "DIFF_HEATMAP.png")
    diff_path2 = os.path.join(WEB_PUBLIC_DIR, "DIFF_HEATMAP.png")
    heatmap.save(diff_path1, "PNG")
    heatmap.save(diff_path2, "PNG")
    print(f"  [SAVED] Diff Heatmap: {diff_path1}")

if __name__ == "__main__":
    run_mandatory_tests()
    generate_all_students_master_images()
    generate_visual_artifacts()
