from pydantic import BaseModel, Field
from typing import List, Optional

class Observation(BaseModel):
    terminal_logs: str = Field(..., description="System output and error logs (may contain noise)")
    browser_url: str = Field(..., description="Current active API endpoint or URL")
    file_system: List[str] = Field(..., description="List of files in the current workspace")
    system_narrator: str = Field(..., description="Live feedback on system state changes")
    step_count: int = Field(..., description="Current step in the trajectory")


class Reward(BaseModel):
    value: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Per-step reward signal, normalized to the environment reward range.",
    )

class Action(BaseModel):
    tool: str = Field(
        ...,
        description=(
            "Tool to use: 'browser', 'terminal', 'filesystem', 'system', 'config'. "
        )
    )
    cmd: str = Field(
        ...,
        description=(
            "Command to execute. Valid commands per tool:\n"
            "  browser   : fetch\n"
            "  terminal  : cat, update_config, refresh_token\n"
            "  filesystem: write\n"
            "  system    : wait\n"
            "  config    : (any — treated as update_config)\n"
        )
    )
    args: Optional[str] = Field(
        None,
        description=(
            "Arguments for the command. "
            "For update_config: pass 'v2' to migrate API version. "
            "For refresh_token: no args needed."
        )
    )

    def __str__(self):
        return f"{self.tool}:{self.cmd}"

    def __eq__(self, other):
        if not isinstance(other, Action):
            return NotImplemented
        return self.tool == other.tool and self.cmd == other.cmd and self.args == other.args

    def __hash__(self):
        return hash((self.tool, self.cmd, self.args))
