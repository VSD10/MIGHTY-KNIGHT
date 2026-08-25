import json
import os
from typing import Dict, List, Any
from pydantic import BaseModel

class BatchConfig(BaseModel):
    symbol: str
    name: str
    min_capacity: int
    max_capacity: int

class SundayConfig(BaseModel):
    start_time: str = "09:00"
    max_end_time: str = "15:00"
    excluded_tournament_coaches: List[str] = ["Dhaanush", "Saravanan"]
    excluded_tournament_levels: List[str] = ["Intermediate"]

class SystemConfig(BaseModel):
    student_levels: List[str] = [
        "Basic 1",
        "Basic 2",
        "Beginner 1",
        "Beginner 2",
        "Beginner 3",
        "Early Intermediate 1",
        "Early Intermediate 2",
        "Intermediate"
    ]
    
    level_groups: Dict[str, int] = {
        "Basic 1": 1,
        "Basic 2": 2,
        "Beginner 1": 3,
        "Beginner 2": 4,
        "Beginner 3": 5,
        "Early Intermediate 1": 6,
        "Early Intermediate 2": 7,
        "Intermediate": 8
    }

    coach_priority: Dict[str, List[str]] = {
        "Basic 1": ["Bathrinath", "Abinaya", "Manikandan", "Prakash", "Guruvanthana"],
        "Basic 2": ["Bathrinath", "Abinaya", "Manikandan", "Prakash", "Guruvanthana"],
        "Beginner 1": ["Bathrinath", "Guruvanthana", "Dhaanush", "Manikandan", "Abinaya", "Prakash"],
        "Beginner 2": ["Guruvanthana", "Dhaanush", "Bathrinath", "Prakash", "Saravanan"],
        "Beginner 3": ["Dhaanush", "Guruvanthana", "Prakash", "Saravanan"],
        "Early Intermediate 1": ["Dhaanush", "Saravanan", "Prakash", "Guruvanthana"],
        "Early Intermediate 2": ["Dhaanush", "Arshath", "Prakash"],
        "Intermediate": ["Arshath", "Dhaanush", "Prakash", "Saravanan"]
    }

    batch_types: Dict[str, BatchConfig] = {
        "G": BatchConfig(symbol="G", name="Group Batch", min_capacity=4, max_capacity=10),
        "L": BatchConfig(symbol="L", name="Limited Students Batch", min_capacity=1, max_capacity=3),
        "I": BatchConfig(symbol="I", name="Individual Batch", min_capacity=1, max_capacity=1)
    }

    weekday_slots: List[str] = [
        "06:00 AM – 07:00 AM",
        "07:00 AM – 08:00 AM",
        "09:00 AM – 10:00 AM",
        "10:00 AM – 11:00 AM",
        "11:00 AM – 12:00 PM",
        "12:00 PM – 01:00 PM",
        "01:00 PM – 02:00 PM",
        "04:00 PM – 05:00 PM",
        "05:00 PM – 06:00 PM",
        "06:00 PM – 07:00 PM",
        "07:00 PM – 08:00 PM",
        "08:00 PM – 09:00 PM",
        "09:00 PM – 10:00 PM"
    ]

    sunday_slots: List[str] = [
        "09:00 AM – 10:00 AM",
        "10:00 AM – 11:00 AM",
        "11:00 AM – 12:00 PM",
        "12:00 PM – 01:00 PM",
        "01:00 PM – 02:00 PM",
        "02:00 PM – 03:00 PM"
    ]

    saturday_peak_slots: List[str] = [
        "05:00 PM – 06:00 PM",
        "06:00 PM – 07:00 PM",
        "07:00 PM – 08:00 PM",
        "08:00 PM – 09:00 PM"
    ]

    sunday_rules: SundayConfig = SundayConfig()

def load_config(config_path: str = None) -> SystemConfig:
    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return SystemConfig(**data)
    return SystemConfig()

def save_config(config: SystemConfig, config_path: str):
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, indent=2)

# Global default configuration instance
DEFAULT_CONFIG = SystemConfig()
