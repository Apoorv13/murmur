"""Audio capture and voice activity detection."""

from __future__ import annotations

import numpy as np
import sounddevice as sd


class AudioCapture:
    """Captures audio from the default microphone."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self._buffer: list[np.ndarray] = []
        self._recording = False

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self) -> None:
        """Start recording audio from the microphone."""
        self._buffer = []
        self._recording = True
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        """Stop recording and return the captured audio buffer.

        Returns:
            Mono float32 numpy array, normalized to [-1, 1]
        """
        self._recording = False
        self._stream.stop()
        self._stream.close()

        if not self._buffer:
            return np.array([], dtype=np.float32)

        audio = np.concatenate(self._buffer, axis=0).flatten()
        self._buffer = []
        return audio

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        """Callback for sounddevice stream — accumulates audio chunks."""
        if self._recording:
            self._buffer.append(indata.copy())
