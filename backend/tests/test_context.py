"""Tests for app context detection."""

from murmur.context import get_context_for_app


def test_vscode_context() -> None:
    ctx = get_context_for_app("com.microsoft.VSCode", "Visual Studio Code")
    assert ctx.category == "code"
    assert "function" in ctx.prompt
    assert ctx.bundle_id == "com.microsoft.VSCode"


def test_terminal_context() -> None:
    ctx = get_context_for_app("com.apple.Terminal", "Terminal")
    assert ctx.category == "terminal"
    assert "sudo" in ctx.prompt


def test_unknown_app_gets_general() -> None:
    ctx = get_context_for_app("com.unknown.app", "Unknown App")
    assert ctx.category == "general"


def test_slack_is_casual() -> None:
    ctx = get_context_for_app("com.tinyspeck.slackmacgap", "Slack")
    assert ctx.category == "casual"
