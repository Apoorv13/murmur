"""Application context detection and vocabulary mapping."""

from __future__ import annotations

from dataclasses import dataclass

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

# Vocabulary prompts per context category
CONTEXT_PROMPTS: dict[str, str] = {
    "code": (
        "Technical programming discussion. Common terms: function, variable, class, "
        "import, async, await, API, endpoint, git, commit, merge, deploy, "
        "TypeScript, Python, Swift, React, Node."
    ),
    "terminal": (
        "Command line and shell commands. Common terms: sudo, grep, pipe, "
        "directory, chmod, ssh, docker, kubectl, npm, pip, brew."
    ),
    "casual": (
        "Casual conversation with colleagues."
    ),
    "general": (
        "General text input."
    ),
}


@dataclass
class AppContext:
    """Context information about the active application."""

    bundle_id: str
    app_name: str
    category: str
    prompt: str


def get_context_for_app(bundle_id: str, app_name: str = "") -> AppContext:
    """Get transcription context based on the active application.

    Args:
        bundle_id: The macOS bundle identifier of the active app
        app_name: Human-readable app name (optional)

    Returns:
        AppContext with category and appropriate vocabulary prompt
    """
    category = APP_CONTEXTS.get(bundle_id, "general")
    prompt = CONTEXT_PROMPTS.get(category, CONTEXT_PROMPTS["general"])

    return AppContext(
        bundle_id=bundle_id,
        app_name=app_name,
        category=category,
        prompt=prompt,
    )
