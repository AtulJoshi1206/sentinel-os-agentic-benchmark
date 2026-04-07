from typing import Optional
import os
from fastapi import FastAPI
from pydantic import BaseModel
from env import SentinelEnv
from models import Action, Observation
from grader import TASK_GRADERS, grade_trajectory
from tasks import TASKS

app = FastAPI()
env_instance = SentinelEnv()


class ResetRequest(BaseModel):
    task_id: str = "efficient_recovery"

@app.get("/")
def root():
    return {
        "status": "Sentinel-OS Benchmark Running",
        "version": "1.0.0",
        "endpoints": ["/reset", "/step", "/state", "/tasks", "/grader", "/validate", "/metadata", "/schema", "/baseline"],
    }

# ✅ SUPPORT BOTH GET AND POST
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
            "has_grader": True,
            "grader_id": task["task_id"],
            "grader_endpoint": f"/grader?task_id={task['task_id']}",
        }
        for task in TASKS
    ]


@app.get("/grader")
def grader(task_id: Optional[str] = None):
    current_state = env_instance.state()
    if task_id is None:
        return {
            "graders": sorted(TASK_GRADERS.keys()),
            "count": len(TASK_GRADERS),
        }
    active_task = task_id
    score = grade_trajectory(current_state, env_instance.trajectory, task_id=active_task)
    return {
        "task_id": active_task,
        "score": score,
        "available_graders": sorted(TASK_GRADERS.keys()),
    }


@app.get("/validate")
def validate():
    task_ids = {task["id"] for task in TASKS}
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


@app.get("/metadata")
def metadata():
    return {
        "name": "sentinel_os",
        "description": "Production-grade agentic recovery benchmark",
        "version": "2.0.0",
        "tags": ["openenv", "reliability", "incident-response"],
        "tasks_count": len(TASKS),
        "graders_count": len(TASK_GRADERS),
    }


@app.get("/schema")
def schema():
    return {
        "action": Action.model_json_schema(),
        "observation": Observation.model_json_schema(),
        "state": {"type": "object"},
    }


@app.get("/baseline")
def baseline():
    scores = {}
    for task in TASKS:
        task_id = task["task_id"]
        cmd = f"TASK_NAME={task_id} python3 inference.py"
        scores[task_id] = {"task_id": task_id, "command": cmd}
    return {
        "tasks": scores,
        "inference_script": "inference.py",
        "model": os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct"),
    }


def main():
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
