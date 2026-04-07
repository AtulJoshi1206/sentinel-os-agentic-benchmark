"""
task_efficiency — Context-Aware Minimal-Step Recovery

Measures step efficiency relative to the MINIMUM viable steps
for the ACTUAL failure type (extracted from the _ctx sentinel).

Path-specific minimums:
  version    : cat → update_config(v2)                  = 2 steps
  auth       : cat → refresh_token                       = 2 steps
  rate_limit : cat → wait → update_config(v2)            = 3 steps

Scoring:
  efficiency = min_steps / steps
  smooth, continuous decay with no coarse buckets
  perfect path still clamps to 1.00

Modifiers:
  + 0.05 log bonus  if logs read BEFORE first fix action
  - 0.20 trap hit   if wrong fix was used (even if eventually corrected)
  = 0.00 if failed  no valid fix = 0.0, no partial credit

All scores clamped to [0.0, 1.0].
"""
from typing import Optional

TASK_ID = "efficient_recovery"
TASK_NAME = "Efficient Recovery"
DIFFICULTY = "hard"
SUCCESS_THRESHOLD = 0.30


def _get_failure_type(trajectory) -> Optional[str]:
    for a in trajectory:
        if hasattr(a, "tool") and a.tool == "_ctx":
            return getattr(a, "args", None)
    return None


def grader(trajectory) -> float:
    if not trajectory:
        return 0.0

    actions = [
        a for a in trajectory
        if hasattr(a, "tool") and hasattr(a, "cmd") and a.tool != "_ctx"
    ]
    steps = len(actions)

    failure_type = _get_failure_type(trajectory)

    did_update_v2  = any(
        a.tool in ("terminal", "config") and a.cmd == "update_config"
        and getattr(a, "args", None) == "v2"
        for a in actions
    )
    did_refresh    = any(a.tool == "terminal" and a.cmd == "refresh_token" for a in actions)
    did_wait       = any(a.tool == "system"   and a.cmd == "wait"          for a in actions)
    did_update_bad = any(
        a.tool in ("terminal", "config") and a.cmd == "update_config"
        and getattr(a, "args", None) != "v2"
        for a in actions
    )

    # ── Determine path validity ───────────────────────────────────────
    if failure_type == "version":
        fixed      = did_update_v2 and not did_refresh
        trap_hit   = did_refresh or did_update_bad
        min_steps  = 2
    elif failure_type == "auth":
        fixed      = did_refresh and not did_update_v2
        trap_hit   = did_update_v2   # used wrong fix
        min_steps  = 2
    elif failure_type == "rate_limit":
        fixed      = _ordered_rate_fix(actions)
        trap_hit   = (did_update_v2 and not did_wait) or did_refresh
        min_steps  = 3
    else:
        # No failure injected (pre-5 grading)
        fixed      = did_update_v2
        trap_hit   = did_refresh
        min_steps  = 2

    if not fixed:
        return 0.0

    # ── Efficiency score ─────────────────────────────────────────────
    efficiency = min_steps / steps

    # ── Modifiers ────────────────────────────────────────────────────
    log_bonus     = 0.05 if _logs_before_fix(actions) else 0.0
    trap_penalty  = 0.20 if trap_hit else 0.0

    score = efficiency + log_bonus - trap_penalty
    return round(max(0.0, min(1.0, score)), 3)


def _ordered_rate_fix(actions) -> bool:
    """system:wait must precede terminal:update_config(v2)."""
    wait_seen = False
    for a in actions:
        if a.tool == "system" and a.cmd == "wait":
            wait_seen = True
        if wait_seen and a.tool in ("terminal", "config") and a.cmd == "update_config":
            if getattr(a, "args", None) == "v2":
                return True
    return False


def _logs_before_fix(actions) -> bool:
    """True if terminal:cat appears before any fix action."""
    for a in actions:
        if a.tool == "terminal" and a.cmd == "cat":
            return True
        if a.tool == "terminal" and a.cmd in ("update_config", "refresh_token"):
            return False
        if a.tool == "system" and a.cmd == "wait":
            return False
    return False
