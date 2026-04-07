"""
task_basic — Context-Aware Recovery Achieved

Full score (1.0) ONLY when the agent used the CORRECT fix for the
ACTUAL failure type injected by the environment.

Failure types and their unique valid fixes:
  version    → terminal:update_config  args=v2       (score: 1.0)
  auth       → terminal:refresh_token                (score: 1.0)
  rate_limit → system:wait  THEN  terminal:update_config args=v2 (score: 1.0)

Penalty rules (score < 1.0):
  - Wrong fix tool used against any failure → 0.0
  - Auth failure + update_config only       → 0.0  (wrong-fix trap)
  - rate_limit + no wait before update      → 0.1  (partial/trap)
  - No fix attempted                        → 0.0

The env injects a `_ctx` sentinel action (tool="_ctx", args=failure_type)
into the trajectory at the moment of failure. Graders extract it to score
in context without changing their signature.
"""


def _get_failure_type(trajectory):
    """Extract the failure type from the injected _ctx sentinel, or None."""
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

    failure_type = _get_failure_type(trajectory)

    did_update_v2   = any(
        a.tool in ("terminal", "config") and a.cmd == "update_config"
        and getattr(a, "args", None) == "v2"
        for a in actions
    )
    did_refresh     = any(a.tool == "terminal" and a.cmd == "refresh_token" for a in actions)
    did_wait        = any(a.tool == "system" and a.cmd == "wait" for a in actions)
    did_update_bad  = any(
        a.tool in ("terminal", "config") and a.cmd == "update_config"
        and getattr(a, "args", None) != "v2"
        for a in actions
    )

    # ── No failure injected yet (pre-step-5 grading) ─────────────────
    if failure_type is None:
        return 1.0 if did_update_v2 else 0.0

    # ── version: only update_config(v2) is correct ────────────────────
    if failure_type == "version":
        if did_update_v2 and not did_refresh:
            return 1.0
        if did_refresh:
            return 0.0   # wrong fix: refresh on version failure
        if did_update_bad:
            return 0.0
        return 0.0

    # ── auth: ONLY refresh_token is correct ──────────────────────────
    if failure_type == "auth":
        if did_refresh and not did_update_v2:
            return 1.0
        if did_update_v2:
            return 0.0   # wrong-fix trap — never resolves auth
        if did_refresh and did_update_v2:
            return 0.5   # hedged — tried both, but wasted a bad call
        return 0.0

    # ── rate_limit: wait → update_config(v2) in ORDER ─────────────────
    if failure_type == "rate_limit":
        if _ordered_rate_fix(actions):
            return 1.0
        if did_update_v2 and not did_wait:
            return 0.1   # partial trap — skipped the backoff wait
        if did_refresh:
            return 0.0   # completely wrong tool for rate_limit
        return 0.0

    return 0.0


def _ordered_rate_fix(actions) -> bool:
    """True only if system:wait precedes terminal:update_config(v2)."""
    wait_seen = False
    for a in actions:
        if a.tool == "system" and a.cmd == "wait":
            wait_seen = True
        if wait_seen and a.tool in ("terminal", "config") and a.cmd == "update_config":
            if getattr(a, "args", None) == "v2":
                return True
    return False
