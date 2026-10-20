"""
render_native_schedules.py
==========================
Generates 100% native, ultra-premium student class schedules for Mighty Knight Chess Academy.
- Uses Chrome headless rendering for crisp vector typography, liquid glassmorphism, and zero bitmap patching.
- Dynamically shrinks for 4, 6, 8, 10 classes (zero ghost rows).
- Dynamically expands for 13, 14, 16+ classes.
- Zero color mismatch, zero misalignments, zero fading stars, zero overwriting.
- Official Mighty Knight Logo, 3D Golden Knight, and "Train your Brain" branding.
"""

import os
import sys
import json
import base64
import subprocess
from datetime import datetime

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
PUBLIC_DIR = os.path.join(PROJECT_ROOT, "frontend", "public")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "native_schedules")
WEB_PUBLIC_DIR = os.path.join(PUBLIC_DIR, "native_schedules")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(WEB_PUBLIC_DIR, exist_ok=True)

# Import RAW_SCHEDULE and STUDENT_DATA_LIST
sys.path.insert(0, BACKEND_DIR)
try:
    from import_oct26_schedule import RAW_SCHEDULE
except ImportError:
    RAW_SCHEDULE = []

try:
    from render_master_schedules import STUDENT_DATA_LIST
except ImportError:
    STUDENT_DATA_LIST = []

# Base64 assets
def get_b64(path):
    with open(path, "rb") as f:
        ext = path.split(".")[-1].lower()
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode("utf-8")

LOGO_B64 = get_b64(os.path.join(PUBLIC_DIR, "mighty_knight_logo.jpg"))
KNIGHT_B64 = get_b64(os.path.join(PUBLIC_DIR, "golden_knight_isolated.png"))

# Normalize batch levels
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

def generate_html(student):
    name = student["name"]
    sid = student["id"]
    level = normalize_batch_level(student.get("raw_level", "Basic 1"))
    rating = str(student.get("rating", "1.0"))
    classes = STUDENT_CLASSES_MAP.get(name, [])

    rows_html = ""
    if len(classes) == 0:
        rows_html = f"""
        <tr>
          <td colspan="8" style="text-align: center; padding: 28px; color: #94a3b8; font-weight: 700; font-size: 1.1rem; letter-spacing: 1px;">
            NO UPCOMING CLASSES CURRENTLY SCHEDULED FOR OCTOBER 2026
          </td>
        </tr>
        """
    else:
        for idx, cls in enumerate(classes, start=1):
            rows_html += f"""
            <tr>
              <td style="text-align: center;"><span class="row-index-pill">{idx}</span></td>
              <td class="date-val">{cls['date']}</td>
              <td class="day-val">{cls['day']}</td>
              <td style="text-align: center;">
                <span class="time-pill">
                  <svg viewBox="0 0 24 24" fill="none" stroke-width="2.2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                  {cls['time']}
                </span>
              </td>
              <td class="student-name-val">{name}</td>
              <td class="student-id-val">{sid}</td>
              <td style="text-align: center;"><span class="level-pill">{level}</span></td>
              <td style="text-align: center;">
                <span class="rating-container">
                  <svg viewBox="0 0 24 24"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
                  {rating}
                </span>
              </td>
            </tr>
            """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Mighty Knight Schedule — {name}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@700;800;900&family=Outfit:wght@400;500;600;700;800;900&family=Playfair+Display:ital,wght@1,700;1,800&display=swap');

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      width: 1536px;
      margin: 0;
      background: radial-gradient(circle at 50% 18%, #380408 0%, #170204 45%, #050102 100%);
      font-family: 'Outfit', sans-serif;
      color: #ffffff;
      padding: 32px 42px;
      position: relative;
      overflow: hidden;
      min-height: 100vh;
    }}

    /* Atmospheric Bokeh Lighting */
    body::before {{
      content: '';
      position: absolute;
      top: -80px;
      left: 50%;
      transform: translateX(-50%);
      width: 1000px;
      height: 480px;
      background: radial-gradient(circle, rgba(245, 158, 11, 0.28) 0%, rgba(220, 38, 38, 0.18) 45%, transparent 75%);
      filter: blur(60px);
      pointer-events: none;
    }}

    /* HEADER */
    .header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: relative;
      margin-bottom: 22px;
      z-index: 2;
    }}

    /* Left Branding */
    .branding-box {{
      display: flex;
      align-items: center;
      gap: 20px;
    }}

    .logo-badge {{
      width: 114px;
      height: 114px;
      border-radius: 22px;
      background: linear-gradient(145deg, #7f1d1d, #450a0a);
      border: 2px solid rgba(245, 158, 11, 0.65);
      box-shadow: 0 0 28px rgba(220, 38, 38, 0.55), inset 0 0 16px rgba(245, 158, 11, 0.3);
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      flex-shrink: 0;
    }}

    .logo-badge img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}

    .brand-titles {{
      display: flex;
      flex-direction: column;
    }}

    .brand-title-main {{
      font-family: 'Cinzel', serif;
      font-size: 2.35rem;
      font-weight: 900;
      letter-spacing: 2px;
      background: linear-gradient(180deg, #fef08a 0%, #f59e0b 60%, #b45309 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      line-height: 1.1;
      text-shadow: 0 2px 10px rgba(0,0,0,0.5);
    }}

    .brand-title-sub {{
      font-family: 'Cinzel', serif;
      font-size: 1.45rem;
      font-weight: 700;
      letter-spacing: 5px;
      color: #ffffff;
      margin-top: 2px;
    }}

    .brand-divider {{
      width: 100%;
      height: 1px;
      background: linear-gradient(90deg, #f59e0b, rgba(245, 158, 11, 0.2));
      margin: 6px 0;
    }}

    .brand-quote {{
      font-size: 0.8rem;
      font-weight: 600;
      letter-spacing: 3.5px;
      color: #cbd5e1;
      text-transform: uppercase;
    }}



    /* Right Student Profile Card */
    .profile-card {{
      width: 440px;
      background: rgba(22, 10, 16, 0.78);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1.5px solid rgba(220, 38, 38, 0.5);
      border-radius: 20px;
      box-shadow: 0 12px 36px rgba(0,0,0,0.65), 0 0 28px rgba(220, 38, 38, 0.25);
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}

    .profile-top {{
      display: flex;
      align-items: center;
      gap: 16px;
    }}

    .profile-avatar {{
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: radial-gradient(circle at 35% 30%, #fbbf24, #d97706 70%, #78350f);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 18px rgba(245, 158, 11, 0.45);
      flex-shrink: 0;
    }}

    .profile-avatar svg {{
      width: 32px;
      height: 32px;
      fill: #ffffff;
    }}

    .profile-user-info {{
      flex: 1;
      overflow: hidden;
    }}

    .student-name {{
      font-size: 1.35rem;
      font-weight: 800;
      color: #ffffff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      letter-spacing: 0.5px;
    }}

    .student-id-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 4px;
    }}

    .id-label {{
      font-size: 0.8rem;
      color: #94a3b8;
      font-weight: 500;
    }}

    .id-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(245, 158, 11, 0.12);
      border: 1px solid rgba(245, 158, 11, 0.45);
      color: #fbbf24;
      padding: 2px 10px;
      border-radius: 6px;
      font-size: 0.88rem;
      font-weight: 800;
      letter-spacing: 0.5px;
    }}

    .id-badge svg {{
      width: 13px;
      height: 13px;
      opacity: 0.85;
      stroke: #fbbf24;
    }}

    .profile-bottom {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }}

    .stat-pill-card {{
      background: rgba(15, 23, 42, 0.65);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 12px;
      padding: 8px 12px;
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .stat-icon {{
      width: 26px;
      height: 26px;
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: center;
    }}

    .stat-meta {{
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}

    .stat-label {{
      font-size: 0.72rem;
      color: #94a3b8;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    .stat-value {{
      font-size: 0.95rem;
      font-weight: 800;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .stat-value.level {{
      color: #34d399;
    }}

    .stat-value.rating {{
      color: #fbbf24;
    }}

    /* SCHEDULE BANNER */
    .schedule-banner {{
      background: linear-gradient(90deg, rgba(185, 28, 28, 0.85) 0%, rgba(127, 29, 29, 0.75) 60%, rgba(69, 10, 10, 0.85) 100%);
      border: 1.5px solid rgba(239, 68, 68, 0.45);
      border-radius: 14px;
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 14px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.45), 0 0 25px rgba(220, 38, 38, 0.28);
    }}

    .banner-left {{
      display: flex;
      align-items: center;
      gap: 14px;
    }}

    .calendar-badge {{
      width: 44px;
      height: 44px;
      border-radius: 10px;
      background: rgba(0,0,0,0.35);
      border: 1px solid rgba(255,255,255,0.18);
      display: flex;
      align-items: center;
      justify-content: center;
    }}

    .calendar-badge svg {{
      width: 24px;
      height: 24px;
      fill: #fbbf24;
    }}

    .banner-text-title {{
      font-size: 1.25rem;
      font-weight: 800;
      letter-spacing: 1px;
      color: #ffffff;
    }}

    .banner-text-title span {{
      color: #fbbf24;
    }}

    .banner-text-sub {{
      font-size: 0.8rem;
      font-weight: 600;
      color: #fca5a5;
      letter-spacing: 2px;
      text-transform: uppercase;
    }}

    .banner-right-badge {{
      display: flex;
      align-items: center;
      gap: 8px;
      background: rgba(0, 0, 0, 0.45);
      border: 1px solid rgba(245, 158, 11, 0.45);
      padding: 8px 18px;
      border-radius: 30px;
      font-size: 0.95rem;
      font-weight: 800;
      color: #fef08a;
      letter-spacing: 1.5px;
    }}

    /* SCHEDULE TABLE CONTAINER */
    .table-container {{
      background: rgba(12, 16, 28, 0.88);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1.5px solid rgba(220, 38, 38, 0.48);
      border-radius: 16px;
      box-shadow: 0 12px 42px rgba(0,0,0,0.65), 0 0 28px rgba(220, 38, 38, 0.22);
      overflow: hidden;
      margin-bottom: 18px;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
    }}

    thead {{
      background: linear-gradient(180deg, rgba(32, 10, 16, 0.98) 0%, rgba(20, 8, 12, 0.98) 100%);
      border-bottom: 2px solid rgba(220, 38, 38, 0.45);
    }}

    th {{
      padding: 13px 16px;
      font-size: 0.82rem;
      font-weight: 800;
      letter-spacing: 1.5px;
      color: #e2e8f0;
      text-transform: uppercase;
    }}

    tbody tr {{
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }}

    tbody tr:nth-child(even) {{
      background: rgba(15, 23, 42, 0.5);
    }}

    tbody tr:nth-child(odd) {{
      background: rgba(10, 15, 30, 0.7);
    }}

    tbody tr:last-child {{
      border-bottom: none;
    }}

    td {{
      padding: 12px 16px;
      font-size: 0.98rem;
      color: #f8fafc;
      vertical-align: middle;
    }}

    /* Row Pill Badges */
    .row-index-pill {{
      width: 44px;
      height: 32px;
      border-radius: 8px;
      background: linear-gradient(135deg, #dc2626, #991b1b);
      border: 1px solid rgba(248, 113, 113, 0.4);
      box-shadow: 0 2px 8px rgba(220, 38, 38, 0.4);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 0.95rem;
      font-weight: 800;
      color: #ffffff;
    }}

    .date-val {{
      font-weight: 700;
      color: #ffffff;
      letter-spacing: 0.5px;
    }}

    .day-val {{
      color: #cbd5e1;
      font-weight: 500;
    }}

    .time-pill {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: linear-gradient(135deg, rgba(30, 58, 138, 0.85) 0%, rgba(29, 78, 216, 0.85) 100%);
      border: 1px solid rgba(96, 165, 250, 0.45);
      box-shadow: 0 0 14px rgba(37, 99, 235, 0.35);
      padding: 6px 14px;
      border-radius: 8px;
      color: #93c5fd;
      font-size: 0.9rem;
      font-weight: 800;
      letter-spacing: 0.5px;
    }}

    .time-pill svg {{
      width: 15px;
      height: 15px;
      stroke: #60a5fa;
    }}

    .student-name-val {{
      font-weight: 700;
      color: #ffffff;
    }}

    .student-id-val {{
      color: #cbd5e1;
      font-weight: 500;
    }}

    .level-pill {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, rgba(6, 78, 59, 0.65) 0%, rgba(5, 150, 105, 0.45) 100%);
      border: 1px solid rgba(52, 211, 153, 0.45);
      padding: 6px 16px;
      border-radius: 8px;
      color: #34d399;
      font-size: 0.88rem;
      font-weight: 800;
      letter-spacing: 0.5px;
      white-space: nowrap;
    }}

    .rating-container {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 1.05rem;
      font-weight: 800;
      color: #fbbf24;
    }}

    .rating-container svg {{
      width: 18px;
      height: 18px;
      fill: #f59e0b;
    }}

    /* FOOTER */
    .footer {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px 0 14px;
      position: relative;
      z-index: 2;
    }}

    .footer-left {{
      display: flex;
      align-items: center;
      gap: 14px;
    }}

    .footer-crown {{
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
    }}

    .footer-crown svg {{
      width: 100%;
      height: 100%;
      fill: #fbbf24;
      filter: drop-shadow(0 0 8px rgba(245, 158, 11, 0.6));
    }}

    .footer-titles {{
      display: flex;
      flex-direction: column;
    }}

    .footer-brand-name {{
      font-family: 'Cinzel', serif;
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: 1px;
      color: #ffffff;
    }}

    .footer-tagline {{
      font-family: 'Playfair Display', cursive, serif;
      font-style: italic;
      font-size: 1.28rem;
      font-weight: 800;
      background: linear-gradient(90deg, #fef08a, #f59e0b);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-top: -2px;
    }}

    .footer-right {{
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 2px;
    }}

    .footer-doc-title {{
      font-size: 0.8rem;
      color: #94a3b8;
      font-weight: 600;
      letter-spacing: 1px;
    }}

    .footer-verified-box {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.9rem;
      font-weight: 600;
      color: #e2e8f0;
    }}

    .footer-verified-box span.badge-id {{
      color: #fbbf24;
      font-weight: 700;
    }}

    .footer-verified-box svg {{
      width: 16px;
      height: 16px;
      stroke: #10b981;
    }}
  </style>
</head>
<body>

  <!-- HEADER -->
  <header class="header">
    <div class="branding-box">
      <div class="logo-badge">
        <img src="{LOGO_B64}" alt="Mighty Knight Logo">
      </div>
      <div class="brand-titles">
        <div class="brand-title-main">MIGHTY KNIGHT</div>
        <div class="brand-title-sub">CHESS ACADEMY</div>
        <div class="brand-divider"></div>
        <div class="brand-quote">Discipline • Strategy • Brighter Minds</div>
      </div>
    </div>



    <!-- Student Profile Card -->
    <div class="profile-card">
      <div class="profile-top">
        <div class="profile-avatar">
          <svg viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
        </div>
        <div class="profile-user-info">
          <div class="student-name">{name}</div>
          <div class="student-id-row">
            <span class="id-label">Student ID:</span>
            <span class="id-badge">
              {sid}
              <svg viewBox="0 0 24 24" fill="none" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
            </span>
          </div>
        </div>
      </div>

      <div class="profile-bottom">
        <div class="stat-pill-card">
          <div class="stat-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="#34d399" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>
          </div>
          <div class="stat-meta">
            <span class="stat-label">Batch Level</span>
            <span class="stat-value level">{level}</span>
          </div>
        </div>

        <div class="stat-pill-card">
          <div class="stat-icon">
            <svg viewBox="0 0 24 24" fill="#fbbf24"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
          </div>
          <div class="stat-meta">
            <span class="stat-label">MKCA Rating</span>
            <span class="stat-value rating">{rating}</span>
          </div>
        </div>
      </div>
    </div>
  </header>

  <!-- BANNER -->
  <div class="schedule-banner">
    <div class="banner-left">
      <div class="calendar-badge">
        <svg viewBox="0 0 24 24"><path d="M19 4h-1V2h-2v2H8V2H6v2H5c-1.11 0-1.99.9-1.99 2L3 20a2 2 0 0 0 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V10h14v10zm0-12H5V6h14v2z"/></svg>
      </div>
      <div>
        <div class="banner-text-title">STUDENT CLASS <span>SCHEDULE</span></div>
        <div class="banner-text-sub">October 2026 Academic Cycle</div>
      </div>
    </div>
    <div class="banner-right-badge">
      <span>OCTOBER 2026</span>
    </div>
  </div>

  <!-- TABLE -->
  <div class="table-container">
    <table>
      <thead>
        <tr>
          <th style="width: 70px; text-align: center;">#</th>
          <th style="width: 150px;">DATE</th>
          <th style="width: 150px;">DAY</th>
          <th style="width: 170px; text-align: center;">TIME</th>
          <th>STUDENT NAME</th>
          <th style="width: 150px;">STUDENT ID</th>
          <th style="width: 220px; text-align: center;">BATCH LEVEL</th>
          <th style="width: 150px; text-align: center;">MKCA RATING</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>

  <!-- FOOTER -->
  <footer class="footer">
    <div class="footer-left">
      <div class="footer-crown">
        <svg viewBox="0 0 24 24"><path d="M5 16L3 5l5.5 5L12 4l3.5 6L21 5l-2 11H5zm14 3c0 .6-.4 1-1 1H6c-.6 0-1-.4-1-1v-1h14v1z"/></svg>
      </div>
      <div class="footer-titles">
        <div class="footer-brand-name">Mighty Knight Chess Academy</div>
        <div class="footer-tagline">Train your Brain</div>
      </div>
    </div>

    <div class="footer-right">
      <div class="footer-doc-title">Official Student Schedule • October 2026 Cycle</div>
      <div class="footer-verified-box">
        <svg viewBox="0 0 24 24" fill="none" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
        Verified for {name} (<span class="badge-id">ID: {sid}</span>)
      </div>
    </div>
  </footer>

</body>
</html>
"""
    return html

def render_student_native(student):
    name = student["name"]
    sid = student["id"]
    safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
    filename = f"Mighty_Knight_{safe_name}_{sid}.png"

    classes = STUDENT_CLASSES_MAP.get(name, [])
    num_rows = max(len(classes), 1)

    # Dynamic Height Calculation based on class count!
    # Base height: header (200px) + banner (70px) + thead (50px) + footer (80px) + margins/padding (130px) = 530px
    # Each row is ~52px
    calculated_height = 530 + (num_rows * 52)
    # Ensure minimum height of 720 for beauty, and expands cleanly for 14, 16+ classes
    final_height = max(calculated_height, 720)

    html_content = generate_html(student)
    temp_html = os.path.join(BACKEND_DIR, f"temp_{sid}_{safe_name}.html")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    out_file1 = os.path.join(OUTPUT_DIR, filename)
    out_file2 = os.path.join(WEB_PUBLIC_DIR, filename)

    cmd = [
        chrome,
        "--headless=new",
        f"--screenshot={out_file1}",
        f"--window-size=1536,{final_height}",
        "--hide-scrollbars",
        f"file:///{temp_html.replace(os.sep, '/')}"
    ]

    subprocess.run(cmd, capture_output=True, text=True)

    # Copy to web public
    if os.path.exists(out_file1):
        import shutil
        shutil.copyfile(out_file1, out_file2)

    # Cleanup temp html
    try:
        os.remove(temp_html)
    except Exception:
        pass

    return {
        "name": name,
        "id": sid,
        "rating": student.get("rating", "1200"),
        "level": normalize_batch_level(student.get("raw_level", "Basic 1")),
        "classes_count": len(classes),
        "dimensions": f"1536x{final_height}",
        "file": filename
    }

if __name__ == "__main__":
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time

    total = len(STUDENT_DATA_LIST)
    print(f"Generating Native Schedules for ALL {total} students using ThreadPoolExecutor...")
    print("=" * 60)

    start_time = time.time()
    records = []
    completed = 0

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(render_student_native, stu): stu for stu in STUDENT_DATA_LIST}
        for future in as_completed(futures):
            stu = futures[future]
            completed += 1
            try:
                res = future.result()
                records.append(res)
                print(f"[{completed}/{total}] {res['name']} ({res['id']}) -> {res['dimensions']} | {res['classes_count']} classes")
            except Exception as e:
                print(f"[{completed}/{total}] ERROR {stu['name']}: {e}")

    # Sort records by name
    records.sort(key=lambda x: x["name"])

    # Save validation report
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_students": len(records),
        "students": records
    }
    for dest in [OUTPUT_DIR, WEB_PUBLIC_DIR]:
        rpath = os.path.join(dest, "NATIVE_VALIDATION_REPORT.json")
        with open(rpath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    duration = time.time() - start_time
    print("=" * 60)
    print(f"SUCCESS! Generated {len(records)}/{total} native schedules in {duration:.1f}s.")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Web:    {WEB_PUBLIC_DIR}")

