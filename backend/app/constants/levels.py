from typing import Tuple, Optional
import re

OFFICIAL_LEVELS = [
    "Basic 1",
    "Basic 2",
    "Beginner 1",
    "Beginner 2",
    "Early Intermediate 1",
    "Early Intermediate 2",
    "Intermediate 1",
    "Intermediate 2",
    "Advanced"
]

def normalize_batch_to_level(batch_str: str, student_id: Optional[str] = None) -> Tuple[str, bool, Optional[str]]:
    """
    Derives the official level strictly from the student's actual batch.
    Ignores G / I / L prefixes, case, extra whitespace, and minor suffixes like A, B, C, D, s.
    Returns (official_level, is_unresolved, reason).
    """
    if not batch_str or not str(batch_str).strip():
        if student_id == "MKS00050":
            return ("Early Intermediate 2", False, None)
        return ("Beginner 1", True, "Batch name is empty or missing")

    b = str(batch_str).strip()
    # Strip leading prefix G, I, L (with optional dash or space)
    core = re.sub(r'^[GILgil][\s\-_]*', '', b).strip()
    core_clean = re.sub(r'\s+', ' ', core).lower()

    if student_id == "MKS00050" or core_clean == "intermediate":
        # Confirmed by user: Ineya Individual (Batch 'I Intermediate', source level 'Early Intermediate')
        return ("Early Intermediate 2", False, None)

    # 1. Basic 1
    if re.search(r'^basic\s*1\b', core_clean) or core_clean == 'basic1':
        return ("Basic 1", False, None)

    # 2. Basic 2 (includes basic 2, basic2, basic2a, etc.)
    if re.search(r'^basic\s*2', core_clean):
        return ("Basic 2", False, None)

    # 3. Beginner 1 (includes beginner 1, beginner1a, beginner1b, beginner1c, beginner1d, beginner1s)
    if re.search(r'^beginner\s*1', core_clean):
        return ("Beginner 1", False, None)

    # 4. Beginner 2 (includes beginner 2, beginner2a, beginner2s)
    if re.search(r'^beginner\s*2', core_clean):
        return ("Beginner 2", False, None)

    # 5. Early Intermediate 1
    if re.search(r'^early\s*int[e]?rmediate\s*1', core_clean):
        return ("Early Intermediate 1", False, None)

    # 6. Early Intermediate 2
    if re.search(r'^early\s*int[e]?rmediate\s*2', core_clean):
        return ("Early Intermediate 2", False, None)

    # 7. Intermediate 1
    if re.search(r'^int[e]?rmediate\s*1', core_clean):
        return ("Intermediate 1", False, None)

    # 8. Intermediate 2
    if re.search(r'^int[e]?rmediate\s*2', core_clean):
        return ("Intermediate 2", False, None)

    # 9. Advanced
    if core_clean.startswith('advanced'):
        return ("Advanced", False, None)

    return ("Beginner 1", True, f"Batch '{batch_str}' does not match any official 9 levels")
