"""
Piper / system TTS provider for local, offline speech synthesis.
Falls back to system 'say' on macOS or 'espeak' on Linux if Piper is unavailable.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path

from agent.providers.base import TTSProvider

logger = logging.getLogger(__name__)


class PiperTTSProvider(TTSProvider):
    """
    Local TTS using Piper TTS.
    If Piper is not installed, falls back to OS-native TTS (say/espeak).
    """

    def __init__(self, voice: str = "en_US-lessac-medium", model_dir: str = "models/tts"):
        self.voice = voice
        self.model_dir = Path(model_dir)
        self._piper_available = self._check_piper()

    def _check_piper(self) -> bool:
        try:
            result = subprocess.run(["piper", "--version"], capture_output=True, timeout=3)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    async def synthesize(self, text: str) -> bytes:
        if self._piper_available:
            return await self._synthesize_piper(text)
        return b""  # No audio bytes for OS fallback

    async def _synthesize_piper(self, text: str) -> bytes:
        model_path = self.model_dir / f"{self.voice}.onnx"
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            out_path = tmp.name

        try:
            proc = await asyncio.create_subprocess_exec(
                "piper",
                "--model", str(model_path),
                "--output_file", out_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate(input=text.encode())
            return Path(out_path).read_bytes()
        finally:
            Path(out_path).unlink(missing_ok=True)

    async def speak(self, text: str) -> None:
        """Speak text aloud using Piper, falling back gracefully if missing."""
        logger.info(f"TTS: {text}")

        if self._piper_available:
            try:
                audio_bytes = await self._synthesize_piper(text)
                await self._play_audio(audio_bytes)
                return
            except Exception as e:
                logger.warning(f"Piper TTS synthesis failed: {e}. Trying fallback.")

        # Fallback to OS TTS
        try:
            await self._os_fallback_speak(text)
        except Exception as e:
            logger.warning(f"OS TTS fallback failed: {e}. Continuing silently.")

    async def _play_audio(self, audio_bytes: bytes) -> None:
        """Play WAV audio bytes via sounddevice or afplay."""
        try:
            import sounddevice as sd
            import soundfile as sf
            import io

            with sf.SoundFile(io.BytesIO(audio_bytes)) as f:
                data = f.read(dtype="float32")
                rate = f.samplerate

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: sd.play(data, rate, blocking=True))
        except Exception as e:
            logger.debug(f"sounddevice playback failed ({e}), trying afplay")
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            try:
                proc = await asyncio.create_subprocess_exec("afplay", tmp_path)
                await proc.wait()
            except FileNotFoundError:
                logger.warning("No audio playback backend available.")
            finally:
                Path(tmp_path).unlink(missing_ok=True)

    async def _os_fallback_speak(self, text: str) -> None:
        """Use macOS 'say', Windows Powershell, or Linux 'espeak' as fallback."""
        import sys
        import subprocess
        if sys.platform == "darwin":
            proc = subprocess.Popen(["say", text], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif sys.platform == "win32":
            # Using PowerShell to speak the text on Windows natively without external dependencies
            escaped_text = text.replace("'", "''")
            script = f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{escaped_text}')"
            proc = subprocess.Popen(["powershell", "-Command", script], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            proc = subprocess.Popen(["espeak", text], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

