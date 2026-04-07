from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, List

from tasks.task_basic import grader as basic_recovery_grader
from tasks.task_efficiency import grader as efficient_recovery_grader
from tasks.task_logs import grader as log_diagnosis_grader


@dataclass(frozen=True)
class Task:
    """Validator-facing task descriptor with attached deterministic grader."""

    task_id: str
    name: str
    difficulty: str
    description: str
    max_steps: int
    success_threshold: float
    grader: Callable
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["id"] = self.task_id
        data["episode_length"] = self.max_steps
        data["grader"] = True
        data["has_grader"] = True
        data["grader_id"] = self.task_id
        return data


TASK_BASIC_RECOVERY = Task(
    task_id="basic_recovery",
    name="Basic Recovery",
    difficulty="easy",
    description="Apply the correct hidden-failure fix.",
    max_steps=15,
    success_threshold=0.95,
    grader=basic_recovery_grader,
    tags=["recovery", "incident-response", "easy"],
)

TASK_LOG_DIAGNOSIS = Task(
    task_id="log_diagnosis",
    name="Log Diagnosis",
    difficulty="medium",
    description="Inspect logs before applying the correct fix.",
    max_steps=15,
    success_threshold=0.95,
    grader=log_diagnosis_grader,
    tags=["logs", "diagnosis", "medium"],
)

TASK_EFFICIENT_RECOVERY = Task(
    task_id="efficient_recovery",
    name="Efficient Recovery",
    difficulty="hard",
    description="Recover with the minimum viable recovery path.",
    max_steps=15,
    success_threshold=0.30,
    grader=efficient_recovery_grader,
    tags=["efficiency", "recovery", "hard"],
)

# Conventional names that private validators may scan for.
TASK_EASY = TASK_BASIC_RECOVERY
TASK_MEDIUM = TASK_LOG_DIAGNOSIS
TASK_HARD = TASK_EFFICIENT_RECOVERY

ALL_TASKS = [
    TASK_BASIC_RECOVERY,
    TASK_LOG_DIAGNOSIS,
    TASK_EFFICIENT_RECOVERY,
]

TASKS = [task.to_dict() for task in ALL_TASKS]


def grade_basic_recovery(trajectory) -> float:
    return round(basic_recovery_grader(trajectory), 3)


def grade_log_diagnosis(trajectory) -> float:
    return round(log_diagnosis_grader(trajectory), 3)


def grade_efficient_recovery(trajectory) -> float:
    return round(efficient_recovery_grader(trajectory), 3)


def grade_easy(trajectory) -> float:
    return grade_basic_recovery(trajectory)


def grade_medium(trajectory) -> float:
    return grade_log_diagnosis(trajectory)


def grade_hard(trajectory) -> float:
    return grade_efficient_recovery(trajectory)


GRADERS = {
    TASK_BASIC_RECOVERY.task_id: grade_basic_recovery,
    TASK_LOG_DIAGNOSIS.task_id: grade_log_diagnosis,
    TASK_EFFICIENT_RECOVERY.task_id: grade_efficient_recovery,
}

TASK_GRADERS = GRADERS
ALL_GRADERS = {
    "easy": grade_easy,
    "medium": grade_medium,
    "hard": grade_hard,
    **TASK_GRADERS,
}
