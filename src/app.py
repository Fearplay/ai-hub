"""Hlavní třída aplikace - drží stav, vykresluje tříslupcový layout."""

from __future__ import annotations

import flet as ft

from src.components.context_panel import context_panel
from src.components.sidebar import sidebar
from src.data.mock import NAV_ITEMS, SECONDARY_NAV
from src.theme import get_theme
from src.views.chat_view import chat_view
from src.views.placeholder_view import placeholder_view


CHAT_SECTION = "ai_career"


class AIHubApp:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.active_section: str = CHAT_SECTION
        self.theme_mode: str = "dark"
        self._configure_page()

    def _configure_page(self) -> None:
        self.page.title = "AI Hub"
        self.page.padding = 0
        self.page.spacing = 0
        self.page.theme_mode = ft.ThemeMode.DARK

        try:
            self.page.window.width = 1280
            self.page.window.height = 820
            self.page.window.min_width = 1080
            self.page.window.min_height = 680
        except AttributeError:
            self.page.window_width = 1280
            self.page.window_height = 820
            self.page.window_min_width = 1080
            self.page.window_min_height = 680

    def _label_for_section(self, key: str) -> str:
        for item in (*NAV_ITEMS, *SECONDARY_NAV):
            if item["key"] == key:
                return item["label"]
        return ""

    def set_section(self, key: str) -> None:
        if key == self.active_section:
            return
        self.active_section = key
        self.build()

    def toggle_theme(self) -> None:
        self.theme_mode = "light" if self.theme_mode == "dark" else "dark"
        self.page.theme_mode = (
            ft.ThemeMode.LIGHT if self.theme_mode == "light" else ft.ThemeMode.DARK
        )
        self.build()

    def _build_main(self, theme) -> ft.Control:
        if self.active_section == CHAT_SECTION:
            return chat_view(theme)
        return placeholder_view(theme, self._label_for_section(self.active_section))

    def build(self) -> None:
        theme = get_theme(self.theme_mode)
        self.page.bgcolor = theme.bg

        main_content = ft.Container(
            content=self._build_main(theme),
            expand=True,
            bgcolor=theme.bg,
        )

        layout = ft.Row(
            controls=[
                sidebar(
                    theme,
                    active_section=self.active_section,
                    on_section_change=self.set_section,
                    theme_mode=self.theme_mode,
                    on_theme_toggle=self.toggle_theme,
                ),
                main_content,
                context_panel(theme),
            ],
            spacing=0,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        self.page.controls.clear()
        self.page.add(layout)
        self.page.update()
