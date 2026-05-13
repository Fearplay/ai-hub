"""Cross-thread refresh helpers for the AI Finance section.

Mirror of :mod:`src.sections.ai_career.refs`. Worker threads in
``pipeline.py`` mutate :data:`src.sections.ai_finance.state.STATE` and
then need the UI to repaint - both the right-hand context panel
(``rerender_context``) and, occasionally, the entire section tree
(``dispatch`` plus :func:`src.app.request_section_refresh`).

Always go through these helpers so cross-thread access is funnelled
through :mod:`src.qt.runtime` (queued signal -> GUI thread).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from src.qt.runtime import dispatch as runtime_dispatch
from src.services import logger as logger_service


@dataclass
class FinanceRefs:
    rerender_context: Optional[Callable[[], None]] = None
    page: Optional[Any] = None

    def dispatch(self, callback: Callable[[], None]) -> None:
        try:
            runtime_dispatch(callback)
        except Exception as exc:
            logger_service.log_exception(
                "ai_finance.refs", "dispatch_failed", exc,
            )

    def request_context_refresh(self) -> None:
        callback = self.rerender_context
        if callback is None:
            return
        self.dispatch(callback)


REFS = FinanceRefs()


def safe(callback: Optional[Callable[[], None]]) -> None:
    if callback is None:
        return
    try:
        callback()
    except Exception as exc:
        logger_service.log_exception(
            "ai_finance.refs", "safe_callback_failed", exc,
        )
