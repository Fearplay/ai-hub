"""Widget lifecycle helpers.

PySide6 widgets and layouts can be destroyed on the C++ side while the
Python wrapper stays alive (typical scenario: ``QObject.deleteLater()``
is called when the user switches sections, but ``runtime.dispatch``
already queued a callback that captures the doomed widget). When the
queued callback runs on the next event-loop tick, it crashes with
``RuntimeError: Internal C++ object (...) already deleted.``

This module provides:

* :func:`is_widget_alive` - safe ``shiboken6.isValid`` wrapper used as
  a guard at the top of ``_render`` / ``_clear`` closures.
* :func:`on_destroyed` - connect a one-shot Python callback to a
  widget's ``destroyed`` signal so each section's ``build_context``
  can null out ``REFS.rerender_context`` and unsubscribe from global
  pub/sub the moment the panel is gone.

See [sections.mdc](mdc:.cursor/rules/sections.mdc) "Cross-thread UI
refresh" - this is the second half of that contract: the dispatcher
queues callbacks safely; this helper makes sure they bail out when
their target is dead.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

import shiboken6
from PySide6.QtWidgets import QWidget

from src.qt.runtime import dispatch as runtime_dispatch
from src.services import logger as logger_service


def is_widget_alive(widget: Optional[QWidget]) -> bool:
    """Return ``True`` when ``widget``'s underlying C++ object is alive.

    Safe to call with ``None`` (returns ``False``) and with widgets
    whose Python wrapper exists but whose ``QObject`` has already been
    destroyed via ``deleteLater()`` (returns ``False``).
    """
    if widget is None:
        return False
    try:
        return bool(shiboken6.isValid(widget))
    except Exception:
        return False


def on_destroyed(widget: QWidget, callback: Callable[[], None]) -> None:
    """Run ``callback`` once when ``widget``'s C++ side is destroyed.

    The wrapper swallows exceptions through the standard logger so a
    broken cleanup never propagates back into Qt's destroyed signal
    chain (which would log a generic Qt warning instead of our
    structured event).
    """

    def _safe(_obj: object = None) -> None:
        try:
            callback()
        except Exception as exc:
            logger_service.log_exception(
                "qt.lifecycle", "destroyed_callback_failed", exc,
            )

    widget.destroyed.connect(_safe)


class CoalescedRefresh:
    """Coalesce high-frequency refresh requests into one queued render.

    AI Jobs fires ``request_context_refresh`` 50+ times during a single
    search run (every ``_set_activity``, every per-position scoring
    finish, every COST listener tick). Without coalescing each one
    queues a separate ``runtime.dispatch`` callback, the GUI thread
    repaints repeatedly and the debug log fills with redundant
    rerender_context errors when something else races.

    The contract: while a refresh is in flight, drop subsequent calls
    because the queued render will read fresh ``STATE`` anyway.

    Usage in a section's ``refs.py``::

        @dataclass
        class JobsRefs:
            rerender_context: Optional[Callable[[], None]] = None
            _refresh: CoalescedRefresh = field(default_factory=CoalescedRefresh)

            def request_context_refresh(self) -> None:
                self._refresh.schedule(lambda: self.rerender_context)

    Pass a *callback provider* (zero-arg callable returning the actual
    callback or ``None``) so the coalescer always reads the latest
    bound render closure - if the user navigates between sections
    while a refresh is queued, the new section's binding wins.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending = False

    def schedule(
        self, callback_provider: Callable[[], Optional[Callable[[], None]]]
    ) -> None:
        with self._lock:
            if self._pending:
                return
            self._pending = True

        def _run() -> None:
            try:
                cb = callback_provider()
                if callable(cb):
                    cb()
            finally:
                with self._lock:
                    self._pending = False

        runtime_dispatch(_run)


__all__ = ["CoalescedRefresh", "is_widget_alive", "on_destroyed"]
