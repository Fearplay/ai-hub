"""Cross-thread refresh helpers for AI Career (PySide6 port).

Worker threads in `pipeline.py` mutate `STATE` and need the UI to repaint.
We route those repaints through `src.qt.runtime.dispatch`, which uses
`Qt.QueuedConnection` to run on the GUI thread.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from src.qt.runtime import dispatch as runtime_dispatch
from src.services import logger as logger_service


@dataclass
class CareerRefs:
    rerender_context: Optional[Callable[[], None]] = None
    page: Optional[Any] = None

    def dispatch(self, callback: Callable[[], None]) -> None:
        try:
            runtime_dispatch(callback)
        except Exception as exc:
            logger_service.log_exception(
                "ai_career.refs", "dispatch_failed", exc,
            )

    def request_context_refresh(self) -> None:
        callback = self.rerender_context
        if callback is None:
            return
        self.dispatch(callback)


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
