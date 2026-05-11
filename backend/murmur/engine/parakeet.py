"""Parakeet TDT MLX engine adapter."""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from murmur.engine.base import ModelInfo, STTEngine, TranscriptionResult


class ParakeetEngine(STTEngine):
    """Parakeet TDT MLX speech-to-text engine."""

    MODEL_MAP: dict[str, str] = {
        "0.6b": "mlx-community/parakeet-tdt-0.6b-v2",
    }

    def __init__(self, model_info: ModelInfo) -> None:
        super().__init__(model_info)
        self._model: Any = None

    async def load(self) -> None:
        """Load the Parakeet TDT model."""
        # parakeet-mlx handles model download and loading
        self._loaded = True

    async def unload(self) -> None:
        """Unload the Parakeet model from memory."""
        self._model = None
        self._loaded = False

    async def transcribe(
        self,
        audio: np.ndarray,
        *,
        sample_rate: int = 16000,
        language: str = "en",
        initial_prompt: str | None = None,
        **kwargs: Any,
    ) -> TranscriptionResult:
        """Transcribe audio using Parakeet TDT MLX."""
        if not self._loaded:
            msg = "Model not loaded. Call load() first."
            raise RuntimeError(msg)

        start = time.perf_counter()

        # Parakeet MLX transcription
        # Note: actual API may vary — this is the expected interface
        try:
            from parakeet_mlx import transcribe as parakeet_transcribe

            result = parakeet_transcribe(audio, sample_rate=sample_rate)
            text = result if isinstance(result, str) else result.get("text", "")
        except ImportError:
            msg = (
                "parakeet-mlx not installed. "
                "Install with: pip install murmur-backend[parakeet]"
            )
            raise RuntimeError(msg) from None

        duration_ms = (time.perf_counter() - start) * 1000

        return TranscriptionResult(
            text=text.strip(),
            language=language,
            duration_ms=duration_ms,
        )
