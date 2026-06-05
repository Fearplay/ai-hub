"""Cross-thread refresh + UI dispatcher for AI Hub.

Workers in :mod:`src.sections.<key>.pipeline` and friends run on
daemon threads (so the UI stays responsive while LLM calls / scrapes /
exports are in flight). When they mutate ``STATE`` and want the UI to
repaint, calling Qt mutators from the worker thread is unsafe - Qt
forbids touching widgets from any thread other than the one that
created them.

The dispatcher solves that by routing callbacks through a single
``QObject`` whose ``run`` signal is connected to its own slot via
``Qt.QueuedConnection``. Emitting the signal from any thread queues the
callback onto the GUI event loop, which runs it on the right thread.

Public API:

* :func:`dispatch(callback)` - run ``callback`` on the GUI thread.
  Falls back to a synchronous call when no ``QApplication`` exists yet
  (e.g. during section auto-discovery).
* :func:`set_main_window(window)` / :func:`get_main_window()` - the
  app shell registers the live ``QMainWindow`` here so sections can
  parent dialogs / file pickers without piping the window through
  every callback.

This is the Qt analogue of the old ``REFS.dispatch`` plumbing in
:mod:`src.sections.ai_cv.refs` and friends. The per-section
``refs.py`` modules now route through this dispatcher rather than
walking ``page.session.connection.loop``.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QApplication, QMainWindow

from src.services import logger as logger_service


_DISPATCHER: Optional["UIDispatcher"] = None
_DISPATCHER_LOCK = threading.Lock()
_MAIN_WINDOW: Optional[QMainWindow] = None


class UIDispatcher(QObject):
    """Thread-safe relay for "run this on the GUI thread" requests.

    The signal is queued (``Qt.QueuedConnection``) so emitting it from
    a worker thread parks the callable on the GUI event loop instead
    of running it inline. Any exception raised by the callback is
    routed through :func:`logger_service.log_exception` so silent
    failures show up in **Settings -> Debug logs**.
    """

    run = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.run.connect(self._on_run, Qt.ConnectionType.QueuedConnection)

    def _on_run(self, callback: Callable[[], None]) -> None:
        try:
            callback()
        except Exception as exc:
            logger_service.log_exception(
                "qt.runtime", "dispatcher_callback_failed", exc
            )


def _ensure_dispatcher() -> Optional[UIDispatcher]:
    global _DISPATCHER
    with _DISPATCHER_LOCK:
        if _DISPATCHER is not None:
            return _DISPATCHER
        app = QApplication.instance()
        if app is None:
            return None
        _DISPATCHER = UIDispatcher()
        # The dispatcher must live on the GUI thread. ``QApplication``
        # is always created there, so re-parenting to the application
        # object guarantees ``_on_run`` executes on the right thread.
        _DISPATCHER.moveToThread(app.thread())
        return _DISPATCHER


def dispatch(callback: Callable[[], None]) -> None:
    """Queue ``callback`` to run on the GUI thread.

    Worker threads should always go through this helper instead of
    touching widgets directly. UI-thread callers can still use it - it
    does the right thing both ways.

    Falls back to a synchronous call when ``QApplication`` is not yet
    alive. This matches the safety net the old Flet ``REFS.dispatch``
    had and keeps section-level auto-discovery (which imports modules
    before the app boots) from crashing.
    """
    if not callable(callback):
        return
    dispatcher = _ensure_dispatcher()
    if dispatcher is None:
        try:
            callback()
        except Exception as exc:
            logger_service.log_exception(
                "qt.runtime", "dispatch_no_app_callback_failed", exc
            )
        return
    dispatcher.run.emit(callback)


def set_main_window(window: QMainWindow) -> None:
    global _MAIN_WINDOW
    _MAIN_WINDOW = window


def get_main_window() -> Optional[QMainWindow]:
    return _MAIN_WINDOW


__all__ = [
    "UIDispatcher",
    "dispatch",
    "get_main_window",
    "set_main_window",
]
