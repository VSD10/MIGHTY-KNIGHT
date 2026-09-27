# ♞ Mighty Knight — Scheduling Engine Architecture

## 1. Engine Overview & Core Principles

The Mighty Knight scheduler is a **Deterministic Priority-Based Constraint Satisfaction Problem (CSP) Engine** designed for chess academy logistics.

### Core Architectural Model
- **Dynamic Student-to-Class Scheduling**: Students are scheduled to class sessions dynamically based on their individual monthly enrolled quotas (`required_classes`, e.g. 16, 8, or 4).
- **Flexible Capacity Pools**: Master batches serve as **reusable session templates and capacity pools** (defining level, batch type, and recurring weekly time patterns), **not permanently locked student cohorts or fixed trainer ownership**.
- **Dynamic Qualified Trainer Selection**: Any trainer qualified for the student level who is available and within their daily and monthly workload limits can be selected.
- **Strict Mathematical Accountability**: Zero students or sessions are lost:
  $$\text{Required Classes} = \text{Scheduled Classes} + \text{Remaining Deficit}$$

| Attribute | Specification |
|---|---|
| **Engine Type** | Deterministic Priority-Based Constraint Satisfaction Problem (CSP) Solver |
| **Language & Runtime** | Python 3.12 + FastAPI |
| **Core Modules** | `app.engine.dynamic_scheduler`, `app.engine.scheduler`, `app.engine.coach_selector`, `app.engine.validator`, `app.engine.accountability` |
| **Data Integrity Invariant** | `Total Required Classes == Total Scheduled Classes + Total Unassigned Deficit` |
| **Persistence Storage** | SQLite (`backend/data/chess_scheduler.db`) with SHA-256 State Fingerprinting |

---

## 2. The 5-Stage Scheduling Pipeline

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: Candidate Session Slot Generation                                       │
│ • Expands master batches into flexible candidate session slots across the month. │
│ • Generates fallback candidate slots from operating hours for unmet demand.      │
│ • Excludes Sunday sessions ending after 3:00 PM (15:00).                         │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: Pass 1 — Strict Weekly Pacing & Fairness Dispatch                       │
│ • Paces quotas evenly across weeks (~4/wk for 16, ~2/wk for 8, ~1/wk for 4).    │
│ • Enforces at most 1 class per student per calendar date.                        │
│ • Prioritizes students with largest relative deficit to prevent starvation.     │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: Dynamic Qualified Trainer Selection (Per Session)                       │
│ • Verifies trainer level qualification against academy priority matrix.          │
│ • Validates trainer day availability and preferred timing windows.               │
│ • Enforces single-occupancy (1 coach = 1 class at a time) & daily/monthly caps. │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 4: Pass 2 — Controlled Deficit Catch-up Pass                              │
│ • Relaxes weekly pacing targets later in the month for students with deficits.   │
│ • Step 2A: Inserts students into open seats of existing compatible classes.      │
│ • Step 2B: Schedules supplemental sessions with available qualified trainers.    │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 5: Exact Accountability & Output 3 Diagnosis                               │
│ • Validates zero-loss invariant for 100% of enrolled students.                   │
│ • Classifies unassigned sessions into actionable diagnostic root-cause codes.    │
│ • Computes SHA-256 state fingerprint and persists schedule atomically.           │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Constraint System: Hard Rules vs. Soft Optimization

### 3.1 Hard Feasibility Constraints (100% Non-Negotiable)
These constraints are strictly validated by both the automated scheduler and the pre-commit mutation validator for all manual edits:

1. **Trainer Overlap Guard**: No trainer can teach two classes simultaneously (single occupancy).
2. **Student Daily Limit**: At most 1 class per student per calendar date (zero same-day duplicates).
3. **Student Monthly Quota Cap**: A student is never scheduled beyond their enrolled `required_classes`.
4. **Trainer Level Qualification**: A trainer must be certified to teach the student's level.
5. **Day Availability**: Both student and trainer must be confirmed available on that calendar day.
6. **Batch Capacity Ceilings**: Group $\le 10$ students, Limited $\le 4$ students, Individual $= 1$ student.
7. **Trainer Workload Limits**: Daily class limit per day-of-week and monthly maximum workload hours.
8. **Sunday Tournament Restrictions**: All Sunday classes must end by 3:00 PM; designated tournament coaches and levels are excluded.
9. **Unified Server-Side Validation**: All manual planner actions (create, edit, delete, assign) are validated server-side on the entire schedule; violations reject with HTTP 400.

### 3.2 Soft Optimization Targets (Fairness & Preferences)
These targets are balanced using deterministic scoring without rejecting feasible assignments:

1. **Even Weekly Pacing**: Spreads sessions evenly (~4/wk for 16, ~2/wk for 8, ~1/wk for 4) with controlled late-month relaxation.
2. **Group Batch Minimum of 4**: Group batches target $\ge 4$ students. If fewer compatible students exist, a soft notice is recorded, but students are **never left unscheduled**.
3. **Time Slot & Day Preferences**: Favors preferred student and trainer time windows.
4. **Continuity Scoring**: Soft preference for students who previously trained together or with the template's preferred trainer.
5. **Trainer Workload Balance**: Distributes sessions across qualified trainers toward their monthly target minimums.

---

## 4. Master Data Fingerprinting & Finalized Schedule Guard

To guarantee that schedules never become silently misaligned with master data:
1. **SHA-256 Fingerprint**: The system calculates a cryptographic hash over all students, trainers, batches, and system configuration.
2. **Draft Schedules**: If master data changes, Draft schedules automatically invalidate and re-run on load.
3. **Finalized Schedules**: Finalized schedules are **never silently overwritten**. If master data changes, the schedule is flagged with `is_stale = True` and a descriptive warning requiring an explicit administrative re-run.

---

## 5. Engine Source Code Reference

| Module Path | Primary Responsibility |
|---|---|
| [dynamic_scheduler.py](file:///d:/CODESPACE/chess/backend/app/engine/dynamic_scheduler.py) | Dynamic candidate generation, 2-pass pacing, fairness scoring, and deficit catch-up |
| [scheduler.py](file:///d:/CODESPACE/chess/backend/app/engine/scheduler.py) | Main pipeline entry point and global schedule integrity validation |
| [coach_selector.py](file:///d:/CODESPACE/chess/backend/app/engine/coach_selector.py) | Trainer level qualification, slot conflict checks, and workload limits |
| [validator.py](file:///d:/CODESPACE/chess/backend/app/engine/validator.py) | Authoritative server-side validator for 10 hard constraints and atomic output recomputation |
| [accountability.py](file:///d:/CODESPACE/chess/backend/app/engine/accountability.py) | Data integrity audit, math invariant verification, and Output 3 diagnostics |
| [database.py](file:///d:/CODESPACE/chess/backend/app/storage/database.py) | SQLite persistence, master data sanitization, and SHA-256 state fingerprinting |
