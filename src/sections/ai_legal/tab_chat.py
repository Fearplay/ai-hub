"""Chat tab for the AI Legal section.

Replicates the screenshot: user asks about ``smlouva_o_dilo.pdf``,
assistant replies with a structured bubble (numbered sections + a
"What it means" callout). The shared :func:`chat_message` doesn't
support callouts mid-bubble, so we hand-build the assistant message
similar to ``ai_marketing.view._assistant_message``.
"""

from __future__ import annotations

import flet as ft

from src.components.chat_input import chat_input
from src.sections.ai_legal.data import (
    SECTION_ICON,
    chat_quick_actions,
)
from src.sections.ai_legal.state import STATE
from src.sections.ai_legal.strings import s
from src.theme import Theme


def _user_attachment_chip(theme: Theme, lang: str) -> ft.Container:
    txt = s(lang)
    file_info = STATE.uploaded_file or {"name": "smlouva_o_dilo.pdf", "type": "PDF"}
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.ATTACH_FILE,
                    color=ft.Colors.with_opacity(0.85, ft.Colors.WHITE),
                    size=14,
                ),
                ft.Text(
                    f"{txt['chat_user_attachment_label']} {file_info['name']}",
                    color=ft.Colors.with_opacity(0.85, ft.Colors.WHITE),
                    size=12,
                ),
            ],
            spacing=6,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.WHITE),
        border_radius=6,
    )


def _user_bubble(theme: Theme, lang: str) -> ft.Row:
    txt = s(lang)
    bubble_body = ft.Column(
        controls=[
            ft.Text(
                txt["chat_user_question"],
                color=theme.user_bubble_text,
                size=14,
                selectable=True,
            ),
            _user_attachment_chip(theme, lang),
        ],
        spacing=8,
        tight=True,
    )
    bubble = ft.Container(
        content=bubble_body,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        bgcolor=theme.user_bubble,
        border_radius=14,
        width=380,
    )
    avatar = ft.Container(
        content=ft.Icon(ft.Icons.PERSON, color=ft.Colors.WHITE, size=16),
        width=28,
        height=28,
        bgcolor=theme.primary_soft,
        border_radius=14,
        alignment=ft.Alignment.CENTER,
    )
    return ft.Row(
        controls=[
            ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Text(txt["chat_user_time"], color=theme.text_muted, size=11),
                        padding=ft.padding.only(right=4),
                    ),
                    ft.Row(
                        controls=[bubble, avatar],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.END,
                        tight=True,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.END,
                spacing=4,
                tight=True,
            ),
        ],
        alignment=ft.MainAxisAlignment.END,
    )


def _section_block(
    theme: Theme,
    *,
    title: str,
    text: str,
    callout: tuple[str, str] | None = None,
    bullets: list[str] | None = None,
) -> ft.Column:
    children: list[ft.Control] = [
        ft.Text(
            title,
            color=theme.text,
            size=14,
            weight=ft.FontWeight.W_700,
            selectable=True,
        ),
        ft.Text(text, color=theme.text, size=14, selectable=True),
    ]
    if callout is not None:
        callout_label, callout_text = callout
        children.append(_callout_box(theme, label=callout_label, text=callout_text))
    if bullets:
        children.append(
            ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Container(
                                width=6,
                                height=6,
                                bgcolor=theme.primary,
                                border_radius=3,
                                margin=ft.margin.only(top=8, right=8, left=4),
                            ),
                            ft.Text(
                                bullet,
                                color=theme.text,
                                size=14,
                                expand=True,
                                selectable=True,
                            ),
                        ],
                        spacing=0,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    )
                    for bullet in bullets
                ],
                spacing=4,
                tight=True,
            )
        )
    return ft.Column(controls=children, spacing=8, tight=True)


def _callout_box(theme: Theme, *, label: str, text: str) -> ft.Container:
    accent = "#F59E0B"
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.INFO_OUTLINE, color=accent, size=16),
                ft.Column(
                    controls=[
                        ft.Text(
                            label,
                            color=theme.text,
                            size=12,
                            weight=ft.FontWeight.W_700,
                        ),
                        ft.Text(
                            text,
                            color=theme.text_muted,
                            size=12,
                            selectable=True,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                    tight=True,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        padding=12,
        bgcolor=ft.Colors.with_opacity(0.10, accent),
        border=ft.border.all(1, ft.Colors.with_opacity(0.22, accent)),
        border_radius=10,
    )


def _action_chip(theme: Theme, icon: str, label: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=theme.primary, size=14),
                ft.Text(
                    label,
                    color=theme.text,
                    size=12,
                    weight=ft.FontWeight.W_500,
                ),
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


def _assistant_bubble(theme: Theme, lang: str) -> ft.Row:
    txt = s(lang)

    bubble = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    txt["chat_assistant_intro"],
                    color=theme.text,
                    size=14,
                    selectable=True,
                ),
                _section_block(
                    theme,
                    title=txt["chat_section1_title"],
                    text=txt["chat_section1_text"],
                    callout=(txt["chat_callout_label"], txt["chat_callout_text"]),
                ),
                _section_block(
                    theme,
                    title=txt["chat_section2_title"],
                    text=txt["chat_section2_text"],
                    bullets=[
                        txt["chat_section2_bullet1"],
                        txt["chat_section2_bullet2"],
                        txt["chat_section2_bullet3"],
                    ],
                ),
            ],
            spacing=14,
            tight=True,
        ),
        padding=16,
        bgcolor=theme.assistant_bubble,
        border_radius=14,
    )

    actions = ft.Row(
        controls=[
            _action_chip(theme, a["icon"], a["label"])
            for a in chat_quick_actions(lang)
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
                content=ft.Text(txt["chat_assistant_time"], color=theme.text_muted, size=11),
                padding=ft.padding.only(left=4),
            ),
            bubble,
            actions,
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


def build_chat_tab(theme: Theme, lang: str) -> ft.Column:
    messages_list = ft.ListView(
        controls=[
            _user_bubble(theme, lang),
            _assistant_bubble(theme, lang),
        ],
        spacing=22,
        padding=ft.padding.symmetric(horizontal=24, vertical=20),
        expand=True,
        auto_scroll=False,
    )

    return ft.Column(
        controls=[
            messages_list,
            chat_input(theme, lang),
        ],
        spacing=0,
        expand=True,
        tight=True,
    )
