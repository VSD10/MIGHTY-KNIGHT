# ♞ Mighty Knight — Scheduling Engine Architecture

## 1. Engine Identification & Overview

The scheduling core of Mighty Knight is a **Priority-Based Constraint Satisfaction Engine** built specifically for complex chess academy logistics. 

Unlike simple calendar tools or naive random assigners, this engine evaluates multi-dimensional constraints (capabilities, day preferences, time slots, workload caps, and academy policies) to deterministically generate an optimal, conflict-free schedule.

| Attribute | Specification |
|---|---|
| **Engine Type** | Deterministic Priority-Based Constraint Satisfaction Problem (CSP) Solver |
| **Language & Runtime** | Python 3.12 + FastAPI |
| **Core Modules** | `app.engine.scheduler`, `app.engine.coach_selector`, `app.engine.batch_builder`, `app.engine.accountability` |
| **Data Integrity Invariant** | `Total Input Students == Scheduled Students + Unscheduled Students` |
| **Database Storage** | SQLite structured via Pydantic Models (PostgreSQL-ready) |

---

## 2. Engine Architecture & Component Flow

```
                             ┌────────────────────────┐
                             │ Excel Data Ingestion   │
                             │ (pandas + openpyxl)    │
                             └───────────┬────────────┘
                                         │
                                         ▼
                             ┌────────────────────────┐
                             │  ACTIVE_DATA Session   │
                             │ (Students & Coaches)   │
                             └───────────┬────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      SCHEDULER PIPELINE CONTROLLER                              │
│                         (app.engine.scheduler)                                  │
└────────┬───────────────────────────────┬───────────────────────────────┬────────┘
         │                               │                               │
         ▼                               ▼                               ▼
┌─────────────────┐             ┌─────────────────┐             ┌─────────────────┐
│  Batch Builder  │             │ Coach Selector  │             │ Accountability  │
│ (batch_builder) │             │(coach_selector) │             │ (accountability)│
└─────────────────┘             └─────────────────┘             └─────────────────┘
  • Same Level                    • 5-Step Selection              • Verifies 100%
  • Same Batch Type               • 7 Hard Constraints             student match
  • Caps: G (8-10), L(3), I(1)    • Priority Ranking              • Audits errors
```

---

## 3. The 5-Step Coach Selection Algorithm (BRD Section 34)

When a batch of students needs a class on a specific date and time slot, the engine evaluates available coaches using a strict 5-step selection sequence:

```
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: Level Qualification                                     │
│ Is the coach listed as qualified for the student's level?       │
└────────────────────────────────────────┬─────────────────────────┘
                                         │ YES
                                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: Level-Wise Priority Ranking                              │
│ Sort qualified coaches according to config priority for level:   │
│ • Basic 1–2: Guruvanthana -> Dhaanush -> Saravanan...           │
│ • Intermediate: Prakash -> Saravanan -> Abinaya...              │
└────────────────────────────────────────┬─────────────────────────┘
                                         │ RANKED
                                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 3: Slot Availability & Overlap Guard                       │
│ Is the coach already assigned to another class at this time?    │
│ (Enforces 1 Coach = 1 Class Rule)                                │
└────────────────────────────────────────┬─────────────────────────┘
                                         │ FREE
                                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 4: Daily Class Cap Check                                   │
│ Has the coach reached their daily max class limit?              │
│ (Mon–Fri max 4, Sat max 5, Sun max 2)                           │
└────────────────────────────────────────┬─────────────────────────┘
                                         │ UNDER CAP
                                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 5: Monthly Capacity Workload Check                          │
│ Has the coach reached their max monthly target capacity?         │
└────────────────────────────────────────┬─────────────────────────┘
                                         │ UNDER CAP
                                         ▼
                              🟢 ASSIGN COACH TO CLASS
```

---

## 4. The 7 Hard Constraint Enforcement Rules (BRD Section 35)

The engine strictly validates **7 non-negotiable condition checks** before confirming any class assignment:

1. **Qualification Check**: Coach capability list must include student level.
2. **Day Availability**: Coach must not be marked off or unavailable on the target date.
3. **Double-Booking Guard**: A coach cannot teach two classes simultaneously.
4. **Daily Workload Limit**: Cannot exceed day-specific class cap (`mon_max` to `sun_max`).
5. **Monthly Workload Limit**: Cannot exceed maximum monthly workload cap (`monthly_capacity_max`).
6. **Sunday Operating Ceiling**: Sunday classes must finish by **03:00 PM** (unless explicitly overridden).
7. **Sunday Tournament Exclusion**: If Sunday Preference is `"No Sunday Tournaments"`, coach is excluded from Sunday tournament slots.

---

## 5. Batch Building Dynamics (BRD Section 31 & 32)

Students are grouped into compatible batches before assigning to coaches:

- **Group Batch (`G`)**: Target size 4–10 students. Same level, same batch type.
- **Limited Batch (`L`)**: Target size 1–3 students.
- **Individual Batch (`I`)**: Single student (1-on-1 coaching).

If a group batch has fewer than 4 students, the engine schedules the batch but attaches a diagnostic warning flag (*Group batch size below target minimum 4*) for administrative review.

---

## 6. Mandatory Accountability Tracker Engine (BRD Section 40)

To guarantee that **zero students are lost or forgotten**, the engine executes a mandatory audit check at the end of every run:

$$\text{Total Input Students} = \text{Successfully Scheduled Students} + \text{Unscheduled Students Count}$$

If a student cannot be assigned a complete schedule:
1. They are placed in **Output 3 (Unscheduled / Administrator Attention Report)**.
2. The engine logs the **exact diagnostic reason** (e.g. *No qualified coach available for Basic 1 at 05:00 PM*, *Coach daily cap reached*, *Student marked unavailable*).

---

## 7. Engine Source Code Index

| Module Path | Primary Responsibility | Key Functions |
|---|---|---|
| [scheduler.py](file:///d:/CODESPACE/chess/backend/app/engine/scheduler.py) | Main pipeline orchestrator | `run_scheduler()` |
| [coach_selector.py](file:///d:/CODESPACE/chess/backend/app/engine/coach_selector.py) | 5-step coach selection & 7 constraints | `select_coach_for_batch()`, `can_coach_teach_slot()` |
| [batch_builder.py](file:///d:/CODESPACE/chess/backend/app/engine/batch_builder.py) | Student batching & capacity caps | `group_students_for_slot()`, `BatchGroup` |
| [accountability.py](file:///d:/CODESPACE/chess/backend/app/engine/accountability.py) | Data integrity audit & math invariant | `audit_student_accountability()` |
| [time_utils.py](file:///d:/CODESPACE/chess/backend/app/engine/time_utils.py) | Time slot parsing & Sunday rules | `parse_time_slot()`, `is_sunday_afternoon_violation()` |
