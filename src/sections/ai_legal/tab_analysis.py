"""Analysis tab for the AI Legal section.

Two presentation modes that share the same mock data
(:func:`src.sections.ai_legal.data.analysis_findings`):

* ``document`` - polished read-only summary with green / yellow / blue
  cards and a Markdown body. Looks like a finished report.
* ``chat`` - the same findings spread across a chain of assistant chat
  bubbles, so the user can scroll through them like a conversation.

The toggle between the two persists in :class:`LegalState` so users
keep their choice when switching tabs / theme / language.
"""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from src.sections.ai_legal.data import (
    SECTION_ICON,
    analysis_findings,
    analysis_markdown,
)
from src.sections.ai_legal.state import STATE
from src.sections.ai_legal.strings import s
from src.theme import Theme


_OK_COLOR = "#22C55E"
_RISK_COLOR = "#F97316"
_INFO_COLOR = "#3B82F6"


def _segmented_button(
    theme: Theme,
    label: str,
    *,
    active: bool,
    on_click: Callable[[ft.ControlEvent], None],
) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            label,
            color=ft.Colors.WHITE if active else theme.text_muted,
            size=12,
            weight=ft.FontWeight.W_600,
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=8),
        bgcolor=theme.primary if active else "transparent",
        border_radius=8,
        ink=True,
        on_click=on_click,
        alignment=ft.Alignment.CENTER,
    )


def _view_toggle(
    theme: Theme,
    lang: str,
    on_change: Callable[[str], None],
) -> ft.Container:
    txt = s(lang)
    mode = STATE.analysis_view_mode
    return ft.Container(
        content=ft.Row(
            controls=[
                _segmented_button(
                    theme,
                    txt["analysis_view_document"],
                    active=mode == "document",
                    on_click=lambda e: on_change("document"),
                ),
                _segmented_button(
                    theme,
                    txt["analysis_view_chat"],
                    active=mode == "chat",
                    on_click=lambda e: on_change("chat"),
                ),
            ],
            spacing=4,
            tight=True,
        ),
        padding=4,
        bgcolor=theme.surface,
        border_radius=10,
        border=ft.border.all(1, theme.border),
    )


def _findings_card(
    theme: Theme,
    *,
    icon: str,
    title: str,
    items: list[str],
    accent: str,
) -> ft.Container:
    rows: list[ft.Control] = [
        ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(icon, color=accent, size=18),
                    width=32,
                    height=32,
                    bgcolor=ft.Colors.with_opacity(0.15, accent),
                    border_radius=8,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text(
                    title,
                    color=theme.text,
                    size=14,
                    weight=ft.FontWeight.W_700,
                    expand=True,
                ),
                ft.Container(
                    content=ft.Text(
                        str(len(items)),
                        color=accent,
                        size=12,
                        weight=ft.FontWeight.W_700,
                    ),
                    padding=ft.padding.symmetric(horizontal=8, vertical=2),
                    bgcolor=ft.Colors.with_opacity(0.18, accent),
                    border_radius=10,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    ]
    for item in items:
        rows.append(
            ft.Row(
                controls=[
                    ft.Container(
                        width=6,
                        height=6,
                        bgcolor=accent,
                        border_radius=3,
                        margin=ft.margin.only(top=8, right=10, left=2),
                    ),
                    ft.Text(
                        item,
                        color=theme.text,
                        size=13,
                        expand=True,
                        selectable=True,
                    ),
                ],
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        )
    return ft.Container(
        content=ft.Column(controls=rows, spacing=10, tight=True),
        padding=16,
        bgcolor=theme.surface,
        border=ft.border.all(1, theme.border),
        border_radius=14,
        expand=True,
    )


def _document_view(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    findings = analysis_findings(lang)

    title_block = ft.Column(
        controls=[
            ft.Text(
                txt["analysis_doc_title"],
                color=theme.text,
                size=18,
                weight=ft.FontWeight.W_700,
            ),
            ft.Text(
                txt["analysis_doc_subtitle"],
                color=theme.text_muted,
                size=13,
            ),
        ],
        spacing=4,
        tight=True,
    )

    cards_row = ft.ResponsiveRow(
        controls=[
            ft.Container(
                content=_findings_card(
                    theme,
                    icon=ft.Icons.CHECK_CIRCLE_OUTLINED,
                    title=txt["analysis_correct_title"],
                    items=findings["right"],
                    accent=_OK_COLOR,
                ),
                col={"xs": 12, "md": 6},
            ),
            ft.Container(
                content=_findings_card(
                    theme,
                    icon=ft.Icons.WARNING_AMBER_OUTLINED,
                    title=txt["analysis_wrong_title"],
                    items=findings["risk"],
                    accent=_RISK_COLOR,
                ),
                col={"xs": 12, "md": 6},
            ),
        ],
        spacing=14,
        run_spacing=14,
    )

    recommendations_card = _findings_card(
        theme,
        icon=ft.Icons.LIGHTBULB_OUTLINE,
        title=txt["analysis_recommendations_title"],
        items=findings["recommendations"],
        accent=_INFO_COLOR,
    )

    md = ft.Container(
        content=ft.Markdown(
            analysis_markdown(lang),
            extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
            selectable=True,
        ),
        padding=18,
        bgcolor=theme.surface,
        border=ft.border.all(1, theme.border),
        border_radius=14,
    )

    column = ft.Column(
        controls=[
            title_block,
            cards_row,
            recommendations_card,
            md,
        ],
        spacing=16,
        tight=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True,
    )
    return ft.Container(
        content=column,
        padding=ft.padding.symmetric(horizontal=24, vertical=20),
        expand=True,
    )


def _chat_avatar(theme: Theme) -> ft.Container:
    return ft.Container(
        content=ft.Icon(SECTION_ICON, color=ft.Colors.WHITE, size=18),
        width=36,
        height=36,
        bgcolor=theme.primary,
        border_radius=10,
        alignment=ft.Alignment.CENTER,
    )


def _chat_bubble(
    theme: Theme,
    *,
    intro: str,
    items: list[str],
    accent: str,
    icon: str,
    time: str,
    bullet_marker: str = "•",
) -> ft.Row:
    bubble_children: list[ft.Control] = [
        ft.Row(
            controls=[
                ft.Icon(icon, color=accent, size=18),
                ft.Text(
                    intro,
                    color=theme.text,
                    size=14,
                    weight=ft.FontWeight.W_700,
                    expand=True,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    ]
    for item in items:
        bubble_children.append(
            ft.Row(
                controls=[
                    ft.Text(
                        bullet_marker,
                        color=accent,
                        size=14,
                        weight=ft.FontWeight.W_700,
                    ),
                    ft.Text(
                        item,
                        color=theme.text,
                        size=14,
                        expand=True,
                        selectable=True,
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        )
    bubble = ft.Container(
        content=ft.Column(controls=bubble_children, spacing=8, tight=True),
        padding=14,
        bgcolor=theme.assistant_bubble,
        border_radius=14,
    )
    return ft.Row(
        controls=[
            _chat_avatar(theme),
            ft.Column(
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
            ),
        ],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def _chat_action_chip(theme: Theme, icon: str, label: str) -> ft.Container:
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


def _chat_view(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    findings = analysis_findings(lang)

    intro_bubble = ft.Row(
        controls=[
            _chat_avatar(theme),
            ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Text("11:14", color=theme.text_muted, size=11),
                        padding=ft.padding.only(left=4),
                    ),
                    ft.Container(
                        content=ft.Text(
                            txt["analysis_chat_intro"],
                            color=theme.text,
                            size=14,
                            selectable=True,
                        ),
                        padding=14,
                        bgcolor=theme.assistant_bubble,
                        border_radius=14,
                    ),
                ],
                spacing=4,
                expand=True,
                tight=True,
            ),
        ],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    actions_row = ft.Row(
        controls=[
            _chat_action_chip(theme, ft.Icons.PICTURE_AS_PDF, txt["analysis_chat_action_export"]),
            _chat_action_chip(theme, ft.Icons.FORWARD_TO_INBOX, txt["analysis_chat_action_email"]),
        ],
        spacing=8,
        wrap=True,
        run_spacing=8,
    )

    items: list[ft.Control] = [
        intro_bubble,
        _chat_bubble(
            theme,
            intro=txt["analysis_correct_title"],
            items=findings["right"],
            accent=_OK_COLOR,
            icon=ft.Icons.CHECK_CIRCLE_OUTLINED,
            time="11:14",
        ),
        _chat_bubble(
            theme,
            intro=txt["analysis_wrong_title"],
            items=findings["risk"],
            accent=_RISK_COLOR,
            icon=ft.Icons.WARNING_AMBER_OUTLINED,
            time="11:15",
        ),
        _chat_bubble(
            theme,
            intro=txt["analysis_recommendations_title"],
            items=findings["recommendations"],
            accent=_INFO_COLOR,
            icon=ft.Icons.LIGHTBULB_OUTLINE,
            time="11:15",
        ),
        actions_row,
    ]

    return ft.ListView(
        controls=items,
        spacing=22,
        padding=ft.padding.symmetric(horizontal=24, vertical=20),
        expand=True,
        auto_scroll=False,
    )


def build_analysis_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Optional[Callable[[], None]] = None,
) -> ft.Column:
    body_holder = ft.Container(
        content=_document_view(theme, lang)
        if STATE.analysis_view_mode == "document"
        else _chat_view(theme, lang),
        expand=True,
    )

    def _switch_mode(mode: str) -> None:
        if mode == STATE.analysis_view_mode:
            return
        STATE.analysis_view_mode = mode
        if on_request_rerender is not None:
            on_request_rerender()

    toggle_row = ft.Container(
        content=ft.Row(
            controls=[_view_toggle(theme, lang, _switch_mode)],
            alignment=ft.MainAxisAlignment.START,
        ),
        padding=ft.padding.only(left=24, right=24, top=14, bottom=4),
    )

    return ft.Column(
        controls=[toggle_row, body_holder],
        spacing=0,
        expand=True,
        tight=True,
    )
