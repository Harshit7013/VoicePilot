"""
FastAPI server — bridges the Python agent runtime to the Tauri/React frontend.

Endpoints:
  GET  /                        - health check
  POST /command                 - submit a text command
  POST /audio                   - upload audio for transcription + execution
  POST /confirm/{id}            - approve/reject a pending confirmation
  GET  /tasks                   - list recent tasks
  GET  /metrics                 - reliability metrics summary
  WS   /ws                      - real-time execution event stream
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.core import VoicePilotAgent
from agent.providers import LocalOfflineLLMProvider, PiperTTSProvider, WhisperSTTProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Global agent instance
_agent: Optional[VoicePilotAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent
    _agent = VoicePilotAgent(
        stt=WhisperSTTProvider(model_size=os.getenv("WHISPER_MODEL", "base")),
        llm=LocalOfflineLLMProvider(model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b")),
        tts=PiperTTSProvider(),
        auto_approve_medium=os.getenv("AUTO_APPROVE_MEDIUM", "false").lower() == "true",
    )
    await _agent.start()
    logger.info("VoicePilot API server ready.")
    yield
    await _agent.stop()


app = FastAPI(
    title="VoicePilot API",
    description="Offline voice-controlled desktop task automation agent.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tauri app origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# Request / Response models
# ──────────────────────────────────────────────

class CommandRequest(BaseModel):
    command: str


class ConfirmRequest(BaseModel):
    approved: bool


class AudioRequest(BaseModel):
    audio_base64: str  # base64-encoded WAV bytes
    sample_rate: int = 16000


# ──────────────────────────────────────────────
# REST Endpoints
# ──────────────────────────────────────────────

@app.get("/")
async def health():
    return {"status": "ok", "agent": "VoicePilot", "version": "1.0.0"}


@app.post("/command")
async def run_command(req: CommandRequest):
    """Submit a text command to the agent."""
    if _agent is None:
        raise HTTPException(503, "Agent not ready")
    # Run in background, return task_id immediately
    task_id_holder = {}

    async def _run():
        result = await _agent.run_command(req.command)
        task_id_holder["result"] = result

    asyncio.create_task(_run())

    return {"status": "accepted", "message": f"Processing: {req.command}"}


@app.post("/command/sync")
async def run_command_sync(req: CommandRequest):
    """Submit a text command and wait for the result (blocking)."""
    if _agent is None:
        raise HTTPException(503, "Agent not ready")
    result = await _agent.run_command(req.command)
    return result.model_dump()


@app.post("/audio")
async def run_audio(req: AudioRequest):
    """Submit base64-encoded audio for transcription and execution."""
    if _agent is None:
        raise HTTPException(503, "Agent not ready")
    audio_bytes = base64.b64decode(req.audio_base64)
    result = await _agent.run_audio(audio_bytes, req.sample_rate)
    return result.model_dump()


@app.post("/confirm/{confirmation_id}")
async def confirm_action(confirmation_id: str, req: ConfirmRequest):
    """Approve or reject a pending confirmation request from the UI."""
    if _agent is None:
        raise HTTPException(503, "Agent not ready")
    await _agent.confirm(confirmation_id, req.approved)
    return {"status": "confirmed", "approved": req.approved}


@app.get("/tasks")
async def get_tasks(limit: int = 20):
    """Get recent task history."""
    if _agent is None:
        raise HTTPException(503, "Agent not ready")
    tasks = await _agent.metrics.get_recent_tasks(limit)
    return {"tasks": tasks}


@app.get("/metrics")
async def get_metrics():
    """Get reliability metrics summary."""
    if _agent is None:
        raise HTTPException(503, "Agent not ready")
    return await _agent.metrics.get_metrics_summary()


# ──────────────────────────────────────────────
# WebSocket: Real-time event stream
# ──────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Real-time execution event stream.
    The frontend connects here to receive all agent events as JSON.
    """
    await websocket.accept()
    logger.info("WebSocket client connected.")

    if _agent is None:
        await websocket.send_json({"type": "error", "data": {"message": "Agent not ready"}})
        await websocket.close()
        return

    try:
        async for event in _agent.stream_events():
            await websocket.send_json(event)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


# ──────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "agent.api:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
        log_level="info",
    )
