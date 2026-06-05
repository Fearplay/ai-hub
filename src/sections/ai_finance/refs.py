"""Cross-thread refresh helpers for the AI Finance section.

Mirror of :mod:`src.sections.ai_cv.refs`. Worker threads in
``pipeline.py`` mutate :data:`src.sections.ai_finance.state.STATE` and
then need the UI to repaint - both the right-hand context panel
(``rerender_context``) and, occasionally, the entire section tree
(``dispatch`` plus :func:`src.app.request_section_refresh`).

Always go through these helpers so cross-thread access is funnelled
through :mod:`src.qt.runtime` (queued signal -> GUI thread).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from src.qt.lifecycle import CoalescedRefresh
from src.qt.runtime import dispatch as runtime_dispatch
from src.services import logger as logger_service
from src.services.activity_tracker import ACTIVITY
from src.sections.ai_finance.state import STATE


@dataclass
class FinanceRefs:
    rerender_context: Optional[Callable[[], None]] = None
    page: Optional[Any] = None
    _refresh: CoalescedRefresh = field(default_factory=CoalescedRefresh)

    def dispatch(self, callback: Callable[[], None]) -> None:
        try:
            runtime_dispatch(callback)
        except Exception as exc:
            logger_service.log_exception(
                "ai_finance.refs", "dispatch_failed", exc,
            )

    def request_context_refresh(self) -> None:
        # The right context panel was removed; this feeds the left-sidebar
        # Activity indicator from any thread.
        ACTIVITY.set_from_value(STATE.activity)
        if self.rerender_context is None:
            return
        self._refresh.schedule(lambda: self.rerender_context)


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
