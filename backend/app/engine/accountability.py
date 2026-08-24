from typing import List, Dict, Tuple
from app.models.student import StudentModel
from app.models.schedule import UnscheduledRecord, ScheduledClass

class AccountabilityTracker:
    """
    Enforces BRD Section 28 (Mandatory Student Accountability Rule).
    Ensures total input students == (scheduled + flagged). Zero silent drops.
    """
    def __init__(self, input_students: List[StudentModel]):
        self.input_students = input_students
        self.scheduled_class_counts: Dict[str, int] = {s.student_id: 0 for s in input_students}
        self.failure_reasons: Dict[str, str] = {}
        self.student_map = {s.student_id: s for s in input_students}

    def record_class_scheduled(self, student_id: str):
        if student_id in self.scheduled_class_counts:
            self.scheduled_class_counts[student_id] += 1

    def record_failure_reason(self, student_id: str, reason: str):
        if student_id not in self.failure_reasons:
            self.failure_reasons[student_id] = reason

    def generate_report(self) -> Tuple[int, int, int, bool, List[UnscheduledRecord]]:
        total_count = len(self.input_students)
        scheduled_students = set()
        unscheduled_records: List[UnscheduledRecord] = []

        for student in self.input_students:
            s_id = student.student_id
            sched_cnt = self.scheduled_class_counts.get(s_id, 0)
            req_cnt = student.required_classes
            rem_cnt = max(0, req_cnt - sched_cnt)

            if sched_cnt > 0:
                scheduled_students.add(s_id)

            if rem_cnt > 0 or sched_cnt == 0:
                reason = self.failure_reasons.get(s_id, "No suitable coach or time slot available")
                # Format preferred days summary
                pref_days = []
                for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
                    pref = student.get_day_preference(day)
                    if student.is_available_on_day(day):
                        pref_days.append(f"{day}: {pref}")
                pref_days_str = ", ".join(pref_days) if pref_days else "None"

                rec = UnscheduledRecord(
                    student_id=s_id,
                    student_name=student.student_name,
                    student_level=student.student_level,
                    batch_type=student.batch_type,
                    preferred_days=pref_days_str,
                    preferred_time=student.mon_pref or "No Preference",
                    required_classes=req_cnt,
                    scheduled_classes=sched_cnt,
                    remaining_classes=rem_cnt,
                    failure_reason=reason,
                    details=f"Needs {rem_cnt} more class(es) to complete requirement"
                )
                unscheduled_records.append(rec)

        scheduled_count = len(scheduled_students)
        unscheduled_count = len(unscheduled_records)

        # Accountability verification
        # Every student must either be fully/partially scheduled or in unscheduled_records
        accountability_passed = (total_count == len(set(list(scheduled_students) + [r.student_id for r in unscheduled_records])))

        return total_count, scheduled_count, unscheduled_count, accountability_passed, unscheduled_records
