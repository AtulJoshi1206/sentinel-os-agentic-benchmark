from fastapi import FastAPI
from env import SentinelEnv
from models import Action

app = FastAPI()
env_instance = SentinelEnv()

@app.get("/")
def root():
    return {"status": "Sentinel-OS Benchmark Running", "version": "1.0.0"}

# ✅ SUPPORT BOTH GET AND POST
@app.get("/reset")
@app.post("/reset")
def reset():
    obs = env_instance.reset()
    return obs.dict()

@app.post("/step")
def step(action: dict):
    action_obj = Action(**action)
    obs, reward, done, _ = env_instance.step(action_obj)
    return {
        "observation": obs.dict(),
        "reward": reward,
        "done": done
    }

@app.get("/state")
def state():
    return env_instance.state


def main():
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()