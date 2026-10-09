"""
Audio capture module — records from the microphone using sounddevice.
Used when the Tauri frontend is not available (CLI mode).
"""

from __future__ import annotations

import asyncio
import io
import logging
import wave
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHANNELS = 1
DEFAULT_SILENCE_THRESHOLD = 0.01
DEFAULT_SILENCE_DURATION = 1.5  # seconds of silence to stop recording


class MicrophoneCapture:
    """
    Records audio from the default microphone until silence is detected.
    Returns raw PCM bytes suitable for faster-whisper.
    """

    def __init__(
        self,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        channels: int = DEFAULT_CHANNELS,
        silence_threshold: float = DEFAULT_SILENCE_THRESHOLD,
        silence_duration: float = DEFAULT_SILENCE_DURATION,
        max_duration: float = 30.0,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.max_duration = max_duration

    async def record(self) -> Optional[bytes]:
        """
        Record until silence or max_duration.
        Returns WAV-encoded bytes, or None if sounddevice is not available.
        """
        try:
            import sounddevice as sd
        except ImportError:
            logger.warning("sounddevice not installed. Microphone capture unavailable.")
            return None

        logger.info("🎙️  Listening… (speak now)")
        chunk_size = int(self.sample_rate * 0.1)  # 100ms chunks
        frames: list[np.ndarray] = []
        silent_chunks = 0
        max_silent_chunks = int(self.silence_duration / 0.1)
        max_chunks = int(self.max_duration / 0.1)

        loop = asyncio.get_event_loop()

        def _record_sync():
            nonlocal silent_chunks
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
            ) as stream:
                for _ in range(max_chunks):
                    chunk, _ = stream.read(chunk_size)
                    frames.append(chunk.copy())
                    rms = np.sqrt(np.mean(chunk ** 2))
                    if rms < self.silence_threshold:
                        silent_chunks += 1
                    else:
                        silent_chunks = 0
                    if silent_chunks >= max_silent_chunks and len(frames) > max_silent_chunks:
                        break

        await loop.run_in_executor(None, _record_sync)

        if not frames:
            return None

        # Convert to WAV bytes
        audio = np.concatenate(frames, axis=0)
        audio_int16 = (audio * 32767).astype(np.int16)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # int16 = 2 bytes
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())

        wav_bytes = buf.getvalue()
        duration = len(frames) * 0.1
        logger.info(f"Recorded {duration:.1f}s of audio ({len(wav_bytes)} bytes)")
        return wav_bytes
