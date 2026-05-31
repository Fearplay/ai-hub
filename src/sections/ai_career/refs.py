"""Cross-thread refresh helpers for AI Career (PySide6 port).

Worker threads in `pipeline.py` mutate `STATE` and need the UI to repaint.
We route those repaints through `src.qt.runtime.dispatch`, which uses
`Qt.QueuedConnection` to run on the GUI thread.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from src.qt.lifecycle import CoalescedRefresh
from src.qt.runtime import dispatch as runtime_dispatch
from src.services import logger as logger_service
from src.services.activity_tracker import ACTIVITY
from src.sections.ai_career.state import STATE


@dataclass
class CareerRefs:
    rerender_context: Optional[Callable[[], None]] = None
    page: Optional[Any] = None
    _refresh: CoalescedRefresh = field(default_factory=CoalescedRefresh)

    def dispatch(self, callback: Callable[[], None]) -> None:
        try:
            runtime_dispatch(callback)
        except Exception as exc:
            logger_service.log_exception(
                "ai_career.refs", "dispatch_failed", exc,
            )

    def request_context_refresh(self) -> None:
        # The right context panel was removed; this is now the chokepoint
        # that feeds the left-sidebar Activity indicator. Pipeline workers
        # and view handlers both call this after mutating STATE.activity.
        ACTIVITY.set_from_value(STATE.activity)
        if self.rerender_context is None:
            return
        self._refresh.schedule(lambda: self.rerender_context)


REFS = CareerRefs()


def safe(callback: Optional[Callable[[], None]]) -> None:
    if callback is None:
        return
    try:
        callback()
    except Exception as exc:
        logger_service.log_exception(
            "ai_career.refs", "safe_callback_failed", exc,
        )
