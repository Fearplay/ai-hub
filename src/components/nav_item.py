"""One row in the left sidebar.

Two flavors:

* :func:`nav_item` - simple builder that just returns a Container. Use this
  if you only need a one-shot row that you do not plan to mutate.
* :func:`nav_item_handle` - returns the row plus references to the icon /
  text controls so callers can flip the active state without rebuilding
  (used by the sidebar to keep section clicks snappy).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import flet as ft

from src.theme import Theme


@dataclass(frozen=True)
class NavItemHandle:
    container: ft.Container
    icon: ft.Icon
    text: ft.Text

    def set_active(self, theme: Theme, *, active: bool) -> None:
        self.container.bgcolor = theme.primary_tint if active else None
        self.icon.color = theme.primary if active else theme.text_muted
        self.text.color = theme.text if active else theme.text_muted
        self.text.weight = ft.FontWeight.W_600 if active else ft.FontWeight.W_500


def nav_item_handle(
    theme: Theme,
    icon: str,
    label: str,
    *,
    active: bool = False,
    badge: Optional[str] = None,
    on_click: Optional[Callable[[ft.ControlEvent], None]] = None,
) -> NavItemHandle:
    icon_control = ft.Icon(
        icon,
        color=theme.primary if active else theme.text_muted,
        size=20,
    )
    text_control = ft.Text(
        label,
        color=theme.text if active else theme.text_muted,
        size=14,
        weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_500,
        expand=True,
        overflow=ft.TextOverflow.ELLIPSIS,
        max_lines=1,
    )

    children: list[ft.Control] = [icon_control, text_control]

    if badge:
        children.append(
            ft.Container(
                content=ft.Text(
                    badge,
                    color=ft.Colors.WHITE,
                    size=11,
                    weight=ft.FontWeight.W_700,
                ),
                bgcolor=theme.badge,
                padding=ft.padding.symmetric(horizontal=8, vertical=2),
                border_radius=10,
                alignment=ft.Alignment.CENTER,
            )
        )

    container = ft.Container(
        content=ft.Row(controls=children, spacing=12),
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        bgcolor=theme.primary_tint if active else None,
        border_radius=10,
        ink=True,
        on_click=on_click,
    )

    return NavItemHandle(container=container, icon=icon_control, text=text_control)


def nav_item(
    theme: Theme,
    icon: str,
    label: str,
    *,
    active: bool = False,
    badge: Optional[str] = None,
    on_click: Optional[Callable[[ft.ControlEvent], None]] = None,
) -> ft.Container:
    return nav_item_handle(
        theme,
        icon,
        label,
        active=active,
        badge=badge,
        on_click=on_click,
    ).container
