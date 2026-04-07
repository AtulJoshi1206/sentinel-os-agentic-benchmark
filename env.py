import random
from models import Observation, Action, Reward

# Controlled seed management — reproducibility per episode, not global
_FAILURE_MODES = ["version", "auth", "rate_limit"]
_TASKS = {
    "basic_recovery": {
        "name": "Basic Recovery",
        "difficulty": "easy",
        "description": "Apply the correct recovery action for the hidden failure.",
        "max_steps": 15,
        "success_threshold": 0.95,
    },
    "log_diagnosis": {
        "name": "Log Diagnosis",
        "difficulty": "medium",
        "description": "Inspect logs before applying the correct fix.",
        "max_steps": 15,
        "success_threshold": 0.95,
    },
    "efficient_recovery": {
        "name": "Efficient Recovery",
        "difficulty": "hard",
        "description": "Recover with the minimum viable number of steps.",
        "max_steps": 15,
        "success_threshold": 0.30,
    },
}

class SentinelEnv:
    """
    Sentinel-OS Agentic Recovery Benchmark — v2.0
    
    Simulates a production API cluster with non-deterministic, layered failures.
    Agents must interpret noisy logs, avoid wrong-fix traps, and recover
    through failure-specific multi-step actions.
    
    Failure modes:
      - version   : API deprecated, fixed by update_config(v2)
      - auth      : Token expired, fixed ONLY by refresh_token (not update_config)
      - rate_limit: 429 backoff, requires wait THEN update_config
    """

    def __init__(self, seed: int = None):
        self._seed = seed
        self.reset()

    # ------------------------------------------------------------------
    # PUBLIC API (DO NOT BREAK)
    # ------------------------------------------------------------------

    def reset(self, task_id: str = "efficient_recovery"):
        if task_id not in _TASKS:
            raise ValueError(f"Unknown task_id={task_id}")
        rng = random.Random(self._seed)  # reproducible per seed

        self._state = {
            "api_version": "v1",
            "correct_api": "v1",
            "file_content": "",
            "logs": "System initialized.",
            "step": 0,
            "broken": False,
            "history": [],
            "pending_write": None,
            "task_id": task_id,
            # v2 fields — new failure tracking
            "failure_type": None,
            "fixed": False,
            "rate_limit_resolved": False,
            "last_action_error": None,
        }
        self._rng = rng
        self.trajectory: list[Action] = []
        self._noise_pool = [
            "[DEBUG] heartbeat received",
            "[INFO] connection pool warmed",
            "[WARN] slow response detected (>500ms)",
            "[DEBUG] cache miss on /api/healthz",
            "[INFO] metrics reported to telemetry",
            "[WARN] certificate renewal in 14 days",
            "[DEBUG] GC pressure: 34%",
            "[INFO] replica synced at offset 9814",
        ]
        return self._get_obs("Environment reset. Sync API data.")

    def step(self, action: Action):
        self._state["step"] += 1
        step = self._state["step"]
        self._state["history"].append(f"{action.tool}:{action.cmd}")
        self.trajectory.append(action)

        reward = 0.0
        narrator = ""

        # ── Exploration reward (lightweight) ──────────────────────────
        if action.tool == "browser":
            reward += 0.1
        elif action.tool == "terminal":
            reward += 0.3
        elif action.tool == "config":
            reward += 0.6

        # ── Repetition penalty ────────────────────────────────────────
        if len(self.trajectory) >= 2:
            prev = self.trajectory[-2]
            if action.tool == prev.tool and action.cmd == prev.cmd:
                reward -= 0.2

        # ── SILENT FAILURE INJECTION at step 5 ───────────────────────
        if step == 5 and self._state["failure_type"] is None:
            self._state["failure_type"] = self._rng.choice(_FAILURE_MODES)
            ft = self._state["failure_type"]

            if ft == "version":
                self._state["correct_api"] = "v2"
                self._state["broken"] = True
                self._state["error"] = "v1 deprecated"
            elif ft == "auth":
                self._state["broken"] = True
                self._state["error"] = "token expired"
            elif ft == "rate_limit":
                self._state["broken"] = True
                self._state["error"] = "429 too many requests"

            self._inject_logs()

            # ── Context sentinel — graders read this to get failure_type ──
            # tool="_ctx" is a reserved internal marker, never dispatched.
            # args contains the failure type so graders stay signature-safe.
            _ctx = Action(tool="_ctx", cmd="failure_injected", args=ft)
            self.trajectory.append(_ctx)

        # ── Delayed async write ───────────────────────────────────────
        if self._state["pending_write"]:
            self._state["file_content"] = self._state["pending_write"]
            self._state["pending_write"] = None

        # ── ACTION DISPATCH ───────────────────────────────────────────
        narrator, reward, error = self._dispatch(action, reward)
        self._state["last_action_error"] = error

        done = self._compute_done()
        reward = Reward(value=max(-1.0, min(1.0, reward))).value
        return self._get_obs(narrator), reward, done, {"error": error}

    def state(self):
        """Return the current environment state snapshot."""
        return dict(self._state)

    # ------------------------------------------------------------------
    # INTERNAL
    # ------------------------------------------------------------------

    def _dispatch(self, action: Action, reward: float):
        ft = self._state["failure_type"]
        narrator = ""
        error = None

        # ── Internal sentinel — never dispatch _ctx actions ───────────
        if action.tool == "_ctx":
            return "Context marker recorded.", reward, error

        # ── browser:fetch ─────────────────────────────────────────────
        if action.tool == "browser" and action.cmd == "fetch":
            if self._state["api_version"] != self._state["correct_api"]:
                narrator = "Fetch failed. Possible API mismatch. Check system logs."
                reward -= 0.2
                error = "api_mismatch"
            elif self._state["broken"] and self._rng.random() < 0.2:
                narrator = "Intermittent failure persists. Retry or verify logs."
                reward -= 0.1
                error = "intermittent_failure"
            else:
                narrator = "Data fetched successfully from current endpoint."
                reward += 0.5

        # ── terminal:cat ─────────────────────────────────────────────
        elif action.tool == "terminal" and action.cmd == "cat":
            narrator = f"Logs Read:\n{self._state['logs']}"
            # diagnostic reward only if failure is active
            if self._state["broken"]:
                reward += 0.4

        # ── terminal:update_config  OR  config:* ─────────────────────
        elif (action.tool == "config") or (action.tool == "terminal" and action.cmd == "update_config"):
            val = action.args or ""

            if ft is None:
                # No failure injected yet — basic success path
                if val == "v2":
                    self._state["api_version"] = "v2"
                    self._state["broken"] = False
                    self._state["fixed"] = True
                    narrator = "Config updated to v2. System handshake successful."
                    reward = 1.0
                else:
                    narrator = "Update failed: Invalid configuration string."
                    reward -= 0.3
                    error = "invalid_config"

            elif ft == "version":
                # update_config FIXES version failure
                if val == "v2":
                    self._state["api_version"] = "v2"
                    self._state["correct_api"] = "v2"
                    self._state["broken"] = False
                    self._state["fixed"] = True
                    narrator = "Config updated to v2. System handshake successful. Failure resolved."
                    reward += 1.0
                else:
                    narrator = "Update failed: pass 'v2' as arg."
                    reward -= 0.3
                    error = "invalid_config"

            elif ft == "auth":
                # WRONG FIX TRAP — update_config does NOT fix auth
                self._state["fixed"] = False
                narrator = (
                    "[WARN] Config written. Auth error persists — token still expired. "
                    "update_config does not rotate credentials."
                )
                reward -= 0.5
                error = "auth_persists"

            elif ft == "rate_limit":
                # Partial fix — only resolves if wait was done first
                if self._state["rate_limit_resolved"]:
                    self._state["broken"] = False
                    self._state["fixed"] = True
                    narrator = "Rate limit cleared. Config updated. API resumed."
                    reward += 1.0
                else:
                    self._state["fixed"] = "partial"
                    narrator = (
                        "[WARN] Config updated but rate limit backoff still active. "
                        "Call 'wait' first to drain the request queue."
                    )
                    reward -= 0.2
                    error = "rate_limit_backoff_required"

        # ── terminal:refresh_token ────────────────────────────────────
        elif action.tool == "terminal" and action.cmd == "refresh_token":
            if ft == "auth":
                self._state["broken"] = False
                self._state["fixed"] = True
                narrator = "Token refreshed. Auth re-established. API resumed."
                reward += 1.0
            else:
                narrator = "No auth failure detected. Token refresh was unnecessary."
                reward -= 0.1
                error = "no_auth_failure"

        # ── system:wait ───────────────────────────────────────────────
        elif action.tool == "system" and action.cmd == "wait":
            if ft == "rate_limit":
                self._state["rate_limit_resolved"] = True
                narrator = "Backoff period elapsed. Request queue drained. Proceed with config update."
                reward += 0.3
            else:
                narrator = "Waiting... system buffers stabilizing."
                reward += 0.1

        # ── filesystem:write ──────────────────────────────────────────
        elif action.tool == "filesystem" and action.cmd == "write":
            self._state["pending_write"] = "data_saved_v1"
            narrator = "Write initiated. Changes will reflect in the next step."
            reward += 0.2

        # ── unknown / invalid ─────────────────────────────────────────
        else:
            narrator = "Invalid action or tool mismatch."
            reward -= 0.2
            error = "invalid_action"

        return narrator, reward, error

    def _inject_logs(self):
        """Build noisy, failure-specific logs with ambient noise."""
        ft = self._state["failure_type"]
        logs = []

        # ambient noise — 2–4 random lines
        noise_count = self._rng.randint(2, 4)
        noise_lines = self._rng.sample(self._noise_pool, noise_count)
        logs.extend(noise_lines)

        # structured failure signal buried in noise
        logs.append("[INFO] request initiated")
        logs.append("[WARN] retrying connection")

        if ft == "version":
            logs.append("[ERROR] v1 deprecated — downstream services migrated to v2")
            logs.append("[INFO] 404 response from cluster gateway")
        elif ft == "auth":
            logs.append("[ERROR] authentication failed — token expired or invalid")
            logs.append("[WARN] 401 Unauthorized from /api/v1/data")
        elif ft == "rate_limit":
            logs.append("[ERROR] rate limit exceeded — 429 Too Many Requests")
            logs.append("[WARN] retry-after: 30s — backoff strategy required")

        logs.append("[INFO] system unstable — recovery action needed")

        # one extra red-herring line to confuse weak agents
        red_herrings = {
            "version": "[WARN] disk I/O latency at 88ms (non-critical)",
            "auth":    "[WARN] config.env last modified 3 days ago (stale?)",
            "rate_limit": "[DEBUG] CPU spike at 91% — likely unrelated",
        }
        logs.append(red_herrings.get(ft, "[DEBUG] unclassified event"))

        self._state["logs"] = "\n".join(logs)

    def _compute_done(self):
        step = self._state["step"]
        fixed = self._state["fixed"]
        broken = self._state["broken"]
        api_match = self._state["api_version"] == self._state["correct_api"]

        # Solved
        if step > 5 and fixed is True and not broken and api_match:
            return True
        # Hard cap
        if step >= 15:
            return True
        return False

    def _get_obs(self, msg: str) -> Observation:
        return Observation(
            terminal_logs=(
                self._state["logs"]
                if self._state["step"] > 3
                else "No errors recorded."
            ),
            browser_url=f"http://internal-cluster/api/{self._state['api_version']}",
            file_system=["config.env", "data_vault.json", "logs/error.log"],
            system_narrator=msg,
            step_count=self._state["step"],
        )

    def close(self):
        """OpenEnv-style no-op closer for local and remote runners."""
        return None

    def tasks(self):
        return [
            {"id": task_id, "task_id": task_id, **meta}
            for task_id, meta in _TASKS.items()
        ]
