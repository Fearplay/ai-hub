"""AI Marketing - right-hand panel (Brief, Quick actions, Recent conversations)."""

from __future__ import annotations

import flet as ft

from src.components.context_panel import (
    context_panel_shell,
    history_column,
    quick_actions_column,
)
from src.components.section_card import section_card
from src.i18n import t
from src.sections.ai_marketing.data import brief_fields, history, quick_actions
from src.sections.ai_marketing.strings import s
from src.theme import Theme


def _brief_field(theme: Theme, *, label: str, value: str, chip: bool = False) -> ft.Column:
    if chip:
        value_control = ft.Container(
            content=ft.Text(
                value,
                color=theme.text,
                size=12,
                weight=ft.FontWeight.W_500,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
            bgcolor=ft.Colors.with_opacity(0.18, theme.primary),
            border_radius=12,
            alignment=ft.Alignment.CENTER_LEFT,
        )
    else:
        value_control = ft.Text(
            value,
            color=theme.text,
            size=13,
            weight=ft.FontWeight.W_500,
        )

    label_text = ft.Text(
        label,
        color=theme.text_muted,
        size=11,
        weight=ft.FontWeight.W_500,
    )

    if chip:
        body = ft.Row(
            controls=[value_control],
            alignment=ft.MainAxisAlignment.START,
        )
    else:
        body = value_control

    return ft.Column(
        controls=[label_text, body],
        spacing=4,
        tight=True,
    )


def _brief_content(theme: Theme, lang: str) -> ft.Column:
    return ft.Column(
        controls=[
            _brief_field(
                theme,
                label=field["label"],
                value=field["value"],
                chip=field.get("chip", False),
            )
            for field in brief_fields(lang)
        ],
        spacing=12,
        tight=True,
    )


def build_context(theme: Theme, lang: str) -> ft.Container:
    txt = s(lang)

    return context_panel_shell(
        theme,
        section_card(
            theme,
            ft.Icons.DESCRIPTION_OUTLINED,
            txt["brief_title"],
            _brief_content(theme, lang),
            action_label=t("edit", lang),
        ),
        section_card(
            theme,
            ft.Icons.BOLT_OUTLINED,
            t("quick_actions", lang),
            quick_actions_column(theme, quick_actions(lang)),
        ),
        section_card(
            theme,
            ft.Icons.HISTORY,
            t("recent_conversations", lang),
            history_column(theme, history(lang)),
            action_label=t("show_all", lang),
        ),
    )
