from typing import List, Dict, Any, Tuple
from app.models.student import StudentModel
from app.config import SystemConfig, BatchConfig

class BatchGroup:
    def __init__(self, level: str, batch_type: str, config: BatchConfig):
        self.level = level
        self.batch_type = batch_type
        self.config = config
        self.students: List[StudentModel] = []

    def can_add_student(self, student: StudentModel) -> bool:
        if student.student_level != self.level or student.batch_type != self.batch_type:
            return False
        return len(self.students) < self.config.max_capacity

    def add_student(self, student: StudentModel) -> bool:
        if self.can_add_student(student):
            self.students.append(student)
            return True
        return False

    def is_valid(self) -> bool:
        if self.batch_type == "G":
            return len(self.students) >= self.config.min_capacity and len(self.students) <= self.config.max_capacity
        return len(self.students) > 0 and len(self.students) <= self.config.max_capacity

    def get_warnings(self) -> List[str]:
        warnings = []
        if self.batch_type == "G" and len(self.students) < self.config.min_capacity:
            warnings.append(f"Group batch size ({len(self.students)}) below target minimum ({self.config.min_capacity})")
        return warnings

def group_students_for_slot(
    candidate_students: List[StudentModel],
    level: str,
    batch_type: str,
    config: SystemConfig
) -> List[BatchGroup]:
    """
    Groups candidate students of the same level and batch_type into valid BatchGroup instances.
    Each group will contain between 1 and max_capacity students.
    """
    batch_cfg = config.batch_types.get(batch_type, config.batch_types["G"])
    groups: List[BatchGroup] = []
    
    current_group = BatchGroup(level, batch_type, batch_cfg)

    for student in candidate_students:
        if not current_group.can_add_student(student):
            groups.append(current_group)
            current_group = BatchGroup(level, batch_type, batch_cfg)
        current_group.add_student(student)

    if len(current_group.students) > 0:
        groups.append(current_group)

    return groups
