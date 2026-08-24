from typing import List, Dict, Any
from app.models.schedule import ScheduleResult, UnscheduledRecord

def format_attention_report(result: ScheduleResult) -> List[Dict[str, Any]]:
    """
    Formats Output 3: Unscheduled / Administrator Attention Report (BRD Section 29, 31).
    Displays every unscheduled or partially-scheduled student with identity, level, batch, preferences, and exact reason.
    """
    report_rows = []
    for rec in result.unscheduled_records:
        row = {
            "student_id": rec.student_id,
            "student_name": rec.student_name,
            "student_level": rec.student_level,
            "batch_type": rec.batch_type,
            "preferred_days": rec.preferred_days,
            "preferred_time": rec.preferred_time,
            "required_classes": rec.required_classes,
            "scheduled_classes": rec.scheduled_classes,
            "remaining_classes": rec.remaining_classes,
            "failure_reason": rec.failure_reason,
            "details": rec.details
        }
        report_rows.append(row)
    return report_rows
