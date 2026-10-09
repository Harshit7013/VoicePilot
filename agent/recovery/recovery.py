"""
Recovery module — handles retries, alternative strategies, and re-planning.
Five-stage recovery: Retry → Alternative → Re-establish → Re-plan → Escalate.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 1.5  # seconds


class RecoveryManager:
    """
    Manages the five-stage recovery process for failed actions.

    Stages:
    1. Retry       — repeat the same action after a short delay
    2. Alternative — try a keyboard shortcut or alternate navigation
    3. Re-establish — reopen the application or restore focus
    4. Re-plan     — ask the LLM to create a new plan
    5. Escalate    — surface the failure to the user
    """

    def __init__(self, planner=None, escalation_callback: Optional[Callable] = None):
        self.planner = planner
        self.escalation_callback = escalation_callback

    async def recover(
        self,
        action: Dict[str, Any],
        error: str,
        task: str,
        retry_count: int,
        executor,
    ) -> Dict[str, Any]:
        """
        Attempt recovery for a failed action.
        Returns the result dict from the best recovery attempt.
        """

        # Stage 1: Retry
        if retry_count < MAX_RETRIES:
            logger.warning(f"[RECOVERY] Retry {retry_count + 1}/{MAX_RETRIES} for action: {action.get('action')}")
            await asyncio.sleep(RETRY_DELAY * (retry_count + 1))
            result = await executor.execute(action)
            if result.get("success"):
                logger.info("[RECOVERY] Retry succeeded.")
                return {**result, "recovery_stage": "retry", "retry_count": retry_count + 1}

        # Stage 2: Alternative action
        alt = self._get_alternative(action)
        if alt:
            logger.warning(f"[RECOVERY] Trying alternative action: {alt.get('action')}")
            result = await executor.execute(alt)
            if result.get("success"):
                logger.info("[RECOVERY] Alternative succeeded.")
                return {**result, "recovery_stage": "alternative"}

        # Stage 3: Re-establish state (e.g., reopen app)
        reestablish = self._get_reestablish_action(action)
        if reestablish:
            logger.warning(f"[RECOVERY] Re-establishing state: {reestablish.get('action')}")
            await executor.execute(reestablish)
            await asyncio.sleep(2.0)
            result = await executor.execute(action)
            if result.get("success"):
                logger.info("[RECOVERY] Re-establish succeeded.")
                return {**result, "recovery_stage": "reestablish"}

        # Stage 4: Re-plan via LLM
        if self.planner:
            logger.warning("[RECOVERY] Re-planning with LLM...")
            try:
                new_plan = await self.planner.plan(
                    f"Retry task: {task}. Previous action '{action.get('action')}' failed with: {error}"
                )
                return {
                    "success": False,
                    "recovery_stage": "replan",
                    "new_plan": new_plan.model_dump(),
                    "error": error,
                }
            except Exception as e:
                logger.error(f"Re-planning failed: {e}")

        # Stage 5: Escalate
        logger.error(f"[RECOVERY] Escalating failure to user. Action: {action.get('action')}, Error: {error}")
        if self.escalation_callback:
            await self.escalation_callback(action, error, task)

        return {
            "success": False,
            "recovery_stage": "escalated",
            "error": f"All recovery stages exhausted. Original error: {error}",
        }

    def _get_alternative(self, action: Dict) -> Optional[Dict]:
        """Return an alternative action for known failure patterns."""
        name = action.get("action", "")

        if name == "click":
            # If clicking fails, try keyboard navigation
            return {"action": "press_key", "key": "tab", "risk": "low"}

        if name == "press_key" and action.get("key") == "ctrl+s":
            # If Ctrl+S fails, try File → Save menu
            return {"action": "press_key", "key": "alt+f", "risk": "low"}

        return None

    def _get_reestablish_action(self, action: Dict) -> Optional[Dict]:
        """Return an action to re-establish expected application state."""
        name = action.get("action", "")

        if name in {"click", "type_text", "press_key"}:
            # Try pressing Escape to dismiss any unexpected dialogs
            return {"action": "press_key", "key": "escape", "risk": "low"}

        return None
