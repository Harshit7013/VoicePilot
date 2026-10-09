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

PLANNER_SYSTEM_PROMPT = """You are VoicePilot, an offline desktop automation agent.
Your job is to convert a user's voice command into a structured JSON action plan.

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
  "task": "<human-readable task description>",
  "expected_outcome": "<what success looks like>",
  "steps": [
    {"action": "<action_name>", "<param>": "<value>", "risk": "low|medium|high"},
    ...
  ]
}
"""


class OllamaLLMProvider(LLMProvider):
    """
    LLM provider using a locally running Ollama instance.
    Model: qwen3:latest or qwen2.5:7b or any Ollama-compatible model.
    """

    def __init__(self, model: str = "qwen2.5:7b", host: str = "http://localhost:11434"):
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
            return self._simulated_response(prompt)

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
            logger.warning(f"Ollama request failed: {e}. Using simulated response.")
            return self._simulated_response(prompt)

    async def stream(self, prompt: str, system: Optional[str] = None) -> AsyncIterator[str]:
        client = self._get_client()

        if client is None:
            yield self._simulated_response(prompt).content
            return

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
            yield self._simulated_response(prompt).content

    def _simulated_response(self, prompt: str) -> LLMResponse:
        """Pattern-aware simulated response fallback when Ollama model is offline."""
        prompt_lower = prompt.lower()

        if "calculator" in prompt_lower or "calc" in prompt_lower or "calculate" in prompt_lower:
            plan = {
                "task": "Open Calculator",
                "expected_outcome": "Calculator application is opened",
                "steps": [
                    {"action": "open_application", "application": "Calculator", "risk": "low"},
                ]
            }
        elif "code" in prompt_lower or "hello.py" in prompt_lower or "vs code" in prompt_lower or "vscode" in prompt_lower:
            plan = {
                "task": "Create hello.py in VS Code",
                "expected_outcome": "hello.py created on Desktop",
                "steps": [
                    {"action": "open_application", "application": "Visual Studio Code", "risk": "low"},
                    {"action": "create_file", "path": "~/Desktop/hello.py", "risk": "medium"},
                    {"action": "write_file", "path": "~/Desktop/hello.py", "content": "print('Hello World')", "risk": "medium"},
                    {"action": "verify_file", "path": "~/Desktop/hello.py", "risk": "low"}
                ]
            }
        elif "browser" in prompt_lower or "search" in prompt_lower or "google" in prompt_lower:
            plan = {
                "task": "Search web in browser",
                "expected_outcome": "Browser opened with search results",
                "steps": [
                    {"action": "open_browser", "url": "https://www.google.com", "risk": "low"},
                    {"action": "browser_search", "query": prompt, "risk": "low"}
                ]
            }
        elif "download" in prompt_lower or "pdf" in prompt_lower:
            plan = {
                "task": "Organize PDF files in Downloads",
                "expected_outcome": "PDF files moved to Desktop/PDFs",
                "steps": [
                    {"action": "find_files", "path": "~/Downloads", "pattern": "*.pdf", "risk": "low"},
                    {"action": "create_directory", "path": "~/Desktop/PDFs", "risk": "medium"},
                ]
            }
        else:
            plan = {
                "task": prompt,
                "expected_outcome": "Command executed successfully",
                "steps": [
                    {"action": "create_directory", "path": "~/Desktop/HackathonDemo", "risk": "medium"},
                    {"action": "create_file", "path": "~/Desktop/HackathonDemo/voicepilot.txt",
                     "content": f"VoicePilot executed: {prompt}", "risk": "medium"},
                    {"action": "verify_file", "path": "~/Desktop/HackathonDemo/voicepilot.txt", "risk": "low"},
                ],
            }
        return LLMResponse(content=json.dumps(plan), model="simulated-qwen3", tokens_used=0)
