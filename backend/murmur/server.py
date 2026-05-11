"""Unix socket IPC server for the Murmur ML backend daemon."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import struct
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from murmur.audio import AudioCapture
from murmur.context import get_context_for_app
from murmur.engine.registry import ModelRegistry

logger = logging.getLogger(__name__)

SOCKET_PATH = Path(tempfile.gettempdir()) / "murmur.sock"
DEFAULT_MODEL = "whisper-base"


class MurmurDaemon:
    """Main daemon server handling IPC commands."""

    def __init__(self, socket_path: Path = SOCKET_PATH) -> None:
        self.socket_path = socket_path
        self.registry = ModelRegistry()
        self.audio = AudioCapture()
        self._server: asyncio.Server | None = None
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

        # Load default model
        await self.registry.load_model(model)

        # Set restrictive permissions on socket
        self._server = await asyncio.start_unix_server(
            self._handle_client,
            path=str(self.socket_path),
        )
        os.chmod(self.socket_path, 0o600)

        import time

        self._stats["uptime_start"] = time.time()
        logger.info("Murmur daemon started on %s", self.socket_path)

        async with self._server:
            await self._server.serve_forever()

    async def stop(self) -> None:
        """Stop the daemon server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
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
        handlers: dict[str, Any] = {
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
        engine = self.registry.active_engine
        if engine is None:
            return {"error": "No model loaded"}

        # Audio comes as base64-encoded float32 array
        import base64

        audio_b64 = request.get("audio", "")
        audio_bytes = base64.b64decode(audio_b64)
        audio = np.frombuffer(audio_bytes, dtype=np.float32)

        # Get app context
        bundle_id = request.get("bundle_id", "")
        app_name = request.get("app_name", "")
        context = get_context_for_app(bundle_id, app_name)

        # Transcribe
        result = await engine.transcribe(
            audio,
            language=request.get("language", "en"),
            initial_prompt=context.prompt,
        )

        # Update stats
        self._stats["transcriptions"] += 1
        self._stats["total_latency_ms"] += result.duration_ms

        return {
            "text": result.text,
            "language": result.language,
            "duration_ms": result.duration_ms,
            "model": self.registry.active_model,
            "context": context.category,
        }

    async def _cmd_switch_model(self, request: dict[str, Any]) -> dict[str, Any]:
        """Switch to a different model."""
        model_name = request.get("model", "")
        if not model_name:
            return {"error": "No model specified"}

        try:
            await self.registry.load_model(model_name)
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
            "active": self.registry.active_model,
        }

    async def _cmd_status(self, _request: dict[str, Any]) -> dict[str, Any]:
        """Return daemon status."""
        import time

        uptime = 0.0
        if self._stats["uptime_start"]:
            uptime = time.time() - self._stats["uptime_start"]

        avg_latency = 0.0
        if self._stats["transcriptions"] > 0:
            avg_latency = self._stats["total_latency_ms"] / self._stats["transcriptions"]

        return {
            "status": "running",
            "model": self.registry.active_model,
            "model_loaded": self.registry.active_engine is not None
            and self.registry.active_engine.is_loaded,
            "transcriptions": self._stats["transcriptions"],
            "avg_latency_ms": round(avg_latency, 1),
            "uptime_seconds": round(uptime, 1),
        }

    async def _cmd_unload(self, _request: dict[str, Any]) -> dict[str, Any]:
        """Unload the current model."""
        await self.registry.unload()
        return {"status": "ok", "model": None}


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
