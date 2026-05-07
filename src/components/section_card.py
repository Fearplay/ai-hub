"""Generic card with a header + content (used in the right context panel)."""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from src.theme import Theme


def section_card(
    theme: Theme,
    icon: str,
    title: str,
    content: ft.Control,
    *,
    action_label: Optional[str] = None,
    on_action: Optional[Callable[[ft.ControlEvent], None]] = None,
) -> ft.Container:
    header_controls: list[ft.Control] = [
        ft.Icon(icon, color=theme.text_muted, size=18),
        ft.Text(
            title,
            color=theme.text,
            size=14,
            weight=ft.FontWeight.W_600,
            expand=True,
        ),
    ]

    if action_label:
        header_controls.append(
            ft.TextButton(
                content=ft.Text(
                    action_label,
                    color=theme.primary,
                    size=12,
                    weight=ft.FontWeight.W_600,
                ),
                style=ft.ButtonStyle(
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    overlay_color=ft.Colors.with_opacity(0.08, theme.primary),
                ),
                on_click=on_action,
            )
        )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=header_controls,
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                content,
            ],
            spacing=14,
            tight=True,
        ),
        padding=16,
        bgcolor=theme.surface,
        border_radius=14,
        border=ft.border.all(1, theme.border),
    )
