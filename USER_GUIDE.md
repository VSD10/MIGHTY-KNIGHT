# ♞ Mighty Knight — Complete User Guide & How It Works

Welcome to **Mighty Knight**, an automated, rule-driven scheduling system built specifically for chess academies.

This guide explains **how the system works, how rules are applied, and step-by-step how to use the web application**.

---

## 1. Quick Overview: What Does Mighty Knight Do?

Mighty Knight automatically takes your **student requirements** and **coach availability/capabilities**, applies academy rules, and creates an optimized schedule.

```
Student Requirements + Coach Capabilities + Priority Rules + Operating Hours = Practical Schedule
```

### The Golden Rule: 100% Student Accountability
Mighty Knight will **NEVER silently drop or hide a student**. Every single student in your Excel file will appear in the output as either:
1. **Scheduled** (assigned to a class slot with a coach), OR
2. **Unscheduled / Attention Required** (flagged in Output 3 with the exact reason why they couldn't be scheduled).

---

## 2. Step 1: Preparing & Uploading Excel Data

### How to Get the Template
1. Open the Web App at **`http://localhost:5173/`**.
2. Click **`Excel Format`** in the top navigation bar or inside the **`Upload Excel Data`** modal.
3. Download **`mighty_knight_template.xlsx`**.

### The Two Excel Sheets

#### **Sheet 1: `Students`**
Contains the students requiring chess classes for the month/period:

| Field Name | Description | Example |
|---|---|---|
| `Student ID` | Unique student ID | `STU001` |
| `Student Name` | Full name | `Aarav Sharma` |
| `Student Level` | Level (Basic 1 to Intermediate) | `Basic 1` |
| `Batch Type` | **G** (Group 8-10), **L** (Limited 1-3), **I** (Individual 1) | `G` |
| `Required Classes` | Total classes needed for period | `8` |
| `Monday` to `Sunday` | Preference: `5 PM - 9 PM`, `No Preference`, or `Not Available` | `05:00 PM – 09:00 PM` |
| `Tournament Preference` | `Yes` or `No` | `No` |

#### **Sheet 2: `Coaches`**
Contains coach qualifications, workload caps, and day availability:

| Field Name | Description | Example |
|---|---|---|
| `Coach Name` | Full name | `Bathrinath` |
| `Levels Handled` | Comma-separated levels coach can teach | `Basic 1, Basic 2, Beginner 1` |
| `Monthly Class Capacity` | Target min - max cap | `60 - 90` |
| `Monday Max` to `Sunday Max` | Max classes allowed on that day | `4` (Mon-Fri), `5` (Sat), `2` (Sun) |
| `Sunday Preference` | `Available` or `No Sunday Tournaments` | `Available` |

---

## 3. Step 2: Selecting Date Range & Running Engine

In the UI, use the **Scheduling Period Selection** bar:

1. **Preset Buttons**: Click `Today`, `Tomorrow`, `This Week`, or `Full Month`.
2. **Custom Dates**: Choose `Start Date` and `End Date`.
3. Click **`Generate Schedule`** or **`Run Engine`**.

---

## 4. How the Engine Works Under the Hood

When you click **Run Engine**, Mighty Knight executes a 7-priority process:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Filter students available on target day                 │
├─────────────────────────────────────────────────────────────┤
│ 2. Form compatible batches (Same Level + Same Batch Type)   │
├─────────────────────────────────────────────────────────────┤
│ 3. Match preferred 1-hour time slots within operating hours  │
├─────────────────────────────────────────────────────────────┤
│ 4. Find qualified coaches for the student level             │
├─────────────────────────────────────────────────────────────┤
│ 5. Apply level-wise coach priority order                    │
├─────────────────────────────────────────────────────────────┤
│ 6. Check 7 mandatory constraints:                           │
│    • Coach qualified?                                       │
│    • Coach available on date/day?                           │
│    • Coach free at time slot (1 coach 1 class rule)?        │
│    • Daily max class limit reached?                         │
│    • Monthly max capacity reached?                          │
│    • Sunday 3 PM max end time rule?                         │
│    • Sunday tournament coach exclusion rule?                │
├─────────────────────────────────────────────────────────────┤
│ 7. Assign coach or flag student for Admin Attention         │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Understanding the 3 Output Views

Mighty Knight generates **three separate views** designed for different user roles:

### 📱 Output 1 — Coach Communication Schedule (WhatsApp Ready)
* **Designed For**: Coaches and instant WhatsApp sharing.
* **Contains**: Date, Day, Time Slot, and Coach Names **ONLY** (No private student details).
* **WhatsApp Action**: Click the green **`Copy Coach Schedule (WhatsApp Ready)`** button. It copies plain text to your clipboard formatted like this:

```text
🏆 *MIGHTY KNIGHT — COACH SCHEDULE*
=================================

📅 *Monday, August 24, 2026*
---------------------------------
• *06:00 AM – 07:00 AM*: Bathrinath
• *05:00 PM – 06:00 PM*: Bathrinath, Dhaanush, Prakash, Abinaya
• *06:00 PM – 07:00 PM*: Bathrinath, Abinaya, Manikandan
```

---

### 📋 Output 2 — Detailed Administrative Schedule
* **Designed For**: Academy Managers and Operational Review.
* **Contains**: Complete class matrix including:
  - Class Date, Day, Time Slot
  - Assigned Coach
  - Student Level & Batch Type
  - Total Headcount
  - Full Student Names & Student IDs
  - Warnings (e.g., *Group Batch size below target minimum 8*)
* **Search & Filter**: Search by coach name, student name, or filter by Student Level.
* **Manual Edit Button**: Click **`Edit Class`** on any row to override assignments.

---

### 🚨 Output 3 — Unscheduled / Administrator Attention Report
* **Designed For**: Mandatory Follow-Up on Flagged Cases.
* **Visually Prominent Red Banner**: Highlights every student who could not be fully scheduled automatically.
* **Accountability Stat Cards**:
  - **Total Considered**: Total input students evaluated.
  - **Scheduled**: Students with allocated classes.
  - **Attention Required**: Students needing manual admin review.
* **Table Breakdown**: Shows Student Name, ID, Level, Batch, Required vs Scheduled vs Missing classes, and the **exact Failure Reason** (e.g. *No qualified coach available*, *Daily coach cap reached*, *Student unavailable*).

---

## 6. Manual Administrative Overrides (Section 37)

If an automatic allocation couldn't be made or you want to override a coach assignment:

1. Go to **Output 2** or **Output 3** and click **`Edit Class`**.
2. A modal pops up allowing you to change the **Coach Name**, **Date**, or **Time Slot**.
3. Click **`Validate Rules`**.
4. The system evaluates live constraints and alerts you if your manual edit causes:
   - ⚠️ Coach Overlap (coach assigned to 2 classes at same time)
   - ⚠️ Daily/Monthly Capacity Breach
   - ⚠️ Sunday 3 PM Violation
5. Click **`Acknowledge & Save Override`** to save your change.

---

## 7. Schedule Status (Draft vs Finalized)

At the top of the header bar, click the **`Status`** pill to toggle:
- **`Draft`**: Editable working version of the schedule.
- **`Finalized`**: Locked and protected version ready for distribution.

---

## 8. Summary Checklist for Daily Use

1. [ ] **Upload Data**: Click `Upload Excel Data` and select your `.xlsx` file (or use default template).
2. [ ] **Pick Period**: Select `Today`, `This Week`, or custom dates.
3. [ ] **Run Engine**: Click `Generate Schedule`.
4. [ ] **Review Output 3**: Check if any student is flagged for Admin Attention.
5. [ ] **Review Output 2**: Inspect detailed classes and make manual edits if needed.
6. [ ] **Share Output 1**: Click `Copy Coach Schedule` and paste into your WhatsApp coach group!
