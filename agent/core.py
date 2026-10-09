"""
VoicePilot Core Agent — The main orchestrator implementing the 11-stage execution loop.

Loop:
  Listen → Transcribe → Plan → Validate → Execute → Observe → Verify → Recover → Complete
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from agent.executor import Executor
from agent.metrics import MetricsStore
from agent.observer import Observer
from agent.planner import ActionPlan, Planner, StepResult, TaskResult
from agent.providers import (
    LLMProvider,
    OllamaLLMProvider,
    PiperTTSProvider,
    STTProvider,
    TTSProvider,
    WhisperSTTProvider,
)
from agent.recovery import RecoveryManager
from agent.safety import PolicyGate, RiskClassifier

logger = logging.getLogger(__name__)


class VoicePilotAgent:
    """
    The main VoicePilot agent.

    Wires together all components and exposes:
      - run_command(text)    → for text-based commands (demo/API)
      - run_audio(bytes)     → for raw audio bytes from the microphone
      - stream_events()      → yields execution events as dicts (for WebSocket)
    """

    def __init__(
        self,
        stt: Optional[STTProvider] = None,
        llm: Optional[LLMProvider] = None,
        tts: Optional[TTSProvider] = None,
        auto_approve_medium: bool = False,
        db_path: str = "data/voicepilot.db",
        confirmation_callback: Optional[Callable] = None,
    ):
        self.stt = stt or WhisperSTTProvider()
        self.llm = llm or OllamaLLMProvider()
        self.tts = tts or PiperTTSProvider()

        self.planner = Planner(self.llm)
        self.executor = Executor()
        self.observer = Observer()
        self.metrics = MetricsStore(db_path)
        self.recovery = RecoveryManager(
            planner=self.planner,
            escalation_callback=self._escalate,
        )

        # Event bus: all execution events are put here, API reads from it
        self._event_queue: asyncio.Queue = asyncio.Queue()

        # Pending confirmation: task_id → asyncio.Future
        self._pending_confirmations: Dict[str, asyncio.Future] = {}

        classifier = RiskClassifier()
        cb = confirmation_callback or self._default_confirmation_callback
        self.safety = PolicyGate(classifier, cb, auto_approve_medium=auto_approve_medium)

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    async def start(self):
        """Initialize all async resources."""
        await self.metrics.connect()
        logger.info("VoicePilot agent started.")
        await self._emit("agent_ready", {"message": "VoicePilot is ready."})

    async def stop(self):
        """Gracefully shut down all resources."""
        await self.executor.close()
        await self.metrics.close()
        logger.info("VoicePilot agent stopped.")

    async def run_command(self, text: str) -> TaskResult:
        """
        Process a text command through the full execution loop.
        This is the primary entry point for both voice and text commands.
        """
        task_id = str(uuid.uuid4())
        start_time = time.time()

        await self._emit("task_start", {"task_id": task_id, "command": text})
        await self.metrics.record_task_start(task_id, text)

        step_results: List[StepResult] = []
        total_retries = 0
        error = None

        try:
            # Stage 1 & 2: (Transcription already done — text passed in directly)
            # Stage 3: Plan
            await self._emit("planning", {"task_id": task_id, "command": text})
            plan = await self.planner.plan(text)
            await self._emit("plan_ready", {
                "task_id": task_id,
                "task": plan.task,
                "steps": plan.steps,
                "expected_outcome": plan.expected_outcome,
            })

            # Stage 4–10: Execute each step
            for i, step in enumerate(plan.steps):
                step_result = await self._execute_step(task_id, plan, step, i)
                step_results.append(step_result)
                total_retries += step_result.retry_count

                if not step_result.success and step_result.retry_count >= 3:
                    error = f"Step {i} failed after max retries: {step_result.error}"
                    break

            # Stage 11: Completion
            success = all(r.success for r in step_results)
            duration = time.time() - start_time
            result = TaskResult(
                task_id=task_id,
                task=plan.task,
                success=success,
                steps=step_results,
                total_retries=total_retries,
                duration_seconds=duration,
                error=error,
            )

            completion_msg = (
                f"Task complete: {plan.task}"
                if success
                else f"Task failed: {error or 'Unknown error'}"
            )
            await self.tts.speak(completion_msg)
            await self._emit("task_complete", result.model_dump())
            await self.metrics.record_task_complete(task_id, success, duration, total_retries, error)
            return result

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Task {task_id} crashed: {e}", exc_info=True)
            error_msg = str(e)
            await self.tts.speak(f"An error occurred: {error_msg}")
            await self._emit("task_error", {"task_id": task_id, "error": error_msg})
            await self.metrics.record_task_complete(task_id, False, duration, total_retries, error_msg)
            return TaskResult(
                task_id=task_id,
                task=text,
                success=False,
                error=error_msg,
                duration_seconds=duration,
            )

    async def run_audio(self, audio_bytes: bytes, sample_rate: int = 16000) -> TaskResult:
        """Process raw audio through STT then run_command."""
        await self._emit("transcribing", {})
        result = await self.stt.transcribe(audio_bytes, sample_rate)
        logger.info(f"Transcribed: {result.text!r} (lang={result.language}, conf={result.confidence:.2f})")
        await self._emit("transcribed", {"text": result.text, "confidence": result.confidence})
        return await self.run_command(result.text)

    async def confirm(self, confirmation_id: str, approved: bool) -> None:
        """Called by the API layer when the user approves/rejects a confirmation."""
        future = self._pending_confirmations.get(confirmation_id)
        if future and not future.done():
            future.set_result(approved)

    async def stream_events(self) -> AsyncIterator[Dict]:
        """Async generator that yields execution events as they happen."""
        while True:
            event = await self._event_queue.get()
            yield event

    # ──────────────────────────────────────────────
    # Internal step execution
    # ──────────────────────────────────────────────

    async def _execute_step(
        self,
        task_id: str,
        plan: ActionPlan,
        step: Dict[str, Any],
        step_index: int,
    ) -> StepResult:
        """Execute a single step with safety validation, observation, and verification."""
        action_name = step.get("action", "unknown")
        retry_count = 0

        await self._emit("step_start", {
            "task_id": task_id,
            "step_index": step_index,
            "action": action_name,
            "details": step,
        })

        # Stage 4: Safety validation
        approved = await self.safety.check(step, plan.task)
        if not approved:
            await self._emit("step_blocked", {"task_id": task_id, "step_index": step_index, "action": action_name})
            return StepResult(
                step_index=step_index,
                action=action_name,
                success=False,
                error="Blocked by safety gate — user did not approve.",
            )

        # Stage 5: Execute
        result = await self.executor.execute(step)
        await self.metrics.record_event(
            task_id, step_index, action_name,
            result.get("success", False), result.get("output"), result.get("error"),
        )

        # Stage 6: Observe
        observation = await self.observer.observe()

        # Stage 7: Verify
        verified = await self._verify_step(step, result, observation)

        if result.get("success") and verified:
            await self._emit("step_complete", {
                "task_id": task_id,
                "step_index": step_index,
                "action": action_name,
                "output": result.get("output"),
                "verified": True,
            })
            await self.metrics.record_event(
                task_id, step_index, action_name,
                True, result.get("output"), verified=True,
            )
            return StepResult(
                step_index=step_index,
                action=action_name,
                success=True,
                output=result.get("output"),
                verified=True,
            )

        # Stage 8: Recovery loop
        while retry_count < 3:
            error_msg = result.get("error", "Verification failed")
            await self._emit("step_retry", {
                "task_id": task_id,
                "step_index": step_index,
                "action": action_name,
                "retry_count": retry_count + 1,
                "error": error_msg,
            })

            recovery_result = await self.recovery.recover(
                step, error_msg, plan.task, retry_count, self.executor
            )
            retry_count += 1

            await self.metrics.record_recovery(
                task_id, step_index,
                recovery_result.get("recovery_stage", "retry"),
                recovery_result.get("success", False),
            )

            if recovery_result.get("success"):
                # Re-observe and re-verify after recovery
                new_observation = await self.observer.observe()
                re_verified = await self._verify_step(step, recovery_result, new_observation)
                if re_verified:
                    await self._emit("step_recovered", {
                        "task_id": task_id,
                        "step_index": step_index,
                        "stage": recovery_result.get("recovery_stage"),
                    })
                    return StepResult(
                        step_index=step_index,
                        action=action_name,
                        success=True,
                        output=recovery_result.get("output"),
                        verified=True,
                        retry_count=retry_count,
                    )

            if recovery_result.get("recovery_stage") == "escalated":
                break

        # All recovery failed
        final_error = result.get("error", "Unknown error")
        await self._emit("step_failed", {
            "task_id": task_id,
            "step_index": step_index,
            "action": action_name,
            "error": final_error,
        })
        return StepResult(
            step_index=step_index,
            action=action_name,
            success=False,
            error=final_error,
            retry_count=retry_count,
        )

    async def _verify_step(
        self,
        step: Dict[str, Any],
        result: Dict[str, Any],
        observation: Dict[str, Any],
    ) -> bool:
        """Verify that the step's expected outcome was achieved."""
        if not result.get("success"):
            return False

        action_name = step.get("action", "")

        # File verification: check the file actually exists
        if action_name == "verify_file":
            path = step.get("path", "")
            if path:
                import os
                return os.path.exists(os.path.expanduser(os.path.expandvars(path)))

        if action_name in {"create_file", "write_file", "create_directory"}:
            path = step.get("path", "")
            if path:
                import os
                return os.path.exists(os.path.expanduser(os.path.expandvars(path)))

        # verify_state: use OCR if description contains expected text
        if action_name == "verify_state":
            description = step.get("description", "")
            if description and observation.get("visible_text"):
                return any(
                    description.lower() in t.lower()
                    for t in observation.get("visible_text", [])
                )

        # Default: trust the tool result
        return result.get("success", False)

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────

    async def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Put an event on the queue for the WebSocket layer to stream."""
        await self._event_queue.put({"type": event_type, "data": data})

    async def _default_confirmation_callback(self, action_name: str, message: str) -> bool:
        """
        Default callback: creates a confirmation request and waits for the
        UI to respond via the /confirm endpoint.
        In CLI mode, falls back to a local asyncio.Future timeout (auto-deny after 30s).
        """
        confirmation_id = str(uuid.uuid4())
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_confirmations[confirmation_id] = future

        await self._emit("confirmation_required", {
            "confirmation_id": confirmation_id,
            "action": action_name,
            "message": message,
        })

        try:
            approved = await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            logger.warning(f"Confirmation timed out for {action_name}. Auto-denying.")
            approved = False
        finally:
            self._pending_confirmations.pop(confirmation_id, None)

        return approved

    async def _escalate(self, action: Dict, error: str, task: str) -> None:
        """Escalate an unrecoverable failure to the user."""
        await self._emit("escalation", {
            "action": action.get("action"),
            "error": error,
            "task": task,
            "message": f"VoicePilot could not complete '{action.get('action')}'. Manual intervention required.",
        })
        await self.tts.speak(
            f"I was unable to complete the action {action.get('action')}. "
            "Please check the task log and try again."
        )
