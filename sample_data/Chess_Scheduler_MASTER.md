# MASTER FILE — Chess Scheduler AI
## Use this file as the ONLY current scheduling reference

IMPORTANT:
- Ignore and do not rely on any previous schedule files, previous generated outputs, or earlier instructions outside this current upload.
- Treat this MASTER FILE plus the current Excel template/reference I upload with it as the complete source of truth.
- Do not merge old and new schedule data.
- Do not invent missing students, trainers, times, days, batches, or planned-class limits.
- When a new approved monthly Excel is supplied later, that new approved month becomes the new reference month for future generation.

---

# PART A — SCHEDULING RULES

# Chess Coaching Monthly Scheduler — Reference Data & Rules

> **Reference source:** `Sep'26 Schedule 24.9.26(3).xlsx` (September 2026 schedule).
> This file is a normalized Markdown representation for an AI scheduling agent.

## 1. Scheduling objective

Generate the next month's schedule from the reference month while preserving the students' recurring attendance days, assigned class slots, trainer assignments, monthly Planned Classes limit, batches, and workbook structure.

## 2. Non-negotiable scheduling rules

1. **Reference-first:** Treat the latest approved monthly workbook as the source of truth. Do not invent students, trainers, batches, times, or class days.
2. **Attendance days are recurrence rules:** A student's eligible days come from the weekdays on which that student is scheduled in the reference month.
3. **Class assignment is fixed:** Reuse the reference student's time + trainer assignment for the corresponding recurring weekday/slot. Do not randomly move a student to another trainer.
4. **Monthly Planned Classes is a hard ceiling:** Never schedule more classes for a student than their `Planned Classes` value.
5. **Calendar conversion:** Convert the recurring weekday pattern to actual dates in the target month. Do not copy September calendar dates by day-of-month.
6. **Preserve exceptions:** The September reference contains some students with multiple trainer/time variants on the same weekday. These are allowed source patterns and must not be silently collapsed. Preserve the exact slot pattern unless an explicit business rule says otherwise.
7. **Blank Planned Classes:** When `Planned Classes` is blank/null, do not invent a new quota. Use the latest approved reference month as the fallback cap and flag the record for review if the agent supports validation flags.
8. **Class/group counting:** For reporting, one class = one unique `(date + start time + trainer)` group, regardless of number of students in that group.
9. **Student counting:** Individual student assignments are counted separately from group classes.
10. **No overbooking by student cap:** A student may be scheduled on an eligible recurring day only while their monthly cap has remaining capacity.
11. **Preserve workbook format:** Keep the original student rows, metadata columns, date-pair structure, comments, formatting, and naming conventions.
12. **Future months:** The same process applies recursively. Use the latest approved month as the reference for the next month, and do not drift the schedule rules over time unless an authorized change is supplied.

## 3. Workbook data model

| Field | Meaning |
|---|---|
| `Student Name` | Student identifier/name; preserve exactly |
| `Stud ID` | Student ID; preserve exactly |
| `MKCA Rating` | Rating from source workbook |
| `Level` | Student level |
| `Batch` | Batch/group label |
| `Planned Classes` | Monthly maximum for scheduling; hard cap |
| `Actual Classes` | Daily class/group count summary |
| `Date pair columns` | One date column + one trainer column per calendar day |
| `Time cell` | Student's scheduled start time |
| `Trainer cell` | Assigned trainer for that student's class |
| `Comments` | Preserve source comments |

## 4. Generation algorithm

1. Load the latest approved workbook.
2. Read every student's metadata and Planned Classes.
3. For each student, collect the recurring weekday → time → trainer slots observed in the reference month.
4. Create every actual calendar date in the target month whose weekday matches one of the student's eligible recurrence weekdays.
5. For each eligible date, assign the corresponding reference slot (time + trainer). If a weekday has multiple source variants, preserve those variants according to their observed occurrence pattern; do not merge them into an invented single trainer.
6. Count the student's generated assignments in chronological order and stop at the Planned Classes cap.
7. Write the target month dates into the date-pair columns, keeping time cells and trainer cells aligned.
8. Recalculate daily Actual Classes as unique `(date + time + trainer)` groups.
9. Run validation before export.

## 5. Validation checklist

- Every target-month date is valid and has the correct weekday.
- No student exceeds Planned Classes.
- No scheduled entry has a missing trainer or time unless that exception exists in the source and is intentionally preserved.
- Student Name / Stud ID / Level / Batch remain unchanged from the reference.
- Every assigned trainer is one of the student's reference trainers unless an authorized trainer change exists.
- Every scheduled weekday is a recurrence weekday supported by the reference.
- Daily Actual Classes equals the number of unique `(date + time + trainer)` groups.
- No duplicate student assignment for the exact same date/time/trainer.
- Comments are preserved.
- Date/time values are stored as Excel dates/times, not text where the source uses Excel date/time cells.

## 6. Reference-month statistics

- Students in reference workbook: **127**
- Reference month: **September 2026**
- Calendar days in reference: **30**
- Students with a non-blank Planned Classes value: **124**
- Students with a blank Planned Classes value: **3**

## 7. Normalized student reference data

Each row below is the machine-readable reference for one student. `slots` are exact recurring patterns observed in September and include how many times the pattern appeared in that month.

| Student | Stud ID | Level | Batch | Planned | Sep Entries | Reference Weekdays | Trainers | Exact recurring slots |
|---|---|---|---|---:|---:|---|---|---|
| B.V.Tijesh | MKS00219 | Basic | G Basic1 | 12 | 12 | Monday, Wednesday, Friday | Abinaya | Monday 7:00 PM — Abinaya (x4); Wednesday 7:00 PM — Abinaya (x4); Friday 7:00 PM — Abinaya (x4) |
| A.Bavinesh | MKS00214 | Basic | G Basic1 | 12 | 12 | Monday, Wednesday, Friday | Abinaya | Monday 7:00 PM — Abinaya (x4); Wednesday 7:00 PM — Abinaya (x4); Friday 7:00 PM — Abinaya (x4) |
| C.V.Chanvika | MKS00196 | Basic | L Basic1 | 12 | 12 | Monday, Wednesday, Friday | Abinaya | Monday 7:00 PM — Abinaya (x4); Wednesday 7:00 PM — Abinaya (x4); Friday 7:00 PM — Abinaya (x4) |
| Sachin | MKS00059 | Intermediate | L Intermediate2 | 12 | 12 | Monday, Thursday, Friday, Saturday, Sunday | Arshath, Dhaanush | Monday 6:00 PM — Dhaanush (x3); Thursday 5:30 PM — Arshath (x2); Friday 5:30 PM — Arshath (x2); Saturday 5:00 PM — Arshath (x2); Saturday 6:00 PM — Arshath (x1); Sunday 10:00 AM — Arshath (x2) |
| Selvakrishna RK | MKS00167 | Intermediate | G Intermediate2 | 12 | 13 | Monday, Tuesday, Friday, Saturday, Sunday | Arshath, Dhaanush, Prakash | Monday 2:00 PM — Arshath (x1); Tuesday 8:00 PM — Dhaanush (x4); Tuesday 8:00 PM — Prakash (x1); Friday 5:30 PM — Arshath (x2); Saturday 6:00 PM — Arshath (x2); Saturday 7:00 PM — Arshath (x1); Sunday 10:00 AM — Dhaanush (x1); Sunday 11:00 AM — Arshath (x1) |
| Srikavi Bharathi | MKS00045 | Intermediate | G Intermediate2 | 14 | 13 | Monday, Tuesday, Friday, Saturday, Sunday | Arshath, Dhaanush, Prakash | Monday 2:00 PM — Arshath (x1); Tuesday 8:00 PM — Dhaanush (x4); Tuesday 8:00 PM — Prakash (x1); Friday 5:30 PM — Arshath (x2); Saturday 6:00 PM — Arshath (x2); Saturday 7:00 PM — Arshath (x1); Sunday 10:00 AM — Dhaanush (x1); Sunday 11:00 AM — Arshath (x1) |
| Krishiv Ajay | MKS00037 | Intermediate | G Intermediate2 | 12 | 12 | Monday, Tuesday, Friday, Saturday, Sunday | Arshath, Dhaanush, Prakash | Monday 2:00 PM — Arshath (x1); Tuesday 8:00 PM — Dhaanush (x4); Tuesday 8:00 PM — Prakash (x1); Friday 5:30 PM — Arshath (x2); Saturday 6:00 PM — Arshath (x2); Saturday 7:00 PM — Arshath (x1); Sunday 11:00 AM — Arshath (x1) |
| YAASHVIN A/L SATEESHKUMAR | MKS00065 | Intermediate | G Intermediate2 | 10 | 10 | Monday, Wednesday, Thursday, Friday, Saturday, Sunday | Arshath, Dhaanush | Monday 2:00 PM — Arshath (x1); Wednesday 6:00 PM — Dhaanush (x1); Thursday 5:30 PM — Arshath (x2); Friday 5:30 PM — Arshath (x2); Saturday 6:00 PM — Arshath (x2); Saturday 7:00 PM — Arshath (x1); Sunday 11:00 AM — Arshath (x1) |
| Sarvin | MKS00060 | Intermediate | G Intermediate2 | 10 | 11 | Monday, Wednesday, Thursday, Friday, Saturday, Sunday | Arshath, Dhaanush | Monday 2:00 PM — Arshath (x1); Wednesday 6:00 PM — Dhaanush (x1); Thursday 5:30 PM — Arshath (x2); Friday 5:30 PM — Arshath (x2); Saturday 6:00 PM — Arshath (x2); Saturday 7:00 PM — Arshath (x1); Sunday 10:00 AM — Dhaanush (x1); Sunday 11:00 AM — Arshath (x1) |
| Vedh Pabba | MKS00190 | Beginner | I Beginner2 | 8 | 8 | Thursday, Friday | Bathri | Thursday 6:00 AM — Bathri (x4); Friday 6:00 AM — Bathri (x4) |
| Magizh | MKS00213 | Basic | I Basic1 | 8 | 7 | Tuesday, Friday | Bathri | Tuesday 11:00 AM — Bathri (x4); Friday 11:00 AM — Bathri (x3) |
| Harri mithran P | MKS00210 | Basic | I Basic2 | 9 | 9 | Tuesday, Friday | Bathri | Tuesday 5:00 PM — Bathri (x5); Friday 5:00 PM — Bathri (x4) |
| V. Dhaksha | MKS00110 | Beginner | I Beginner1 | 11 | 15 | Monday, Tuesday, Wednesday, Thursday, Friday | Bathri, Prakash, bathri | Monday 7:00 PM — Bathri (x3); Tuesday 7:00 PM — Bathri (x3); Tuesday 7:00 PM — bathri (x1); Wednesday 7:00 PM — Bathri (x1); Wednesday 7:00 PM — Prakash (x1); Wednesday 7:00 PM — bathri (x1); Thursday 7:00 PM — Bathri (x1); Friday 6:00 PM — Bathri (x1); Friday 7:00 PM — Bathri (x2); Friday 7:00 PM — bathri (x1) |
| HAASHINI  SHRIVY V | MKS00115 | Beginner | G beginner1 | 10 | 10 | Monday, Tuesday, Friday, Saturday, Sunday | Bathri, Guru, Prakash | Monday 3:00 PM — Bathri (x1); Monday 6:00 PM — Prakash (x1); Tuesday 6:00 PM — Prakash (x2); Friday 7:00 PM — Bathri (x1); Saturday 8:00 PM — Bathri (x1); Saturday 8:00 PM — Guru (x1); Sunday 11:00 AM — Guru (x3) |
| H V Kanishk | MKS00154 | Beginner | G beginner1C | 12 | 12 | Tuesday, Friday, Saturday, Sunday | Abinaya, Bathri, Guru, Prakash, bathri | Tuesday 8:00 PM — Bathri (x1); Friday 7:00 PM — Prakash (x3); Friday 7:00 PM — bathri (x1); Saturday 8:00 PM — Bathri (x4); Sunday 11:00 AM — Abinaya (x1); Sunday 11:00 AM — Guru (x2) |
| S. Thashwin Raj | MKS00155 | Beginner | G beginner1C | 13 | 12 | Tuesday, Thursday, Friday, Saturday, Sunday | Bathri, Guru, Prakash, bathri | Tuesday 8:00 PM — Bathri (x1); Thursday 8:00 PM — Bathri (x1); Friday 7:00 PM — Prakash (x3); Friday 7:00 PM — bathri (x1); Saturday 8:00 PM — Bathri (x3); Sunday 11:00 AM — Guru (x3) |
| A R Thatchiraa Shree | MKS00172 | Beginner | G beginner1s | 12 | 11 | Tuesday, Friday, Saturday, Sunday | Bathri, Guru, Prakash, bathri | Tuesday 8:00 PM — Bathri (x1); Friday 7:00 PM — Prakash (x3); Friday 7:00 PM — bathri (x1); Saturday 8:00 PM — Bathri (x3); Sunday 11:00 AM — Guru (x3) |
| Vikash | MKS00168 | Beginner | G beginner1C | 12 | 11 | Thursday, Friday, Saturday, Sunday | Bathri, Guru, Prakash, bathri | Thursday 8:00 PM — Bathri (x1); Friday 7:00 PM — Prakash (x3); Friday 7:00 PM — bathri (x1); Saturday 8:00 PM — Bathri (x3); Sunday 11:00 AM — Guru (x3) |
| D R RAJAGOPALAN | MKS00176 | Beginner | G beginner1D | 12 | 13 | Tuesday, Thursday, Friday, Saturday, Sunday | Abinaya, Bathri | Tuesday 8:00 PM — Bathri (x1); Thursday 8:00 PM — Bathri (x1); Friday 8:00 PM — Bathri (x4); Saturday 8:00 PM — Bathri (x4); Sunday 10:00 AM — Abinaya (x3) |
| S.P.NEHASRI | MKS00157 | Basic | G Basic2A | 13 | 12 | Tuesday, Friday, Saturday, Sunday | Abinaya, Bathri, Guru, bathri | Tuesday 8:00 PM — Bathri (x1); Friday 8:00 PM — Bathri (x3); Friday 8:00 PM — bathri (x1); Saturday 8:00 PM — Bathri (x3); Saturday 8:00 PM — Guru (x1); Sunday 11:00 AM — Abinaya (x3) |
| P.V Subhiksha | MKS00150 | Beginner | I Beginner1 | 10 | 10 | Tuesday, Thursday, Friday | Dhaanush | Tuesday 5:00 PM — Dhaanush (x5); Thursday 5:00 PM — Dhaanush (x2); Friday 5:00 PM — Dhaanush (x3) |
| Nithesh Nagarathinam | MKS00054 | Early Intermediate | L Early Intermediate1 | 24 | 24 | Monday, Tuesday, Wednesday, Thursday, Friday, Saturday | Dhaanush | Monday 6:00 PM — Dhaanush (x3); Tuesday 6:00 PM — Dhaanush (x5); Wednesday 6:00 PM — Dhaanush (x4); Thursday 6:00 PM — Dhaanush (x4); Friday 6:00 PM — Dhaanush (x4); Saturday 6:00 PM — Dhaanush (x4) |
| Rohith kumar.B | MKS00207 | beginner | G Beginner2 | 16 | 15 | Monday, Tuesday, Friday, Saturday, Sunday | Abinaya, Dhaanush, Guru, Hema, Prakash | Monday 6:00 PM — Prakash (x1); Monday 7:00 PM — Dhaanush (x3); Tuesday 7:00 PM — Dhaanush (x1); Friday 6:00 PM — Guru (x1); Friday 7:00 PM — Dhaanush (x2); Saturday 5:00 PM — Dhaanush (x4); Sunday 10:00 AM — Abinaya (x2); Sunday 11:00 AM — Hema (x1) |
| V.D. THARUN ADITHYA | MKS00212 | Beginner | G beginner2 | 12 | 14 | Monday, Tuesday, Friday, Saturday, Sunday | Abinaya, Dhaanush, Prakash, hema | Monday 7:00 PM — Dhaanush (x4); Tuesday 7:00 PM — Dhaanush (x1); Friday 7:00 PM — Dhaanush (x3); Friday 7:00 PM — Prakash (x1); Saturday 5:00 PM — Dhaanush (x2); Sunday 10:00 AM — Abinaya (x2); Sunday 11:00 AM — hema (x1) |
| Yuviga | MKS00107 | Beginner | G Beginner2 | 12 | 12 | Monday, Tuesday, Friday, Sunday | Abinaya, Dhaanush, Guru | Monday 7:00 PM — Dhaanush (x4); Tuesday 7:00 PM — Dhaanush (x1); Friday 6:00 PM — Guru (x1); Friday 7:00 PM — Dhaanush (x3); Sunday 10:00 AM — Abinaya (x3) |
| Ayaan Haris | MKS00092 | Beginner | G Beginner2 | 12 | 12 | Monday, Tuesday, Friday, Sunday | Abinaya, Dhaanush, Guru | Monday 7:00 PM — Dhaanush (x4); Tuesday 7:00 PM — Dhaanush (x1); Friday 6:00 PM — Guru (x1); Friday 7:00 PM — Dhaanush (x3); Sunday 10:00 AM — Abinaya (x3) |
| D. Tharun | MKS00127 | Beginner | G Beginner2 | 12 | 12 | Monday, Tuesday, Friday, Sunday | Abinaya, Dhaanush, Guru, Hema | Monday 7:00 PM — Dhaanush (x4); Tuesday 7:00 PM — Dhaanush (x1); Friday 6:00 PM — Guru (x1); Friday 7:00 PM — Dhaanush (x3); Sunday 10:00 AM — Abinaya (x2); Sunday 11:00 AM — Hema (x1) |
| Nakshathra. C | MKS00227 | Beginner | G Beginner2 | 10 | 10 | Monday, Tuesday, Friday, Sunday | Abinaya, Dhaanush | Monday 7:00 PM — Dhaanush (x4); Tuesday 7:00 PM — Dhaanush (x1); Friday 7:00 PM — Dhaanush (x3); Sunday 10:00 AM — Abinaya (x2) |
| B SARVESSH | MKS00108 | Beginner | G Beginner2 | 12 | 12 | Monday, Tuesday, Friday, Sunday | Abinaya, Dhaanush, Guru, Hema | Monday 7:00 PM — Dhaanush (x4); Tuesday 7:00 PM — Dhaanush (x1); Friday 6:00 PM — Guru (x1); Friday 7:00 PM — Dhaanush (x3); Sunday 10:00 AM — Abinaya (x1); Sunday 11:00 AM — Abinaya (x1); Sunday 11:00 AM — Hema (x1) |
| Abhijay | MKS00202 | Beginner | G Beginner2 | 13 | 12 | Monday, Tuesday, Friday, Saturday, Sunday | Abinaya, Bathri, Dhaanush, Guru | Monday 7:00 PM — Dhaanush (x3); Monday 8:00 PM — Dhaanush (x1); Tuesday 7:00 PM — Dhaanush (x1); Friday 7:00 PM — Dhaanush (x3); Saturday 8:00 PM — Bathri (x1); Sunday 10:00 AM — Abinaya (x2); Sunday 11:00 AM — Guru (x1) |
| KAVIBHARATHI P | MKS00201 | Early Intermediate | G Early Intermediate1 | 12 | 11 | Monday, Friday, Sunday | Abinaya, Dhaanush | Monday 8:00 PM — Dhaanush (x4); Friday 8:00 PM — Dhaanush (x4); Sunday 10:00 AM — Abinaya (x3) |
| V.Pranav | MKS00173 | Early Intermediate | G Early Intermediate1 | 12 | 11 | Monday, Friday, Sunday | Abinaya, Dhaanush | Monday 8:00 PM — Dhaanush (x4); Friday 8:00 PM — Dhaanush (x4); Sunday 10:00 AM — Abinaya (x3) |
| Pranith | MKS00143 | Early Intermediate | G Early Intermediate1 | 12 | 11 | Monday, Friday, Sunday | Abinaya, Dhaanush, Manikandan | Monday 8:00 PM — Dhaanush (x4); Friday 8:00 PM — Dhaanush (x4); Sunday 10:00 AM — Abinaya (x2); Sunday 10:00 AM — Manikandan (x1) |
| Kavinpriyan | MKS00023 | Early Intermediate | G Early Intermediate1 | 12 | 11 | Monday, Friday, Sunday | Abinaya, Dhaanush | Monday 8:00 PM — Dhaanush (x4); Friday 8:00 PM — Dhaanush (x4); Sunday 10:00 AM — Abinaya (x3) |
| K. Sudhir | MKS00228 | Early Intermediate | G Early Intermediate1 | 9 | 7 | Monday, Friday, Sunday | Abinaya, Dhaanush | Monday 8:00 PM — Dhaanush (x2); Friday 8:00 PM — Dhaanush (x3); Sunday 10:00 AM — Abinaya (x2) |
| M Nethran | MKS00020 | Early Intermediate | G Early Intermediate1 | 12 | 11 | Monday, Friday, Sunday | Dhaanush, Hema, Manikandan, Prakash | Monday 8:00 PM — Dhaanush (x4); Friday 8:00 PM — Dhaanush (x4); Sunday 11:00 AM — Hema (x1); Sunday 11:00 AM — Manikandan (x1); Sunday 11:00 AM — Prakash (x1) |
| Keshav Krishna | YTC | Beginner | G Early Intermediate1 | 12 | 11 | Monday, Friday, Sunday | Dhaanush, Hema, Manikandan, Prakash | Monday 8:00 PM — Dhaanush (x4); Friday 8:00 PM — Dhaanush (x4); Sunday 11:00 AM — Hema (x1); Sunday 11:00 AM — Manikandan (x1); Sunday 11:00 AM — Prakash (x1) |
| Samuel Rajan | MKS00182 | Early Intermediate | G Intermediate1 | 12 | 12 | Tuesday, Wednesday, Friday | Dhaanush, Prakash, Saravanan | Tuesday 8:00 PM — Dhaanush (x4); Tuesday 8:00 PM — Prakash (x1); Wednesday 7:00 PM — Saravanan (x5); Friday 8:00 PM — Dhaanush (x2) |
| S Mounitha | MKS00226 | Basic | G Beginner2 | 11 | 11 | Monday, Tuesday, Wednesday, Friday, Saturday | Manikandan | Monday 7:00 PM — Manikandan (x2); Tuesday 7:00 PM — Manikandan (x2); Wednesday 7:00 PM — Manikandan (x3); Friday 6:00 PM — Manikandan (x1); Friday 7:00 PM — Manikandan (x2); Saturday 7:00 PM — Manikandan (x1) |
| M VARUNESH PANDI | MKS00166 | Beginner | L Beginner1 | 12 | 13 | Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday | Abinaya, Bathri, Guru, Manikandan, Prakash | Monday 8:00 PM — Manikandan (x1); Tuesday 8:00 PM — Bathri (x1); Tuesday 8:00 PM — Manikandan (x1); Tuesday 8:00 PM — Prakash (x1); Wednesday 8:00 PM — Manikandan (x1); Thursday 8:00 PM — Prakash (x2); Friday 8:00 PM — Guru (x1); Friday 8:00 PM — Manikandan (x1); Saturday 8:00 PM — Manikandan (x1); Sunday 11:00 AM — Guru (x1); Sunday 1:30 PM — Abinaya (x2) |
| Dev dharsan | MKS00142 | Beginner | L Beginner1 | 12 | 14 | Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday | Abinaya, Guru, Manikandan, Prakash | Monday 8:00 PM — Manikandan (x1); Tuesday 8:00 PM — Manikandan (x1); Tuesday 8:00 PM — Prakash (x1); Wednesday 7:00 PM — Prakash (x1); Wednesday 8:00 PM — Manikandan (x1); Thursday 8:00 PM — Prakash (x2); Friday 8:00 PM — Guru (x1); Friday 8:00 PM — Manikandan (x2); Saturday 8:00 PM — Manikandan (x1); Sunday 11:00 AM — Abinaya (x1); Sunday 11:00 AM — Prakash (x1); Sunday 1:30 PM — Abinaya (x1) |
| Alagu Durai | MKS00141 | Beginner | I Beginner2 | 5 | 5 | Tuesday, Wednesday, Friday | Prakash | Tuesday 9:00 AM — Prakash (x2); Wednesday 9:00 AM — Prakash (x1); Friday 9:00 AM — Prakash (x2) |
| Syed Individual | MKS00076 | Beginner | I Beginner1 | 10 | 12 | Tuesday, Thursday, Friday, Saturday | Bathri, Prakash | Tuesday 6:00 PM — Bathri (x1); Tuesday 7:00 PM — Bathri (x4); Thursday 7:00 PM — Bathri (x1); Friday 8:00 PM — Bathri (x1); Friday 8:00 PM — Prakash (x2); Saturday 7:00 PM — Bathri (x2); Saturday 7:00 PM — Prakash (x1) |
| J Jerwin | MKS00230 | Basic | G Basic2 | — | 8 | Monday, Tuesday, Thursday, Friday, Sunday | Abinaya, Bathri, Manikandan, Prakash | Monday 7:00 PM — Manikandan (x2); Tuesday 8:00 PM — Bathri (x2); Thursday 7:00 PM — Manikandan (x1); Thursday 8:00 PM — Abinaya (x1); Friday 8:00 PM — Manikandan (x1); Sunday 11:00 AM — Prakash (x1) |
| Sri Varshini | MKS00232 | Basic | G Basic1 | — | 5 | Tuesday, Thursday, Saturday | Manikandan | Tuesday 7:00 PM — Manikandan (x1); Thursday 8:00 PM — Manikandan (x2); Saturday 7:00 PM — Manikandan (x2) |
| Aaradheya P | MKS00225 | Basic | G Basic1 | — | 6 | Monday, Tuesday, Thursday, Saturday | Manikandan, Prakash | Monday 7:00 PM — Prakash (x1); Tuesday 7:00 PM — Manikandan (x1); Thursday 8:00 PM — Manikandan (x1); Saturday 7:00 PM — Manikandan (x2); Saturday 8:00 PM — Manikandan (x1) |
| Kavinth P | MKS00217 | Basic | G Beginner1 | 12 | 13 | Monday, Wednesday, Friday, Saturday, Sunday | Abinaya, Manikandan | Monday 8:00 PM — Abinaya (x3); Monday 8:00 PM — Manikandan (x1); Wednesday 8:00 PM — Abinaya (x4); Friday 8:00 PM — Manikandan (x1); Saturday 7:00 PM — Manikandan (x1); Sunday 11:00 AM — Abinaya (x3) |
| Thenamilthan.S | MKS00200 | Basic | G Beginner1 | 12 | 12 | Monday, Tuesday, Wednesday, Thursday, Sunday | Abinaya | Monday 8:00 PM — Abinaya (x4); Tuesday 8:00 PM — Abinaya (x1); Wednesday 8:00 PM — Abinaya (x3); Thursday 8:00 PM — Abinaya (x1); Sunday 11:00 AM — Abinaya (x3) |
| S.Kavirenu | MKS00199 | Basic | G Beginner1 | 12 | 12 | Monday, Tuesday, Wednesday, Thursday, Sunday | Abinaya | Monday 8:00 PM — Abinaya (x4); Tuesday 8:00 PM — Abinaya (x1); Wednesday 8:00 PM — Abinaya (x3); Thursday 8:00 PM — Abinaya (x1); Sunday 11:00 AM — Abinaya (x3) |
| S.Kabilan | MKS00198 | Basic | G Beginner1 | 12 | 12 | Monday, Tuesday, Wednesday, Thursday, Sunday | Abinaya | Monday 8:00 PM — Abinaya (x4); Tuesday 8:00 PM — Abinaya (x1); Wednesday 8:00 PM — Abinaya (x3); Thursday 8:00 PM — Abinaya (x1); Sunday 11:00 AM — Abinaya (x3) |
| M.Srisaran | MKS00186 | Basic | G Beginner1 | 12 | 12 | Monday, Tuesday, Wednesday, Sunday | Abinaya, Prakash | Monday 8:00 PM — Abinaya (x4); Tuesday 7:00 PM — Prakash (x1); Wednesday 7:00 PM — Abinaya (x1); Wednesday 8:00 PM — Abinaya (x3); Sunday 11:00 AM — Abinaya (x3) |
| Devansh gade | MKS00218 | Basic | I basic2 | 8 | 9 | Monday, Wednesday | Bathri, Prakash | Monday 4:30 PM — Bathri (x4); Wednesday 4:30 PM — Bathri (x3); Wednesday 4:30 PM — Prakash (x2) |
| Vikaesh | MKS00221 | Beginner | I Beginner1 | 12 | 12 | Monday, Wednesday, Thursday, Friday, Sunday | Bathri, bathri | Monday 6:00 PM — Bathri (x4); Wednesday 6:00 PM — Bathri (x2); Wednesday 8:00 PM — Bathri (x1); Thursday 11:15 AM — bathri (x1); Friday 7:00 PM — Bathri (x1); Sunday 11:00 AM — Bathri (x1); Sunday 9:00 AM — Bathri (x2) |
| Vivaan Aaditya | MKS00053 | Intermediate | L Intermediate2 | 12 | 16 | Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday | Arshath, Dhaanush, Prakash | Monday 6:00 PM — Dhaanush (x3); Tuesday 6:00 PM — Dhaanush (x1); Tuesday 8:00 PM — Dhaanush (x2); Tuesday 8:00 PM — Prakash (x1); Wednesday 6:00 PM — Dhaanush (x2); Thursday 6:00 PM — Dhaanush (x1); Friday 5:30 PM — Arshath (x1); Saturday 5:00 PM — Arshath (x2); Saturday 6:00 PM — Arshath (x1); Sunday 10:00 AM — Arshath (x2) |
| Hithesh | MKS00206 | Early Intermediate | G Early Intermediate2 | 12 | 12 | Monday, Wednesday, Saturday, Sunday | Dhaanush, Hema, Manikandan | Monday 8:00 PM — Dhaanush (x1); Wednesday 7:00 PM — Dhaanush (x4); Saturday 7:00 PM — Dhaanush (x4); Sunday 10:00 AM — Hema (x2); Sunday 10:00 AM — Manikandan (x1) |
| Ryan Stalin | MKS00007 | Beginner | G Beginner2s | 12 | 12 | Monday, Friday, Saturday, Sunday | Bathri, Guru, Prakash | Monday 3:00 PM — Bathri (x1); Monday 8:00 PM — Guru (x2); Friday 8:00 PM — Bathri (x3); Saturday 8:00 PM — Guru (x3); Sunday 11:00 AM — Guru (x2); Sunday 11:00 AM — Prakash (x1) |
| D KAVISH | MKS00079 | Beginner | G Beginner1A | 12 | 12 | Monday, Wednesday, Saturday, Sunday | Abinaya, Guru, bathri | Monday 8:00 PM — Guru (x4); Wednesday 8:00 PM — bathri (x1); Saturday 8:00 PM — Guru (x4); Sunday 10:00 AM — Abinaya (x1); Sunday 11:00 AM — Guru (x2) |
| V. Srikaviyazhini | MKS00131 | Beginner | G Beginner1A | 12 | 11 | Monday, Saturday, Sunday | Guru, Hema | Monday 8:00 PM — Guru (x4); Saturday 8:00 PM — Guru (x4); Sunday 11:00 AM — Guru (x2); Sunday 11:00 AM — Hema (x1) |
| M.Nalini Hirthika | MKS00118 | Beginner | G Beginner1A | 12 | 12 | Monday, Wednesday, Saturday, Sunday | Guru, bathri | Monday 8:00 PM — Guru (x4); Wednesday 8:00 PM — bathri (x1); Saturday 8:00 PM — Guru (x4); Sunday 11:00 AM — Guru (x3) |
| Dhanya   sri S S | MKS00114 | Beginner | G Beginner1A | 12 | 12 | Monday, Wednesday, Saturday, Sunday | Guru, bathri | Monday 8:00 PM — Guru (x4); Wednesday 8:00 PM — bathri (x1); Saturday 8:00 PM — Guru (x4); Sunday 11:00 AM — Guru (x3) |
| Nirupan | MKS00185 | Beginner | G Beginner1B | 12 | 11 | Monday, Friday, Saturday, Sunday | Bathri, Guru | Monday 8:00 PM — Guru (x4); Friday 8:00 PM — Bathri (x1); Saturday 8:00 PM — Guru (x3); Sunday 11:00 AM — Guru (x3) |
| R Logeshwaran | MKS00222 | Beginner | G beginner1 | 12 | 12 | Monday, Tuesday, Thursday, Sunday | Bathri, Guru, Manikandan, Prakash, hema | Monday 12:00 PM — Bathri (x1); Monday 7:00 PM — Bathri (x1); Monday 7:00 PM — Prakash (x1); Tuesday 8:00 PM — Bathri (x2); Thursday 7:00 PM — Manikandan (x3); Thursday 8:00 PM — Manikandan (x1); Sunday 11:00 AM — Guru (x2); Sunday 11:00 AM — hema (x1) |
| Jeevith. N.M | MKS00224 | Basic | G Basic2 | 10 | 10 | Monday, Tuesday, Thursday | Bathri, Manikandan, Prakash | Monday 12:00 PM — Bathri (x1); Monday 7:00 PM — Bathri (x1); Monday 7:00 PM — Manikandan (x1); Monday 7:00 PM — Prakash (x1); Tuesday 8:00 PM — Bathri (x3); Thursday 7:00 PM — Manikandan (x3) |
| Bhavadharani.B | MKS00203 | Basic | G Beginner1 | 13 | 13 | Monday, Tuesday, Thursday, Friday, Saturday, Sunday | Abinaya, Bathri, Manikandan, Prakash | Monday 12:00 PM — Bathri (x1); Monday 7:00 PM — Bathri (x1); Monday 7:00 PM — Prakash (x1); Tuesday 7:00 PM — Abinaya (x1); Tuesday 8:00 PM — Bathri (x1); Thursday 7:00 PM — Abinaya (x1); Thursday 7:00 PM — Manikandan (x2); Friday 8:00 PM — Manikandan (x1); Saturday 7:00 PM — Manikandan (x1); Sunday 11:00 AM — Abinaya (x3) |
| Rooban | MKS00215 | Basic | G beginner1 | 12 | 13 | Monday, Tuesday, Thursday, Saturday, Sunday | Abinaya, Bathri, Guru, Prakash | Monday 6:00 PM — Prakash (x4); Tuesday 6:00 PM — Prakash (x1); Thursday 6:00 PM — Prakash (x1); Saturday 6:00 PM — Bathri (x1); Saturday 6:00 PM — Prakash (x3); Sunday 11:00 AM — Abinaya (x2); Sunday 11:00 AM — Guru (x1) |
| Mithra sree A | MKS00161 | Beginner | G Beginner1 | 12 | 13 | Monday, Tuesday, Thursday, Saturday, Sunday | Bathri, Guru, Hema, Prakash | Monday 6:00 PM — Prakash (x4); Tuesday 6:00 PM — Prakash (x1); Thursday 6:00 PM — Prakash (x1); Saturday 6:00 PM — Bathri (x1); Saturday 6:00 PM — Prakash (x3); Sunday 11:00 AM — Guru (x1); Sunday 11:00 AM — Hema (x1); Sunday 11:00 AM — Prakash (x1) |
| Mithun Rajamani chakravarthi | MKS00112 | Beginner | G Beginner1 | 12 | 13 | Monday, Tuesday, Thursday, Saturday, Sunday | Bathri, Guru, Hema, Prakash | Monday 6:00 PM — Prakash (x4); Tuesday 6:00 PM — Prakash (x1); Thursday 6:00 PM — Prakash (x1); Saturday 6:00 PM — Bathri (x1); Saturday 6:00 PM — Prakash (x3); Sunday 11:00 AM — Guru (x1); Sunday 11:00 AM — Hema (x1); Sunday 11:00 AM — Prakash (x1) |
| Charvi | MKS00163 | Beginner | G Beginner1 | 12 | 12 | Monday, Thursday, Saturday, Sunday | Bathri, Guru, Prakash | Monday 6:00 PM — Prakash (x4); Thursday 6:00 PM — Prakash (x1); Saturday 6:00 PM — Bathri (x1); Saturday 6:00 PM — Prakash (x3); Sunday 11:00 AM — Guru (x2); Sunday 11:00 AM — Prakash (x1) |
| M. R. Darshan | MKS00101 | Beginner | G Beginner1 | 12 | 12 | Monday, Thursday, Saturday, Sunday | Bathri, Guru, Prakash | Monday 6:00 PM — Prakash (x4); Thursday 6:00 PM — Prakash (x1); Saturday 6:00 PM — Bathri (x1); Saturday 6:00 PM — Prakash (x3); Sunday 11:00 AM — Guru (x2); Sunday 11:00 AM — Prakash (x1) |
| Nitharsana | MKS00095 | Beginner | G Beginner1 | 12 | 12 | Monday, Thursday, Saturday, Sunday | Bathri, Guru, Prakash | Monday 6:00 PM — Prakash (x4); Thursday 6:00 PM — Prakash (x1); Saturday 6:00 PM — Bathri (x1); Saturday 6:00 PM — Prakash (x3); Sunday 11:00 AM — Guru (x2); Sunday 11:00 AM — Prakash (x1) |
| A.T.Vagish | MKS00149 | Beginner | G Beginner1 | 12 | 11 | Monday, Thursday, Saturday, Sunday | Bathri, Guru, Prakash | Monday 6:00 PM — Prakash (x4); Thursday 6:00 PM — Prakash (x1); Saturday 6:00 PM — Bathri (x1); Saturday 6:00 PM — Prakash (x3); Sunday 11:00 AM — Guru (x2) |
| Oviya B | MKS00038 | Beginner | G Beginner2s | 12 | 14 | Monday, Wednesday, Thursday, Friday, Saturday, Sunday | Bathri, Guru, Hema, Prakash | Monday 3:00 PM — Bathri (x1); Monday 6:00 PM — Prakash (x2); Wednesday 7:00 PM — Prakash (x1); Thursday 6:00 PM — Bathri (x1); Thursday 6:00 PM — Prakash (x1); Friday 8:00 PM — Bathri (x3); Saturday 6:00 PM — Prakash (x2); Saturday 8:00 PM — Guru (x1); Sunday 11:00 AM — Hema (x1); Sunday 11:00 AM — Prakash (x1) |
| N.sri dharshni | MKS00055 | Beginner | L Beginner2 | 12 | 10 | Monday, Tuesday, Wednesday, Thursday, Sunday | Abinaya, Bathri, Dhaanush, Prakash, prakash | Monday 7:00 PM — Prakash (x2); Tuesday 7:00 PM — Dhaanush (x1); Tuesday 7:00 PM — Prakash (x1); Wednesday 7:00 PM — Prakash (x2); Thursday 7:00 PM — Bathri (x1); Thursday 8:00 PM — prakash (x1); Sunday 1:30 PM — Abinaya (x1); Sunday 1:30 PM — prakash (x1) |
| Harini | MKS00073 | Beginner | G Beginner2 | 12 | 12 | Monday, Tuesday, Thursday, Friday, Sunday | Bathri, Guru, Hema, Prakash, manikandan | Monday 3:00 PM — Bathri (x1); Monday 6:00 PM — Prakash (x2); Tuesday 6:00 PM — Bathri (x2); Tuesday 6:00 PM — Prakash (x1); Thursday 6:00 PM — Bathri (x2); Friday 6:00 PM — Guru (x1); Sunday 11:00 AM — Hema (x1); Sunday 11:00 AM — Prakash (x1); Sunday 11:00 AM — manikandan (x1) |
| Aadhav Mithun | MKS00170 | Basic | I Basic2 | 5 | 5 | Saturday, Sunday | Abinaya | Saturday 10:00 AM — Abinaya (x3); Saturday 5:00 PM — Abinaya (x1); Sunday 10:00 AM — Abinaya (x1) |
| Sudharshika | MKS00216 | Basic | G Basic2 | 12 | 12 | Tuesday, Friday, Saturday, Sunday | Abinaya | Tuesday 7:00 PM — Abinaya (x4); Friday 8:00 PM — Abinaya (x1); Saturday 7:00 PM — Abinaya (x4); Sunday 11:00 AM — Abinaya (x3) |
| B.SAI SRI | MKS00211 | Basic | G Basic2 | 12 | 12 | Tuesday, Friday, Saturday, Sunday | Abinaya | Tuesday 7:00 PM — Abinaya (x4); Friday 8:00 PM — Abinaya (x1); Saturday 7:00 PM — Abinaya (x4); Sunday 11:00 AM — Abinaya (x3) |
| Adhigan Amarnath | MKS00204 | Basic | L Basic2 | 12 | 12 | Tuesday, Friday, Saturday, Sunday | Abinaya | Tuesday 7:00 PM — Abinaya (x4); Friday 8:00 PM — Abinaya (x1); Saturday 7:00 PM — Abinaya (x4); Sunday 11:00 AM — Abinaya (x3) |
| Pugazhini Navaneethan | MKS00156 | Beginner | I Beginner1 | 9 | 9 | Tuesday, Saturday | Bathri | Tuesday 6:00 AM — Bathri (x5); Saturday 6:00 AM — Bathri (x4) |
| Akshadhasree | MKS00067 | Beginner | L Beginner1B | 8 | 8 | Monday, Saturday, Sunday | Bathri, Hema, Manikandan, Prakash | Monday 6:00 PM — Prakash (x1); Saturday 11:00 AM — Bathri (x4); Sunday 11:00 AM — Hema (x1); Sunday 11:00 AM — Manikandan (x1); Sunday 11:00 AM — Prakash (x1) |
| Anikha | MKS00066 | Beginner | L Beginner1B | 8 | 8 | Monday, Saturday, Sunday | Abinaya, Bathri, Hema, Manikandan, Prakash | Monday 6:00 PM — Prakash (x1); Saturday 11:00 AM — Bathri (x4); Sunday 11:00 AM — Hema (x1); Sunday 11:00 AM — Manikandan (x1); Sunday 1:30 PM — Abinaya (x1) |
| T L KANISHKAR | MKS00195 | Basic | I Basic2 | 4 | 4 | Saturday | Bathri | Saturday 6:00 PM — Bathri (x4) |
| Nishwanth R | MKS00171 | Beginner | G beginner1 | 9 | 9 | Tuesday, Thursday, Saturday | Bathri | Tuesday 8:00 PM — Bathri (x3); Thursday 8:00 PM — Bathri (x4); Saturday 8:00 PM — Bathri (x2) |
| C S Sharwin | MKS00197 | Beginner | G Beginner1B | 13 | 12 | Monday, Tuesday, Thursday, Saturday, Sunday | Bathri, Hema, Prakash | Monday 6:00 PM — Prakash (x1); Tuesday 8:00 PM — Bathri (x3); Thursday 8:00 PM — Bathri (x3); Saturday 6:00 PM — Prakash (x1); Saturday 8:00 PM — Bathri (x3); Sunday 11:00 AM — Hema (x1) |
| Ridhanya Sri.V | MKS00178 | Beginner | G beginner1 | 12 | 12 | Tuesday, Thursday, Saturday | Bathri | Tuesday 8:00 PM — Bathri (x4); Thursday 8:00 PM — Bathri (x4); Saturday 8:00 PM — Bathri (x4) |
| Vaishnavi Krishna | MKS00165 | Beginner | L Beginner1 | 8 | 8 | Wednesday, Saturday | Bathri, Prakash | Wednesday 6:00 AM — Bathri (x4); Wednesday 6:00 AM — Prakash (x1); Saturday 9:00 PM — Bathri (x3) |
| Vaibhavi Krishna | MKS00164 | Beginner | L Beginner1 | 8 | 8 | Wednesday, Saturday | Bathri, Prakash | Wednesday 6:00 AM — Bathri (x4); Wednesday 6:00 AM — Prakash (x1); Saturday 9:00 PM — Bathri (x3) |
| Manikandan S | MKS00183 | Early Intermediate | G Early Intermediate1 | 15 | 16 | Monday, Tuesday, Wednesday, Saturday, Sunday | Abinaya, Arshath, Dhaanush, Prakash | Monday 2:00 PM — Arshath (x1); Tuesday 8:00 PM — Dhaanush (x4); Tuesday 8:00 PM — Prakash (x1); Wednesday 7:00 PM — Dhaanush (x5); Saturday 5:00 PM — Dhaanush (x4); Sunday 10:00 AM — Abinaya (x1) |
| Avyukt A Praveen | MKS00174 | Beginner | G Beginner2A | 8 | 7 | Saturday, Sunday | Dhaanush, Hema, Manikandan, Prakash | Saturday 5:00 PM — Dhaanush (x4); Sunday 11:00 AM — Hema (x1); Sunday 11:00 AM — Manikandan (x1); Sunday 11:00 AM — Prakash (x1) |
| Thivya | MKS00056 | Early Intermediate | L Early Intermediate2 | 12 | 13 | Tuesday, Friday, Saturday, Sunday | Dhaanush, Prakash | Tuesday 6:00 PM — Dhaanush (x4); Friday 6:00 PM — Dhaanush (x2); Saturday 6:00 PM — Dhaanush (x4); Sunday 10:00 AM — Dhaanush (x2); Sunday 10:00 AM — Prakash (x1) |
| Reyhan nawaz | MKS00049 | Early Intermediate | L Early Intermediate2 | 12 | 12 | Tuesday, Saturday, Sunday | Dhaanush, Prakash | Tuesday 6:00 PM — Dhaanush (x5); Saturday 6:00 PM — Dhaanush (x4); Sunday 10:00 AM — Dhaanush (x2); Sunday 10:00 AM — Prakash (x1) |
| S R Sabeshwar | MKS00223 | Early Intermediate | G Early Intermediate1 | 12 | 12 | Tuesday, Wednesday, Friday, Saturday, Sunday | Abinaya, Dhaanush, Prakash | Tuesday 8:00 PM — Dhaanush (x1); Tuesday 8:00 PM — Prakash (x1); Wednesday 7:00 PM — Dhaanush (x3); Friday 8:00 PM — Dhaanush (x2); Saturday 7:00 PM — Dhaanush (x3); Sunday 10:00 AM — Abinaya (x2) |
| S.Raagavarshenee | MKS00009 | Early Intermediate | G Early Intermediate2 | 12 | 12 | Wednesday, Saturday, Sunday | Abinaya, Dhaanush | Wednesday 7:00 PM — Dhaanush (x5); Saturday 7:00 PM — Dhaanush (x4); Sunday 10:00 AM — Abinaya (x3) |
| Praduksha | MKS00091 | Early Intermediate | G Early Intermediate2 | 12 | 12 | Wednesday, Saturday, Sunday | Dhaanush, Hema, Manikandan | Wednesday 7:00 PM — Dhaanush (x5); Saturday 7:00 PM — Dhaanush (x4); Sunday 10:00 AM — Hema (x2); Sunday 10:00 AM — Manikandan (x1) |
| Arishmithran | MKS00072 | Early Intermediate | G Early Intermediate2 | 12 | 12 | Wednesday, Saturday, Sunday | Dhaanush, Hema, Manikandan | Wednesday 7:00 PM — Dhaanush (x5); Saturday 7:00 PM — Dhaanush (x4); Sunday 10:00 AM — Hema (x2); Sunday 10:00 AM — Manikandan (x1) |
| Sanjumithra | MKS00070 | Early Intermediate | G Early Intermediate2 | 12 | 12 | Wednesday, Saturday, Sunday | Dhaanush, Hema, Manikandan | Wednesday 7:00 PM — Dhaanush (x5); Saturday 7:00 PM — Dhaanush (x4); Sunday 10:00 AM — Hema (x2); Sunday 10:00 AM — Manikandan (x1) |
| Shakthivishakan A | MKS00034 | Early Intermediate | G Early Intermediate2 | 12 | 12 | Wednesday, Saturday, Sunday | Dhaanush, Hema, Manikandan | Wednesday 7:00 PM — Dhaanush (x5); Saturday 7:00 PM — Dhaanush (x4); Sunday 10:00 AM — Hema (x2); Sunday 10:00 AM — Manikandan (x1) |
| Mohhan | MKS00064 | Early Intermediate | G Early Intermediate2 | 8 | 9 | Wednesday, Saturday, Sunday | Dhaanush, Hema, Manikandan | Wednesday 7:00 PM — Dhaanush (x4); Saturday 7:00 PM — Dhaanush (x3); Sunday 10:00 AM — Hema (x1); Sunday 10:00 AM — Manikandan (x1) |
| S. YASWANNTH | MKS00039 | Beginner | G Beginner1s | 8 | 7 | Friday, Saturday | Bathri, Guru | Friday 8:00 PM — Bathri (x3); Saturday 8:00 PM — Guru (x4) |
| Kirthik | MKS00048 | Beginner | I Beginner2 | 10 | 11 | Tuesday, Thursday, Saturday | Bathri, Prakash | Tuesday 6:00 AM — Bathri (x1); Tuesday 6:00 AM — Prakash (x4); Thursday 6:00 AM — Prakash (x2); Saturday 6:00 AM — Prakash (x4) |
| Ineya Individual | MKS00050 | Early Intermediate | I Intermediate | 4 | 4 | Saturday | Prakash | Saturday 7:00 PM — Prakash (x4) |
| Madesh | MKS00194 | Beginner | L Beginner1 | 15 | 15 | Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday | Abinaya, Dhaanush, Hema, Prakash | Tuesday 7:00 PM — Prakash (x3); Wednesday 8:00 PM — Prakash (x1); Thursday 7:00 PM — Dhaanush (x1); Thursday 7:00 PM — Prakash (x2); Friday 8:00 PM — Prakash (x1); Saturday 8:00 PM — Dhaanush (x1); Saturday 8:00 PM — Prakash (x3); Sunday 10:00 AM — Abinaya (x2); Sunday 11:00 AM — Hema (x1) |
| B.AARAV NARAYAN | MKS00098 | Early Intermediate | L Early Intermediate1 | 12 | 13 | Tuesday, Thursday, Saturday, Sunday | Abinaya, Dhaanush, Hema, Prakash | Tuesday 7:00 PM — Dhaanush (x1); Tuesday 7:00 PM — Prakash (x3); Thursday 7:00 PM — Dhaanush (x1); Thursday 7:00 PM — Prakash (x2); Saturday 8:00 PM — Prakash (x3); Sunday 10:00 AM — Abinaya (x2); Sunday 11:00 AM — Hema (x1) |
| M.Nishik | MKS00113 | Early Intermediate | G Intermediate1 | 12 | 13 | Monday, Wednesday, Saturday, Sunday | Arshath, Dhaanush, Prakash, Saravanan | Monday 2:00 PM — Arshath (x1); Wednesday 7:00 PM — Saravanan (x5); Saturday 7:00 PM — Saravanan (x4); Sunday 10:00 AM — Dhaanush (x2); Sunday 10:00 AM — Prakash (x1) |
| Hitesh prabu | MKS00014 | Early Intermediate | G Intermediate1 | 12 | 12 | Wednesday, Saturday, Sunday | Dhaanush, Hema, Manikandan, Saravanan | Wednesday 7:00 PM — Dhaanush (x1); Wednesday 7:00 PM — Saravanan (x4); Saturday 7:00 PM — Saravanan (x4); Sunday 10:00 AM — Hema (x2); Sunday 10:00 AM — Manikandan (x1) |
| Mithran P | MKS00083 | Early Intermediate | G Intermediate1 | 12 | 12 | Wednesday, Saturday, Sunday | Dhaanush, Prakash, Saravanan | Wednesday 7:00 PM — Saravanan (x5); Saturday 7:00 PM — Saravanan (x4); Sunday 10:00 AM — Dhaanush (x2); Sunday 10:00 AM — Prakash (x1) |
| Vedhanth V | MKS00102 | Early Intermediate | G Intermediate1 | 12 | 12 | Wednesday, Saturday, Sunday | Dhaanush, Prakash, Saravanan | Wednesday 7:00 PM — Saravanan (x5); Saturday 7:00 PM — Saravanan (x4); Sunday 10:00 AM — Dhaanush (x2); Sunday 10:00 AM — Prakash (x1) |
| Diya | MKS00024 | Early Intermediate | G Intermediate1 | 12 | 12 | Wednesday, Saturday, Sunday | Dhaanush, Prakash, Saravanan | Wednesday 7:00 PM — Saravanan (x5); Saturday 7:00 PM — Saravanan (x4); Sunday 10:00 AM — Dhaanush (x2); Sunday 10:00 AM — Prakash (x1) |
| Kamesh kumar c | MKS00231 | Intermediate | I Intermediate2 | 7 | 7 | Tuesday, Wednesday, Thursday, Sunday | Dhaanush | Tuesday 8:00 PM — Dhaanush (x2); Wednesday 8:00 PM — Dhaanush (x2); Thursday 8:00 PM — Dhaanush (x2); Sunday 9:00 AM — Dhaanush (x1) |
| Priyan | MKS00162 | Beginner | I Beginner1 | 8 | 8 | Wednesday, Friday | Manikandan, Prakash | Wednesday 6:00 AM — Manikandan (x4); Wednesday 6:00 AM — Prakash (x1); Friday 6:00 AM — Manikandan (x2); Friday 6:00 AM — Prakash (x1) |
| Jovinya | MKS00075 | Beginner | L Beginner1 | 12 | 12 | Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday | Abinaya, Bathri, Prakash, bathri, prakash | Tuesday 6:00 PM — Bathri (x2); Wednesday 5:00 PM — Prakash (x1); Wednesday 5:00 PM — bathri (x2); Thursday 8:00 PM — prakash (x1); Friday 6:00 PM — Bathri (x1); Saturday 7:00 PM — Bathri (x2); Sunday 1:30 PM — Abinaya (x2); Sunday 1:30 PM — prakash (x1) |
| S.V.Kavisree | MKS00111 | Beginner | L Beginner1 | 12 | 12 | Tuesday, Wednesday, Friday, Saturday, Sunday | Abinaya, Bathri, Guru, Prakash, bathri | Tuesday 6:00 PM — Bathri (x2); Wednesday 5:00 PM — Prakash (x1); Wednesday 5:00 PM — bathri (x2); Friday 6:00 PM — Bathri (x1); Saturday 6:00 PM — Prakash (x1); Saturday 7:00 PM — Bathri (x2); Sunday 11:00 AM — Guru (x1); Sunday 1:30 PM — Abinaya (x2) |
| Kaashvi Prakash | MKS00184 | Basic | I Basic2 | 5 | 5 | Wednesday | Prakash | Wednesday 6:00 PM — Prakash (x4); Wednesday 7:00 PM — Prakash (x1) |
| Viraaj Shanmugam | MKS00153 | Basic | I Basic2 | 11 | 11 | Wednesday, Saturday, Sunday | Bathri, Guru | Wednesday 7:00 PM — Guru (x5); Saturday 12:15 PM — Bathri (x3); Sunday 11:00 AM — Bathri (x1); Sunday 9:00 AM — Guru (x2) |
| Sai Eswar | MKS00132 | Intermediate | I Intermediate2 | 18 | 17 | Tuesday, Wednesday, Thursday, Sunday | Dhaanush, Prakash | Tuesday 8:00 PM — Dhaanush (x4); Tuesday 8:00 PM — Prakash (x1); Wednesday 8:00 PM — Dhaanush (x5); Thursday 8:00 PM — Dhaanush (x4); Sunday 9:00 AM — Dhaanush (x3) |
| yaazhini | MKS00147 | Beginner | G Beginner1B | 12 | 11 | Monday, Tuesday, Thursday, Friday, Sunday | Bathri, Hema, Prakash, manikandan | Monday 3:00 PM — Bathri (x1); Tuesday 6:00 PM — Bathri (x2); Tuesday 6:00 PM — Prakash (x1); Thursday 6:00 PM — Bathri (x2); Thursday 8:00 PM — Bathri (x1); Friday 8:00 PM — Bathri (x1); Sunday 11:00 AM — Hema (x1); Sunday 11:00 AM — Prakash (x1); Sunday 11:00 AM — manikandan (x1) |
| MELWIN G | MKS00100 | Beginner | G Beginner2 | 12 | 12 | Monday, Tuesday, Thursday, Friday, Sunday | Bathri, Guru, Hema, Prakash, manikandan | Monday 3:00 PM — Bathri (x1); Tuesday 6:00 PM — Bathri (x2); Tuesday 6:00 PM — Prakash (x1); Thursday 6:00 PM — Bathri (x2); Friday 6:00 PM — Guru (x1); Friday 8:00 PM — Bathri (x2); Sunday 11:00 AM — Hema (x1); Sunday 11:00 AM — Prakash (x1); Sunday 11:00 AM — manikandan (x1) |
| N.Charan | MKS00148 | Beginner | G beginner1 | 12 | 12 | Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday | Abinaya, Bathri, Guru, Prakash, manikandan | Monday 3:00 PM — Bathri (x1); Tuesday 6:00 PM — Bathri (x1); Tuesday 6:00 PM — Prakash (x1); Wednesday 7:00 PM — Abinaya (x1); Thursday 6:00 PM — Bathri (x2); Friday 8:00 PM — Bathri (x1); Saturday 8:00 PM — Bathri (x1); Saturday 8:00 PM — Prakash (x1); Sunday 11:00 AM — Guru (x1); Sunday 11:00 AM — Prakash (x1); Sunday 11:00 AM — manikandan (x1) |
| Sarvesh K | MKS00175 | Beginner | G beginner1C | 12 | 12 | Tuesday, Thursday, Friday, Saturday, Sunday | Abinaya, Bathri, Hema, Prakash, manikandan | Tuesday 6:00 PM — Bathri (x2); Tuesday 6:00 PM — Prakash (x1); Thursday 6:00 PM — Bathri (x2); Thursday 8:00 PM — Bathri (x1); Friday 6:00 PM — Prakash (x1); Friday 8:00 PM — Bathri (x1); Saturday 8:00 PM — Bathri (x1); Sunday 11:00 AM — Abinaya (x1); Sunday 11:00 AM — Hema (x1); Sunday 11:00 AM — manikandan (x1) |
| Nyvan | MKS00208 | Basic | G Beginner1 | 12 | 12 | Tuesday, Thursday, Sunday | Abinaya | Tuesday 8:00 PM — Abinaya (x5); Thursday 8:00 PM — Abinaya (x4); Sunday 11:00 AM — Abinaya (x3) |
| Thiyashwar S | MKS00181 | Basic | G Beginner1 | 12 | 12 | Tuesday, Thursday, Sunday | Abinaya | Tuesday 8:00 PM — Abinaya (x5); Thursday 8:00 PM — Abinaya (x4); Sunday 11:00 AM — Abinaya (x3) |
| RITHIKNATH K.M | MKS00193 | Basic | G Beginner1 | 12 | 12 | Tuesday, Wednesday, Thursday, Sunday | Abinaya, Prakash | Tuesday 7:00 PM — Prakash (x1); Tuesday 8:00 PM — Abinaya (x4); Wednesday 7:00 PM — Abinaya (x1); Thursday 8:00 PM — Abinaya (x3); Sunday 11:00 AM — Abinaya (x3) |
| Cholamithran BR | MKS00192 | Basic | G Beginner1 | 12 | 12 | Tuesday, Wednesday, Thursday, Sunday | Abinaya, Prakash | Tuesday 7:00 PM — Prakash (x1); Tuesday 8:00 PM — Abinaya (x4); Wednesday 7:00 PM — Abinaya (x1); Thursday 8:00 PM — Abinaya (x3); Sunday 11:00 AM — Abinaya (x3) |
| BHAANAVI.V | MKS00189 | Basic | G Beginner1 | 12 | 12 | Tuesday, Wednesday, Thursday, Sunday | Abinaya, Prakash | Tuesday 7:00 PM — Prakash (x1); Tuesday 8:00 PM — Abinaya (x4); Wednesday 7:00 PM — Abinaya (x1); Thursday 8:00 PM — Abinaya (x3); Sunday 11:00 AM — Abinaya (x3) |
| Jayasudhan | MKS00220 | Basic | G Beginner1 | 12 | 13 | Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday | Abinaya, Manikandan | Monday 8:00 PM — Manikandan (x1); Tuesday 7:00 PM — Abinaya (x1); Tuesday 8:00 PM — Abinaya (x4); Wednesday 8:00 PM — Abinaya (x1); Thursday 8:00 PM — Abinaya (x3); Friday 8:00 PM — Manikandan (x1); Saturday 7:00 PM — Manikandan (x1); Sunday 11:00 AM — Abinaya (x1) |
| V.Dharmasastha Individual | MKS00093 | Early Intermediate | I Early Intermediate2 | 6 | 8 | Thursday, Friday, Sunday | Dhaanush, Prakash | Thursday 7:00 PM — Dhaanush (x4); Friday 7:00 PM — Dhaanush (x1); Sunday 10:00 AM — Dhaanush (x2); Sunday 10:00 AM — Prakash (x1) |
| AATHISH S | MKS00229 | Beginner | G Beginner1 | 1 | 1 | Wednesday | Bathri | Wednesday 7:00 AM — Bathri (x1) |

## 8. Important source-data note

The September workbook contains students who were assigned to more than one trainer during the month, and some students have more than one time/trainer variant on the same weekday. Therefore, a future scheduler must use the exact source slot patterns rather than assuming every student has one globally fixed trainer.

## 9. Recommended output structure

Create the next-month workbook in the same layout as the reference: metadata columns on the left, then one two-column date/trainer pair for every calendar day of the target month, followed by Comments. Maintain the existing style and formatting.

## 10. Agent instruction (copy/paste)

```text
You are the scheduling engine for the chess academy.
Use the latest approved monthly Excel workbook as the ONLY source of truth for students, batches, recurring attendance days, class times, trainer assignments, Planned Classes, and comments.

Generate the target month schedule by converting each student's reference-month recurring weekday pattern into the target month's actual calendar dates.
Do NOT copy dates by day-of-month.
Do NOT invent new students, times, trainers, batches, or attendance days.
Do NOT change a student's trainer unless an explicit authorized update exists.
Treat Planned Classes as a strict monthly maximum. Never exceed it.
If the natural recurrence would create more classes than Planned Classes, stop scheduling that student once the cap is reached.
If Planned Classes is blank, use the latest approved month's scheduled count as a fallback cap and flag the student for review.
If a student has multiple time/trainer variants on the same weekday in the reference, preserve the observed source pattern instead of collapsing it.

For reporting:
one group class = one unique Date + Start Time + Trainer combination.
The number of students inside that group does not increase the class count.

Before exporting, validate:
1) no student exceeds Planned Classes;
2) every scheduled weekday exists in that student's reference pattern;
3) every trainer/time assignment is supported by the source pattern;
4) daily Actual Classes equals unique Date + Time + Trainer groups;
5) no duplicate student assignment exists for the same exact slot;
6) workbook layout and formatting remain unchanged.

Then export the next-month workbook using the same structure and naming convention.
```


---

# PART B — OCTOBER 2026 REFERENCE DATA

The following section is the normalized data representation of the fresh October schedule. Use it as structured data when understanding the current schedule.

# October 2026 Chess Coaching Schedule — AI Reference

## Source

- Source workbook: `Oct'26 Schedule_FRESH.xlsx`
- Sheet: `Oct26`
- Month: October 2026
- Students: 127
- Individual student assignments: 1406
- Group classes: 414 (unique Date + Time + Trainer)

## Schedule rules represented by this file

- `Planned Classes` is the monthly maximum for the student.
- A scheduled entry contains a student, date, day, time, and trainer.
- For class/group reporting, students with the same date, start time, and trainer are one class group.
- Student-level rows preserve the schedule generated in the workbook; this Markdown does not invent or alter assignments.

## Trainer summary

| Trainer | Student Assignments | Group Classes |
|---|---:|---:|
| Bathri | 284 | 120 |
| Dhaanush | 338 | 87 |
| Prakash | 170 | 67 |
| Abinaya | 270 | 48 |
| Manikandan | 71 | 34 |
| Guru | 105 | 24 |
| Arshath | 65 | 18 |
| Hema | 61 | 8 |
| Saravanan | 42 | 8 |
| **TOTAL** | **1406** | **414** |

## Student master data

| Student | Stud ID | MKCA Rating | Level | Batch | Planned Classes | Comments |
|---|---|---:|---|---|---:|---|
| B.V.Tijesh | MKS00219 | 0.5 | Basic | G Basic1 | 12 |  |
| A.Bavinesh | MKS00214 | 0.6 | Basic | G Basic1 | 12 |  |
| C.V.Chanvika | MKS00196 | 0.7 | Basic | L Basic1 | 12 |  |
| Sachin | MKS00059 | 7.6 | Intermediate | L Intermediate2 | 12 |  |
| Selvakrishna RK | MKS00167 | 6.6 | Intermediate | G Intermediate2 | 12 |  |
| Srikavi Bharathi | MKS00045 | 7 | Intermediate | G Intermediate2 | 14 |  |
| Krishiv Ajay | MKS00037 | 7.5 | Intermediate | G Intermediate2 | 12 |  |
| YAASHVIN A/L SATEESHKUMAR | MKS00065 | 6.9 | Intermediate | G Intermediate2 | 10 |  |
| Sarvin | MKS00060 | 7.6 | Intermediate | G Intermediate2 | 10 |  |
| Vedh Pabba | MKS00190 | 2.9 | Beginner | I Beginner2 | 8 |  |
| Magizh | MKS00213 | 0.4 | Basic | I Basic1 | 8 |  |
| Harri mithran P | MKS00210 | 1.1 | Basic | I Basic2 | 9 |  |
| V. Dhaksha | MKS00110 | 3.4 | Beginner | I Beginner1 | 11 |  |
| HAASHINI  SHRIVY V | MKS00115 | 2.9 | Beginner | G beginner1 | 10 |  |
| H V Kanishk | MKS00154 | 2.8 | Beginner | G beginner1C | 12 |  |
| S. Thashwin Raj | MKS00155 | 2.6 | Beginner | G beginner1C | 13 |  |
| A R Thatchiraa Shree | MKS00172 | 2.8 | Beginner | G beginner1s | 12 | , 8pm only available |
| Vikash | MKS00168 | 2.8 | Beginner | G beginner1C | 12 |  |
| D R RAJAGOPALAN | MKS00176 | 3.9 | Beginner | G beginner1D | 12 |  |
| S.P.NEHASRI | MKS00157 | 1.8 | Basic | G Basic2A | 13 |  |
| P.V Subhiksha | MKS00150 | 3.3 | Beginner | I Beginner1 | 10 |  |
| Nithesh Nagarathinam | MKS00054 | 5.8 | Early Intermediate | L Early Intermediate1 | 24 |  |
| Rohith kumar.B | MKS00207 | 3.4 | beginner | G Beginner2 | 16 |  |
| V.D. THARUN ADITHYA | MKS00212 | 3.3 | Beginner | G beginner2 | 12 |  |
| Yuviga | MKS00107 | 4.2 | Beginner | G Beginner2 | 12 |  |
| Ayaan Haris | MKS00092 | 4.3 | Beginner | G Beginner2 | 12 |  |
| D. Tharun | MKS00127 | 4 | Beginner | G Beginner2 | 12 |  |
| Nakshathra. C | MKS00227 | 2.8 | Beginner | G Beginner2 | 10 |  |
| B SARVESSH | MKS00108 | 4.1 | Beginner | G Beginner2 | 12 |  |
| Abhijay | MKS00202 | 2.8 | Beginner | G Beginner2 | 13 |  |
| KAVIBHARATHI P | MKS00201 | 4.7 | Early Intermediate | G Early Intermediate1 | 12 |  |
| V.Pranav | MKS00173 | 3.5 | Early Intermediate | G Early Intermediate1 | 12 |  |
| Pranith | MKS00143 | 3.8 | Early Intermediate | G Early Intermediate1 | 12 |  |
| Kavinpriyan | MKS00023 | 4.8 | Early Intermediate | G Early Intermediate1 | 12 | Available only on tuesday, Thursday & saturday |
| K. Sudhir | MKS00228 | 3 | Early Intermediate | G Early Intermediate1 | 9 |  |
| M Nethran | MKS00020 | 3.8 | Early Intermediate | G Early Intermediate1 | 12 |  |
| Keshav Krishna | YTC | 3.3 | Beginner | G Early Intermediate1 | 12 |  |
| Samuel Rajan | MKS00182 | 5.6 | Early Intermediate | G Intermediate1 | 12 |  |
| S Mounitha | MKS00226 | 0.7 | Basic | G Beginner2 | 11 |  |
| M VARUNESH PANDI | MKS00166 | 3.1 | Beginner | L Beginner1 | 12 | Saturday work till 6 |
| Dev dharsan | MKS00142 | 2.6 | Beginner | L Beginner1 | 12 |  |
| Alagu Durai | MKS00141 | 4.8 | Beginner | I Beginner2 | 5 |  |
| Syed Individual | MKS00076 | 3.5 | Beginner | I Beginner1 | 10 |  |
| J Jerwin | MKS00230 | 1.8 | Basic | G Basic2 |  |  |
| Sri Varshini | MKS00232 | 0.2 | Basic | G Basic1 |  |  |
| Aaradheya P | MKS00225 | 0.2 | Basic | G Basic1 |  |  |
| Kavinth P | MKS00217 | 1.1 | Basic | G Beginner1 | 12 |  |
| Thenamilthan.S | MKS00200 | 1.8 | Basic | G Beginner1 | 12 |  |
| S.Kavirenu | MKS00199 | 1.8 | Basic | G Beginner1 | 12 |  |
| S.Kabilan | MKS00198 | 1.8 | Basic | G Beginner1 | 12 |  |
| M.Srisaran | MKS00186 | 2.2 | Basic | G Beginner1 | 12 |  |
| Devansh gade | MKS00218 | 0.7 | Basic | I basic2 | 8 |  |
| Vikaesh | MKS00221 | 2.1 | Beginner | I Beginner1 | 12 |  |
| Vivaan Aaditya | MKS00053 | 8 | Intermediate | L Intermediate2 | 12 | Monday to Thursday Hindi class from 7 to 7.45pm |
| Hithesh | MKS00206 | 4.8 | Early Intermediate | G Early Intermediate2 | 12 |  |
| Ryan Stalin | MKS00007 | 3.4 | Beginner | G Beginner2s | 12 |  |
| D KAVISH | MKS00079 | 4.2 | Beginner | G Beginner1A | 12 |  |
| V. Srikaviyazhini | MKS00131 | 3.2 | Beginner | G Beginner1A | 12 |  |
| M.Nalini Hirthika | MKS00118 | 3.4 | Beginner | G Beginner1A | 12 |  |
| Dhanya   sri S S | MKS00114 | 3.5 | Beginner | G Beginner1A | 12 | joined may |
| Nirupan | MKS00185 | 3 | Beginner | G Beginner1B | 12 |  |
| R Logeshwaran | MKS00222 | 1.8 | Beginner | G beginner1 | 12 |  |
| Jeevith. N.M | MKS00224 | 1.8 | Basic | G Basic2 | 10 |  |
| Bhavadharani.B | MKS00203 | 1.3 | Basic | G Beginner1 | 13 |  |
| Rooban | MKS00215 | 3 | Basic | G beginner1 | 12 |  |
| Mithra sree A | MKS00161 | 4 | Beginner | G Beginner1 | 12 |  |
| Mithun Rajamani chakravarthi | MKS00112 | 3.5 | Beginner | G Beginner1 | 12 |  |
| Charvi | MKS00163 | 3 | Beginner | G Beginner1 | 12 |  |
| M. R. Darshan | MKS00101 | 3.5 | Beginner | G Beginner1 | 12 | 1 makeup class to be given |
| Nitharsana | MKS00095 | 3.3 | Beginner | G Beginner1 | 12 |  |
| A.T.Vagish | MKS00149 | 2.8 | Beginner | G Beginner1 | 12 |  |
| Oviya B | MKS00038 | 3.2 | Beginner | G Beginner2s | 12 |  |
| N.sri dharshni | MKS00055 | 4.4 | Beginner | L Beginner2 | 12 | Sidharthh |
| Harini | MKS00073 | 2.8 | Beginner | G Beginner2 | 12 |  |
| Aadhav Mithun | MKS00170 | 1.1 | Basic | I Basic2 | 5 |  |
| Sudharshika | MKS00216 | 1.1 | Basic | G Basic2 | 12 |  |
| B.SAI SRI | MKS00211 | 1.1 | Basic | G Basic2 | 12 |  |
| Adhigan Amarnath | MKS00204 | 1.3 | Basic | L Basic2 | 12 |  |
| Pugazhini Navaneethan | MKS00156 | 3.2 | Beginner | I Beginner1 | 9 |  |
| Akshadhasree | MKS00067 | 3 | Beginner | L Beginner1B | 8 |  |
| Anikha | MKS00066 | 3.1 | Beginner | L Beginner1B | 8 |  |
| T L KANISHKAR | MKS00195 | 2.8 | Basic | I Basic2 | 4 |  |
| Nishwanth R | MKS00171 | 2.4 | Beginner | G beginner1 | 9 |  |
| C S Sharwin | MKS00197 | 2.4 | Beginner | G Beginner1B | 13 |  |
| Ridhanya Sri.V | MKS00178 | 2.4 | Beginner | G beginner1 | 12 |  |
| Vaishnavi Krishna | MKS00165 | 2.6 | Beginner | L Beginner1 | 8 |  |
| Vaibhavi Krishna | MKS00164 | 2.7 | Beginner | L Beginner1 | 8 |  |
| Manikandan S | MKS00183 | 4.5 | Early Intermediate | G Early Intermediate1 | 15 |  |
| Avyukt A Praveen | MKS00174 | 3.3 | Beginner | G Beginner2A | 8 |  |
| Thivya | MKS00056 | 6.2 | Early Intermediate | L Early Intermediate2 | 12 |  |
| Reyhan nawaz | MKS00049 | 5.6 | Early Intermediate | L Early Intermediate2 | 12 |  |
| S R Sabeshwar | MKS00223 | 4.5 | Early Intermediate | G Early Intermediate1 | 12 |  |
| S.Raagavarshenee | MKS00009 | 4.3 | Early Intermediate | G Early Intermediate2 | 12 |  |
| Praduksha | MKS00091 | 5.1 | Early Intermediate | G Early Intermediate2 | 12 |  |
| Arishmithran | MKS00072 | 5 | Early Intermediate | G Early Intermediate2 | 12 |  |
| Sanjumithra | MKS00070 | 5.2 | Early Intermediate | G Early Intermediate2 | 12 |  |
| Shakthivishakan A | MKS00034 | 5.2 | Early Intermediate | G Early Intermediate2 | 12 |  |
| Mohhan | MKS00064 | 4.6 | Early Intermediate | G Early Intermediate2 | 8 |  |
| S. YASWANNTH | MKS00039 | 3.8 | Beginner | G Beginner1s | 8 | Sunday not available |
| Kirthik | MKS00048 | 5.4 | Beginner | I Beginner2 | 10 |  |
| Ineya Individual | MKS00050 | 7.3 | Early Intermediate | I Intermediate | 4 |  |
| Madesh | MKS00194 | 4.7 | Beginner | L Beginner1 | 15 |  |
| B.AARAV NARAYAN | MKS00098 | 4.5 | Early Intermediate | L Early Intermediate1 | 12 |  |
| M.Nishik | MKS00113 | 6.5 | Early Intermediate | G Intermediate1 | 12 |  |
| Hitesh prabu | MKS00014 | 4.7 | Early Intermediate | G Intermediate1 | 12 | weekday 8-9, satu & sunda-ok |
| Mithran P | MKS00083 | 5.8 | Early Intermediate | G Intermediate1 | 12 |  |
| Vedhanth V | MKS00102 | 6.1 | Early Intermediate | G Intermediate1 | 12 |  |
| Diya | MKS00024 | 5.9 | Early Intermediate | G Intermediate1 | 12 |  |
| Kamesh kumar c | MKS00231 | 6 | Intermediate | I Intermediate2 | 7 |  |
| Priyan | MKS00162 | 3.7 | Beginner | I Beginner1 | 8 |  |
| Jovinya | MKS00075 | 4 | Beginner | L Beginner1 | 12 |  |
| S.V.Kavisree | MKS00111 | 3.4 | Beginner | L Beginner1 | 12 |  |
| Kaashvi Prakash | MKS00184 | 1.5 | Basic | I Basic2 | 5 |  |
| Viraaj Shanmugam | MKS00153 | 2 | Basic | I Basic2 | 11 |  |
| Sai Eswar | MKS00132 | 7.5 | Intermediate | I Intermediate2 | 18 |  |
| yaazhini | MKS00147 | 3.5 | Beginner | G Beginner1B | 12 |  |
| MELWIN G | MKS00100 | 3 | Beginner | G Beginner2 | 12 |  |
| N.Charan | MKS00148 | 2.8 | Beginner | G beginner1 | 12 |  |
| Sarvesh K | MKS00175 | 3.2 | Beginner | G beginner1C | 12 |  |
| Nyvan | MKS00208 | 1.7 | Basic | G Beginner1 | 12 |  |
| Thiyashwar S | MKS00181 | 1.7 | Basic | G Beginner1 | 12 |  |
| RITHIKNATH K.M | MKS00193 | 2.1 | Basic | G Beginner1 | 12 |  |
| Cholamithran BR | MKS00192 | 2.1 | Basic | G Beginner1 | 12 |  |
| BHAANAVI.V | MKS00189 | 2.2 | Basic | G Beginner1 | 12 |  |
| Jayasudhan | MKS00220 | 1.1 | Basic | G Beginner1 | 12 |  |
| V.Dharmasastha Individual | MKS00093 | 5.8 | Early Intermediate | I Early Intermediate2 | 6 |  |
| AATHISH S | MKS00229 | 3.5 | Beginner | G Beginner1 | 1 |  |

## Full schedule — one row per student assignment

| Date | Day | Time | Trainer | Student | Stud ID |
|---|---|---|---|---|---|
| 2026-10-01 | Thursday | 06:00:00 | Bathri | Vedh Pabba | MKS00190 |
| 2026-10-01 | Thursday | 06:00:00 | Prakash | Kirthik | MKS00048 |
| 2026-10-01 | Thursday | 11:15:00 | Bathri | Vikaesh | MKS00221 |
| 2026-10-01 | Thursday | 17:00:00 | Dhaanush | P.V Subhiksha | MKS00150 |
| 2026-10-01 | Thursday | 17:30:00 | Arshath | Sachin | MKS00059 |
| 2026-10-01 | Thursday | 17:30:00 | Arshath | Sarvin | MKS00060 |
| 2026-10-01 | Thursday | 17:30:00 | Arshath | YAASHVIN A/L SATEESHKUMAR | MKS00065 |
| 2026-10-01 | Thursday | 18:00:00 | Bathri | Harini | MKS00073 |
| 2026-10-01 | Thursday | 18:00:00 | Bathri | MELWIN G | MKS00100 |
| 2026-10-01 | Thursday | 18:00:00 | Bathri | N.Charan | MKS00148 |
| 2026-10-01 | Thursday | 18:00:00 | Bathri | Oviya B | MKS00038 |
| 2026-10-01 | Thursday | 18:00:00 | Bathri | Sarvesh K | MKS00175 |
| 2026-10-01 | Thursday | 18:00:00 | Bathri | yaazhini | MKS00147 |
| 2026-10-01 | Thursday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-01 | Thursday | 18:00:00 | Dhaanush | Vivaan Aaditya | MKS00053 |
| 2026-10-01 | Thursday | 18:00:00 | Prakash | A.T.Vagish | MKS00149 |
| 2026-10-01 | Thursday | 18:00:00 | Prakash | Charvi | MKS00163 |
| 2026-10-01 | Thursday | 18:00:00 | Prakash | M. R. Darshan | MKS00101 |
| 2026-10-01 | Thursday | 18:00:00 | Prakash | Mithra sree A | MKS00161 |
| 2026-10-01 | Thursday | 18:00:00 | Prakash | Mithun Rajamani chakravarthi | MKS00112 |
| 2026-10-01 | Thursday | 18:00:00 | Prakash | Nitharsana | MKS00095 |
| 2026-10-01 | Thursday | 18:00:00 | Prakash | Rooban | MKS00215 |
| 2026-10-01 | Thursday | 19:00:00 | Bathri | N.sri dharshni | MKS00055 |
| 2026-10-01 | Thursday | 19:00:00 | Bathri | Syed Individual | MKS00076 |
| 2026-10-01 | Thursday | 19:00:00 | Bathri | V. Dhaksha | MKS00110 |
| 2026-10-01 | Thursday | 19:00:00 | Dhaanush | V.Dharmasastha Individual | MKS00093 |
| 2026-10-01 | Thursday | 19:00:00 | Manikandan | Bhavadharani.B | MKS00203 |
| 2026-10-01 | Thursday | 19:00:00 | Manikandan | J Jerwin | MKS00230 |
| 2026-10-01 | Thursday | 19:00:00 | Manikandan | Jeevith. N.M | MKS00224 |
| 2026-10-01 | Thursday | 19:00:00 | Manikandan | R Logeshwaran | MKS00222 |
| 2026-10-01 | Thursday | 19:00:00 | Prakash | B.AARAV NARAYAN | MKS00098 |
| 2026-10-01 | Thursday | 19:00:00 | Prakash | Madesh | MKS00194 |
| 2026-10-01 | Thursday | 20:00:00 | Abinaya | BHAANAVI.V | MKS00189 |
| 2026-10-01 | Thursday | 20:00:00 | Abinaya | Cholamithran BR | MKS00192 |
| 2026-10-01 | Thursday | 20:00:00 | Abinaya | Jayasudhan | MKS00220 |
| 2026-10-01 | Thursday | 20:00:00 | Abinaya | Nyvan | MKS00208 |
| 2026-10-01 | Thursday | 20:00:00 | Abinaya | RITHIKNATH K.M | MKS00193 |
| 2026-10-01 | Thursday | 20:00:00 | Abinaya | S.Kabilan | MKS00198 |
| 2026-10-01 | Thursday | 20:00:00 | Abinaya | S.Kavirenu | MKS00199 |
| 2026-10-01 | Thursday | 20:00:00 | Abinaya | Thenamilthan.S | MKS00200 |
| 2026-10-01 | Thursday | 20:00:00 | Abinaya | Thiyashwar S | MKS00181 |
| 2026-10-01 | Thursday | 20:00:00 | Bathri | C S Sharwin | MKS00197 |
| 2026-10-01 | Thursday | 20:00:00 | Bathri | D R RAJAGOPALAN | MKS00176 |
| 2026-10-01 | Thursday | 20:00:00 | Bathri | Nishwanth R | MKS00171 |
| 2026-10-01 | Thursday | 20:00:00 | Bathri | Ridhanya Sri.V | MKS00178 |
| 2026-10-01 | Thursday | 20:00:00 | Bathri | S. Thashwin Raj | MKS00155 |
| 2026-10-01 | Thursday | 20:00:00 | Bathri | Vikash | MKS00168 |
| 2026-10-01 | Thursday | 20:00:00 | Dhaanush | Kamesh kumar c | MKS00231 |
| 2026-10-01 | Thursday | 20:00:00 | Dhaanush | Sai Eswar | MKS00132 |
| 2026-10-01 | Thursday | 20:00:00 | Manikandan | Aaradheya P | MKS00225 |
| 2026-10-01 | Thursday | 20:00:00 | Manikandan | Sri Varshini | MKS00232 |
| 2026-10-01 | Thursday | 20:00:00 | Prakash | Dev dharsan | MKS00142 |
| 2026-10-01 | Thursday | 20:00:00 | Prakash | Jovinya | MKS00075 |
| 2026-10-01 | Thursday | 20:00:00 | Prakash | M VARUNESH PANDI | MKS00166 |
| 2026-10-02 | Friday | 06:00:00 | Bathri | Vedh Pabba | MKS00190 |
| 2026-10-02 | Friday | 06:00:00 | Manikandan | Priyan | MKS00162 |
| 2026-10-02 | Friday | 09:00:00 | Prakash | Alagu Durai | MKS00141 |
| 2026-10-02 | Friday | 11:00:00 | Bathri | Magizh | MKS00213 |
| 2026-10-02 | Friday | 17:00:00 | Bathri | Harri mithran P | MKS00210 |
| 2026-10-02 | Friday | 17:00:00 | Dhaanush | P.V Subhiksha | MKS00150 |
| 2026-10-02 | Friday | 17:30:00 | Arshath | Krishiv Ajay | MKS00037 |
| 2026-10-02 | Friday | 17:30:00 | Arshath | Sachin | MKS00059 |
| 2026-10-02 | Friday | 17:30:00 | Arshath | Sarvin | MKS00060 |
| 2026-10-02 | Friday | 17:30:00 | Arshath | Selvakrishna RK | MKS00167 |
| 2026-10-02 | Friday | 17:30:00 | Arshath | Srikavi Bharathi | MKS00045 |
| 2026-10-02 | Friday | 17:30:00 | Arshath | Vivaan Aaditya | MKS00053 |
| 2026-10-02 | Friday | 17:30:00 | Arshath | YAASHVIN A/L SATEESHKUMAR | MKS00065 |
| 2026-10-02 | Friday | 18:00:00 | Bathri | Jovinya | MKS00075 |
| 2026-10-02 | Friday | 18:00:00 | Bathri | S.V.Kavisree | MKS00111 |
| 2026-10-02 | Friday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-02 | Friday | 18:00:00 | Dhaanush | Thivya | MKS00056 |
| 2026-10-02 | Friday | 18:00:00 | Guru | Harini | MKS00073 |
| 2026-10-02 | Friday | 18:00:00 | Prakash | Sarvesh K | MKS00175 |
| 2026-10-02 | Friday | 19:00:00 | Abinaya | A.Bavinesh | MKS00214 |
| 2026-10-02 | Friday | 19:00:00 | Abinaya | B.V.Tijesh | MKS00219 |
| 2026-10-02 | Friday | 19:00:00 | Abinaya | C.V.Chanvika | MKS00196 |
| 2026-10-02 | Friday | 19:00:00 | Bathri | HAASHINI  SHRIVY V | MKS00115 |
| 2026-10-02 | Friday | 19:00:00 | Bathri | V. Dhaksha | MKS00110 |
| 2026-10-02 | Friday | 19:00:00 | Bathri | Vikaesh | MKS00221 |
| 2026-10-02 | Friday | 19:00:00 | Dhaanush | Abhijay | MKS00202 |
| 2026-10-02 | Friday | 19:00:00 | Dhaanush | Ayaan Haris | MKS00092 |
| 2026-10-02 | Friday | 19:00:00 | Dhaanush | B SARVESSH | MKS00108 |
| 2026-10-02 | Friday | 19:00:00 | Dhaanush | D. Tharun | MKS00127 |
| 2026-10-02 | Friday | 19:00:00 | Dhaanush | Nakshathra. C | MKS00227 |
| 2026-10-02 | Friday | 19:00:00 | Dhaanush | Rohith kumar.B | MKS00207 |
| 2026-10-02 | Friday | 19:00:00 | Dhaanush | V.D. THARUN ADITHYA | MKS00212 |
| 2026-10-02 | Friday | 19:00:00 | Dhaanush | V.Dharmasastha Individual | MKS00093 |
| 2026-10-02 | Friday | 19:00:00 | Dhaanush | Yuviga | MKS00107 |
| 2026-10-02 | Friday | 19:00:00 | Manikandan | S Mounitha | MKS00226 |
| 2026-10-02 | Friday | 19:00:00 | Prakash | A R Thatchiraa Shree | MKS00172 |
| 2026-10-02 | Friday | 19:00:00 | Prakash | H V Kanishk | MKS00154 |
| 2026-10-02 | Friday | 19:00:00 | Prakash | S. Thashwin Raj | MKS00155 |
| 2026-10-02 | Friday | 19:00:00 | Prakash | Vikash | MKS00168 |
| 2026-10-02 | Friday | 20:00:00 | Abinaya | Adhigan Amarnath | MKS00204 |
| 2026-10-02 | Friday | 20:00:00 | Abinaya | B.SAI SRI | MKS00211 |
| 2026-10-02 | Friday | 20:00:00 | Abinaya | Sudharshika | MKS00216 |
| 2026-10-02 | Friday | 20:00:00 | Bathri | D R RAJAGOPALAN | MKS00176 |
| 2026-10-02 | Friday | 20:00:00 | Bathri | MELWIN G | MKS00100 |
| 2026-10-02 | Friday | 20:00:00 | Bathri | N.Charan | MKS00148 |
| 2026-10-02 | Friday | 20:00:00 | Bathri | Nirupan | MKS00185 |
| 2026-10-02 | Friday | 20:00:00 | Bathri | Oviya B | MKS00038 |
| 2026-10-02 | Friday | 20:00:00 | Bathri | Ryan Stalin | MKS00007 |
| 2026-10-02 | Friday | 20:00:00 | Bathri | S. YASWANNTH | MKS00039 |
| 2026-10-02 | Friday | 20:00:00 | Bathri | S.P.NEHASRI | MKS00157 |
| 2026-10-02 | Friday | 20:00:00 | Bathri | yaazhini | MKS00147 |
| 2026-10-02 | Friday | 20:00:00 | Dhaanush | K. Sudhir | MKS00228 |
| 2026-10-02 | Friday | 20:00:00 | Dhaanush | KAVIBHARATHI P | MKS00201 |
| 2026-10-02 | Friday | 20:00:00 | Dhaanush | Kavinpriyan | MKS00023 |
| 2026-10-02 | Friday | 20:00:00 | Dhaanush | Keshav Krishna | YTC |
| 2026-10-02 | Friday | 20:00:00 | Dhaanush | M Nethran | MKS00020 |
| 2026-10-02 | Friday | 20:00:00 | Dhaanush | Pranith | MKS00143 |
| 2026-10-02 | Friday | 20:00:00 | Dhaanush | S R Sabeshwar | MKS00223 |
| 2026-10-02 | Friday | 20:00:00 | Dhaanush | Samuel Rajan | MKS00182 |
| 2026-10-02 | Friday | 20:00:00 | Dhaanush | V.Pranav | MKS00173 |
| 2026-10-02 | Friday | 20:00:00 | Guru | M VARUNESH PANDI | MKS00166 |
| 2026-10-02 | Friday | 20:00:00 | Manikandan | Bhavadharani.B | MKS00203 |
| 2026-10-02 | Friday | 20:00:00 | Manikandan | Dev dharsan | MKS00142 |
| 2026-10-02 | Friday | 20:00:00 | Manikandan | J Jerwin | MKS00230 |
| 2026-10-02 | Friday | 20:00:00 | Manikandan | Jayasudhan | MKS00220 |
| 2026-10-02 | Friday | 20:00:00 | Manikandan | Kavinth P | MKS00217 |
| 2026-10-02 | Friday | 20:00:00 | Prakash | Madesh | MKS00194 |
| 2026-10-02 | Friday | 20:00:00 | Prakash | Syed Individual | MKS00076 |
| 2026-10-03 | Saturday | 06:00:00 | Bathri | Pugazhini Navaneethan | MKS00156 |
| 2026-10-03 | Saturday | 06:00:00 | Prakash | Kirthik | MKS00048 |
| 2026-10-03 | Saturday | 10:00:00 | Abinaya | Aadhav Mithun | MKS00170 |
| 2026-10-03 | Saturday | 11:00:00 | Bathri | Akshadhasree | MKS00067 |
| 2026-10-03 | Saturday | 11:00:00 | Bathri | Anikha | MKS00066 |
| 2026-10-03 | Saturday | 12:15:00 | Bathri | Viraaj Shanmugam | MKS00153 |
| 2026-10-03 | Saturday | 17:00:00 | Arshath | Sachin | MKS00059 |
| 2026-10-03 | Saturday | 17:00:00 | Arshath | Vivaan Aaditya | MKS00053 |
| 2026-10-03 | Saturday | 17:00:00 | Dhaanush | Avyukt A Praveen | MKS00174 |
| 2026-10-03 | Saturday | 17:00:00 | Dhaanush | Manikandan S | MKS00183 |
| 2026-10-03 | Saturday | 17:00:00 | Dhaanush | Rohith kumar.B | MKS00207 |
| 2026-10-03 | Saturday | 17:00:00 | Dhaanush | V.D. THARUN ADITHYA | MKS00212 |
| 2026-10-03 | Saturday | 18:00:00 | Arshath | Krishiv Ajay | MKS00037 |
| 2026-10-03 | Saturday | 18:00:00 | Arshath | Sarvin | MKS00060 |
| 2026-10-03 | Saturday | 18:00:00 | Arshath | Selvakrishna RK | MKS00167 |
| 2026-10-03 | Saturday | 18:00:00 | Arshath | Srikavi Bharathi | MKS00045 |
| 2026-10-03 | Saturday | 18:00:00 | Arshath | YAASHVIN A/L SATEESHKUMAR | MKS00065 |
| 2026-10-03 | Saturday | 18:00:00 | Bathri | T L KANISHKAR | MKS00195 |
| 2026-10-03 | Saturday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-03 | Saturday | 18:00:00 | Dhaanush | Reyhan nawaz | MKS00049 |
| 2026-10-03 | Saturday | 18:00:00 | Dhaanush | Thivya | MKS00056 |
| 2026-10-03 | Saturday | 18:00:00 | Prakash | A.T.Vagish | MKS00149 |
| 2026-10-03 | Saturday | 18:00:00 | Prakash | Charvi | MKS00163 |
| 2026-10-03 | Saturday | 18:00:00 | Prakash | M. R. Darshan | MKS00101 |
| 2026-10-03 | Saturday | 18:00:00 | Prakash | Mithra sree A | MKS00161 |
| 2026-10-03 | Saturday | 18:00:00 | Prakash | Mithun Rajamani chakravarthi | MKS00112 |
| 2026-10-03 | Saturday | 18:00:00 | Prakash | Nitharsana | MKS00095 |
| 2026-10-03 | Saturday | 18:00:00 | Prakash | Oviya B | MKS00038 |
| 2026-10-03 | Saturday | 18:00:00 | Prakash | Rooban | MKS00215 |
| 2026-10-03 | Saturday | 19:00:00 | Abinaya | Adhigan Amarnath | MKS00204 |
| 2026-10-03 | Saturday | 19:00:00 | Abinaya | B.SAI SRI | MKS00211 |
| 2026-10-03 | Saturday | 19:00:00 | Abinaya | Sudharshika | MKS00216 |
| 2026-10-03 | Saturday | 19:00:00 | Bathri | Jovinya | MKS00075 |
| 2026-10-03 | Saturday | 19:00:00 | Bathri | S.V.Kavisree | MKS00111 |
| 2026-10-03 | Saturday | 19:00:00 | Bathri | Syed Individual | MKS00076 |
| 2026-10-03 | Saturday | 19:00:00 | Dhaanush | Arishmithran | MKS00072 |
| 2026-10-03 | Saturday | 19:00:00 | Dhaanush | Hithesh | MKS00206 |
| 2026-10-03 | Saturday | 19:00:00 | Dhaanush | Mohhan | MKS00064 |
| 2026-10-03 | Saturday | 19:00:00 | Dhaanush | Praduksha | MKS00091 |
| 2026-10-03 | Saturday | 19:00:00 | Dhaanush | S R Sabeshwar | MKS00223 |
| 2026-10-03 | Saturday | 19:00:00 | Dhaanush | S.Raagavarshenee | MKS00009 |
| 2026-10-03 | Saturday | 19:00:00 | Dhaanush | Sanjumithra | MKS00070 |
| 2026-10-03 | Saturday | 19:00:00 | Dhaanush | Shakthivishakan A | MKS00034 |
| 2026-10-03 | Saturday | 19:00:00 | Manikandan | Aaradheya P | MKS00225 |
| 2026-10-03 | Saturday | 19:00:00 | Manikandan | Bhavadharani.B | MKS00203 |
| 2026-10-03 | Saturday | 19:00:00 | Manikandan | Jayasudhan | MKS00220 |
| 2026-10-03 | Saturday | 19:00:00 | Manikandan | Kavinth P | MKS00217 |
| 2026-10-03 | Saturday | 19:00:00 | Manikandan | S Mounitha | MKS00226 |
| 2026-10-03 | Saturday | 19:00:00 | Manikandan | Sri Varshini | MKS00232 |
| 2026-10-03 | Saturday | 19:00:00 | Prakash | Ineya Individual | MKS00050 |
| 2026-10-03 | Saturday | 19:00:00 | Saravanan | Diya | MKS00024 |
| 2026-10-03 | Saturday | 19:00:00 | Saravanan | Hitesh prabu | MKS00014 |
| 2026-10-03 | Saturday | 19:00:00 | Saravanan | M.Nishik | MKS00113 |
| 2026-10-03 | Saturday | 19:00:00 | Saravanan | Mithran P | MKS00083 |
| 2026-10-03 | Saturday | 19:00:00 | Saravanan | Vedhanth V | MKS00102 |
| 2026-10-03 | Saturday | 20:00:00 | Bathri | A R Thatchiraa Shree | MKS00172 |
| 2026-10-03 | Saturday | 20:00:00 | Bathri | Abhijay | MKS00202 |
| 2026-10-03 | Saturday | 20:00:00 | Bathri | C S Sharwin | MKS00197 |
| 2026-10-03 | Saturday | 20:00:00 | Bathri | D R RAJAGOPALAN | MKS00176 |
| 2026-10-03 | Saturday | 20:00:00 | Bathri | H V Kanishk | MKS00154 |
| 2026-10-03 | Saturday | 20:00:00 | Bathri | Nishwanth R | MKS00171 |
| 2026-10-03 | Saturday | 20:00:00 | Bathri | Ridhanya Sri.V | MKS00178 |
| 2026-10-03 | Saturday | 20:00:00 | Bathri | S. Thashwin Raj | MKS00155 |
| 2026-10-03 | Saturday | 20:00:00 | Bathri | S.P.NEHASRI | MKS00157 |
| 2026-10-03 | Saturday | 20:00:00 | Bathri | Sarvesh K | MKS00175 |
| 2026-10-03 | Saturday | 20:00:00 | Bathri | Vikash | MKS00168 |
| 2026-10-03 | Saturday | 20:00:00 | Guru | D KAVISH | MKS00079 |
| 2026-10-03 | Saturday | 20:00:00 | Guru | Dhanya
  sri S S | MKS00114 |
| 2026-10-03 | Saturday | 20:00:00 | Guru | HAASHINI  SHRIVY V | MKS00115 |
| 2026-10-03 | Saturday | 20:00:00 | Guru | M.Nalini Hirthika | MKS00118 |
| 2026-10-03 | Saturday | 20:00:00 | Guru | Nirupan | MKS00185 |
| 2026-10-03 | Saturday | 20:00:00 | Guru | Ryan Stalin | MKS00007 |
| 2026-10-03 | Saturday | 20:00:00 | Guru | S. YASWANNTH | MKS00039 |
| 2026-10-03 | Saturday | 20:00:00 | Guru | V. Srikaviyazhini | MKS00131 |
| 2026-10-03 | Saturday | 20:00:00 | Manikandan | Dev dharsan | MKS00142 |
| 2026-10-03 | Saturday | 20:00:00 | Manikandan | M VARUNESH PANDI | MKS00166 |
| 2026-10-03 | Saturday | 20:00:00 | Prakash | B.AARAV NARAYAN | MKS00098 |
| 2026-10-03 | Saturday | 20:00:00 | Prakash | Madesh | MKS00194 |
| 2026-10-03 | Saturday | 20:00:00 | Prakash | N.Charan | MKS00148 |
| 2026-10-03 | Saturday | 21:00:00 | Bathri | Vaibhavi Krishna | MKS00164 |
| 2026-10-03 | Saturday | 21:00:00 | Bathri | Vaishnavi Krishna | MKS00165 |
| 2026-10-04 | Sunday | 09:00:00 | Bathri | Vikaesh | MKS00221 |
| 2026-10-04 | Sunday | 09:00:00 | Dhaanush | Kamesh kumar c | MKS00231 |
| 2026-10-04 | Sunday | 09:00:00 | Dhaanush | Sai Eswar | MKS00132 |
| 2026-10-04 | Sunday | 09:00:00 | Guru | Viraaj Shanmugam | MKS00153 |
| 2026-10-04 | Sunday | 10:00:00 | Abinaya | Aadhav Mithun | MKS00170 |
| 2026-10-04 | Sunday | 10:00:00 | Abinaya | Abhijay | MKS00202 |
| 2026-10-04 | Sunday | 10:00:00 | Abinaya | Ayaan Haris | MKS00092 |
| 2026-10-04 | Sunday | 10:00:00 | Abinaya | B SARVESSH | MKS00108 |
| 2026-10-04 | Sunday | 10:00:00 | Abinaya | B.AARAV NARAYAN | MKS00098 |
| 2026-10-04 | Sunday | 10:00:00 | Abinaya | D R RAJAGOPALAN | MKS00176 |
| 2026-10-04 | Sunday | 10:00:00 | Abinaya | D. Tharun | MKS00127 |
| 2026-10-04 | Sunday | 10:00:00 | Abinaya | K. Sudhir | MKS00228 |
| 2026-10-04 | Sunday | 10:00:00 | Abinaya | KAVIBHARATHI P | MKS00201 |
| 2026-10-04 | Sunday | 10:00:00 | Abinaya | Kavinpriyan | MKS00023 |
| 2026-10-04 | Sunday | 10:00:00 | Abinaya | Madesh | MKS00194 |
| 2026-10-04 | Sunday | 10:00:00 | Abinaya | Manikandan S | MKS00183 |
| 2026-10-04 | Sunday | 10:00:00 | Abinaya | Nakshathra. C | MKS00227 |
| 2026-10-04 | Sunday | 10:00:00 | Abinaya | Pranith | MKS00143 |
| 2026-10-04 | Sunday | 10:00:00 | Abinaya | Rohith kumar.B | MKS00207 |
| 2026-10-04 | Sunday | 10:00:00 | Abinaya | S R Sabeshwar | MKS00223 |
| 2026-10-04 | Sunday | 10:00:00 | Abinaya | S.Raagavarshenee | MKS00009 |
| 2026-10-04 | Sunday | 10:00:00 | Abinaya | V.D. THARUN ADITHYA | MKS00212 |
| 2026-10-04 | Sunday | 10:00:00 | Abinaya | V.Pranav | MKS00173 |
| 2026-10-04 | Sunday | 10:00:00 | Abinaya | Yuviga | MKS00107 |
| 2026-10-04 | Sunday | 10:00:00 | Arshath | Sachin | MKS00059 |
| 2026-10-04 | Sunday | 10:00:00 | Arshath | Vivaan Aaditya | MKS00053 |
| 2026-10-04 | Sunday | 10:00:00 | Dhaanush | Diya | MKS00024 |
| 2026-10-04 | Sunday | 10:00:00 | Dhaanush | M.Nishik | MKS00113 |
| 2026-10-04 | Sunday | 10:00:00 | Dhaanush | Mithran P | MKS00083 |
| 2026-10-04 | Sunday | 10:00:00 | Dhaanush | Reyhan nawaz | MKS00049 |
| 2026-10-04 | Sunday | 10:00:00 | Dhaanush | Sarvin | MKS00060 |
| 2026-10-04 | Sunday | 10:00:00 | Dhaanush | Selvakrishna RK | MKS00167 |
| 2026-10-04 | Sunday | 10:00:00 | Dhaanush | Srikavi Bharathi | MKS00045 |
| 2026-10-04 | Sunday | 10:00:00 | Dhaanush | Thivya | MKS00056 |
| 2026-10-04 | Sunday | 10:00:00 | Dhaanush | V.Dharmasastha Individual | MKS00093 |
| 2026-10-04 | Sunday | 10:00:00 | Dhaanush | Vedhanth V | MKS00102 |
| 2026-10-04 | Sunday | 10:00:00 | Hema | Arishmithran | MKS00072 |
| 2026-10-04 | Sunday | 10:00:00 | Hema | Hitesh prabu | MKS00014 |
| 2026-10-04 | Sunday | 10:00:00 | Hema | Hithesh | MKS00206 |
| 2026-10-04 | Sunday | 10:00:00 | Hema | Mohhan | MKS00064 |
| 2026-10-04 | Sunday | 10:00:00 | Hema | Praduksha | MKS00091 |
| 2026-10-04 | Sunday | 10:00:00 | Hema | Sanjumithra | MKS00070 |
| 2026-10-04 | Sunday | 10:00:00 | Hema | Shakthivishakan A | MKS00034 |
| 2026-10-04 | Sunday | 11:00:00 | Abinaya | Adhigan Amarnath | MKS00204 |
| 2026-10-04 | Sunday | 11:00:00 | Abinaya | B.SAI SRI | MKS00211 |
| 2026-10-04 | Sunday | 11:00:00 | Abinaya | BHAANAVI.V | MKS00189 |
| 2026-10-04 | Sunday | 11:00:00 | Abinaya | Bhavadharani.B | MKS00203 |
| 2026-10-04 | Sunday | 11:00:00 | Abinaya | Cholamithran BR | MKS00192 |
| 2026-10-04 | Sunday | 11:00:00 | Abinaya | Dev dharsan | MKS00142 |
| 2026-10-04 | Sunday | 11:00:00 | Abinaya | Jayasudhan | MKS00220 |
| 2026-10-04 | Sunday | 11:00:00 | Abinaya | Kavinth P | MKS00217 |
| 2026-10-04 | Sunday | 11:00:00 | Abinaya | M.Srisaran | MKS00186 |
| 2026-10-04 | Sunday | 11:00:00 | Abinaya | Nyvan | MKS00208 |
| 2026-10-04 | Sunday | 11:00:00 | Abinaya | RITHIKNATH K.M | MKS00193 |
| 2026-10-04 | Sunday | 11:00:00 | Abinaya | Rooban | MKS00215 |
| 2026-10-04 | Sunday | 11:00:00 | Abinaya | S.Kabilan | MKS00198 |
| 2026-10-04 | Sunday | 11:00:00 | Abinaya | S.Kavirenu | MKS00199 |
| 2026-10-04 | Sunday | 11:00:00 | Abinaya | S.P.NEHASRI | MKS00157 |
| 2026-10-04 | Sunday | 11:00:00 | Abinaya | Sudharshika | MKS00216 |
| 2026-10-04 | Sunday | 11:00:00 | Abinaya | Thenamilthan.S | MKS00200 |
| 2026-10-04 | Sunday | 11:00:00 | Abinaya | Thiyashwar S | MKS00181 |
| 2026-10-04 | Sunday | 11:00:00 | Arshath | Krishiv Ajay | MKS00037 |
| 2026-10-04 | Sunday | 11:00:00 | Arshath | YAASHVIN A/L SATEESHKUMAR | MKS00065 |
| 2026-10-04 | Sunday | 11:00:00 | Guru | A R Thatchiraa Shree | MKS00172 |
| 2026-10-04 | Sunday | 11:00:00 | Guru | A.T.Vagish | MKS00149 |
| 2026-10-04 | Sunday | 11:00:00 | Guru | Charvi | MKS00163 |
| 2026-10-04 | Sunday | 11:00:00 | Guru | D KAVISH | MKS00079 |
| 2026-10-04 | Sunday | 11:00:00 | Guru | Dhanya
  sri S S | MKS00114 |
| 2026-10-04 | Sunday | 11:00:00 | Guru | H V Kanishk | MKS00154 |
| 2026-10-04 | Sunday | 11:00:00 | Guru | HAASHINI  SHRIVY V | MKS00115 |
| 2026-10-04 | Sunday | 11:00:00 | Guru | M. R. Darshan | MKS00101 |
| 2026-10-04 | Sunday | 11:00:00 | Guru | M.Nalini Hirthika | MKS00118 |
| 2026-10-04 | Sunday | 11:00:00 | Guru | N.Charan | MKS00148 |
| 2026-10-04 | Sunday | 11:00:00 | Guru | Nirupan | MKS00185 |
| 2026-10-04 | Sunday | 11:00:00 | Guru | Nitharsana | MKS00095 |
| 2026-10-04 | Sunday | 11:00:00 | Guru | R Logeshwaran | MKS00222 |
| 2026-10-04 | Sunday | 11:00:00 | Guru | Ryan Stalin | MKS00007 |
| 2026-10-04 | Sunday | 11:00:00 | Guru | S. Thashwin Raj | MKS00155 |
| 2026-10-04 | Sunday | 11:00:00 | Guru | V. Srikaviyazhini | MKS00131 |
| 2026-10-04 | Sunday | 11:00:00 | Guru | Vikash | MKS00168 |
| 2026-10-04 | Sunday | 11:00:00 | Hema | Akshadhasree | MKS00067 |
| 2026-10-04 | Sunday | 11:00:00 | Hema | Anikha | MKS00066 |
| 2026-10-04 | Sunday | 11:00:00 | Hema | Avyukt A Praveen | MKS00174 |
| 2026-10-04 | Sunday | 11:00:00 | Hema | C S Sharwin | MKS00197 |
| 2026-10-04 | Sunday | 11:00:00 | Hema | Harini | MKS00073 |
| 2026-10-04 | Sunday | 11:00:00 | Hema | Keshav Krishna | YTC |
| 2026-10-04 | Sunday | 11:00:00 | Hema | M Nethran | MKS00020 |
| 2026-10-04 | Sunday | 11:00:00 | Hema | MELWIN G | MKS00100 |
| 2026-10-04 | Sunday | 11:00:00 | Hema | Mithra sree A | MKS00161 |
| 2026-10-04 | Sunday | 11:00:00 | Hema | Mithun Rajamani chakravarthi | MKS00112 |
| 2026-10-04 | Sunday | 11:00:00 | Hema | Oviya B | MKS00038 |
| 2026-10-04 | Sunday | 11:00:00 | Hema | Sarvesh K | MKS00175 |
| 2026-10-04 | Sunday | 11:00:00 | Hema | yaazhini | MKS00147 |
| 2026-10-04 | Sunday | 11:00:00 | Prakash | J Jerwin | MKS00230 |
| 2026-10-04 | Sunday | 13:30:00 | Abinaya | Jovinya | MKS00075 |
| 2026-10-04 | Sunday | 13:30:00 | Abinaya | M VARUNESH PANDI | MKS00166 |
| 2026-10-04 | Sunday | 13:30:00 | Abinaya | S.V.Kavisree | MKS00111 |
| 2026-10-04 | Sunday | 13:30:00 | Prakash | N.sri dharshni | MKS00055 |
| 2026-10-05 | Monday | 12:00:00 | Bathri | Bhavadharani.B | MKS00203 |
| 2026-10-05 | Monday | 12:00:00 | Bathri | Jeevith. N.M | MKS00224 |
| 2026-10-05 | Monday | 12:00:00 | Bathri | R Logeshwaran | MKS00222 |
| 2026-10-05 | Monday | 14:00:00 | Arshath | Krishiv Ajay | MKS00037 |
| 2026-10-05 | Monday | 14:00:00 | Arshath | M.Nishik | MKS00113 |
| 2026-10-05 | Monday | 14:00:00 | Arshath | Manikandan S | MKS00183 |
| 2026-10-05 | Monday | 14:00:00 | Arshath | Sarvin | MKS00060 |
| 2026-10-05 | Monday | 14:00:00 | Arshath | Selvakrishna RK | MKS00167 |
| 2026-10-05 | Monday | 14:00:00 | Arshath | Srikavi Bharathi | MKS00045 |
| 2026-10-05 | Monday | 14:00:00 | Arshath | YAASHVIN A/L SATEESHKUMAR | MKS00065 |
| 2026-10-05 | Monday | 15:00:00 | Bathri | HAASHINI  SHRIVY V | MKS00115 |
| 2026-10-05 | Monday | 15:00:00 | Bathri | MELWIN G | MKS00100 |
| 2026-10-05 | Monday | 15:00:00 | Bathri | N.Charan | MKS00148 |
| 2026-10-05 | Monday | 15:00:00 | Bathri | yaazhini | MKS00147 |
| 2026-10-05 | Monday | 16:30:00 | Bathri | Devansh gade | MKS00218 |
| 2026-10-05 | Monday | 18:00:00 | Bathri | Vikaesh | MKS00221 |
| 2026-10-05 | Monday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-05 | Monday | 18:00:00 | Dhaanush | Sachin | MKS00059 |
| 2026-10-05 | Monday | 18:00:00 | Dhaanush | Vivaan Aaditya | MKS00053 |
| 2026-10-05 | Monday | 18:00:00 | Prakash | A.T.Vagish | MKS00149 |
| 2026-10-05 | Monday | 18:00:00 | Prakash | Akshadhasree | MKS00067 |
| 2026-10-05 | Monday | 18:00:00 | Prakash | Anikha | MKS00066 |
| 2026-10-05 | Monday | 18:00:00 | Prakash | C S Sharwin | MKS00197 |
| 2026-10-05 | Monday | 18:00:00 | Prakash | Charvi | MKS00163 |
| 2026-10-05 | Monday | 18:00:00 | Prakash | Harini | MKS00073 |
| 2026-10-05 | Monday | 18:00:00 | Prakash | M. R. Darshan | MKS00101 |
| 2026-10-05 | Monday | 18:00:00 | Prakash | Mithra sree A | MKS00161 |
| 2026-10-05 | Monday | 18:00:00 | Prakash | Mithun Rajamani chakravarthi | MKS00112 |
| 2026-10-05 | Monday | 18:00:00 | Prakash | Nitharsana | MKS00095 |
| 2026-10-05 | Monday | 18:00:00 | Prakash | Oviya B | MKS00038 |
| 2026-10-05 | Monday | 18:00:00 | Prakash | Rooban | MKS00215 |
| 2026-10-05 | Monday | 19:00:00 | Abinaya | A.Bavinesh | MKS00214 |
| 2026-10-05 | Monday | 19:00:00 | Abinaya | B.V.Tijesh | MKS00219 |
| 2026-10-05 | Monday | 19:00:00 | Abinaya | C.V.Chanvika | MKS00196 |
| 2026-10-05 | Monday | 19:00:00 | Bathri | V. Dhaksha | MKS00110 |
| 2026-10-05 | Monday | 19:00:00 | Dhaanush | Abhijay | MKS00202 |
| 2026-10-05 | Monday | 19:00:00 | Dhaanush | Ayaan Haris | MKS00092 |
| 2026-10-05 | Monday | 19:00:00 | Dhaanush | B SARVESSH | MKS00108 |
| 2026-10-05 | Monday | 19:00:00 | Dhaanush | D. Tharun | MKS00127 |
| 2026-10-05 | Monday | 19:00:00 | Dhaanush | Nakshathra. C | MKS00227 |
| 2026-10-05 | Monday | 19:00:00 | Dhaanush | Rohith kumar.B | MKS00207 |
| 2026-10-05 | Monday | 19:00:00 | Dhaanush | V.D. THARUN ADITHYA | MKS00212 |
| 2026-10-05 | Monday | 19:00:00 | Dhaanush | Yuviga | MKS00107 |
| 2026-10-05 | Monday | 19:00:00 | Manikandan | J Jerwin | MKS00230 |
| 2026-10-05 | Monday | 19:00:00 | Manikandan | S Mounitha | MKS00226 |
| 2026-10-05 | Monday | 19:00:00 | Prakash | Aaradheya P | MKS00225 |
| 2026-10-05 | Monday | 19:00:00 | Prakash | N.sri dharshni | MKS00055 |
| 2026-10-05 | Monday | 20:00:00 | Abinaya | Kavinth P | MKS00217 |
| 2026-10-05 | Monday | 20:00:00 | Abinaya | M.Srisaran | MKS00186 |
| 2026-10-05 | Monday | 20:00:00 | Abinaya | S.Kabilan | MKS00198 |
| 2026-10-05 | Monday | 20:00:00 | Abinaya | S.Kavirenu | MKS00199 |
| 2026-10-05 | Monday | 20:00:00 | Abinaya | Thenamilthan.S | MKS00200 |
| 2026-10-05 | Monday | 20:00:00 | Dhaanush | Hithesh | MKS00206 |
| 2026-10-05 | Monday | 20:00:00 | Dhaanush | K. Sudhir | MKS00228 |
| 2026-10-05 | Monday | 20:00:00 | Dhaanush | KAVIBHARATHI P | MKS00201 |
| 2026-10-05 | Monday | 20:00:00 | Dhaanush | Kavinpriyan | MKS00023 |
| 2026-10-05 | Monday | 20:00:00 | Dhaanush | Keshav Krishna | YTC |
| 2026-10-05 | Monday | 20:00:00 | Dhaanush | M Nethran | MKS00020 |
| 2026-10-05 | Monday | 20:00:00 | Dhaanush | Pranith | MKS00143 |
| 2026-10-05 | Monday | 20:00:00 | Dhaanush | V.Pranav | MKS00173 |
| 2026-10-05 | Monday | 20:00:00 | Guru | D KAVISH | MKS00079 |
| 2026-10-05 | Monday | 20:00:00 | Guru | Dhanya
  sri S S | MKS00114 |
| 2026-10-05 | Monday | 20:00:00 | Guru | M.Nalini Hirthika | MKS00118 |
| 2026-10-05 | Monday | 20:00:00 | Guru | Nirupan | MKS00185 |
| 2026-10-05 | Monday | 20:00:00 | Guru | Ryan Stalin | MKS00007 |
| 2026-10-05 | Monday | 20:00:00 | Guru | V. Srikaviyazhini | MKS00131 |
| 2026-10-05 | Monday | 20:00:00 | Manikandan | Dev dharsan | MKS00142 |
| 2026-10-05 | Monday | 20:00:00 | Manikandan | Jayasudhan | MKS00220 |
| 2026-10-05 | Monday | 20:00:00 | Manikandan | M VARUNESH PANDI | MKS00166 |
| 2026-10-06 | Tuesday | 06:00:00 | Bathri | Pugazhini Navaneethan | MKS00156 |
| 2026-10-06 | Tuesday | 06:00:00 | Prakash | Kirthik | MKS00048 |
| 2026-10-06 | Tuesday | 09:00:00 | Prakash | Alagu Durai | MKS00141 |
| 2026-10-06 | Tuesday | 11:00:00 | Bathri | Magizh | MKS00213 |
| 2026-10-06 | Tuesday | 17:00:00 | Bathri | Harri mithran P | MKS00210 |
| 2026-10-06 | Tuesday | 17:00:00 | Dhaanush | P.V Subhiksha | MKS00150 |
| 2026-10-06 | Tuesday | 18:00:00 | Bathri | Harini | MKS00073 |
| 2026-10-06 | Tuesday | 18:00:00 | Bathri | Jovinya | MKS00075 |
| 2026-10-06 | Tuesday | 18:00:00 | Bathri | MELWIN G | MKS00100 |
| 2026-10-06 | Tuesday | 18:00:00 | Bathri | N.Charan | MKS00148 |
| 2026-10-06 | Tuesday | 18:00:00 | Bathri | S.V.Kavisree | MKS00111 |
| 2026-10-06 | Tuesday | 18:00:00 | Bathri | Sarvesh K | MKS00175 |
| 2026-10-06 | Tuesday | 18:00:00 | Bathri | yaazhini | MKS00147 |
| 2026-10-06 | Tuesday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-06 | Tuesday | 18:00:00 | Dhaanush | Reyhan nawaz | MKS00049 |
| 2026-10-06 | Tuesday | 18:00:00 | Dhaanush | Thivya | MKS00056 |
| 2026-10-06 | Tuesday | 18:00:00 | Prakash | HAASHINI  SHRIVY V | MKS00115 |
| 2026-10-06 | Tuesday | 18:00:00 | Prakash | Mithra sree A | MKS00161 |
| 2026-10-06 | Tuesday | 18:00:00 | Prakash | Mithun Rajamani chakravarthi | MKS00112 |
| 2026-10-06 | Tuesday | 18:00:00 | Prakash | Rooban | MKS00215 |
| 2026-10-06 | Tuesday | 19:00:00 | Abinaya | Adhigan Amarnath | MKS00204 |
| 2026-10-06 | Tuesday | 19:00:00 | Abinaya | B.SAI SRI | MKS00211 |
| 2026-10-06 | Tuesday | 19:00:00 | Abinaya | Bhavadharani.B | MKS00203 |
| 2026-10-06 | Tuesday | 19:00:00 | Abinaya | Sudharshika | MKS00216 |
| 2026-10-06 | Tuesday | 19:00:00 | Bathri | Syed Individual | MKS00076 |
| 2026-10-06 | Tuesday | 19:00:00 | Bathri | V. Dhaksha | MKS00110 |
| 2026-10-06 | Tuesday | 19:00:00 | Dhaanush | Abhijay | MKS00202 |
| 2026-10-06 | Tuesday | 19:00:00 | Dhaanush | Ayaan Haris | MKS00092 |
| 2026-10-06 | Tuesday | 19:00:00 | Dhaanush | B SARVESSH | MKS00108 |
| 2026-10-06 | Tuesday | 19:00:00 | Dhaanush | D. Tharun | MKS00127 |
| 2026-10-06 | Tuesday | 19:00:00 | Dhaanush | N.sri dharshni | MKS00055 |
| 2026-10-06 | Tuesday | 19:00:00 | Dhaanush | Nakshathra. C | MKS00227 |
| 2026-10-06 | Tuesday | 19:00:00 | Dhaanush | Rohith kumar.B | MKS00207 |
| 2026-10-06 | Tuesday | 19:00:00 | Dhaanush | V.D. THARUN ADITHYA | MKS00212 |
| 2026-10-06 | Tuesday | 19:00:00 | Dhaanush | Yuviga | MKS00107 |
| 2026-10-06 | Tuesday | 19:00:00 | Manikandan | Aaradheya P | MKS00225 |
| 2026-10-06 | Tuesday | 19:00:00 | Manikandan | S Mounitha | MKS00226 |
| 2026-10-06 | Tuesday | 19:00:00 | Manikandan | Sri Varshini | MKS00232 |
| 2026-10-06 | Tuesday | 19:00:00 | Prakash | B.AARAV NARAYAN | MKS00098 |
| 2026-10-06 | Tuesday | 19:00:00 | Prakash | M.Srisaran | MKS00186 |
| 2026-10-06 | Tuesday | 19:00:00 | Prakash | Madesh | MKS00194 |
| 2026-10-06 | Tuesday | 20:00:00 | Abinaya | BHAANAVI.V | MKS00189 |
| 2026-10-06 | Tuesday | 20:00:00 | Abinaya | Cholamithran BR | MKS00192 |
| 2026-10-06 | Tuesday | 20:00:00 | Abinaya | Jayasudhan | MKS00220 |
| 2026-10-06 | Tuesday | 20:00:00 | Abinaya | Nyvan | MKS00208 |
| 2026-10-06 | Tuesday | 20:00:00 | Abinaya | RITHIKNATH K.M | MKS00193 |
| 2026-10-06 | Tuesday | 20:00:00 | Abinaya | S.Kabilan | MKS00198 |
| 2026-10-06 | Tuesday | 20:00:00 | Abinaya | S.Kavirenu | MKS00199 |
| 2026-10-06 | Tuesday | 20:00:00 | Abinaya | Thenamilthan.S | MKS00200 |
| 2026-10-06 | Tuesday | 20:00:00 | Abinaya | Thiyashwar S | MKS00181 |
| 2026-10-06 | Tuesday | 20:00:00 | Bathri | A R Thatchiraa Shree | MKS00172 |
| 2026-10-06 | Tuesday | 20:00:00 | Bathri | C S Sharwin | MKS00197 |
| 2026-10-06 | Tuesday | 20:00:00 | Bathri | D R RAJAGOPALAN | MKS00176 |
| 2026-10-06 | Tuesday | 20:00:00 | Bathri | H V Kanishk | MKS00154 |
| 2026-10-06 | Tuesday | 20:00:00 | Bathri | J Jerwin | MKS00230 |
| 2026-10-06 | Tuesday | 20:00:00 | Bathri | Jeevith. N.M | MKS00224 |
| 2026-10-06 | Tuesday | 20:00:00 | Bathri | M VARUNESH PANDI | MKS00166 |
| 2026-10-06 | Tuesday | 20:00:00 | Bathri | Nishwanth R | MKS00171 |
| 2026-10-06 | Tuesday | 20:00:00 | Bathri | R Logeshwaran | MKS00222 |
| 2026-10-06 | Tuesday | 20:00:00 | Bathri | Ridhanya Sri.V | MKS00178 |
| 2026-10-06 | Tuesday | 20:00:00 | Bathri | S. Thashwin Raj | MKS00155 |
| 2026-10-06 | Tuesday | 20:00:00 | Bathri | S.P.NEHASRI | MKS00157 |
| 2026-10-06 | Tuesday | 20:00:00 | Dhaanush | Kamesh kumar c | MKS00231 |
| 2026-10-06 | Tuesday | 20:00:00 | Dhaanush | Krishiv Ajay | MKS00037 |
| 2026-10-06 | Tuesday | 20:00:00 | Dhaanush | Manikandan S | MKS00183 |
| 2026-10-06 | Tuesday | 20:00:00 | Dhaanush | Sai Eswar | MKS00132 |
| 2026-10-06 | Tuesday | 20:00:00 | Dhaanush | Samuel Rajan | MKS00182 |
| 2026-10-06 | Tuesday | 20:00:00 | Dhaanush | Selvakrishna RK | MKS00167 |
| 2026-10-06 | Tuesday | 20:00:00 | Dhaanush | Srikavi Bharathi | MKS00045 |
| 2026-10-06 | Tuesday | 20:00:00 | Dhaanush | Vivaan Aaditya | MKS00053 |
| 2026-10-06 | Tuesday | 20:00:00 | Prakash | Dev dharsan | MKS00142 |
| 2026-10-06 | Tuesday | 20:00:00 | Prakash | S R Sabeshwar | MKS00223 |
| 2026-10-07 | Wednesday | 06:00:00 | Bathri | Vaibhavi Krishna | MKS00164 |
| 2026-10-07 | Wednesday | 06:00:00 | Bathri | Vaishnavi Krishna | MKS00165 |
| 2026-10-07 | Wednesday | 06:00:00 | Manikandan | Priyan | MKS00162 |
| 2026-10-07 | Wednesday | 07:00:00 | Bathri | AATHISH S | MKS00229 |
| 2026-10-07 | Wednesday | 09:00:00 | Prakash | Alagu Durai | MKS00141 |
| 2026-10-07 | Wednesday | 16:30:00 | Bathri | Devansh gade | MKS00218 |
| 2026-10-07 | Wednesday | 17:00:00 | Bathri | Jovinya | MKS00075 |
| 2026-10-07 | Wednesday | 17:00:00 | Bathri | S.V.Kavisree | MKS00111 |
| 2026-10-07 | Wednesday | 18:00:00 | Bathri | Vikaesh | MKS00221 |
| 2026-10-07 | Wednesday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-07 | Wednesday | 18:00:00 | Dhaanush | Sarvin | MKS00060 |
| 2026-10-07 | Wednesday | 18:00:00 | Dhaanush | Vivaan Aaditya | MKS00053 |
| 2026-10-07 | Wednesday | 18:00:00 | Dhaanush | YAASHVIN A/L SATEESHKUMAR | MKS00065 |
| 2026-10-07 | Wednesday | 18:00:00 | Prakash | Kaashvi Prakash | MKS00184 |
| 2026-10-07 | Wednesday | 19:00:00 | Abinaya | A.Bavinesh | MKS00214 |
| 2026-10-07 | Wednesday | 19:00:00 | Abinaya | B.V.Tijesh | MKS00219 |
| 2026-10-07 | Wednesday | 19:00:00 | Abinaya | BHAANAVI.V | MKS00189 |
| 2026-10-07 | Wednesday | 19:00:00 | Abinaya | C.V.Chanvika | MKS00196 |
| 2026-10-07 | Wednesday | 19:00:00 | Abinaya | Cholamithran BR | MKS00192 |
| 2026-10-07 | Wednesday | 19:00:00 | Abinaya | N.Charan | MKS00148 |
| 2026-10-07 | Wednesday | 19:00:00 | Abinaya | RITHIKNATH K.M | MKS00193 |
| 2026-10-07 | Wednesday | 19:00:00 | Bathri | V. Dhaksha | MKS00110 |
| 2026-10-07 | Wednesday | 19:00:00 | Dhaanush | Arishmithran | MKS00072 |
| 2026-10-07 | Wednesday | 19:00:00 | Dhaanush | Hithesh | MKS00206 |
| 2026-10-07 | Wednesday | 19:00:00 | Dhaanush | Manikandan S | MKS00183 |
| 2026-10-07 | Wednesday | 19:00:00 | Dhaanush | Mohhan | MKS00064 |
| 2026-10-07 | Wednesday | 19:00:00 | Dhaanush | Praduksha | MKS00091 |
| 2026-10-07 | Wednesday | 19:00:00 | Dhaanush | S R Sabeshwar | MKS00223 |
| 2026-10-07 | Wednesday | 19:00:00 | Dhaanush | S.Raagavarshenee | MKS00009 |
| 2026-10-07 | Wednesday | 19:00:00 | Dhaanush | Sanjumithra | MKS00070 |
| 2026-10-07 | Wednesday | 19:00:00 | Dhaanush | Shakthivishakan A | MKS00034 |
| 2026-10-07 | Wednesday | 19:00:00 | Guru | Viraaj Shanmugam | MKS00153 |
| 2026-10-07 | Wednesday | 19:00:00 | Manikandan | S Mounitha | MKS00226 |
| 2026-10-07 | Wednesday | 19:00:00 | Prakash | Dev dharsan | MKS00142 |
| 2026-10-07 | Wednesday | 19:00:00 | Prakash | N.sri dharshni | MKS00055 |
| 2026-10-07 | Wednesday | 19:00:00 | Prakash | Oviya B | MKS00038 |
| 2026-10-07 | Wednesday | 19:00:00 | Saravanan | Diya | MKS00024 |
| 2026-10-07 | Wednesday | 19:00:00 | Saravanan | Hitesh prabu | MKS00014 |
| 2026-10-07 | Wednesday | 19:00:00 | Saravanan | M.Nishik | MKS00113 |
| 2026-10-07 | Wednesday | 19:00:00 | Saravanan | Mithran P | MKS00083 |
| 2026-10-07 | Wednesday | 19:00:00 | Saravanan | Samuel Rajan | MKS00182 |
| 2026-10-07 | Wednesday | 19:00:00 | Saravanan | Vedhanth V | MKS00102 |
| 2026-10-07 | Wednesday | 20:00:00 | Abinaya | Jayasudhan | MKS00220 |
| 2026-10-07 | Wednesday | 20:00:00 | Abinaya | Kavinth P | MKS00217 |
| 2026-10-07 | Wednesday | 20:00:00 | Abinaya | M.Srisaran | MKS00186 |
| 2026-10-07 | Wednesday | 20:00:00 | Abinaya | S.Kabilan | MKS00198 |
| 2026-10-07 | Wednesday | 20:00:00 | Abinaya | S.Kavirenu | MKS00199 |
| 2026-10-07 | Wednesday | 20:00:00 | Abinaya | Thenamilthan.S | MKS00200 |
| 2026-10-07 | Wednesday | 20:00:00 | Bathri | D KAVISH | MKS00079 |
| 2026-10-07 | Wednesday | 20:00:00 | Bathri | Dhanya
  sri S S | MKS00114 |
| 2026-10-07 | Wednesday | 20:00:00 | Bathri | M.Nalini Hirthika | MKS00118 |
| 2026-10-07 | Wednesday | 20:00:00 | Dhaanush | Kamesh kumar c | MKS00231 |
| 2026-10-07 | Wednesday | 20:00:00 | Dhaanush | Sai Eswar | MKS00132 |
| 2026-10-07 | Wednesday | 20:00:00 | Manikandan | M VARUNESH PANDI | MKS00166 |
| 2026-10-07 | Wednesday | 20:00:00 | Prakash | Madesh | MKS00194 |
| 2026-10-08 | Thursday | 06:00:00 | Bathri | Vedh Pabba | MKS00190 |
| 2026-10-08 | Thursday | 06:00:00 | Prakash | Kirthik | MKS00048 |
| 2026-10-08 | Thursday | 11:15:00 | Bathri | Vikaesh | MKS00221 |
| 2026-10-08 | Thursday | 17:00:00 | Dhaanush | P.V Subhiksha | MKS00150 |
| 2026-10-08 | Thursday | 17:30:00 | Arshath | Sachin | MKS00059 |
| 2026-10-08 | Thursday | 17:30:00 | Arshath | Sarvin | MKS00060 |
| 2026-10-08 | Thursday | 17:30:00 | Arshath | YAASHVIN A/L SATEESHKUMAR | MKS00065 |
| 2026-10-08 | Thursday | 18:00:00 | Bathri | Harini | MKS00073 |
| 2026-10-08 | Thursday | 18:00:00 | Bathri | MELWIN G | MKS00100 |
| 2026-10-08 | Thursday | 18:00:00 | Bathri | N.Charan | MKS00148 |
| 2026-10-08 | Thursday | 18:00:00 | Bathri | Oviya B | MKS00038 |
| 2026-10-08 | Thursday | 18:00:00 | Bathri | Sarvesh K | MKS00175 |
| 2026-10-08 | Thursday | 18:00:00 | Bathri | yaazhini | MKS00147 |
| 2026-10-08 | Thursday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-08 | Thursday | 18:00:00 | Dhaanush | Vivaan Aaditya | MKS00053 |
| 2026-10-08 | Thursday | 18:00:00 | Prakash | A.T.Vagish | MKS00149 |
| 2026-10-08 | Thursday | 18:00:00 | Prakash | Charvi | MKS00163 |
| 2026-10-08 | Thursday | 18:00:00 | Prakash | M. R. Darshan | MKS00101 |
| 2026-10-08 | Thursday | 18:00:00 | Prakash | Mithra sree A | MKS00161 |
| 2026-10-08 | Thursday | 18:00:00 | Prakash | Mithun Rajamani chakravarthi | MKS00112 |
| 2026-10-08 | Thursday | 18:00:00 | Prakash | Nitharsana | MKS00095 |
| 2026-10-08 | Thursday | 18:00:00 | Prakash | Rooban | MKS00215 |
| 2026-10-08 | Thursday | 19:00:00 | Bathri | N.sri dharshni | MKS00055 |
| 2026-10-08 | Thursday | 19:00:00 | Bathri | Syed Individual | MKS00076 |
| 2026-10-08 | Thursday | 19:00:00 | Bathri | V. Dhaksha | MKS00110 |
| 2026-10-08 | Thursday | 19:00:00 | Dhaanush | V.Dharmasastha Individual | MKS00093 |
| 2026-10-08 | Thursday | 19:00:00 | Manikandan | Bhavadharani.B | MKS00203 |
| 2026-10-08 | Thursday | 19:00:00 | Manikandan | J Jerwin | MKS00230 |
| 2026-10-08 | Thursday | 19:00:00 | Manikandan | Jeevith. N.M | MKS00224 |
| 2026-10-08 | Thursday | 19:00:00 | Manikandan | R Logeshwaran | MKS00222 |
| 2026-10-08 | Thursday | 19:00:00 | Prakash | B.AARAV NARAYAN | MKS00098 |
| 2026-10-08 | Thursday | 19:00:00 | Prakash | Madesh | MKS00194 |
| 2026-10-08 | Thursday | 20:00:00 | Abinaya | BHAANAVI.V | MKS00189 |
| 2026-10-08 | Thursday | 20:00:00 | Abinaya | Cholamithran BR | MKS00192 |
| 2026-10-08 | Thursday | 20:00:00 | Abinaya | Jayasudhan | MKS00220 |
| 2026-10-08 | Thursday | 20:00:00 | Abinaya | Nyvan | MKS00208 |
| 2026-10-08 | Thursday | 20:00:00 | Abinaya | RITHIKNATH K.M | MKS00193 |
| 2026-10-08 | Thursday | 20:00:00 | Abinaya | S.Kabilan | MKS00198 |
| 2026-10-08 | Thursday | 20:00:00 | Abinaya | S.Kavirenu | MKS00199 |
| 2026-10-08 | Thursday | 20:00:00 | Abinaya | Thenamilthan.S | MKS00200 |
| 2026-10-08 | Thursday | 20:00:00 | Abinaya | Thiyashwar S | MKS00181 |
| 2026-10-08 | Thursday | 20:00:00 | Bathri | C S Sharwin | MKS00197 |
| 2026-10-08 | Thursday | 20:00:00 | Bathri | D R RAJAGOPALAN | MKS00176 |
| 2026-10-08 | Thursday | 20:00:00 | Bathri | Nishwanth R | MKS00171 |
| 2026-10-08 | Thursday | 20:00:00 | Bathri | Ridhanya Sri.V | MKS00178 |
| 2026-10-08 | Thursday | 20:00:00 | Bathri | S. Thashwin Raj | MKS00155 |
| 2026-10-08 | Thursday | 20:00:00 | Bathri | Vikash | MKS00168 |
| 2026-10-08 | Thursday | 20:00:00 | Dhaanush | Kamesh kumar c | MKS00231 |
| 2026-10-08 | Thursday | 20:00:00 | Dhaanush | Sai Eswar | MKS00132 |
| 2026-10-08 | Thursday | 20:00:00 | Manikandan | Aaradheya P | MKS00225 |
| 2026-10-08 | Thursday | 20:00:00 | Manikandan | Sri Varshini | MKS00232 |
| 2026-10-08 | Thursday | 20:00:00 | Prakash | Dev dharsan | MKS00142 |
| 2026-10-08 | Thursday | 20:00:00 | Prakash | Jovinya | MKS00075 |
| 2026-10-08 | Thursday | 20:00:00 | Prakash | M VARUNESH PANDI | MKS00166 |
| 2026-10-09 | Friday | 06:00:00 | Bathri | Vedh Pabba | MKS00190 |
| 2026-10-09 | Friday | 06:00:00 | Manikandan | Priyan | MKS00162 |
| 2026-10-09 | Friday | 09:00:00 | Prakash | Alagu Durai | MKS00141 |
| 2026-10-09 | Friday | 11:00:00 | Bathri | Magizh | MKS00213 |
| 2026-10-09 | Friday | 17:00:00 | Bathri | Harri mithran P | MKS00210 |
| 2026-10-09 | Friday | 17:00:00 | Dhaanush | P.V Subhiksha | MKS00150 |
| 2026-10-09 | Friday | 17:30:00 | Arshath | Krishiv Ajay | MKS00037 |
| 2026-10-09 | Friday | 17:30:00 | Arshath | Sachin | MKS00059 |
| 2026-10-09 | Friday | 17:30:00 | Arshath | Sarvin | MKS00060 |
| 2026-10-09 | Friday | 17:30:00 | Arshath | Selvakrishna RK | MKS00167 |
| 2026-10-09 | Friday | 17:30:00 | Arshath | Srikavi Bharathi | MKS00045 |
| 2026-10-09 | Friday | 17:30:00 | Arshath | Vivaan Aaditya | MKS00053 |
| 2026-10-09 | Friday | 17:30:00 | Arshath | YAASHVIN A/L SATEESHKUMAR | MKS00065 |
| 2026-10-09 | Friday | 18:00:00 | Bathri | Jovinya | MKS00075 |
| 2026-10-09 | Friday | 18:00:00 | Bathri | S.V.Kavisree | MKS00111 |
| 2026-10-09 | Friday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-09 | Friday | 18:00:00 | Dhaanush | Thivya | MKS00056 |
| 2026-10-09 | Friday | 18:00:00 | Guru | Harini | MKS00073 |
| 2026-10-09 | Friday | 18:00:00 | Prakash | Sarvesh K | MKS00175 |
| 2026-10-09 | Friday | 19:00:00 | Abinaya | A.Bavinesh | MKS00214 |
| 2026-10-09 | Friday | 19:00:00 | Abinaya | B.V.Tijesh | MKS00219 |
| 2026-10-09 | Friday | 19:00:00 | Abinaya | C.V.Chanvika | MKS00196 |
| 2026-10-09 | Friday | 19:00:00 | Bathri | HAASHINI  SHRIVY V | MKS00115 |
| 2026-10-09 | Friday | 19:00:00 | Bathri | V. Dhaksha | MKS00110 |
| 2026-10-09 | Friday | 19:00:00 | Bathri | Vikaesh | MKS00221 |
| 2026-10-09 | Friday | 19:00:00 | Dhaanush | Abhijay | MKS00202 |
| 2026-10-09 | Friday | 19:00:00 | Dhaanush | Ayaan Haris | MKS00092 |
| 2026-10-09 | Friday | 19:00:00 | Dhaanush | B SARVESSH | MKS00108 |
| 2026-10-09 | Friday | 19:00:00 | Dhaanush | D. Tharun | MKS00127 |
| 2026-10-09 | Friday | 19:00:00 | Dhaanush | Nakshathra. C | MKS00227 |
| 2026-10-09 | Friday | 19:00:00 | Dhaanush | Rohith kumar.B | MKS00207 |
| 2026-10-09 | Friday | 19:00:00 | Dhaanush | V.D. THARUN ADITHYA | MKS00212 |
| 2026-10-09 | Friday | 19:00:00 | Dhaanush | V.Dharmasastha Individual | MKS00093 |
| 2026-10-09 | Friday | 19:00:00 | Dhaanush | Yuviga | MKS00107 |
| 2026-10-09 | Friday | 19:00:00 | Manikandan | S Mounitha | MKS00226 |
| 2026-10-09 | Friday | 19:00:00 | Prakash | A R Thatchiraa Shree | MKS00172 |
| 2026-10-09 | Friday | 19:00:00 | Prakash | H V Kanishk | MKS00154 |
| 2026-10-09 | Friday | 19:00:00 | Prakash | S. Thashwin Raj | MKS00155 |
| 2026-10-09 | Friday | 19:00:00 | Prakash | Vikash | MKS00168 |
| 2026-10-09 | Friday | 20:00:00 | Abinaya | Adhigan Amarnath | MKS00204 |
| 2026-10-09 | Friday | 20:00:00 | Abinaya | B.SAI SRI | MKS00211 |
| 2026-10-09 | Friday | 20:00:00 | Abinaya | Sudharshika | MKS00216 |
| 2026-10-09 | Friday | 20:00:00 | Bathri | D R RAJAGOPALAN | MKS00176 |
| 2026-10-09 | Friday | 20:00:00 | Bathri | MELWIN G | MKS00100 |
| 2026-10-09 | Friday | 20:00:00 | Bathri | N.Charan | MKS00148 |
| 2026-10-09 | Friday | 20:00:00 | Bathri | Nirupan | MKS00185 |
| 2026-10-09 | Friday | 20:00:00 | Bathri | Oviya B | MKS00038 |
| 2026-10-09 | Friday | 20:00:00 | Bathri | Ryan Stalin | MKS00007 |
| 2026-10-09 | Friday | 20:00:00 | Bathri | S. YASWANNTH | MKS00039 |
| 2026-10-09 | Friday | 20:00:00 | Bathri | S.P.NEHASRI | MKS00157 |
| 2026-10-09 | Friday | 20:00:00 | Bathri | yaazhini | MKS00147 |
| 2026-10-09 | Friday | 20:00:00 | Dhaanush | K. Sudhir | MKS00228 |
| 2026-10-09 | Friday | 20:00:00 | Dhaanush | KAVIBHARATHI P | MKS00201 |
| 2026-10-09 | Friday | 20:00:00 | Dhaanush | Kavinpriyan | MKS00023 |
| 2026-10-09 | Friday | 20:00:00 | Dhaanush | Keshav Krishna | YTC |
| 2026-10-09 | Friday | 20:00:00 | Dhaanush | M Nethran | MKS00020 |
| 2026-10-09 | Friday | 20:00:00 | Dhaanush | Pranith | MKS00143 |
| 2026-10-09 | Friday | 20:00:00 | Dhaanush | S R Sabeshwar | MKS00223 |
| 2026-10-09 | Friday | 20:00:00 | Dhaanush | Samuel Rajan | MKS00182 |
| 2026-10-09 | Friday | 20:00:00 | Dhaanush | V.Pranav | MKS00173 |
| 2026-10-09 | Friday | 20:00:00 | Guru | M VARUNESH PANDI | MKS00166 |
| 2026-10-09 | Friday | 20:00:00 | Manikandan | Bhavadharani.B | MKS00203 |
| 2026-10-09 | Friday | 20:00:00 | Manikandan | Dev dharsan | MKS00142 |
| 2026-10-09 | Friday | 20:00:00 | Manikandan | J Jerwin | MKS00230 |
| 2026-10-09 | Friday | 20:00:00 | Manikandan | Jayasudhan | MKS00220 |
| 2026-10-09 | Friday | 20:00:00 | Manikandan | Kavinth P | MKS00217 |
| 2026-10-09 | Friday | 20:00:00 | Prakash | Madesh | MKS00194 |
| 2026-10-09 | Friday | 20:00:00 | Prakash | Syed Individual | MKS00076 |
| 2026-10-10 | Saturday | 06:00:00 | Bathri | Pugazhini Navaneethan | MKS00156 |
| 2026-10-10 | Saturday | 06:00:00 | Prakash | Kirthik | MKS00048 |
| 2026-10-10 | Saturday | 10:00:00 | Abinaya | Aadhav Mithun | MKS00170 |
| 2026-10-10 | Saturday | 11:00:00 | Bathri | Akshadhasree | MKS00067 |
| 2026-10-10 | Saturday | 11:00:00 | Bathri | Anikha | MKS00066 |
| 2026-10-10 | Saturday | 12:15:00 | Bathri | Viraaj Shanmugam | MKS00153 |
| 2026-10-10 | Saturday | 17:00:00 | Arshath | Sachin | MKS00059 |
| 2026-10-10 | Saturday | 17:00:00 | Arshath | Vivaan Aaditya | MKS00053 |
| 2026-10-10 | Saturday | 17:00:00 | Dhaanush | Avyukt A Praveen | MKS00174 |
| 2026-10-10 | Saturday | 17:00:00 | Dhaanush | Manikandan S | MKS00183 |
| 2026-10-10 | Saturday | 17:00:00 | Dhaanush | Rohith kumar.B | MKS00207 |
| 2026-10-10 | Saturday | 17:00:00 | Dhaanush | V.D. THARUN ADITHYA | MKS00212 |
| 2026-10-10 | Saturday | 18:00:00 | Arshath | Krishiv Ajay | MKS00037 |
| 2026-10-10 | Saturday | 18:00:00 | Arshath | Sarvin | MKS00060 |
| 2026-10-10 | Saturday | 18:00:00 | Arshath | Selvakrishna RK | MKS00167 |
| 2026-10-10 | Saturday | 18:00:00 | Arshath | Srikavi Bharathi | MKS00045 |
| 2026-10-10 | Saturday | 18:00:00 | Arshath | YAASHVIN A/L SATEESHKUMAR | MKS00065 |
| 2026-10-10 | Saturday | 18:00:00 | Bathri | T L KANISHKAR | MKS00195 |
| 2026-10-10 | Saturday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-10 | Saturday | 18:00:00 | Dhaanush | Reyhan nawaz | MKS00049 |
| 2026-10-10 | Saturday | 18:00:00 | Dhaanush | Thivya | MKS00056 |
| 2026-10-10 | Saturday | 18:00:00 | Prakash | A.T.Vagish | MKS00149 |
| 2026-10-10 | Saturday | 18:00:00 | Prakash | Charvi | MKS00163 |
| 2026-10-10 | Saturday | 18:00:00 | Prakash | M. R. Darshan | MKS00101 |
| 2026-10-10 | Saturday | 18:00:00 | Prakash | Mithra sree A | MKS00161 |
| 2026-10-10 | Saturday | 18:00:00 | Prakash | Mithun Rajamani chakravarthi | MKS00112 |
| 2026-10-10 | Saturday | 18:00:00 | Prakash | Nitharsana | MKS00095 |
| 2026-10-10 | Saturday | 18:00:00 | Prakash | Oviya B | MKS00038 |
| 2026-10-10 | Saturday | 18:00:00 | Prakash | Rooban | MKS00215 |
| 2026-10-10 | Saturday | 19:00:00 | Abinaya | Adhigan Amarnath | MKS00204 |
| 2026-10-10 | Saturday | 19:00:00 | Abinaya | B.SAI SRI | MKS00211 |
| 2026-10-10 | Saturday | 19:00:00 | Abinaya | Sudharshika | MKS00216 |
| 2026-10-10 | Saturday | 19:00:00 | Bathri | Jovinya | MKS00075 |
| 2026-10-10 | Saturday | 19:00:00 | Bathri | S.V.Kavisree | MKS00111 |
| 2026-10-10 | Saturday | 19:00:00 | Bathri | Syed Individual | MKS00076 |
| 2026-10-10 | Saturday | 19:00:00 | Dhaanush | Arishmithran | MKS00072 |
| 2026-10-10 | Saturday | 19:00:00 | Dhaanush | Hithesh | MKS00206 |
| 2026-10-10 | Saturday | 19:00:00 | Dhaanush | Mohhan | MKS00064 |
| 2026-10-10 | Saturday | 19:00:00 | Dhaanush | Praduksha | MKS00091 |
| 2026-10-10 | Saturday | 19:00:00 | Dhaanush | S R Sabeshwar | MKS00223 |
| 2026-10-10 | Saturday | 19:00:00 | Dhaanush | S.Raagavarshenee | MKS00009 |
| 2026-10-10 | Saturday | 19:00:00 | Dhaanush | Sanjumithra | MKS00070 |
| 2026-10-10 | Saturday | 19:00:00 | Dhaanush | Shakthivishakan A | MKS00034 |
| 2026-10-10 | Saturday | 19:00:00 | Manikandan | Aaradheya P | MKS00225 |
| 2026-10-10 | Saturday | 19:00:00 | Manikandan | Bhavadharani.B | MKS00203 |
| 2026-10-10 | Saturday | 19:00:00 | Manikandan | Jayasudhan | MKS00220 |
| 2026-10-10 | Saturday | 19:00:00 | Manikandan | Kavinth P | MKS00217 |
| 2026-10-10 | Saturday | 19:00:00 | Manikandan | S Mounitha | MKS00226 |
| 2026-10-10 | Saturday | 19:00:00 | Manikandan | Sri Varshini | MKS00232 |
| 2026-10-10 | Saturday | 19:00:00 | Prakash | Ineya Individual | MKS00050 |
| 2026-10-10 | Saturday | 19:00:00 | Saravanan | Diya | MKS00024 |
| 2026-10-10 | Saturday | 19:00:00 | Saravanan | Hitesh prabu | MKS00014 |
| 2026-10-10 | Saturday | 19:00:00 | Saravanan | M.Nishik | MKS00113 |
| 2026-10-10 | Saturday | 19:00:00 | Saravanan | Mithran P | MKS00083 |
| 2026-10-10 | Saturday | 19:00:00 | Saravanan | Vedhanth V | MKS00102 |
| 2026-10-10 | Saturday | 20:00:00 | Bathri | A R Thatchiraa Shree | MKS00172 |
| 2026-10-10 | Saturday | 20:00:00 | Bathri | Abhijay | MKS00202 |
| 2026-10-10 | Saturday | 20:00:00 | Bathri | C S Sharwin | MKS00197 |
| 2026-10-10 | Saturday | 20:00:00 | Bathri | D R RAJAGOPALAN | MKS00176 |
| 2026-10-10 | Saturday | 20:00:00 | Bathri | H V Kanishk | MKS00154 |
| 2026-10-10 | Saturday | 20:00:00 | Bathri | Nishwanth R | MKS00171 |
| 2026-10-10 | Saturday | 20:00:00 | Bathri | Ridhanya Sri.V | MKS00178 |
| 2026-10-10 | Saturday | 20:00:00 | Bathri | S. Thashwin Raj | MKS00155 |
| 2026-10-10 | Saturday | 20:00:00 | Bathri | S.P.NEHASRI | MKS00157 |
| 2026-10-10 | Saturday | 20:00:00 | Bathri | Sarvesh K | MKS00175 |
| 2026-10-10 | Saturday | 20:00:00 | Bathri | Vikash | MKS00168 |
| 2026-10-10 | Saturday | 20:00:00 | Guru | D KAVISH | MKS00079 |
| 2026-10-10 | Saturday | 20:00:00 | Guru | Dhanya
  sri S S | MKS00114 |
| 2026-10-10 | Saturday | 20:00:00 | Guru | HAASHINI  SHRIVY V | MKS00115 |
| 2026-10-10 | Saturday | 20:00:00 | Guru | M.Nalini Hirthika | MKS00118 |
| 2026-10-10 | Saturday | 20:00:00 | Guru | Nirupan | MKS00185 |
| 2026-10-10 | Saturday | 20:00:00 | Guru | Ryan Stalin | MKS00007 |
| 2026-10-10 | Saturday | 20:00:00 | Guru | S. YASWANNTH | MKS00039 |
| 2026-10-10 | Saturday | 20:00:00 | Guru | V. Srikaviyazhini | MKS00131 |
| 2026-10-10 | Saturday | 20:00:00 | Manikandan | Dev dharsan | MKS00142 |
| 2026-10-10 | Saturday | 20:00:00 | Manikandan | M VARUNESH PANDI | MKS00166 |
| 2026-10-10 | Saturday | 20:00:00 | Prakash | B.AARAV NARAYAN | MKS00098 |
| 2026-10-10 | Saturday | 20:00:00 | Prakash | Madesh | MKS00194 |
| 2026-10-10 | Saturday | 20:00:00 | Prakash | N.Charan | MKS00148 |
| 2026-10-10 | Saturday | 21:00:00 | Bathri | Vaibhavi Krishna | MKS00164 |
| 2026-10-10 | Saturday | 21:00:00 | Bathri | Vaishnavi Krishna | MKS00165 |
| 2026-10-11 | Sunday | 09:00:00 | Bathri | Vikaesh | MKS00221 |
| 2026-10-11 | Sunday | 09:00:00 | Dhaanush | Kamesh kumar c | MKS00231 |
| 2026-10-11 | Sunday | 09:00:00 | Dhaanush | Sai Eswar | MKS00132 |
| 2026-10-11 | Sunday | 09:00:00 | Guru | Viraaj Shanmugam | MKS00153 |
| 2026-10-11 | Sunday | 10:00:00 | Abinaya | Aadhav Mithun | MKS00170 |
| 2026-10-11 | Sunday | 10:00:00 | Abinaya | Abhijay | MKS00202 |
| 2026-10-11 | Sunday | 10:00:00 | Abinaya | Ayaan Haris | MKS00092 |
| 2026-10-11 | Sunday | 10:00:00 | Abinaya | B SARVESSH | MKS00108 |
| 2026-10-11 | Sunday | 10:00:00 | Abinaya | B.AARAV NARAYAN | MKS00098 |
| 2026-10-11 | Sunday | 10:00:00 | Abinaya | D R RAJAGOPALAN | MKS00176 |
| 2026-10-11 | Sunday | 10:00:00 | Abinaya | D. Tharun | MKS00127 |
| 2026-10-11 | Sunday | 10:00:00 | Abinaya | K. Sudhir | MKS00228 |
| 2026-10-11 | Sunday | 10:00:00 | Abinaya | KAVIBHARATHI P | MKS00201 |
| 2026-10-11 | Sunday | 10:00:00 | Abinaya | Kavinpriyan | MKS00023 |
| 2026-10-11 | Sunday | 10:00:00 | Abinaya | Madesh | MKS00194 |
| 2026-10-11 | Sunday | 10:00:00 | Abinaya | Manikandan S | MKS00183 |
| 2026-10-11 | Sunday | 10:00:00 | Abinaya | Nakshathra. C | MKS00227 |
| 2026-10-11 | Sunday | 10:00:00 | Abinaya | Pranith | MKS00143 |
| 2026-10-11 | Sunday | 10:00:00 | Abinaya | Rohith kumar.B | MKS00207 |
| 2026-10-11 | Sunday | 10:00:00 | Abinaya | S R Sabeshwar | MKS00223 |
| 2026-10-11 | Sunday | 10:00:00 | Abinaya | S.Raagavarshenee | MKS00009 |
| 2026-10-11 | Sunday | 10:00:00 | Abinaya | V.D. THARUN ADITHYA | MKS00212 |
| 2026-10-11 | Sunday | 10:00:00 | Abinaya | V.Pranav | MKS00173 |
| 2026-10-11 | Sunday | 10:00:00 | Abinaya | Yuviga | MKS00107 |
| 2026-10-11 | Sunday | 10:00:00 | Arshath | Sachin | MKS00059 |
| 2026-10-11 | Sunday | 10:00:00 | Arshath | Vivaan Aaditya | MKS00053 |
| 2026-10-11 | Sunday | 10:00:00 | Dhaanush | Diya | MKS00024 |
| 2026-10-11 | Sunday | 10:00:00 | Dhaanush | M.Nishik | MKS00113 |
| 2026-10-11 | Sunday | 10:00:00 | Dhaanush | Mithran P | MKS00083 |
| 2026-10-11 | Sunday | 10:00:00 | Dhaanush | Reyhan nawaz | MKS00049 |
| 2026-10-11 | Sunday | 10:00:00 | Dhaanush | Sarvin | MKS00060 |
| 2026-10-11 | Sunday | 10:00:00 | Dhaanush | Selvakrishna RK | MKS00167 |
| 2026-10-11 | Sunday | 10:00:00 | Dhaanush | Srikavi Bharathi | MKS00045 |
| 2026-10-11 | Sunday | 10:00:00 | Dhaanush | Thivya | MKS00056 |
| 2026-10-11 | Sunday | 10:00:00 | Dhaanush | V.Dharmasastha Individual | MKS00093 |
| 2026-10-11 | Sunday | 10:00:00 | Dhaanush | Vedhanth V | MKS00102 |
| 2026-10-11 | Sunday | 10:00:00 | Hema | Arishmithran | MKS00072 |
| 2026-10-11 | Sunday | 10:00:00 | Hema | Hitesh prabu | MKS00014 |
| 2026-10-11 | Sunday | 10:00:00 | Hema | Hithesh | MKS00206 |
| 2026-10-11 | Sunday | 10:00:00 | Hema | Mohhan | MKS00064 |
| 2026-10-11 | Sunday | 10:00:00 | Hema | Praduksha | MKS00091 |
| 2026-10-11 | Sunday | 10:00:00 | Hema | Sanjumithra | MKS00070 |
| 2026-10-11 | Sunday | 10:00:00 | Hema | Shakthivishakan A | MKS00034 |
| 2026-10-11 | Sunday | 11:00:00 | Abinaya | Adhigan Amarnath | MKS00204 |
| 2026-10-11 | Sunday | 11:00:00 | Abinaya | B.SAI SRI | MKS00211 |
| 2026-10-11 | Sunday | 11:00:00 | Abinaya | BHAANAVI.V | MKS00189 |
| 2026-10-11 | Sunday | 11:00:00 | Abinaya | Bhavadharani.B | MKS00203 |
| 2026-10-11 | Sunday | 11:00:00 | Abinaya | Cholamithran BR | MKS00192 |
| 2026-10-11 | Sunday | 11:00:00 | Abinaya | Dev dharsan | MKS00142 |
| 2026-10-11 | Sunday | 11:00:00 | Abinaya | Jayasudhan | MKS00220 |
| 2026-10-11 | Sunday | 11:00:00 | Abinaya | Kavinth P | MKS00217 |
| 2026-10-11 | Sunday | 11:00:00 | Abinaya | M.Srisaran | MKS00186 |
| 2026-10-11 | Sunday | 11:00:00 | Abinaya | Nyvan | MKS00208 |
| 2026-10-11 | Sunday | 11:00:00 | Abinaya | RITHIKNATH K.M | MKS00193 |
| 2026-10-11 | Sunday | 11:00:00 | Abinaya | Rooban | MKS00215 |
| 2026-10-11 | Sunday | 11:00:00 | Abinaya | S.Kabilan | MKS00198 |
| 2026-10-11 | Sunday | 11:00:00 | Abinaya | S.Kavirenu | MKS00199 |
| 2026-10-11 | Sunday | 11:00:00 | Abinaya | S.P.NEHASRI | MKS00157 |
| 2026-10-11 | Sunday | 11:00:00 | Abinaya | Sudharshika | MKS00216 |
| 2026-10-11 | Sunday | 11:00:00 | Abinaya | Thenamilthan.S | MKS00200 |
| 2026-10-11 | Sunday | 11:00:00 | Abinaya | Thiyashwar S | MKS00181 |
| 2026-10-11 | Sunday | 11:00:00 | Arshath | Krishiv Ajay | MKS00037 |
| 2026-10-11 | Sunday | 11:00:00 | Arshath | YAASHVIN A/L SATEESHKUMAR | MKS00065 |
| 2026-10-11 | Sunday | 11:00:00 | Guru | A R Thatchiraa Shree | MKS00172 |
| 2026-10-11 | Sunday | 11:00:00 | Guru | A.T.Vagish | MKS00149 |
| 2026-10-11 | Sunday | 11:00:00 | Guru | Charvi | MKS00163 |
| 2026-10-11 | Sunday | 11:00:00 | Guru | D KAVISH | MKS00079 |
| 2026-10-11 | Sunday | 11:00:00 | Guru | Dhanya
  sri S S | MKS00114 |
| 2026-10-11 | Sunday | 11:00:00 | Guru | H V Kanishk | MKS00154 |
| 2026-10-11 | Sunday | 11:00:00 | Guru | HAASHINI  SHRIVY V | MKS00115 |
| 2026-10-11 | Sunday | 11:00:00 | Guru | M. R. Darshan | MKS00101 |
| 2026-10-11 | Sunday | 11:00:00 | Guru | M.Nalini Hirthika | MKS00118 |
| 2026-10-11 | Sunday | 11:00:00 | Guru | N.Charan | MKS00148 |
| 2026-10-11 | Sunday | 11:00:00 | Guru | Nirupan | MKS00185 |
| 2026-10-11 | Sunday | 11:00:00 | Guru | Nitharsana | MKS00095 |
| 2026-10-11 | Sunday | 11:00:00 | Guru | R Logeshwaran | MKS00222 |
| 2026-10-11 | Sunday | 11:00:00 | Guru | Ryan Stalin | MKS00007 |
| 2026-10-11 | Sunday | 11:00:00 | Guru | S. Thashwin Raj | MKS00155 |
| 2026-10-11 | Sunday | 11:00:00 | Guru | V. Srikaviyazhini | MKS00131 |
| 2026-10-11 | Sunday | 11:00:00 | Guru | Vikash | MKS00168 |
| 2026-10-11 | Sunday | 11:00:00 | Hema | Akshadhasree | MKS00067 |
| 2026-10-11 | Sunday | 11:00:00 | Hema | Anikha | MKS00066 |
| 2026-10-11 | Sunday | 11:00:00 | Hema | Avyukt A Praveen | MKS00174 |
| 2026-10-11 | Sunday | 11:00:00 | Hema | C S Sharwin | MKS00197 |
| 2026-10-11 | Sunday | 11:00:00 | Hema | Harini | MKS00073 |
| 2026-10-11 | Sunday | 11:00:00 | Hema | Keshav Krishna | YTC |
| 2026-10-11 | Sunday | 11:00:00 | Hema | M Nethran | MKS00020 |
| 2026-10-11 | Sunday | 11:00:00 | Hema | MELWIN G | MKS00100 |
| 2026-10-11 | Sunday | 11:00:00 | Hema | Mithra sree A | MKS00161 |
| 2026-10-11 | Sunday | 11:00:00 | Hema | Mithun Rajamani chakravarthi | MKS00112 |
| 2026-10-11 | Sunday | 11:00:00 | Hema | Oviya B | MKS00038 |
| 2026-10-11 | Sunday | 11:00:00 | Hema | Sarvesh K | MKS00175 |
| 2026-10-11 | Sunday | 11:00:00 | Hema | yaazhini | MKS00147 |
| 2026-10-11 | Sunday | 11:00:00 | Prakash | J Jerwin | MKS00230 |
| 2026-10-11 | Sunday | 13:30:00 | Abinaya | Jovinya | MKS00075 |
| 2026-10-11 | Sunday | 13:30:00 | Abinaya | M VARUNESH PANDI | MKS00166 |
| 2026-10-11 | Sunday | 13:30:00 | Abinaya | S.V.Kavisree | MKS00111 |
| 2026-10-11 | Sunday | 13:30:00 | Prakash | N.sri dharshni | MKS00055 |
| 2026-10-12 | Monday | 12:00:00 | Bathri | Bhavadharani.B | MKS00203 |
| 2026-10-12 | Monday | 12:00:00 | Bathri | Jeevith. N.M | MKS00224 |
| 2026-10-12 | Monday | 12:00:00 | Bathri | R Logeshwaran | MKS00222 |
| 2026-10-12 | Monday | 14:00:00 | Arshath | Krishiv Ajay | MKS00037 |
| 2026-10-12 | Monday | 14:00:00 | Arshath | M.Nishik | MKS00113 |
| 2026-10-12 | Monday | 14:00:00 | Arshath | Manikandan S | MKS00183 |
| 2026-10-12 | Monday | 14:00:00 | Arshath | Selvakrishna RK | MKS00167 |
| 2026-10-12 | Monday | 14:00:00 | Arshath | Srikavi Bharathi | MKS00045 |
| 2026-10-12 | Monday | 15:00:00 | Bathri | HAASHINI  SHRIVY V | MKS00115 |
| 2026-10-12 | Monday | 15:00:00 | Bathri | MELWIN G | MKS00100 |
| 2026-10-12 | Monday | 15:00:00 | Bathri | N.Charan | MKS00148 |
| 2026-10-12 | Monday | 15:00:00 | Bathri | yaazhini | MKS00147 |
| 2026-10-12 | Monday | 16:30:00 | Bathri | Devansh gade | MKS00218 |
| 2026-10-12 | Monday | 18:00:00 | Bathri | Vikaesh | MKS00221 |
| 2026-10-12 | Monday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-12 | Monday | 18:00:00 | Dhaanush | Sachin | MKS00059 |
| 2026-10-12 | Monday | 18:00:00 | Dhaanush | Vivaan Aaditya | MKS00053 |
| 2026-10-12 | Monday | 18:00:00 | Prakash | A.T.Vagish | MKS00149 |
| 2026-10-12 | Monday | 18:00:00 | Prakash | Akshadhasree | MKS00067 |
| 2026-10-12 | Monday | 18:00:00 | Prakash | Anikha | MKS00066 |
| 2026-10-12 | Monday | 18:00:00 | Prakash | C S Sharwin | MKS00197 |
| 2026-10-12 | Monday | 18:00:00 | Prakash | Charvi | MKS00163 |
| 2026-10-12 | Monday | 18:00:00 | Prakash | Harini | MKS00073 |
| 2026-10-12 | Monday | 18:00:00 | Prakash | M. R. Darshan | MKS00101 |
| 2026-10-12 | Monday | 18:00:00 | Prakash | Mithra sree A | MKS00161 |
| 2026-10-12 | Monday | 18:00:00 | Prakash | Mithun Rajamani chakravarthi | MKS00112 |
| 2026-10-12 | Monday | 18:00:00 | Prakash | Nitharsana | MKS00095 |
| 2026-10-12 | Monday | 18:00:00 | Prakash | Oviya B | MKS00038 |
| 2026-10-12 | Monday | 18:00:00 | Prakash | Rooban | MKS00215 |
| 2026-10-12 | Monday | 19:00:00 | Abinaya | A.Bavinesh | MKS00214 |
| 2026-10-12 | Monday | 19:00:00 | Abinaya | B.V.Tijesh | MKS00219 |
| 2026-10-12 | Monday | 19:00:00 | Abinaya | C.V.Chanvika | MKS00196 |
| 2026-10-12 | Monday | 19:00:00 | Bathri | V. Dhaksha | MKS00110 |
| 2026-10-12 | Monday | 19:00:00 | Dhaanush | Abhijay | MKS00202 |
| 2026-10-12 | Monday | 19:00:00 | Dhaanush | Ayaan Haris | MKS00092 |
| 2026-10-12 | Monday | 19:00:00 | Dhaanush | B SARVESSH | MKS00108 |
| 2026-10-12 | Monday | 19:00:00 | Dhaanush | D. Tharun | MKS00127 |
| 2026-10-12 | Monday | 19:00:00 | Dhaanush | Nakshathra. C | MKS00227 |
| 2026-10-12 | Monday | 19:00:00 | Dhaanush | Rohith kumar.B | MKS00207 |
| 2026-10-12 | Monday | 19:00:00 | Dhaanush | V.D. THARUN ADITHYA | MKS00212 |
| 2026-10-12 | Monday | 19:00:00 | Dhaanush | Yuviga | MKS00107 |
| 2026-10-12 | Monday | 19:00:00 | Manikandan | S Mounitha | MKS00226 |
| 2026-10-12 | Monday | 19:00:00 | Prakash | N.sri dharshni | MKS00055 |
| 2026-10-12 | Monday | 20:00:00 | Abinaya | Kavinth P | MKS00217 |
| 2026-10-12 | Monday | 20:00:00 | Abinaya | M.Srisaran | MKS00186 |
| 2026-10-12 | Monday | 20:00:00 | Abinaya | S.Kabilan | MKS00198 |
| 2026-10-12 | Monday | 20:00:00 | Abinaya | S.Kavirenu | MKS00199 |
| 2026-10-12 | Monday | 20:00:00 | Abinaya | Thenamilthan.S | MKS00200 |
| 2026-10-12 | Monday | 20:00:00 | Dhaanush | Hithesh | MKS00206 |
| 2026-10-12 | Monday | 20:00:00 | Dhaanush | K. Sudhir | MKS00228 |
| 2026-10-12 | Monday | 20:00:00 | Dhaanush | KAVIBHARATHI P | MKS00201 |
| 2026-10-12 | Monday | 20:00:00 | Dhaanush | Kavinpriyan | MKS00023 |
| 2026-10-12 | Monday | 20:00:00 | Dhaanush | Keshav Krishna | YTC |
| 2026-10-12 | Monday | 20:00:00 | Dhaanush | M Nethran | MKS00020 |
| 2026-10-12 | Monday | 20:00:00 | Dhaanush | Pranith | MKS00143 |
| 2026-10-12 | Monday | 20:00:00 | Dhaanush | V.Pranav | MKS00173 |
| 2026-10-12 | Monday | 20:00:00 | Guru | D KAVISH | MKS00079 |
| 2026-10-12 | Monday | 20:00:00 | Guru | Dhanya
  sri S S | MKS00114 |
| 2026-10-12 | Monday | 20:00:00 | Guru | M.Nalini Hirthika | MKS00118 |
| 2026-10-12 | Monday | 20:00:00 | Guru | Nirupan | MKS00185 |
| 2026-10-12 | Monday | 20:00:00 | Guru | Ryan Stalin | MKS00007 |
| 2026-10-12 | Monday | 20:00:00 | Guru | V. Srikaviyazhini | MKS00131 |
| 2026-10-12 | Monday | 20:00:00 | Manikandan | Dev dharsan | MKS00142 |
| 2026-10-12 | Monday | 20:00:00 | Manikandan | Jayasudhan | MKS00220 |
| 2026-10-12 | Monday | 20:00:00 | Manikandan | M VARUNESH PANDI | MKS00166 |
| 2026-10-13 | Tuesday | 06:00:00 | Bathri | Pugazhini Navaneethan | MKS00156 |
| 2026-10-13 | Tuesday | 06:00:00 | Prakash | Kirthik | MKS00048 |
| 2026-10-13 | Tuesday | 09:00:00 | Prakash | Alagu Durai | MKS00141 |
| 2026-10-13 | Tuesday | 11:00:00 | Bathri | Magizh | MKS00213 |
| 2026-10-13 | Tuesday | 17:00:00 | Bathri | Harri mithran P | MKS00210 |
| 2026-10-13 | Tuesday | 17:00:00 | Dhaanush | P.V Subhiksha | MKS00150 |
| 2026-10-13 | Tuesday | 18:00:00 | Bathri | Harini | MKS00073 |
| 2026-10-13 | Tuesday | 18:00:00 | Bathri | Jovinya | MKS00075 |
| 2026-10-13 | Tuesday | 18:00:00 | Bathri | MELWIN G | MKS00100 |
| 2026-10-13 | Tuesday | 18:00:00 | Bathri | S.V.Kavisree | MKS00111 |
| 2026-10-13 | Tuesday | 18:00:00 | Bathri | Sarvesh K | MKS00175 |
| 2026-10-13 | Tuesday | 18:00:00 | Bathri | yaazhini | MKS00147 |
| 2026-10-13 | Tuesday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-13 | Tuesday | 18:00:00 | Dhaanush | Reyhan nawaz | MKS00049 |
| 2026-10-13 | Tuesday | 18:00:00 | Dhaanush | Thivya | MKS00056 |
| 2026-10-13 | Tuesday | 18:00:00 | Prakash | HAASHINI  SHRIVY V | MKS00115 |
| 2026-10-13 | Tuesday | 18:00:00 | Prakash | Mithra sree A | MKS00161 |
| 2026-10-13 | Tuesday | 18:00:00 | Prakash | Mithun Rajamani chakravarthi | MKS00112 |
| 2026-10-13 | Tuesday | 18:00:00 | Prakash | Rooban | MKS00215 |
| 2026-10-13 | Tuesday | 19:00:00 | Abinaya | Adhigan Amarnath | MKS00204 |
| 2026-10-13 | Tuesday | 19:00:00 | Abinaya | B.SAI SRI | MKS00211 |
| 2026-10-13 | Tuesday | 19:00:00 | Abinaya | Bhavadharani.B | MKS00203 |
| 2026-10-13 | Tuesday | 19:00:00 | Abinaya | Sudharshika | MKS00216 |
| 2026-10-13 | Tuesday | 19:00:00 | Bathri | Syed Individual | MKS00076 |
| 2026-10-13 | Tuesday | 19:00:00 | Bathri | V. Dhaksha | MKS00110 |
| 2026-10-13 | Tuesday | 19:00:00 | Dhaanush | Abhijay | MKS00202 |
| 2026-10-13 | Tuesday | 19:00:00 | Dhaanush | Ayaan Haris | MKS00092 |
| 2026-10-13 | Tuesday | 19:00:00 | Dhaanush | B SARVESSH | MKS00108 |
| 2026-10-13 | Tuesday | 19:00:00 | Dhaanush | D. Tharun | MKS00127 |
| 2026-10-13 | Tuesday | 19:00:00 | Dhaanush | N.sri dharshni | MKS00055 |
| 2026-10-13 | Tuesday | 19:00:00 | Dhaanush | Nakshathra. C | MKS00227 |
| 2026-10-13 | Tuesday | 19:00:00 | Dhaanush | Rohith kumar.B | MKS00207 |
| 2026-10-13 | Tuesday | 19:00:00 | Dhaanush | V.D. THARUN ADITHYA | MKS00212 |
| 2026-10-13 | Tuesday | 19:00:00 | Dhaanush | Yuviga | MKS00107 |
| 2026-10-13 | Tuesday | 19:00:00 | Manikandan | S Mounitha | MKS00226 |
| 2026-10-13 | Tuesday | 19:00:00 | Prakash | B.AARAV NARAYAN | MKS00098 |
| 2026-10-13 | Tuesday | 19:00:00 | Prakash | M.Srisaran | MKS00186 |
| 2026-10-13 | Tuesday | 19:00:00 | Prakash | Madesh | MKS00194 |
| 2026-10-13 | Tuesday | 20:00:00 | Abinaya | BHAANAVI.V | MKS00189 |
| 2026-10-13 | Tuesday | 20:00:00 | Abinaya | Cholamithran BR | MKS00192 |
| 2026-10-13 | Tuesday | 20:00:00 | Abinaya | Nyvan | MKS00208 |
| 2026-10-13 | Tuesday | 20:00:00 | Abinaya | RITHIKNATH K.M | MKS00193 |
| 2026-10-13 | Tuesday | 20:00:00 | Abinaya | S.Kabilan | MKS00198 |
| 2026-10-13 | Tuesday | 20:00:00 | Abinaya | S.Kavirenu | MKS00199 |
| 2026-10-13 | Tuesday | 20:00:00 | Abinaya | Thenamilthan.S | MKS00200 |
| 2026-10-13 | Tuesday | 20:00:00 | Abinaya | Thiyashwar S | MKS00181 |
| 2026-10-13 | Tuesday | 20:00:00 | Bathri | A R Thatchiraa Shree | MKS00172 |
| 2026-10-13 | Tuesday | 20:00:00 | Bathri | C S Sharwin | MKS00197 |
| 2026-10-13 | Tuesday | 20:00:00 | Bathri | D R RAJAGOPALAN | MKS00176 |
| 2026-10-13 | Tuesday | 20:00:00 | Bathri | H V Kanishk | MKS00154 |
| 2026-10-13 | Tuesday | 20:00:00 | Bathri | Jeevith. N.M | MKS00224 |
| 2026-10-13 | Tuesday | 20:00:00 | Bathri | Nishwanth R | MKS00171 |
| 2026-10-13 | Tuesday | 20:00:00 | Bathri | R Logeshwaran | MKS00222 |
| 2026-10-13 | Tuesday | 20:00:00 | Bathri | Ridhanya Sri.V | MKS00178 |
| 2026-10-13 | Tuesday | 20:00:00 | Bathri | S. Thashwin Raj | MKS00155 |
| 2026-10-13 | Tuesday | 20:00:00 | Bathri | S.P.NEHASRI | MKS00157 |
| 2026-10-13 | Tuesday | 20:00:00 | Dhaanush | Kamesh kumar c | MKS00231 |
| 2026-10-13 | Tuesday | 20:00:00 | Dhaanush | Krishiv Ajay | MKS00037 |
| 2026-10-13 | Tuesday | 20:00:00 | Dhaanush | Manikandan S | MKS00183 |
| 2026-10-13 | Tuesday | 20:00:00 | Dhaanush | Sai Eswar | MKS00132 |
| 2026-10-13 | Tuesday | 20:00:00 | Dhaanush | Samuel Rajan | MKS00182 |
| 2026-10-13 | Tuesday | 20:00:00 | Dhaanush | Selvakrishna RK | MKS00167 |
| 2026-10-13 | Tuesday | 20:00:00 | Dhaanush | Srikavi Bharathi | MKS00045 |
| 2026-10-13 | Tuesday | 20:00:00 | Prakash | S R Sabeshwar | MKS00223 |
| 2026-10-14 | Wednesday | 06:00:00 | Bathri | Vaibhavi Krishna | MKS00164 |
| 2026-10-14 | Wednesday | 06:00:00 | Bathri | Vaishnavi Krishna | MKS00165 |
| 2026-10-14 | Wednesday | 06:00:00 | Manikandan | Priyan | MKS00162 |
| 2026-10-14 | Wednesday | 16:30:00 | Bathri | Devansh gade | MKS00218 |
| 2026-10-14 | Wednesday | 17:00:00 | Bathri | Jovinya | MKS00075 |
| 2026-10-14 | Wednesday | 17:00:00 | Bathri | S.V.Kavisree | MKS00111 |
| 2026-10-14 | Wednesday | 18:00:00 | Bathri | Vikaesh | MKS00221 |
| 2026-10-14 | Wednesday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-14 | Wednesday | 18:00:00 | Prakash | Kaashvi Prakash | MKS00184 |
| 2026-10-14 | Wednesday | 19:00:00 | Abinaya | A.Bavinesh | MKS00214 |
| 2026-10-14 | Wednesday | 19:00:00 | Abinaya | B.V.Tijesh | MKS00219 |
| 2026-10-14 | Wednesday | 19:00:00 | Abinaya | BHAANAVI.V | MKS00189 |
| 2026-10-14 | Wednesday | 19:00:00 | Abinaya | C.V.Chanvika | MKS00196 |
| 2026-10-14 | Wednesday | 19:00:00 | Abinaya | Cholamithran BR | MKS00192 |
| 2026-10-14 | Wednesday | 19:00:00 | Abinaya | RITHIKNATH K.M | MKS00193 |
| 2026-10-14 | Wednesday | 19:00:00 | Bathri | V. Dhaksha | MKS00110 |
| 2026-10-14 | Wednesday | 19:00:00 | Dhaanush | Arishmithran | MKS00072 |
| 2026-10-14 | Wednesday | 19:00:00 | Dhaanush | Hithesh | MKS00206 |
| 2026-10-14 | Wednesday | 19:00:00 | Dhaanush | Manikandan S | MKS00183 |
| 2026-10-14 | Wednesday | 19:00:00 | Dhaanush | Mohhan | MKS00064 |
| 2026-10-14 | Wednesday | 19:00:00 | Dhaanush | Praduksha | MKS00091 |
| 2026-10-14 | Wednesday | 19:00:00 | Dhaanush | S R Sabeshwar | MKS00223 |
| 2026-10-14 | Wednesday | 19:00:00 | Dhaanush | S.Raagavarshenee | MKS00009 |
| 2026-10-14 | Wednesday | 19:00:00 | Dhaanush | Sanjumithra | MKS00070 |
| 2026-10-14 | Wednesday | 19:00:00 | Dhaanush | Shakthivishakan A | MKS00034 |
| 2026-10-14 | Wednesday | 19:00:00 | Guru | Viraaj Shanmugam | MKS00153 |
| 2026-10-14 | Wednesday | 19:00:00 | Manikandan | S Mounitha | MKS00226 |
| 2026-10-14 | Wednesday | 19:00:00 | Prakash | N.sri dharshni | MKS00055 |
| 2026-10-14 | Wednesday | 19:00:00 | Prakash | Oviya B | MKS00038 |
| 2026-10-14 | Wednesday | 19:00:00 | Saravanan | Diya | MKS00024 |
| 2026-10-14 | Wednesday | 19:00:00 | Saravanan | Hitesh prabu | MKS00014 |
| 2026-10-14 | Wednesday | 19:00:00 | Saravanan | M.Nishik | MKS00113 |
| 2026-10-14 | Wednesday | 19:00:00 | Saravanan | Mithran P | MKS00083 |
| 2026-10-14 | Wednesday | 19:00:00 | Saravanan | Samuel Rajan | MKS00182 |
| 2026-10-14 | Wednesday | 19:00:00 | Saravanan | Vedhanth V | MKS00102 |
| 2026-10-14 | Wednesday | 20:00:00 | Abinaya | Kavinth P | MKS00217 |
| 2026-10-14 | Wednesday | 20:00:00 | Abinaya | M.Srisaran | MKS00186 |
| 2026-10-14 | Wednesday | 20:00:00 | Abinaya | S.Kabilan | MKS00198 |
| 2026-10-14 | Wednesday | 20:00:00 | Abinaya | S.Kavirenu | MKS00199 |
| 2026-10-14 | Wednesday | 20:00:00 | Abinaya | Thenamilthan.S | MKS00200 |
| 2026-10-14 | Wednesday | 20:00:00 | Bathri | D KAVISH | MKS00079 |
| 2026-10-14 | Wednesday | 20:00:00 | Bathri | Dhanya
  sri S S | MKS00114 |
| 2026-10-14 | Wednesday | 20:00:00 | Bathri | M.Nalini Hirthika | MKS00118 |
| 2026-10-14 | Wednesday | 20:00:00 | Dhaanush | Sai Eswar | MKS00132 |
| 2026-10-14 | Wednesday | 20:00:00 | Prakash | Madesh | MKS00194 |
| 2026-10-15 | Thursday | 06:00:00 | Bathri | Vedh Pabba | MKS00190 |
| 2026-10-15 | Thursday | 06:00:00 | Prakash | Kirthik | MKS00048 |
| 2026-10-15 | Thursday | 11:15:00 | Bathri | Vikaesh | MKS00221 |
| 2026-10-15 | Thursday | 17:00:00 | Dhaanush | P.V Subhiksha | MKS00150 |
| 2026-10-15 | Thursday | 17:30:00 | Arshath | Sachin | MKS00059 |
| 2026-10-15 | Thursday | 18:00:00 | Bathri | Harini | MKS00073 |
| 2026-10-15 | Thursday | 18:00:00 | Bathri | MELWIN G | MKS00100 |
| 2026-10-15 | Thursday | 18:00:00 | Bathri | Sarvesh K | MKS00175 |
| 2026-10-15 | Thursday | 18:00:00 | Bathri | yaazhini | MKS00147 |
| 2026-10-15 | Thursday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-15 | Thursday | 18:00:00 | Prakash | A.T.Vagish | MKS00149 |
| 2026-10-15 | Thursday | 18:00:00 | Prakash | Charvi | MKS00163 |
| 2026-10-15 | Thursday | 18:00:00 | Prakash | M. R. Darshan | MKS00101 |
| 2026-10-15 | Thursday | 18:00:00 | Prakash | Mithra sree A | MKS00161 |
| 2026-10-15 | Thursday | 18:00:00 | Prakash | Mithun Rajamani chakravarthi | MKS00112 |
| 2026-10-15 | Thursday | 18:00:00 | Prakash | Nitharsana | MKS00095 |
| 2026-10-15 | Thursday | 18:00:00 | Prakash | Rooban | MKS00215 |
| 2026-10-15 | Thursday | 19:00:00 | Bathri | N.sri dharshni | MKS00055 |
| 2026-10-15 | Thursday | 19:00:00 | Bathri | Syed Individual | MKS00076 |
| 2026-10-15 | Thursday | 19:00:00 | Bathri | V. Dhaksha | MKS00110 |
| 2026-10-15 | Thursday | 19:00:00 | Manikandan | Bhavadharani.B | MKS00203 |
| 2026-10-15 | Thursday | 19:00:00 | Manikandan | Jeevith. N.M | MKS00224 |
| 2026-10-15 | Thursday | 19:00:00 | Manikandan | R Logeshwaran | MKS00222 |
| 2026-10-15 | Thursday | 19:00:00 | Prakash | B.AARAV NARAYAN | MKS00098 |
| 2026-10-15 | Thursday | 19:00:00 | Prakash | Madesh | MKS00194 |
| 2026-10-15 | Thursday | 20:00:00 | Abinaya | BHAANAVI.V | MKS00189 |
| 2026-10-15 | Thursday | 20:00:00 | Abinaya | Cholamithran BR | MKS00192 |
| 2026-10-15 | Thursday | 20:00:00 | Abinaya | Nyvan | MKS00208 |
| 2026-10-15 | Thursday | 20:00:00 | Abinaya | RITHIKNATH K.M | MKS00193 |
| 2026-10-15 | Thursday | 20:00:00 | Abinaya | S.Kabilan | MKS00198 |
| 2026-10-15 | Thursday | 20:00:00 | Abinaya | S.Kavirenu | MKS00199 |
| 2026-10-15 | Thursday | 20:00:00 | Abinaya | Thenamilthan.S | MKS00200 |
| 2026-10-15 | Thursday | 20:00:00 | Abinaya | Thiyashwar S | MKS00181 |
| 2026-10-15 | Thursday | 20:00:00 | Bathri | C S Sharwin | MKS00197 |
| 2026-10-15 | Thursday | 20:00:00 | Bathri | D R RAJAGOPALAN | MKS00176 |
| 2026-10-15 | Thursday | 20:00:00 | Bathri | Nishwanth R | MKS00171 |
| 2026-10-15 | Thursday | 20:00:00 | Bathri | Ridhanya Sri.V | MKS00178 |
| 2026-10-15 | Thursday | 20:00:00 | Bathri | S. Thashwin Raj | MKS00155 |
| 2026-10-15 | Thursday | 20:00:00 | Bathri | Vikash | MKS00168 |
| 2026-10-15 | Thursday | 20:00:00 | Dhaanush | Sai Eswar | MKS00132 |
| 2026-10-16 | Friday | 06:00:00 | Bathri | Vedh Pabba | MKS00190 |
| 2026-10-16 | Friday | 06:00:00 | Manikandan | Priyan | MKS00162 |
| 2026-10-16 | Friday | 11:00:00 | Bathri | Magizh | MKS00213 |
| 2026-10-16 | Friday | 17:00:00 | Bathri | Harri mithran P | MKS00210 |
| 2026-10-16 | Friday | 17:00:00 | Dhaanush | P.V Subhiksha | MKS00150 |
| 2026-10-16 | Friday | 17:30:00 | Arshath | Krishiv Ajay | MKS00037 |
| 2026-10-16 | Friday | 17:30:00 | Arshath | Sachin | MKS00059 |
| 2026-10-16 | Friday | 17:30:00 | Arshath | Selvakrishna RK | MKS00167 |
| 2026-10-16 | Friday | 17:30:00 | Arshath | Srikavi Bharathi | MKS00045 |
| 2026-10-16 | Friday | 18:00:00 | Bathri | S.V.Kavisree | MKS00111 |
| 2026-10-16 | Friday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-16 | Friday | 18:00:00 | Dhaanush | Thivya | MKS00056 |
| 2026-10-16 | Friday | 18:00:00 | Guru | Harini | MKS00073 |
| 2026-10-16 | Friday | 18:00:00 | Prakash | Sarvesh K | MKS00175 |
| 2026-10-16 | Friday | 19:00:00 | Abinaya | A.Bavinesh | MKS00214 |
| 2026-10-16 | Friday | 19:00:00 | Abinaya | B.V.Tijesh | MKS00219 |
| 2026-10-16 | Friday | 19:00:00 | Abinaya | C.V.Chanvika | MKS00196 |
| 2026-10-16 | Friday | 19:00:00 | Bathri | Vikaesh | MKS00221 |
| 2026-10-16 | Friday | 19:00:00 | Dhaanush | Abhijay | MKS00202 |
| 2026-10-16 | Friday | 19:00:00 | Dhaanush | Ayaan Haris | MKS00092 |
| 2026-10-16 | Friday | 19:00:00 | Dhaanush | B SARVESSH | MKS00108 |
| 2026-10-16 | Friday | 19:00:00 | Dhaanush | D. Tharun | MKS00127 |
| 2026-10-16 | Friday | 19:00:00 | Dhaanush | Nakshathra. C | MKS00227 |
| 2026-10-16 | Friday | 19:00:00 | Dhaanush | Rohith kumar.B | MKS00207 |
| 2026-10-16 | Friday | 19:00:00 | Dhaanush | V.D. THARUN ADITHYA | MKS00212 |
| 2026-10-16 | Friday | 19:00:00 | Dhaanush | Yuviga | MKS00107 |
| 2026-10-16 | Friday | 19:00:00 | Manikandan | S Mounitha | MKS00226 |
| 2026-10-16 | Friday | 19:00:00 | Prakash | A R Thatchiraa Shree | MKS00172 |
| 2026-10-16 | Friday | 19:00:00 | Prakash | H V Kanishk | MKS00154 |
| 2026-10-16 | Friday | 19:00:00 | Prakash | S. Thashwin Raj | MKS00155 |
| 2026-10-16 | Friday | 19:00:00 | Prakash | Vikash | MKS00168 |
| 2026-10-16 | Friday | 20:00:00 | Abinaya | Adhigan Amarnath | MKS00204 |
| 2026-10-16 | Friday | 20:00:00 | Abinaya | B.SAI SRI | MKS00211 |
| 2026-10-16 | Friday | 20:00:00 | Abinaya | Sudharshika | MKS00216 |
| 2026-10-16 | Friday | 20:00:00 | Bathri | D R RAJAGOPALAN | MKS00176 |
| 2026-10-16 | Friday | 20:00:00 | Bathri | MELWIN G | MKS00100 |
| 2026-10-16 | Friday | 20:00:00 | Bathri | Nirupan | MKS00185 |
| 2026-10-16 | Friday | 20:00:00 | Bathri | Ryan Stalin | MKS00007 |
| 2026-10-16 | Friday | 20:00:00 | Bathri | S. YASWANNTH | MKS00039 |
| 2026-10-16 | Friday | 20:00:00 | Bathri | S.P.NEHASRI | MKS00157 |
| 2026-10-16 | Friday | 20:00:00 | Bathri | yaazhini | MKS00147 |
| 2026-10-16 | Friday | 20:00:00 | Dhaanush | K. Sudhir | MKS00228 |
| 2026-10-16 | Friday | 20:00:00 | Dhaanush | KAVIBHARATHI P | MKS00201 |
| 2026-10-16 | Friday | 20:00:00 | Dhaanush | Kavinpriyan | MKS00023 |
| 2026-10-16 | Friday | 20:00:00 | Dhaanush | Keshav Krishna | YTC |
| 2026-10-16 | Friday | 20:00:00 | Dhaanush | M Nethran | MKS00020 |
| 2026-10-16 | Friday | 20:00:00 | Dhaanush | Pranith | MKS00143 |
| 2026-10-16 | Friday | 20:00:00 | Dhaanush | S R Sabeshwar | MKS00223 |
| 2026-10-16 | Friday | 20:00:00 | Dhaanush | Samuel Rajan | MKS00182 |
| 2026-10-16 | Friday | 20:00:00 | Dhaanush | V.Pranav | MKS00173 |
| 2026-10-16 | Friday | 20:00:00 | Manikandan | Kavinth P | MKS00217 |
| 2026-10-16 | Friday | 20:00:00 | Prakash | Madesh | MKS00194 |
| 2026-10-16 | Friday | 20:00:00 | Prakash | Syed Individual | MKS00076 |
| 2026-10-17 | Saturday | 06:00:00 | Bathri | Pugazhini Navaneethan | MKS00156 |
| 2026-10-17 | Saturday | 06:00:00 | Prakash | Kirthik | MKS00048 |
| 2026-10-17 | Saturday | 10:00:00 | Abinaya | Aadhav Mithun | MKS00170 |
| 2026-10-17 | Saturday | 11:00:00 | Bathri | Akshadhasree | MKS00067 |
| 2026-10-17 | Saturday | 11:00:00 | Bathri | Anikha | MKS00066 |
| 2026-10-17 | Saturday | 12:15:00 | Bathri | Viraaj Shanmugam | MKS00153 |
| 2026-10-17 | Saturday | 17:00:00 | Dhaanush | Avyukt A Praveen | MKS00174 |
| 2026-10-17 | Saturday | 17:00:00 | Dhaanush | Manikandan S | MKS00183 |
| 2026-10-17 | Saturday | 17:00:00 | Dhaanush | Rohith kumar.B | MKS00207 |
| 2026-10-17 | Saturday | 17:00:00 | Dhaanush | V.D. THARUN ADITHYA | MKS00212 |
| 2026-10-17 | Saturday | 18:00:00 | Arshath | Krishiv Ajay | MKS00037 |
| 2026-10-17 | Saturday | 18:00:00 | Arshath | Selvakrishna RK | MKS00167 |
| 2026-10-17 | Saturday | 18:00:00 | Arshath | Srikavi Bharathi | MKS00045 |
| 2026-10-17 | Saturday | 18:00:00 | Bathri | T L KANISHKAR | MKS00195 |
| 2026-10-17 | Saturday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-17 | Saturday | 18:00:00 | Dhaanush | Reyhan nawaz | MKS00049 |
| 2026-10-17 | Saturday | 18:00:00 | Dhaanush | Thivya | MKS00056 |
| 2026-10-17 | Saturday | 18:00:00 | Prakash | A.T.Vagish | MKS00149 |
| 2026-10-17 | Saturday | 18:00:00 | Prakash | Charvi | MKS00163 |
| 2026-10-17 | Saturday | 18:00:00 | Prakash | M. R. Darshan | MKS00101 |
| 2026-10-17 | Saturday | 18:00:00 | Prakash | Mithra sree A | MKS00161 |
| 2026-10-17 | Saturday | 18:00:00 | Prakash | Mithun Rajamani chakravarthi | MKS00112 |
| 2026-10-17 | Saturday | 18:00:00 | Prakash | Nitharsana | MKS00095 |
| 2026-10-17 | Saturday | 18:00:00 | Prakash | Rooban | MKS00215 |
| 2026-10-17 | Saturday | 19:00:00 | Abinaya | Adhigan Amarnath | MKS00204 |
| 2026-10-17 | Saturday | 19:00:00 | Abinaya | B.SAI SRI | MKS00211 |
| 2026-10-17 | Saturday | 19:00:00 | Abinaya | Sudharshika | MKS00216 |
| 2026-10-17 | Saturday | 19:00:00 | Bathri | S.V.Kavisree | MKS00111 |
| 2026-10-17 | Saturday | 19:00:00 | Dhaanush | Arishmithran | MKS00072 |
| 2026-10-17 | Saturday | 19:00:00 | Dhaanush | Hithesh | MKS00206 |
| 2026-10-17 | Saturday | 19:00:00 | Dhaanush | Mohhan | MKS00064 |
| 2026-10-17 | Saturday | 19:00:00 | Dhaanush | Praduksha | MKS00091 |
| 2026-10-17 | Saturday | 19:00:00 | Dhaanush | S R Sabeshwar | MKS00223 |
| 2026-10-17 | Saturday | 19:00:00 | Dhaanush | S.Raagavarshenee | MKS00009 |
| 2026-10-17 | Saturday | 19:00:00 | Dhaanush | Sanjumithra | MKS00070 |
| 2026-10-17 | Saturday | 19:00:00 | Dhaanush | Shakthivishakan A | MKS00034 |
| 2026-10-17 | Saturday | 19:00:00 | Manikandan | Kavinth P | MKS00217 |
| 2026-10-17 | Saturday | 19:00:00 | Prakash | Ineya Individual | MKS00050 |
| 2026-10-17 | Saturday | 19:00:00 | Saravanan | Diya | MKS00024 |
| 2026-10-17 | Saturday | 19:00:00 | Saravanan | Hitesh prabu | MKS00014 |
| 2026-10-17 | Saturday | 19:00:00 | Saravanan | M.Nishik | MKS00113 |
| 2026-10-17 | Saturday | 19:00:00 | Saravanan | Mithran P | MKS00083 |
| 2026-10-17 | Saturday | 19:00:00 | Saravanan | Vedhanth V | MKS00102 |
| 2026-10-17 | Saturday | 20:00:00 | Bathri | A R Thatchiraa Shree | MKS00172 |
| 2026-10-17 | Saturday | 20:00:00 | Bathri | Abhijay | MKS00202 |
| 2026-10-17 | Saturday | 20:00:00 | Bathri | C S Sharwin | MKS00197 |
| 2026-10-17 | Saturday | 20:00:00 | Bathri | H V Kanishk | MKS00154 |
| 2026-10-17 | Saturday | 20:00:00 | Bathri | Nishwanth R | MKS00171 |
| 2026-10-17 | Saturday | 20:00:00 | Bathri | Ridhanya Sri.V | MKS00178 |
| 2026-10-17 | Saturday | 20:00:00 | Bathri | S. Thashwin Raj | MKS00155 |
| 2026-10-17 | Saturday | 20:00:00 | Bathri | S.P.NEHASRI | MKS00157 |
| 2026-10-17 | Saturday | 20:00:00 | Bathri | Vikash | MKS00168 |
| 2026-10-17 | Saturday | 20:00:00 | Guru | D KAVISH | MKS00079 |
| 2026-10-17 | Saturday | 20:00:00 | Guru | Dhanya
  sri S S | MKS00114 |
| 2026-10-17 | Saturday | 20:00:00 | Guru | M.Nalini Hirthika | MKS00118 |
| 2026-10-17 | Saturday | 20:00:00 | Guru | Nirupan | MKS00185 |
| 2026-10-17 | Saturday | 20:00:00 | Guru | Ryan Stalin | MKS00007 |
| 2026-10-17 | Saturday | 20:00:00 | Guru | S. YASWANNTH | MKS00039 |
| 2026-10-17 | Saturday | 20:00:00 | Guru | V. Srikaviyazhini | MKS00131 |
| 2026-10-17 | Saturday | 20:00:00 | Prakash | B.AARAV NARAYAN | MKS00098 |
| 2026-10-17 | Saturday | 20:00:00 | Prakash | Madesh | MKS00194 |
| 2026-10-17 | Saturday | 21:00:00 | Bathri | Vaibhavi Krishna | MKS00164 |
| 2026-10-17 | Saturday | 21:00:00 | Bathri | Vaishnavi Krishna | MKS00165 |
| 2026-10-18 | Sunday | 09:00:00 | Dhaanush | Sai Eswar | MKS00132 |
| 2026-10-18 | Sunday | 09:00:00 | Guru | Viraaj Shanmugam | MKS00153 |
| 2026-10-18 | Sunday | 10:00:00 | Abinaya | Abhijay | MKS00202 |
| 2026-10-18 | Sunday | 10:00:00 | Abinaya | Ayaan Haris | MKS00092 |
| 2026-10-18 | Sunday | 10:00:00 | Abinaya | B SARVESSH | MKS00108 |
| 2026-10-18 | Sunday | 10:00:00 | Abinaya | B.AARAV NARAYAN | MKS00098 |
| 2026-10-18 | Sunday | 10:00:00 | Abinaya | D. Tharun | MKS00127 |
| 2026-10-18 | Sunday | 10:00:00 | Abinaya | K. Sudhir | MKS00228 |
| 2026-10-18 | Sunday | 10:00:00 | Abinaya | KAVIBHARATHI P | MKS00201 |
| 2026-10-18 | Sunday | 10:00:00 | Abinaya | Kavinpriyan | MKS00023 |
| 2026-10-18 | Sunday | 10:00:00 | Abinaya | Manikandan S | MKS00183 |
| 2026-10-18 | Sunday | 10:00:00 | Abinaya | Nakshathra. C | MKS00227 |
| 2026-10-18 | Sunday | 10:00:00 | Abinaya | Pranith | MKS00143 |
| 2026-10-18 | Sunday | 10:00:00 | Abinaya | Rohith kumar.B | MKS00207 |
| 2026-10-18 | Sunday | 10:00:00 | Abinaya | S.Raagavarshenee | MKS00009 |
| 2026-10-18 | Sunday | 10:00:00 | Abinaya | V.Pranav | MKS00173 |
| 2026-10-18 | Sunday | 10:00:00 | Abinaya | Yuviga | MKS00107 |
| 2026-10-18 | Sunday | 10:00:00 | Dhaanush | Diya | MKS00024 |
| 2026-10-18 | Sunday | 10:00:00 | Dhaanush | M.Nishik | MKS00113 |
| 2026-10-18 | Sunday | 10:00:00 | Dhaanush | Mithran P | MKS00083 |
| 2026-10-18 | Sunday | 10:00:00 | Dhaanush | Reyhan nawaz | MKS00049 |
| 2026-10-18 | Sunday | 10:00:00 | Dhaanush | Srikavi Bharathi | MKS00045 |
| 2026-10-18 | Sunday | 10:00:00 | Dhaanush | Thivya | MKS00056 |
| 2026-10-18 | Sunday | 10:00:00 | Dhaanush | Vedhanth V | MKS00102 |
| 2026-10-18 | Sunday | 10:00:00 | Hema | Arishmithran | MKS00072 |
| 2026-10-18 | Sunday | 10:00:00 | Hema | Hitesh prabu | MKS00014 |
| 2026-10-18 | Sunday | 10:00:00 | Hema | Hithesh | MKS00206 |
| 2026-10-18 | Sunday | 10:00:00 | Hema | Mohhan | MKS00064 |
| 2026-10-18 | Sunday | 10:00:00 | Hema | Praduksha | MKS00091 |
| 2026-10-18 | Sunday | 10:00:00 | Hema | Sanjumithra | MKS00070 |
| 2026-10-18 | Sunday | 10:00:00 | Hema | Shakthivishakan A | MKS00034 |
| 2026-10-18 | Sunday | 11:00:00 | Abinaya | Adhigan Amarnath | MKS00204 |
| 2026-10-18 | Sunday | 11:00:00 | Abinaya | B.SAI SRI | MKS00211 |
| 2026-10-18 | Sunday | 11:00:00 | Abinaya | BHAANAVI.V | MKS00189 |
| 2026-10-18 | Sunday | 11:00:00 | Abinaya | Cholamithran BR | MKS00192 |
| 2026-10-18 | Sunday | 11:00:00 | Abinaya | M.Srisaran | MKS00186 |
| 2026-10-18 | Sunday | 11:00:00 | Abinaya | Nyvan | MKS00208 |
| 2026-10-18 | Sunday | 11:00:00 | Abinaya | RITHIKNATH K.M | MKS00193 |
| 2026-10-18 | Sunday | 11:00:00 | Abinaya | S.Kabilan | MKS00198 |
| 2026-10-18 | Sunday | 11:00:00 | Abinaya | S.Kavirenu | MKS00199 |
| 2026-10-18 | Sunday | 11:00:00 | Abinaya | S.P.NEHASRI | MKS00157 |
| 2026-10-18 | Sunday | 11:00:00 | Abinaya | Sudharshika | MKS00216 |
| 2026-10-18 | Sunday | 11:00:00 | Abinaya | Thenamilthan.S | MKS00200 |
| 2026-10-18 | Sunday | 11:00:00 | Abinaya | Thiyashwar S | MKS00181 |
| 2026-10-18 | Sunday | 11:00:00 | Guru | A R Thatchiraa Shree | MKS00172 |
| 2026-10-18 | Sunday | 11:00:00 | Guru | A.T.Vagish | MKS00149 |
| 2026-10-18 | Sunday | 11:00:00 | Guru | Charvi | MKS00163 |
| 2026-10-18 | Sunday | 11:00:00 | Guru | D KAVISH | MKS00079 |
| 2026-10-18 | Sunday | 11:00:00 | Guru | Dhanya
  sri S S | MKS00114 |
| 2026-10-18 | Sunday | 11:00:00 | Guru | H V Kanishk | MKS00154 |
| 2026-10-18 | Sunday | 11:00:00 | Guru | M. R. Darshan | MKS00101 |
| 2026-10-18 | Sunday | 11:00:00 | Guru | M.Nalini Hirthika | MKS00118 |
| 2026-10-18 | Sunday | 11:00:00 | Guru | Nirupan | MKS00185 |
| 2026-10-18 | Sunday | 11:00:00 | Guru | Nitharsana | MKS00095 |
| 2026-10-18 | Sunday | 11:00:00 | Guru | R Logeshwaran | MKS00222 |
| 2026-10-18 | Sunday | 11:00:00 | Guru | Ryan Stalin | MKS00007 |
| 2026-10-18 | Sunday | 11:00:00 | Guru | V. Srikaviyazhini | MKS00131 |
| 2026-10-18 | Sunday | 11:00:00 | Guru | Vikash | MKS00168 |
| 2026-10-18 | Sunday | 11:00:00 | Hema | Akshadhasree | MKS00067 |
| 2026-10-18 | Sunday | 11:00:00 | Hema | Anikha | MKS00066 |
| 2026-10-18 | Sunday | 11:00:00 | Hema | Avyukt A Praveen | MKS00174 |
| 2026-10-18 | Sunday | 11:00:00 | Hema | C S Sharwin | MKS00197 |
| 2026-10-18 | Sunday | 11:00:00 | Hema | Keshav Krishna | YTC |
| 2026-10-18 | Sunday | 11:00:00 | Hema | M Nethran | MKS00020 |
| 2026-10-18 | Sunday | 13:30:00 | Prakash | N.sri dharshni | MKS00055 |
| 2026-10-19 | Monday | 12:00:00 | Bathri | Jeevith. N.M | MKS00224 |
| 2026-10-19 | Monday | 12:00:00 | Bathri | R Logeshwaran | MKS00222 |
| 2026-10-19 | Monday | 14:00:00 | Arshath | M.Nishik | MKS00113 |
| 2026-10-19 | Monday | 14:00:00 | Arshath | Manikandan S | MKS00183 |
| 2026-10-19 | Monday | 14:00:00 | Arshath | Srikavi Bharathi | MKS00045 |
| 2026-10-19 | Monday | 16:30:00 | Bathri | Devansh gade | MKS00218 |
| 2026-10-19 | Monday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-19 | Monday | 18:00:00 | Prakash | A.T.Vagish | MKS00149 |
| 2026-10-19 | Monday | 18:00:00 | Prakash | Charvi | MKS00163 |
| 2026-10-19 | Monday | 18:00:00 | Prakash | M. R. Darshan | MKS00101 |
| 2026-10-19 | Monday | 18:00:00 | Prakash | Nitharsana | MKS00095 |
| 2026-10-19 | Monday | 19:00:00 | Abinaya | A.Bavinesh | MKS00214 |
| 2026-10-19 | Monday | 19:00:00 | Abinaya | B.V.Tijesh | MKS00219 |
| 2026-10-19 | Monday | 19:00:00 | Abinaya | C.V.Chanvika | MKS00196 |
| 2026-10-19 | Monday | 19:00:00 | Dhaanush | Ayaan Haris | MKS00092 |
| 2026-10-19 | Monday | 19:00:00 | Dhaanush | B SARVESSH | MKS00108 |
| 2026-10-19 | Monday | 19:00:00 | Dhaanush | D. Tharun | MKS00127 |
| 2026-10-19 | Monday | 19:00:00 | Dhaanush | Rohith kumar.B | MKS00207 |
| 2026-10-19 | Monday | 19:00:00 | Dhaanush | Yuviga | MKS00107 |
| 2026-10-19 | Monday | 20:00:00 | Abinaya | M.Srisaran | MKS00186 |
| 2026-10-19 | Monday | 20:00:00 | Dhaanush | Hithesh | MKS00206 |
| 2026-10-19 | Monday | 20:00:00 | Dhaanush | K. Sudhir | MKS00228 |
| 2026-10-19 | Monday | 20:00:00 | Dhaanush | KAVIBHARATHI P | MKS00201 |
| 2026-10-19 | Monday | 20:00:00 | Dhaanush | Kavinpriyan | MKS00023 |
| 2026-10-19 | Monday | 20:00:00 | Dhaanush | Keshav Krishna | YTC |
| 2026-10-19 | Monday | 20:00:00 | Dhaanush | M Nethran | MKS00020 |
| 2026-10-19 | Monday | 20:00:00 | Dhaanush | Pranith | MKS00143 |
| 2026-10-19 | Monday | 20:00:00 | Dhaanush | V.Pranav | MKS00173 |
| 2026-10-19 | Monday | 20:00:00 | Guru | D KAVISH | MKS00079 |
| 2026-10-19 | Monday | 20:00:00 | Guru | Dhanya
  sri S S | MKS00114 |
| 2026-10-19 | Monday | 20:00:00 | Guru | M.Nalini Hirthika | MKS00118 |
| 2026-10-19 | Monday | 20:00:00 | Guru | Nirupan | MKS00185 |
| 2026-10-19 | Monday | 20:00:00 | Guru | Ryan Stalin | MKS00007 |
| 2026-10-19 | Monday | 20:00:00 | Guru | V. Srikaviyazhini | MKS00131 |
| 2026-10-20 | Tuesday | 06:00:00 | Bathri | Pugazhini Navaneethan | MKS00156 |
| 2026-10-20 | Tuesday | 06:00:00 | Prakash | Kirthik | MKS00048 |
| 2026-10-20 | Tuesday | 11:00:00 | Bathri | Magizh | MKS00213 |
| 2026-10-20 | Tuesday | 17:00:00 | Bathri | Harri mithran P | MKS00210 |
| 2026-10-20 | Tuesday | 17:00:00 | Dhaanush | P.V Subhiksha | MKS00150 |
| 2026-10-20 | Tuesday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-20 | Tuesday | 18:00:00 | Dhaanush | Reyhan nawaz | MKS00049 |
| 2026-10-20 | Tuesday | 18:00:00 | Dhaanush | Thivya | MKS00056 |
| 2026-10-20 | Tuesday | 19:00:00 | Abinaya | Adhigan Amarnath | MKS00204 |
| 2026-10-20 | Tuesday | 19:00:00 | Abinaya | B.SAI SRI | MKS00211 |
| 2026-10-20 | Tuesday | 19:00:00 | Abinaya | Sudharshika | MKS00216 |
| 2026-10-20 | Tuesday | 19:00:00 | Dhaanush | Ayaan Haris | MKS00092 |
| 2026-10-20 | Tuesday | 19:00:00 | Dhaanush | B SARVESSH | MKS00108 |
| 2026-10-20 | Tuesday | 19:00:00 | Dhaanush | D. Tharun | MKS00127 |
| 2026-10-20 | Tuesday | 19:00:00 | Dhaanush | Rohith kumar.B | MKS00207 |
| 2026-10-20 | Tuesday | 19:00:00 | Dhaanush | Yuviga | MKS00107 |
| 2026-10-20 | Tuesday | 19:00:00 | Prakash | B.AARAV NARAYAN | MKS00098 |
| 2026-10-20 | Tuesday | 19:00:00 | Prakash | M.Srisaran | MKS00186 |
| 2026-10-20 | Tuesday | 20:00:00 | Abinaya | BHAANAVI.V | MKS00189 |
| 2026-10-20 | Tuesday | 20:00:00 | Abinaya | Cholamithran BR | MKS00192 |
| 2026-10-20 | Tuesday | 20:00:00 | Abinaya | Nyvan | MKS00208 |
| 2026-10-20 | Tuesday | 20:00:00 | Abinaya | RITHIKNATH K.M | MKS00193 |
| 2026-10-20 | Tuesday | 20:00:00 | Abinaya | Thiyashwar S | MKS00181 |
| 2026-10-20 | Tuesday | 20:00:00 | Bathri | A R Thatchiraa Shree | MKS00172 |
| 2026-10-20 | Tuesday | 20:00:00 | Bathri | H V Kanishk | MKS00154 |
| 2026-10-20 | Tuesday | 20:00:00 | Bathri | Jeevith. N.M | MKS00224 |
| 2026-10-20 | Tuesday | 20:00:00 | Bathri | Nishwanth R | MKS00171 |
| 2026-10-20 | Tuesday | 20:00:00 | Bathri | R Logeshwaran | MKS00222 |
| 2026-10-20 | Tuesday | 20:00:00 | Bathri | Ridhanya Sri.V | MKS00178 |
| 2026-10-20 | Tuesday | 20:00:00 | Bathri | S.P.NEHASRI | MKS00157 |
| 2026-10-20 | Tuesday | 20:00:00 | Dhaanush | Manikandan S | MKS00183 |
| 2026-10-20 | Tuesday | 20:00:00 | Dhaanush | Sai Eswar | MKS00132 |
| 2026-10-20 | Tuesday | 20:00:00 | Dhaanush | Samuel Rajan | MKS00182 |
| 2026-10-21 | Wednesday | 06:00:00 | Bathri | Vaibhavi Krishna | MKS00164 |
| 2026-10-21 | Wednesday | 06:00:00 | Bathri | Vaishnavi Krishna | MKS00165 |
| 2026-10-21 | Wednesday | 06:00:00 | Manikandan | Priyan | MKS00162 |
| 2026-10-21 | Wednesday | 16:30:00 | Bathri | Devansh gade | MKS00218 |
| 2026-10-21 | Wednesday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-21 | Wednesday | 18:00:00 | Prakash | Kaashvi Prakash | MKS00184 |
| 2026-10-21 | Wednesday | 19:00:00 | Abinaya | A.Bavinesh | MKS00214 |
| 2026-10-21 | Wednesday | 19:00:00 | Abinaya | B.V.Tijesh | MKS00219 |
| 2026-10-21 | Wednesday | 19:00:00 | Abinaya | BHAANAVI.V | MKS00189 |
| 2026-10-21 | Wednesday | 19:00:00 | Abinaya | C.V.Chanvika | MKS00196 |
| 2026-10-21 | Wednesday | 19:00:00 | Abinaya | Cholamithran BR | MKS00192 |
| 2026-10-21 | Wednesday | 19:00:00 | Abinaya | RITHIKNATH K.M | MKS00193 |
| 2026-10-21 | Wednesday | 19:00:00 | Dhaanush | Arishmithran | MKS00072 |
| 2026-10-21 | Wednesday | 19:00:00 | Dhaanush | Hithesh | MKS00206 |
| 2026-10-21 | Wednesday | 19:00:00 | Dhaanush | Manikandan S | MKS00183 |
| 2026-10-21 | Wednesday | 19:00:00 | Dhaanush | Praduksha | MKS00091 |
| 2026-10-21 | Wednesday | 19:00:00 | Dhaanush | S.Raagavarshenee | MKS00009 |
| 2026-10-21 | Wednesday | 19:00:00 | Dhaanush | Sanjumithra | MKS00070 |
| 2026-10-21 | Wednesday | 19:00:00 | Dhaanush | Shakthivishakan A | MKS00034 |
| 2026-10-21 | Wednesday | 19:00:00 | Guru | Viraaj Shanmugam | MKS00153 |
| 2026-10-21 | Wednesday | 19:00:00 | Saravanan | Diya | MKS00024 |
| 2026-10-21 | Wednesday | 19:00:00 | Saravanan | Hitesh prabu | MKS00014 |
| 2026-10-21 | Wednesday | 19:00:00 | Saravanan | M.Nishik | MKS00113 |
| 2026-10-21 | Wednesday | 19:00:00 | Saravanan | Mithran P | MKS00083 |
| 2026-10-21 | Wednesday | 19:00:00 | Saravanan | Samuel Rajan | MKS00182 |
| 2026-10-21 | Wednesday | 19:00:00 | Saravanan | Vedhanth V | MKS00102 |
| 2026-10-21 | Wednesday | 20:00:00 | Abinaya | M.Srisaran | MKS00186 |
| 2026-10-21 | Wednesday | 20:00:00 | Bathri | D KAVISH | MKS00079 |
| 2026-10-21 | Wednesday | 20:00:00 | Bathri | Dhanya
  sri S S | MKS00114 |
| 2026-10-21 | Wednesday | 20:00:00 | Bathri | M.Nalini Hirthika | MKS00118 |
| 2026-10-21 | Wednesday | 20:00:00 | Dhaanush | Sai Eswar | MKS00132 |
| 2026-10-22 | Thursday | 06:00:00 | Bathri | Vedh Pabba | MKS00190 |
| 2026-10-22 | Thursday | 06:00:00 | Prakash | Kirthik | MKS00048 |
| 2026-10-22 | Thursday | 17:00:00 | Dhaanush | P.V Subhiksha | MKS00150 |
| 2026-10-22 | Thursday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-22 | Thursday | 19:00:00 | Manikandan | Jeevith. N.M | MKS00224 |
| 2026-10-22 | Thursday | 20:00:00 | Abinaya | Nyvan | MKS00208 |
| 2026-10-22 | Thursday | 20:00:00 | Abinaya | Thiyashwar S | MKS00181 |
| 2026-10-22 | Thursday | 20:00:00 | Bathri | Ridhanya Sri.V | MKS00178 |
| 2026-10-22 | Thursday | 20:00:00 | Dhaanush | Sai Eswar | MKS00132 |
| 2026-10-23 | Friday | 06:00:00 | Bathri | Vedh Pabba | MKS00190 |
| 2026-10-23 | Friday | 06:00:00 | Manikandan | Priyan | MKS00162 |
| 2026-10-23 | Friday | 11:00:00 | Bathri | Magizh | MKS00213 |
| 2026-10-23 | Friday | 17:00:00 | Bathri | Harri mithran P | MKS00210 |
| 2026-10-23 | Friday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-23 | Friday | 19:00:00 | Abinaya | A.Bavinesh | MKS00214 |
| 2026-10-23 | Friday | 19:00:00 | Abinaya | B.V.Tijesh | MKS00219 |
| 2026-10-23 | Friday | 19:00:00 | Abinaya | C.V.Chanvika | MKS00196 |
| 2026-10-23 | Friday | 19:00:00 | Dhaanush | Rohith kumar.B | MKS00207 |
| 2026-10-23 | Friday | 20:00:00 | Bathri | S. YASWANNTH | MKS00039 |
| 2026-10-23 | Friday | 20:00:00 | Bathri | S.P.NEHASRI | MKS00157 |
| 2026-10-23 | Friday | 20:00:00 | Dhaanush | KAVIBHARATHI P | MKS00201 |
| 2026-10-23 | Friday | 20:00:00 | Dhaanush | Kavinpriyan | MKS00023 |
| 2026-10-23 | Friday | 20:00:00 | Dhaanush | Keshav Krishna | YTC |
| 2026-10-23 | Friday | 20:00:00 | Dhaanush | M Nethran | MKS00020 |
| 2026-10-23 | Friday | 20:00:00 | Dhaanush | Pranith | MKS00143 |
| 2026-10-23 | Friday | 20:00:00 | Dhaanush | Samuel Rajan | MKS00182 |
| 2026-10-23 | Friday | 20:00:00 | Dhaanush | V.Pranav | MKS00173 |
| 2026-10-24 | Saturday | 06:00:00 | Bathri | Pugazhini Navaneethan | MKS00156 |
| 2026-10-24 | Saturday | 12:15:00 | Bathri | Viraaj Shanmugam | MKS00153 |
| 2026-10-24 | Saturday | 17:00:00 | Dhaanush | Avyukt A Praveen | MKS00174 |
| 2026-10-24 | Saturday | 18:00:00 | Bathri | T L KANISHKAR | MKS00195 |
| 2026-10-24 | Saturday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-24 | Saturday | 18:00:00 | Dhaanush | Reyhan nawaz | MKS00049 |
| 2026-10-24 | Saturday | 19:00:00 | Dhaanush | Arishmithran | MKS00072 |
| 2026-10-24 | Saturday | 19:00:00 | Dhaanush | Praduksha | MKS00091 |
| 2026-10-24 | Saturday | 19:00:00 | Dhaanush | S.Raagavarshenee | MKS00009 |
| 2026-10-24 | Saturday | 19:00:00 | Dhaanush | Sanjumithra | MKS00070 |
| 2026-10-24 | Saturday | 19:00:00 | Dhaanush | Shakthivishakan A | MKS00034 |
| 2026-10-24 | Saturday | 19:00:00 | Prakash | Ineya Individual | MKS00050 |
| 2026-10-24 | Saturday | 19:00:00 | Saravanan | Diya | MKS00024 |
| 2026-10-24 | Saturday | 19:00:00 | Saravanan | Hitesh prabu | MKS00014 |
| 2026-10-24 | Saturday | 19:00:00 | Saravanan | Mithran P | MKS00083 |
| 2026-10-24 | Saturday | 19:00:00 | Saravanan | Vedhanth V | MKS00102 |
| 2026-10-24 | Saturday | 20:00:00 | Bathri | Ridhanya Sri.V | MKS00178 |
| 2026-10-24 | Saturday | 20:00:00 | Guru | S. YASWANNTH | MKS00039 |
| 2026-10-24 | Saturday | 20:00:00 | Guru | V. Srikaviyazhini | MKS00131 |
| 2026-10-24 | Saturday | 21:00:00 | Bathri | Vaibhavi Krishna | MKS00164 |
| 2026-10-24 | Saturday | 21:00:00 | Bathri | Vaishnavi Krishna | MKS00165 |
| 2026-10-25 | Sunday | 09:00:00 | Dhaanush | Sai Eswar | MKS00132 |
| 2026-10-25 | Sunday | 09:00:00 | Guru | Viraaj Shanmugam | MKS00153 |
| 2026-10-25 | Sunday | 10:00:00 | Abinaya | KAVIBHARATHI P | MKS00201 |
| 2026-10-25 | Sunday | 10:00:00 | Abinaya | Kavinpriyan | MKS00023 |
| 2026-10-25 | Sunday | 10:00:00 | Abinaya | Pranith | MKS00143 |
| 2026-10-25 | Sunday | 10:00:00 | Abinaya | S.Raagavarshenee | MKS00009 |
| 2026-10-25 | Sunday | 10:00:00 | Abinaya | V.Pranav | MKS00173 |
| 2026-10-25 | Sunday | 10:00:00 | Dhaanush | Diya | MKS00024 |
| 2026-10-25 | Sunday | 10:00:00 | Dhaanush | Mithran P | MKS00083 |
| 2026-10-25 | Sunday | 10:00:00 | Dhaanush | Reyhan nawaz | MKS00049 |
| 2026-10-25 | Sunday | 10:00:00 | Dhaanush | Vedhanth V | MKS00102 |
| 2026-10-25 | Sunday | 10:00:00 | Hema | Arishmithran | MKS00072 |
| 2026-10-25 | Sunday | 10:00:00 | Hema | Hitesh prabu | MKS00014 |
| 2026-10-25 | Sunday | 10:00:00 | Hema | Praduksha | MKS00091 |
| 2026-10-25 | Sunday | 10:00:00 | Hema | Sanjumithra | MKS00070 |
| 2026-10-25 | Sunday | 10:00:00 | Hema | Shakthivishakan A | MKS00034 |
| 2026-10-25 | Sunday | 11:00:00 | Abinaya | Nyvan | MKS00208 |
| 2026-10-25 | Sunday | 11:00:00 | Abinaya | Thiyashwar S | MKS00181 |
| 2026-10-25 | Sunday | 11:00:00 | Guru | V. Srikaviyazhini | MKS00131 |
| 2026-10-25 | Sunday | 11:00:00 | Hema | Avyukt A Praveen | MKS00174 |
| 2026-10-25 | Sunday | 11:00:00 | Hema | Keshav Krishna | YTC |
| 2026-10-25 | Sunday | 11:00:00 | Hema | M Nethran | MKS00020 |
| 2026-10-26 | Monday | 16:30:00 | Bathri | Devansh gade | MKS00218 |
| 2026-10-26 | Monday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-26 | Monday | 19:00:00 | Abinaya | A.Bavinesh | MKS00214 |
| 2026-10-26 | Monday | 19:00:00 | Abinaya | B.V.Tijesh | MKS00219 |
| 2026-10-26 | Monday | 19:00:00 | Abinaya | C.V.Chanvika | MKS00196 |
| 2026-10-26 | Monday | 20:00:00 | Dhaanush | KAVIBHARATHI P | MKS00201 |
| 2026-10-26 | Monday | 20:00:00 | Dhaanush | Kavinpriyan | MKS00023 |
| 2026-10-26 | Monday | 20:00:00 | Dhaanush | Keshav Krishna | YTC |
| 2026-10-26 | Monday | 20:00:00 | Dhaanush | M Nethran | MKS00020 |
| 2026-10-26 | Monday | 20:00:00 | Dhaanush | Pranith | MKS00143 |
| 2026-10-26 | Monday | 20:00:00 | Dhaanush | V.Pranav | MKS00173 |
| 2026-10-26 | Monday | 20:00:00 | Guru | V. Srikaviyazhini | MKS00131 |
| 2026-10-27 | Tuesday | 06:00:00 | Bathri | Pugazhini Navaneethan | MKS00156 |
| 2026-10-27 | Tuesday | 11:00:00 | Bathri | Magizh | MKS00213 |
| 2026-10-27 | Tuesday | 17:00:00 | Bathri | Harri mithran P | MKS00210 |
| 2026-10-27 | Tuesday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-27 | Tuesday | 18:00:00 | Dhaanush | Reyhan nawaz | MKS00049 |
| 2026-10-27 | Tuesday | 20:00:00 | Abinaya | Nyvan | MKS00208 |
| 2026-10-27 | Tuesday | 20:00:00 | Abinaya | Thiyashwar S | MKS00181 |
| 2026-10-27 | Tuesday | 20:00:00 | Bathri | Ridhanya Sri.V | MKS00178 |
| 2026-10-27 | Tuesday | 20:00:00 | Dhaanush | Sai Eswar | MKS00132 |
| 2026-10-27 | Tuesday | 20:00:00 | Dhaanush | Samuel Rajan | MKS00182 |
| 2026-10-28 | Wednesday | 06:00:00 | Bathri | Vaibhavi Krishna | MKS00164 |
| 2026-10-28 | Wednesday | 06:00:00 | Bathri | Vaishnavi Krishna | MKS00165 |
| 2026-10-28 | Wednesday | 06:00:00 | Manikandan | Priyan | MKS00162 |
| 2026-10-28 | Wednesday | 16:30:00 | Bathri | Devansh gade | MKS00218 |
| 2026-10-28 | Wednesday | 18:00:00 | Dhaanush | Nithesh Nagarathinam | MKS00054 |
| 2026-10-28 | Wednesday | 18:00:00 | Prakash | Kaashvi Prakash | MKS00184 |
| 2026-10-28 | Wednesday | 19:00:00 | Abinaya | A.Bavinesh | MKS00214 |
| 2026-10-28 | Wednesday | 19:00:00 | Abinaya | B.V.Tijesh | MKS00219 |
| 2026-10-28 | Wednesday | 19:00:00 | Abinaya | C.V.Chanvika | MKS00196 |
| 2026-10-28 | Wednesday | 19:00:00 | Dhaanush | Arishmithran | MKS00072 |
| 2026-10-28 | Wednesday | 19:00:00 | Dhaanush | Praduksha | MKS00091 |
| 2026-10-28 | Wednesday | 19:00:00 | Dhaanush | S.Raagavarshenee | MKS00009 |
| 2026-10-28 | Wednesday | 19:00:00 | Dhaanush | Sanjumithra | MKS00070 |
| 2026-10-28 | Wednesday | 19:00:00 | Dhaanush | Shakthivishakan A | MKS00034 |
| 2026-10-28 | Wednesday | 19:00:00 | Saravanan | Diya | MKS00024 |
| 2026-10-28 | Wednesday | 19:00:00 | Saravanan | Hitesh prabu | MKS00014 |
| 2026-10-28 | Wednesday | 19:00:00 | Saravanan | Mithran P | MKS00083 |
| 2026-10-28 | Wednesday | 19:00:00 | Saravanan | Samuel Rajan | MKS00182 |
| 2026-10-28 | Wednesday | 19:00:00 | Saravanan | Vedhanth V | MKS00102 |
| 2026-10-28 | Wednesday | 20:00:00 | Dhaanush | Sai Eswar | MKS00132 |
| 2026-10-29 | Thursday | 20:00:00 | Dhaanush | Sai Eswar | MKS00132 |
| 2026-10-30 | Friday | 17:00:00 | Bathri | Harri mithran P | MKS00210 |
| 2026-10-31 | Saturday | 06:00:00 | Bathri | Pugazhini Navaneethan | MKS00156 |

## Daily group-class summary

| Date | Day | Group Classes |
|---|---|---:|
| 2026-10-01 | Thursday | 17 |
| 2026-10-02 | Friday | 22 |
| 2026-10-03 | Saturday | 22 |
| 2026-10-04 | Sunday | 14 |
| 2026-10-05 | Monday | 16 |
| 2026-10-06 | Tuesday | 18 |
| 2026-10-07 | Wednesday | 21 |
| 2026-10-08 | Thursday | 17 |
| 2026-10-09 | Friday | 22 |
| 2026-10-10 | Saturday | 22 |
| 2026-10-11 | Sunday | 14 |
| 2026-10-12 | Monday | 16 |
| 2026-10-13 | Tuesday | 18 |
| 2026-10-14 | Wednesday | 18 |
| 2026-10-15 | Thursday | 14 |
| 2026-10-16 | Friday | 20 |
| 2026-10-17 | Saturday | 20 |
| 2026-10-18 | Sunday | 9 |
| 2026-10-19 | Monday | 10 |
| 2026-10-20 | Tuesday | 12 |
| 2026-10-21 | Wednesday | 12 |
| 2026-10-22 | Thursday | 8 |
| 2026-10-23 | Friday | 9 |
| 2026-10-24 | Saturday | 11 |
| 2026-10-25 | Sunday | 8 |
| 2026-10-26 | Monday | 5 |
| 2026-10-27 | Tuesday | 7 |
| 2026-10-28 | Wednesday | 9 |
| 2026-10-29 | Thursday | 1 |
| 2026-10-30 | Friday | 1 |
| 2026-10-31 | Saturday | 1 |


---

# PART C — OPERATING INSTRUCTION FOR FUTURE MONTHS

Use the latest approved monthly schedule as the reference month.

For a requested target month:

1. Read every student's attendance pattern from the latest approved reference.
2. Preserve the student's recurring attendance days.
3. Preserve the time and trainer assignment associated with those recurring slots.
4. Generate the real calendar dates for the target month.
5. Never exceed that student's Planned Classes limit.
6. Preserve multi-trainer or multi-slot exceptions when they exist in the approved reference.
7. Keep the same workbook structure and formatting.
8. Recalculate daily Actual Classes using:
   UNIQUE(Date + Start Time + Trainer) = 1 group class.
9. Validate before export:
   - no student over Planned Classes
   - no unsupported weekday
   - no unsupported trainer/time
   - no duplicate exact student slot
   - actual class totals match unique group sessions
10. Export the target month's Excel.

IMPORTANT:
This is a recurring schedule system with a monthly Planned Classes ceiling.
It is NOT a system where the previous month's exact dates are copied to the next month.

---

# COPY/PASTE COMMAND FOR THE AI AGENT

You are the chess academy monthly scheduling engine.

Use ONLY the files I am uploading in this conversation as the current source of truth.
Ignore all previous files, previous schedules, and previous generated outputs.

Use:
1. The Excel file I upload as the workbook/layout/template reference.
2. This MASTER Markdown file as the normalized schedule data and scheduling rules.

Generate the requested future month.

Rules:
- Keep every student's attendance days based on the approved reference schedule.
- Keep the student's assigned trainer and time.
- Convert recurring weekdays into actual target-month dates.
- Never exceed Planned Classes.
- Preserve existing exceptions and multi-trainer patterns.
- Do not invent data.
- Keep the Excel structure and formatting.
- Count one class as one unique Date + Start Time + Trainer group.
- Validate everything before exporting.

When I say "generate November", "generate December", etc., use the latest approved monthly schedule as the reference month and repeat the same process.

Do not use any older file unless I explicitly say it is the current reference.
