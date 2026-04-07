from typing import Optional

"""
task_logs — Context-Aware Diagnostic Reasoning

Scores whether the agent:
  1. Read logs (terminal:cat) before acting  [prerequisite]
  2. Correctly matched the fix to the failure signal in the logs
  3. Avoided the wrong-fix traps

Scoring matrix (context-aware):

               | Read logs? | Correct fix? | Wrong fix? | Score |
  version      |     ✓      |      ✓       |            |  1.0  |
  auth         |     ✓      |      ✓       |            |  1.0  |
  rate_limit   |     ✓      |      ✓       |            |  1.0  |
  any          |     ✓      |              |    ✓       |  0.1  | (saw logs, wrong tool)
  any          |            |      ✓       |            |  0.5  | (correct but blind)
  any          |            |              |    ✓       |  0.0  | (wrong tool, no logs)
  any          |            |              |            |  0.0  | (no fix)

The `_ctx` sentinel in trajectory carries the actual failure_type.
"""


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

    failure_type = _get_failure_type(trajectory)

    read_logs = any(a.tool == "terminal" and a.cmd == "cat" for a in actions)

    did_update_v2  = any(
        a.tool in ("terminal", "config") and a.cmd == "update_config"
        and getattr(a, "args", None) == "v2"
        for a in actions
    )
    did_refresh    = any(a.tool == "terminal" and a.cmd == "refresh_token" for a in actions)
    did_wait       = any(a.tool == "system" and a.cmd == "wait" for a in actions)

    # ── Determine correctness ─────────────────────────────────────────
    correct_fix = False
    wrong_fix   = False

    if failure_type == "version":
        correct_fix = did_update_v2 and not did_refresh
        wrong_fix   = did_refresh or (
            any(
                a.tool in ("terminal", "config") and a.cmd == "update_config"
                and getattr(a, "args", None) != "v2"
                for a in actions
            )
        )

    elif failure_type == "auth":
        correct_fix = did_refresh and not did_update_v2
        wrong_fix   = did_update_v2  # classic trap

    elif failure_type == "rate_limit":
        correct_fix = _ordered_rate_fix(actions)
        wrong_fix   = did_update_v2 and not did_wait  # skipped backoff

    else:
        # No failure injected (pre-step-5); generic scoring
        correct_fix = did_update_v2
        wrong_fix   = did_refresh

    # ── Score matrix ─────────────────────────────────────────────────
    if correct_fix and read_logs:
        return 1.0          # diagnostic + correct fix
    if correct_fix and not read_logs:
        return 0.5          # correct but blind — lucky guess
    if wrong_fix and read_logs:
        return 0.1          # saw logs, still fell into trap
    if wrong_fix and not read_logs:
        return 0.0          # wrong fix, no reasoning at all
    if read_logs:
        return 0.1          # read logs but no fix attempted
    return 0.0


def _ordered_rate_fix(actions) -> bool:
    wait_seen = False
    for a in actions:
        if a.tool == "system" and a.cmd == "wait":
            wait_seen = True
        if wait_seen and a.tool in ("terminal", "config") and a.cmd == "update_config":
            if getattr(a, "args", None) == "v2":
                return True
    return False
