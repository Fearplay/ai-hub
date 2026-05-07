"""Generic tab bar under the header.

When ``on_change`` is provided, tabs become clickable and the active styling
is updated in place via ``bar.update()`` - the same trick the sidebar uses
to keep section switching snappy without rebuilding the whole row.
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
        padding=ft.padding.only(top=4),
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
    state = {"active": active_index}
    row = ft.Row(spacing=24, scroll=ft.ScrollMode.HIDDEN)
    bar = ft.Container(
        content=row,
        padding=ft.padding.only(left=24, right=24, top=4),
        border=ft.border.only(bottom=ft.BorderSide(1, theme.border)),
    )

    def _make_handler(idx: int) -> Callable[[ft.ControlEvent], None]:
        def handler(_event: ft.ControlEvent) -> None:
            if idx == state["active"]:
                return
            state["active"] = idx
            _render()
            bar.update()
            if on_change is not None:
                on_change(idx)

        return handler

    def _render() -> None:
        row.controls = [
            _tab(
                theme,
                label,
                active=i == state["active"],
                on_click=_make_handler(i) if on_change is not None else None,
            )
            for i, label in enumerate(tabs)
        ]

    _render()
    return bar
