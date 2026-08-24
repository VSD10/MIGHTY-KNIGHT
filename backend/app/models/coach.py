from typing import List, Optional, Dict
from pydantic import BaseModel, Field, ConfigDict

class CoachModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    coach_name: str = Field(..., description="Coach Name")
    levels_handled: List[str] = Field(default_factory=list, description="Levels the coach can handle")
    monthly_capacity_min: int = Field(0, description="Preferred workload target (lower bound)")
    monthly_capacity_max: int = Field(100, description="Maximum permitted capacity (upper bound)")
    
    # Daily max limits
    mon_max: int = Field(4, ge=0, description="Monday max classes")
    tue_max: int = Field(4, ge=0, description="Tuesday max classes")
    wed_max: int = Field(4, ge=0, description="Wednesday max classes")
    thu_max: int = Field(4, ge=0, description="Thursday max classes")
    fri_max: int = Field(4, ge=0, description="Friday max classes")
    sat_max: int = Field(5, ge=0, description="Saturday max classes")
    sun_max: int = Field(2, ge=0, description="Sunday max classes")

    day_wise_availability: Optional[Dict[str, str]] = Field(default_factory=dict)
    preferred_timings: Optional[str] = Field("No Preference", description="Preferred timings")
    sunday_pref: Optional[str] = Field("Available", description="Sunday preference")
    sunday_max_classes: Optional[int] = Field(2, ge=0, description="Sunday maximum classes")
    special_comments: Optional[str] = Field("", description="Special comments")
    temporary_exceptions: Optional[str] = Field("", description="Temporary exceptions")

    def get_daily_max(self, day_name: str) -> int:
        day_map = {
            "Monday": self.mon_max,
            "Tuesday": self.tue_max,
            "Wednesday": self.wed_max,
            "Thursday": self.thu_max,
            "Friday": self.fri_max,
            "Saturday": self.sat_max,
            "Sunday": self.sun_max if self.sunday_max_classes is None else self.sunday_max_classes
        }
        return day_map.get(day_name, 4)

    def can_handle_level(self, level: str) -> bool:
        normalized_handled = [l.strip().lower() for l in self.levels_handled]
        return level.strip().lower() in normalized_handled
