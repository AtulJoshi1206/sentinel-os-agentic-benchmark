# Sentinel-OS: Agentic Recovery Benchmark

## What this evaluates

Sentinel-OS evaluates whether an AI agent can **detect, diagnose, and recover from hidden system failures** using multi-step reasoning.

Unlike conventional environments, failures are not explicitly exposed.  
Agents must infer them from logs, system responses, and evolving state.

The objective is not just task completion — but **intelligent, efficient recovery under uncertainty**.

---

## Core Scenario

The environment simulates a real-world system with a silent failure:

- Initial state: API operates normally (v1)  
- At step 5: hidden failure is triggered  
- API endpoint internally changes (v1 → v2)  
- System responses degrade without explicit error  
- Root cause is only discoverable through logs  

---

## Required Agent Behavior

A correct agent must:

1. Execute normal operations  
2. Detect abnormal system response  
3. Inspect logs (diagnostic reasoning)  
4. Infer API migration (v1 → v2)  
5. Update configuration  
6. Resume successful execution  

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

Recovery Efficiency Score (RES):

```

RES = diagnostic_actions / retry_actions

```

Where:

- diagnostic_actions → meaningful inspection (e.g., reading logs)  
- retry_actions → blind or repeated attempts  

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
- trigger hidden failure  
- perform recovery sequence  
- output trajectory and final score  

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
HF_TOKEN (optional)

```

---

## Repository Structure

```

sentinel_os/
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

It is a **behavioral diagnostic benchmark** for evaluating:

- reasoning capability  
- failure understanding  
- recovery efficiency  

under real-world-like uncertainty.


