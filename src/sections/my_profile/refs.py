"""Cross-thread refresh helpers for My Profile.

The extraction runs on a worker thread; it mutates ``STATE`` and needs the
GUI to repaint. We route repaints through ``src.qt.runtime.dispatch`` so
they always land on the GUI thread.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from src.qt.runtime import dispatch as runtime_dispatch
from src.services import logger as logger_service


@dataclass
class MyProfileRefs:
    rerender_context: Optional[Callable[[], None]] = None

    def dispatch(self, callback: Callable[[], None]) -> None:
        try:
            runtime_dispatch(callback)
        except Exception as exc:
            logger_service.log_exception("my_profile.refs", "dispatch_failed", exc)

    def request_context_refresh(self) -> None:
        if self.rerender_context is None:
            return
        self.dispatch(self.rerender_context)


REFS = MyProfileRefs()
