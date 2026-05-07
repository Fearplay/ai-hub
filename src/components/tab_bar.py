"""Generic tab bar under the header.

The component is purely visual by default - it draws a row of labels and
underlines the one whose index matches ``active_index``. Sections that
need real navigation pass ``on_change``; clicking any tab then invokes
the callback with the clicked index. Sections that don't pass it (career,
marketing) still get a static, decorative tab bar.
"""

from __future__ import annotations

from typing import Callable, Optional, Sequence

import flet as ft

from src.theme import Theme


def _tab(
    theme: Theme,
    label: str,
    *,
    active: bool,
    on_click: Optional[Callable[[ft.ControlEvent], None]] = None,
) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Text(
                        label,
                        color=theme.text if active else theme.text_muted,
                        size=14,
                        weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_500,
                    ),
                    padding=ft.padding.only(bottom=10),
                ),
                ft.Container(
                    height=2,
                    bgcolor=theme.primary if active else "transparent",
                    border_radius=1,
                ),
            ],
            spacing=0,
            tight=True,
        ),
        padding=ft.padding.only(top=4, left=2, right=2),
        ink=on_click is not None,
        on_click=on_click,
    )


def tab_bar(
    theme: Theme,
    *,
    tabs: Sequence[str],
    active_index: int = 0,
    on_change: Optional[Callable[[int], None]] = None,
) -> ft.Container:
    def _make_handler(idx: int) -> Optional[Callable[[ft.ControlEvent], None]]:
        if on_change is None:
            return None
        return lambda e, i=idx: on_change(i)

    children = [
        _tab(theme, label, active=i == active_index, on_click=_make_handler(i))
        for i, label in enumerate(tabs)
    ]
    return ft.Container(
        content=ft.Row(
            controls=children,
            spacing=24,
            scroll=ft.ScrollMode.HIDDEN,
        ),
        padding=ft.padding.only(left=24, right=24, top=4),
        border=ft.border.only(bottom=ft.BorderSide(1, theme.border)),
    )
