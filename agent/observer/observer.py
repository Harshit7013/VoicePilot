"""
Observer — captures screenshots and uses PaddleOCR to inspect visible UI state.
Used by the verification step to compare expected vs actual outcomes.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Observer:
    """
    Captures the current system state (screenshot + OCR text).
    Provides verification helpers to check whether an expected condition is met.
    """

    def __init__(self, screenshot_dir: str = "data/screenshots"):
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self._ocr = None
        self._gui = None

    def _get_gui(self):
        if self._gui is not None:
            return self._gui
        try:
            import pyautogui
            self._gui = pyautogui
        except ImportError:
            pass
        return self._gui

    def _get_ocr(self):
        if self._ocr is not None:
            return self._ocr
        try:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
            logger.info("PaddleOCR initialized.")
        except ImportError:
            logger.warning("PaddleOCR not installed. OCR checks will be skipped.")
        return self._ocr

    async def capture_screenshot(self, label: str = "obs") -> Optional[str]:
        """Take a screenshot and save it. Returns the file path."""
        gui = self._get_gui()
        if gui is None:
            logger.debug("PyAutoGUI not available; skipping screenshot.")
            return None
        try:
            loop = asyncio.get_event_loop()
            screenshot = await loop.run_in_executor(None, gui.screenshot)
            path = self.screenshot_dir / f"{label}_{int(asyncio.get_event_loop().time()*1000)}.png"
            screenshot.save(str(path))
            logger.debug(f"Screenshot saved: {path}")
            return str(path)
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")
            return None

    async def extract_text_from_screen(self, screenshot_path: Optional[str] = None) -> List[str]:
        """Run OCR on a screenshot and return all text strings found."""
        if screenshot_path is None:
            screenshot_path = await self.capture_screenshot("ocr_check")

        if screenshot_path is None:
            return []

        def _do_ocr(path: str) -> List[str]:
            ocr = self._get_ocr()
            if ocr is None:
                return []
            results = ocr.ocr(path, True)
            texts = []
            for line in (results or []):
                if line:
                    for item in line:
                        if item and len(item) >= 2 and item[1]:
                            texts.append(item[1][0])
            return texts

        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _do_ocr, screenshot_path)
        except Exception as e:
            logger.warning(f"OCR failed: {e}")
            return []

    async def verify_text_on_screen(self, expected_text: str) -> bool:
        """Return True if expected_text appears somewhere on screen via OCR."""
        texts = await self.extract_text_from_screen()
        found = any(expected_text.lower() in t.lower() for t in texts)
        logger.info(f"OCR verify '{expected_text}': {'FOUND' if found else 'NOT FOUND'}")
        return found

    async def observe(self) -> Dict[str, Any]:
        """Full observation: screenshot + OCR text."""
        path = await self.capture_screenshot("observe")
        texts = await self.extract_text_from_screen(path) if path else []
        return {
            "screenshot": path,
            "visible_text": texts,
        }
