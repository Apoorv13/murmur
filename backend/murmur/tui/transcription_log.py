"""In-memory transcription history helpers for the TUI."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from rich.text import Text

DEFAULT_MAX_TRANSCRIPTION_LOG_ENTRIES = 200
_MAX_LABEL_LENGTH = 64
_MAX_TEXT_LENGTH = 500


@dataclass(frozen=True)
class TranscriptionLogEntry:
    """Single transcription captured during the current TUI session."""

    timestamp: datetime
    text: str
    model: str | None = None
    context: str | None = None
    language: str | None = None
    duration_ms: float | None = None


class TranscriptionHistory:
    """Bounded, in-memory transcription history with no disk persistence."""

    def __init__(
        self,
        *,
        max_entries: int = DEFAULT_MAX_TRANSCRIPTION_LOG_ENTRIES,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if max_entries <= 0:
            msg = "max_entries must be greater than zero"
            raise ValueError(msg)

        self._entries: deque[TranscriptionLogEntry] = deque(maxlen=max_entries)
        self._clock = clock or datetime.now

    @property
    def entries(self) -> tuple[TranscriptionLogEntry, ...]:
        """Return entries from oldest to newest."""
        return tuple(self._entries)

    def append(
        self,
        text: str,
        *,
        timestamp: datetime | None = None,
        model: str | None = None,
        context: str | None = None,
        language: str | None = None,
        duration_ms: float | None = None,
    ) -> TranscriptionLogEntry:
        """Append a transcription entry and return the stored value."""
        entry = TranscriptionLogEntry(
            timestamp=timestamp or self._clock(),
            text=_normalize_text(text, fallback="Transcript text unavailable."),
            model=_optional_label(model),
            context=_optional_label(context),
            language=_optional_label(language),
            duration_ms=duration_ms if duration_ms is None or duration_ms >= 0 else None,
        )
        self._entries.append(entry)
        return entry

    def append_from_response(
        self,
        response: Mapping[str, Any],
        *,
        timestamp: datetime | None = None,
    ) -> TranscriptionLogEntry:
        """Append a transcription entry from a daemon-style response payload."""
        raw_text = response.get("text")
        speech_detected = response.get("speech_detected")
        fallback = (
            "No speech detected."
            if speech_detected is False
            else "Transcript text unavailable from daemon."
        )
        text = raw_text if isinstance(raw_text, str) and raw_text.split() else fallback

        return self.append(
            text,
            timestamp=timestamp,
            model=_optional_label(response.get("model")),
            context=_optional_label(response.get("context")),
            language=_optional_label(response.get("language")),
            duration_ms=_coerce_float(response.get("duration_ms")),
        )

    def clear(self) -> None:
        """Clear all entries captured by this TUI session."""
        self._entries.clear()


def render_transcription_history(entries: Sequence[TranscriptionLogEntry]) -> Text:
    """Render transcription history entries for the scrollable log panel."""
    rendered = Text("Transcription history\n", style="bold")
    rendered.append("In-memory only · c clears this panel\n", style="dim")

    if not entries:
        rendered.append("\nNo transcriptions captured in this TUI session.\n", style="dim")
        rendered.append(
            "Daemon history is not exposed yet; new daemon activity is shown as a local notice.",
            style="dim",
        )
        return rendered

    for entry in entries:
        rendered.append("\n")
        rendered.append(render_transcription_entry(entry))

    return rendered


def render_transcription_entry(entry: TranscriptionLogEntry) -> Text:
    """Render one transcription log entry with timestamp and optional metadata."""
    rendered = Text(f"[{entry.timestamp:%H:%M:%S}] ", style="bold cyan")
    metadata = _format_metadata(entry)
    if metadata:
        rendered.append(metadata, style="dim")
        rendered.append("\n")
    rendered.append(entry.text)
    return rendered


def _format_metadata(entry: TranscriptionLogEntry) -> str:
    fields: list[str] = []
    if entry.model:
        fields.append(f"model={entry.model}")
    if entry.context:
        fields.append(f"context={entry.context}")
    if entry.language:
        fields.append(f"lang={entry.language}")
    if entry.duration_ms is not None:
        fields.append(f"{entry.duration_ms:.1f} ms")
    return " · ".join(fields)


def _normalize_text(value: str, *, fallback: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        return fallback
    return _clip(normalized, _MAX_TEXT_LENGTH)


def _optional_label(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split())
    if not normalized:
        return None
    return _clip(normalized, _MAX_LABEL_LENGTH)


def _coerce_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value) if value >= 0 else None
    if isinstance(value, str):
        try:
            parsed = float(value)
        except ValueError:
            return None
        return parsed if parsed >= 0 else None
    return None


def _clip(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 1]}…"
