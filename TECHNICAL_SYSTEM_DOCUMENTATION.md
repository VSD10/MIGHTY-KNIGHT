# ♞ Mighty Knight — Technical System Documentation

**Complete System Architecture, Database Schema, Engine Algorithms & Deployment Guide**

Version 2.0 · Single Source of Technical Truth

---

## 1. System Overview & Technology Stack

**Mighty Knight** is a rule-driven, constraint satisfaction scheduling system engineered for chess academies. It assigns enrolled students to monthly class sessions based on individual quotas (`required_classes`), using master batches as flexible capacity pools and dynamically selecting qualified trainers per session.

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
| **Core Scheduling Engine** | Python 3.12 (`dynamic_scheduler.py`) | Priority-based constraint satisfaction with weekly pacing |
| **Pre-Commit Validation Layer** | Python 3.12 (`validator.py`) | Unified server-side validator for 10 hard rules |
| **Persistence Storage** | SQLite 3 (`backend/data/chess_scheduler.db`) | 0-loss database storage with SHA-256 state fingerprinting |

---

## 2. Core Scheduling Engine Architecture

The engine implements a **Deterministic Priority-Based Constraint Satisfaction Problem (CSP) Solver** featuring dynamic student-to-class scheduling and flexible capacity pools.

```
                             ┌────────────────────────┐
                             │ Master Batch Templates │
                             │ & Academy Time Slots   │
                             └───────────┬────────────┘
                                         │
                                         ▼
                             ┌────────────────────────┐
                             │ Candidate Pool Gen     │
                             │ (Weekdays & Sun < 3PM) │
                             └───────────┬────────────┘
                                         │
                                         ▼
                             ┌────────────────────────┐
                             │ Pass 1: Weekly Pacing  │
                             │ (~4/wk, ~2/wk, ~1/wk)  │
                             └───────────┬────────────┘
                                         │
                                         ▼
                             ┌────────────────────────┐
                             │ Dynamic Coach Match    │
                             │ (Checks 10 Hard Rules) │
                             └───────────┬────────────┘
                                         │
                                         ▼
                             ┌────────────────────────┐
                             │ Pass 2: Deficit Catchup│
                             │ (Open seats + Extra)   │
                             └───────────┬────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
       🟢 ASSIGN COACH & CLASS                    🔴 FLAG IN OUTPUT 3
    (Output 1, Output 2, Output 5)                (Attention Required Report)
```

### 2.1 The 5 Execution Stages

1. **Stage 1: Candidate Session Slot Generation**:
   - Expands master batches into flexible candidate session slots across target dates.
   - Injects fallback operating slot windows (06:00 AM – 10:00 PM weekdays, 09:00 AM – 03:00 PM Sundays) for uncovered levels.
   - Master batches serve as session templates / capacity pools rather than rigid student cohorts.

2. **Stage 2: Pass 1 — Strict Weekly Pacing & Fairness Dispatch**:
   - Distributes student monthly quotas across weeks (`target_weekly = ceil(quota / num_weeks)`):
     - 16 classes: ~4/week (max weekly cap: 5)
     - 8 classes: ~2/week (max weekly cap: 3)
     - 4 classes: ~1/week (max weekly cap: 2)
   - Dispatches slots using Lexicographical Fairness scoring (`deficit * 200 + urgency + continuity`) to prevent high-quota students from starving low-quota students.

3. **Stage 3: Dynamic Qualified Trainer Selection (Per Session)**:
   - Evaluates available coaches using level qualification priority matrix.
   - Enforces single-occupancy (1 coach = 1 class at a time) and day-specific class caps.

4. **Stage 4: Pass 2 — Controlled Deficit Catch-up Pass**:
   - For students with remaining deficits, relaxes weekly pacing targets later in the month.
   - Step 2A fills open seats in existing classes.
   - Step 2B schedules supplemental sessions with available qualified trainers.

5. **Stage 5: Accountability & Root-Cause Diagnosis**:
   - Validates the zero-loss mathematical invariant: `Total Required = Scheduled + Deficit` for every student.
   - Classifies unassigned sessions into diagnostic failure codes in Output 3:
     - `LEVEL_CAPACITY_EXHAUSTED` (No available qualified coach within slot windows)
     - `TRAINER_LEVEL_UNQUALIFIED` (Available coaches cannot teach student level)
     - `SUNDAY_TOURNAMENT_RESTRICTION` (Sunday 15:00 ceiling or tournament exclusions)
     - `STUDENT_UNAVAILABLE_SLOTS` (No mutually available slots)

---

## 3. Database Architecture & Schema

The application uses an embedded **SQLite 3** database located at `backend/data/chess_scheduler.db`.

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                         CHESS_SCHEDULER.DB (SQLite 3)                          │
├───────────────────┬───────────────────┬───────────────────┬────────────────────┤
│     schedules     │     students      │      coaches      │      batches       │
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
Stores master student directory with `required_classes` quota.

### Table 3: `coaches`
Stores master coach directory with capability levels and workload limits.

### Table 4: `batches`
Stores master batch templates (recurring day/time slots, level, and capacity).

---

## 4. Operational Views

- **Daily Schedule Planner**: Visual board for inspecting and modifying day-by-day classes with live drag-and-drop.
- **Output 1 — Coach Schedule**: WhatsApp-ready plain text communication schedule.
- **Output 2 — Detailed Matrix**: Administrative matrix of classes, students, and coaches.
- **Output 3 — Attention Report**: Actionable diagnosis of any unfulfilled quotas.
- **Output 4 — Coach Workload**: Visual breakdown of trainer session hours vs. target capacity.
- **Output 5 — Student Schedules**: Individual student timetables with downloadable `.ics` calendars.
- **Master Data Hub**: Comprehensive CRUD and import manager for Students, Coaches, and Batches.
- **Engine Settings Dashboard**: Visual architectural explanation of the dynamic monthly scheduling engine.

---

## 5. Verification & Testing

Run the complete test suite:
```bash
python -m pytest
```

All 25 unit and integration tests pass, confirming end-to-end constraint enforcement, pacing, accountability, and manual edit pre-commit validation.

---

*— End of Technical Documentation —*
