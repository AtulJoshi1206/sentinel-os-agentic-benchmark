from tasks.task_basic import grader as basic_recovery_grader
from tasks.task_logs import grader as log_diagnosis_grader
from tasks.task_efficiency import grader as efficient_recovery_grader

TASKS = [
    {
        "id": "basic_recovery",
        "task_id": "basic_recovery",
        "name": "Basic Recovery",
        "difficulty": "easy",
        "description": "Apply the correct hidden-failure fix.",
        "max_steps": 15,
        "success_threshold": 0.95,
    },
    {
        "id": "log_diagnosis",
        "task_id": "log_diagnosis",
        "name": "Log Diagnosis",
        "difficulty": "medium",
        "description": "Inspect logs before applying the correct fix.",
        "max_steps": 15,
        "success_threshold": 0.95,
    },
    {
        "id": "efficient_recovery",
        "task_id": "efficient_recovery",
        "name": "Efficient Recovery",
        "difficulty": "hard",
        "description": "Recover with the minimum viable recovery path.",
        "max_steps": 15,
        "success_threshold": 0.30,
    },
]

GRADERS = {
    "basic_recovery": basic_recovery_grader,
    "log_diagnosis": log_diagnosis_grader,
    "efficient_recovery": efficient_recovery_grader,
}
