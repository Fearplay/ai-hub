"""Tab bar + swappable content holder.

Sections hand ``tabbed_panel`` one ``QWidget`` per tab; the helper owns
the state and swaps the content area in place via a ``QStackedLayout``
when the tab changes.
"""

from __future__ import annotations

from typing import Sequence

from PySide6.QtWidgets import QFrame, QStackedLayout, QWidget

from src.components.tab_bar import tab_bar
from src.qt.widgets import vbox
from src.services import logger as logger_service
from src.theme import Theme


def tabbed_panel(
    theme: Theme,
    *,
    tabs: Sequence[str],
    panels: Sequence[QWidget],
    initial_index: int = 0,
) -> QFrame:
    if len(panels) != len(tabs):
        raise ValueError(
            f"tabbed_panel: got {len(tabs)} tab labels but {len(panels)} panels"
        )

    container = QFrame()
    container.setStyleSheet("background: transparent;")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    body = QFrame()
    body.setStyleSheet("background: transparent;")
    stack = QStackedLayout(body)
    stack.setContentsMargins(0, 0, 0, 0)
    for panel in panels:
        stack.addWidget(panel)
    stack.setCurrentIndex(initial_index)

    def _on_change(idx: int) -> None:
        try:
            stack.setCurrentIndex(idx)
        except Exception as exc:
            logger_service.log_exception(
                "tabbed_panel", "on_change_set_index_failed", exc,
                idx=idx, total_panels=len(panels),
            )

    bar = tab_bar(theme, tabs=tabs, active_index=initial_index, on_change=_on_change)
    layout.addWidget(bar)
    layout.addWidget(body, 1)

    return container
