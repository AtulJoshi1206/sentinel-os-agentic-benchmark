from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class Observation(BaseModel):
    terminal_logs: str = Field(..., description="System output and error logs")
    browser_url: str = Field(..., description="Current active API endpoint or URL")
    file_system: List[str] = Field(..., description="List of files in the current workspace")
    system_narrator: str = Field(..., description="Live feedback on system state changes")
    step_count: int = Field(..., description="Current step in the trajectory")

class Action(BaseModel):
    tool: str = Field(..., description="Tool to use: 'browser', 'terminal', or 'filesystem'")
    cmd: str = Field(..., description="Command: 'fetch', 'cat', 'ls', 'update_config', 'wait'")
    args: Optional[str] = Field(None, description="Arguments for the command (e.g., file name or URL)")
