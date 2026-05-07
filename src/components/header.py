"""Generic top bar of a section view (icon, title, subtitle, actions)."""

from __future__ import annotations

from typing import Optional

import flet as ft

from src.i18n import t
from src.theme import Theme


def _category_icon(theme: Theme, icon: str) -> ft.Container:
    return ft.Container(
        content=ft.Icon(icon, color=ft.Colors.WHITE, size=22),
        width=44,
        height=44,
        bgcolor=theme.primary,
        border_radius=12,
        alignment=ft.Alignment.CENTER,
    )


def _help_button(theme: Theme, label: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.MENU_BOOK_OUTLINED, color=theme.text, size=16),
                ft.Text(label, color=theme.text, size=13, weight=ft.FontWeight.W_500),
            ],
            spacing=8,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        bgcolor=theme.surface,
        border_radius=10,
        border=ft.border.all(1, theme.border),
        ink=True,
        on_click=lambda e: None,
    )


def _menu_button(theme: Theme) -> ft.Container:
    return ft.Container(
        content=ft.Icon(ft.Icons.MORE_HORIZ, color=theme.text, size=18),
        width=38,
        height=38,
        bgcolor=theme.surface,
        border_radius=10,
        border=ft.border.all(1, theme.border),
        alignment=ft.Alignment.CENTER,
        ink=True,
        on_click=lambda e: None,
    )


def header(
    theme: Theme,
    lang: str,
    *,
    icon: str,
    title: str,
    subtitle: Optional[str] = None,
) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                _category_icon(theme, icon),
                ft.Column(
                    controls=[
                        ft.Text(
                            title,
                            color=theme.text,
                            size=18,
                            weight=ft.FontWeight.W_700,
                        ),
                        ft.Text(
                            subtitle or "",
                            color=theme.text_muted,
                            size=12,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
                _help_button(theme, t("how_to_use", lang)),
                _menu_button(theme),
            ],
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.only(left=24, right=24, top=22, bottom=10),
    )
