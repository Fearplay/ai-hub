"""Hlavní view - chat AI Životopis / Kariéra (to z obrázku)."""

from __future__ import annotations

import flet as ft

from src.components.chat_input import chat_input
from src.components.chat_message import chat_message
from src.components.header import header
from src.components.tab_bar import tab_bar
from src.data.mock import MESSAGES
from src.theme import Theme


def chat_view(theme: Theme) -> ft.Column:
    messages_list = ft.ListView(
        controls=[chat_message(theme, **m) for m in MESSAGES],
        spacing=22,
        padding=ft.padding.symmetric(horizontal=24, vertical=20),
        expand=True,
        auto_scroll=False,
    )

    return ft.Column(
        controls=[
            header(theme),
            tab_bar(theme, active="chat"),
            messages_list,
            chat_input(theme),
        ],
        spacing=0,
        expand=True,
        tight=True,
    )
