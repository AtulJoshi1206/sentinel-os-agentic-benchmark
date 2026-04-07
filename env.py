import random
from models import Observation, Action

class SentinelEnv:
    def __init__(self):
        self.reset()

    def reset(self):
        self.state = {
            "api_version": "v1",
            "correct_api": "v1",
            "file_content": "",
            "logs": "System initialized.",
            "step": 0,
            "broken": False,
            "history": [],
            "pending_write": None
        }
        self.trajectory = []
        return self._get_obs("Environment reset. Sync API data.")

    def step(self, action: Action):
        self.state["step"] += 1
        self.state["history"].append(f"{action.tool}:{action.cmd}")
        self.trajectory.append(action)

        narrator = ""
        reward = 0.0

        # Repeated action penalty
        repeated_action = False
        if len(self.state["history"]) > 1:
            if self.state["history"][-1] == self.state["history"][-2]:
                repeated_action = True

        if action.tool == "browser":
            reward += 0.1
        elif action.tool == "terminal":
            reward += 0.3
        elif action.tool == "config":
            reward += 0.6

        # penalize useless repetition
        if repeated_action:
            reward -= 0.2

        # 🔥 Silent failure trigger (The "Meta" Moment)
        if self.state["step"] == 5:
            self.state["correct_api"] = "v2"
            self.state["broken"] = True
            self.state["logs"] += "\n[ERROR] 404: v1 deprecated. Migration to v2 detected."

        # 🔁 Delayed file write (Simulating real-world async I/O)
        if self.state["pending_write"]:
            self.state["file_content"] = self.state["pending_write"]
            self.state["pending_write"] = None

        # --- ACTION LOGIC ---

        if action.tool == "browser" and action.cmd == "fetch":
            if self.state["api_version"] != self.state["correct_api"]:
                narrator = "Fetch failed. Possible API mismatch. Check system logs."
                reward -= 0.2
            elif self.state["broken"] and random.random() < 0.2:
                narrator = "Intermittent failure persists. Retry or verify logs."
                reward -= 0.1
            else:
                narrator = "Data fetched successfully from current endpoint."
                reward += 0.5

        elif action.tool == "filesystem" and action.cmd == "write":
            self.state["pending_write"] = "data_saved_v1"
            narrator = "Write initiated. Changes will reflect in the next step."
            reward += 0.2

        elif action.tool == "terminal" and action.cmd == "cat":
            narrator = f"Logs Read: {self.state['logs']}"

        elif action.tool == "config" or (action.tool == "terminal" and action.cmd == "update_config"):
            if action.args == "v2":
                self.state["api_version"] = "v2"
                self.state["broken"] = False
                narrator = "Config updated to v2. System handshake successful."
                reward = 1.0  # Max reward for success
            else:
                narrator = "Update failed: Invalid configuration string."
                reward -= 0.3

        elif action.tool == "system" and action.cmd == "wait":
            narrator = "Waiting... system buffers stabilizing."
            reward += 0.1

        else:
            narrator = "Invalid action or tool mismatch."
            reward -= 0.2

        # Early exit only if we've successfully navigated the silent failure at step 5
        done = (
            self.state["step"] > 5 
            and self.state["api_version"] == self.state["correct_api"]
            and not self.state["broken"]
        ) or self.state["step"] >= 15

        # Ensure reward is always between -1.0 and 1.0
        reward = max(-1.0, min(1.0, reward))

        return self._get_obs(narrator), reward, done, {}

    def _get_obs(self, msg):
        return Observation(
            terminal_logs=self.state["logs"] if self.state["step"] > 3 else "No errors recorded.",
            browser_url=f"http://internal-cluster/api/{self.state['api_version']}",
            file_system=["config.env", "data_vault.json", "logs/error.log"],
            system_narrator=msg,
            step_count=self.state["step"]
        )
