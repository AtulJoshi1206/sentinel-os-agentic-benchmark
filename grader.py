from tasks.task_basic import grader as basic_grader
from tasks.task_logs import grader as logs_grader
from tasks.task_efficiency import grader as efficiency_grader


def grade_trajectory(state, trajectory=None):
    """
    Composite benchmark score in [0, 1].

    Equal-weight blend of:
      - task_basic       : correct recovery path
      - task_logs        : diagnostic reasoning
      - task_efficiency  : path efficiency
    """
    if trajectory is None:
        return 0.0

    basic = basic_grader(trajectory)
    logs = logs_grader(trajectory)
    efficiency = efficiency_grader(trajectory)
    return round((basic + logs + efficiency) / 3.0, 3)
