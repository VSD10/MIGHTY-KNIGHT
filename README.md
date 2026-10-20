# Mighty Knight — Dynamic Academy Scheduling System

**Mighty Knight** is a rule-driven scheduling engine for chess academies, designed according to the specifications in `Mighty_Knight_BRD.md`.

It assigns students to class sessions dynamically based on their individual monthly enrolled quotas (`required_classes`), using master batches as **flexible capacity pools and session templates**, and dynamically assigns qualified trainers per session.

---

## Key System Features

- **Dynamic Monthly Quota Scheduling**: Students are scheduled to class sessions dynamically according to their required monthly class counts (e.g., 16, 8, or 4) with even weekly pacing (~4/wk for 16, ~2/wk for 8, ~1/wk for 4).
- **Flexible Capacity Pools**: Master batches provide recurring slot templates and level requirements rather than permanently locked cohorts. Trainers are selected dynamically per session.
- **Strict Constraint Enforcement**:
  - Trainer overlap guard (1 trainer = 1 class at a time).
  - Student daily limit (at most 1 class per calendar day).
  - Monthly quota cap (never scheduled beyond `required_classes`).
  - Level qualification matching and Sunday 3:00 PM operating limit.
  - Hard batch capacity limits (Group max 10, Limited max 4, Individual 1; Group min 4 is a soft warning).
- **Mandatory Student Accountability**: Zero students are forgotten. Mathematical invariant enforced:
  $$\text{Required Classes} = \text{Scheduled Classes} + \text{Remaining Deficit}$$
- **Independent Operational Views**:
  1. **Daily Schedule Planner**: Interactive timeline board for viewing and customizing day-by-day classes with live drag-and-drop and slot editing.
  2. **Output 1 — WhatsApp Coach Schedule**: Date, Day, Time, and Trainer names with one-click WhatsApp clipboard copy.
  3. **Output 2 — Detailed Administrative Matrix**: Complete class roster, student levels, batch types, and compatibility checks.
  4. **Output 3 — Attention Required Report**: Flags unscheduled/deficit students with diagnostic root causes.
  5. **Output 4 — Coach Workload**: Visual breakdown of trainer session hours vs. target capacity.
  6. **Output 5 — Student Schedules**: Individual student schedules and downloadable iCalendar `.ics` files.
  7. **Master Data Hub**: Comprehensive manager for Students, Coaches, and Batches with SQLite persistence.
  8. **Engine Settings Dashboard**: Visual architectural explanation of the 5-stage dynamic scheduling process and hard/soft rules.
- **Unified Server-Side Validation**: All manual edits, additions, and deletions are validated on the server across the entire schedule before committing; violations reject with HTTP 400.
- **SHA-256 State Fingerprinting**: Invalidation of draft schedules on master data updates, with protection for Finalized schedules.

---

## Setup & Running Instructions

### Prerequisites
- Python 3.10+
- Node.js v18+ and npm

---

### 1. Run Backend (FastAPI + Python)

```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Run pytest test suite (All 25 tests)
python -m pytest

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

The API server will run at `http://localhost:8000`. API documentation is available at `http://localhost:8000/docs`.

---

### 2. Run Frontend (React + Vite)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```

The Web UI will be available at `http://localhost:5173`.

---

## Project Structure

```
chess/
├── Mighty_Knight_BRD.md             # Single source of truth BRD
├── SCHEDULING_ENGINE.md             # Detailed engine architecture & 5-stage pipeline
├── TECHNICAL_SYSTEM_DOCUMENTATION.md # Technical documentation
├── README.md                        # Setup and run guide
├── backend/
│   ├── app/
│   │   ├── config.py                # SystemConfig & ConstraintRule models
│   │   ├── main.py                  # FastAPI endpoints & CORS
│   │   ├── models/                  # Pydantic data models (student, coach, batch, schedule)
│   │   ├── ingestion/               # Excel parser & validator
│   │   ├── engine/                  # dynamic_scheduler, coach_selector, validator, accountability
│   │   ├── outputs/                 # Output 1, 2, 3, 5 generators
│   │   └── storage/                 # SQLite database persistence & SHA-256 fingerprinting
│   ├── data/
│   │   └── chess_scheduler.db       # Active SQLite database
│   ├── tests/                       # Comprehensive pytest suite (25 tests)
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── components/              # React UI components (SettingsView, DailySchedulePlanner, etc.)
    │   ├── services/                # Axios API client
    │   ├── App.jsx
    │   └── index.css                # Modern dark/gold UI styling
    ├── package.json
    └── vite.config.js
```

---

## Running Verification Tests

Run backend unit and integration test suite:

```bash
python -m pytest
```

Expect output:
```
============================== 25 passed in 5.00s ==============================
```
