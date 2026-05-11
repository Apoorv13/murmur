"""Application context detection and vocabulary mapping."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_LANGUAGE = "en"
DEFAULT_ACCENT_PROFILE = "indian_english"

# Map app bundle IDs to context categories
APP_CONTEXTS: dict[str, str] = {
    # IDEs and editors
    "com.microsoft.VSCode": "code",
    "com.apple.dt.Xcode": "code",
    "com.jetbrains.intellij": "code",
    "com.sublimetext.4": "code",
    "com.googlecode.iterm2": "terminal",
    "com.apple.Terminal": "terminal",
    # Communication
    "com.tinyspeck.slackmacgap": "casual",
    "com.apple.MobileSMS": "casual",
    "us.zoom.xos": "casual",
    # Browsers
    "com.google.Chrome": "general",
    "com.apple.Safari": "general",
    "org.mozilla.firefox": "general",
}

SHARED_TECHNICAL_TERMS = (
    "API, repo, branch, commit, pull request, npm, pip, kubectl, TypeScript, Python, Swift"
)

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

# Vocabulary prompts per context category
CONTEXT_PROMPTS: dict[str, str] = {
    "code": (
        "Technical programming discussion. Common terms: function, variable, class, "
        "import, async, await, endpoint, git, merge, deploy, React, Node, "
        f"{SHARED_TECHNICAL_TERMS}."
    ),
    "terminal": (
        "Command line and shell commands. Common terms: sudo, grep, pipe, "
        "directory, chmod, ssh, docker, brew, shell, zsh, bash, "
        f"{SHARED_TECHNICAL_TERMS}."
    ),
    "casual": ("Casual conversation with colleagues."),
    "general": ("General text input."),
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


def build_context_prompt(category: str, accent_profile: str = DEFAULT_ACCENT_PROFILE) -> str:
    """Build a prompt from app context and accent recognition hints."""
    context_prompt = CONTEXT_PROMPTS.get(category, CONTEXT_PROMPTS["general"])
    accent_prompt = ACCENT_PROFILES.get(accent_profile, ACCENT_PROFILES[DEFAULT_ACCENT_PROFILE])

    if not accent_prompt:
        return context_prompt
    return f"{context_prompt} {accent_prompt}"


def get_context_for_app(
    bundle_id: str,
    app_name: str = "",
    *,
    accent_profile: str = DEFAULT_ACCENT_PROFILE,
) -> AppContext:
    """Get transcription context based on the active application.

    Args:
        bundle_id: The macOS bundle identifier of the active app
        app_name: Human-readable app name (optional)
        accent_profile: Recognition hint profile to include in the prompt

    Returns:
        AppContext with category and appropriate vocabulary prompt
    """
    category = APP_CONTEXTS.get(bundle_id, "general")
    prompt = build_context_prompt(category, accent_profile)

    return AppContext(
        bundle_id=bundle_id,
        app_name=app_name,
        category=category,
        prompt=prompt,
        language=DEFAULT_LANGUAGE,
        accent_profile=accent_profile,
    )
