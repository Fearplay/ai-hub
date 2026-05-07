"""Drafts tab for the AI Legal section.

The user dictates rewrites in plain Czech / English; without an LLM
backend we mock the assistant by appending a static reply each time
they send. The crucial bit is the inline A4 preview embedded inside the
first assistant bubble - a paper-like ``ft.Container`` with the rewritten
text. Subsequent user instructions appear as additional chat bubbles.
"""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from src.sections.ai_legal.data import (
    SECTION_ICON,
    drafts_diff,
    drafts_preview_paragraphs,
    drafts_quick_actions,
)
from src.sections.ai_legal.state import STATE
from src.sections.ai_legal.strings import s
from src.theme import Theme


def _avatar(theme: Theme) -> ft.Container:
    return ft.Container(
        content=ft.Icon(SECTION_ICON, color=ft.Colors.WHITE, size=18),
        width=36,
        height=36,
        bgcolor=theme.primary,
        border_radius=10,
        alignment=ft.Alignment.CENTER,
    )


def _user_avatar(theme: Theme) -> ft.Container:
    return ft.Container(
        content=ft.Icon(ft.Icons.PERSON, color=ft.Colors.WHITE, size=16),
        width=28,
        height=28,
        bgcolor=theme.primary_soft,
        border_radius=14,
        alignment=ft.Alignment.CENTER,
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
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        bgcolor=theme.surface,
        border_radius=8,
        border=ft.border.all(1, theme.border),
        ink=True,
        on_click=lambda e: None,
    )


def _a4_preview(theme: Theme, lang: str) -> ft.Container:
    txt = s(lang)
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    height=4,
                    bgcolor=theme.primary,
                    border_radius=2,
                    width=64,
                ),
                ft.Text(
                    txt["preview_doc_heading"],
                    color="#0F172A",
                    size=18,
                    weight=ft.FontWeight.W_700,
                ),
                ft.Text(
                    txt["preview_doc_subheading"],
                    color="#475569",
                    size=12,
                    weight=ft.FontWeight.W_600,
                ),
                *[
                    ft.Text(
                        p,
                        color="#0F172A",
                        size=11,
                        selectable=True,
                    )
                    for p in drafts_preview_paragraphs(lang)
                ],
                ft.Container(height=4),
                ft.Text(
                    txt["preview_doc_footer"],
                    color="#94A3B8",
                    size=10,
                ),
            ],
            spacing=8,
            tight=True,
        ),
        padding=ft.padding.symmetric(horizontal=22, vertical=20),
        bgcolor="#F8FAFC",
        border=ft.border.all(1, "#CBD5F5"),
        border_radius=8,
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=14,
            color=ft.Colors.with_opacity(0.18, ft.Colors.BLACK),
            offset=ft.Offset(0, 4),
        ),
    )


def _open_full_button(theme: Theme, lang: str) -> ft.Container:
    txt = s(lang)
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.OPEN_IN_FULL, color=theme.primary, size=14),
                ft.Text(
                    txt["drafts_preview_open"],
                    color=theme.primary,
                    size=12,
                    weight=ft.FontWeight.W_600,
                ),
            ],
            spacing=6,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        bgcolor=ft.Colors.with_opacity(0.10, theme.primary),
        border_radius=8,
        ink=True,
        on_click=lambda e: None,
    )


def _initial_assistant_bubble(theme: Theme, lang: str) -> ft.Row:
    txt = s(lang)

    preview_block = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Icon(ft.Icons.ARTICLE_OUTLINED, color=theme.primary, size=16),
                    ft.Text(
                        txt["drafts_preview_title"],
                        color=theme.primary,
                        size=13,
                        weight=ft.FontWeight.W_700,
                    ),
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            _a4_preview(theme, lang),
            ft.Row(
                controls=[_open_full_button(theme, lang)],
                alignment=ft.MainAxisAlignment.END,
            ),
        ],
        spacing=10,
        tight=True,
    )

    bubble = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    txt["drafts_assistant_intro"],
                    color=theme.text,
                    size=14,
                    selectable=True,
                ),
                preview_block,
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
            for a in drafts_quick_actions(lang)
        ],
        spacing=8,
        wrap=True,
        run_spacing=8,
    )

    body = ft.Column(
        controls=[
            ft.Container(
                content=ft.Text(txt["drafts_assistant_time"], color=theme.text_muted, size=11),
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
        controls=[_avatar(theme), body],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def _initial_user_bubble(theme: Theme, lang: str) -> ft.Row:
    txt = s(lang)
    bubble = ft.Container(
        content=ft.Text(
            txt["drafts_user_message"],
            color=theme.user_bubble_text,
            size=14,
            selectable=True,
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        bgcolor=theme.user_bubble,
        border_radius=14,
    )
    return ft.Row(
        controls=[
            ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Text(txt["drafts_user_time"], color=theme.text_muted, size=11),
                        padding=ft.padding.only(right=4),
                    ),
                    ft.Row(
                        controls=[bubble, _user_avatar(theme)],
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


def _diff_assistant_bubble(theme: Theme, lang: str) -> ft.Row:
    txt = s(lang)
    diff_items = drafts_diff(lang)
    bubble_children: list[ft.Control] = [
        ft.Text(
            txt["drafts_assistant_diff_intro"],
            color=theme.text,
            size=14,
            weight=ft.FontWeight.W_600,
            selectable=True,
        ),
    ]
    for item in diff_items:
        bubble_children.append(
            ft.Row(
                controls=[
                    ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINED, color="#22C55E", size=16),
                    ft.Text(
                        item,
                        color=theme.text,
                        size=14,
                        expand=True,
                        selectable=True,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        )

    bubble = ft.Container(
        content=ft.Column(controls=bubble_children, spacing=8, tight=True),
        padding=14,
        bgcolor=theme.assistant_bubble,
        border_radius=14,
    )
    body = ft.Column(
        controls=[
            ft.Container(
                content=ft.Text("11:09", color=theme.text_muted, size=11),
                padding=ft.padding.only(left=4),
            ),
            bubble,
        ],
        spacing=4,
        expand=True,
        tight=True,
    )
    return ft.Row(
        controls=[_avatar(theme), body],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def _user_input_bubble(theme: Theme, time: str, text: str) -> ft.Row:
    bubble = ft.Container(
        content=ft.Text(text, color=theme.user_bubble_text, size=14, selectable=True),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        bgcolor=theme.user_bubble,
        border_radius=14,
    )
    return ft.Row(
        controls=[
            ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Text(time, color=theme.text_muted, size=11),
                        padding=ft.padding.only(right=4),
                    ),
                    ft.Row(
                        controls=[bubble, _user_avatar(theme)],
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


def _mock_assistant_bubble(theme: Theme, lang: str, time: str) -> ft.Row:
    txt = s(lang)
    bubble = ft.Container(
        content=ft.Text(
            txt["drafts_mock_response"],
            color=theme.text,
            size=14,
            selectable=True,
            italic=True,
        ),
        padding=14,
        bgcolor=theme.assistant_bubble,
        border_radius=14,
    )
    body = ft.Column(
        controls=[
            ft.Container(
                content=ft.Text(time, color=theme.text_muted, size=11),
                padding=ft.padding.only(left=4),
            ),
            bubble,
        ],
        spacing=4,
        expand=True,
        tight=True,
    )
    return ft.Row(
        controls=[_avatar(theme), body],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def _format_now() -> str:
    from datetime import datetime
    return datetime.now().strftime("%H:%M")


def _interactive_input(
    theme: Theme,
    lang: str,
    on_send: Callable[[str], None],
) -> ft.Container:
    txt = s(lang)
    field_ref = ft.Ref[ft.TextField]()

    def _send(_e: ft.ControlEvent) -> None:
        field = field_ref.current
        if field is None:
            return
        value = (field.value or "").strip()
        if not value:
            return
        field.value = ""
        try:
            field.update()
        except AssertionError:
            pass
        on_send(value)

    text_field = ft.TextField(
        ref=field_ref,
        hint_text=txt["drafts_mock_user_label"] + "...",
        hint_style=ft.TextStyle(color=theme.text_muted, size=14),
        text_style=ft.TextStyle(color=theme.text, size=14),
        border=ft.InputBorder.NONE,
        filled=False,
        bgcolor="transparent",
        cursor_color=theme.primary,
        content_padding=ft.padding.symmetric(horizontal=4, vertical=12),
        expand=True,
        on_submit=_send,
    )

    send_btn = ft.Container(
        content=ft.Icon(ft.Icons.SEND, color=ft.Colors.WHITE, size=18),
        width=40,
        height=40,
        bgcolor=theme.primary,
        border_radius=10,
        alignment=ft.Alignment.CENTER,
        ink=True,
        on_click=_send,
    )

    return ft.Container(
        content=ft.Row(
            controls=[text_field, send_btn],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        bgcolor=theme.surface,
        border_radius=12,
        border=ft.border.all(1, theme.border),
        margin=ft.margin.symmetric(horizontal=24, vertical=12),
    )


def build_drafts_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Optional[Callable[[], None]] = None,
) -> ft.Column:
    base_messages: list[ft.Control] = [
        _initial_assistant_bubble(theme, lang),
        _initial_user_bubble(theme, lang),
        _diff_assistant_bubble(theme, lang),
    ]

    for entry in STATE.drafts_messages:
        if entry["role"] == "user":
            base_messages.append(
                _user_input_bubble(theme, entry["time"], entry["text"])
            )
        else:
            base_messages.append(_mock_assistant_bubble(theme, lang, entry["time"]))

    messages_list = ft.ListView(
        controls=base_messages,
        spacing=22,
        padding=ft.padding.symmetric(horizontal=24, vertical=20),
        expand=True,
        auto_scroll=True,
    )

    def _on_send(value: str) -> None:
        time = _format_now()
        STATE.drafts_messages.append({"role": "user", "text": value, "time": time})
        STATE.drafts_messages.append({"role": "assistant", "text": "", "time": time})
        if on_request_rerender is not None:
            on_request_rerender()

    return ft.Column(
        controls=[
            messages_list,
            _interactive_input(theme, lang, _on_send),
        ],
        spacing=0,
        expand=True,
        tight=True,
    )
