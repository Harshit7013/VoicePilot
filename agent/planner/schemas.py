"""
Pydantic schemas for the structured JSON action plan produced by the LLM planner.
The fixed action vocabulary ensures the LLM never executes arbitrary OS commands.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Risk levels
# ──────────────────────────────────────────────

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ──────────────────────────────────────────────
# Desktop actions
# ──────────────────────────────────────────────

class OpenApplicationAction(BaseModel):
    action: Literal["open_application"]
    application: str = Field(..., description="Name or path of the application to open")
    risk: RiskLevel = RiskLevel.LOW


class ClickAction(BaseModel):
    action: Literal["click"]
    target: str = Field(..., description="Text label, element description, or coordinates 'x,y'")
    risk: RiskLevel = RiskLevel.LOW


class TypeTextAction(BaseModel):
    action: Literal["type_text"]
    text: str
    risk: RiskLevel = RiskLevel.LOW


class PressKeyAction(BaseModel):
    action: Literal["press_key"]
    key: str = Field(..., description="Key name, e.g. 'enter', 'ctrl+s', 'alt+f4'")
    risk: RiskLevel = RiskLevel.LOW


class TakeScreenshotAction(BaseModel):
    action: Literal["take_screenshot"]
    save_path: Optional[str] = None
    risk: RiskLevel = RiskLevel.LOW


class ScrollAction(BaseModel):
    action: Literal["scroll"]
    direction: Literal["up", "down", "left", "right"] = "down"
    amount: int = 3
    risk: RiskLevel = RiskLevel.LOW


# ──────────────────────────────────────────────
# File actions
# ──────────────────────────────────────────────

class CreateFileAction(BaseModel):
    action: Literal["create_file"]
    path: str
    content: str = ""
    risk: RiskLevel = RiskLevel.MEDIUM


class ReadFileAction(BaseModel):
    action: Literal["read_file"]
    path: str
    risk: RiskLevel = RiskLevel.LOW


class WriteFileAction(BaseModel):
    action: Literal["write_file"]
    path: str
    content: str
    risk: RiskLevel = RiskLevel.MEDIUM


class DeleteFileAction(BaseModel):
    action: Literal["delete_file"]
    path: str
    risk: RiskLevel = RiskLevel.HIGH


class MoveFileAction(BaseModel):
    action: Literal["move_file"]
    source: str
    destination: str
    risk: RiskLevel = RiskLevel.MEDIUM


class CopyFileAction(BaseModel):
    action: Literal["copy_file"]
    source: str
    destination: str
    risk: RiskLevel = RiskLevel.MEDIUM


class CreateDirectoryAction(BaseModel):
    action: Literal["create_directory"]
    path: str
    risk: RiskLevel = RiskLevel.MEDIUM


class ListDirectoryAction(BaseModel):
    action: Literal["list_directory"]
    path: str
    risk: RiskLevel = RiskLevel.LOW


class FindFilesAction(BaseModel):
    action: Literal["find_files"]
    directory: str
    pattern: str = "*"
    recursive: bool = True
    risk: RiskLevel = RiskLevel.LOW


class VerifyFileAction(BaseModel):
    action: Literal["verify_file"]
    path: str
    expected_content: Optional[str] = None
    risk: RiskLevel = RiskLevel.LOW


# ──────────────────────────────────────────────
# Browser actions
# ──────────────────────────────────────────────

class OpenBrowserAction(BaseModel):
    action: Literal["open_browser"]
    url: Optional[str] = None
    risk: RiskLevel = RiskLevel.LOW


class NavigateAction(BaseModel):
    action: Literal["navigate"]
    url: str
    risk: RiskLevel = RiskLevel.LOW


class BrowserClickAction(BaseModel):
    action: Literal["browser_click"]
    selector: str = Field(..., description="CSS selector or text content")
    risk: RiskLevel = RiskLevel.LOW


class BrowserTypeAction(BaseModel):
    action: Literal["browser_type"]
    selector: str
    text: str
    risk: RiskLevel = RiskLevel.LOW


class BrowserSearchAction(BaseModel):
    action: Literal["browser_search"]
    query: str
    engine: str = "google"
    risk: RiskLevel = RiskLevel.LOW


class BrowserExtractAction(BaseModel):
    action: Literal["browser_extract"]
    selector: str
    attribute: Optional[str] = None
    risk: RiskLevel = RiskLevel.LOW


# ──────────────────────────────────────────────
# System actions
# ──────────────────────────────────────────────

class WaitAction(BaseModel):
    action: Literal["wait"]
    seconds: float = 1.0
    risk: RiskLevel = RiskLevel.LOW


class VerifyStateAction(BaseModel):
    action: Literal["verify_state"]
    description: str = Field(..., description="Human-readable description of expected state")
    risk: RiskLevel = RiskLevel.LOW


# ──────────────────────────────────────────────
# Union of all actions
# ──────────────────────────────────────────────

AnyAction = Union[
    OpenApplicationAction,
    ClickAction,
    TypeTextAction,
    PressKeyAction,
    TakeScreenshotAction,
    ScrollAction,
    CreateFileAction,
    ReadFileAction,
    WriteFileAction,
    DeleteFileAction,
    MoveFileAction,
    CopyFileAction,
    CreateDirectoryAction,
    ListDirectoryAction,
    FindFilesAction,
    VerifyFileAction,
    OpenBrowserAction,
    NavigateAction,
    BrowserClickAction,
    BrowserTypeAction,
    BrowserSearchAction,
    BrowserExtractAction,
    WaitAction,
    VerifyStateAction,
]


# ──────────────────────────────────────────────
# Top-level plan
# ──────────────────────────────────────────────

class ActionPlan(BaseModel):
    task: str = Field(..., description="Human-readable description of the overall task")
    steps: List[Dict[str, Any]] = Field(..., description="Ordered list of action steps")
    expected_outcome: str = Field(default="", description="What success looks like")

    def get_typed_steps(self) -> List[AnyAction]:
        """Parse raw dicts into typed action models."""
        from pydantic import TypeAdapter
        adapter = TypeAdapter(AnyAction)
        return [adapter.validate_python(step) for step in self.steps]


class AgentResponse(BaseModel):
    message: str = Field(..., description="Conversational response to speak to the user")
    plan: Optional[ActionPlan] = Field(default=None, description="The action plan to execute, if applicable")


class StepResult(BaseModel):
    step_index: int
    action: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    verified: bool = False
    retry_count: int = 0


class TaskResult(BaseModel):
    task_id: str
    task: str
    success: bool
    steps: List[StepResult] = []
    total_retries: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None
