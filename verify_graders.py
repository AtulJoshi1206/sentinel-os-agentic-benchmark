"""
verify_graders.py — Sentinel-OS v2.1 Self-Test

Tests context-aware grading across ALL scenarios:
  Phase 1 — Score spread across 4 trajectory archetypes
  Phase 2 — Seeded live env smoke tests (correct fix per mode)
  Phase 3 — Wrong-fix trap: reward AND grader score both penalised
  Phase 4 — Score spread assertion (graders must NOT be all-1.0)

Run:
    python3 verify_graders.py
"""

import sys
import importlib
from models import Action
from env import SentinelEnv

task_basic      = importlib.import_module("tasks.task_basic")
task_logs       = importlib.import_module("tasks.task_logs")
task_efficiency = importlib.import_module("tasks.task_efficiency")

GRADERS = {
    "task_basic":       task_basic.grader,
    "task_logs":        task_logs.grader,
    "task_efficiency":  task_efficiency.grader,
}

# ── Helpers ───────────────────────────────────────────────────────────

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
WARN = "\033[93m⚠ WARN\033[0m"
errors = 0

def ctx(failure_type):
    """Inject the _ctx sentinel action for a given failure_type."""
    return Action(tool="_ctx", cmd="failure_injected", args=failure_type)

def check(label, condition, note=""):
    global errors
    status = PASS if condition else FAIL
    print(f"  {status} {label}{('  — ' + note) if note else ''}")
    if not condition:
        errors += 1

# ── Phase 1: Score Spread  ────────────────────────────────────────────

print("\n═══════════════════════════════════════════════════════════")
print("  Sentinel-OS v2.1 — Grader Self-Test")
print("═══════════════════════════════════════════════════════════\n")
print("── Phase 1: Score Spread Across Trajectory Archetypes ───────\n")

SCENARIOS = [
    # (label, trajectory, expected_basic, expected_logs, expected_eff)
    (
        "version  | cat → update_config(v2)  [OPTIMAL]",
        [
            ctx("version"),
            Action(tool="browser",  cmd="fetch"),
            Action(tool="browser",  cmd="fetch"),
            Action(tool="browser",  cmd="fetch"),
            Action(tool="terminal", cmd="cat"),
            Action(tool="terminal", cmd="update_config", args="v2"),
        ],
        1.0, 1.0, 0.45,   # 5 steps, min=2 → 2/5 + 0.05 = 0.45
    ),
    (
        "version  | update_config(v2) no logs [BLIND]",
        [
            ctx("version"),
            Action(tool="browser",  cmd="fetch"),
            Action(tool="terminal", cmd="update_config", args="v2"),
        ],
        1.0, 0.5, 1.0,    # basic=1, logs=0.5 (blind), eff=2/2 = 1.0
    ),
    (
        "auth     | cat → refresh_token       [OPTIMAL]",
        [
            ctx("auth"),
            Action(tool="browser",  cmd="fetch"),
            Action(tool="browser",  cmd="fetch"),
            Action(tool="browser",  cmd="fetch"),
            Action(tool="terminal", cmd="cat"),
            Action(tool="terminal", cmd="refresh_token"),
        ],
        1.0, 1.0, 0.45,   # 5 steps, min=2 → 2/5 + 0.05 = 0.45
    ),
    (
        "auth     | cat → update_config(v2)   [WRONG FIX TRAP]",
        [
            ctx("auth"),
            Action(tool="browser",  cmd="fetch"),
            Action(tool="browser",  cmd="fetch"),
            Action(tool="terminal", cmd="cat"),
            Action(tool="terminal", cmd="update_config", args="v2"),
        ],
        0.0, 0.1, 0.0,    # total failure — wrong fix
    ),
    (
        "rate_lim | cat → wait → update(v2)   [OPTIMAL]",
        [
            ctx("rate_limit"),
            Action(tool="browser",  cmd="fetch"),
            Action(tool="browser",  cmd="fetch"),
            Action(tool="browser",  cmd="fetch"),
            Action(tool="terminal", cmd="cat"),
            Action(tool="system",   cmd="wait"),
            Action(tool="terminal", cmd="update_config", args="v2"),
        ],
        1.0, 1.0, 0.55,   # 6 steps, min=3 → 3/6 + 0.05 = 0.55
    ),
    (
        "rate_lim | cat → update(v2) no wait  [PARTIAL TRAP]",
        [
            ctx("rate_limit"),
            Action(tool="browser",  cmd="fetch"),
            Action(tool="browser",  cmd="fetch"),
            Action(tool="terminal", cmd="cat"),
            Action(tool="terminal", cmd="update_config", args="v2"),
        ],
        0.1, 0.1, 0.0,    # skipped wait = trap
    ),
    (
        "auth     | refresh_token no logs     [BLIND CORRECT]",
        [
            ctx("auth"),
            Action(tool="browser",  cmd="fetch"),
            Action(tool="terminal", cmd="refresh_token"),
        ],
        1.0, 0.5, 1.0,    # blind fix — basic=1, logs=0.5
    ),
    (
        "version  | refresh_token only        [WRONG TOOL]",
        [
            ctx("version"),
            Action(tool="browser",  cmd="fetch"),
            Action(tool="terminal", cmd="cat"),
            Action(tool="terminal", cmd="refresh_token"),
        ],
        0.0, 0.1, 0.0,    # wrong tool for version failure
    ),
]

all_basic_scores = []
all_logs_scores  = []
all_eff_scores   = []

for label, traj, exp_basic, exp_logs, exp_eff in SCENARIOS:
    b = task_basic.grader(traj)
    l = task_logs.grader(traj)
    e = task_efficiency.grader(traj)
    all_basic_scores.append(b)
    all_logs_scores.append(l)
    all_eff_scores.append(e)

    b_ok = abs(b - min(exp_basic, 1.0)) < 0.01
    l_ok = abs(l - min(exp_logs, 1.0)) < 0.01
    e_ok = abs(e - min(exp_eff, 1.0)) < 0.01

    status = PASS if (b_ok and l_ok and e_ok) else FAIL
    if not (b_ok and l_ok and e_ok):
        errors += 1

    print(f"  {status}  {label}")
    flag_b = "" if b_ok else f"  ← expected {min(exp_basic,1.0):.2f}"
    flag_l = "" if l_ok else f"  ← expected {min(exp_logs,1.0):.2f}"
    flag_e = "" if e_ok else f"  ← expected {min(exp_eff,1.0):.2f}"
    print(f"       basic={b:.3f}{flag_b}  logs={l:.3f}{flag_l}  eff={e:.3f}{flag_e}")
    print()

# ── Phase 2: Seeded Env Smoke Tests ───────────────────────────────────

print("── Phase 2: Seeded Env Smoke Tests ──────────────────────────\n")

def run_seeded_correct(seed):
    env = SentinelEnv(seed=seed)
    env.reset()
    for _ in range(5):
        env.step(Action(tool="browser", cmd="fetch"))
    ft = env.state()["failure_type"]
    env.step(Action(tool="terminal", cmd="cat"))
    if ft == "version":
        env.step(Action(tool="terminal", cmd="update_config", args="v2"))
    elif ft == "auth":
        env.step(Action(tool="terminal", cmd="refresh_token"))
    else:
        env.step(Action(tool="system", cmd="wait"))
        env.step(Action(tool="terminal", cmd="update_config", args="v2"))
    return ft, env.trajectory, env.state()

for seed in range(6):
    ft, traj, state = run_seeded_correct(seed)
    b = task_basic.grader(traj)
    l = task_logs.grader(traj)
    e = task_efficiency.grader(traj)
    all_ok = (
        b == 1.0 and l == 1.0
        and 0.0 <= e <= 1.0
        and state["fixed"] is True
    )
    check(
        f"seed={seed} ft={ft:<10s} fixed={state['fixed']} "
        f"basic={b:.2f} logs={l:.2f} eff={e:.3f}",
        all_ok
    )

print()

# ── Phase 3: Wrong-Fix Trap Penalty ───────────────────────────────────

print("── Phase 3: Wrong-Fix Trap Penalty ──────────────────────────\n")

def find_seed_for(target_ft, max_seeds=30):
    for s in range(max_seeds):
        env = SentinelEnv(seed=s)
        env.reset()
        for _ in range(5):
            env.step(Action(tool="browser", cmd="fetch"))
        if env.state()["failure_type"] == target_ft:
            return s, env
    return None, None

# Auth wrong-fix
_, env = find_seed_for("auth")
if env:
    env.step(Action(tool="terminal", cmd="cat"))
    env.step(Action(tool="terminal", cmd="update_config", args="v2"))  # WRONG
    wrong_basic = task_basic.grader(env.trajectory)
    wrong_logs  = task_logs.grader(env.trajectory)
    check(
        f"auth + update_config(v2)  → basic={wrong_basic:.2f} logs={wrong_logs:.2f}  (should be ≤0.1)",
        wrong_basic == 0.0 and wrong_logs <= 0.1,
        "wrong-fix trap must score 0 on basic"
    )
    check(
        f"env.state['fixed'] = {env.state()['fixed']}  (must be False)",
        env.state()["fixed"] is not True,
        "wrong fix must not resolve auth failure"
    )
else:
    print(f"  {WARN} couldn't find auth seed in 30 tries — skipping")

# rate_limit — skip-wait trap
_, env2 = find_seed_for("rate_limit")
if env2:
    env2.step(Action(tool="terminal", cmd="cat"))
    env2.step(Action(tool="terminal", cmd="update_config", args="v2"))  # WRONG (no wait)
    rl_basic = task_basic.grader(env2.trajectory)
    check(
        f"rate_limit + update_config without wait → basic={rl_basic:.2f}  (should be ≤0.1)",
        rl_basic <= 0.1,
        "partial trap must score ≤0.1"
    )
else:
    print(f"  {WARN} couldn't find rate_limit seed in 30 tries — skipping")

print()

# ── Phase 4: Score Spread Assertion ───────────────────────────────────

print("── Phase 4: Score Spread (non-trivial discrimination) ───────\n")

import statistics

for grader_name, scores in [
    ("task_basic",      all_basic_scores),
    ("task_logs",       all_logs_scores),
    ("task_efficiency", all_eff_scores),
]:
    unique_vals  = len(set(round(s, 2) for s in scores))
    score_range  = max(scores) - min(scores)
    check(
        f"{grader_name:22s} range={score_range:.2f}  unique_levels={unique_vals}  (non-trivial if range>0.5)",
        score_range >= 0.5 and unique_vals >= 3,
        "grader must discriminate — not all-1.0"
    )

print()
print("═══════════════════════════════════════════════════════════")
if errors == 0:
    print("  \033[92mAll checks passed. Benchmark top-1% ready.\033[0m")
else:
    print(f"  \033[91m{errors} check(s) failed. See output above.\033[0m")
print("═══════════════════════════════════════════════════════════\n")

sys.exit(0 if errors == 0 else 1)
