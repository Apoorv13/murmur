"""Unix socket IPC server for the Murmur ML backend daemon."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import resource
import signal
import struct
import sys
import tempfile
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import numpy as np

from murmur.audio import AudioCapture
from murmur.context import DEFAULT_ACCENT_PROFILE, get_context_for_app
from murmur.engine.base import STTEngine
from murmur.engine.registry import ModelRegistry
from murmur.vad import EnergyVoiceActivityDetector

logger = logging.getLogger(__name__)

Handler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]

SOCKET_PATH = Path(tempfile.gettempdir()) / "murmur.sock"
DEFAULT_MODEL = "whisper-base"
DEFAULT_IDLE_TIMEOUT_SECONDS = 60.0
IDLE_TIMEOUT_ENV = "MURMUR_IDLE_TIMEOUT_SECONDS"
MAX_MESSAGE_BYTES = 100 * 1024 * 1024


class MurmurDaemon:
    """Main daemon server handling IPC commands."""

    def __init__(
        self,
        socket_path: Path = SOCKET_PATH,
        idle_timeout_seconds: float | None = None,
    ) -> None:
        self.socket_path = socket_path
        self.registry = ModelRegistry()
        self.audio = AudioCapture()
        self.vad = EnergyVoiceActivityDetector()
        self.default_model = DEFAULT_MODEL
        self.idle_timeout_seconds = self._resolve_idle_timeout(idle_timeout_seconds)
        self._selected_model = DEFAULT_MODEL
        self._server: asyncio.Server | None = None
        self._model_lock = asyncio.Lock()
        self._loading_model: str | None = None
        self._last_activity_at: float | None = None
        self._last_activity_loop_time: float | None = None
        self._idle_handle: asyncio.TimerHandle | None = None
        self._stats: dict[str, Any] = {
            "transcriptions": 0,
            "total_latency_ms": 0.0,
            "uptime_start": None,
        }

    async def start(self, model: str = DEFAULT_MODEL) -> None:
        """Start the daemon server."""
        # Clean up stale socket
        if self.socket_path.exists():
            self.socket_path.unlink()

        self.default_model = model
        self._selected_model = model

        # Load default model
        async with self._model_lock:
            await self._load_model(model)

        # Set restrictive permissions on socket
        self._server = await asyncio.start_unix_server(
            self._handle_client,
            path=str(self.socket_path),
        )
        os.chmod(self.socket_path, 0o600)

        self._stats["uptime_start"] = time.time()
        self._mark_activity()
        logger.info("Murmur daemon started on %s", self.socket_path)

        async with self._server:
            await self._server.serve_forever()

    async def stop(self) -> None:
        """Stop the daemon server."""
        self._cancel_idle_unload()
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        async with self._model_lock:
            await self.registry.unload()
        if self.socket_path.exists():
            self.socket_path.unlink()
        logger.info("Murmur daemon stopped")

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a client connection."""
        try:
            # Read message length (4 bytes, big-endian)
            length_bytes = await reader.readexactly(4)
            length = struct.unpack(">I", length_bytes)[0]
            if length > MAX_MESSAGE_BYTES:
                msg = f"Message too large: {length} bytes"
                raise ValueError(msg)

            # Read message
            data = await reader.readexactly(length)
            request = json.loads(data.decode())

            # Dispatch command
            command = request.get("command", "")
            response = await self._dispatch(command, request)

            # Send response
            response_bytes = json.dumps(response).encode()
            writer.write(struct.pack(">I", len(response_bytes)))
            writer.write(response_bytes)
            await writer.drain()
        except Exception as e:
            logger.exception("Error handling client: %s", e)
            error_response = json.dumps({"error": str(e)}).encode()
            writer.write(struct.pack(">I", len(error_response)))
            writer.write(error_response)
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def _dispatch(self, command: str, request: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a command to the appropriate handler."""
        handlers: dict[str, Handler] = {
            "transcribe": self._cmd_transcribe,
            "switch-model": self._cmd_switch_model,
            "list-models": self._cmd_list_models,
            "status": self._cmd_status,
            "unload": self._cmd_unload,
        }

        handler = handlers.get(command)
        if handler is None:
            return {"error": f"Unknown command: {command}"}

        return await handler(request)

    async def _cmd_transcribe(self, request: dict[str, Any]) -> dict[str, Any]:
        """Transcribe audio buffer."""
        self._cancel_idle_unload()
        async with self._model_lock:
            try:
                engine = await self._ensure_model_loaded()
            except (ValueError, RuntimeError) as e:
                return {"error": str(e)}

            try:
                # Audio comes as base64-encoded float32 array
                audio_b64 = request.get("audio", "")
                audio_bytes = base64.b64decode(audio_b64)
                audio = np.frombuffer(audio_bytes, dtype=np.float32)
                sample_rate = int(request.get("sample_rate", self.audio.sample_rate))

                # Get app context
                bundle_id = request.get("bundle_id", "")
                app_name = request.get("app_name", "")
                accent_profile = request.get("accent_profile", DEFAULT_ACCENT_PROFILE)
                context = get_context_for_app(bundle_id, app_name, accent_profile=accent_profile)

                vad_result = self.vad.detect(audio, sample_rate=sample_rate)
                if not vad_result.has_speech:
                    return {
                        "text": "",
                        "language": request.get("language", context.language),
                        "duration_ms": 0.0,
                        "model": self.registry.active_model,
                        "context": context.category,
                        "accent_profile": context.accent_profile,
                        "speech_detected": False,
                    }

                # Transcribe
                result = await engine.transcribe(
                    vad_result.trimmed_audio,
                    sample_rate=sample_rate,
                    language=request.get("language", context.language),
                    initial_prompt=context.prompt,
                )
            finally:
                self._mark_activity()

        # Update stats
        self._stats["transcriptions"] += 1
        self._stats["total_latency_ms"] += result.duration_ms

        return {
            "text": result.text,
            "language": result.language,
            "duration_ms": result.duration_ms,
            "model": self.registry.active_model,
            "context": context.category,
            "accent_profile": context.accent_profile,
            "speech_detected": True,
            "vad": {
                "start_sample": vad_result.start_sample,
                "end_sample": vad_result.end_sample,
                "speech_duration_ms": round(vad_result.speech_duration_ms, 1),
                "original_duration_ms": round(vad_result.original_duration_ms, 1),
            },
        }

    async def _cmd_switch_model(self, request: dict[str, Any]) -> dict[str, Any]:
        """Switch to a different model."""
        model_name = request.get("model", "")
        if not model_name:
            return {"error": "No model specified"}

        try:
            self._cancel_idle_unload()
            async with self._model_lock:
                await self._load_model(model_name)
                self._selected_model = model_name
                self._mark_activity()
            return {"status": "ok", "model": model_name}
        except (ValueError, RuntimeError) as e:
            return {"error": str(e)}

    async def _cmd_list_models(self, _request: dict[str, Any]) -> dict[str, Any]:
        """List available models."""
        models = ModelRegistry.list_models()
        return {
            "models": {
                name: {
                    "family": info.family,
                    "size": info.size,
                    "language": info.language,
                    "ram_mb": info.estimated_ram_mb,
                    "latency_ms": info.estimated_latency_ms,
                    "description": info.description,
                }
                for name, info in models.items()
            },
            "active": self._selected_model,
            "loaded": self.registry.active_model,
        }

    async def _cmd_status(self, _request: dict[str, Any]) -> dict[str, Any]:
        """Return daemon status."""
        uptime = 0.0
        if self._stats["uptime_start"]:
            uptime = time.time() - self._stats["uptime_start"]

        avg_latency = 0.0
        if self._stats["transcriptions"] > 0:
            avg_latency = self._stats["total_latency_ms"] / self._stats["transcriptions"]

        model_loaded = self._is_model_loaded()
        last_activity_seconds_ago = None
        if self._last_activity_at is not None:
            last_activity_seconds_ago = round(time.time() - self._last_activity_at, 1)

        return {
            "status": "running",
            "model": self.registry.active_model,
            "active_model": self._selected_model,
            "default_model": self.default_model,
            "loaded_model": self.registry.active_model,
            "model_loaded": model_loaded,
            "model_loading": self._loading_model is not None,
            "loading_model": self._loading_model,
            "idle_timeout_seconds": self.idle_timeout_seconds,
            "last_activity_at": self._last_activity_at,
            "last_activity_seconds_ago": last_activity_seconds_ago,
            "next_idle_unload_seconds": self._next_idle_unload_seconds(),
            "transcriptions": self._stats["transcriptions"],
            "avg_latency_ms": round(avg_latency, 1),
            "uptime_seconds": round(uptime, 1),
            "resources": self._resource_metrics(),
        }

    async def _cmd_unload(self, _request: dict[str, Any]) -> dict[str, Any]:
        """Unload the current model."""
        self._cancel_idle_unload()
        async with self._model_lock:
            await self.registry.unload()
        return {"status": "ok", "model": None, "active_model": self._selected_model}

    @staticmethod
    def _resolve_idle_timeout(configured: float | None) -> float:
        if configured is not None:
            return max(0.0, configured)

        raw_timeout = os.environ.get(IDLE_TIMEOUT_ENV)
        if raw_timeout is None:
            return DEFAULT_IDLE_TIMEOUT_SECONDS

        try:
            return max(0.0, float(raw_timeout))
        except ValueError:
            logger.warning(
                "Invalid %s=%r; using default %.1fs",
                IDLE_TIMEOUT_ENV,
                raw_timeout,
                DEFAULT_IDLE_TIMEOUT_SECONDS,
            )
            return DEFAULT_IDLE_TIMEOUT_SECONDS

    async def _load_model(self, model: str) -> None:
        self._loading_model = model
        try:
            await self.registry.load_model(model)
        finally:
            self._loading_model = None

    async def _ensure_model_loaded(self) -> STTEngine:
        engine = self.registry.active_engine
        if engine is not None and engine.is_loaded:
            return engine

        model_name = self._selected_model or self.default_model
        await self._load_model(model_name)
        self._selected_model = model_name

        loaded_engine = self.registry.active_engine
        if loaded_engine is None:
            msg = f"Model failed to load: {model_name}"
            raise RuntimeError(msg)
        return loaded_engine

    def _mark_activity(self) -> None:
        loop = asyncio.get_running_loop()
        self._last_activity_at = time.time()
        self._last_activity_loop_time = loop.time()
        self._schedule_idle_unload()

    def _schedule_idle_unload(self) -> None:
        self._cancel_idle_unload()
        if self.idle_timeout_seconds <= 0 or self.registry.active_engine is None:
            return

        loop = asyncio.get_running_loop()
        self._idle_handle = loop.call_later(
            self.idle_timeout_seconds,
            self._on_idle_timeout,
        )

    def _cancel_idle_unload(self) -> None:
        if self._idle_handle is not None:
            self._idle_handle.cancel()
            self._idle_handle = None

    def _on_idle_timeout(self) -> None:
        self._idle_handle = None
        task = asyncio.create_task(self._unload_if_idle())
        task.add_done_callback(self._log_background_task_result)

    @staticmethod
    def _log_background_task_result(task: asyncio.Task[None]) -> None:
        try:
            task.result()
        except Exception:
            logger.exception("Idle model unload failed")

    async def _unload_if_idle(self) -> None:
        if self.idle_timeout_seconds <= 0:
            return

        async with self._model_lock:
            engine = self.registry.active_engine
            if engine is None or self._last_activity_loop_time is None:
                return

            loop = asyncio.get_running_loop()
            idle_seconds = loop.time() - self._last_activity_loop_time
            remaining_seconds = self.idle_timeout_seconds - idle_seconds
            if remaining_seconds > 0:
                self._cancel_idle_unload()
                self._idle_handle = loop.call_later(
                    remaining_seconds,
                    self._on_idle_timeout,
                )
                return

            model_name = self.registry.active_model or self._selected_model
            await self.registry.unload()
            logger.info(
                "Unloaded idle model: %s after %.1fs idle",
                model_name,
                idle_seconds,
            )

    def _next_idle_unload_seconds(self) -> float | None:
        if self._idle_handle is None or self._idle_handle.cancelled():
            return None

        loop = asyncio.get_running_loop()
        return round(max(0.0, self._idle_handle.when() - loop.time()), 1)

    def _is_model_loaded(self) -> bool:
        engine = self.registry.active_engine
        return engine is not None and engine.is_loaded

    @staticmethod
    def _resource_metrics() -> dict[str, float]:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        peak_rss_mb = float(usage.ru_maxrss)
        if sys.platform == "darwin":
            peak_rss_mb = peak_rss_mb / 1024 / 1024
        else:
            peak_rss_mb = peak_rss_mb / 1024

        return {
            "peak_rss_mb": round(peak_rss_mb, 1),
            "user_cpu_seconds": round(usage.ru_utime, 3),
            "system_cpu_seconds": round(usage.ru_stime, 3),
        }


def main() -> None:
    """Entry point for the murmur-daemon command."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    daemon = MurmurDaemon()

    loop = asyncio.new_event_loop()

    def shutdown(sig: signal.Signals) -> None:
        logger.info("Received %s, shutting down...", sig.name)
        loop.create_task(daemon.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown, sig)

    try:
        loop.run_until_complete(daemon.start())
    except KeyboardInterrupt:
        loop.run_until_complete(daemon.stop())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
