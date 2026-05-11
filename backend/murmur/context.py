"""Application context detection and vocabulary mapping."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

DEFAULT_LANGUAGE = "en"
DEFAULT_ACCENT_PROFILE = "indian_english"


@dataclass(frozen=True)
class VocabularyProfile:
    """Vocabulary profile for a known application."""

    category: str
    terms: tuple[str, ...] = ()


SHARED_TECHNICAL_TERMS = (
    "API",
    "repo",
    "branch",
    "commit",
    "pull request",
    "npm",
    "pip",
    "kubectl",
    "TypeScript",
    "Python",
    "Swift",
)

CATEGORY_ALIASES: dict[str, str] = {
    "casual": "messaging",
}

# Accent profiles provide recognition hints only. They do not change locality, telemetry,
# or audio handling; transcription remains English by default.
ACCENT_PROFILES: dict[str, str] = {
    "indian_english": (
        "Accent profile: Indian English. Transcribe in English using standard spelling. "
        "Recognition hints: Indian English pronunciation and workplace phrasing may appear; "
        "preserve acronyms, product names, and common terms such as prepone, revert, lakh, "
        "and crore when spoken."
    ),
    "none": "",
}

# Vocabulary prompts per context category.
CONTEXT_PROMPTS: dict[str, str] = {
    "code": "Technical programming discussion.",
    "terminal": "Command line and shell commands.",
    "browser": "Browser-based reading, navigation, forms, and web apps.",
    "messaging": "Conversation with colleagues, friends, or collaborators.",
    "docs_email": "Documents, notes, spreadsheets, presentations, and email.",
    "general": "General text input.",
}

CATEGORY_VOCABULARY: dict[str, tuple[str, ...]] = {
    "code": (
        "function",
        "variable",
        "class",
        "import",
        "async",
        "await",
        "endpoint",
        "git",
        "merge",
        "deploy",
        "React",
        "Node",
        "debugger",
        "stack trace",
        *SHARED_TECHNICAL_TERMS,
    ),
    "terminal": (
        "sudo",
        "grep",
        "pipe",
        "directory",
        "chmod",
        "ssh",
        "docker",
        "brew",
        "shell",
        "zsh",
        "bash",
        "PATH",
        "environment variable",
        *SHARED_TECHNICAL_TERMS,
    ),
    "browser": (
        "URL",
        "tab",
        "address bar",
        "bookmark",
        "extension",
        "browser console",
        "localhost",
        "web app",
        "search query",
        "download",
    ),
    "messaging": (
        "thread",
        "channel",
        "DM",
        "mention",
        "emoji",
        "reaction",
        "standup",
        "sync",
        "FYI",
        "ETA",
        "OOO",
    ),
    "docs_email": (
        "document",
        "note",
        "spreadsheet",
        "slide",
        "comment",
        "track changes",
        "inbox",
        "subject line",
        "attachment",
        "calendar invite",
        "agenda",
        "action item",
    ),
    "general": (),
}

# Map app bundle IDs to categories plus app-specific vocabulary hints. Keep this data-only so
# downstream builds can override it without changing transcription behavior.
APP_VOCABULARY: dict[str, VocabularyProfile] = {
    # IDEs and editors
    "com.microsoft.VSCode": VocabularyProfile(
        "code",
        ("VS Code", "workspace", "extension", "command palette", "integrated terminal"),
    ),
    "com.apple.dt.Xcode": VocabularyProfile(
        "code",
        ("Xcode", "SwiftUI", "simulator", "scheme", "build setting"),
    ),
    "com.jetbrains.intellij": VocabularyProfile(
        "code",
        ("IntelliJ", "refactor", "run configuration", "inspection"),
    ),
    "com.jetbrains.pycharm": VocabularyProfile("code", ("PyCharm", "virtualenv", "pytest")),
    "com.jetbrains.WebStorm": VocabularyProfile("code", ("WebStorm", "npm script", "bundler")),
    "com.sublimetext.4": VocabularyProfile("code", ("Sublime Text", "palette", "snippet")),
    # Terminals
    "com.googlecode.iterm2": VocabularyProfile("terminal", ("iTerm2", "profile", "split pane")),
    "com.apple.Terminal": VocabularyProfile("terminal", ("Terminal", "man page", "shell script")),
    "dev.warp.Warp-Stable": VocabularyProfile("terminal", ("Warp", "block", "command palette")),
    "com.mitchellh.ghostty": VocabularyProfile("terminal", ("Ghostty", "terminal emulator")),
    # Browsers
    "com.google.Chrome": VocabularyProfile(
        "browser",
        ("Chrome", "DevTools", "omnibox", "incognito"),
    ),
    "com.apple.Safari": VocabularyProfile("browser", ("Safari", "reader mode", "tab group")),
    "org.mozilla.firefox": VocabularyProfile("browser", ("Firefox", "container tab")),
    "com.microsoft.edgemac": VocabularyProfile("browser", ("Edge", "profile", "collection")),
    "company.thebrowser.Browser": VocabularyProfile("browser", ("Arc", "space", "split view")),
    "com.brave.Browser": VocabularyProfile("browser", ("Brave", "shields", "private window")),
    # Communication
    "com.tinyspeck.slackmacgap": VocabularyProfile(
        "messaging",
        ("Slack", "huddle", "canvas", "workflow"),
    ),
    "com.apple.MobileSMS": VocabularyProfile("messaging", ("Messages", "iMessage", "group chat")),
    "com.microsoft.teams2": VocabularyProfile("messaging", ("Teams", "meeting chat", "channel")),
    "com.hnc.Discord": VocabularyProfile("messaging", ("Discord", "server", "voice channel")),
    "org.whispersystems.signal-desktop": VocabularyProfile(
        "messaging",
        ("Signal", "encrypted message"),
    ),
    "us.zoom.xos": VocabularyProfile("messaging", ("Zoom", "meeting", "chat")),
    # Documents and email
    "com.apple.mail": VocabularyProfile("docs_email", ("Mail", "mailbox", "reply all")),
    "com.microsoft.Outlook": VocabularyProfile("docs_email", ("Outlook", "inbox", "calendar")),
    "com.microsoft.Word": VocabularyProfile("docs_email", ("Word", "heading", "review comment")),
    "com.microsoft.Excel": VocabularyProfile("docs_email", ("Excel", "formula", "pivot table")),
    "com.microsoft.Powerpoint": VocabularyProfile(
        "docs_email",
        ("PowerPoint", "speaker notes", "deck"),
    ),
    "com.apple.iWork.Pages": VocabularyProfile("docs_email", ("Pages", "document layout")),
    "com.apple.iWork.Numbers": VocabularyProfile("docs_email", ("Numbers", "sheet", "formula")),
    "com.apple.iWork.Keynote": VocabularyProfile("docs_email", ("Keynote", "slide", "deck")),
    "notion.id": VocabularyProfile("docs_email", ("Notion", "database", "page")),
    "md.obsidian": VocabularyProfile("docs_email", ("Obsidian", "markdown", "backlink")),
}

# Backward-compatible category lookup for callers that only need the coarse context.
APP_CONTEXTS: dict[str, str] = {
    bundle_id: profile.category for bundle_id, profile in APP_VOCABULARY.items()
}


@dataclass
class AppContext:
    """Context information about the active application."""

    bundle_id: str
    app_name: str
    category: str
    prompt: str
    language: str
    accent_profile: str


def _canonical_category(category: str) -> str:
    return CATEGORY_ALIASES.get(category, category)


def _dedupe_terms(terms: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for term in terms:
        normalized = term.casefold()
        if normalized not in seen:
            deduped.append(term)
            seen.add(normalized)
    return tuple(deduped)


def build_context_prompt(
    category: str,
    accent_profile: str = DEFAULT_ACCENT_PROFILE,
    *,
    app_terms: Sequence[str] = (),
) -> str:
    """Build a prompt from app context and accent recognition hints."""
    canonical_category = _canonical_category(category)
    context_prompt = CONTEXT_PROMPTS.get(canonical_category, CONTEXT_PROMPTS["general"])
    category_terms = CATEGORY_VOCABULARY.get(
        canonical_category,
        CATEGORY_VOCABULARY["general"],
    )
    vocabulary = _dedupe_terms((*category_terms, *app_terms))
    accent_prompt = ACCENT_PROFILES.get(accent_profile, ACCENT_PROFILES[DEFAULT_ACCENT_PROFILE])

    if vocabulary:
        context_prompt = f"{context_prompt} Vocabulary hints: {', '.join(vocabulary)}."

    if not accent_prompt:
        return context_prompt
    return f"{context_prompt} {accent_prompt}"


def get_context_for_app(
    bundle_id: str,
    app_name: str = "",
    *,
    accent_profile: str = DEFAULT_ACCENT_PROFILE,
    vocabulary_map: Mapping[str, VocabularyProfile] | None = None,
) -> AppContext:
    """Get transcription context based on the active application.

    Args:
        bundle_id: The macOS bundle identifier of the active app
        app_name: Human-readable app name (optional)
        accent_profile: Recognition hint profile to include in the prompt
        vocabulary_map: Optional bundle ID vocabulary map override

    Returns:
        AppContext with category and appropriate vocabulary prompt
    """
    profiles = APP_VOCABULARY if vocabulary_map is None else vocabulary_map
    profile = profiles.get(bundle_id, VocabularyProfile("general"))
    category = _canonical_category(profile.category)
    prompt = build_context_prompt(category, accent_profile, app_terms=profile.terms)

    return AppContext(
        bundle_id=bundle_id,
        app_name=app_name,
        category=category,
        prompt=prompt,
        language=DEFAULT_LANGUAGE,
        accent_profile=accent_profile,
    )
