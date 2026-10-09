"""
Base provider abstractions for STT, LLM, and TTS.
All concrete implementations must implement these interfaces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Optional


@dataclass
class TranscriptionResult:
    text: str
    language: str
    confidence: float


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int


class STTProvider(ABC):
    """Abstract Speech-to-Text provider."""

    @abstractmethod
    async def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> TranscriptionResult:
        """Transcribe raw audio bytes to text."""
        ...

    @abstractmethod
    async def transcribe_file(self, path: str) -> TranscriptionResult:
        """Transcribe an audio file to text."""
        ...


class LLMProvider(ABC):
    """Abstract Large Language Model provider."""

    @abstractmethod
    async def complete(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        """Generate a completion from a prompt."""
        ...

    @abstractmethod
    async def stream(self, prompt: str, system: Optional[str] = None) -> AsyncIterator[str]:
        """Stream a completion token by token."""
        ...


class TTSProvider(ABC):
    """Abstract Text-to-Speech provider."""

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Convert text to audio bytes (WAV/PCM)."""
        ...

    @abstractmethod
    async def speak(self, text: str) -> None:
        """Synthesize and immediately play audio."""
        ...


class MockSTTProvider(STTProvider):
    def __init__(self, default_text: str = "Create hello.py on Desktop"):
        self.default_text = default_text

    async def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> TranscriptionResult:
        return TranscriptionResult(text=self.default_text, language="en", confidence=0.99)

    async def transcribe_file(self, path: str) -> TranscriptionResult:
        return TranscriptionResult(text=self.default_text, language="en", confidence=0.99)


class MockLLMProvider(LLMProvider):
    def __init__(self, response_text: str = ""):
        self.response_text = response_text or '{"task":"Mock Task","steps":[{"action":"open_application","application":"Calculator"}]}'

    async def complete(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        return LLMResponse(content=self.response_text, model="mock-qwen3", tokens_used=42)

    async def stream(self, prompt: str, system: Optional[str] = None) -> AsyncIterator[str]:
        yield self.response_text


class MockTTSProvider(TTSProvider):
    async def synthesize(self, text: str) -> bytes:
        return b"MOCK_WAV_HEADER_DATA"

    async def speak(self, text: str) -> None:
        pass

