"""Tests for TUI IPC framing helpers."""

import pytest

from murmur.tui.ipc import DaemonIPCError, build_request, decode_message, encode_message


def test_build_request_adds_command() -> None:
    assert build_request("status") == {"command": "status"}
    assert build_request("list-models") == {"command": "list-models"}


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
