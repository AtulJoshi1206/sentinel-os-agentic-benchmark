from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel
from env import SentinelEnv
from models import Action
from grader import TASK_GRADERS, grade_trajectory

app = FastAPI()
env_instance = SentinelEnv()


class ResetRequest(BaseModel):
    task_id: str = "efficient_recovery"

@app.get("/")
def root():
    return {
        "status": "Sentinel-OS Benchmark Running",
        "version": "1.0.0",
        "endpoints": ["/reset", "/step", "/state", "/tasks", "/grader", "/validate"],
    }

@app.get("/reset")
@app.post("/reset")
def reset(req: Optional[ResetRequest] = None):
    req = req or ResetRequest()
    obs = env_instance.reset(task_id=req.task_id)
    return obs.dict()

@app.post("/step")
def step(action: dict):
    action_obj = Action(**action)
    obs, reward, done, info = env_instance.step(action_obj)
    return {
        "observation": obs.dict(),
        "reward": reward,
        "done": done,
        "error": info.get("error"),
    }

@app.get("/state")
def state():
    return env_instance.state()


@app.get("/tasks")
def tasks():
    return [
        {
            **task,
            "grader": True,
        }
        for task in env_instance.tasks()
    ]


@app.get("/grader")
def grader(task_id: Optional[str] = None):
    current_state = env_instance.state()
    active_task = task_id or current_state.get("task_id", "efficient_recovery")
    score = grade_trajectory(current_state, env_instance.trajectory, task_id=active_task)
    return {
        "task_id": active_task,
        "score": score,
        "available_graders": sorted(TASK_GRADERS.keys()),
    }


@app.get("/validate")
def validate():
    task_ids = {task["id"] for task in env_instance.tasks()}
    return {
        "valid": len(task_ids & set(TASK_GRADERS)) >= 3,
        "checks": {
            "min_3_tasks": len(task_ids) >= 3,
            "all_tasks_have_graders": all(task_id in TASK_GRADERS for task_id in task_ids),
            "state_endpoint": True,
            "step_endpoint": True,
            "reset_endpoint": True,
        },
    }
