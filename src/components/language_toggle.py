"""Sidebar English / Czech language switch.

OFF = English (default), ON = Czech. Mirrors the theme toggle visually so
both controls live as a tidy pair at the bottom of the sidebar.
"""

from __future__ import annotations

from typing import Callable

import flet as ft

from src.i18n import t
from src.theme import Theme


def language_toggle(
    theme: Theme,
    lang: str,
    *,
    on_toggle: Callable[[], None],
) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.TRANSLATE, color=theme.text_muted, size=18),
                ft.Text(t("czech", lang), color=theme.text_muted, size=13, expand=True),
                ft.Switch(
                    value=lang == "cs",
                    active_color=theme.primary,
                    on_change=lambda e: on_toggle(),
                    scale=0.85,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=4),
    )
