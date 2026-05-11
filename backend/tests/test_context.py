"""Tests for app context detection."""

from murmur.context import (
    DEFAULT_ACCENT_PROFILE,
    DEFAULT_LANGUAGE,
    MAX_INITIAL_PROMPT_CHARS,
    VocabularyProfile,
    build_context_prompt,
    build_initial_prompt,
    get_context_for_app,
)


def test_vscode_context() -> None:
    ctx = get_context_for_app("com.microsoft.VSCode", "Visual Studio Code")
    assert ctx.category == "code"
    assert "Local dictation guidance" in ctx.prompt
    assert "Active app category: code" in ctx.prompt
    assert "Language: English" in ctx.prompt
    assert "function" in ctx.prompt
    assert "workspace" in ctx.prompt
    assert "command palette" in ctx.prompt
    assert ctx.bundle_id == "com.microsoft.VSCode"
    assert ctx.language == DEFAULT_LANGUAGE
    assert ctx.accent_profile == DEFAULT_ACCENT_PROFILE


def test_terminal_context() -> None:
    ctx = get_context_for_app("com.apple.Terminal", "Terminal")
    assert ctx.category == "terminal"
    assert "Active app category: terminal" in ctx.prompt
    assert "sudo" in ctx.prompt
    assert "man page" in ctx.prompt


def test_browser_context() -> None:
    ctx = get_context_for_app("com.google.Chrome", "Google Chrome")
    assert ctx.category == "browser"
    assert "Active app category: browser" in ctx.prompt
    assert "URL" in ctx.prompt
    assert "tab" in ctx.prompt
    assert "DevTools" in ctx.prompt


def test_unknown_app_gets_general() -> None:
    ctx = get_context_for_app("com.unknown.app", "Unknown App")
    assert ctx.category == "general"
    assert "Active app category: general" in ctx.prompt
    assert "General text input" in ctx.prompt


def test_slack_is_messaging() -> None:
    ctx = get_context_for_app("com.tinyspeck.slackmacgap", "Slack")
    assert ctx.category == "messaging"
    assert "Active app category: messaging" in ctx.prompt
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
    assert "Active app category: docs_email" in ctx.prompt
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


def test_language_hint_can_be_supplied() -> None:
    ctx = get_context_for_app("com.microsoft.VSCode", "Visual Studio Code", language="en-IN")
    assert ctx.language == "en-IN"
    assert "Language: en-IN." in ctx.prompt


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


def test_initial_prompt_is_bounded() -> None:
    prompt = build_initial_prompt(
        "code",
        accent_profile="none",
        app_terms=tuple(f"custom-term-{index:03d}" for index in range(200)),
        max_chars=420,
    )
    assert len(prompt) <= 420
    assert prompt.startswith("Local dictation guidance")
    assert "custom-term-199" not in prompt


def test_initial_prompt_keeps_complete_sections_when_tightly_bounded() -> None:
    prompt = build_initial_prompt("code", max_chars=300)
    assert len(prompt) <= 300
    assert prompt.endswith(".")
    assert "Active app category: code" in prompt


def test_initial_prompt_deduplicates_vocabulary_case_insensitively() -> None:
    prompt = build_initial_prompt(
        "terminal",
        accent_profile="none",
        app_terms=("CustomCTL", "customctl", "  CustomCTL  ", "deploy\nship"),
    )
    assert prompt.count("CustomCTL") == 1
    assert "deploy ship" in prompt


def test_initial_prompt_falls_back_for_unknown_category_and_accent() -> None:
    prompt = build_initial_prompt("unknown-category", accent_profile="unexpected")
    assert "Active app category: general" in prompt
    assert "General text input" in prompt
    assert "Indian English" in prompt
    assert len(prompt) <= MAX_INITIAL_PROMPT_CHARS
