"""
Ollama-based local LLM provider.
Generates structured JSON action plans using a Qwen3-class or similar model.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Optional

from agent.providers.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are PULSE (Personal Unleashed AI), an offline desktop automation agent.
Your job is to act as a conversational assistant that can also execute structured JSON action plans.

RULES:
1. Only use actions from the approved vocabulary.
2. Never output shell commands or arbitrary code.
3. Always include a verify_file or verify_state step at the end.
4. Keep plans minimal — use the fewest steps needed.
5. Set risk levels correctly: LOW for reads/opens, MEDIUM for creates/moves, HIGH for deletes/sends.

APPROVED ACTIONS:
Desktop: open_application, click, type_text, press_key, take_screenshot, scroll
Files: create_file, read_file, write_file, delete_file, move_file, copy_file,
       create_directory, list_directory, find_files, verify_file
Browser: open_browser, navigate, browser_click, browser_type, browser_search, browser_extract
System: wait, verify_state

OUTPUT FORMAT (JSON only, no markdown):
{
  "message": "<A human-centric, conversational response. If ambiguous, ask for clarification.>",
  "plan": {
    "task": "<human-readable task description>",
    "expected_outcome": "<what success looks like>",
    "steps": [
      {"action": "<action_name>", "<param>": "<value>", "risk": "low|medium|high"}
    ]
  } // OR null if you just need to speak a message/ask a question.
}
"""


class OllamaLLMProvider(LLMProvider):
    """
    LLM provider using a locally running Ollama instance.
    Model: qwen3:latest or qwen2.5:7b or any Ollama-compatible model.
    """

    def __init__(self, model: str = "qwen2.5:1.5b", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import ollama
            self._client = ollama.AsyncClient(host=self.host)
            return self._client
        except ImportError:
            logger.warning("ollama package not installed. Using simulated LLM.")
            return None

    async def complete(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        client = self._get_client()

        if client is None:
            raise RuntimeError("Ollama LLM is not installed. Please install Ollama and run 'ollama pull qwen2.5:7b'.")

        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = await client.chat(model=self.model, messages=messages)
            content = response.message.content
            tokens = response.eval_count or 0

            return LLMResponse(content=content, model=self.model, tokens_used=tokens)

        except Exception as e:
            logger.warning(f"Ollama request failed: {e}")
            raise RuntimeError(f"Ollama LLM request failed. Ensure Ollama is running (localhost:11434). Error: {e}")

    async def stream(self, prompt: str, system: Optional[str] = None) -> AsyncIterator[str]:
        client = self._get_client()

        if client is None:
            raise RuntimeError("Ollama LLM is not installed. Please install Ollama and run 'ollama pull qwen2.5:7b'.")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            async for chunk in await client.chat(model=self.model, messages=messages, stream=True):
                if chunk.message and chunk.message.content:
                    yield chunk.message.content
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            raise RuntimeError(f"Ollama LLM streaming failed. Ensure Ollama is running (localhost:11434). Error: {e}")
