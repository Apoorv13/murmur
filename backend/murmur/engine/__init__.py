"""Speech-to-text engine abstractions and adapters."""

from murmur.engine.base import STTEngine
from murmur.engine.registry import ModelRegistry

__all__ = ["STTEngine", "ModelRegistry"]
