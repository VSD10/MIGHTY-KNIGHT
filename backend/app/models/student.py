from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator

class StudentModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    student_id: str = Field(..., description="Unique Student ID")
    student_name: str = Field(..., description="Student Name")
    student_level: str = Field(..., description="Student Level (e.g. Basic 1)")
    batch_type: str = Field("G", description="Batch Type: G, L, or I")
    batch: Optional[str] = Field(None, description="Full Batch Name/Identity (e.g. G Beginner1)")
    mkca_rating: Optional[float] = Field(None, description="MKCA Rating")
    assigned_batch_id: Optional[str] = Field(None, description="Assigned Master Batch ID")
    region_timezone: Optional[str] = Field("IST", description="Region or Time Zone")
    required_classes: int = Field(..., ge=0, description="Number of required classes")
    
    mon_pref: Optional[str] = Field("No Preference", description="Monday Preference")
    tue_pref: Optional[str] = Field("No Preference", description="Tuesday Preference")
    wed_pref: Optional[str] = Field("No Preference", description="Wednesday Preference")
    thu_pref: Optional[str] = Field("No Preference", description="Thursday Preference")
    fri_pref: Optional[str] = Field("No Preference", description="Friday Preference")
    sat_pref: Optional[str] = Field("No Preference", description="Saturday Preference")
    sun_pref: Optional[str] = Field("No Preference", description="Sunday Preference")
    
    tournament_pref: Optional[str] = Field("No", description="Tournament Preference (Yes/No)")
    additional_comments: Optional[str] = Field("", description="Additional Comments")
    
    # F1 Master Data Hub fields
    level_history: list = Field(default_factory=list, description="Level history with timestamps")
    requirement_mode: str = Field("fixed", description="Requirement mode: fixed or count_by_weekdays")
    requirement_exception: Optional[Dict[str, Any]] = Field(None, description="Documented requirement exception (>12)")
    availability: Dict[str, Any] = Field(default_factory=dict, description="Multi-window availability per weekday")
    is_morning_available: bool = Field(False, description="Explicit morning availability (before 4 PM Mon-Sat)")
    preferred_times: list = Field(default_factory=list, description="Preferred time priority order")
    preferred_coach: Optional[str] = Field(None, description="Preferred coach (soft)")
    standing_exceptions: list = Field(default_factory=list, description="Standing exceptions e.g. Saturday 9 PM")
    linked_student_id: Optional[str] = Field(None, description="Linked student unit for shared individual class")
    start_date: Optional[str] = Field(None, description="Mid-month start date")
    notes: Optional[str] = Field("", description="Administrative notes")
    is_active: bool = Field(True, description="Active status")

    def get_tournament_eligibility(self) -> str:
        """Derived read-only tournament eligibility description (Part C2)."""
        if self.batch_type == "I":
            return "Not eligible (Individual batch students never participate in tournaments)"
        if self.student_level == "Basic 1":
            return "Not eligible (Basic 1 students attend regular classes only)"
        if self.student_level == "Intermediate 2":
            return "Friday tournament (Intermediate 2)"
        if self.student_level in ["Basic 2", "Beginner 1", "Beginner 2", "Early Intermediate 1", "Early Intermediate 2", "Intermediate 1"]:
            return "Sunday tournament eligible"
        return f"Not eligible ({self.student_level} not eligible)"

    @model_validator(mode="before")
    @classmethod
    def normalize_batch_and_level(cls, values: Any) -> Any:
        if isinstance(values, dict):
            # Infer batch_type and batch
            raw_batch = values.get("batch") or values.get("batch_type") or "G"
            raw_batch_str = str(raw_batch).strip()
            if not values.get("batch") and raw_batch_str:
                values["batch"] = raw_batch_str
            
            # Extract prefix G/L/I
            prefix = raw_batch_str[:1].upper() if raw_batch_str else "G"
            if prefix in ["G", "L", "I"]:
                values["batch_type"] = prefix
            else:
                values["batch_type"] = "G"

            if "mkca_rating" in values and values["mkca_rating"] is not None:
                try:
                    values["mkca_rating"] = float(values["mkca_rating"])
                except (ValueError, TypeError):
                    import re
                    nums = [float(x) for x in re.findall(r"\d+\.?\d*", str(values["mkca_rating"]))]
                    values["mkca_rating"] = sum(nums) / len(nums) if nums else None
        return values

    def get_batch_identity(self) -> str:
        if self.batch and str(self.batch).strip():
            return str(self.batch).strip()
        return f"{self.batch_type} {self.student_level}"

    def get_day_preference(self, day_name: str) -> str:
        day_map = {
            "Monday": self.mon_pref,
            "Tuesday": self.tue_pref,
            "Wednesday": self.wed_pref,
            "Thursday": self.thu_pref,
            "Friday": self.fri_pref,
            "Saturday": self.sat_pref,
            "Sunday": self.sun_pref
        }
        val = day_map.get(day_name, "No Preference")
        if not val or str(val).strip().lower() in ["nan", "none", "", "null"]:
            return "No Preference"
        return str(val).strip()

    def is_available_on_day(self, day_name: str) -> bool:
        pref = self.get_day_preference(day_name).lower()
        if pref in ["not available", "na", "no", "false", "0", "off"]:
            return False
        return True

