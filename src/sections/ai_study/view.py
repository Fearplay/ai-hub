"""AI Study - main center view (matches the design screenshot)."""

from __future__ import annotations

import flet as ft

from src.components.chat_input import chat_input
from src.components.chat_message import chat_message
from src.components.header import header
from src.components.tab_bar import tab_bar
from src.sections.ai_study.data import (
    SECTION_ICON,
    assistant_actions,
    recommended_sources,
    tabs,
)
from src.sections.ai_study.strings import s
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


def _bullet_row(theme: Theme, text: str) -> ft.Row:
    return ft.Row(
        controls=[
            ft.Container(
                content=ft.Text("•", color=theme.text, size=14, weight=ft.FontWeight.W_700),
                width=14,
                alignment=ft.Alignment.CENTER,
            ),
            ft.Text(text, color=theme.text, size=14, expand=True, selectable=True),
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def _particles_artwork(theme: Theme) -> ft.Container:
    """Small decorative purple-particle illustration (no asset, pure flet)."""
    primary = theme.primary

    def orb(size: int, color: str, opacity: float) -> ft.Container:
        return ft.Container(
            width=size,
            height=size,
            border_radius=size // 2,
            bgcolor=ft.Colors.with_opacity(opacity, color),
        )

    halo_a = ft.Container(
        width=58,
        height=58,
        border_radius=29,
        bgcolor=ft.Colors.with_opacity(0.18, primary),
        alignment=ft.Alignment.CENTER,
        content=orb(26, primary, 0.95),
    )
    halo_b = ft.Container(
        width=58,
        height=58,
        border_radius=29,
        bgcolor=ft.Colors.with_opacity(0.18, primary),
        alignment=ft.Alignment.CENTER,
        content=orb(26, primary, 0.95),
    )

    connector = ft.Container(
        width=44,
        height=2,
        bgcolor=ft.Colors.with_opacity(0.55, primary),
        border_radius=1,
    )

    return ft.Container(
        content=ft.Row(
            controls=[halo_a, connector, halo_b],
            spacing=2,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        alignment=ft.Alignment.CENTER,
    )


def _simple_block(theme: Theme, lang: str) -> ft.Container:
    txt = s(lang)

    text_col = ft.Column(
        controls=[
            _section_heading(theme, ft.Icons.LIGHTBULB_OUTLINE, txt["section_simple_title"]),
            ft.Text(
                txt["section_simple_text"],
                color=theme.text,
                size=13,
                selectable=True,
            ),
        ],
        spacing=8,
        tight=True,
        expand=True,
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(content=text_col, expand=True),
                _particles_artwork(theme),
            ],
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=14,
        bgcolor=ft.Colors.with_opacity(0.35, theme.primary_tint),
        border_radius=12,
        border=ft.border.all(1, ft.Colors.with_opacity(0.35, theme.primary)),
    )


def _keypoints_block(theme: Theme, lang: str) -> ft.Column:
    txt = s(lang)
    return ft.Column(
        controls=[
            _section_heading(theme, ft.Icons.PUSH_PIN_OUTLINED, txt["section_keypoints_title"]),
            ft.Column(
                controls=[
                    _bullet_row(theme, txt["key_bullet1"]),
                    _bullet_row(theme, txt["key_bullet2"]),
                    _bullet_row(theme, txt["key_bullet3"]),
                    _bullet_row(theme, txt["key_bullet4"]),
                ],
                spacing=4,
                tight=True,
            ),
        ],
        spacing=8,
        tight=True,
    )


def _example_block(theme: Theme, lang: str) -> ft.Column:
    txt = s(lang)
    return ft.Column(
        controls=[
            _section_heading(theme, ft.Icons.AUTO_STORIES_OUTLINED, txt["section_example_title"]),
            ft.Text(
                txt["section_example_text"],
                color=theme.text,
                size=14,
                selectable=True,
            ),
        ],
        spacing=8,
        tight=True,
    )


def _action_chip(theme: Theme, icon: str, label: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=theme.primary, size=14),
                ft.Text(label, color=theme.text, size=12, weight=ft.FontWeight.W_500),
            ],
            spacing=6,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        bgcolor=theme.surface,
        border_radius=20,
        border=ft.border.all(1, theme.border),
        ink=True,
        on_click=lambda e: None,
    )


def _assistant_message(theme: Theme, lang: str) -> ft.Row:
    txt = s(lang)

    bubble_children: list[ft.Control] = [
        ft.Text(txt["msg2_intro"], color=theme.text, size=14, selectable=True),
        _simple_block(theme, lang),
        _keypoints_block(theme, lang),
        _example_block(theme, lang),
    ]

    bubble = ft.Container(
        content=ft.Column(
            controls=bubble_children,
            spacing=14,
            tight=True,
        ),
        padding=16,
        bgcolor=theme.assistant_bubble,
        border_radius=14,
    )

    actions_row = ft.Row(
        controls=[_action_chip(theme, a["icon"], a["label"]) for a in assistant_actions(lang)],
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
                content=ft.Text("10:24", color=theme.text_muted, size=11),
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


def _source_card(theme: Theme, source: dict) -> ft.Container:
    badge = ft.Container(
        content=ft.Icon(source["icon"], color=ft.Colors.WHITE, size=16),
        width=32,
        height=32,
        bgcolor=source["color"],
        border_radius=8,
        alignment=ft.Alignment.CENTER,
    )
    info = ft.Column(
        controls=[
            ft.Text(
                source["title"],
                color=theme.text,
                size=12,
                weight=ft.FontWeight.W_600,
                overflow=ft.TextOverflow.ELLIPSIS,
                max_lines=2,
            ),
            ft.Text(
                source["domain"],
                color=theme.text_muted,
                size=10,
                overflow=ft.TextOverflow.ELLIPSIS,
                max_lines=1,
            ),
        ],
        spacing=2,
        tight=True,
        expand=True,
    )
    return ft.Container(
        content=ft.Row(
            controls=[badge, info],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=10,
        bgcolor=theme.surface,
        border_radius=10,
        border=ft.border.all(1, theme.border),
        width=200,
        ink=True,
        on_click=lambda e: None,
    )


def _show_more(theme: Theme, label: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Text(label, color=theme.text, size=12, weight=ft.FontWeight.W_500),
                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=theme.text_muted, size=16),
            ],
            spacing=4,
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


def _sources_card(theme: Theme, lang: str) -> ft.Container:
    txt = s(lang)
    sources = recommended_sources(lang)

    cards_row = ft.Row(
        controls=[_source_card(theme, src) for src in sources] + [_show_more(theme, txt["source_show_more"])],
        spacing=10,
        scroll=ft.ScrollMode.HIDDEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    txt["sources_title"],
                    color=theme.text_muted,
                    size=12,
                    weight=ft.FontWeight.W_500,
                ),
                cards_row,
            ],
            spacing=8,
            tight=True,
        ),
        padding=ft.padding.only(left=24, right=24, top=4, bottom=8),
    )


def build_view(theme: Theme, lang: str) -> ft.Column:
    txt = s(lang)

    user_msg = chat_message(
        theme,
        lang,
        avatar_icon=SECTION_ICON,
        role="user",
        time="10:24",
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
            _sources_card(theme, lang),
            chat_input(theme, lang),
        ],
        spacing=0,
        expand=True,
        tight=True,
    )
