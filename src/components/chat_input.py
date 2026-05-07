"""Bottom message input - text field + action chips."""

from __future__ import annotations

import flet as ft

from src.i18n import t
from src.theme import Theme


def _input_action_chip(theme: Theme, icon: str, label: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=theme.text_muted, size=14),
                ft.Text(label, color=theme.text, size=12),
            ],
            spacing=6,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        bgcolor=theme.surface,
        border_radius=8,
        border=ft.border.all(1, theme.border),
        ink=True,
        on_click=lambda e: None,
    )


def _send_button(theme: Theme, lang: str) -> ft.Container:
    return ft.Container(
        content=ft.Icon(ft.Icons.SEND, color=ft.Colors.WHITE, size=18),
        width=40,
        height=40,
        bgcolor=theme.primary,
        border_radius=10,
        alignment=ft.Alignment.CENTER,
        ink=True,
        on_click=lambda e: None,
        tooltip=t("send", lang),
    )


def chat_input(theme: Theme, lang: str) -> ft.Container:
    text_field = ft.TextField(
        hint_text=t("type_message", lang),
        hint_style=ft.TextStyle(color=theme.text_muted, size=14),
        text_style=ft.TextStyle(color=theme.text, size=14),
        border=ft.InputBorder.NONE,
        filled=False,
        bgcolor="transparent",
        cursor_color=theme.primary,
        content_padding=ft.padding.symmetric(horizontal=4, vertical=12),
        expand=True,
    )

    attach_btn = ft.IconButton(
        icon=ft.Icons.ATTACH_FILE,
        icon_color=theme.text_muted,
        icon_size=18,
        tooltip=t("attach_file", lang),
        on_click=lambda e: None,
    )

    input_row = ft.Container(
        content=ft.Row(
            controls=[attach_btn, text_field, _send_button(theme, lang)],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        bgcolor=theme.surface,
        border_radius=12,
        border=ft.border.all(1, theme.border),
    )

    actions_row = ft.Row(
        controls=[
            _input_action_chip(theme, ft.Icons.ATTACH_FILE, t("attach_file", lang)),
            _input_action_chip(theme, ft.Icons.MIC_NONE_OUTLINED, t("voice_input", lang)),
            _input_action_chip(theme, ft.Icons.AUTO_FIX_HIGH, t("improve_prompt", lang)),
            ft.Container(expand=True),
            ft.Text(
                t("ai_disclaimer", lang),
                color=theme.text_subtle,
                size=11,
                italic=True,
            ),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    return ft.Container(
        content=ft.Column(
            controls=[input_row, actions_row],
            spacing=12,
            tight=True,
        ),
        padding=ft.padding.only(left=24, right=24, top=12, bottom=20),
    )
