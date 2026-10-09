"""
Browser Executor — uses Playwright for browser automation.
Falls back to simulation if Playwright is not installed.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

SEARCH_ENGINES = {
    "google": "https://www.google.com/search?q=",
    "bing": "https://www.bing.com/search?q=",
    "duckduckgo": "https://duckduckgo.com/?q=",
}


class BrowserExecutor:
    """Handles browser automation actions via Playwright."""

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._page = None

    async def _ensure_browser(self):
        if self._page is not None:
            return True
        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=False)
            self._page = await self._browser.new_page()
            logger.info("Playwright browser launched.")
            return True
        except ImportError:
            logger.warning("Playwright not installed. Browser actions will be simulated.")
            return False

    async def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        action_name = action.get("action")
        handlers = {
            "open_browser": self._open_browser,
            "navigate": self._navigate,
            "browser_click": self._browser_click,
            "browser_type": self._browser_type,
            "browser_search": self._browser_search,
            "browser_extract": self._browser_extract,
        }
        handler = handlers.get(action_name)
        if handler is None:
            return {"success": False, "error": f"Unknown browser action: {action_name}"}
        return await handler(action)

    async def _open_browser(self, action: Dict) -> Dict:
        ok = await self._ensure_browser()
        if not ok:
            return {"success": True, "output": "[SIM] Browser opened"}
        url = action.get("url")
        if url:
            await self._page.goto(url)
        return {"success": True, "output": "Browser opened"}

    async def _navigate(self, action: Dict) -> Dict:
        url = action.get("url", "")
        ok = await self._ensure_browser()
        if not ok:
            return {"success": True, "output": f"[SIM] Navigated to {url}"}
        try:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return {"success": True, "output": f"Navigated to {url}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _browser_click(self, action: Dict) -> Dict:
        selector = action.get("selector", "")
        ok = await self._ensure_browser()
        if not ok:
            return {"success": True, "output": f"[SIM] Clicked {selector}"}
        try:
            await self._page.click(selector, timeout=5000)
            return {"success": True, "output": f"Clicked {selector}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _browser_type(self, action: Dict) -> Dict:
        selector = action.get("selector", "")
        text = action.get("text", "")
        ok = await self._ensure_browser()
        if not ok:
            return {"success": True, "output": f"[SIM] Typed into {selector}"}
        try:
            await self._page.fill(selector, text)
            return {"success": True, "output": f"Typed into {selector}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _browser_search(self, action: Dict) -> Dict:
        query = action.get("query", "")
        engine = action.get("engine", "google").lower()
        base_url = SEARCH_ENGINES.get(engine, SEARCH_ENGINES["google"])
        url = base_url + query.replace(" ", "+")

        ok = await self._ensure_browser()
        if not ok:
            return {"success": True, "output": f"[SIM] Searched for: {query}"}
        try:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return {"success": True, "output": f"Searched: {query}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _browser_extract(self, action: Dict) -> Dict:
        selector = action.get("selector", "")
        attribute = action.get("attribute")
        ok = await self._ensure_browser()
        if not ok:
            return {"success": True, "output": f"[SIM] Extracted from {selector}"}
        try:
            element = await self._page.query_selector(selector)
            if element is None:
                return {"success": False, "error": f"Element not found: {selector}"}
            if attribute:
                value = await element.get_attribute(attribute)
            else:
                value = await element.inner_text()
            return {"success": True, "output": value}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
