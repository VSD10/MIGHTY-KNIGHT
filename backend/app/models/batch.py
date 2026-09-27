from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class WeeklySlot(BaseModel):
    day: str = Field(..., description="Day name e.g. Monday or Mon")
    time_slot: str = Field(..., description="Time slot e.g. 08:00 PM")

class BatchModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    batch_id: str = Field(..., description="Unique batch identifier (e.g. BAT_001)")
    batch_name: str = Field(..., description="Human-readable batch name (e.g. G Intermediate 2)")
    batch_type: str = Field("G", description="Batch type: G (Group), L (Limited), I (Individual)")
    level: str = Field("Beginner 1", description="Student skill level (e.g. Basic 1, Beginner 1, Intermediate 1)")
    
    capacity_min: int = Field(4, ge=1, description="Minimum capacity required for batch")
    capacity_max: int = Field(10, ge=1, description="Maximum capacity allowed for batch")
    
    fixed_trainer: Optional[str] = Field("Unassigned", description="Assigned fixed coach/trainer name")
    schedule_timings: Optional[str] = Field("", description="Human-readable summary of timings")
    weekly_slots: List[str] = Field(default_factory=list, description="List of recurring slots like 'Mon 08:00 PM'")
    
    student_ids: List[str] = Field(default_factory=list, description="List of enrolled student IDs")
    notes: Optional[str] = Field("", description="Optional notes or admin remarks")

    @classmethod
    def default_capacity(cls, b_type: str) -> tuple[int, int]:
        b_type = (b_type or "G").upper()
        if b_type == "I":
            return (1, 1)
        elif b_type == "L":
            return (1, 4)
        return (4, 10)
