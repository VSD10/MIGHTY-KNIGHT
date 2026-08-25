# Mighty Knight System — Assumptions & BRD Interpretations

This document tracks all design decisions, rule interpretations, and assumptions made where the Business Requirement Document (`Mighty_Knight_BRD.md`) left specifics open to implementation choices.

---

## 1. Time Slot Standardization & Operating Hours
- **Default Slot Duration**: 1 Hour (60 minutes).
- **Standard Operating Hours** (Mon – Sat):
  - Morning Session: `06:00 AM – 08:00 AM` (Slots: 06:00-07:00, 07:00-08:00)
  - Midday Session: `09:00 AM – 02:00 PM` (Slots: 09:00-10:00, 10:00-11:00, 11:00-12:00, 12:00-01:00, 01:00-02:00)
  - Evening Session: `04:00 PM – 09:00 PM` (Slots: 04:00-05:00, 05:00-06:00, 06:00-07:00, 07:00-08:00, 08:00-09:00)
  - Exceptional Slot: `09:00 PM – 10:00 PM` (Configurable option)
- **Saturday Peak Hours**: `05:00 PM – 09:00 PM` treated with high priority for student demand matching.
- **Sunday Operating Hours**: `09:00 AM – 03:00 PM` max. Normal classes & tournaments must complete by 03:00 PM.

---

## 2. Student Timing Preference Parsing
- **Format Flexibility**: Accepts strings such as `5 PM - 9 PM`, `17:00-21:00`, `6 PM`, `Preferred Time`, `No Preference`, `Not Available`, `NA`.
- **Interpretation Logic**:
  - `Not Available` / `NA` / `No`: The student cannot be scheduled on this day under any circumstances.
  - `No Preference` / `Any` / Blank: Student can be scheduled in any valid operating time slot for that day.
  - Specific Time Range (e.g. `5 PM - 9 PM`): Engine attempts to assign a 1-hour slot falling within this range. If all slots within the preferred range are full or lack coach coverage, the engine evaluates adjacent operating slots on the same day before reporting a failure.

---

## 3. Required Classes Distribution Across Date Windows
- **Monthly Target**: The `required_classes` field in the student record (e.g., 8 classes) is the target for the full monthly period.
- **Date Range / Single Day Scheduling**:
  - If a user schedules for a full month, the engine distributes the 8 classes across the 4 weeks (typically 2 classes per week on preferred days).
  - If a user schedules for a specific date or date range (e.g. 1 week), the target count is proportionally calculated or assigned up to the available preferred days in that window.

---

## 4. Batch Grouping & Minimum Capacity Flagging
- **Group Batch (`G`)**: Max capacity 10, target minimum 4.
  - Students of the same level, batch type `G`, same day, and time slot are grouped together.
  - If fewer than 4 students match for a slot, the system **does not reject the class**; instead, it schedules the class to ensure student progress and flags a warning: `Group Batch capacity below target (X/4 students) — Administrator Review Suggested`.
- **Limited Batch (`L`)**: Capacity 1–3 students.
- **Individual Batch (`I`)**: Capacity 1 student.

---

## 5. Coach Monthly Capacity Ranges
- **Format**: Specified as `min-max` (e.g. `60-90`, `35-40`).
- **Meaning**:
  - `min`: Workload preference target. Scheduler tries to give coaches at least `min` classes before over-concentrating work on a single coach.
  - `max`: Hard ceiling. Automated scheduler will never assign beyond `max` classes in a month.

---

## 6. Sunday & Tournament Rules
- **Time Ceiling**: Sunday classes end strictly by 3:00 PM (15:00).
- **Coach Exclusions**: Coaches `Dhaanush` and `Saravanan` are excluded from Sunday tournament class assignments.
- **Level Restrictions**: `Intermediate` level students do not participate in Sunday tournaments.
- **Class Credit**: A Sunday tournament counts as 1 class towards the student's `required_classes`.

---

## 7. Dynamic Data & Zero Hardcoding
- All level names, level group mappings, coach priority lists, batch sizes, operating hours, and time slot definitions are stored in `backend/app/config.py` / `config.json`.
- The engine dynamically reads the student and coach sheets from any uploaded Excel, making it 100% resilient to changes in student/coach counts or names.
