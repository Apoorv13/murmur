"""Tests for TUI IPC framing helpers."""

from typing import Any

import pytest

from murmur.tui.ipc import (
    DaemonIPCError,
    MurmurIPCClient,
    build_request,
    decode_message,
    encode_message,
)


class RecordingIPCClient(MurmurIPCClient):
    """IPC client test double that records command payloads."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def command(self, command: str, **payload: Any) -> dict[str, Any]:
        self.calls.append((command, dict(payload)))
        return {"status": "ok", "model": payload.get("model")}


def test_build_request_adds_command() -> None:
    assert build_request("status") == {"command": "status"}
    assert build_request("list-models") == {"command": "list-models"}
    assert build_request("switch-model", model="whisper-small") == {
        "command": "switch-model",
        "model": "whisper-small",
    }


def test_encode_decode_round_trip() -> None:
    message = {"command": "status", "nested": {"value": 1}}

    frame = encode_message(message)

    assert decode_message(frame) == message


def test_decode_rejects_short_frame() -> None:
    with pytest.raises(DaemonIPCError, match="length prefix"):
        decode_message(b"abc")


def test_decode_rejects_length_mismatch() -> None:
    frame = encode_message({"status": "running"})[:-1]

    with pytest.raises(DaemonIPCError, match="declared"):
        decode_message(frame)


def test_decode_rejects_non_object_json() -> None:
    body = b"[]"
    frame = len(body).to_bytes(4, "big") + body

    with pytest.raises(DaemonIPCError, match="JSON object"):
        decode_message(frame)


@pytest.mark.asyncio
async def test_switch_model_sends_expected_command_payload() -> None:
    client = RecordingIPCClient()

    response = await client.switch_model("whisper-small")

    assert response == {"status": "ok", "model": "whisper-small"}
    assert client.calls == [("switch-model", {"model": "whisper-small"})]
