"""Application shell.

Owns three pieces of state - active section, theme mode, language - and
wires the auto-discovered section registry into the three-column layout.
This file should NOT reference any individual section by key. Adding a
new section happens by creating a folder under ``src/sections/`` (see
``src/sections/SECTION_TEMPLATE/``).
"""

from __future__ import annotations

import flet as ft

from src.components.context_panel import empty_context_panel
from src.components.sidebar import sidebar
from src.i18n import DEFAULT_LANG, normalize_lang
from src.sections import SECTION_BY_KEY, SECTIONS
from src.theme import get_theme


class AIHubApp:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.active_section: str = SECTIONS[0].key if SECTIONS else ""
        self.theme_mode: str = "dark"
        self.lang: str = DEFAULT_LANG
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

    def set_section(self, key: str) -> None:
        if key == self.active_section:
            return
        if key not in SECTION_BY_KEY:
            return
        self.active_section = key
        self.build()

    def toggle_theme(self) -> None:
        self.theme_mode = "light" if self.theme_mode == "dark" else "dark"
        self.page.theme_mode = (
            ft.ThemeMode.LIGHT if self.theme_mode == "light" else ft.ThemeMode.DARK
        )
        self.build()

    def toggle_lang(self) -> None:
        self.lang = "cs" if self.lang == "en" else "en"
        self.lang = normalize_lang(self.lang)
        self.build()

    def _build_main(self, theme) -> ft.Control:
        section = SECTION_BY_KEY.get(self.active_section)
        if section is None and SECTIONS:
            section = SECTIONS[0]
        if section is None:
            return ft.Container()
        return section.build_view(theme, self.lang)

    def _build_context(self, theme) -> ft.Control:
        section = SECTION_BY_KEY.get(self.active_section)
        if section and section.build_context:
            return section.build_context(theme, self.lang)
        return empty_context_panel(theme)

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
                    lang=self.lang,
                    active_section=self.active_section,
                    on_section_change=self.set_section,
                    theme_mode=self.theme_mode,
                    on_theme_toggle=self.toggle_theme,
                    on_lang_toggle=self.toggle_lang,
                ),
                main_content,
                self._build_context(theme),
            ],
            spacing=0,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        self.page.controls.clear()
        self.page.add(layout)
        self.page.update()
