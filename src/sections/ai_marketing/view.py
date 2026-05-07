"""AI Marketing - main center view (matches the design screenshot)."""

from __future__ import annotations

import flet as ft

from src.components.chat_input import chat_input
from src.components.chat_message import chat_message
from src.components.header import header
from src.components.tab_bar import tab_bar
from src.sections.ai_marketing.data import (
    SECTION_ICON,
    assistant_actions,
    tabs,
)
from src.sections.ai_marketing.phone_mockup import phone_mockup
from src.sections.ai_marketing.strings import s
from src.theme import Theme


def _section_heading(theme: Theme, icon: str, title: str) -> ft.Row:
    return ft.Row(
        controls=[
            ft.Icon(icon, color=theme.primary, size=16),
            ft.Text(
                title,
                color=theme.primary,
                size=13,
                weight=ft.FontWeight.W_700,
            ),
        ],
        spacing=6,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _check_bullet(theme: Theme, text: str) -> ft.Row:
    return ft.Row(
        controls=[
            ft.Icon(
                ft.Icons.CHECK_BOX_OUTLINED,
                color="#22C55E",
                size=18,
            ),
            ft.Text(text, color=theme.text, size=14, expand=True, selectable=True),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _action_chip(theme: Theme, icon: str, label: str) -> ft.Container:
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


def _assistant_message(theme: Theme, lang: str) -> ft.Row:
    txt = s(lang)

    headline_block = ft.Column(
        controls=[
            _section_heading(theme, ft.Icons.PUSH_PIN_OUTLINED, txt["msg2_headline_title"]),
            ft.Text(
                txt["msg2_headline_text"],
                color=theme.text,
                size=14,
                selectable=True,
            ),
        ],
        spacing=6,
        tight=True,
    )

    post_block = ft.Column(
        controls=[
            _section_heading(theme, ft.Icons.EDIT_OUTLINED, txt["msg2_post_title"]),
            ft.Text(
                txt["msg2_post_intro"],
                color=theme.text,
                size=14,
                selectable=True,
            ),
            ft.Column(
                controls=[
                    _check_bullet(theme, txt["msg2_check1"]),
                    _check_bullet(theme, txt["msg2_check2"]),
                    _check_bullet(theme, txt["msg2_check3"]),
                    _check_bullet(theme, txt["msg2_check4"]),
                ],
                spacing=4,
                tight=True,
            ),
            ft.Text(
                txt["msg2_cta"],
                color=theme.text,
                size=14,
                weight=ft.FontWeight.W_600,
                selectable=True,
            ),
            ft.Text(
                txt["msg2_hashtags"],
                color=theme.primary,
                size=13,
                selectable=True,
            ),
        ],
        spacing=10,
        tight=True,
        expand=True,
    )

    left_column = ft.Column(
        controls=[headline_block, post_block],
        spacing=14,
        expand=True,
        tight=True,
    )

    body_row = ft.Row(
        controls=[
            ft.Container(content=left_column, expand=True),
            phone_mockup(theme, lang),
        ],
        spacing=18,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    bubble = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(txt["msg2_intro"], color=theme.text, size=14, selectable=True),
                body_row,
            ],
            spacing=14,
            tight=True,
        ),
        padding=18,
        bgcolor=theme.assistant_bubble,
        border_radius=14,
    )

    actions_row = ft.Row(
        controls=[
            _action_chip(theme, a["icon"], a["label"])
            for a in assistant_actions(lang)
        ],
        spacing=8,
        wrap=True,
        run_spacing=8,
    )

    avatar = ft.Container(
        content=ft.Icon(SECTION_ICON, color=ft.Colors.WHITE, size=18),
        width=36,
        height=36,
        bgcolor=theme.primary,
        border_radius=10,
        alignment=ft.Alignment.CENTER,
    )

    body = ft.Column(
        controls=[
            ft.Container(
                content=ft.Text("10:42", color=theme.text_muted, size=11),
                padding=ft.padding.only(left=4),
            ),
            bubble,
            actions_row,
        ],
        spacing=10,
        expand=True,
        tight=True,
    )

    return ft.Row(
        controls=[avatar, body],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def build_view(theme: Theme, lang: str) -> ft.Column:
    txt = s(lang)

    user_msg = chat_message(
        theme,
        lang,
        avatar_icon=SECTION_ICON,
        role="user",
        time="10:42",
        text=txt["msg1_user"],
    )

    messages_list = ft.ListView(
        controls=[
            user_msg,
            _assistant_message(theme, lang),
        ],
        spacing=22,
        padding=ft.padding.symmetric(horizontal=24, vertical=20),
        expand=True,
        auto_scroll=False,
    )

    return ft.Column(
        controls=[
            header(
                theme,
                lang,
                icon=SECTION_ICON,
                title=txt["title"],
                subtitle=txt["subtitle"],
            ),
            tab_bar(theme, tabs=tabs(lang), active_index=0),
            messages_list,
            chat_input(theme, lang),
        ],
        spacing=0,
        expand=True,
        tight=True,
    )
