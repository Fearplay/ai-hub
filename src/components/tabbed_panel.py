"""Tab bar + swappable content holder.

Sections used to render ``[tab_bar(...), <chat content>]`` directly. With
clickable tabs each section now hands ``tabbed_panel`` one ``ft.Control``
per tab; the helper owns the state and swaps the content area in place
when the tab changes.
"""

from __future__ import annotations

from typing import Sequence

import flet as ft

from src.components.tab_bar import tab_bar
from src.services import logger as logger_service
from src.theme import Theme


def tabbed_panel(
    theme: Theme,
    *,
    tabs: Sequence[str],
    panels: Sequence[ft.Control],
    initial_index: int = 0,
) -> ft.Column:
    if len(panels) != len(tabs):
        raise ValueError(
            f"tabbed_panel: got {len(tabs)} tab labels but {len(panels)} panels"
        )

    holder = ft.Container(content=panels[initial_index], expand=True)

    def on_change(idx: int) -> None:
        try:
            holder.content = panels[idx]
        except Exception as exc:
            logger_service.log_exception(
                "tabbed_panel", "on_change_set_content_failed", exc,
                idx=idx, total_panels=len(panels),
            )
            return
        if not logger_service.try_update(holder):
            logger_service.log_event(
                "ERROR", "tabbed_panel", "on_change_update_failed",
                idx=idx,
            )

    bar = tab_bar(
        theme,
        tabs=tabs,
        active_index=initial_index,
        on_change=on_change,
    )

    return ft.Column(
        controls=[bar, holder],
        spacing=0,
        expand=True,
        tight=True,
    )
