"""Tests for the model registry."""

import pytest

from murmur.engine.base import ModelInfo
from murmur.engine.registry import MODELS, ModelRegistry


def test_list_models_returns_all_models() -> None:
    models = ModelRegistry.list_models()
    assert len(models) >= 6
    assert "whisper-base" in models
    assert "parakeet-tdt-0.6b-v2" in models


def test_get_model_info_existing() -> None:
    info = ModelRegistry.get_model_info("whisper-base")
    assert info is not None
    assert info.family == "whisper"
    assert info.size == "base"


def test_get_model_info_nonexistent() -> None:
    info = ModelRegistry.get_model_info("nonexistent-model")
    assert info is None


def test_model_info_immutable() -> None:
    info = MODELS["whisper-base"]
    with pytest.raises(Exception):
        info.name = "hacked"  # type: ignore[misc]


@pytest.mark.asyncio
async def test_load_unknown_model() -> None:
    registry = ModelRegistry()
    with pytest.raises(ValueError, match="Unknown model"):
        await registry.load_model("nonexistent")


def test_registry_initial_state() -> None:
    registry = ModelRegistry()
    assert registry.active_model is None
    assert registry.active_engine is None
