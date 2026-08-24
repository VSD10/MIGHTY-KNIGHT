# MIGHTY KNIGHT
## Dynamic Academy Scheduling System

**Software Requirements and Functional Specification**
**Pre-Development Requirement Document**

**Version 1.0**

*Prepared for internal review and development planning*
*Business Requirement Document · Confidential*

---

## 1. Introduction

Mighty Knight is a dynamic academy scheduling system designed to automatically allocate students to suitable classes and assign appropriate coaches.

The system uses uploaded academy data and applies the Mighty Knight scheduling rules to determine which student attends which class, on which date, at what time, and with which coach.

The system must generate a practical schedule while allowing the administrator to review and manually handle exceptional cases.

## 2. Core Objective

Mighty Knight must automatically process:

- Student level
- Batch type
- Preferred days
- Preferred timings
- Required number of classes
- Coach capability
- Coach priority
- Coach availability and preferences
- Daily class limits
- Monthly class capacity
- Academy operating hours
- Batch capacity
- Sunday and tournament rules

The result should be a complete scheduling output based on the uploaded data and Mighty Knight protocols.

## 3. Primary Input Method

The primary input source for Mighty Knight is an Excel file.

The administrator uploads the required student and coach data into the system. The administrator is responsible for ensuring that the uploaded data is accurate and consistent.

Mighty Knight should then:

- Read the uploaded Excel data.
- Recognize students and coaches.
- Process the available fields.
- Apply the Mighty Knight scheduling rules.
- Generate the schedule.

The system must not depend on a fixed number of students or coaches. If a future Excel file contains new students or new coaches, the system should process them according to the available data and configured rules.

## 4. Data Quality Assumption

The administrator will provide properly prepared data. Mighty Knight should use the uploaded information as the source for scheduling.

The system should not require changes to its scheduling logic merely because:

- New students are added
- Students are removed
- New coaches are added
- Coach capabilities change
- Student preferences change
- Batch counts change
- The scheduling month changes

The scheduling engine must dynamically operate based on the available input data.

## 5. Student Data

Each student will have a unique identity. The student data may include:

- Student Name
- Unique Student ID
- Student Level
- Batch Type
- Region or Time Zone
- Number of Classes Required
- Monday, Tuesday, Wednesday, Thursday, Friday, Saturday and Sunday Preference
- Tournament Preference
- Additional Comments
- Other scheduling information where applicable

The system should use the information available in the uploaded Excel file.

## 6. Coach Data

Coach information may include:

- Coach Name
- Levels the coach can handle
- Monthly class capacity
- Daily maximum classes
- Day-wise availability
- Preferred timings
- Sunday preference
- Sunday maximum classes
- Special comments
- Temporary exceptions
- Other applicable scheduling information

The current coach list includes:

| # | Coach Name |
|---|---|
| 1 | Guruvanthana |
| 2 | Dhaanush |
| 3 | Arshath |
| 4 | Saravanan |
| 5 | Bathrinath |
| 6 | Abinaya |
| 7 | Prakash |
| 8 | Manikandan |

The final system should use the coach names provided in the academy's master data.

## 7. Student Levels

The academy currently uses eight levels. The level and group mapping should be configurable.

| Group | Student Level |
|---|---|
| 1 | Basic 1 |
| 2 | Basic 2 |
| 3 | Beginner 1 |
| 4 | Beginner 2 |
| 5 | Beginner 3 |
| 6 | Early Intermediate 1 |
| 7 | Early Intermediate 2 |
| 8 | Intermediate |

## 8. Class Duration and Time Slots

Each class has a duration of 1 Hour. The scheduling engine should work primarily with one-hour slots.

Examples include:

- 6:00 AM – 7:00 AM
- 7:00 AM – 8:00 AM
- 9:00 AM – 10:00 AM
- 10:00 AM – 11:00 AM
- 4:00 PM – 5:00 PM
- 5:00 PM – 6:00 PM
- 6:00 PM – 7:00 PM
- 7:00 PM – 8:00 PM
- 8:00 PM – 9:00 PM

An exceptional 9:00 PM – 10:00 PM slot may be allowed when configured.

## 9. Academy Operating Hours

**Monday to Saturday — Normal Operating Periods**

- 6:00 AM – 8:00 AM
- 9:00 AM – 2:00 PM
- 4:00 PM – 9:00 PM

Exceptional scheduling periods may be configured separately.

**Sunday**

Sunday scheduling begins from 9:00 AM onwards. Classes must normally end by 3:00 PM. Sunday tournament rules must also be considered.

## 10. Saturday Peak Period

Saturday evening is an important scheduling period: 5:00 PM – 9:00 PM. The system should utilize this period effectively based on student demand, coach availability, and capacity.

## 11. Batch Types

The academy currently uses three batch categories. These values should be configurable. The scheduler must not exceed the maximum batch capacity.

| Batch Type | Symbol | Capacity |
|---|---|---|
| Group Batch | G | 8 – 10 students |
| Limited Students Batch | L | 1 – 3 students |
| Individual Batch | I | 1 student |

If a Group Batch cannot reach its configured minimum because of scheduling constraints, the system should flag it for administrator review.

## 12. Student Allocation Rules

Students should normally be grouped according to:

- Student level
- Batch type
- Preferred day
- Preferred time
- Required number of classes
- Applicable scheduling rules

Students should not be unnecessarily mixed into incompatible classes. A class should normally contain students whose scheduling requirements are compatible.

## 13. Student Preferences

Students may have different preferences for different days. Examples:

- Monday: 5 PM – 9 PM
- Tuesday: 6 PM – 9 PM
- Wednesday: Not Available
- Thursday: No Preference

The system should interpret these values as follows:

| Preference Value | System Interpretation |
|---|---|
| Preferred Time | Attempt to schedule within the preferred period first; if necessary, select the nearest suitable slot according to the scheduling rules. |
| No Preference | Any valid academy time slot may be considered. |
| Not Available | The student must not be scheduled on that day. |

## 14. Required Number of Classes

Each student may require a different number of classes. The scheduler must use the exact value provided in the student data.

The system should distribute the required classes across the selected scheduling period based on:

- Student availability
- Student timing preferences
- Batch compatibility
- Coach availability
- Academy operating hours
- Mighty Knight scheduling rules

The system must not assume that all students require the same number of classes.

## 15. Coach Capability

A coach may teach only the levels assigned to them in the available coach data. Before assigning a coach, Mighty Knight must verify that the coach is qualified to handle the required student level. If a new coach is added through future data, the system should use the capability information provided for that coach.

## 16. Level-Wise Coach Priority

Coach selection should follow the configured priority order for each student level. The priority mapping should be configurable.

| Student Level | Coach Priority Order (Highest → Lowest) |
|---|---|
| Basic 1 | Bathrinath → Abinaya → Manikandan → Prakash → Guruvanthana |
| Basic 2 | Bathrinath → Abinaya → Manikandan → Prakash → Guruvanthana |
| Beginner 1 | Bathrinath → Guruvanthana → Dhaanush → Manikandan → Abinaya → Prakash |
| Beginner 2 | Guruvanthana → Dhaanush → Bathrinath → Prakash → Saravanan |
| Beginner 3 | Dhaanush → Guruvanthana → Prakash → Saravanan |
| Early Intermediate 1 | Dhaanush → Saravanan → Prakash → Guruvanthana |
| Early Intermediate 2 | Dhaanush → Arshath → Prakash |
| Intermediate | Arshath → Dhaanush → Prakash → Saravanan |

## 17. Coach Selection Logic

For every class, Mighty Knight should follow this process:

1. **Step 1.** Identify the student level.
2. **Step 2.** Find coaches capable of handling that level.
3. **Step 3.** Apply the configured level-wise priority.
4. **Step 4.** Check whether the coach meets every condition below.
5. **Step 5.** If the highest-priority coach cannot be assigned, check the next suitable coach. The system should continue until a valid assignment is found.

Step 4 checks include:

- Is capable of teaching the level
- Is available on the required date
- Is available during the required time
- Does not have another class at the same time
- Has not exceeded the daily class limit
- Has not exceeded the monthly maximum capacity
- Does not violate a special condition or exception

## 18. Coach Preference

Coach timing and day preferences should be considered when generating the schedule. Preferences should guide the scheduling process but should not automatically override mandatory scheduling rules.

The system should first satisfy:

- Mandatory academy rules
- Student requirements
- Coach capability
- Coach priority
- Coach availability
- Capacity restrictions

Coach preferences should then be used to select the most suitable practical assignment.

## 19. One Coach, One Class at a Time

This is a **mandatory rule**. A coach can handle only one class during the same time slot. A coach assigned from 6:00 PM – 7:00 PM cannot be assigned to another overlapping class. The system must automatically prevent coach conflicts.

## 20. Daily Coach Class Limits

Each coach may have a different maximum number of classes for each day. The system should use the day-wise limits provided in the coach data, for example:

- Monday maximum classes
- Tuesday maximum classes
- Wednesday maximum classes
- Thursday maximum classes
- Friday maximum classes
- Saturday maximum classes
- Sunday maximum classes

The scheduler must not exceed these limits unless the administrator manually handles an exceptional case.

## 21. Monthly Coach Capacity

Coach monthly capacity may be provided as a range. Examples: 60–90, 35–40, 70–78, 16–20, 30–60, 30–100.

| Value | Meaning |
|---|---|
| Lower value | Preferred workload target |
| Higher value | Maximum permitted capacity |

The scheduler should avoid exceeding the maximum. The system may also display workload information to help the administrator review coach distribution.

## 22. Special Conditions

Coach data may include:

- Temporary availability changes
- Special comments
- Tournament restrictions
- Makeup conditions
- Substitute-only conditions
- Other exceptions

These should be treated as configurable data and applied during scheduling where relevant. The scheduling logic should not require code changes for ordinary temporary conditions.

## 23. Sunday and Tournament Rules

Sunday scheduling must follow the configured Sunday rules. Current requirements include:

- Classes only until 3:00 PM
- Sunday tournaments may count as a class where applicable
- Avoid Dhaanush and Saravanan for Sunday tournament assignments
- Intermediate batch does not have Sunday tournament
- Tournament assignments may follow special matching rules

These rules should be applied separately from normal weekday scheduling.

## 24. Selected-Date Scheduling

The administrator should be able to select a specific date, for example: Monday, August 24, 2026.

Mighty Knight should identify the students applicable for that date and generate the corresponding schedule.

The result should show:

- Scheduled classes
- Time slots
- Assigned coaches
- Student allocation
- Batch allocation
- Scheduling warnings
- Unscheduled students requiring attention

## 25. Multi-Date and Monthly Scheduling

The system should support:

- Today
- Tomorrow
- Selected date
- Selected date range
- Remaining period of a month
- Full month

The scheduling engine must not be permanently tied to a specific month. Future schedules should work using the same Mighty Knight protocols and uploaded data.

## 26. Calendar-Based Access

The administrator should be able to select the required scheduling date or period using a simple calendar interface, for example: Today, Tomorrow, Selected date, Selected week, Selected range, Full month.

The generated schedule should be available immediately after processing.

## 27. Core Scheduling Workflow

The Mighty Knight scheduling process should follow this sequence:

1. Upload Student and Coach Excel Data
2. System Reads and Recognizes Available Data
3. Administrator Selects Date or Scheduling Period
4. System Identifies Students Requiring Classes
5. System Checks Level, Batch, Timing, Availability and Required Classes
6. System Creates Compatible Class Groups
7. System Applies Coach Capability and Level Priority
8. System Checks Availability, Capacity, Preferences and Conflicts
9. System Assigns the Most Suitable Coach
10. System Records Every Scheduled and Unscheduled Student
11. System Generates the Required Outputs
12. Administrator Reviews the Result and Handles Exceptional Cases

## 28. Mandatory Student Accountability Rule

This is a **critical Mighty Knight requirement**. Every student considered during the selected scheduling period must appear in the system output. The system must never silently ignore or remove students.

| Metric | Example |
|---|---|
| Total applicable students | 120 |
| Successfully scheduled | 100 |
| Unable to schedule | 20 |

The remaining 20 students must be explicitly displayed. The administrator must be able to identify exactly who was not scheduled.

## 29. Unscheduled / Administrator Attention Section

If Mighty Knight cannot find a valid schedule for a student or batch, the system must create a clearly visible section such as:

> ■ Unscheduled — Administrator Attention Required

For every unscheduled student, display relevant information such as:

- Student Name
- Student ID
- Student Level
- Batch Type
- Preferred Day
- Preferred Time
- Required Classes
- Number of Classes Successfully Allocated
- Remaining Required Classes
- Reason for Scheduling Failure

Possible reasons include:

- No suitable coach available
- No valid time slot
- Coach capacity reached
- Batch capacity reached
- Student unavailable
- No qualified coach available
- Sunday restriction
- Tournament restriction
- Scheduling conflict
- Other applicable rule

## 30. Daily Unscheduled Reporting

For a selected date, Mighty Knight must clearly show:

- Students successfully scheduled
- Students not scheduled
- Relevant student details
- Reason for the issue

The administrator should immediately know which students require manual attention.

## 31. Multi-Date and Monthly Unscheduled Reporting

The same accountability rule applies to longer scheduling periods. For a selected range or month, the system should track every student's scheduling progress. For example:

| Student | Required Classes | Scheduled | Remaining | Status |
|---|---|---|---|---|
| Student A | 8 | 8 | 0 | Completed |
| Student B | 8 | 6 | 2 | Attention Required |
| Student C | 4 | 0 | 4 | Unscheduled |

The administrator must be able to identify incomplete allocations throughout the selected period.

## 32. Suggested Exception Handling

When the system cannot automatically assign a student or batch, it should not attempt to hide the problem. Instead, it should:

- Flag the allocation.
- Explain the likely reason.
- Show the affected students.
- Display the relevant preferences and requirements.
- Indicate that administrator attention is required.

The administrator can then manually decide how to handle the exceptional situation.

## 33. Output A — Coach Communication Schedule

This output is designed for coach communication. It should contain only: Date, Day, Time and Coach names. It should not contain detailed student information.

**Monday, August 24, 2026**

| Time | Coach Names |
|---|---|
| 6:00 AM – 7:00 AM | Bathrinath |
| 6:00 PM – 7:00 PM | Bathrinath, Dhaanush, Prakash, Abinaya |
| 7:00 PM – 8:00 PM | Guruvanthana, Saravanan |

The format should be clean and easy to read.

## 34. WhatsApp-Ready Output

The system should provide a simple action: **Copy Coach Schedule**. The administrator should be able to:

> Generate → Review → Copy → Paste into WhatsApp

The copied content should already be properly formatted. No additional editing should normally be required.

## 35. Output B — Detailed Administrative Schedule

The detailed administrative output should contain complete scheduling information. For each class:

- Date
- Day
- Time
- Coach
- Student names
- Student IDs
- Student levels
- Batch type
- Number of students
- Relevant warnings or exceptions

| Field | Example |
|---|---|
| Date / Day / Time | Monday, August 24, 2026 · 6:00 PM – 7:00 PM |
| Coach | Bathrinath |
| Level / Batch | Basic 1 · Group Batch |
| Students | Student 1 — ID · Student 2 — ID · Student 3 — ID |

The detailed output must remain separate from the coach communication schedule.

## 36. Schedule Review

The administrator should be able to review:

- Total students considered
- Successfully scheduled students
- Unscheduled students
- Total classes
- Coach assignments
- Coach workload
- Batch sizes
- Capacity warnings
- Scheduling conflicts
- Students requiring administrator attention

The review process must make missing or incomplete allocations visible.

## 37. Manual Administrative Handling

Mighty Knight is an automated scheduling system, but exceptional cases may require administrator intervention. When the system flags a difficult allocation, the administrator should be able to review the affected class or student and make the necessary decision.

The system should warn the administrator when a manual decision creates:

- Coach overlap
- Coach capacity violation
- Batch capacity violation
- Student availability conflict
- Scheduling outside academy operating hours

Exceptional decisions may be handled by the administrator when required.

## 38. Schedule Status

A generated schedule should have clear status control. Possible statuses:

| Status | Description |
|---|---|
| Draft | Editable working version of the schedule. |
| Finalized | Protected from accidental modification. |

The administrator should retain appropriate control over exceptional administrative changes.

## 39. Scheduling Priority Order

Mighty Knight should broadly follow this priority:

| Priority | Description |
|---|---|
| 1. Mandatory Rules | Apply academy operating hours, Sunday rules, batch limits, and conflict restrictions. |
| 2. Student Requirements | Match level, batch, availability, preferred timing and required number of classes. |
| 3. Coach Capability | Only eligible coaches should be considered. |
| 4. Coach Priority | Apply the configured priority order for the required level. |
| 5. Availability and Capacity | Check date, time, existing assignments, daily maximum, monthly maximum and special conditions. |
| 6. Practical Optimization | Select the most suitable available assignment. |
| 7. Exception Reporting | If no valid assignment exists, flag the student or batch for administrator attention. |

## 40. Configurable Data

The following should preferably be maintained as configurable data rather than fixed code:

- Student levels
- Level group numbers
- Coach names
- Coach capability
- Level-wise coach priority
- Batch definitions
- Batch capacities
- Academy operating hours
- Time slots
- Daily coach limits
- Monthly coach capacity
- Sunday rules
- Tournament rules
- Temporary exceptions
- Special scheduling conditions

This allows Mighty Knight to adapt to future data without changing the core scheduling engine.

## 41. Dynamic Behavior with Future Excel Data

Future Excel files may contain:

- New students
- New coaches
- Different student counts
- Updated preferences
- Different coach capabilities
- Different class requirements

Mighty Knight should process the available data dynamically. The system should continue to operate according to the established scheduling rules and protocols.

The software must not assume a fixed number of:

- Students
- Coaches
- Classes
- Batches
- Scheduling days

## 42. Final System Outputs

Mighty Knight must provide three important results.

| Output | Contains | Designed For |
|---|---|---|
| Output 1 — Coach Communication Schedule | Date, Day, Time, Coach names | Quick reading, easy copying, WhatsApp communication |
| Output 2 — Detailed Administrative Schedule | Complete class allocation, coach assignment, student information, level, batch, time, warnings | Internal review, operational management, schedule verification |
| Output 3 — Unscheduled and Attention Report | Student identity, level, batch, preferences, required/scheduled/remaining classes, reason for failure | Mandatory administrator follow-up |

## 43. Core Principle

Mighty Knight is not simply a student and coach data viewer. It is a rule-driven scheduling engine. Its purpose is:

> Student Requirements + Coach Capability + Coach Priority + Availability + Batch Rules + Academy Rules = Practical Schedule

Every applicable student must be accounted for. A student should be either:

- **Scheduled**, or
- **Clearly Flagged for Administrator Attention**

There must be no silent omission.

## 44. Final Development Scope

The development process should focus on:

- Excel data input
- Dynamic data recognition
- Student scheduling
- Batch allocation
- Coach allocation
- Coach priority logic
- Daily scheduling
- Multi-date scheduling
- Monthly scheduling
- Calendar-based access
- Detailed administrative output
- Coach communication output
- WhatsApp-ready copy format
- Complete unscheduled reporting
- Exception flags
- Administrator review
- Draft and finalized schedule status

## 45. Final Requirement Summary

Mighty Knight is a dynamic academy scheduling system that receives student and coach information through Excel input, processes the available data according to Mighty Knight scheduling protocols, groups compatible students into appropriate batches, assigns suitable coaches using capability, priority, availability and capacity rules, and generates schedules for selected dates or periods.

The system must produce:

- A clean Coach Communication Schedule for WhatsApp sharing.
- A complete Detailed Administrative Schedule.
- A mandatory Unscheduled / Administrator Attention Report for every student or batch that cannot be allocated automatically.

**The most important accountability rule is:**

> Every applicable student must be represented in the final result. No student may be silently omitted.

If Mighty Knight cannot create a valid automatic allocation, the system must clearly identify the student, show the relevant scheduling details, explain the reason where possible, and flag the case for administrator attention.

---

*— End of Document —*

**MIGHTY KNIGHT Pre-Development Requirement Document · v1.0**
*Confidential — Internal Use Only · Mighty Knight Dynamic Academy Scheduling System*
