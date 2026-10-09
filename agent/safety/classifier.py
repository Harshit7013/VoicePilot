"""
Safety module: Risk classification and policy gate.
Every planned action is classified and passed through the policy gate before execution.
"""

from __future__ import annotations

import logging
from typing import Callable, Awaitable

from agent.planner.schemas import AnyAction, RiskLevel

logger = logging.getLogger(__name__)


class RiskClassifier:
    """
    Classifies each action into LOW / MEDIUM / HIGH risk.
    The risk level is embedded in the action schema itself but this
    classifier can also apply override rules based on context.
    """

    # Action types that are always treated as HIGH risk regardless of schema
    HIGH_RISK_ACTIONS = {"delete_file", "delete_directory"}
    MEDIUM_RISK_ACTIONS = {
        "create_file", "write_file", "move_file", "copy_file",
        "create_directory", "browser_type", "type_text",
    }

    def classify(self, action: dict) -> RiskLevel:
        action_name = action.get("action", "")
        schema_risk = action.get("risk", "low")

        if action_name in self.HIGH_RISK_ACTIONS:
            return RiskLevel.HIGH
        if action_name in self.MEDIUM_RISK_ACTIONS:
            return RiskLevel.MEDIUM
        return RiskLevel(schema_risk)


# Type alias for a confirmation callback provided by the API layer
ConfirmationCallback = Callable[[str, str], Awaitable[bool]]


class PolicyGate:
    """
    Applies the risk policy:
    - LOW    → auto-approve
    - MEDIUM → configurable (auto or ask)
    - HIGH   → always ask for confirmation

    The confirmation_callback is an async function that the API layer
    provides to surface the confirmation request to the UI.
    """

    def __init__(
        self,
        classifier: RiskClassifier,
        confirmation_callback: ConfirmationCallback,
        auto_approve_medium: bool = False,
    ):
        self.classifier = classifier
        self.confirmation_callback = confirmation_callback
        self.auto_approve_medium = auto_approve_medium

    async def check(self, action: dict, task: str) -> bool:
        """
        Returns True if execution is approved, False if blocked.
        """
        risk = self.classifier.classify(action)
        action_name = action.get("action", "unknown")

        if risk == RiskLevel.LOW:
            logger.debug(f"AUTO-APPROVE (low risk): {action_name}")
            return True

        if risk == RiskLevel.MEDIUM:
            if self.auto_approve_medium:
                logger.debug(f"AUTO-APPROVE (medium, policy): {action_name}")
                return True
            message = f"Action '{action_name}' requires confirmation.\nTask: {task}"
            return await self.confirmation_callback(action_name, message)

        if risk == RiskLevel.HIGH:
            message = (
                f"⚠️ HIGH-RISK action: '{action_name}'\n"
                f"Task: {task}\n"
                f"Details: {action}"
            )
            logger.warning(f"CONFIRMATION REQUIRED (high risk): {action_name}")
            return await self.confirmation_callback(action_name, message)

        return True  # Default allow
