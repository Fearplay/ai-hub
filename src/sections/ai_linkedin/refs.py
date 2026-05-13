"""Cross-thread refresh helpers for AI LinkedIn (PySide6 port).

The section talks to LLMs / scrapes / writes files on daemon threads.
Once those workers mutate :data:`STATE`, the UI has to repaint, but
``QWidget.update()`` is not safe to call from a non-GUI thread. The
:class:`src.qt.runtime.UIDispatcher` solves that: we pass the callback
through ``Qt.QueuedConnection`` so it lands on the GUI thread within the
next event loop tick.

UI-thread callers can keep calling ``REFS.request_context_refresh()``
or ``REFS.dispatch(callback)`` directly; worker threads use the same
API and the underlying dispatcher routes the call to the GUI thread.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from src.qt.runtime import dispatch as runtime_dispatch
from src.services import logger as logger_service


@dataclass
class LinkedInRefs:
    """Cross-cutting handles shared between view + worker threads."""

    rerender_context: Optional[Callable[[], None]] = None

    def dispatch(self, callback: Callable[[], None]) -> None:
        """Run ``callback`` on the GUI thread."""
        try:
            runtime_dispatch(callback)
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.refs", "dispatch_failed", exc,
            )

    def request_context_refresh(self) -> None:
        """Request a right-hand context panel refresh from any thread."""
        callback = self.rerender_context
        if callback is None:
            return
        self.dispatch(callback)


REFS = LinkedInRefs()


def safe(callback: Optional[Callable[[], None]]) -> None:
    """Call ``callback`` if non-None, logging any exception."""
    if callback is None:
        return
    try:
        callback()
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.refs", "safe_callback_failed", exc,
        )
