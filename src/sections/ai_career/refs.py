"""Cross-tab rerender hooks for AI Career.

The view + tabs + context panel each register a callback on this singleton
when they mount. Handlers in pipeline / setup tabs can then call the
appropriate hook to repaint without reaching into Flet internals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class CareerRefs:
    rerender_main: Optional[Callable[[], None]] = None
    rerender_tab_body: Optional[Callable[[], None]] = None
    rerender_context: Optional[Callable[[], None]] = None
    rerender_documents: Optional[Callable[[], None]] = None


REFS = CareerRefs()


def safe(callback: Optional[Callable[[], None]]) -> None:
    if callback is None:
        return
    try:
        callback()
    except Exception:
        pass
