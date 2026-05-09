"""Non-secret user preferences (provider, model, demo mode, …).

Lives next to :mod:`src.services.secrets` but stores values in plain JSON
under ``~/AI Hub/settings.json``. API keys never go here - those use the
OS keystore via :mod:`src.services.secrets`.

Why a JSON file and not :func:`flet.Page.client_storage`? Multiple sections
read these values from non-UI threads (pipeline calls); the JSON file is
cheap, sync, and works without an active page handle.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any


_LOCK = threading.Lock()


PROVIDER_OPENAI = "openai"
PROVIDER_ANTHROPIC = "anthropic"

DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5"

OPENAI_MODELS = (
    "gpt-5.4-mini",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-5.4",
    "gpt-5.5",
)
ANTHROPIC_MODELS = (
    "claude-haiku-4-5",
    "claude-sonnet-4-6",
    "claude-opus-4-7",
)


def _settings_path() -> Path:
    return Path.home() / "AI Hub" / "settings.json"


def _read() -> dict[str, Any]:
    path = _settings_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write(data: dict[str, Any]) -> bool:
    path = _settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        return False
    return True


def get(key: str, default: Any = None) -> Any:
    with _LOCK:
        return _read().get(key, default)


def set_value(key: str, value: Any) -> bool:
    with _LOCK:
        data = _read()
        data[key] = value
        return _write(data)


def get_provider() -> str:
    value = get("provider", PROVIDER_OPENAI)
    if value not in (PROVIDER_OPENAI, PROVIDER_ANTHROPIC):
        return PROVIDER_OPENAI
    return value


def set_provider(provider: str) -> bool:
    if provider not in (PROVIDER_OPENAI, PROVIDER_ANTHROPIC):
        return False
    return set_value("provider", provider)


def get_model(provider: str | None = None) -> str:
    p = provider or get_provider()
    if p == PROVIDER_ANTHROPIC:
        return get("anthropic_model", DEFAULT_ANTHROPIC_MODEL) or DEFAULT_ANTHROPIC_MODEL
    return get("openai_model", DEFAULT_OPENAI_MODEL) or DEFAULT_OPENAI_MODEL


def set_model(provider: str, model: str) -> bool:
    model = (model or "").strip()
    if not model:
        return False
    key = "anthropic_model" if provider == PROVIDER_ANTHROPIC else "openai_model"
    return set_value(key, model)


def get_demo_default() -> bool:
    return bool(get("demo_default", False))


def set_demo_default(value: bool) -> bool:
    return set_value("demo_default", bool(value))


def get_ask_followups() -> bool:
    # Default ON: the clarifying-questions step typically lifts the
    # match-analysis quality enough to be worth the extra LLM call. Users
    # who explicitly toggled it off keep their saved choice (the JSON
    # value wins over the default below).
    return bool(get("ask_followups", True))


def set_ask_followups(value: bool) -> bool:
    return set_value("ask_followups", bool(value))


# Theme + UI-language preferences. These survive app restarts so the
# user doesn't have to flip the toggles every launch. Stored in the
# same JSON as the provider / model settings.
_THEME_MODES = ("dark", "light")
_LANG_CODES = ("en", "cs")


def get_theme_mode() -> str:
    value = get("theme_mode", "dark")
    if value not in _THEME_MODES:
        return "dark"
    return value


def set_theme_mode(value: str) -> bool:
    if value not in _THEME_MODES:
        return False
    return set_value("theme_mode", value)


def get_lang() -> str:
    value = get("lang", "en")
    if value not in _LANG_CODES:
        return "en"
    return value


def set_lang(value: str) -> bool:
    if value not in _LANG_CODES:
        return False
    return set_value("lang", value)


def settings_path_str() -> str:
    return str(_settings_path())


def keystore_label() -> str:
    """Return a friendly name for the OS-level secret backend."""
    if os.name == "nt":
        return "Windows Credential Manager"
    if os.name == "posix":
        if "darwin" in os.sys.platform:  # type: ignore[attr-defined]
            return "macOS Keychain"
        return "Secret Service / KWallet"
    return "OS keystore"
