"""Formatting helpers for the TUI stats panel."""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

from rich.text import Text


def format_uptime(seconds: object) -> str:
    """Format uptime seconds as a compact duration."""
    value = _non_negative_number(seconds)
    if value is None:
        return "n/a"

    total_seconds = int(round(value))
    days, remainder = divmod(total_seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes, seconds = divmod(remainder, 60)

    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def format_latency_ms(milliseconds: object) -> str:
    """Format daemon latency in milliseconds."""
    value = _non_negative_number(milliseconds)
    if value is None or value == 0:
        return "n/a"
    if value >= 1_000:
        return f"{value / 1_000:.2f} s"
    return f"{value:.1f} ms"


def format_count(value: object) -> str:
    """Format a non-negative count."""
    number = _non_negative_number(value)
    if number is None:
        return "0"
    return f"{int(number):,}"


def render_stats(
    status: Mapping[str, Any] | None,
    *,
    unavailable_message: str | None = None,
    age_seconds: float | None = None,
) -> Text:
    """Render daemon stats with unavailable/stale states."""
    if not status:
        text = Text("Stats panel\n", style="bold")
        text.append("Daemon unavailable", style="bold red")
        if unavailable_message:
            text.append(f"\n{unavailable_message}", style="yellow")
        return text

    text = Text("Stats panel\n", style="bold")
    if unavailable_message:
        text.append("Connection: stale", style="bold yellow")
        if age_seconds is not None:
            text.append(f" ({format_uptime(age_seconds)} old)", style="yellow")
        text.append("\n")
        text.append(f"Last error: {unavailable_message}\n", style="yellow")
    else:
        daemon_status = _display_value(status.get("status"), default="unknown")
        text.append(f"Connection: {daemon_status}\n", style="green")

    text.append(f"Active model: {_display_value(status.get('model'), default='none')}\n")
    text.append(f"Loaded: {_format_loaded(status.get('model_loaded'))}\n")
    text.append(f"Average latency: {format_latency_ms(status.get('avg_latency_ms'))}\n")
    text.append(f"Transcriptions: {format_count(status.get('transcriptions'))}\n")
    text.append(f"Uptime: {format_uptime(status.get('uptime_seconds'))}")
    return text


def _format_loaded(value: object) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    return "unknown"


def _display_value(value: object, *, default: str) -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value if value else default
    return str(value)


def _non_negative_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value)
        except ValueError:
            return None
    else:
        return None

    if not isfinite(number) or number < 0:
        return None
    return number
