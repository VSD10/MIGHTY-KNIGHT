import json
import os
from typing import Dict, List, Any
from pydantic import BaseModel, Field

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

class ConstraintRule(BaseModel):
    rule_id: str
    name: str
    description: str
    category: str
    constraint_type: str = "HARD_CONSTRAINT"  # "HARD_CONSTRAINT" or "SOFT_CONSTRAINT"
    enabled: bool = True
    priority: int = 1
    params: Dict[str, Any] = {}

def get_default_rules_registry() -> List[ConstraintRule]:
    return [
        ConstraintRule(
            rule_id="RULE_BATCH_CAPACITY",
            name="Group & Batch Size Capacity Bounds",
            description="Enforces min and max student limits per batch type (Group: 4-10, Limited: 1-4, Individual: 1).",
            category="Batch Capacity",
            constraint_type="HARD_CONSTRAINT",
            enabled=True,
            priority=1,
            params={
                "g_min": 4, "g_max": 10,
                "l_min": 1, "l_max": 4,
                "i_min": 1, "i_max": 1
            }
        ),
        ConstraintRule(
            rule_id="RULE_STUDENT_DAILY_LIMIT",
            name="Student Daily Class Uniqueness",
            description="Enforces at most 1 class per student per calendar date (max 1 class/day).",
            category="Student Limits",
            constraint_type="HARD_CONSTRAINT",
            enabled=True,
            priority=1,
            params={
                "max_classes_per_day": 1
            }
        ),
        ConstraintRule(
            rule_id="RULE_SUNDAY_TOURNAMENT",
            name="Sunday Operating Hours & Tournament Cap",
            description="Restricts Sunday classes to end by 3:00 PM and excludes tournament coaches/levels.",
            category="Sunday Rules",
            constraint_type="HARD_CONSTRAINT",
            enabled=True,
            priority=1,
            params={
                "max_end_time": "15:00",
                "excluded_tournament_coaches": ["Dhaanush", "Saravanan"],
                "excluded_tournament_levels": ["Intermediate"]
            }
        ),
        ConstraintRule(
            rule_id="RULE_COACH_PRIORITY",
            name="Coach Capability & Level Priority Matrix",
            description="Routes student levels strictly to qualified coaches ordered by preferred priority list.",
            category="Coach Capability",
            constraint_type="HARD_CONSTRAINT",
            enabled=True,
            priority=1,
            params={
                "coach_priority": {
                    "Basic 1": ["Bathrinath", "Abinaya", "Manikandan", "Prakash", "Guruvanthana"],
                    "Basic 2": ["Bathrinath", "Abinaya", "Manikandan", "Prakash", "Guruvanthana"],
                    "Beginner 1": ["Bathrinath", "Guruvanthana", "Dhaanush", "Manikandan", "Abinaya", "Prakash"],
                    "Beginner 2": ["Guruvanthana", "Dhaanush", "Bathrinath", "Prakash", "Saravanan"],
                    "Beginner 3": ["Guruvanthana", "Dhaanush", "Bathrinath", "Prakash", "Saravanan"],
                    "Early Intermediate 1": ["Dhaanush", "Saravanan", "Arshath", "Prakash", "Guruvanthana"],
                    "Early Intermediate 2": ["Dhaanush", "Saravanan", "Arshath", "Prakash", "Guruvanthana"],
                    "Intermediate": ["Arshath", "Dhaanush", "Prakash", "Saravanan"]
                }
            }
        ),
        ConstraintRule(
            rule_id="RULE_OPERATING_TIME_SLOTS",
            name="Academy Operating Time Slots",
            description="Defines allowable weekday (06:00 AM – 10:00 PM) and Sunday (09:00 AM – 03:00 PM) slot windows.",
            category="Time Slots",
            constraint_type="HARD_CONSTRAINT",
            enabled=True,
            priority=1,
            params={
                "weekday_slots": [
                    "06:00 AM – 07:00 AM", "07:00 AM – 08:00 AM", "09:00 AM – 10:00 AM",
                    "10:00 AM – 11:00 AM", "11:00 AM – 12:00 PM", "12:00 PM – 01:00 PM",
                    "01:00 PM – 02:00 PM", "04:00 PM – 05:00 PM", "05:00 PM – 06:00 PM",
                    "06:00 PM – 07:00 PM", "07:00 PM – 08:00 PM", "08:00 PM – 09:00 PM",
                    "09:00 PM – 10:00 PM"
                ],
                "sunday_slots": [
                    "09:00 AM – 10:00 AM", "10:00 AM – 11:00 AM", "11:00 AM – 12:00 PM",
                    "12:00 PM – 01:00 PM", "01:00 PM – 02:00 PM", "02:00 PM – 03:00 PM"
                ]
            }
        )
    ]

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
        "Beginner 3": ["Guruvanthana", "Dhaanush", "Bathrinath", "Prakash", "Saravanan"],
        "Early Intermediate 1": ["Dhaanush", "Saravanan", "Arshath", "Prakash", "Guruvanthana"],
        "Early Intermediate 2": ["Dhaanush", "Saravanan", "Arshath", "Prakash", "Guruvanthana"],
        "Intermediate": ["Arshath", "Dhaanush", "Prakash", "Saravanan"]
    }

    batch_types: Dict[str, BatchConfig] = {
        "G": BatchConfig(symbol="G", name="Group Batch", min_capacity=4, max_capacity=10),
        "L": BatchConfig(symbol="L", name="Limited Students Batch", min_capacity=1, max_capacity=4),
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
    rules_registry: List[ConstraintRule] = Field(default_factory=get_default_rules_registry)

    def sync_from_rules_registry(self):
        """
        Synchronizes internal fields (batch_types, sunday_rules, coach_priority, weekday_slots, sunday_slots)
        with values from rules_registry if present.
        """
        for r in self.rules_registry:
            if r.rule_id == "RULE_BATCH_CAPACITY" and r.params:
                g_min = r.params.get("g_min", self.batch_types["G"].min_capacity)
                g_max = r.params.get("g_max", self.batch_types["G"].max_capacity)
                l_min = r.params.get("l_min", self.batch_types["L"].min_capacity)
                l_max = r.params.get("l_max", self.batch_types["L"].max_capacity)
                i_min = r.params.get("i_min", self.batch_types["I"].min_capacity)
                i_max = r.params.get("i_max", self.batch_types["I"].max_capacity)

                self.batch_types["G"] = BatchConfig(symbol="G", name="Group Batch", min_capacity=g_min, max_capacity=g_max)
                self.batch_types["L"] = BatchConfig(symbol="L", name="Limited Students Batch", min_capacity=l_min, max_capacity=l_max)
                self.batch_types["I"] = BatchConfig(symbol="I", name="Individual Batch", min_capacity=i_min, max_capacity=i_max)

            elif r.rule_id == "RULE_SUNDAY_TOURNAMENT" and r.params:
                max_end = r.params.get("max_end_time", self.sunday_rules.max_end_time)
                coaches = r.params.get("excluded_tournament_coaches", self.sunday_rules.excluded_tournament_coaches)
                levels = r.params.get("excluded_tournament_levels", self.sunday_rules.excluded_tournament_levels)
                self.sunday_rules = SundayConfig(
                    max_end_time=max_end,
                    excluded_tournament_coaches=coaches,
                    excluded_tournament_levels=levels
                )

            elif r.rule_id == "RULE_COACH_PRIORITY" and r.params:
                cp = r.params.get("coach_priority")
                if cp and isinstance(cp, dict):
                    self.coach_priority = cp

            elif r.rule_id == "RULE_OPERATING_TIME_SLOTS" and r.params:
                w_slots = r.params.get("weekday_slots")
                s_slots = r.params.get("sunday_slots")
                if w_slots and isinstance(w_slots, list):
                    self.weekday_slots = w_slots
                if s_slots and isinstance(s_slots, list):
                    self.sunday_slots = s_slots

    def sync_to_rules_registry(self):
        """
        Updates parameters inside rules_registry to reflect internal fields.
        """
        registry_map = {r.rule_id: r for r in self.rules_registry}

        if "RULE_BATCH_CAPACITY" in registry_map:
            registry_map["RULE_BATCH_CAPACITY"].params = {
                "g_min": self.batch_types["G"].min_capacity,
                "g_max": self.batch_types["G"].max_capacity,
                "l_min": self.batch_types["L"].min_capacity,
                "l_max": self.batch_types["L"].max_capacity,
                "i_min": self.batch_types["I"].min_capacity,
                "i_max": self.batch_types["I"].max_capacity
            }

        if "RULE_SUNDAY_TOURNAMENT" in registry_map:
            registry_map["RULE_SUNDAY_TOURNAMENT"].params = {
                "max_end_time": self.sunday_rules.max_end_time,
                "excluded_tournament_coaches": self.sunday_rules.excluded_tournament_coaches,
                "excluded_tournament_levels": self.sunday_rules.excluded_tournament_levels
            }

        if "RULE_COACH_PRIORITY" in registry_map:
            registry_map["RULE_COACH_PRIORITY"].params = {
                "coach_priority": self.coach_priority
            }

        if "RULE_OPERATING_TIME_SLOTS" in registry_map:
            registry_map["RULE_OPERATING_TIME_SLOTS"].params = {
                "weekday_slots": self.weekday_slots,
                "sunday_slots": self.sunday_slots
            }

def load_config(config_path: str = None) -> SystemConfig:
    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            cfg = SystemConfig(**data)
            cfg.sync_from_rules_registry()
            return cfg
    cfg = SystemConfig()
    cfg.sync_to_rules_registry()
    return cfg

def save_config(config: SystemConfig, config_path: str):
    config.sync_to_rules_registry()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, indent=2)

# Global default configuration instance
DEFAULT_CONFIG = SystemConfig()
DEFAULT_CONFIG.sync_to_rules_registry()
