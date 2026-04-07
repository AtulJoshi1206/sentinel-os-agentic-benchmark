from grader import TASK_GRADERS as GRADERS, grade_trajectory
from tasks import (
    ALL_TASKS,
    TASK_GRADERS,
    grade_basic_recovery,
    grade_efficient_recovery,
    grade_log_diagnosis,
)


ALL_GRADERS = TASK_GRADERS


def grade_task(task_id, trajectory):
    grader = GRADERS.get(task_id)
    if grader is None:
        return 0.0
    return round(grader(trajectory), 3)
