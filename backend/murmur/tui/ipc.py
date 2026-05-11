"""IPC client for the Murmur daemon Unix socket."""

from __future__ import annotations

import asyncio
import json
import struct
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SOCKET_PATH = Path(tempfile.gettempdir()) / "murmur.sock"
_MAX_MESSAGE_BYTES = 10 * 1024 * 1024


class DaemonIPCError(RuntimeError):
    """Raised when the daemon returns invalid data or reports an error."""


class DaemonUnavailableError(DaemonIPCError):
    """Raised when the daemon socket cannot be reached."""


def build_request(command: str, **payload: Any) -> dict[str, Any]:
    """Build a daemon command request payload."""
    return {"command": command, **payload}


def encode_message(message: Mapping[str, Any]) -> bytes:
    """Encode a daemon IPC message using the length-prefixed JSON framing."""
    body = json.dumps(dict(message)).encode()
    return struct.pack(">I", len(body)) + body


def decode_message(frame: bytes) -> dict[str, Any]:
    """Decode a complete length-prefixed daemon IPC frame."""
    if len(frame) < 4:
        msg = "Frame is missing length prefix"
        raise DaemonIPCError(msg)

    length = struct.unpack(">I", frame[:4])[0]
    if length > _MAX_MESSAGE_BYTES:
        msg = f"Frame length {length} exceeds maximum {_MAX_MESSAGE_BYTES}"
        raise DaemonIPCError(msg)

    body = frame[4:]
    if len(body) != length:
        msg = f"Frame declared {length} bytes but contained {len(body)} bytes"
        raise DaemonIPCError(msg)

    try:
        decoded = json.loads(body.decode())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        msg = "Frame body is not valid JSON"
        raise DaemonIPCError(msg) from exc

    if not isinstance(decoded, dict):
        msg = "Frame body must decode to a JSON object"
        raise DaemonIPCError(msg)

    return decoded


class MurmurIPCClient:
    """Small async client for MurmurDaemon commands."""

    def __init__(self, socket_path: Path = SOCKET_PATH, timeout_seconds: float = 2.0) -> None:
        self.socket_path = socket_path
        self.timeout_seconds = timeout_seconds

    async def command(self, command: str, **payload: Any) -> dict[str, Any]:
        """Send a command to the daemon and return the JSON response."""
        request = build_request(command, **payload)
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(str(self.socket_path)),
                timeout=self.timeout_seconds,
            )
        except (FileNotFoundError, ConnectionRefusedError, OSError, TimeoutError) as exc:
            msg = f"Could not connect to daemon socket {self.socket_path}"
            raise DaemonUnavailableError(msg) from exc

        try:
            writer.write(encode_message(request))
            await asyncio.wait_for(writer.drain(), timeout=self.timeout_seconds)

            length_bytes = await asyncio.wait_for(
                reader.readexactly(4),
                timeout=self.timeout_seconds,
            )
            length = struct.unpack(">I", length_bytes)[0]
            if length > _MAX_MESSAGE_BYTES:
                msg = f"Response length {length} exceeds maximum {_MAX_MESSAGE_BYTES}"
                raise DaemonIPCError(msg)
            body = await asyncio.wait_for(reader.readexactly(length), timeout=self.timeout_seconds)
            response = decode_message(length_bytes + body)
        except asyncio.IncompleteReadError as exc:
            msg = "Daemon closed the connection before sending a complete response"
            raise DaemonIPCError(msg) from exc
        except TimeoutError as exc:
            msg = "Timed out waiting for daemon response"
            raise DaemonIPCError(msg) from exc
        finally:
            writer.close()
            await writer.wait_closed()

        if "error" in response:
            raise DaemonIPCError(str(response["error"]))
        return response

    async def status(self) -> dict[str, Any]:
        """Return daemon status."""
        return await self.command("status")

    async def list_models(self) -> dict[str, Any]:
        """Return available daemon models."""
        return await self.command("list-models")

    async def switch_model(self, model: str) -> dict[str, Any]:
        """Ask the daemon to switch to a different model."""
        return await self.command("switch-model", model=model)

    async def unload_model(self) -> dict[str, Any]:
        """Ask the daemon to unload the current model."""
        return await self.command("unload")
