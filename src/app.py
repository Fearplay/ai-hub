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
from src.services import settings_store
from src.theme import Theme, get_theme


# Module-level handle to the running app so sections can request a full
# rebuild without circular-importing the class. Sections call
# ``request_section_refresh()`` (defined below) which forwards to the live
# instance; this avoids passing ``self`` through every section's
# build_view callback chain.
_active_app: Optional["AIHubApp"] = None


def request_section_refresh() -> None:
    """Re-run ``section.build_view()`` for the currently active section.

    Safe to call from anywhere (UI thread or worker thread) - the
    underlying mutations happen synchronously, but the resulting
    ``page.update()`` is enough to flush the new tree on Windows desktop.
    Workers that want a guaranteed flush from a non-UI thread should pipe
    this through ``REFS.dispatch(request_section_refresh)`` so the call
    lands on the page's asyncio loop.
    """
    if _active_app is not None:
        _active_app._refresh_active_section()


class AIHubApp:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.active_section: str = SECTIONS[0].key if SECTIONS else ""
        # Persisted preferences survive app restarts. ``settings_store``
        # falls back to sane defaults ("dark" / "en") on first launch.
        self.theme_mode: str = settings_store.get_theme_mode()
        self.lang: str = normalize_lang(settings_store.get_lang() or DEFAULT_LANG)

        self._main_container: Optional[ft.Container] = None
        self._context_container: Optional[ft.Container] = None
        self._sidebar_set_active: Optional[SetActive] = None

        global _active_app
        _active_app = self

        self._configure_page()

    def _configure_page(self) -> None:
        self.page.title = "AI Hub"
        self.page.padding = 0
        self.page.spacing = 0
        self.page.theme_mode = (
            ft.ThemeMode.LIGHT if self.theme_mode == "light" else ft.ThemeMode.DARK
        )

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

    def _refresh_active_section(self) -> None:
        """Rebuild the currently active section's center + right column.

        Used by sections (via :func:`request_section_refresh`) when their
        internal state changes in a way that needs the entire view
        re-laid out - tab change, mode toggle, "New analysis" reset,
        worker thread completion, etc. We reuse the same machinery as
        :meth:`set_section` because the per-section ``content_holder``
        mutation pattern is unreliable for deep subtrees in Flet 0.84
        (see plan: ai-cv-refresh-fix).
        """
        if (
            self._main_container is None
            or self._context_container is None
        ):
            return
        section = SECTION_BY_KEY.get(self.active_section)
        if section is None:
            return
        section_theme = self._section_theme(section)
        try:
            new_main = section.build_view(section_theme, self.lang)
            new_context = self._build_context_for(section, section_theme)
        except Exception:
            return
        self._main_container.content = new_main
        self._context_container.content = new_context
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
        settings_store.set_theme_mode(self.theme_mode)
        self._schedule_rebuild()

    def toggle_lang(self) -> None:
        self.lang = "cs" if self.lang == "en" else "en"
        self.lang = normalize_lang(self.lang)
        settings_store.set_lang(self.lang)
        self._schedule_rebuild()

    def _schedule_rebuild(self) -> None:
        """Defer ``self.build()`` to the next event-loop tick.

        The Switch / Toggle controls in the sidebar fire ``on_change`` on
        the UI thread; if we call ``self.build()`` synchronously in that
        handler we ``page.controls.clear()`` the very Switch that is
        still mid-event, which Flet handles by freezing the whole window
        until the user restarts the app.

        Bouncing the rebuild through ``loop.call_soon`` lets the
        ``on_change`` handler return cleanly first, after which the loop
        runs ``self.build()`` and the Switch is recreated as part of the
        new tree.
        """
        loop = None
        try:
            loop = self.page.session.connection.loop
        except Exception:
            loop = None
        if loop is None:
            try:
                self.build()
            except Exception:
                pass
            return
        try:
            loop.call_soon_threadsafe(self._safe_rebuild)
        except Exception:
            try:
                self.build()
            except Exception:
                pass

    def _safe_rebuild(self) -> None:
        try:
            self.build()
        except Exception:
            pass
        try:
            self.page.update()
        except Exception:
            pass

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
