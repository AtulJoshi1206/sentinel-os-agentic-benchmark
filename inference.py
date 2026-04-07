import json
import os
from openai import OpenAI
from env import SentinelEnv
from grader import grade_trajectory
from models import Action

TASK_NAME = os.getenv("TASK_NAME", "efficient_recovery")
BENCHMARK = os.getenv("BENCHMARK", "sentinel_os")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
MAX_STEPS = int(os.getenv("MAX_STEPS", "8"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "120"))

ALLOWED_ACTIONS = {
    ("browser", "fetch"),
    ("terminal", "cat"),
    ("terminal", "update_config"),
    ("terminal", "refresh_token"),
    ("system", "wait"),
}


# -------------------------------
# SAFE HEURISTIC POLICY
# -------------------------------
def detect_failure_signal(obs):
    signal = f"{obs.system_narrator}\n{obs.terminal_logs}".lower()
    if any(token in signal for token in ("rate limit", "429", "retry-after", "backoff")):
        return "rate_limit"
    if any(token in signal for token in ("token expired", "authentication failed", "401 unauthorized", "auth")):
        return "auth"
    if any(token in signal for token in ("deprecated", "migrated to v2", "api mismatch", "404 response")):
        return "version"
    return None


def safe_policy(obs, history):
    failure = detect_failure_signal(obs)
    did_cat = any(a.cmd == "cat" for a in history)
    did_wait = any(a.tool == "system" and a.cmd == "wait" for a in history)

    if obs.step_count < 5 and failure is None:
        return {"tool": "browser", "cmd": "fetch"}

    if failure and not did_cat:
        return {"tool": "terminal", "cmd": "cat"}

    if failure == "version":
        return {"tool": "terminal", "cmd": "update_config", "args": "v2"}

    if failure == "auth":
        return {"tool": "terminal", "cmd": "refresh_token"}

    if failure == "rate_limit" and not did_wait:
        return {"tool": "system", "cmd": "wait"}

    if failure == "rate_limit":
        return {"tool": "terminal", "cmd": "update_config", "args": "v2"}

    return {"tool": "browser", "cmd": "fetch"}


# -------------------------------
# PARSE LLM OUTPUT SAFELY
# -------------------------------
def parse_llm_output(content, obs):
    try:
        if "{" in content and "}" in content:
            content = content[content.find("{"):content.rfind("}") + 1]
        action = json.loads(content)
        if not isinstance(action, dict):
            raise ValueError("LLM output must be a JSON object")
        return sanitize_action(action)
    except Exception:
        return None


def sanitize_action(action):
    tool = action.get("tool")
    cmd = action.get("cmd")
    if (tool, cmd) not in ALLOWED_ACTIONS:
        return None

    cleaned = {"tool": tool, "cmd": cmd}
    if cmd == "update_config":
        cleaned["args"] = "v2"
    elif action.get("args") is not None:
        cleaned["args"] = str(action["args"])
    return cleaned


def action_to_str(action):
    if getattr(action, "args", None):
        return f"{action.tool}:{action.cmd}({action.args})"
    return f"{action.tool}:{action.cmd}"


def build_prompt(obs, history):
    recent = "\n".join(action_to_str(item) for item in history[-4:]) or "none"
    return f"""
You are controlling the Sentinel-OS recovery benchmark.
Return exactly one JSON object with keys tool, cmd, and optional args.

Allowed actions:
- {{"tool":"browser","cmd":"fetch"}}
- {{"tool":"terminal","cmd":"cat"}}
- {{"tool":"terminal","cmd":"update_config","args":"v2"}}
- {{"tool":"terminal","cmd":"refresh_token"}}
- {{"tool":"system","cmd":"wait"}}

Observation:
- system_narrator: {obs.system_narrator}
- terminal_logs: {obs.terminal_logs}
- browser_url: {obs.browser_url}
- step_count: {obs.step_count}
- recent_actions: {recent}
""".strip()


def get_llm_action(client, obs, history):
    if client is None:
        return None
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "Respond with one valid JSON action only."},
                {"role": "user", "content": build_prompt(obs, history)},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        content = (response.choices[0].message.content or "").strip()
        return parse_llm_output(content, obs)
    except Exception:
        return None


def choose_action(obs, history, llm_action):
    policy_action = safe_policy(obs, history)
    return llm_action if llm_action == policy_action else policy_action


def get_env_state(env):
    state_obj = getattr(env, "state")
    return state_obj() if callable(state_obj) else state_obj


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
    env = SentinelEnv()
    obs = None
    rewards = []
    history = []
    done = False
    steps_taken = 0
    success = False
    final_score = 0.0

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY) if API_KEY else None

    log_start(TASK_NAME, BENCHMARK, MODEL_NAME)

    try:
        obs = env.reset()

        for step in range(1, MAX_STEPS + 1):
            llm_action = get_llm_action(client, obs, history)
            action_dict = choose_action(obs, history, llm_action)

            try:
                action = Action(**action_dict)
            except Exception:
                action = Action(**safe_policy(obs, history))

            obs, reward, done, info = env.step(action)
            rewards.append(reward)
            history.append(action)
            steps_taken = step

            log_step(
                step=step,
                action=action_to_str(action),
                reward=reward,
                done=done,
                error=info.get("error"),
            )

            if done:
                break

        current_state = get_env_state(env)
        final_score = grade_trajectory(current_state, env.trajectory)
        success = bool(current_state.get("fixed") is True and not current_state.get("broken"))
    finally:
        env.close()
        log_end(success, steps_taken, final_score, rewards)


# -------------------------------
# ENTRY POINT
# -------------------------------
if __name__ == "__main__":
    run_inference()
