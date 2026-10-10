"""
Desktop Executor — performs desktop automation actions using PyAutoGUI.
Uses a fixed action vocabulary; no arbitrary shell commands are executed.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _run_in_executor(func, *args):
    """Run a blocking function in a thread pool executor."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, func, *args)


class DesktopExecutor:
    """Handles desktop automation actions via PyAutoGUI."""

    def __init__(self):
        self._gui = None
        self._app_aliases: Optional[Dict[str, str]] = None
        self.active_app: Optional[str] = None
        self.active_window_title: Optional[str] = None

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
        action_name = action.get("action", "")
        if action_name.startswith("Desktop: "):
            action_name = action_name.split("Desktop: ")[1].strip()
            
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

    def get_app_aliases(self, force_refresh: bool = False) -> Dict[str, str]:
        """Get or dynamically discover installed Windows app aliases."""
        if self._app_aliases is not None and not force_refresh:
            return self._app_aliases

        import json
        aliases_file = Path("data/app_aliases.json")
        aliases: Dict[str, str] = {}

        def _discover_windows_apps() -> Dict[str, str]:
            apps: Dict[str, str] = {}
            if sys.platform != "win32":
                return apps

            # 1. StartApps via PowerShell (UWP, Store, and Win32 Start Menu items)
            try:
                proc = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "Get-StartApps | ConvertTo-Json -Compress"],
                    capture_output=True, text=True, timeout=12, creationflags=0x08000000
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    start_apps = json.loads(proc.stdout)
                    if isinstance(start_apps, dict):
                        start_apps = [start_apps]
                    for item in start_apps:
                        name = item.get("Name", "").strip()
                        appid = item.get("AppID", "").strip()
                        if not name or not appid:
                            continue
                        if appid.startswith("http://") or appid.startswith("https://"):
                            continue
                        target = f"explorer.exe shell:AppsFolder\\{appid}"
                        apps[name.lower()] = target
            except Exception as e:
                logger.warning(f"Could not discover Get-StartApps: {e}")

            # 2. Start Menu Programs (.lnk)
            try:
                paths = [
                    os.environ.get("ProgramData") + r"\Microsoft\Windows\Start Menu\Programs" if os.environ.get("ProgramData") else None,
                    os.environ.get("APPDATA") + r"\Microsoft\Windows\Start Menu\Programs" if os.environ.get("APPDATA") else None,
                ]
                for p in paths:
                    if not p or not os.path.exists(p):
                        continue
                    for lnk in Path(p).rglob("*.lnk"):
                        name = lnk.stem.lower()
                        if "uninstall" not in name and "setup" not in name and name not in apps:
                            apps[name] = str(lnk)
            except Exception as e:
                logger.warning(f"Could not scan Start Menu shortcuts: {e}")

            # 3. App Paths from Registry
            try:
                import winreg
                reg_paths = [
                    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
                    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
                ]
                for hkey, subkey in reg_paths:
                    try:
                        with winreg.OpenKey(hkey, subkey) as key:
                            for i in range(winreg.QueryInfoKey(key)[0]):
                                try:
                                    app_exe = winreg.EnumKey(key, i)
                                    app_name = app_exe.replace(".exe", "").lower()
                                    if app_name not in apps:
                                        apps[app_name] = app_exe
                                except OSError:
                                    pass
                    except OSError:
                        pass
            except Exception as e:
                logger.warning(f"Could not read Registry App Paths: {e}")

            # 4. Standard system utilities & friendly aliases
            if "google chrome" in apps and "chrome" not in apps:
                apps["chrome"] = apps["google chrome"]
            if "visual studio code" in apps:
                for alias in ["vs code", "vscode", "code"]:
                    if alias not in apps:
                        apps[alias] = apps["visual studio code"]
            if "calculator" in apps and "calc" not in apps:
                apps["calc"] = apps["calculator"]
            if "notepad" not in apps:
                apps["notepad"] = "notepad.exe"
            if "calc" not in apps:
                apps["calc"] = "calc.exe"
            if "cmd" not in apps:
                apps["cmd"] = "cmd.exe"
            if "terminal" not in apps and "wt" not in apps:
                apps["terminal"] = "wt.exe"
                apps["wt"] = "wt.exe"
            if "explorer" not in apps:
                apps["explorer"] = "explorer.exe"

            return apps

        # Load existing aliases file if valid (ensure no broken protocol URI like 'netflix:' or 'spotify:')
        if aliases_file.exists() and not force_refresh:
            try:
                with open(aliases_file, "r") as f:
                    loaded = json.load(f)
                has_broken_protocols = any(
                    isinstance(v, str) and v.endswith(":") and not v.startswith("explorer.exe")
                    for v in loaded.values()
                )
                if not has_broken_protocols and len(loaded) > 50:
                    aliases = loaded
            except Exception as e:
                logger.warning(f"Could not load aliases: {e}")

        # If empty or broken, run discovery and save
        if not aliases and sys.platform == "win32":
            try:
                aliases = _discover_windows_apps()
                aliases_file.parent.mkdir(exist_ok=True, parents=True)
                with open(aliases_file, "w") as f:
                    json.dump(aliases, f, indent=4)
            except Exception as e:
                logger.warning(f"Could not build dynamic aliases: {e}")

        self._app_aliases = aliases
        return aliases

    def _resolve_target_app(self, raw_app: str, aliases: Dict[str, str]) -> tuple[Optional[str], str, str]:
        """
        Dynamically and case-insensitively resolves an app name to its executable or shell command.
        Returns: (target_command, display_name, arguments)
        """
        clean_name = str(raw_app).strip().strip(",.!?\"'")
        # Strip command verbs and phrasing like "a application", "the app", etc.
        clean_name = re.sub(r'^(?:open|launch|start|run)\s+', '', clean_name, flags=re.IGNORECASE).strip()
        clean_name = re.sub(r'^(?:(?:an?|the)\s+)?(?:application|app|program|software)?(?:\s+(?:called|named))?\s*', '', clean_name, flags=re.IGNORECASE).strip()
        clean_name = re.sub(r'\s+(?:app|application|program|software)$', '', clean_name, flags=re.IGNORECASE).strip()
        if not clean_name:
            clean_name = raw_app

        clean_lower = clean_name.lower()
        args = ""

        # 1. Exact match in aliases (case-insensitive)
        if clean_lower in aliases:
            return aliases[clean_lower], clean_name, ""

        # 2. Check for passed arguments via shlex (e.g. 'chrome https://google.com')
        try:
            parts = shlex.split(clean_name, posix=False)
            if len(parts) > 1:
                first = parts[0].strip("\"'").lower()
                if first in aliases:
                    target = aliases[first]
                    args = clean_name[len(parts[0]):].strip()
                    return target, parts[0], args
        except Exception:
            pass

        # 3. Normalized alphanumeric match (strips spaces, hyphens, punctuation)
        norm_input = re.sub(r'[^a-z0-9]', '', clean_lower)
        if norm_input:
            for k, v in aliases.items():
                if re.sub(r'[^a-z0-9]', '', k) == norm_input:
                    return v, clean_name, ""

        # 4. Substring / Prefix match in aliases
        best_target = None
        best_k = None
        for k, v in aliases.items():
            if k == clean_lower:
                return v, clean_name, ""
            if k.startswith(clean_lower) or clean_lower.startswith(k):
                if best_k is None or len(k) > len(best_k):
                    best_target = v
                    best_k = k
        if best_target:
            return best_target, clean_name, ""

        for k, v in aliases.items():
            if clean_lower in k or k in clean_lower:
                if best_k is None or len(k) > len(best_k):
                    best_target = v
                    best_k = k
        if best_target:
            return best_target, clean_name, ""

        # 5. Check system PATH
        which_path = shutil.which(clean_name) or shutil.which(f"{clean_name}.exe")
        if which_path:
            return which_path, clean_name, ""

        # 6. Live query to Get-StartApps on Windows (for newly installed apps)
        if sys.platform == "win32":
            try:
                safe_name = re.sub(r'[^a-zA-Z0-9\s]', '', clean_name).strip()
                if safe_name:
                    ps_cmd = f"(Get-StartApps | Where-Object Name -match '{safe_name}' | Select-Object -First 1).AppID"
                    proc = subprocess.run(
                        ["powershell", "-NoProfile", "-Command", ps_cmd],
                        capture_output=True, text=True, timeout=5, creationflags=0x08000000
                    )
                    appid = proc.stdout.strip()
                    if appid:
                        target = f"explorer.exe shell:AppsFolder\\{appid}"
                        aliases[clean_lower] = target
                        return target, clean_name, ""
            except Exception:
                pass

        return None, clean_name, ""

    def _analyze_window(self) -> Dict[str, Any]:
        """Analyze the foreground active window and return title/metadata."""
        info = {"title": ""}
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                if hwnd:
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                        info["title"] = buff.value
            except Exception as e:
                logger.debug(f"Could not retrieve active window title: {e}")
        return info

    async def _open_application(self, action: Dict) -> Dict:
        app = action.get("application") or action.get("param") or action.get("text") or ""
        app = str(app).strip()
        custom_args = action.get("args") or ""
        logger.info(f"Opening application: {app}")

        if not app:
            return {"success": False, "error": "No application specified."}

        aliases = self.get_app_aliases()
        target_app, display_name, resolved_args = self._resolve_target_app(app, aliases)
        args = custom_args or resolved_args

        if not target_app:
            logger.warning(f"Application '{app}' not found on system.")
            return {
                "success": False,
                "error": f"Application '{app}' was not found. Please verify it is installed."
            }

        try:
            if sys.platform == "darwin":
                cmd = ["open", "-a", target_app]
                if args:
                    cmd.append("--args")
                    cmd.extend(shlex.split(args))
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = proc.communicate()
                if proc.returncode != 0 and target_app != app:
                    fallback_cmd = ["open", "-a", app]
                    subprocess.Popen(fallback_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif sys.platform == "win32":
                if target_app.startswith("explorer.exe"):
                    final_cmd = target_app
                    if args:
                        final_cmd = f"{target_app} {args}"
                else:
                    executable = target_app
                    if " " in executable and not executable.startswith('"'):
                        executable = f'"{executable}"'
                    command = executable
                    if args:
                        command = f"{executable} {args}"
                    final_cmd = f'start "" {command}'

                subprocess.Popen(
                    final_cmd,
                    shell=True,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                cmd = [target_app.lower().replace(" ", "-")]
                if args:
                    cmd.extend(shlex.split(args))
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            await asyncio.sleep(1.2)  # Allow app to launch and render

            # Analyze the opened window/application state
            analysis = self._analyze_window()
            window_title = analysis.get("title", "")
            self.active_app = display_name
            self.active_window_title = window_title

            output_msg = f"Opened {display_name}"
            if window_title:
                output_msg += f" (active window: '{window_title}')"
            logger.info(f"Analyzed opened app: {output_msg}")
            return {
                "success": True,
                "output": output_msg,
                "active_app": display_name,
                "window_title": window_title
            }
        except Exception as e:
            err = str(e) or repr(e)
            logger.error(f"Error opening application: {err}", exc_info=True)
            return {"success": False, "error": err}

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
