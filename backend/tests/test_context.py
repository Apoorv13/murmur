"""Tests for app context detection."""

from murmur.context import (
    DEFAULT_ACCENT_PROFILE,
    DEFAULT_LANGUAGE,
    VocabularyProfile,
    build_context_prompt,
    get_context_for_app,
)


def test_vscode_context() -> None:
    ctx = get_context_for_app("com.microsoft.VSCode", "Visual Studio Code")
    assert ctx.category == "code"
    assert "function" in ctx.prompt
    assert "workspace" in ctx.prompt
    assert "command palette" in ctx.prompt
    assert ctx.bundle_id == "com.microsoft.VSCode"
    assert ctx.language == DEFAULT_LANGUAGE
    assert ctx.accent_profile == DEFAULT_ACCENT_PROFILE


def test_terminal_context() -> None:
    ctx = get_context_for_app("com.apple.Terminal", "Terminal")
    assert ctx.category == "terminal"
    assert "sudo" in ctx.prompt
    assert "man page" in ctx.prompt


def test_browser_context() -> None:
    ctx = get_context_for_app("com.google.Chrome", "Google Chrome")
    assert ctx.category == "browser"
    assert "URL" in ctx.prompt
    assert "tab" in ctx.prompt
    assert "DevTools" in ctx.prompt


def test_unknown_app_gets_general() -> None:
    ctx = get_context_for_app("com.unknown.app", "Unknown App")
    assert ctx.category == "general"


def test_slack_is_messaging() -> None:
    ctx = get_context_for_app("com.tinyspeck.slackmacgap", "Slack")
    assert ctx.category == "messaging"
    assert "thread" in ctx.prompt
    assert "huddle" in ctx.prompt


def test_messages_uses_messaging_vocabulary() -> None:
    ctx = get_context_for_app("com.apple.MobileSMS", "Messages")
    assert ctx.category == "messaging"
    assert "iMessage" in ctx.prompt
    assert "group chat" in ctx.prompt


def test_docs_email_context() -> None:
    ctx = get_context_for_app("com.apple.mail", "Mail")
    assert ctx.category == "docs_email"
    assert "subject line" in ctx.prompt
    assert "reply all" in ctx.prompt


def test_docs_editor_context() -> None:
    ctx = get_context_for_app("com.microsoft.Word", "Microsoft Word")
    assert ctx.category == "docs_email"
    assert "document" in ctx.prompt
    assert "review comment" in ctx.prompt


def test_default_prompt_includes_indian_english_hints() -> None:
    ctx = get_context_for_app("com.unknown.app", "Unknown App")
    assert "Indian English" in ctx.prompt
    assert "standard spelling" in ctx.prompt
    assert "prepone" in ctx.prompt
    assert "revert" in ctx.prompt


def test_code_prompt_includes_contextual_technical_vocabulary() -> None:
    prompt = build_context_prompt("code")
    for term in ("API", "repo", "branch", "commit", "TypeScript", "Python", "Swift"):
        assert term in prompt


def test_terminal_prompt_includes_command_line_vocabulary() -> None:
    prompt = build_context_prompt("terminal")
    for term in ("npm", "pip", "kubectl", "shell", "zsh", "bash"):
        assert term in prompt


def test_accent_profile_can_be_disabled() -> None:
    ctx = get_context_for_app("com.microsoft.VSCode", "Visual Studio Code", accent_profile="none")
    assert ctx.accent_profile == "none"
    assert "Indian English" not in ctx.prompt


def test_legacy_casual_category_aliases_to_messaging() -> None:
    prompt = build_context_prompt("casual", accent_profile="none")
    assert "Conversation" in prompt
    assert "thread" in prompt


def test_vocabulary_map_can_be_overridden() -> None:
    ctx = get_context_for_app(
        "com.example.custom",
        "Custom Console",
        accent_profile="none",
        vocabulary_map={
            "com.example.custom": VocabularyProfile("terminal", ("customctl", "Custom Console")),
        },
    )
    assert ctx.category == "terminal"
    assert "customctl" in ctx.prompt
    assert "Custom Console" in ctx.prompt
    assert "Indian English" not in ctx.prompt
