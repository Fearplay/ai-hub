"""Levý sidebar - logo, nová konverzace, navigace, profil, theme toggle."""

from __future__ import annotations

from typing import Callable

import flet as ft

from src.components.nav_item import nav_item
from src.components.user_card import user_card
from src.data.mock import NAV_ITEMS, SECONDARY_NAV
from src.theme import Theme


def _logo(theme: Theme) -> ft.Row:
    icon_box = ft.Container(
        content=ft.Icon(ft.Icons.PSYCHOLOGY_ALT_OUTLINED, color=ft.Colors.WHITE, size=22),
        width=38,
        height=38,
        bgcolor=theme.primary,
        border_radius=10,
        alignment=ft.Alignment.CENTER,
    )
    title = ft.Row(
        controls=[
            ft.Text("AI Hub", color=theme.text, size=18, weight=ft.FontWeight.W_700),
            ft.Text("+", color=theme.primary, size=18, weight=ft.FontWeight.W_700),
        ],
        spacing=2,
        tight=True,
    )
    return ft.Row(
        controls=[icon_box, title],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _new_chat_button(theme: Theme) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.ADD, color=ft.Colors.WHITE, size=18),
                ft.Text(
                    "Nová konverzace",
                    color=ft.Colors.WHITE,
                    size=14,
                    weight=ft.FontWeight.W_600,
                ),
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
            tight=True,
        ),
        bgcolor=theme.primary,
        padding=ft.padding.symmetric(horizontal=14, vertical=12),
        border_radius=10,
        ink=True,
        on_click=lambda e: None,
        alignment=ft.Alignment.CENTER,
    )


def _theme_toggle(
    theme: Theme,
    theme_mode: str,
    on_theme_toggle: Callable[[], None],
) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.WB_SUNNY_OUTLINED, color=theme.text_muted, size=18),
                ft.Text("Světlý režim", color=theme.text_muted, size=13, expand=True),
                ft.Switch(
                    value=theme_mode == "light",
                    active_color=theme.primary,
                    on_change=lambda e: on_theme_toggle(),
                    scale=0.85,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=4),
    )


def sidebar(
    theme: Theme,
    *,
    active_section: str,
    on_section_change: Callable[[str], None],
    theme_mode: str,
    on_theme_toggle: Callable[[], None],
) -> ft.Container:
    primary_nav = ft.Column(
        controls=[
            nav_item(
                theme,
                item["icon"],
                item["label"],
                active=item["key"] == active_section,
                on_click=lambda e, k=item["key"]: on_section_change(k),
            )
            for item in NAV_ITEMS
        ],
        spacing=2,
        tight=True,
    )

    secondary_nav = ft.Column(
        controls=[
            nav_item(
                theme,
                item["icon"],
                item["label"],
                active=item["key"] == active_section,
                badge=item.get("badge"),
                on_click=lambda e, k=item["key"]: on_section_change(k),
            )
            for item in SECONDARY_NAV
        ],
        spacing=2,
        tight=True,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    content=_logo(theme),
                    padding=ft.padding.symmetric(horizontal=20, vertical=20),
                ),
                ft.Container(
                    content=_new_chat_button(theme),
                    padding=ft.padding.symmetric(horizontal=16),
                ),
                ft.Container(
                    content=primary_nav,
                    padding=ft.padding.only(left=12, right=12, top=18, bottom=4),
                ),
                ft.Container(
                    content=ft.Divider(color=theme.border, height=1, thickness=1),
                    padding=ft.padding.symmetric(horizontal=16, vertical=8),
                ),
                ft.Container(
                    content=secondary_nav,
                    padding=ft.padding.symmetric(horizontal=12, vertical=4),
                ),
                ft.Container(expand=True),
                ft.Container(
                    content=user_card(theme),
                    padding=ft.padding.only(left=12, right=12, top=8, bottom=8),
                ),
                _theme_toggle(theme, theme_mode, on_theme_toggle),
                ft.Container(height=12),
            ],
            spacing=0,
            tight=True,
        ),
        width=280,
        bgcolor=theme.sidebar_bg,
        border=ft.border.only(right=ft.BorderSide(1, theme.border)),
    )
