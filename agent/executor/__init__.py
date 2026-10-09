"""Executor package — routes actions to the correct executor."""

from __future__ import annotations

import logging
from typing import Any, Dict

from agent.executor.desktop import DesktopExecutor
from agent.executor.file_ops import FileExecutor
from agent.executor.browser import BrowserExecutor

logger = logging.getLogger(__name__)

DESKTOP_ACTIONS = {"open_application", "click", "type_text", "press_key", "take_screenshot", "scroll"}
FILE_ACTIONS = {
    "create_file", "read_file", "write_file", "delete_file", "move_file",
    "copy_file", "create_directory", "list_directory", "find_files", "verify_file",
}
BROWSER_ACTIONS = {"open_browser", "navigate", "browser_click", "browser_type", "browser_search", "browser_extract"}
SYSTEM_ACTIONS = {"wait", "verify_state"}


class Executor:
    """Routes actions to the appropriate executor (desktop / file / browser)."""

    def __init__(self):
        self.desktop = DesktopExecutor()
        self.file = FileExecutor()
        self.browser = BrowserExecutor()

    async def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        action_name = action.get("action", "")

        if action_name in DESKTOP_ACTIONS:
            return await self.desktop.execute(action)
        elif action_name in FILE_ACTIONS:
            return await self.file.execute(action)
        elif action_name in BROWSER_ACTIONS:
            return await self.browser.execute(action)
        elif action_name == "wait":
            import asyncio
            await asyncio.sleep(float(action.get("seconds", 1)))
            return {"success": True, "output": f"Waited {action.get('seconds', 1)}s"}
        elif action_name == "verify_state":
            # Observer handles actual verification; here we just pass through
            return {"success": True, "output": action.get("description", "State check requested")}
        else:
            return {"success": False, "error": f"Unknown action: {action_name}"}

    async def close(self):
        await self.browser.close()


__all__ = ["Executor"]
