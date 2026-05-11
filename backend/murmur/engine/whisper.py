"""Whisper MLX engine adapter."""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from murmur.engine.base import ModelInfo, STTEngine, TranscriptionResult


class WhisperEngine(STTEngine):
    """MLX Whisper speech-to-text engine."""

    # Map our model names to mlx-whisper model identifiers
    MODEL_MAP: dict[str, str] = {
        "tiny": "mlx-community/whisper-tiny-mlx",
        "base": "mlx-community/whisper-base-mlx",
        "small": "mlx-community/whisper-small-mlx",
        "large": "mlx-community/whisper-large-v3-turbo",
    }

    def __init__(self, model_info: ModelInfo) -> None:
        super().__init__(model_info)
        self._model_path: str | None = None

    async def load(self) -> None:
        """Load the Whisper MLX model."""
        import mlx_whisper  # noqa: F401 — validates import

        self._model_path = self.MODEL_MAP.get(self.model_info.size)
        if self._model_path is None:
            msg = f"Unknown Whisper size: {self.model_info.size}"
            raise ValueError(msg)

        # Warm up the model by running a tiny transcription
        # mlx_whisper loads lazily on first call
        self._loaded = True

    async def unload(self) -> None:
        """Unload the Whisper model from memory."""
        self._model_path = None
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
        """Transcribe audio using Whisper MLX."""
        if not self._loaded or self._model_path is None:
            msg = "Model not loaded. Call load() first."
            raise RuntimeError(msg)

        import mlx_whisper

        start = time.perf_counter()

        result = mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=self._model_path,
            language=language,
            initial_prompt=initial_prompt,
        )

        duration_ms = (time.perf_counter() - start) * 1000
        text = result.get("text", "").strip()

        return TranscriptionResult(
            text=text,
            language=language,
            duration_ms=duration_ms,
        )
