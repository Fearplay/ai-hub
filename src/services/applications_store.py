"""Job application tracker - persistent list at ``~/AI Hub/applications.json``.

Mirrors :mod:`src.services.profiles_store` (thread-safe JSON CRUD). Each
application captures the position the user is pursuing plus their progress:

* identity: ``title`` / ``company`` / ``url`` / ``source``
* pipeline ``status`` (see :data:`STATUSES`)
* a free-text ``deadline`` (kept as a string so locale formats just work)
* ``notes`` + ``next_step`` reminders
* ``documents`` - linked run folders / files (e.g. a tailored CV the AI
  Career section produced for this role)
* ``created_at`` / ``updated_at`` timestamps

The store is intentionally section-agnostic (a shared service): AI Job
Search writes to it from a result card, and any future section can read or
extend it without a cross-section import.
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.services import logger as logger_service
from src.services import store

_LOCK = threading.RLock()
APPLICATIONS_VERSION = 1


# Pipeline statuses (stored as ids; labels are localised per-section).
STATUS_FOUND = "found"
STATUS_CV_READY = "cv_ready"
STATUS_SENT = "sent"
STATUS_INTERVIEW = "interview"
STATUS_OFFER = "offer"
STATUS_REJECTED = "rejected"
STATUS_ACCEPTED = "accepted"
STATUS_ARCHIVED = "archived"

STATUSES = (
    STATUS_FOUND,
    STATUS_CV_READY,
    STATUS_SENT,
    STATUS_INTERVIEW,
    STATUS_OFFER,
    STATUS_REJECTED,
    STATUS_ACCEPTED,
    STATUS_ARCHIVED,
)


def path() -> Path:
    return store.root_dir() / "applications.json"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _normalize_url(url: str) -> str:
    return (url or "").strip().rstrip("/").lower()


def _read() -> dict:
    p = path()
    if not p.exists():
        return {"version": APPLICATIONS_VERSION, "applications": []}
    try:
        with _LOCK:
            data = json.loads(p.read_text(encoding="utf-8")) or {}
    except (OSError, json.JSONDecodeError) as exc:
        logger_service.log_exception("applications_store", "read_failed", exc)
        return {"version": APPLICATIONS_VERSION, "applications": []}
    if not isinstance(data.get("applications"), list):
        data["applications"] = []
    return data


def _write(data: dict) -> bool:
    p = path()
    try:
        with _LOCK:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except OSError as exc:
        logger_service.log_exception("applications_store", "write_failed", exc)
        return False


def list_applications() -> list[dict]:
    """Return all applications, newest first."""
    apps = _read().get("applications", [])
    return sorted(apps, key=lambda a: str(a.get("created_at") or ""), reverse=True)


def get_application(app_id: str) -> Optional[dict]:
    for app in _read().get("applications", []):
        if app.get("id") == app_id:
            return app
    return None


def find_by_url(url: str) -> Optional[dict]:
    target = _normalize_url(url)
    if not target:
        return None
    for app in _read().get("applications", []):
        if _normalize_url(app.get("url", "")) == target:
            return app
    return None


def add_application(
    *,
    title: str,
    company: str = "",
    url: str = "",
    source: str = "",
    status: str = STATUS_FOUND,
    deadline: str = "",
    notes: str = "",
    next_step: str = "",
    documents: Optional[list] = None,
) -> tuple[dict, bool]:
    """Add (or return existing) application. Deduped by URL.

    Returns ``(record, created)`` - ``created`` is ``False`` when an entry
    with the same URL already existed (we never duplicate a posting).
    """
    with _LOCK:
        existing = find_by_url(url) if url else None
        if existing is not None:
            logger_service.log_event(
                "INFO", "applications_store", "add_duplicate_skipped",
                app_id=existing.get("id"),
            )
            return existing, False

        record = {
            "id": uuid.uuid4().hex[:12],
            "title": (title or "").strip() or "Untitled role",
            "company": (company or "").strip(),
            "url": (url or "").strip(),
            "source": (source or "").strip(),
            "status": status if status in STATUSES else STATUS_FOUND,
            "deadline": (deadline or "").strip(),
            "notes": (notes or "").strip(),
            "next_step": (next_step or "").strip(),
            "documents": list(documents or []),
            "created_at": _now(),
            "updated_at": _now(),
        }
        data = _read()
        data.setdefault("applications", []).append(record)
        data["version"] = APPLICATIONS_VERSION
        _write(data)
    logger_service.log_event(
        "INFO", "applications_store", "add_done",
        app_id=record["id"], status=record["status"],
    )
    return record, True


def update_application(app_id: str, **fields) -> Optional[dict]:
    """Patch the given fields on an application; stamps ``updated_at``."""
    allowed = {
        "title", "company", "url", "source", "status",
        "deadline", "notes", "next_step", "documents",
    }
    with _LOCK:
        data = _read()
        target: Optional[dict] = None
        for app in data.get("applications", []):
            if app.get("id") == app_id:
                target = app
                break
        if target is None:
            logger_service.log_event(
                "WARNING", "applications_store", "update_missing", app_id=app_id,
            )
            return None
        for key, value in fields.items():
            if key not in allowed:
                continue
            if key == "status" and value not in STATUSES:
                continue
            target[key] = value
        target["updated_at"] = _now()
        _write(data)
    return target


def add_document(app_id: str, *, label: str, path_str: str) -> Optional[dict]:
    """Append a linked document (label + path) to an application."""
    if not path_str:
        return get_application(app_id)
    with _LOCK:
        app = get_application(app_id)
        if app is None:
            return None
        docs = list(app.get("documents") or [])
        docs.append({"label": (label or "").strip() or "Document", "path": path_str})
        return update_application(app_id, documents=docs)


def delete_application(app_id: str) -> bool:
    with _LOCK:
        data = _read()
        before = len(data.get("applications", []))
        data["applications"] = [
            a for a in data.get("applications", []) if a.get("id") != app_id
        ]
        if len(data["applications"]) == before:
            return False
        _write(data)
    logger_service.log_event("INFO", "applications_store", "delete_done", app_id=app_id)
    return True


def count() -> int:
    return len(_read().get("applications", []))
