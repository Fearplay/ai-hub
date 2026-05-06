"""Tab bar pod headerem (Chat / Formulářový režim)."""

from __future__ import annotations

import flet as ft

from src.theme import Theme


def _tab(theme: Theme, label: str, *, active: bool) -> ft.Container:
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
    )


def tab_bar(theme: Theme, *, active: str = "chat") -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                _tab(theme, "Chat", active=active == "chat"),
                _tab(theme, "Formulářový režim", active=active == "form"),
            ],
            spacing=24,
        ),
        padding=ft.padding.only(left=24, right=24, top=4),
        border=ft.border.only(bottom=ft.BorderSide(1, theme.border)),
    )
