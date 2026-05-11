"""Abstract base class for speech-to-text engines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class ModelInfo:
    """Metadata about a speech-to-text model."""

    name: str
    family: str  # "whisper" or "parakeet"
    size: str  # "tiny", "base", "small", "medium", "large", "0.6b"
    language: str  # "en", "multilingual"
    estimated_ram_mb: int
    estimated_latency_ms: int
    description: str


@dataclass
class TranscriptionResult:
    """Result from a transcription operation."""

    text: str
    language: str
    duration_ms: float
    confidence: float | None = None


class STTEngine(ABC):
    """Abstract base class for speech-to-text engines.

    All engines must implement load, unload, and transcribe.
    Hot-swapping is supported: unload current engine, load new one.
    """

    def __init__(self, model_info: ModelInfo) -> None:
        self.model_info = model_info
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @abstractmethod
    async def load(self) -> None:
        """Load the model into memory. Must be called before transcribe."""
        ...

    @abstractmethod
    async def unload(self) -> None:
        """Unload the model from memory, freeing resources."""
        ...

    @abstractmethod
    async def transcribe(
        self,
        audio: np.ndarray,
        *,
        sample_rate: int = 16000,
        language: str = "en",
        initial_prompt: str | None = None,
        **kwargs: Any,
    ) -> TranscriptionResult:
        """Transcribe audio buffer to text.

        Args:
            audio: Audio samples as float32 numpy array (mono, normalized -1 to 1)
            sample_rate: Sample rate of the audio (default 16kHz)
            language: Language code for transcription
            initial_prompt: Optional context prompt to guide transcription

        Returns:
            TranscriptionResult with transcribed text and metadata
        """
        ...
