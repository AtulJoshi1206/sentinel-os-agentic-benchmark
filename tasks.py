from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, List

from task_modules.task_basic import grader as basic_recovery_grader
from task_modules.task_efficiency import grader as efficient_recovery_grader
from task_modules.task_logs import grader as log_diagnosis_grader


@dataclass(frozen=True)
class Task:
    """Canonical top-level task registry for validator discovery."""

    task_id: str
    name: str
    description: str
    difficulty: str
    episode_length: int
    success_threshold: float
    grader: Callable
    tags: List[str] = field(default_factory=list)

    @property
    def max_steps(self) -> int:
        return self.episode_length

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["id"] = self.task_id
        data["max_steps"] = self.episode_length
        data["grader"] = True
        data["has_grader"] = True
        data["grader_id"] = self.task_id
        return data


TASK_EASY = Task(
    task_id="task_basic",
    name="Basic Recovery",
    description="Apply the correct hidden-failure fix.",
    difficulty="easy",
    episode_length=15,
    success_threshold=0.95,
    grader=basic_recovery_grader,
    tags=["recovery", "incident-response", "easy"],
)

TASK_MEDIUM = Task(
    task_id="task_logs",
    name="Log Diagnosis",
    description="Inspect logs before applying the correct fix.",
    difficulty="medium",
    episode_length=15,
    success_threshold=0.95,
    grader=log_diagnosis_grader,
    tags=["logs", "diagnosis", "medium"],
)

TASK_HARD = Task(
    task_id="task_efficiency",
    name="Efficient Recovery",
    description="Recover with the minimum viable recovery path.",
    difficulty="hard",
    episode_length=15,
    success_threshold=0.30,
    grader=efficient_recovery_grader,
    tags=["efficiency", "recovery", "hard"],
)

TASK_BASIC_RECOVERY = TASK_EASY
TASK_LOG_DIAGNOSIS = TASK_MEDIUM
TASK_EFFICIENT_RECOVERY = TASK_HARD

ALL_TASKS = [
    TASK_EASY,
    TASK_MEDIUM,
    TASK_HARD,
]

TASKS = [task.to_dict() for task in ALL_TASKS]


def grade_easy(trajectory) -> float:
    return round(basic_recovery_grader(trajectory), 3)


def grade_medium(trajectory) -> float:
    return round(log_diagnosis_grader(trajectory), 3)


def grade_hard(trajectory) -> float:
    return round(efficient_recovery_grader(trajectory), 3)


def grade_basic_recovery(trajectory) -> float:
    return grade_easy(trajectory)


def grade_log_diagnosis(trajectory) -> float:
    return grade_medium(trajectory)


def grade_efficient_recovery(trajectory) -> float:
    return grade_hard(trajectory)


GRADERS = {
    TASK_EASY.task_id: grade_easy,
    TASK_MEDIUM.task_id: grade_medium,
    TASK_HARD.task_id: grade_hard,
}

TASK_GRADERS = GRADERS
ALL_GRADERS = {
    "easy": grade_easy,
    "medium": grade_medium,
    "hard": grade_hard,
    **TASK_GRADERS,
}
