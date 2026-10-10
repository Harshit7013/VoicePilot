"""
LLM Planner — converts a voice command into a typed ActionPlan.
Uses the LLMProvider to generate JSON then validates it against the schema.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from agent.planner.schemas import ActionPlan, AgentResponse
from agent.providers.base import LLMProvider
from agent.providers.llm_ollama import PLANNER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class Planner:
    """
    Converts transcribed voice text → validated AgentResponse.

    Flow:
    1. Build a prompt from the user command and history.
    2. Send to LLM with the PLANNER_SYSTEM_PROMPT.
    3. Extract JSON from the response.
    4. Validate against AgentResponse schema.
    5. Return the validated response.
    """

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    @staticmethod
    def _extract_open_app_target(command: str) -> Optional[str]:
        """
        Dynamically extracts application name from voice/text commands regardless of case
        or phrasing (e.g., 'open a application Netflix', 'open Netflix', 'start Netflix',
        'launch the netflix app', 'open netflix').
        """
        text = command.strip().strip(",.!?\"'")
        # Strip polite prefixes
        text = re.sub(
            r'^(?:please\s+|can\s+you\s+(?:please\s+)?|could\s+you\s+(?:please\s+)?|would\s+you\s+(?:please\s+)?|hey\s+)?',
            '', text, flags=re.IGNORECASE
        ).strip()
        pattern = r'^(?:open|launch|start|run)\s+(?:(?:an?|the)\s+)?(?:application|app|program|software)?(?:\s+(?:called|named))?\s*(.*?)(?:\s+(?:app|application|program|software))?(?:\s+please)?$'
        m = re.match(pattern, text, flags=re.IGNORECASE)
        if m:
            target = m.group(1).strip().strip(",.!?\"'")
            target = re.sub(r'^(?:the|an?)\s+', '', target, flags=re.IGNORECASE).strip()
            target = re.sub(r'^(?:(?:an?|the)\s+)?(?:application|app|program|software)?(?:\s+(?:called|named))?\s*', '', target, flags=re.IGNORECASE).strip()
            if target:
                return target
        return None

    async def plan(self, command: str, history: list[str] = None) -> AgentResponse:
        """Generate and validate a response/plan from a voice command."""
        logger.info(f"Planning for command: {command!r}")

        # Fast path intent routing for instant response (Siri/Alexa style)
        app_target = self._extract_open_app_target(command)
        if app_target:
            logger.info(f"Fast path match: open application {app_target!r}")
            return AgentResponse(
                message=f"Opening {app_target}",
                plan=ActionPlan(
                    task=f"Open {app_target}",
                    expected_outcome=f"{app_target} is opened.",
                    steps=[{"action": "open_application", "application": app_target, "risk": "low"}]
                )
            )

        prompt = self._build_prompt(command, history or [])
        
        system_prompt = PLANNER_SYSTEM_PROMPT
        try:
            from agent.executor.desktop import DesktopExecutor
            executor = DesktopExecutor()
            aliases = executor.get_app_aliases()
            apps = list(aliases.keys())
            if apps:
                system_prompt += f"\n\nKNOWN INSTALLED APPLICATIONS:\n{', '.join(apps)}"
        except Exception as e:
            logger.warning(f"Failed to load known applications for planner: {e}")
            
        response = await self.llm.complete(prompt, system=system_prompt)

        raw_json = self._extract_json(response.content)
        if raw_json is None:
            logger.error("LLM returned no valid JSON.")
            # Fallback for failed JSON extraction
            return AgentResponse(message="I didn't quite catch what I should do.", plan=None)

        try:
            agent_response = AgentResponse.model_validate(raw_json)
            if agent_response.plan:
                logger.info(f"Plan generated: {len(agent_response.plan.steps)} steps for task: {agent_response.plan.task!r}")
            return agent_response
        except Exception as e:
            logger.error(f"Plan validation failed: {e}")
            raise ValueError(f"Invalid agent response from LLM: {e}") from e

    def _build_prompt(self, command: str, history: list[str]) -> str:
        history_str = "\n".join(history)
        return (
            f"Conversation History:\n{history_str}\n\n"
            f"The user said: \"{command}\"\n\n"
            "Create a structured JSON response. If you need clarification, provide a message and leave plan null. "
            "If you have enough context, provide a message AND the action plan object. "
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
