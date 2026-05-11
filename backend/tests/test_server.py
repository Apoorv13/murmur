"""Tests for daemon resource management."""

from __future__ import annotations

import asyncio
import base64
import json
import struct
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

from murmur.engine.base import ModelInfo, STTEngine, TranscriptionResult
from murmur.engine.registry import MODELS, ModelRegistry
from murmur.server import MAX_MESSAGE_BYTES, MurmurDaemon


class FakeEngine(STTEngine):
    """In-memory test engine that avoids loading real ML models."""

    def __init__(self, model_info: ModelInfo) -> None:
        super().__init__(model_info)
        self.initial_prompts: list[str | None] = []

    async def load(self) -> None:
        self._loaded = True

    async def unload(self) -> None:
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
        self.initial_prompts.append(initial_prompt)
        return TranscriptionResult(text="hello world", language=language, duration_ms=12.3)


class FakeRegistry:
    def __init__(self) -> None:
        self._active_engine: FakeEngine | None = None
        self._active_model_name: str | None = None
        self.loaded_models: list[str] = []

    @property
    def active_model(self) -> str | None:
        return self._active_model_name

    @property
    def active_engine(self) -> FakeEngine | None:
        return self._active_engine

    async def load_model(self, name: str) -> STTEngine:
        if self._active_engine is not None:
            await self._active_engine.unload()

        engine = FakeEngine(MODELS[name])
        await engine.load()
        self._active_engine = engine
        self._active_model_name = name
        self.loaded_models.append(name)
        return engine

    async def unload(self) -> None:
        if self._active_engine is not None:
            await self._active_engine.unload()
            self._active_engine = None
            self._active_model_name = None


class OversizedMessageReader:
    def __init__(self) -> None:
        self.read_calls: list[int] = []

    async def readexactly(self, size: int) -> bytes:
        self.read_calls.append(size)
        if size == 4:
            return struct.pack(">I", MAX_MESSAGE_BYTES + 1)
        msg = "Oversized message body should not be read"
        raise AssertionError(msg)


class CapturingWriter:
    def __init__(self) -> None:
        self.buffer = bytearray()
        self.closed = False

    def write(self, data: bytes) -> None:
        self.buffer.extend(data)

    async def drain(self) -> None:
        return

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        return


def _daemon_with_fake_registry(
    tmp_path: Path,
    idle_timeout_seconds: float,
) -> tuple[MurmurDaemon, FakeRegistry]:
    daemon = MurmurDaemon(
        socket_path=tmp_path / "murmur.sock",
        idle_timeout_seconds=idle_timeout_seconds,
    )
    registry = FakeRegistry()
    daemon.registry = cast(ModelRegistry, registry)
    return daemon, registry


@pytest.mark.asyncio
async def test_idle_timeout_unloads_model_but_keeps_selected_model(tmp_path: Path) -> None:
    daemon, registry = _daemon_with_fake_registry(tmp_path, idle_timeout_seconds=0.01)
    await registry.load_model("whisper-small")
    daemon.default_model = "whisper-base"
    daemon._selected_model = "whisper-small"

    daemon._mark_activity()
    await asyncio.sleep(0.05)

    assert registry.active_engine is None
    assert registry.active_model is None
    status = await daemon._cmd_status({})
    assert status["active_model"] == "whisper-small"
    assert status["default_model"] == "whisper-base"
    assert status["model_loaded"] is False


@pytest.mark.asyncio
async def test_transcribe_reloads_last_selected_model_after_idle_unload(tmp_path: Path) -> None:
    daemon, registry = _daemon_with_fake_registry(tmp_path, idle_timeout_seconds=10.0)
    daemon.default_model = "whisper-base"
    daemon._selected_model = "whisper-small"
    audio = np.full(4000, 0.1, dtype=np.float32)
    audio_b64 = base64.b64encode(audio.tobytes()).decode()

    response = await daemon._cmd_transcribe(
        {"audio": audio_b64, "bundle_id": "com.microsoft.VSCode", "app_name": "Visual Studio Code"},
    )

    assert response["text"] == "hello world"
    assert response["model"] == "whisper-small"
    assert registry.loaded_models == ["whisper-small"]
    active_engine = registry.active_engine
    assert active_engine is not None
    assert active_engine.initial_prompts
    initial_prompt = active_engine.initial_prompts[0]
    assert initial_prompt is not None
    assert "Local dictation guidance" in initial_prompt
    assert "Active app category: code" in initial_prompt
    assert "workspace" in initial_prompt
    assert "Indian English" in initial_prompt
    status = await daemon._cmd_status({})
    assert status["active_model"] == "whisper-small"
    assert status["loaded_model"] == "whisper-small"
    assert status["model_loaded"] is True
    assert status["next_idle_unload_seconds"] is not None
    daemon._cancel_idle_unload()


@pytest.mark.asyncio
async def test_zero_idle_timeout_disables_auto_unload(tmp_path: Path) -> None:
    daemon, registry = _daemon_with_fake_registry(tmp_path, idle_timeout_seconds=0.0)
    await registry.load_model("whisper-base")
    daemon._selected_model = "whisper-base"

    daemon._mark_activity()
    await asyncio.sleep(0.02)

    assert registry.active_engine is not None
    assert daemon._next_idle_unload_seconds() is None


@pytest.mark.asyncio
async def test_oversized_socket_message_is_rejected_before_body_read(tmp_path: Path) -> None:
    daemon = MurmurDaemon(socket_path=tmp_path / "murmur.sock")
    reader = OversizedMessageReader()
    writer = CapturingWriter()

    await daemon._handle_client(
        cast(asyncio.StreamReader, reader),
        cast(asyncio.StreamWriter, writer),
    )

    assert reader.read_calls == [4]
    assert writer.closed is True
    response_length = struct.unpack(">I", writer.buffer[:4])[0]
    response = json.loads(writer.buffer[4 : 4 + response_length].decode())
    assert "Message too large" in response["error"]
