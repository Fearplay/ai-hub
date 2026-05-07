"""OS-native API key storage via ``keyring``.

We persist API keys in the platform's credential manager:

* Windows  → Credential Manager
* macOS    → Keychain
* Linux    → Secret Service / KWallet (when available)

The plaintext key never touches disk in our code; ``keyring`` writes it
through the OS-encrypted store. This module is a tiny wrapper so sections
do not need to know about the backend.

If the ``keyring`` package is missing (e.g. headless container) or no
backend is available, every getter returns ``None`` and writers return
``False``. Callers must handle that gracefully and the Settings UI shows
a "vault unavailable" state.
"""

from __future__ import annotations

from typing import Optional

try:
    import keyring  # type: ignore[import-not-found]
    import keyring.errors  # type: ignore[import-not-found]

    _KEYRING_AVAILABLE = True
except Exception:  # pragma: no cover - import-time fallback
    keyring = None  # type: ignore[assignment]
    _KEYRING_AVAILABLE = False


SERVICE = "ai-hub"

OPENAI_API_KEY = "openai_api_key"
ANTHROPIC_API_KEY = "anthropic_api_key"
GITHUB_TOKEN = "github_token"

KNOWN_KEYS = (OPENAI_API_KEY, ANTHROPIC_API_KEY, GITHUB_TOKEN)


def is_available() -> bool:
    """``True`` if a keyring backend is reachable.

    We probe by trying a no-op read on a non-existent key. ``keyring``
    raises :class:`NoKeyringError` when no backend is registered (e.g.
    headless Linux without ``secret-service``); we treat that as
    "vault disabled" so the rest of the app stays usable.
    """
    if not _KEYRING_AVAILABLE or keyring is None:
        return False
    try:
        keyring.get_password(SERVICE, "__probe__")
    except keyring.errors.NoKeyringError:  # type: ignore[attr-defined]
        return False
    except Exception:
        return False
    return True


def set_secret(name: str, value: str) -> bool:
    """Store ``value`` under ``name``. Returns ``True`` on success."""
    if not _KEYRING_AVAILABLE or keyring is None:
        return False
    if not value:
        return False
    try:
        keyring.set_password(SERVICE, name, value)
    except Exception:
        return False
    return True


def get_secret(name: str) -> Optional[str]:
    """Return the stored value for ``name`` or ``None`` if missing."""
    if not _KEYRING_AVAILABLE or keyring is None:
        return None
    try:
        value = keyring.get_password(SERVICE, name)
    except Exception:
        return None
    if value:
        return value
    return None


def delete_secret(name: str) -> bool:
    """Remove the stored value. Returns ``True`` if anything was removed."""
    if not _KEYRING_AVAILABLE or keyring is None:
        return False
    try:
        keyring.delete_password(SERVICE, name)
    except keyring.errors.PasswordDeleteError:  # type: ignore[attr-defined]
        return False
    except Exception:
        return False
    return True


def has_secret(name: str) -> bool:
    return get_secret(name) is not None
