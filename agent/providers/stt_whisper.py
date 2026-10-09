"""
faster-whisper based local Speech-to-Text provider.
Falls back to simulated transcription if the model is not installed.
"""

from __future__ import annotations

import io
import logging
import tempfile
from pathlib import Path
from typing import Optional

try:
    import numpy as np
except ImportError:
    np = None

from agent.providers.base import STTProvider, TranscriptionResult

logger = logging.getLogger(__name__)


class WhisperSTTProvider(STTProvider):
    """
    Local STT using faster-whisper.
    Model sizes: tiny, base, small, medium, large-v3
    Default: 'base' for CPU-only systems.
    """

    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Loading Whisper model '{self.model_size}' on {self.device}...")
            self._model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
            logger.info("Whisper model loaded successfully.")
        except ImportError:
            logger.warning("faster-whisper not installed. Using simulated STT.")
            self._model = "SIMULATED"

    async def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> TranscriptionResult:
        self._load_model()

        if self._model == "SIMULATED":
            return TranscriptionResult(
                text="[SIMULATED] Create a folder named demo on the desktop.",
                language="en",
                confidence=0.99,
            )

        # Write audio bytes to a temp file and transcribe
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        try:
            segments, info = self._model.transcribe(tmp_path, beam_size=5, language="en")
            text = " ".join(seg.text for seg in segments).strip()
            return TranscriptionResult(
                text=text,
                language=info.language,
                confidence=info.language_probability,
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def transcribe_file(self, path: str) -> TranscriptionResult:
        self._load_model()

        if self._model == "SIMULATED":
            return TranscriptionResult(text="[SIMULATED TRANSCRIPTION]", language="en", confidence=0.99)

        segments, info = self._model.transcribe(path, beam_size=5)
        text = " ".join(seg.text for seg in segments).strip()
        return TranscriptionResult(text=text, language=info.language, confidence=info.language_probability)
