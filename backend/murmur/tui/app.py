"""Textual dashboard for Murmur."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from time import monotonic
from typing import Any

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from murmur.tui.ipc import DaemonIPCError, DaemonUnavailableError, MurmurIPCClient
from murmur.tui.stats import render_stats

_REFRESH_INTERVAL_SECONDS = 5.0


@dataclass(frozen=True)
class ModelSummary:
    """Privacy-safe model metadata shown in the TUI."""

    name: str
    family: str
    ram_mb: int | None
    latency_ms: int | None
    active: bool


def build_model_summaries(response: Mapping[str, Any]) -> tuple[ModelSummary, ...]:
    """Extract whitelisted model metadata from a list-models response."""
    active_value = response.get("active")
    active_model = active_value if isinstance(active_value, str) else None
    models = _as_mapping(response.get("models"))

    summaries: list[ModelSummary] = []
    for raw_name, raw_info in models.items():
        info = _as_mapping(raw_info)
        name = _safe_label(raw_name, fallback="unknown-model")
        family = _safe_label(info.get("family"), fallback="unknown")
        summaries.append(
            ModelSummary(
                name=name,
                family=family,
                ram_mb=_coerce_int(info.get("ram_mb")),
                latency_ms=_coerce_int(info.get("latency_ms")),
                active=name == active_model,
            ),
        )

    return tuple(sorted(summaries, key=lambda model: model.name))


def advance_model_index(current: int, model_count: int, delta: int) -> int:
    """Return the next selectable model index, wrapping around the model list."""
    if model_count <= 0:
        return 0
    return (current + delta) % model_count


def render_model_switcher(
    models: Sequence[ModelSummary],
    *,
    selected_index: int,
    status_message: str,
    status_style: str = "dim",
) -> Text:
    """Render the model switcher panel."""
    text = Text("Model switcher\n", style="bold")
    text.append("↑/↓ or j/k select · s switch · r refresh\n", style="dim")
    if status_message:
        text.append(status_message, style=status_style)
        text.append("\n")

    if not models:
        text.append("\nNo models available from daemon.", style="yellow")
        return text

    active_name = next((model.name for model in models if model.active), "None")
    text.append(f"Active: {active_name}\n\n")
    text.append(
        f"{'':1} {'Model':28} {'Family':10} {'RAM':>8} {'Latency':>9} State\n",
        style="bold",
    )

    for index, model in enumerate(models):
        selected = index == selected_index
        marker = "›" if selected else " "
        state = "active" if model.active else "available"
        style = "reverse" if selected else "green" if model.active else ""
        text.append(
            f"{marker} {_clip(model.name, 28):28} "
            f"{_clip(model.family, 10):10} "
            f"{_format_mb(model.ram_mb):>8} "
            f"{_format_latency(model.latency_ms):>9} "
            f"{state}\n",
            style=style,
        )

    return text


class ModelSwitcherPanel(Static):
    """Model list and selection state for switching daemon models."""

    def __init__(self) -> None:
        super().__init__("Model switcher", id="model-panel", classes="panel column")
        self.models: tuple[ModelSummary, ...] = ()
        self.selected_index = 0
        self.pending_model: str | None = None
        self.status_message = "Waiting for daemon state…"
        self.status_style = "dim"

    @property
    def selected_model(self) -> str | None:
        if not self.models:
            return None
        return self.models[self.selected_index].name

    def update_models(self, response: Mapping[str, Any]) -> None:
        selected_model = self.selected_model
        self.models = build_model_summaries(response)
        self.selected_index = self._preferred_index(selected_model)
        self.pending_model = None
        self.status_message = f"Loaded {len(self.models)} model option(s)."
        self.status_style = "green"
        self.refresh_view()

    def set_unavailable(self) -> None:
        self.models = ()
        self.selected_index = 0
        self.pending_model = None
        self.status_message = "Daemon unavailable. Start murmur-daemon, then refresh."
        self.status_style = "bold red"
        self.refresh_view()

    def set_error(self, message: str) -> None:
        self.status_message = message
        self.status_style = "bold red"
        self.refresh_view()

    def select_next(self) -> None:
        self._move_selection(1)

    def select_previous(self) -> None:
        self._move_selection(-1)

    def request_confirmation(self, model: str) -> None:
        self.pending_model = model
        self.status_message = f"Press s again to switch to {model}."
        self.status_style = "yellow"
        self.refresh_view()

    def switch_succeeded(self, model: str) -> None:
        self.models = tuple(
            ModelSummary(
                name=item.name,
                family=item.family,
                ram_mb=item.ram_mb,
                latency_ms=item.latency_ms,
                active=item.name == model,
            )
            for item in self.models
        )
        self.pending_model = None
        self.status_message = f"Switched active model to {model}."
        self.status_style = "green"
        self.selected_index = self._preferred_index(model)
        self.refresh_view()

    def refresh_view(self) -> None:
        self.update(
            render_model_switcher(
                self.models,
                selected_index=self.selected_index,
                status_message=self.status_message,
                status_style=self.status_style,
            ),
        )

    def _move_selection(self, delta: int) -> None:
        if not self.models:
            return
        self.selected_index = advance_model_index(self.selected_index, len(self.models), delta)
        self.pending_model = None
        self.status_message = f"Selected {self.models[self.selected_index].name}."
        self.status_style = "dim"
        self.refresh_view()

    def _preferred_index(self, preferred_model: str | None) -> int:
        if not self.models:
            return 0

        for index, model in enumerate(self.models):
            if model.name == preferred_model:
                return index

        for index, model in enumerate(self.models):
            if model.active:
                return index

        return min(self.selected_index, len(self.models) - 1)


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

    BINDINGS = [
        ("r", "refresh_dashboard", "Refresh"),
        ("up", "select_previous_model", "Prev model"),
        ("k", "select_previous_model", "Prev model"),
        ("down", "select_next_model", "Next model"),
        ("j", "select_next_model", "Next model"),
        ("s", "switch_model", "Switch model"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, client: MurmurIPCClient | None = None) -> None:
        super().__init__()
        self.client = client or MurmurIPCClient()
        self._last_status: dict[str, Any] | None = None
        self._last_status_at: float | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="dashboard"):
            with Horizontal():
                yield ModelSwitcherPanel()
                yield Static("Stats panel placeholder", id="stats-panel", classes="panel column")
            yield Static("Log panel placeholder", id="log-panel", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_dashboard()
        self.set_interval(_REFRESH_INTERVAL_SECONDS, self.refresh_dashboard)

    def action_refresh_dashboard(self) -> None:
        self.refresh_dashboard()

    def action_select_next_model(self) -> None:
        self.query_one(ModelSwitcherPanel).select_next()

    def action_select_previous_model(self) -> None:
        self.query_one(ModelSwitcherPanel).select_previous()

    async def action_switch_model(self) -> None:
        model_panel = self.query_one(ModelSwitcherPanel)
        log_panel = self.query_one("#log-panel", Static)
        selected_model = model_panel.selected_model

        if selected_model is None:
            model_panel.set_error("No daemon models are available to switch.")
            log_panel.update(Text("No model selected.", style="yellow"))
            return

        if any(model.name == selected_model and model.active for model in model_panel.models):
            model_panel.set_error(f"{selected_model} is already active.")
            log_panel.update(Text("Selected model is already active.", style="yellow"))
            return

        if model_panel.pending_model != selected_model:
            model_panel.request_confirmation(selected_model)
            log_panel.update(
                Text(f"Confirm switch to {selected_model} by pressing s again.", style="yellow"),
            )
            return

        try:
            response = await self.client.switch_model(selected_model)
        except DaemonUnavailableError:
            message = "Daemon unavailable. Start murmur-daemon, then retry."
            model_panel.set_error(message)
            log_panel.update(Text(message, style="bold red"))
            return
        except DaemonIPCError as exc:
            message = f"Switch failed: {_safe_error(exc)}"
            model_panel.set_error(message)
            log_panel.update(Text(message, style="bold red"))
            return

        switched_model = _safe_label(response.get("model"), fallback=selected_model)
        model_panel.switch_succeeded(switched_model)
        log_panel.update(Text(f"Switched active model to {switched_model}.", style="green"))
        self.refresh_dashboard()

    def refresh_dashboard(self) -> None:
        self.run_worker(
            self._refresh_dashboard(),
            name="dashboard-refresh",
            group="dashboard",
            exclusive=True,
        )

    async def _refresh_dashboard(self) -> None:
        model_panel = self.query_one(ModelSwitcherPanel)
        stats_panel = self.query_one("#stats-panel", Static)
        log_panel = self.query_one("#log-panel", Static)

        try:
            status, models = await asyncio.gather(
                self.client.status(),
                self.client.list_models(),
            )
        except DaemonUnavailableError as exc:
            model_panel.set_unavailable()
            stats_panel.update(
                render_stats(
                    self._last_status,
                    unavailable_message=_safe_error(exc),
                    age_seconds=self._last_status_age_seconds(),
                ),
            )
            log_panel.update(
                Text("Daemon unavailable. Start murmur-daemon, then refresh.", style="yellow"),
            )
            return
        except DaemonIPCError as exc:
            message = f"IPC error: {_safe_error(exc)}"
            model_panel.set_error("Unable to read daemon model state.")
            stats_panel.update(
                render_stats(
                    self._last_status,
                    unavailable_message=message,
                    age_seconds=self._last_status_age_seconds(),
                ),
            )
            log_panel.update(Text(message, style="yellow"))
            return

        self._last_status = dict(status)
        self._last_status_at = monotonic()
        model_panel.update_models(models)
        stats_panel.update(self._render_stats(self._last_status))
        log_panel.update(Text("Connected to Murmur daemon", style="green"))

    def _render_stats(self, status: Mapping[str, Any]) -> Text:
        return render_stats(status)

    def _last_status_age_seconds(self) -> float | None:
        if self._last_status_at is None:
            return None
        return monotonic() - self._last_status_at


def _as_mapping(value: object) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    return {}


def _coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _safe_label(value: object, *, fallback: str) -> str:
    if not isinstance(value, str):
        return fallback
    label = " ".join(value.split())
    if not label:
        return fallback
    return _clip(label, 64)


def _safe_error(error: BaseException) -> str:
    return _clip(" ".join(str(error).split()), 160)


def _clip(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 1]}…"


def _format_mb(value: int | None) -> str:
    if value is None:
        return "unknown"
    return f"{value} MB"


def _format_latency(value: int | None) -> str:
    if value is None:
        return "unknown"
    return f"{value} ms"


def main() -> None:
    """Run the murmur-tui entry point."""
    MurmurControlPanel().run()


if __name__ == "__main__":
    main()
