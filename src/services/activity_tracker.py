"""Per-session activity status shared across sections.

Mirrors :mod:`src.services.cost_tracker`: a single in-memory singleton
that the left-sidebar status block subscribes to so it can show what the
active section is currently doing ("Ready" / "Working..." / "Error").

Why a global tracker instead of the old per-section right panel? The
right context panel was removed; session cost + Activity now live in the
left navigation sidebar. Cost was already global (:data:`COST`); this
gives Activity the same treatment. Sections push their pipeline status
here through the same chokepoints that already update
``STATE.activity`` (each section's ``_set_activity`` helper /
``REFS.request_context_refresh``), so the wiring stays in one place per
section.

The sidebar maps :attr:`ActivityTracker.category` onto a dot colour and
shows a localized label. We deliberately collapse every per-section
stage name ("scraping", "analyzing", "scoring", ...) onto three coarse
categories so the shared block stays section-agnostic and never has to
know one section's string table. Use :func:`category_for` to do that
mapping from a raw ``STATE.activity`` value.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable


# Coarse status categories that drive the sidebar dot colour. Every
# per-section ``STATE.activity`` value collapses onto one of these via
# :func:`category_for`.
CATEGORY_READY = "ready"
CATEGORY_BUSY = "busy"
CATEGORY_ERROR = "error"


# Raw ``STATE.activity`` values (lower-cased) that mean "nothing is
# running". Everything not listed here - and not an error - is treated
# as "busy" so any new pipeline stage shows the working indicator
# without needing to be enumerated.
_READY_VALUES = {"", "ready", "idle", "done", "complete", "completed"}
_ERROR_VALUES = {"error", "failed", "failure"}


def category_for(value: str) -> str:
    """Collapse a raw per-section activity value onto a coarse category."""
    token = (value or "").strip().lower()
    if token in _ERROR_VALUES:
        return CATEGORY_ERROR
    if token in _READY_VALUES:
        return CATEGORY_READY
    return CATEGORY_BUSY


@dataclass
class ActivityTracker:
    category: str = CATEGORY_READY
    label: str = ""
    listeners: list[Callable[[], None]] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def set(self, category: str, label: str = "") -> None:
        """Publish a new activity status and notify listeners on change.

        ``label`` is an optional already-localized override; when empty
        the sidebar falls back to a generic per-category string. Callers
        from worker threads are fine - listeners are expected to hop to
        the GUI thread themselves (the sidebar uses ``runtime.dispatch``).
        """
        with self._lock:
            changed = category != self.category or label != self.label
            self.category = category
            self.label = label
            listeners = list(self.listeners) if changed else []
        for listener in listeners:
            try:
                listener()
            except Exception:
                # A broken listener must never break the pipeline that
                # is reporting progress. The sidebar guards its own
                # widget liveness; anything else is best-effort.
                pass

    def set_from_value(self, value: str, label: str = "") -> None:
        """Convenience: publish using a raw ``STATE.activity`` value."""
        self.set(category_for(value), label)

    def reset(self) -> None:
        self.set(CATEGORY_READY, "")

    def subscribe(self, listener: Callable[[], None]) -> Callable[[], None]:
        with self._lock:
            self.listeners.append(listener)

        def _unsub() -> None:
            with self._lock:
                if listener in self.listeners:
                    self.listeners.remove(listener)

        return _unsub


ACTIVITY = ActivityTracker()
