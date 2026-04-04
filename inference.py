import os
import json
from openai import OpenAI
from env import SentinelEnv
from grader import grade_trajectory
from models import Action


# -------------------------------
# SIMPLE FALLBACK AGENT (SAFE)
# -------------------------------
def simple_agent(obs):
    if "Fetch failed" in obs.system_narrator:
        return {"tool": "terminal", "cmd": "cat"}

    if "deprecated" in obs.terminal_logs and not obs.browser_url.endswith("v2"):
        return {"tool": "terminal", "cmd": "update_config", "args": "v2"}

    return {"tool": "browser", "cmd": "fetch"}


# -------------------------------
# PARSE LLM OUTPUT SAFELY
# -------------------------------
def parse_llm_output(content, obs):
    try:
        if "{" in content and "}" in content:
            content = content[content.find("{"):content.rfind("}") + 1]
        return json.loads(content)
    except Exception:
        return simple_agent(obs)


# -------------------------------
# LOGGING (MANDATORY FORMAT)
# -------------------------------
def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step, action, reward, done, error=None):
    error_val = error if error else "null"
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={error_val}",
        flush=True,
    )


def log_end(success, steps, score, rewards):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# -------------------------------
# MAIN EXECUTION
# -------------------------------
def run_inference():
    API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
    API_KEY = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY")
    MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")

    env = SentinelEnv()
    obs = env.reset()

    rewards = []
    done = False

    # Initialize client if key present
    client = None
    if API_KEY:
        client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    log_start("recovery", "sentinel_os", MODEL_NAME)

    while not done:
        prompt = f"""
System State: {obs.system_narrator}
Terminal Logs: {obs.terminal_logs}
Current URL: {obs.browser_url}
Files: {obs.file_system}
Step: {obs.step_count}/15

Respond ONLY with JSON action.
"""

        action_dict = None

        # -------- LLM --------
        if client:
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=100
                )
                content = response.choices[0].message.content.strip()
                action_dict = parse_llm_output(content, obs)
            except Exception:
                action_dict = None

        # -------- FALLBACK --------
        if not action_dict:
            action_dict = simple_agent(obs)

        # -------- EXECUTE --------
        try:
            action = Action(**action_dict)
        except Exception:
            action = Action(**simple_agent(obs))

        obs, reward, done, _ = env.step(action)
        rewards.append(reward)

        action_str = f"{action.tool}:{action.cmd}"
        log_step(obs.step_count, action_str, reward, done)

    # -------- FINAL --------
    final_score = grade_trajectory(env.state)

    success = not env.state["broken"]
    steps = env.state["step"]

    log_end(success, steps, final_score, rewards)


# -------------------------------
# ENTRY POINT
# -------------------------------
if __name__ == "__main__":
    run_inference()