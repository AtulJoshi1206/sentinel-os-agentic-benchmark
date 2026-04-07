from task_modules.task_basic import grader as basic_grader
from task_modules.task_logs import grader as logs_grader
from task_modules.task_efficiency import grader as efficiency_grader
from task_modules._score import strict_unit_interval

TASK_GRADERS = {
    "task_basic": basic_grader,
    "task_logs": logs_grader,
    "task_efficiency": efficiency_grader,
}

_ALL_GRADERS = {
    "basic_recovery": basic_grader,
    "log_diagnosis": logs_grader,
    "efficient_recovery": efficiency_grader,
    "easy": basic_grader,
    "medium": logs_grader,
    "hard": efficiency_grader,
    **TASK_GRADERS,
}


def grade_trajectory(state, trajectory=None, task_id=None):
    """
    Composite benchmark score in [0, 1].

    Equal-weight blend of:
      - task_basic       : correct recovery path
      - task_logs        : diagnostic reasoning
      - task_efficiency  : path efficiency
    """
    if trajectory is None:
        return strict_unit_interval(0.0)

    if task_id in _ALL_GRADERS:
        return strict_unit_interval(_ALL_GRADERS[task_id](trajectory))

    basic = basic_grader(trajectory)
    logs = logs_grader(trajectory)
    efficiency = efficiency_grader(trajectory)
    return strict_unit_interval((basic + logs + efficiency) / 3.0)
