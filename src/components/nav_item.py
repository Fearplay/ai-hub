"""One row in the left sidebar."""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from src.theme import Theme


def nav_item(
    theme: Theme,
    icon: str,
    label: str,
    *,
    active: bool = False,
    badge: Optional[str] = None,
    on_click: Optional[Callable[[ft.ControlEvent], None]] = None,
) -> ft.Container:
    icon_color = theme.primary if active else theme.text_muted
    text_color = theme.text if active else theme.text_muted
    text_weight = ft.FontWeight.W_600 if active else ft.FontWeight.W_500

    children: list[ft.Control] = [
        ft.Icon(icon, color=icon_color, size=20),
        ft.Text(
            label,
            color=text_color,
            size=14,
            weight=text_weight,
            expand=True,
            overflow=ft.TextOverflow.ELLIPSIS,
            max_lines=1,
        ),
    ]

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

    return ft.Container(
        content=ft.Row(controls=children, spacing=12),
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        bgcolor=theme.primary_tint if active else None,
        border_radius=10,
        ink=True,
        on_click=on_click,
    )
