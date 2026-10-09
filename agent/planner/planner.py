"""
LLM Planner — converts a voice command into a typed ActionPlan.
Uses the LLMProvider to generate JSON then validates it against the schema.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from agent.planner.schemas import ActionPlan
from agent.providers.base import LLMProvider
from agent.providers.llm_ollama import PLANNER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class Planner:
    """
    Converts transcribed voice text → validated ActionPlan.

    Flow:
    1. Build a prompt from the user command.
    2. Send to LLM with the PLANNER_SYSTEM_PROMPT.
    3. Extract JSON from the response.
    4. Validate against ActionPlan schema.
    5. Return the validated plan.
    """

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def plan(self, command: str) -> ActionPlan:
        """Generate and validate an action plan from a voice command."""
        logger.info(f"Planning for command: {command!r}")

        prompt = self._build_prompt(command)
        response = await self.llm.complete(prompt, system=PLANNER_SYSTEM_PROMPT)

        raw_json = self._extract_json(response.content)
        if raw_json is None:
            logger.error("LLM returned no valid JSON. Using fallback plan.")
            raw_json = self._fallback_plan(command)

        try:
            plan = ActionPlan.model_validate(raw_json)
            logger.info(f"Plan generated: {len(plan.steps)} steps for task: {plan.task!r}")
            return plan
        except Exception as e:
            logger.error(f"Plan validation failed: {e}")
            raise ValueError(f"Invalid action plan from LLM: {e}") from e

    def _build_prompt(self, command: str) -> str:
        return (
            f"The user said: \"{command}\"\n\n"
            "Create a structured JSON action plan to complete this task. "
            "Output ONLY the JSON object, no markdown fences or explanations."
        )

    def _extract_json(self, text: str) -> Optional[dict]:
        """Extract the first JSON object from an LLM response."""
        # Try direct parse first
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Strip markdown fences
        text = re.sub(r"```(?:json)?", "", text).strip("` \n")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Find the first {...} block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    def _fallback_plan(self, command: str) -> dict:
        """Return a safe no-op plan when the LLM fails."""
        return {
            "task": command,
            "expected_outcome": "Unable to plan — escalating to user.",
            "steps": [
                {
                    "action": "verify_state",
                    "description": "Fallback: LLM planning failed. No action taken.",
                    "risk": "low",
                }
            ],
        }
