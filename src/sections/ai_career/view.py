"""AI Career - main center view (chat with the existing CV mockup)."""

from __future__ import annotations

import flet as ft

from src.components.chat_input import chat_input
from src.components.chat_message import chat_message
from src.components.header import header
from src.components.tab_bar import tab_bar
from src.sections.ai_career.data import SECTION_ICON, messages
from src.sections.ai_career.strings import s
from src.theme import Theme


def build_view(theme: Theme, lang: str) -> ft.Column:
    txt = s(lang)

    messages_list = ft.ListView(
        controls=[
            chat_message(theme, lang, avatar_icon=SECTION_ICON, **m)
            for m in messages(lang)
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
            tab_bar(theme, tabs=[txt["tab_chat"], txt["tab_form"]], active_index=0),
            messages_list,
            chat_input(theme, lang),
        ],
        spacing=0,
        expand=True,
        tight=True,
    )
