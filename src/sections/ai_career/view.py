"""AI Career - main center view.

The first tab keeps the existing CV chat mockup; the second tab swaps in
a "Form mode" preview powered by the shared :func:`mock_form_panel`.
"""

from __future__ import annotations

import flet as ft

from src.components.chat_input import chat_input
from src.components.chat_message import chat_message
from src.components.header import header
from src.components.mock_panel import mock_form_panel
from src.components.tabbed_panel import tabbed_panel
from src.sections.ai_career.data import SECTION_ICON, messages
from src.sections.ai_career.strings import s
from src.theme import Theme


def _chat_panel(theme: Theme, lang: str) -> ft.Control:
    return ft.ListView(
        controls=[
            chat_message(theme, lang, avatar_icon=SECTION_ICON, **m)
            for m in messages(lang)
        ],
        spacing=22,
        padding=ft.padding.symmetric(horizontal=24, vertical=20),
        expand=True,
        auto_scroll=False,
    )


def _form_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    fields = [
        {"label": txt["form_field_name"], "hint": txt["form_field_name_hint"]},
        {"label": txt["form_field_email"], "hint": txt["form_field_email_hint"]},
        {"label": txt["form_field_position"], "hint": txt["form_field_position_hint"]},
        {"label": txt["form_field_experience"], "hint": txt["form_field_experience_hint"]},
        {"label": txt["form_field_skills"], "hint": txt["form_field_skills_hint"], "multiline": True},
        {"label": txt["form_field_languages"], "hint": txt["form_field_languages_hint"]},
    ]
    return mock_form_panel(
        theme,
        lang,
        icon=ft.Icons.ARTICLE_OUTLINED,
        title=txt["form_title"],
        description=txt["form_desc"],
        fields=fields,
        button_label=txt["form_btn_generate"],
        examples=[txt["form_example_1"], txt["form_example_2"], txt["form_example_3"]],
    )


def build_view(theme: Theme, lang: str) -> ft.Column:
    txt = s(lang)

    return ft.Column(
        controls=[
            header(
                theme,
                lang,
                icon=SECTION_ICON,
                title=txt["title"],
                subtitle=txt["subtitle"],
            ),
            tabbed_panel(
                theme,
                tabs=[txt["tab_chat"], txt["tab_form"]],
                panels=[_chat_panel(theme, lang), _form_panel(theme, lang)],
            ),
            chat_input(theme, lang),
        ],
        spacing=0,
        expand=True,
        tight=True,
    )
