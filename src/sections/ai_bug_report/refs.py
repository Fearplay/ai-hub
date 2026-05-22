"""Cross-callback bridge for the AI Bug Report section.

The center column (``view.py``) and the right context panel
(``context.py``) live in two separate calls from
:meth:`src.app.AIHubApp.build`. They need to re-render in response to
events triggered inside the *other* one (the pipeline mutates
``STATE.activity`` from a worker thread; the context panel must repaint
the badge immediately).

Each build registers no-arg lambdas on this module-level :class:`Refs`
singleton; callers invoke whichever side they need. ``request_*``
helpers route through :func:`src.qt.runtime.dispatch` so the calls are
safe from background threads (per ``sections.mdc`` - never mutate Qt
widgets from a non-GUI thread).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from src.qt.runtime import dispatch as runtime_dispatch
from src.services import logger as logger_service


@dataclass
class BugReportRefs:
    rerender_main: Optional[Callable[[], None]] = None
    rerender_context: Optional[Callable[[], None]] = None

    def request_context_refresh(self) -> None:
        """Schedule the right-hand context panel to repaint on the GUI thread."""
        fn = self.rerender_context
        if not callable(fn):
            return

        def _safe() -> None:
            try:
                fn()
            except Exception as exc:
                logger_service.log_exception(
                    "ai_bug_report.refs", "request_context_refresh_failed", exc,
                )

        runtime_dispatch(_safe)

    def request_main_refresh(self) -> None:
        """Schedule the center column to rebuild on the GUI thread."""
        fn = self.rerender_main
        if not callable(fn):
            return

        def _safe() -> None:
            try:
                fn()
            except Exception as exc:
                logger_service.log_exception(
                    "ai_bug_report.refs", "request_main_refresh_failed", exc,
                )

        runtime_dispatch(_safe)


REFS = BugReportRefs()
