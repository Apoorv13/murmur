"""Tests for TUI stats formatting helpers."""

from murmur.tui.stats import format_count, format_latency_ms, format_uptime, render_stats


def test_format_uptime_uses_compact_units() -> None:
    assert format_uptime(None) == "n/a"
    assert format_uptime(0) == "0s"
    assert format_uptime(65) == "1m 5s"
    assert format_uptime(3_725) == "1h 2m 5s"
    assert format_uptime(176_461) == "2d 1h 1m"


def test_format_latency_ms_uses_milliseconds_and_seconds() -> None:
    assert format_latency_ms(None) == "n/a"
    assert format_latency_ms(0) == "n/a"
    assert format_latency_ms(42) == "42.0 ms"
    assert format_latency_ms(1_250) == "1.25 s"


def test_format_count_rejects_invalid_values() -> None:
    assert format_count(None) == "0"
    assert format_count(-1) == "0"
    assert format_count(12_345) == "12,345"


def test_render_stats_includes_daemon_fields() -> None:
    status = {
        "status": "running",
        "model": "whisper-base",
        "model_loaded": True,
        "transcriptions": 1_234,
        "avg_latency_ms": 87.6,
        "uptime_seconds": 125,
    }

    rendered = render_stats(status).plain

    assert "Connection: running" in rendered
    assert "Active model: whisper-base" in rendered
    assert "Loaded: yes" in rendered
    assert "Average latency: 87.6 ms" in rendered
    assert "Transcriptions: 1,234" in rendered
    assert "Uptime: 2m 5s" in rendered


def test_render_stats_marks_cached_data_stale() -> None:
    status = {
        "status": "running",
        "model": "parakeet-tdt-0.6b-v2",
        "model_loaded": False,
        "transcriptions": 2,
        "avg_latency_ms": 1_500,
        "uptime_seconds": 3_600,
    }

    rendered = render_stats(
        status,
        unavailable_message="Could not connect",
        age_seconds=10,
    ).plain

    assert "Connection: stale (10s old)" in rendered
    assert "Last error: Could not connect" in rendered
    assert "Active model: parakeet-tdt-0.6b-v2" in rendered
    assert "Loaded: no" in rendered
    assert "Average latency: 1.50 s" in rendered


def test_render_stats_handles_unavailable_daemon_without_cache() -> None:
    rendered = render_stats(None, unavailable_message="socket missing").plain

    assert "Daemon unavailable" in rendered
    assert "socket missing" in rendered
