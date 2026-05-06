"""Spodní profilová karta v sidebaru."""

from __future__ import annotations

import flet as ft

from src.data.mock import USER
from src.theme import Theme


def user_card(theme: Theme) -> ft.Container:
    avatar = ft.Container(
        content=ft.Icon(ft.Icons.PERSON, color=ft.Colors.WHITE, size=20),
        width=40,
        height=40,
        bgcolor=theme.primary_soft,
        border_radius=20,
        alignment=ft.Alignment.CENTER,
    )

    info = ft.Column(
        controls=[
            ft.Text(
                USER["name"],
                color=theme.text,
                size=13,
                weight=ft.FontWeight.W_600,
            ),
            ft.Text(
                USER["email"],
                color=theme.text_muted,
                size=11,
            ),
        ],
        spacing=2,
        expand=True,
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                avatar,
                info,
                ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, color=theme.text_muted, size=18),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=10,
        bgcolor=theme.surface_2,
        border_radius=12,
    )
