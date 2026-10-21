import math
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
    Groups candidate students of the same level and batch_type into balanced BatchGroup instances.
    Uses balanced partitioning so groups are spread evenly across capacity bounds.
    """
    if not candidate_students:
        return []

    batch_cfg = config.batch_types.get(batch_type, config.batch_types["G"])
    max_cap = batch_cfg.max_capacity
    total = len(candidate_students)

    num_groups = max(1, math.ceil(total / max_cap))

    groups: List[BatchGroup] = [BatchGroup(level, batch_type, batch_cfg) for _ in range(num_groups)]
    for i, student in enumerate(candidate_students):
        group_idx = i % num_groups
        groups[group_idx].add_student(student)

    return [g for g in groups if len(g.students) > 0]
