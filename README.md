# Mighty Knight — Dynamic Academy Scheduling System

**Mighty Knight** is a rule-driven scheduling engine for chess academies, designed according to the specifications in `Mighty_Knight_BRD.md`.

It reads uploaded student and coach Excel data, applies level-wise coach capability and priority order, batch capacities, time slots, operating hours, and mandatory accountability rules to produce practical academy schedules.

---

## Key System Features

- **100% Rule-Driven Architecture (Zero Hardcoding)**: All student levels, coach priority lists, batch sizes, daily limits, monthly capacity ranges, operating hours, and Sunday/tournament rules are dynamically configurable.
- **Mandatory Student Accountability Rule (BRD Section 28)**: Every input student is guaranteed to be accounted for: `Total Input Students == Scheduled + Unscheduled`.
- **Excel Ingestion with Row-Level Validation**: Reads uploaded `.xlsx` files, normalizes headers, validates fields, and reports row-level errors without crashing.
- **Three Genuinely Independent Output Views (BRD Section 42)**:
  1. **Output 1 — Coach Communication Schedule**: Date, Day, Time, and Coach names only, with a **"Copy Coach Schedule" action for WhatsApp-ready plain text**.
  2. **Output 2 — Detailed Administrative Schedule**: Complete class breakdown, student IDs, names, levels, batch types, and compatibility warnings.
  3. **Output 3 — Unscheduled / Administrator Attention Report**: Visually prominent report highlighting every unscheduled/partially-scheduled student with exact failure reasons.
- **Manual Administrative Edits**: Allows admin overrides with real-time rule violation checks (coach overlap, daily caps, Sunday restrictions) before saving.

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

# Run pytest test suite (All 10 tests)
$env:PYTHONPATH="backend"; python -m pytest backend/tests

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
├── NOTES.md                         # Documented assumptions & rule interpretations
├── README.md                        # Setup and run guide
├── sample_data/
│   └── mighty_knight_template.xlsx  # Sample Excel workbook (Students + Coaches sheets)
├── backend/
│   ├── app/
│   │   ├── config.py                # Configurable level priorities & rules
│   │   ├── main.py                  # FastAPI endpoints & CORS
│   │   ├── models/                  # Pydantic data models
│   │   ├── ingestion/               # Excel parser & validator
│   │   ├── engine/                  # Core scheduler, coach selector, batch builder
│   │   ├── outputs/                 # Output 1, 2, 3 generators
│   │   └── storage/                 # SQLite database persistence
│   ├── tests/                       # Comprehensive pytest suite (10 tests)
│   ├── sample_generator.py          # Script to generate sample Excel template
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── components/              # React UI components
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
$env:PYTHONPATH="backend"; python -m pytest backend/tests
```

Expect output:
```
============================== 10 passed in 3.65s ==============================
```
