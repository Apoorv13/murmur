"""Tests for the Textual TUI helpers."""

from datetime import datetime

from murmur.tui.app import (
    ModelSummary,
    advance_model_index,
    build_model_summaries,
    render_model_switcher,
)
from murmur.tui.transcription_log import (
    TranscriptionHistory,
    render_transcription_entry,
    render_transcription_history,
)


def test_build_model_summaries_whitelists_privacy_safe_metadata() -> None:
    response = {
        "active": "whisper-base",
        "models": {
            "whisper-base": {
                "family": "whisper",
                "ram_mb": "300",
                "latency_ms": 500,
                "description": "Balanced speed and accuracy",
                "local_path": "/Users/example/private/model",
            },
            "parakeet-tdt-0.6b-v3": {
                "family": "parakeet\nhidden",
                "ram_mb": 2500,
                "latency_ms": 150,
            },
        },
    }

    summaries = build_model_summaries(response)

    assert summaries == (
        ModelSummary(
            name="parakeet-tdt-0.6b-v3",
            family="parakeet hidden",
            ram_mb=2500,
            latency_ms=150,
            active=False,
        ),
        ModelSummary(
            name="whisper-base",
            family="whisper",
            ram_mb=300,
            latency_ms=500,
            active=True,
        ),
    )

    rendered = render_model_switcher(
        summaries,
        selected_index=1,
        status_message="ready",
    ).plain
    assert "whisper-base" in rendered
    assert "whisper" in rendered
    assert "300 MB" in rendered
    assert "500 ms" in rendered
    assert "active" in rendered
    assert "Balanced speed" not in rendered
    assert "/Users/example/private" not in rendered


def test_advance_model_index_wraps_selection() -> None:
    assert advance_model_index(0, 3, 1) == 1
    assert advance_model_index(2, 3, 1) == 0
    assert advance_model_index(0, 3, -1) == 2
    assert advance_model_index(5, 0, 1) == 0


def test_transcription_history_appends_and_formats_metadata() -> None:
    history = TranscriptionHistory()
    timestamp = datetime(2024, 1, 2, 3, 4, 5)

    entry = history.append(
        " hello\nworld ",
        timestamp=timestamp,
        model="whisper-base",
        context="code editor",
        language="en",
        duration_ms=12.34,
    )

    assert history.entries == (entry,)
    rendered = render_transcription_entry(entry).plain
    assert "[03:04:05]" in rendered
    assert "model=whisper-base" in rendered
    assert "context=code editor" in rendered
    assert "lang=en" in rendered
    assert "12.3 ms" in rendered
    assert "hello world" in rendered


def test_transcription_history_appends_daemon_response() -> None:
    history = TranscriptionHistory()

    history.append_from_response(
        {
            "text": "ship it",
            "model": "parakeet-tdt-0.6b-v3",
            "context": "terminal",
            "language": "en",
            "duration_ms": "45.6",
            "speech_detected": True,
        },
    )

    rendered = render_transcription_history(history.entries).plain
    assert "ship it" in rendered
    assert "model=parakeet-tdt-0.6b-v3" in rendered
    assert "context=terminal" in rendered
    assert "45.6 ms" in rendered


def test_transcription_history_formats_no_speech_response() -> None:
    history = TranscriptionHistory()

    history.append_from_response({"text": "", "speech_detected": False})

    assert "No speech detected." in render_transcription_history(history.entries).plain


def test_transcription_history_clear_removes_entries() -> None:
    history = TranscriptionHistory()
    history.append("first")
    history.append("second")

    history.clear()

    assert history.entries == ()
    assert "No transcriptions captured" in render_transcription_history(history.entries).plain
