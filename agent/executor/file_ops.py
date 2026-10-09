"""
File Operations Executor — uses pathlib and shutil only.
No shell commands. All paths are resolved safely.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _resolve(path: str) -> Path:
    """Resolve ~ and make absolute."""
    return Path(os.path.expandvars(os.path.expanduser(path))).resolve()


class FileExecutor:
    """Handles all file system operations via pathlib / shutil."""

    async def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        action_name = action.get("action")
        handlers = {
            "create_file": self._create_file,
            "read_file": self._read_file,
            "write_file": self._write_file,
            "delete_file": self._delete_file,
            "move_file": self._move_file,
            "copy_file": self._copy_file,
            "create_directory": self._create_directory,
            "list_directory": self._list_directory,
            "find_files": self._find_files,
            "verify_file": self._verify_file,
        }
        handler = handlers.get(action_name)
        if handler is None:
            return {"success": False, "error": f"Unknown file action: {action_name}"}
        try:
            return await handler(action)
        except PermissionError as e:
            return {"success": False, "error": f"Permission denied: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _create_file(self, action: Dict) -> Dict:
        path = _resolve(action["path"])
        content = action.get("content", "")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        logger.info(f"Created file: {path}")
        return {"success": True, "output": str(path)}

    async def _read_file(self, action: Dict) -> Dict:
        path = _resolve(action["path"])
        if not path.exists():
            return {"success": False, "error": f"File not found: {path}"}
        content = path.read_text(encoding="utf-8", errors="replace")
        return {"success": True, "output": content}

    async def _write_file(self, action: Dict) -> Dict:
        path = _resolve(action["path"])
        content = action.get("content", "")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        logger.info(f"Wrote file: {path}")
        return {"success": True, "output": str(path)}

    async def _delete_file(self, action: Dict) -> Dict:
        path = _resolve(action["path"])
        if not path.exists():
            return {"success": False, "error": f"Not found: {path}"}
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        logger.info(f"Deleted: {path}")
        return {"success": True, "output": str(path)}

    async def _move_file(self, action: Dict) -> Dict:
        src = _resolve(action["source"])
        dst = _resolve(action["destination"])
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        logger.info(f"Moved {src} → {dst}")
        return {"success": True, "output": str(dst)}

    async def _copy_file(self, action: Dict) -> Dict:
        src = _resolve(action["source"])
        dst = _resolve(action["destination"])
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
        else:
            shutil.copy2(str(src), str(dst))
        logger.info(f"Copied {src} → {dst}")
        return {"success": True, "output": str(dst)}

    async def _create_directory(self, action: Dict) -> Dict:
        path = _resolve(action["path"])
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {path}")
        return {"success": True, "output": str(path)}

    async def _list_directory(self, action: Dict) -> Dict:
        path = _resolve(action["path"])
        if not path.exists():
            return {"success": False, "error": f"Directory not found: {path}"}
        entries = [str(p) for p in sorted(path.iterdir())]
        return {"success": True, "output": entries}

    async def _find_files(self, action: Dict) -> Dict:
        directory = _resolve(action["directory"])
        pattern = action.get("pattern", "*")
        recursive = action.get("recursive", True)

        if not directory.exists():
            return {"success": False, "error": f"Directory not found: {directory}"}

        if recursive:
            results = [str(p) for p in directory.rglob(pattern) if p.is_file()]
        else:
            results = [str(p) for p in directory.glob(pattern) if p.is_file()]

        return {"success": True, "output": results}

    async def _verify_file(self, action: Dict) -> Dict:
        path = _resolve(action["path"])
        expected_content = action.get("expected_content")

        if not path.exists():
            return {"success": False, "error": f"File not found: {path}", "verified": False}

        if expected_content is not None:
            actual = path.read_text(encoding="utf-8", errors="replace")
            if expected_content not in actual:
                return {
                    "success": False,
                    "error": "Content mismatch",
                    "verified": False,
                    "expected": expected_content,
                    "actual": actual[:200],
                }

        return {"success": True, "output": str(path), "verified": True}
