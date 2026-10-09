"""
VoicePilot CLI — command-line interface for testing without the Tauri UI.
Runs a continuous voice loop in the terminal.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("voicepilot.cli")

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║          🎙️  VoicePilot — Offline Desktop AI Agent          ║
║          Privacy-first · Action-oriented · Self-recovering   ║
╠══════════════════════════════════════════════════════════════╣
║  Commands:                                                    ║
║    [Enter]        → Start voice recording                     ║
║    text + [Enter] → Send a text command                       ║
║    /quit           → Exit                                     ║
║    /metrics        → Show reliability metrics                 ║
║    /demo           → Run the offline demo task                ║
╚══════════════════════════════════════════════════════════════╝
"""

DEMO_COMMAND = (
    "Create a folder named Hackathon Demo on the desktop "
    "with a text file inside saying VoicePilot works offline."
)


async def run_cli():
    from agent.core import VoicePilotAgent
    from agent.audio.capture import MicrophoneCapture

    print(BANNER)

    agent = VoicePilotAgent(
        auto_approve_medium=True,  # CLI: skip medium-risk confirmations for demo
    )

    # Override confirmation callback for CLI
    async def cli_confirm(action_name: str, message: str) -> bool:
        print(f"\n⚠️  CONFIRMATION REQUIRED")
        print(f"   Action: {action_name}")
        print(f"   {message}")
        resp = input("   Approve? [y/N]: ").strip().lower()
        return resp in ("y", "yes")

    agent.safety.confirmation_callback = cli_confirm

    await agent.start()

    mic = MicrophoneCapture()

    # Background task to print events
    async def _print_events():
        async for event in agent.stream_events():
            _print_event(event)

    asyncio.create_task(_print_events())

    print("\n✅ VoicePilot ready. Type a command or press Enter to use voice.\n")

    while True:
        try:
            user_input = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("▶ ").strip()
            )
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            # Voice mode
            audio = await mic.record()
            if audio:
                await agent.run_audio(audio)
            else:
                print("  [Mic unavailable] Using demo command instead.")
                await agent.run_command(DEMO_COMMAND)

        elif user_input == "/quit":
            break

        elif user_input == "/metrics":
            metrics = await agent.metrics.get_metrics_summary()
            print("\n📊 Reliability Metrics:")
            for k, v in metrics.items():
                print(f"   {k}: {v}")
            print()

        elif user_input == "/demo":
            print(f"\n🚀 Running demo: {DEMO_COMMAND}\n")
            await agent.run_command(DEMO_COMMAND)

        else:
            await agent.run_command(user_input)

    print("\n👋 VoicePilot shutting down...")
    await agent.stop()


def _print_event(event: dict):
    t = event.get("type", "")
    d = event.get("data", {})
    colors = {
        "planning": "\033[34m",   # blue
        "plan_ready": "\033[34m",
        "step_start": "\033[33m",  # yellow
        "step_complete": "\033[32m",  # green
        "step_failed": "\033[31m",  # red
        "step_retry": "\033[33m",
        "task_complete": "\033[32m",
        "task_error": "\033[31m",
        "confirmation_required": "\033[35m",  # magenta
    }
    reset = "\033[0m"
    color = colors.get(t, "\033[37m")

    if t == "step_complete":
        print(f"  {color}✓ [{d.get('step_index')}] {d.get('action')}{reset}")
    elif t == "step_failed":
        print(f"  {color}✕ [{d.get('step_index')}] {d.get('action')} — {d.get('error', '')[:60]}{reset}")
    elif t == "step_retry":
        print(f"  {color}↻ [{d.get('step_index')}] retry #{d.get('retry_count')} — {d.get('action')}{reset}")
    elif t == "plan_ready":
        print(f"\n{color}📋 Plan: {d.get('task')}{reset}")
        for i, step in enumerate((d.get("steps") or [])):
            print(f"     {i+1}. {step.get('action')} [{step.get('risk', 'low')}]")
        print()
    elif t == "task_complete":
        status = "✅ SUCCESS" if d.get("success") else "❌ FAILED"
        dur = d.get("duration_seconds", 0)
        print(f"\n{color}{status} · {d.get('task', '')} ({dur:.1f}s){reset}\n")
    elif t == "transcribed":
        print(f"  {color}🎤 Transcribed: \"{d.get('text', '')}\"{reset}")


if __name__ == "__main__":
    asyncio.run(run_cli())
