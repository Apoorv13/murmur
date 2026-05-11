"""Model registry for managing available STT engines."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from murmur.engine.base import ModelInfo, STTEngine

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# Available models catalog
MODELS: dict[str, ModelInfo] = {
    "whisper-tiny": ModelInfo(
        name="whisper-tiny",
        family="whisper",
        size="tiny",
        language="multilingual",
        estimated_ram_mb=150,
        estimated_latency_ms=400,
        description="Fastest Whisper model, good for quick dictation",
    ),
    "whisper-base": ModelInfo(
        name="whisper-base",
        family="whisper",
        size="base",
        language="multilingual",
        estimated_ram_mb=300,
        estimated_latency_ms=500,
        description="Balanced speed and accuracy (default)",
    ),
    "whisper-small": ModelInfo(
        name="whisper-small",
        family="whisper",
        size="small",
        language="multilingual",
        estimated_ram_mb=900,
        estimated_latency_ms=800,
        description="Higher accuracy, moderate latency",
    ),
    "whisper-large-v3-turbo": ModelInfo(
        name="whisper-large-v3-turbo",
        family="whisper",
        size="large",
        language="multilingual",
        estimated_ram_mb=3000,
        estimated_latency_ms=1000,
        description="Highest accuracy Whisper model (turbo variant)",
    ),
    "parakeet-tdt-0.6b-v2": ModelInfo(
        name="parakeet-tdt-0.6b-v2",
        family="parakeet",
        size="0.6b",
        language="en",
        estimated_ram_mb=2500,
        estimated_latency_ms=130,
        description="Best accuracy (1.67% WER), English only, very fast",
    ),
    "parakeet-tdt-0.6b-v3": ModelInfo(
        name="parakeet-tdt-0.6b-v3",
        family="parakeet",
        size="0.6b",
        language="multilingual",
        estimated_ram_mb=2500,
        estimated_latency_ms=150,
        description="Multilingual Parakeet, 25 languages, high accuracy",
    ),
}


class ModelRegistry:
    """Registry for managing STT model lifecycle.

    Supports listing available models, loading/unloading engines,
    and hot-swapping between models at runtime.
    """

    def __init__(self) -> None:
        self._active_engine: STTEngine | None = None
        self._active_model_name: str | None = None

    @property
    def active_model(self) -> str | None:
        """Name of the currently loaded model, or None."""
        return self._active_model_name

    @property
    def active_engine(self) -> STTEngine | None:
        """The currently loaded engine, or None."""
        return self._active_engine

    @staticmethod
    def list_models() -> dict[str, ModelInfo]:
        """List all available models with their metadata."""
        return MODELS.copy()

    @staticmethod
    def get_model_info(name: str) -> ModelInfo | None:
        """Get metadata for a specific model."""
        return MODELS.get(name)

    async def load_model(self, name: str) -> STTEngine:
        """Load a model by name. Unloads current model if one is active.

        Args:
            name: Model name from the registry catalog

        Returns:
            The loaded STTEngine instance

        Raises:
            ValueError: If model name is not in the catalog
            RuntimeError: If engine fails to load
        """
        if name not in MODELS:
            msg = f"Unknown model: {name}. Available: {list(MODELS.keys())}"
            raise ValueError(msg)

        # Unload current model if switching
        if self._active_engine is not None:
            logger.info("Unloading current model: %s", self._active_model_name)
            await self._active_engine.unload()
            self._active_engine = None
            self._active_model_name = None

        model_info = MODELS[name]
        engine = self._create_engine(model_info)

        logger.info("Loading model: %s (RAM: ~%dMB)", name, model_info.estimated_ram_mb)
        await engine.load()

        self._active_engine = engine
        self._active_model_name = name
        logger.info("Model loaded: %s", name)
        return engine

    async def unload(self) -> None:
        """Unload the currently active model."""
        if self._active_engine is not None:
            await self._active_engine.unload()
            logger.info("Unloaded model: %s", self._active_model_name)
            self._active_engine = None
            self._active_model_name = None

    def _create_engine(self, model_info: ModelInfo) -> STTEngine:
        """Create the appropriate engine adapter for a model."""
        if model_info.family == "whisper":
            from murmur.engine.whisper import WhisperEngine

            return WhisperEngine(model_info)
        elif model_info.family == "parakeet":
            from murmur.engine.parakeet import ParakeetEngine

            return ParakeetEngine(model_info)
        else:
            msg = f"Unknown model family: {model_info.family}"
            raise ValueError(msg)
