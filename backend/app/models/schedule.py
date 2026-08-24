from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class ScheduledClass(BaseModel):
    class_id: str
    date: str
    day: str
    time_slot: str
    coach_name: str
    student_level: str
    batch_type: str
    student_ids: List[str]
    student_names: List[str]
    warnings: List[str] = Field(default_factory=list)
    is_manual_override: bool = False

class UnscheduledRecord(BaseModel):
    student_id: str
    student_name: str
    student_level: str
    batch_type: str
    preferred_days: str
    preferred_time: str
    required_classes: int
    scheduled_classes: int
    remaining_classes: int
    failure_reason: str
    details: Optional[str] = ""

class CoachCommunicationSlot(BaseModel):
    date: str
    day: str
    time_slot: str
    coaches: List[str]

class ScheduleResult(BaseModel):
    schedule_id: str
    status: str = "Draft" # Draft or Finalized
    start_date: str
    end_date: str
    total_students_considered: int
    successfully_scheduled_students: int
    unscheduled_students_count: int
    accountability_passed: bool
    scheduled_classes: List[ScheduledClass]
    unscheduled_records: List[UnscheduledRecord]
    coach_schedule: List[CoachCommunicationSlot]
    created_at: str
