from fastapi import FastAPI
import uvicorn
from env import SentinelEnv
from models import Action

def create_app():
    app = FastAPI()
    env_instance = SentinelEnv()

    @app.get("/")
    def root():
        return {"status": "Sentinel-OS Benchmark Running", "version": "1.0.0"}

    @app.get("/reset")
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

    return app


# Required by OpenEnv
def main():
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=7860)


# For validator
if __name__ == "__main__":
    main()


# Export app for ASGI
app = create_app()