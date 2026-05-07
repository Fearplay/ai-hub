"""AI Career - right-hand context panel (Context, Quick actions, History)."""

from __future__ import annotations

import flet as ft

from src.components.context_panel import (
    add_document_button,
    context_panel_shell,
    history_column,
    quick_actions_column,
)
from src.components.document_chip import document_chip
from src.components.section_card import section_card
from src.i18n import t
from src.sections.ai_career.data import context_docs, history, quick_actions
from src.theme import Theme


def build_context(theme: Theme, lang: str) -> ft.Container:
    docs_content = ft.Column(
        controls=[
            ft.Text(
                t("attached_documents", lang),
                color=theme.text_muted,
                size=11,
                weight=ft.FontWeight.W_500,
            ),
            *[
                document_chip(theme, lang, name=d["name"], ext=d["type"], size=d["size"])
                for d in context_docs(lang)
            ],
            add_document_button(theme, lang),
        ],
        spacing=10,
        tight=True,
    )

    return context_panel_shell(
        theme,
        section_card(
            theme,
            ft.Icons.INFO_OUTLINE,
            t("context_title", lang),
            docs_content,
            action_label=t("manage", lang),
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
            t("conversation_history", lang),
            history_column(theme, history(lang)),
            action_label=t("show_all", lang),
        ),
    )
