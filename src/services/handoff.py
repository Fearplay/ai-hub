"""One-shot cross-section handoff slots.

Sections are isolated (no cross-imports), but the user flow wants to jump
from a Job Search result straight into AI Career ("tailor my CV to this
job") or AI LinkedIn ("tune my profile for this role") with the job's
details carried along. This module is a tiny thread-safe mailbox keyed by
the *target* section key:

* the source section calls :func:`set_payload(target_key, payload)` then
  navigates with ``window.set_section(target_key)``;
* the target section calls :func:`take(target_key)` once at the top of its
  ``build_view`` and pre-fills its inputs from the returned payload.

``take`` pops the slot so the payload is consumed exactly once (a later
manual visit to the section starts clean). Payloads are plain ``dict``s so
no section type leaks across the boundary.
"""

from __future__ import annotations

import threading
from typing import Optional

from src.services import logger as logger_service

_LOCK = threading.RLock()
_SLOTS: dict[str, dict] = {}


def set_payload(target_key: str, payload: dict) -> None:
    """Stash ``payload`` for the next time ``target_key`` builds its view."""
    if not target_key:
        return
    with _LOCK:
        _SLOTS[target_key] = dict(payload or {})
    logger_service.log_event(
        "INFO", "handoff", "set_payload",
        target=target_key, keys=sorted((payload or {}).keys()),
    )


def take(target_key: str) -> Optional[dict]:
    """Pop and return the pending payload for ``target_key`` (or ``None``)."""
    with _LOCK:
        payload = _SLOTS.pop(target_key, None)
    if payload is not None:
        logger_service.log_event(
            "INFO", "handoff", "take", target=target_key, keys=sorted(payload.keys()),
        )
    return payload


def peek(target_key: str) -> Optional[dict]:
    """Return the pending payload without consuming it."""
    with _LOCK:
        payload = _SLOTS.get(target_key)
    return dict(payload) if payload is not None else None


def has_pending(target_key: str) -> bool:
    with _LOCK:
        return target_key in _SLOTS


def clear(target_key: str) -> None:
    with _LOCK:
        _SLOTS.pop(target_key, None)
