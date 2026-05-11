"""Tests for the Textual model switcher helpers."""

from murmur.tui.app import (
    ModelSummary,
    advance_model_index,
    build_model_summaries,
    render_model_switcher,
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
