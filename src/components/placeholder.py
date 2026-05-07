"""Default "coming soon" view used by sections that aren't built out yet."""

from __future__ import annotations

import flet as ft

from src.i18n import t
from src.theme import Theme


def placeholder_view(theme: Theme, lang: str, *, title: str) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.HOURGLASS_EMPTY_ROUNDED,
                        color=theme.primary,
                        size=44,
                    ),
                    width=88,
                    height=88,
                    bgcolor=theme.primary_tint,
                    border_radius=22,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text(
                    title,
                    color=theme.text,
                    size=22,
                    weight=ft.FontWeight.W_700,
                ),
                ft.Text(
                    t("coming_soon", lang),
                    color=theme.text_muted,
                    size=14,
                ),
            ],
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
    )
