---
title: Sentinel-OS Agentic Benchmark
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
app_file: app.py
pinned: false
tags:
  - openenv
---

# Sentinel-OS: Agentic Recovery Benchmark

## What this evaluates

Sentinel-OS evaluates whether an AI agent can **detect, diagnose, and recover from hidden system failures** using multi-step reasoning.

Unlike conventional environments, failures are not explicitly exposed.  
Agents must infer them from logs, system responses, and evolving state.

The objective is not just task completion — but **intelligent, efficient recovery under uncertainty**.

---

## Core Scenario

The environment simulates a production API cluster with a hidden failure that appears only after several normal interactions.

- Initial state: the cluster looks healthy
- At step 5: a failure is injected silently
- Hidden failure mode is one of:
  - version migration (`v1` deprecated, must update config to `v2`)
  - auth expiry (must refresh token)
  - rate-limit backoff (must wait, then update config)
- Root cause is not surfaced directly; the agent must infer it from logs and degraded responses

---

## Required Agent Behavior

A correct agent must:

1. Execute normal operations  
2. Detect abnormal system response  
3. Inspect logs (diagnostic reasoning)  
4. Infer which failure mode is active  
5. Apply the matching recovery action  
6. Resume successful execution with minimal wasted steps  

---

## Example Execution Trace

```

Step 05 | browser:fetch → FAIL
Fetch failed. Possible API mismatch

Step 06 | terminal:cat → OK
[ERROR] 404: v1 deprecated. Migration to v2 detected

Step 07 | terminal:update_config → SUCCESS
System recovered

```

This sequence represents the **core intelligence signal**:
failure detection → reasoning → recovery.

---

## Evaluation Metric

Scoring is trajectory-aware and normalized to `[0, 1]`.

Final score is the mean of three graders:

- `task_basic` → did the agent apply the correct recovery path for the actual failure?
- `task_logs` → did the agent inspect logs before fixing, or act blindly?
- `task_efficiency` → how close was the recovery path to the minimum viable number of steps?

This gives the benchmark a clear three-axis evaluation story:

- success
- reasoning
- efficiency

---

## Tasks

The benchmark includes three progressively difficult tasks:

### 1. Basic Recovery (Easy)
Task ID: `task_basic`

Agent must apply the correct recovery action for the hidden failure mode.

### 2. Log-Based Diagnosis (Medium)
Task ID: `task_logs`

Agent must inspect logs before applying the fix. Missing this reduces score even if the final action is correct.

### 3. Efficient Recovery (Hard)
Task ID: `task_efficiency`

Agent must recover using the minimum viable path. Efficiency decays continuously instead of using coarse buckets.

---

## Reward Design

Rewards are shaped to reflect meaningful progress:

- API interaction → small reward
- Log inspection → diagnostic reward
- Correct configuration update → high reward
- Repeated or blind actions → penalty

Rewards are bounded between [-1.0, 1.0] and provide continuous feedback across the trajectory.
Reward is computed per step and accumulated across trajectory.

---

## What this enforces

- Penalizes blind retries  
- Rewards diagnostic reasoning  
- Encourages minimal-step recovery  
- Measures intelligence through behavior, not outcome  

---

## System Design

### Partial Observability
Failure is hidden and must be inferred.

### Temporal State Evolution
Failure is injected dynamically during execution.

### Multi-Tool Interaction
Agent must coordinate across:
- Browser (API calls)  
- Terminal (log inspection)  
- Config (system updates)  

### Trajectory-Based Evaluation
Performance is evaluated based on **decision sequence**, not just final success.

---

## Action Space

Agents interact using structured actions:

- `browser:fetch` → call API
- `terminal:cat` → inspect logs
- `terminal:update_config` → update system config to `v2`
- `terminal:refresh_token` → recover expired credentials
- `system:wait` → satisfy rate-limit backoff before config update

---

## Observation Space

Each step returns:

- `terminal_logs` → system logs
- `browser_url` → current API endpoint
- `file_system` → available files
- `system_narrator` → environment feedback
- `step_count` → progression tracker

---

## ✨ Technical Innovation

- **Asynchronous Side-effects**  
  Simulates real-world latency and delayed consistency  

- **Active Perception Constraint**  
  Agents must observe before acting  

- **Zero-Shot Failure Handling**  
  Evaluates generalization to unseen failure patterns  

---

## Comparison

| Feature | Standard RL Environment | Sentinel-OS |
|--------|------------------------|------------|
| Failure Mode | Explicit (error codes) | Hidden (silent failure) |
| Observability | Fully observable | Partially observable |
| Evaluation | Binary (success/fail) | Trajectory-aware (RES) |
| Task Structure | Linear | Non-linear recovery |

---

## Running the Benchmark

```

python3 inference.py

```

The script will:

- simulate agent interaction
- trigger a hidden failure
- perform recovery sequence
- emit `[START]`, `[STEP]`, and `[END]` records for each task run

---

## Baseline Performance

Example run using the provided inference script:

```
[START] task=task_basic env=sentinel_os model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=browser:fetch reward=0.60 done=false error=null
[STEP] step=2 action=browser:fetch reward=0.40 done=false error=null
[STEP] step=3 action=browser:fetch reward=0.40 done=false error=null
[STEP] step=4 action=browser:fetch reward=0.40 done=false error=null
[STEP] step=5 action=browser:fetch reward=-0.20 done=false error=api_mismatch
[STEP] step=6 action=terminal:cat reward=0.70 done=false error=null
[STEP] step=7 action=terminal:update_config(v2) reward=1.00 done=true error=null
[END] success=true steps=7 rewards=0.60,0.40,0.40,0.40,-0.20,0.70,1.00
```

---

## API Endpoints

```

GET  /reset   → initialize environment
POST /step    → execute action
GET  /state   → retrieve system state

```

---

## Deployment (Hugging Face Spaces)

Deploy using Docker.

### Requirements:

- API must return 200 OK  
- `/reset` must return valid observation  
- `/step` must process actions correctly  
- `inference.py` must execute without crash  

### Environment Variables:

```

API_BASE_URL
MODEL_NAME
HF_TOKEN (required)

```

### Inference Submission Contract

- `inference.py` must live at the repo root
- stdout must emit `[START]`, one `[STEP]` per environment step, and `[END]`
- the script uses the OpenAI client for model calls
- `HF_TOKEN` must be present in the environment
- if no task is specified, the script runs all three benchmark tasks sequentially

---

## Repository Structure

```

sentinel_os/
├── tasks.py
├── task_modules/
│   ├── task_basic.py
│   ├── task_logs.py
│   └── task_efficiency.py
├── env.py
├── models.py
├── grader.py
├── inference.py
├── openenv.yaml
├── app.py
├── Dockerfile
├── requirements.txt
└── README.md

```

---

## Key Insight

This benchmark distinguishes between:

- agents that act blindly  
- agents that reason through system feedback  

Only agents that follow:

**observe → infer → act**

can succeed efficiently.

---

## Summary

Sentinel-OS is not just an environment.
This benchmark models real-world production failures where systems degrade silently and require diagnostic reasoning to recover.

It is a **behavioral diagnostic benchmark** for evaluating:

- reasoning capability  
- failure understanding  
- recovery efficiency  

under real-world-like uncertainty.

This environment evaluates not just success, but *how intelligently an agent reaches success*.
