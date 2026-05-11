"""Local voice activity detection for trimming silent audio."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class VADConfig:
    """Configuration for energy-based voice activity detection."""

    sample_rate: int = 16000
    frame_duration_ms: int = 30
    rms_threshold: float = 0.01
    adaptive_noise_multiplier: float = 3.0
    min_speech_duration_ms: int = 120
    max_silence_gap_ms: int = 150
    speech_pad_ms: int = 100


@dataclass(frozen=True)
class VADResult:
    """Result of a VAD pass over an audio buffer."""

    has_speech: bool
    trimmed_audio: np.ndarray
    start_sample: int
    end_sample: int
    speech_duration_ms: float
    original_duration_ms: float


class EnergyVoiceActivityDetector:
    """Energy/RMS-based VAD with adaptive noise-floor handling."""

    def __init__(self, config: VADConfig | None = None) -> None:
        self.config = config or VADConfig()

    def detect(self, audio: np.ndarray, *, sample_rate: int | None = None) -> VADResult:
        """Detect speech and trim leading/trailing silence from a mono audio buffer."""
        rate = sample_rate or self.config.sample_rate
        samples = np.asarray(audio, dtype=np.float32).flatten()
        original_duration_ms = self._samples_to_ms(samples.size, rate)

        if samples.size == 0:
            return self._empty_result(original_duration_ms)

        frame_size = max(1, int(rate * self.config.frame_duration_ms / 1000))
        rms = self._frame_rms(samples, frame_size)
        if rms.size == 0:
            return self._empty_result(original_duration_ms)

        threshold = self._speech_threshold(rms)
        speech_frames = rms >= threshold
        spans = self._speech_spans(speech_frames)

        if not spans:
            return self._empty_result(original_duration_ms)

        pad_samples = int(rate * self.config.speech_pad_ms / 1000)
        start_frame = spans[0][0]
        end_frame = spans[-1][1]
        start_sample = max(0, (start_frame * frame_size) - pad_samples)
        end_sample = min(samples.size, ((end_frame + 1) * frame_size) + pad_samples)
        trimmed_audio = samples[start_sample:end_sample].astype(np.float32, copy=True)
        speech_duration_ms = self._samples_to_ms(end_sample - start_sample, rate)

        return VADResult(
            has_speech=True,
            trimmed_audio=trimmed_audio,
            start_sample=start_sample,
            end_sample=end_sample,
            speech_duration_ms=speech_duration_ms,
            original_duration_ms=original_duration_ms,
        )

    def _empty_result(self, original_duration_ms: float) -> VADResult:
        return VADResult(
            has_speech=False,
            trimmed_audio=np.array([], dtype=np.float32),
            start_sample=0,
            end_sample=0,
            speech_duration_ms=0.0,
            original_duration_ms=original_duration_ms,
        )

    def _speech_threshold(self, rms: np.ndarray) -> float:
        noise_floor = float(np.percentile(rms, 10))
        speech_level = float(np.percentile(rms, 90))
        if speech_level <= noise_floor * self.config.adaptive_noise_multiplier:
            return self.config.rms_threshold
        adaptive_threshold = noise_floor * self.config.adaptive_noise_multiplier
        return max(self.config.rms_threshold, adaptive_threshold)

    def _speech_spans(self, speech_frames: np.ndarray) -> list[tuple[int, int]]:
        raw_spans = self._contiguous_spans(speech_frames)
        if not raw_spans:
            return []

        max_gap_frames = self._duration_to_frames(self.config.max_silence_gap_ms)
        merged: list[tuple[int, int]] = []
        for start, end in raw_spans:
            if merged and start - merged[-1][1] - 1 <= max_gap_frames:
                merged[-1] = (merged[-1][0], end)
            else:
                merged.append((start, end))

        min_speech_frames = self._duration_to_frames(self.config.min_speech_duration_ms)
        return [(start, end) for start, end in merged if end - start + 1 >= min_speech_frames]

    @staticmethod
    def _frame_rms(samples: np.ndarray, frame_size: int) -> np.ndarray:
        frame_count = int(np.ceil(samples.size / frame_size))
        values = np.empty(frame_count, dtype=np.float32)
        for index in range(frame_count):
            frame = samples[index * frame_size : (index + 1) * frame_size]
            values[index] = np.sqrt(np.mean(np.square(frame), dtype=np.float64))
        return values

    @staticmethod
    def _contiguous_spans(mask: np.ndarray) -> list[tuple[int, int]]:
        spans: list[tuple[int, int]] = []
        start: int | None = None
        for index, is_speech in enumerate(mask):
            if bool(is_speech) and start is None:
                start = index
            elif not bool(is_speech) and start is not None:
                spans.append((start, index - 1))
                start = None
        if start is not None:
            spans.append((start, mask.size - 1))
        return spans

    def _duration_to_frames(self, duration_ms: int) -> int:
        return int(np.ceil(duration_ms / self.config.frame_duration_ms))

    @staticmethod
    def _samples_to_ms(sample_count: int, sample_rate: int) -> float:
        return (sample_count / sample_rate) * 1000
