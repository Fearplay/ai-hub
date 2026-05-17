"""Persistence for the AI Jobs section's saved search profiles.

Step 12 of the setup form lets the user save the current search setup
as a named template and rerun it later with one click. This module is
the single source of truth for that on-disk list - it owns the JSON
file format, the lock that serialises writes, and the schema used by
:mod:`src.sections.ai_jobs.tab_setup`.

Disk layout::

    ~/AI Hub/
        jobs_profiles.json    # JSON array, newest-first

Each entry has the shape (extra keys are kept verbatim so future
versions can add fields without losing older data)::

    {
      "id":          "01HXY...",       # opaque, stable per profile
      "name":        "QA Automation Remote Europe",
      "created":     "2026-05-16T10:24:11",
      "last_run":    "2026-05-16T11:02:43",   # optional, empty when never run
      "snapshot": {
        "keywords": "...",
        "profile_text": "...",
        "linkedin_url": "...",
        "location_preset": "eu",
        "location_custom": "",
        "tech_skills": "Python, FastAPI...",
        "additional_experience": "...",
        "seniority": "senior",
        "excluded_keywords": "...",
        "excluded_companies": "...",
        "excluded_locations": "...",
        "excluded_work_types": ["unpaid", "sales"],
        "selected_sources": ["recommended_for_region", "jobs_cz"],
        "custom_source_urls": "...",
        "job_age": "7d",
        "verify_active_links": true,
        "show_without_date": true,
        "work_mode": "remote",
        "contract_types": ["hpp", "ico"],
        "max_results": 10,
        "search_mode": "smart",
        "salary_min": 70000,
        "salary_currency": "CZK",
        "output_language": "auto"
      }
    }

Profile snapshots intentionally exclude the uploaded CV file (binary
blob), session-level results, and the activity badge - reloading a
profile only restores the *inputs*, the user still has to drag the CV
again to keep the on-disk JSON small.
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.services import logger as logger_service
from src.services import store


_LOCK = threading.Lock()

# Cap so a runaway "save" loop can't fill the file. Newest entries are
# kept, anything beyond this is dropped silently.
_MAX_PROFILES = 50


def profiles_path() -> Path:
    """Path to the JSON file on disk."""
    return store.root_dir() / "jobs_profiles.json"


def _ensure_parent() -> None:
    try:
        profiles_path().parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger_service.log_exception(
            "ai_jobs.profiles_store", "ensure_parent_failed", exc,
        )


def _read_raw() -> list[dict[str, Any]]:
    path = profiles_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger_service.log_exception(
            "ai_jobs.profiles_store", "read_failed", exc, path=str(path),
        )
        return []
    return data if isinstance(data, list) else []


def _write_raw(items: list[dict[str, Any]]) -> bool:
    path = profiles_path()
    _ensure_parent()
    try:
        path.write_text(
            json.dumps(items, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        logger_service.log_exception(
            "ai_jobs.profiles_store", "write_failed", exc, path=str(path),
        )
        return False
    return True


def _new_id() -> str:
    return uuid.uuid4().hex


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_profiles() -> list[dict[str, Any]]:
    """Return all saved profiles, newest-first.

    The on-disk file is the authoritative source; the in-memory mirror
    on :data:`STATE.saved_profiles` is repopulated from this call on
    every full refresh.
    """
    with _LOCK:
        return list(_read_raw())


def save_profile(*, name: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    """Append a new profile and return the stored record.

    Raises :class:`ValueError` when the name is blank.
    """
    name = (name or "").strip()
    if not name:
        raise ValueError("Profile name cannot be empty.")

    record = {
        "id": _new_id(),
        "name": name,
        "created": _now(),
        "last_run": "",
        "snapshot": snapshot or {},
    }
    with _LOCK:
        items = _read_raw()
        items.insert(0, record)
        items = items[:_MAX_PROFILES]
        if not _write_raw(items):
            raise OSError("Could not write jobs_profiles.json")

    logger_service.log_event(
        "INFO", "ai_jobs.profiles_store", "profile_saved",
        profile_id=record["id"], name=name,
    )
    return record


def delete_profile(profile_id: str) -> bool:
    """Delete a profile by id. Returns ``True`` when something changed."""
    if not profile_id:
        return False
    with _LOCK:
        items = _read_raw()
        kept = [item for item in items if item.get("id") != profile_id]
        if len(kept) == len(items):
            return False
        ok = _write_raw(kept)
    if ok:
        logger_service.log_event(
            "INFO", "ai_jobs.profiles_store", "profile_deleted",
            profile_id=profile_id,
        )
    return ok


def duplicate_profile(profile_id: str, *, suffix: str = " (copy)") -> Optional[dict[str, Any]]:
    """Clone a profile, append the suffix to the name and return it."""
    if not profile_id:
        return None
    with _LOCK:
        items = _read_raw()
        source = next((item for item in items if item.get("id") == profile_id), None)
        if source is None:
            return None
        clone = {
            "id": _new_id(),
            "name": (source.get("name") or "Profile") + suffix,
            "created": _now(),
            "last_run": "",
            "snapshot": dict(source.get("snapshot") or {}),
        }
        items.insert(0, clone)
        items = items[:_MAX_PROFILES]
        if not _write_raw(items):
            return None
    logger_service.log_event(
        "INFO", "ai_jobs.profiles_store", "profile_duplicated",
        source_id=profile_id, new_id=clone["id"],
    )
    return clone


def update_snapshot(profile_id: str, snapshot: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Replace the snapshot of an existing profile (used by Edit)."""
    if not profile_id:
        return None
    with _LOCK:
        items = _read_raw()
        target = next((item for item in items if item.get("id") == profile_id), None)
        if target is None:
            return None
        target["snapshot"] = snapshot or {}
        if not _write_raw(items):
            return None
    logger_service.log_event(
        "INFO", "ai_jobs.profiles_store", "profile_updated",
        profile_id=profile_id,
    )
    return target


def stamp_last_run(profile_id: str) -> None:
    """Bump the ``last_run`` timestamp - called after Run again succeeds."""
    if not profile_id:
        return
    with _LOCK:
        items = _read_raw()
        target = next((item for item in items if item.get("id") == profile_id), None)
        if target is None:
            return
        target["last_run"] = _now()
        _write_raw(items)


def find_profile(profile_id: str) -> Optional[dict[str, Any]]:
    """Return one profile by id (or ``None``)."""
    if not profile_id:
        return None
    with _LOCK:
        for item in _read_raw():
            if item.get("id") == profile_id:
                return item
    return None
