"""
Desktop Executor — performs desktop automation actions using PyAutoGUI.
Uses a fixed action vocabulary; no arbitrary shell commands are executed.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


def _run_in_executor(func, *args):
    """Run a blocking function in a thread pool executor."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, func, *args)


class DesktopExecutor:
    """Handles desktop automation actions via PyAutoGUI."""

    def __init__(self):
        self._gui = None

    def _get_gui(self):
        if self._gui is not None:
            return self._gui
        try:
            import pyautogui
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.3
            self._gui = pyautogui
            return self._gui
        except ImportError:
            logger.warning("PyAutoGUI not installed. Desktop actions will be simulated.")
            return None

    async def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        action_name = action.get("action")
        handlers = {
            "open_application": self._open_application,
            "click": self._click,
            "type_text": self._type_text,
            "press_key": self._press_key,
            "take_screenshot": self._take_screenshot,
            "scroll": self._scroll,
        }
        handler = handlers.get(action_name)
        if handler is None:
            return {"success": False, "error": f"Unknown desktop action: {action_name}"}
        return await handler(action)

    async def _open_application(self, action: Dict) -> Dict:
        app = action.get("application", "").strip()
        logger.info(f"Opening application: {app}")

        # Common macOS / OS application name aliases
        aliases = {
            "calculator": "Calculator",
            "calc": "Calculator",
            "vs code": "Visual Studio Code",
            "vscode": "Visual Studio Code",
            "code": "Visual Studio Code",
            "visual studio code": "Visual Studio Code",
            "chrome": "Google Chrome",
            "google chrome": "Google Chrome",
            "safari": "Safari",
            "terminal": "Terminal",
            "finder": "Finder",
            "notes": "Notes",
            "textedit": "TextEdit",
        }
        target_app = aliases.get(app.lower(), app)

        try:
            if sys.platform == "darwin":
                proc = await asyncio.create_subprocess_exec(
                    "open", "-a", target_app,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode != 0 and target_app != app:
                    # Retry with raw app name if alias failed
                    proc2 = await asyncio.create_subprocess_exec(
                        "open", "-a", app,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    await proc2.wait()
            elif sys.platform == "win32":
                proc = await asyncio.create_subprocess_exec(
                    "start", target_app, shell=True,
                    stdout=asyncio.subprocess.DEVNULL,
                )
            else:
                proc = await asyncio.create_subprocess_exec(
                    target_app.lower().replace(" ", "-"),
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
            await asyncio.sleep(1.0)  # Allow app to launch
            return {"success": True, "output": f"Opened {target_app}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _click(self, action: Dict) -> Dict:
        gui = self._get_gui()
        target = action.get("target", "")
        logger.info(f"Clicking: {target}")
        if gui is None:
            return {"success": True, "output": f"[SIM] Clicked {target}"}
        try:
            # Try coordinate click first
            if "," in target and all(p.strip().isdigit() for p in target.split(",")):
                x, y = [int(p.strip()) for p in target.split(",")]
                await _run_in_executor(gui.click, x, y)
            else:
                # Find by image/text — use locateOnScreen if available
                location = await _run_in_executor(gui.locateOnScreen, target, 3)
                if location:
                    await _run_in_executor(gui.click, location)
                else:
                    return {"success": False, "error": f"Could not find element: {target}"}
            return {"success": True, "output": f"Clicked {target}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _type_text(self, action: Dict) -> Dict:
        gui = self._get_gui()
        text = action.get("text", "")
        logger.info(f"Typing text: {text[:30]}...")
        if gui is None:
            return {"success": True, "output": f"[SIM] Typed: {text}"}
        try:
            await _run_in_executor(gui.typewrite, text, 0.05)
            return {"success": True, "output": f"Typed: {text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _press_key(self, action: Dict) -> Dict:
        gui = self._get_gui()
        key = action.get("key", "")
        logger.info(f"Pressing key: {key}")
        if gui is None:
            return {"success": True, "output": f"[SIM] Pressed: {key}"}
        try:
            keys = key.split("+")
            if len(keys) > 1:
                await _run_in_executor(gui.hotkey, *keys)
            else:
                await _run_in_executor(gui.press, key)
            return {"success": True, "output": f"Pressed: {key}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _take_screenshot(self, action: Dict) -> Dict:
        gui = self._get_gui()
        save_path = action.get("save_path", "screenshot.png")
        if gui is None:
            return {"success": True, "output": f"[SIM] Screenshot saved to {save_path}"}
        try:
            screenshot = await _run_in_executor(gui.screenshot)
            screenshot.save(save_path)
            return {"success": True, "output": save_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _scroll(self, action: Dict) -> Dict:
        gui = self._get_gui()
        direction = action.get("direction", "down")
        amount = action.get("amount", 3)
        if gui is None:
            return {"success": True, "output": f"[SIM] Scrolled {direction} {amount}"}
        try:
            clicks = amount if direction in ("up", "right") else -amount
            await _run_in_executor(gui.scroll, clicks)
            return {"success": True, "output": f"Scrolled {direction}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
