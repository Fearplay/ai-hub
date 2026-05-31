"""Single source of truth for the application version.

Bump :data:`__version__` following Semantic Versioning (MAJOR.MINOR.PATCH);
see ``.cursor/rules/app-version.mdc`` for exactly when each component
changes. Everything that needs the version (the Settings "About" card,
the window title, future build metadata) reads it from here so there is
never a second copy to forget.
"""

from __future__ import annotations

__version__ = "1.6.2"

# Friendly product name paired with the version in the UI.
APP_NAME = "AI Hub"


def version_string() -> str:
    """Return e.g. ``"v0.1.0"`` for display in the UI."""
    return f"v{__version__}"
