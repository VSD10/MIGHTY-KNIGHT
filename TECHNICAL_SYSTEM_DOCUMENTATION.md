# ♞ Mighty Knight — Technical System Documentation

**Complete System Architecture, Database Schema, Engine Algorithms & Deployment Guide**

Version 1.0 · Single Source of Technical Truth

---

## 1. System Overview & Technology Stack

**Mighty Knight** is a rule-driven, constraint satisfaction scheduling system engineered for chess academies. It processes student data, coach capabilities, time preferences, daily caps, operating hours, and mandatory accountability rules to produce practical academy schedules.

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                                 REACT 18 WEB UI                                │
│          (Vite + Lucide Icons + Glassmorphism UI + Axios Client)              │
└───────────────────────────────────────┬────────────────────────────────────────┘
                                        │ REST API (HTTP / JSON)
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                             FASTAPI BACKEND SERVER                             │
│                  (Python 3.12 + Pydantic v2 Data Models)                       │
└───────┬───────────────────────────────┬───────────────────────────────┬────────┘
        │                               │                               │
        ▼                               ▼                               ▼
┌─────────────────┐             ┌─────────────────┐             ┌─────────────────┐
│ Excel Ingestion │             │ Scheduling Core │             │ SQLite Database │
│ (pandas/openpyxl)             │ (app.engine)    │             │ (chess_scheduler)
└─────────────────┘             └─────────────────┘             └─────────────────┘
```

### Technology Stack Table

| Layer | Component / Tool | Primary Function |
|---|---|---|
| **Frontend Framework** | React 18 + Vite | Modern single-page application dashboard |
| **Styling & Aesthetics** | Vanilla CSS3 (Custom Design System) | Dark mode, glassmorphism, responsive grid layouts |
| **Backend API** | FastAPI + Uvicorn | Asynchronous RESTful API server with auto-docs (`/docs`) |
| **Data Validation & Schemas** | Pydantic v2 | Strict type validation and JSON serialization |
| **Core Scheduling Engine** | Python 3.12 (Custom CSP Engine) | Priority-based constraint satisfaction algorithm |
| **Excel Processing** | pandas + openpyxl | Header normalization and row-level data ingestion |
| **Persistence Storage** | SQLite 3 (`chess_scheduler.db`) | 0-loss database storage for master data & schedules |

---

## 2. Core Scheduling Engine Architecture

The engine implements a **Deterministic Priority-Based Constraint Satisfaction Problem (CSP) Solver**. It processes candidate student batches across target scheduling dates and available time slots.

```
                             ┌────────────────────────┐
                             │ Target Dates & Slots   │
                             │ (Mon–Sat & Sunday)     │
                             └───────────┬────────────┘
                                         │
                                         ▼
                             ┌────────────────────────┐
                             │ Level Priority Sort    │
                             │ (Intermediate → Basic) │
                             └───────────┬────────────┘
                                         │
                                         ▼
                             ┌────────────────────────┐
                             │ Balanced Batching      │
                             │ (N >= 4 -> 6 & 5)      │
                             └───────────┬────────────┘
                                         │
                                         ▼
                             ┌────────────────────────┐
                             │ 5-Step Coach Selector  │
                             │ (Checks 7 Constraints) │
                             └───────────┬────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
       🟢 ASSIGN COACH & CLASS                    🔴 FLAG IN OUTPUT 3
    (Output 1, Output 2, Output 5)                (Attention Required Report)
```

---

### 2.1 The 5-Step Coach Selection Algorithm

When assigning a coach to a batch of students for a specific date and time slot, the engine executes this sequence:

1. **Step 1: Qualification Check**: Verifies that the candidate coach is qualified to teach the target student level (checking `CoachModel.can_handle_level`).
2. **Step 2: Priority Matrix Ranking**: Ranks eligible coaches according to the level-wise priority list configured in system rules.
3. **Step 3: Workload Target Preference**: Prioritizes coaches who have not yet reached their preferred target workload (`monthly_capacity_min`) over those who have already met their target.
4. **Step 4: Hard Constraint Evaluation**: Validates 7 mandatory conditions:
   - Is coach marked available on the required day?
   - Does coach match preferred day-wise timing window?
   - Has coach exceeded day-specific class cap (`mon_max` to `sun_max`)?
   - Has coach exceeded monthly maximum capacity limit (`monthly_capacity_max`)?
   - Is coach free during the target slot? (**1 Coach = 1 Class Double-Booking Guard**).
   - If Sunday tournament: is coach excluded from tournament assignments (`Dhaanush`, `Saravanan`)?
   - Does class end by Sunday 3:00 PM ceiling?
5. **Step 5: Fallback & Substitute Selection**: If no primary coach meets all preferred window conditions, checks qualified substitute coaches before flagging as unscheduled.

---

### 2.2 Level Group Scheduling Priority Order

To prevent lower-level classes from exhausting the daily class limits of multi-level coaches, the engine sorts student levels by **Group Number Descending**:

$$\text{Intermediate (8)} \longrightarrow \text{Early Intermediate 2 (7)} \longrightarrow \text{Early Intermediate 1 (6)} \longrightarrow \dots \longrightarrow \text{Basic 1 (1)}$$

Coaches with rare capabilities (e.g. `Arshath` and `Dhaanush` for Intermediate/Early Intermediate) are reserved for high-level classes first, while basic levels are served by broader coach pools (`Bathrinath`, `Abinaya`, `Manikandan`, `Guruvanthana`, `Raveena`).

---

### 2.3 Balanced Batch Grouping Algorithm

Instead of naive greedy packing (which creates orphan undersized batches of 1–3 students when grouping 11, 12, or 13 students), the engine applies **Balanced Partitioning**:

$$k = \max\left(1, \left\lceil \frac{N}{\text{max\_capacity}} \right\rceil\right)$$

- **Example 1 ($N = 11$, Group Batch $G$)**: $k = \lceil 11 / 10 \rceil = 2$ groups. Sizes: **6** and **5** (both $\ge 4$ min capacity).
- **Example 2 ($N = 3$, Group Batch $G$)**: $k = 1$ group. Size: **3** (flagged in Output 3 for admin review with warning `"Group batch size (3) below target minimum 4"`).

---

### 2.4 Mandatory Student Accountability Invariant

Every input student MUST be accounted for in the output. The math invariant is strictly enforced:

$$\text{Total Input Students} = \text{Successfully Scheduled Students} + \text{Unscheduled Students Count}$$

Where:
- **Successfully Scheduled**: Students with `remaining_classes == 0` (Fully Scheduled).
- **Unscheduled / Attention Required**: Students with `remaining_classes > 0` (Flagged in Output 3 with exact failure reasons).

---

## 3. Database Architecture & Schema

The application uses an embedded **SQLite 3** database located at `backend/data/chess_scheduler.db` (or custom path configured via `CHESS_DB_PATH`).

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                         CHESS_SCHEDULER.DB (SQLite 3)                          │
├───────────────────┬───────────────────┬───────────────────┬────────────────────┤
│     schedules     │     students      │      coaches      │   system_config    │
└───────────────────┴───────────────────┴───────────────────┴────────────────────┘
```

### Table 1: `schedules`
Stores full generated schedule snapshots for state recovery and version control.

| Column Name | SQL Type | Description |
|---|---|---|
| `schedule_id` | `TEXT PRIMARY KEY` | Unique ID e.g. `SCH_803605C6` |
| `status` | `TEXT NOT NULL` | Status: `"Draft"` or `"Finalized"` |
| `start_date` | `TEXT NOT NULL` | Start date string (`YYYY-MM-DD`) |
| `end_date` | `TEXT NOT NULL` | End date string (`YYYY-MM-DD`) |
| `total_students` | `INTEGER NOT NULL` | Total students evaluated |
| `scheduled_students` | `INTEGER NOT NULL` | Fully scheduled student count |
| `unscheduled_students` | `INTEGER NOT NULL` | Attention required student count |
| `accountability_passed`| `INTEGER NOT NULL` | Boolean flag (1 = True, 0 = False) |
| `data_json` | `TEXT NOT NULL` | Full serialized `ScheduleResult` JSON object |
| `created_at` | `TEXT NOT NULL` | ISO 8601 timestamp string |

### Table 2: `students`
Stores master student directory.

| Column Name | SQL Type | Description |
|---|---|---|
| `student_id` | `TEXT PRIMARY KEY` | Unique Student ID e.g. `MKS00074` |
| `student_name` | `TEXT NOT NULL` | Full student name |
| `student_level` | `TEXT NOT NULL` | Level e.g. `Basic 1`, `Intermediate` |
| `batch_type` | `TEXT NOT NULL` | Batch code: `G` (Group), `L` (Limited), `I` (Individual) |
| `region_timezone` | `TEXT` | Timezone e.g. `IST`, `EST` |
| `required_classes` | `INTEGER NOT NULL` | Required number of classes per period |
| `data_json` | `TEXT NOT NULL` | Full serialized `StudentModel` JSON object |

### Table 3: `coaches`
Stores master coach directory.

| Column Name | SQL Type | Description |
|---|---|---|
| `coach_name` | `TEXT PRIMARY KEY` | Full coach name e.g. `Bathrinath` |
| `levels_handled_json` | `TEXT NOT NULL` | JSON array of handling levels |
| `monthly_capacity_min`| `INTEGER NOT NULL` | Preferred target workload lower bound |
| `monthly_capacity_max`| `INTEGER NOT NULL` | Maximum workload upper ceiling |
| `data_json` | `TEXT NOT NULL` | Full serialized `CoachModel` JSON object |

### Table 4: `system_config`
Stores active rules registry, level priority matrix, and time slot configurations.

| Column Name | SQL Type | Description |
|---|---|---|
| `config_key` | `TEXT PRIMARY KEY` | Key name (e.g. `"active_config"`) |
| `config_json` | `TEXT NOT NULL` | Full serialized `SystemConfig` JSON object |
| `updated_at` | `TEXT NOT NULL` | Timestamp of last modification |

---

## 4. API Specifications & Output Views

The FastAPI server exposes REST endpoints for web applications, external integrations, and calendar synchronization.

### 4.1 Core API Endpoint Reference

| HTTP Method | Endpoint Path | Description |
|---|---|---|
| `GET` | `/api/health` | API health check & system status |
| `GET` | `/api/config` | Retrieve system rules & level priority matrix |
| `POST` | `/api/config` | Update system configuration rules |
| `POST` | `/api/upload` | Ingest Excel file and generate schedule |
| `POST` | `/api/schedule/run` | Trigger scheduling run for date range |
| `GET` | `/api/schedule/latest/active` | Get active schedule for 0-loss app refresh |
| `GET` | `/api/schedule/{id}/output1` | **Output 1 — Coach Communication Schedule & WhatsApp Text** |
| `GET` | `/api/schedule/{id}/output2` | **Output 2 — Detailed Administrative Schedule & Workload** |
| `GET` | `/api/schedule/{id}/output3` | **Output 3 — Unscheduled / Attention Report** |
| `GET` | `/api/schedule/{id}/output5` | **Output 5 — Student-Wise Timetables** |
| `POST` | `/api/schedule/{id}/assign-student` | Drag & Drop / One-Click assignment resolver |
| `POST` | `/api/schedule/{id}/create-class-for-student` | Create new custom class slot for unscheduled student |
| `DELETE` | `/api/schedule/{id}/class/{class_id}` | Delete class assignment with real-time accountability sync |
| `GET` | `/api/schedule/{id}/coach/{name}/export-ics` | Export iCalendar (`.ics`) file for coach |
| `GET` | `/api/schedule/{id}/student/{id}/export-ics` | Export iCalendar (`.ics`) file for student |
| `GET` | `/api/master/data` | Fetch master student and coach tables |
| `POST` | `/api/master/students` | Add / Edit master student record |
| `DELETE` | `/api/master/students/{id}` | Delete master student record |
| `POST` | `/api/master/coaches` | Add / Edit master coach record |
| `DELETE` | `/api/master/coaches/{name}` | Delete master coach record |

---

### 4.2 System Output Views Summary

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              THE 3 PRIMARY OUTPUTS                              │
├──────────────────────────┬──────────────────────────┬───────────────────────────┤
│ Output 1: Coach Schedule │ Output 2: Admin Schedule │ Output 3: Attention Report│
│ • Date, Day, Time        │ • Full class roster      │ • Unscheduled students    │
│ • Coach names only       │ • Student IDs & levels   │ • Exact failure reasons   │
│ • WhatsApp copy-ready    │ • Workload summary       │ • One-click assignment    │
└──────────────────────────┴──────────────────────────┴───────────────────────────┘
```

- **Output 1 — Coach Communication Schedule**: Designed for quick reading and WhatsApp broadcast. Displays date, day, time, and assigned coach names. Includes a **"Copy Coach Schedule"** button.
- **Output 2 — Detailed Administrative Schedule**: Complete operational breakdown including Date, Time, Coach, Level, Batch Type, Student IDs, Names, and Warnings.
- **Output 3 — Unscheduled / Attention Report**: Visually prominent report highlighting every unscheduled/partially-scheduled student with exact failure reasons and one-click resolution.
- **Output 5 — Student-Wise Timetables**: Individual schedules per student with one-click `.ics` calendar sync for Google/Apple Calendar.

---

## 5. Deployment & Hosting Options

### 5.1 Option 1: Cloud Hosting (Render / Railway / Fly.io / AWS EC2) 🌟 Recommended

- **Frontend**: Host `frontend/` on **Vercel** or **Netlify** (Free tier).
- **Backend**: Host `backend/` on **Render** or **Railway**.
- **Database Persistence**: Attach a **Persistent Storage Volume** to the backend container (mount `/app/data`) so `chess_scheduler.db` persists across restarts.

### 5.2 Option 2: Local Office Network (LAN Server)

Run on one main office PC so staff on academy Wi-Fi can access the app:
```powershell
# 1. Start Backend on Local Network IP
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2. Start Frontend on Local Network IP
npm run dev -- --host
```
Staff access the app at `http://<OFFICE_PC_IP>:5173`.

### 5.3 Option 3: 1-Click Windows Desktop Launcher

Double-click `Start_Mighty_Knight.bat` in the project root to start backend, frontend, and open the app in Chrome/Edge automatically.

---

## 6. PostgreSQL / Supabase Migration Guide

To upgrade from SQLite to PostgreSQL/Supabase for multi-server auto-scaling:

1. Install PostgreSQL adapter: `pip install psycopg2-binary`
2. Set environment variable: `CHESS_DB_PATH="postgresql://user:pass@host:5432/dbname"`
3. Update database connection in [database.py](file:///d:/CODESPACE/chess/backend/app/storage/database.py) to parse `postgresql://` URIs.
4. **Zero Engine Changes**: The core scheduling engine (`scheduler.py`), models (`student.py`, `coach.py`), and React frontend require zero modifications.

---

*— End of Technical Documentation —*
