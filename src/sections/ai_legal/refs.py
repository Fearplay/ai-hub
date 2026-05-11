"""Cross-callback bridge for the AI Legal section.

The center column (``view.py``) and the right context panel
(``context.py``) live in two separate calls from
:meth:`src.app.AIHubApp.build`. They both want to re-render in response
to events triggered inside the *other* one - e.g. clicking *Show
detailed analysis* in the right panel must switch the center column to
the Analysis tab; dropping a PDF onto the drop zone in the right panel
must update the chat header (which mentions the file name) on the
left.

To avoid threading an awkward "controller" through every helper, each
build registers a no-arg ``rerender`` lambda on this module-level
:class:`LegalRefs` singleton. Callbacks then just invoke whichever side
they need to refresh. Re-binding on every rebuild keeps the closures
pointing at the latest theme / lang.

``request_context_refresh`` is the thread-safe variant: workers in
:mod:`src.sections.ai_legal.pipeline` queue it through
:func:`src.qt.runtime.dispatch` so the GUI updates happen on the main
thread regardless of which thread mutated ``STATE``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from src.qt.runtime import dispatch as runtime_dispatch
from src.services import logger as logger_service


@dataclass
class LegalRefs:
    rerender_main: Optional[Callable[[], None]] = None
    rerender_tab_body: Optional[Callable[[], None]] = None
    rerender_context: Optional[Callable[[], None]] = field(default=None)

    def request_context_refresh(self) -> None:
        """Schedule the right-hand context panel to repaint on the GUI thread.

        Pipeline workers call this from background threads after
        mutating ``STATE.activity`` / ``STATE.uploaded_file`` /
        ``STATE.last_error`` so the badge, document chip and error
        labels reflect the new values on the next event loop tick.
        """
        fn = self.rerender_context
        if not callable(fn):
            return

        def _safe() -> None:
            try:
                fn()
            except Exception as exc:
                logger_service.log_exception(
                    "ai_legal.refs", "request_context_refresh_failed", exc,
                )

        runtime_dispatch(_safe)

    def request_tab_body_refresh(self) -> None:
        """Schedule the active tab body to rebuild on the GUI thread."""
        fn = self.rerender_tab_body
        if not callable(fn):
            return

        def _safe() -> None:
            try:
                fn()
            except Exception as exc:
                logger_service.log_exception(
                    "ai_legal.refs", "request_tab_body_refresh_failed", exc,
                )

        runtime_dispatch(_safe)


REFS = LegalRefs()
