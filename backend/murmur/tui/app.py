"""Textual dashboard scaffold for Murmur."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from murmur.tui.ipc import DaemonIPCError, DaemonUnavailableError, MurmurIPCClient


class MurmurControlPanel(App[None]):
    """Murmur daemon control panel."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #dashboard {
        height: 1fr;
        padding: 1;
    }

    .column {
        width: 1fr;
        height: 1fr;
    }

    .panel {
        border: round $accent;
        padding: 1 2;
        margin: 0 1 1 0;
        height: 1fr;
    }

    #log-panel {
        height: 8;
    }
    """

    BINDINGS = [("r", "refresh_dashboard", "Refresh"), ("q", "quit", "Quit")]

    def __init__(self, client: MurmurIPCClient | None = None) -> None:
        super().__init__()
        self.client = client or MurmurIPCClient()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="dashboard"):
            with Horizontal():
                yield Static("Model panel placeholder", id="model-panel", classes="panel column")
                yield Static("Stats panel placeholder", id="stats-panel", classes="panel column")
            yield Static("Log panel placeholder", id="log-panel", classes="panel")
        yield Footer()

    async def on_mount(self) -> None:
        await self.refresh_dashboard()
        self.set_interval(5.0, self.refresh_dashboard)

    async def action_refresh_dashboard(self) -> None:
        await self.refresh_dashboard()

    async def refresh_dashboard(self) -> None:
        model_panel = self.query_one("#model-panel", Static)
        stats_panel = self.query_one("#stats-panel", Static)
        log_panel = self.query_one("#log-panel", Static)

        try:
            status = await self.client.status()
            models = await self.client.list_models()
        except DaemonUnavailableError as exc:
            model_panel.update(Text("Model panel\nNo daemon connection", style="bold red"))
            stats_panel.update(Text("Stats panel\nDaemon unavailable", style="bold red"))
            log_panel.update(Text(str(exc), style="yellow"))
            return
        except DaemonIPCError as exc:
            model_panel.update(Text("Model panel\nUnable to read daemon state", style="bold red"))
            stats_panel.update(Text("Stats panel\nIPC error", style="bold red"))
            log_panel.update(Text(str(exc), style="yellow"))
            return

        model_panel.update(self._render_models(models))
        stats_panel.update(self._render_stats(status))
        log_panel.update(Text("Connected to Murmur daemon", style="green"))

    def _render_models(self, models: Mapping[str, Any]) -> Text:
        active = models.get("active") or "None"
        model_map = _as_mapping(models.get("models"))
        text = Text("Model panel\n", style="bold")
        text.append(f"Active: {active}\n")
        text.append(f"Available models: {len(model_map)}\n\n")
        for name in sorted(model_map)[:8]:
            prefix = "• " if name != active else "▶ "
            text.append(f"{prefix}{name}\n")
        if len(model_map) > 8:
            text.append(f"…and {len(model_map) - 8} more")
        return text

    def _render_stats(self, status: Mapping[str, Any]) -> Text:
        text = Text("Stats panel\n", style="bold")
        text.append(f"Status: {status.get('status', 'unknown')}\n")
        text.append(f"Model loaded: {status.get('model_loaded', False)}\n")
        text.append(f"Transcriptions: {status.get('transcriptions', 0)}\n")
        text.append(f"Average latency: {status.get('avg_latency_ms', 0)} ms\n")
        text.append(f"Uptime: {status.get('uptime_seconds', 0)} s")
        return text


def _as_mapping(value: object) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def main() -> None:
    """Run the murmur-tui entry point."""
    MurmurControlPanel().run()


if __name__ == "__main__":
    main()
