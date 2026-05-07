"""Sidebar light / dark mode switch."""

from __future__ import annotations

from typing import Callable

import flet as ft

from src.i18n import t
from src.theme import Theme


def theme_toggle(
    theme: Theme,
    lang: str,
    *,
    theme_mode: str,
    on_toggle: Callable[[], None],
) -> ft.Container:
    is_light = theme_mode == "light"
    icon = ft.Icons.WB_SUNNY_OUTLINED if is_light else ft.Icons.NIGHTLIGHT_ROUND
    label = t("light_mode" if is_light else "dark_mode", lang)

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=theme.text_muted, size=18),
                ft.Text(label, color=theme.text_muted, size=13, expand=True),
                ft.Switch(
                    value=is_light,
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
