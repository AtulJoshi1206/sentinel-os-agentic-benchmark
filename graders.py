from grader import TASK_GRADERS as GRADERS, grade_trajectory


def grade_task(task_id, trajectory):
    grader = GRADERS.get(task_id)
    if grader is None:
        return 0.0
    return round(grader(trajectory), 3)
