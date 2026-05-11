"""Tests for voice activity detection."""

from __future__ import annotations

import base64
from typing import Any

import numpy as np
import pytest

from murmur.engine.base import ModelInfo, STTEngine, TranscriptionResult
from murmur.engine.registry import ModelRegistry
from murmur.server import MurmurDaemon
from murmur.vad import EnergyVoiceActivityDetector, VADConfig


def _detector() -> EnergyVoiceActivityDetector:
    return EnergyVoiceActivityDetector(
        VADConfig(
            sample_rate=1000,
            frame_duration_ms=10,
            rms_threshold=0.02,
            min_speech_duration_ms=30,
            max_silence_gap_ms=20,
            speech_pad_ms=20,
        ),
    )


def _audio_request(audio: np.ndarray, *, sample_rate: int = 1000) -> dict[str, Any]:
    return {
        "audio": base64.b64encode(audio.astype(np.float32).tobytes()).decode(),
        "sample_rate": sample_rate,
        "language": "en",
    }


def test_vad_rejects_silence() -> None:
    detector = _detector()
    audio = np.zeros(500, dtype=np.float32)

    result = detector.detect(audio, sample_rate=1000)

    assert not result.has_speech
    assert result.trimmed_audio.size == 0
    assert result.start_sample == 0
    assert result.end_sample == 0


def test_vad_detects_speech() -> None:
    detector = _detector()
    audio = np.full(200, 0.15, dtype=np.float32)

    result = detector.detect(audio, sample_rate=1000)

    assert result.has_speech
    assert result.trimmed_audio.size == audio.size
    assert result.speech_duration_ms == pytest.approx(200.0)


def test_vad_trims_leading_and_trailing_silence() -> None:
    detector = _detector()
    leading = np.zeros(100, dtype=np.float32)
    speech = np.full(200, 0.15, dtype=np.float32)
    trailing = np.zeros(100, dtype=np.float32)
    audio = np.concatenate([leading, speech, trailing])

    result = detector.detect(audio, sample_rate=1000)

    assert result.has_speech
    assert result.start_sample == 80
    assert result.end_sample == 320
    assert result.trimmed_audio.size == 240


class RecordingEngine(STTEngine):
    """STT engine test double that records audio passed to transcription."""

    def __init__(self) -> None:
        super().__init__(
            ModelInfo(
                name="test-model",
                family="test",
                size="tiny",
                language="en",
                estimated_ram_mb=1,
                estimated_latency_ms=1,
                description="test",
            ),
        )
        self._loaded = True
        self.calls: list[np.ndarray] = []

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
        self.calls.append(audio.copy())
        return TranscriptionResult(text="hello", language=language, duration_ms=12.5)


def _daemon_with_engine(engine: RecordingEngine) -> MurmurDaemon:
    daemon = MurmurDaemon()
    registry = ModelRegistry()
    registry._active_engine = engine
    registry._active_model_name = "test-model"
    daemon.registry = registry
    return daemon


@pytest.mark.asyncio
async def test_daemon_returns_empty_text_without_transcribing_silence() -> None:
    engine = RecordingEngine()
    daemon = _daemon_with_engine(engine)

    response = await daemon._cmd_transcribe(_audio_request(np.zeros(500, dtype=np.float32)))

    assert response["text"] == ""
    assert response["speech_detected"] is False
    assert engine.calls == []
    assert daemon._stats["transcriptions"] == 0


@pytest.mark.asyncio
async def test_daemon_trims_silence_before_transcribing() -> None:
    engine = RecordingEngine()
    daemon = _daemon_with_engine(engine)
    audio = np.concatenate(
        [
            np.zeros(500, dtype=np.float32),
            np.full(300, 0.15, dtype=np.float32),
            np.zeros(500, dtype=np.float32),
        ],
    )

    response = await daemon._cmd_transcribe(_audio_request(audio))

    assert response["text"] == "hello"
    assert response["speech_detected"] is True
    assert len(engine.calls) == 1
    assert engine.calls[0].size < audio.size
    assert response["vad"]["start_sample"] > 0
    assert response["vad"]["end_sample"] < audio.size
