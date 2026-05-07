"""Application shell.

Owns three pieces of state - active section, theme mode, language - and
wires the auto-discovered section registry into the three-column layout.
This file should NOT reference any individual section by key. Adding a
new section happens by creating a folder under ``src/sections/`` (see
``src/sections/SECTION_TEMPLATE/``).

Section clicks do an in-place swap of the center + right panels (and
re-highlight the sidebar row) instead of rebuilding the whole page;
without this, the marketing/career sections feel sluggish to switch into
because the sidebar + heavy phone mockup get re-instantiated every time.
Theme and language toggles still do a full rebuild - they affect every
control in the tree, so a partial update is not worth the complexity.
"""

from __future__ import annotations

from typing import Optional

import flet as ft

from src.components.context_panel import empty_context_panel
from src.components.sidebar import SetActive, sidebar
from src.i18n import DEFAULT_LANG, normalize_lang
from src.sections import SECTION_BY_KEY, SECTIONS
from src.sections._base import Section
from src.theme import Theme, get_theme


class AIHubApp:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.active_section: str = SECTIONS[0].key if SECTIONS else ""
        self.theme_mode: str = "dark"
        self.lang: str = DEFAULT_LANG

        self._main_container: Optional[ft.Container] = None
        self._context_container: Optional[ft.Container] = None
        self._sidebar_set_active: Optional[SetActive] = None

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

        if (
            self._main_container is None
            or self._context_container is None
            or self._sidebar_set_active is None
        ):
            self.active_section = key
            self.build()
            return

        section = SECTION_BY_KEY[key]
        section_theme = self._section_theme(section)

        # Build the new section's center + context views BEFORE mutating
        # ``self.active_section`` and the live containers. If a section's
        # ``build_view`` raises (e.g. a stale Flet state from the previous
        # section), we want the click to be a no-op - not a half-applied
        # navigation that hides the sidebar from accepting any further
        # clicks on the same key (since ``set_section`` short-circuits
        # when ``key == self.active_section``).
        try:
            new_main = section.build_view(section_theme, self.lang)
            new_context = self._build_context_for(section, section_theme)
        except Exception:
            return

        self.active_section = key
        self._main_container.content = new_main
        self._context_container.content = new_context

        self._sidebar_set_active(key)
        try:
            self._main_container.update()
        except Exception:
            pass
        try:
            self._context_container.update()
        except Exception:
            pass
        try:
            self.page.update()
        except Exception:
            pass

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

    def _section_theme(self, section: Optional[Section]) -> Theme:
        base_theme = get_theme(self.theme_mode)
        if section and section.accent:
            return base_theme.with_accent(section.accent)
        return base_theme

    def _build_context_for(self, section: Optional[Section], theme: Theme) -> ft.Control:
        if section and section.build_context:
            return section.build_context(theme, self.lang)
        return empty_context_panel(theme)

    def _resolve_section(self) -> Optional[Section]:
        section = SECTION_BY_KEY.get(self.active_section)
        if section is None and SECTIONS:
            section = SECTIONS[0]
        return section

    def build(self) -> None:
        section = self._resolve_section()
        section_theme = self._section_theme(section)

        self.page.bgcolor = section_theme.bg

        main_view = section.build_view(section_theme, self.lang) if section else ft.Container()
        context_view = self._build_context_for(section, section_theme)

        self._main_container = ft.Container(
            content=main_view,
            expand=True,
            bgcolor=section_theme.bg,
        )
        self._context_container = ft.Container(content=context_view)

        sidebar_container, set_active = sidebar(
            section_theme,
            lang=self.lang,
            active_section=self.active_section,
            on_section_change=self.set_section,
            theme_mode=self.theme_mode,
            on_theme_toggle=self.toggle_theme,
            on_lang_toggle=self.toggle_lang,
        )
        self._sidebar_set_active = set_active

        layout = ft.Row(
            controls=[
                sidebar_container,
                self._main_container,
                self._context_container,
            ],
            spacing=0,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        self.page.controls.clear()
        self.page.add(layout)
        self.page.update()
