"""Shared career profile - the CV/LinkedIn/GitHub the user uploads once.

The "My Profile" section parses the user's CV (+ optional LinkedIn export,
GitHub, notes) into one structured profile and persists it here, at
``~/AI Hub/career_profile.json``. AI Career, AI Job Search and AI LinkedIn
then read from this store instead of asking the user to upload the same
documents again.

This module is persistence-only (it mirrors ``settings_store`` /
``profiles_store`` and never calls an AI provider). The structured
extraction lives in ``src/sections/my_profile/pipeline.py`` - an AI
section. Sections must not import each other, but they may all import this
shared service.

On-disk shape (``career_profile.json``)::

    {
      "version": 1,
      "updated_at": "2026-05-28 21:00",
      "demo": false,
      "sources": {
        "resume":   {path, name, ext, size_bytes, text} | null,
        "linkedin": {path, name, ext, size_bytes, text} | null,
        "github_url": "...",
        "github_username": "...",
        "github_summary": "...",
        "notes": "..."
      },
      "profile": { ...unified CAREER_PROFILE_SCHEMA result... }
    }
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.services import logger as logger_service
from src.services import store


_LOCK = threading.RLock()
PROFILE_VERSION = 1


def path() -> Path:
    return store.root_dir() / "career_profile.json"


def load() -> dict:
    """Return the persisted profile dict, or ``{}`` when none exists."""
    p = path()
    if not p.exists():
        return {}
    try:
        with _LOCK:
            return json.loads(p.read_text(encoding="utf-8")) or {}
    except (OSError, json.JSONDecodeError) as exc:
        logger_service.log_exception("career_profile_store", "load_failed", exc)
        return {}


def save(data: dict) -> bool:
    """Persist ``data`` (stamps ``version`` + ``updated_at``)."""
    payload = dict(data or {})
    payload.setdefault("version", PROFILE_VERSION)
    payload["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    p = path()
    try:
        with _LOCK:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        logger_service.log_event(
            "INFO", "career_profile_store", "save_done",
            has_profile=bool(payload.get("profile")),
            demo=bool(payload.get("demo")),
        )
        return True
    except OSError as exc:
        logger_service.log_exception("career_profile_store", "save_failed", exc)
        return False


def clear() -> bool:
    p = path()
    try:
        with _LOCK:
            if p.exists():
                p.unlink()
        logger_service.log_event("INFO", "career_profile_store", "clear_done")
        return True
    except OSError as exc:
        logger_service.log_exception("career_profile_store", "clear_failed", exc)
        return False


def has_profile() -> bool:
    """True when a structured profile or at least a parsed resume exists."""
    data = load()
    if not data:
        return False
    profile = data.get("profile")
    if isinstance(profile, dict) and profile:
        return True
    resume = (data.get("sources") or {}).get("resume") or {}
    return bool(isinstance(resume, dict) and resume.get("text"))


def get_profile() -> Optional[dict]:
    data = load()
    profile = data.get("profile")
    return profile if isinstance(profile, dict) and profile else None


def get_sources() -> dict:
    data = load()
    sources = data.get("sources")
    return sources if isinstance(sources, dict) else {}


def get_meta() -> dict:
    data = load()
    return {
        "updated_at": str(data.get("updated_at") or ""),
        "demo": bool(data.get("demo", False)),
    }


def resume_source() -> Optional[dict]:
    src = get_sources().get("resume")
    if isinstance(src, dict) and src.get("text"):
        return src
    return None


def linkedin_source() -> Optional[dict]:
    src = get_sources().get("linkedin")
    if isinstance(src, dict) and src.get("text"):
        return src
    return None


def github_url() -> str:
    return str(get_sources().get("github_url") or "").strip()


def github_summary() -> str:
    return str(get_sources().get("github_summary") or "")


def notes() -> str:
    return str(get_sources().get("notes") or "").strip()


def display_name() -> str:
    return str((get_profile() or {}).get("full_name") or "").strip()


def headline() -> str:
    return str((get_profile() or {}).get("headline") or "").strip()
