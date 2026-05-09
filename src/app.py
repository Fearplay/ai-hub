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
from src.services import logger as logger_service
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
    if _active_app is None:
        logger_service.log_event(
            "WARNING", "app", "request_section_refresh_no_app"
        )
        return
    _active_app._refresh_active_section()


def get_active_page() -> Optional[ft.Page]:
    """Return the live ``ft.Page`` for the currently running app, if any.

    Sections used to capture the page by reading ``container.page`` after
    creating the holder - that path stopped working in Flet 0.84 because
    the property now raises ``RuntimeError`` for not-yet-mounted controls
    (Container 229 / 419 / 710 in the user log). The app instance always
    has the page handy from ``__init__``, so we expose it here so
    sections can grab it without walking the (broken) parent chain.
    """
    if _active_app is None:
        return None
    return _active_app.page


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
        logger_service.log_event(
            "INFO",
            "app",
            "boot",
            theme_mode=self.theme_mode,
            lang=self.lang,
            active_section=self.active_section,
            sections=len(SECTIONS),
        )

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
            logger_service.log_event(
                "DEBUG", "app", "set_section_noop", key=key
            )
            return
        if key not in SECTION_BY_KEY:
            logger_service.log_event(
                "WARNING", "app", "set_section_unknown", key=key
            )
            return

        logger_service.log_event(
            "INFO",
            "app",
            "set_section",
            from_key=self.active_section,
            to_key=key,
        )

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
        new_main = section.safe_build_view(section_theme, self.lang)
        new_context = self._safe_context_for(section, section_theme)

        self.active_section = key
        self._main_container.content = new_main
        self._context_container.content = new_context

        self._sidebar_set_active(key)
        try:
            self._main_container.update()
        except Exception as exc:
            logger_service.log_exception("app", "set_section_main_update", exc)
        try:
            self._context_container.update()
        except Exception as exc:
            logger_service.log_exception("app", "set_section_context_update", exc)
        try:
            self.page.update()
        except Exception as exc:
            logger_service.log_exception("app", "set_section_page_update", exc)

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
            logger_service.log_event(
                "WARNING", "app", "refresh_no_containers"
            )
            return
        section = SECTION_BY_KEY.get(self.active_section)
        if section is None:
            logger_service.log_event(
                "WARNING", "app", "refresh_no_section", key=self.active_section
            )
            return
        logger_service.log_event(
            "DEBUG", "app", "refresh_active_section", key=self.active_section
        )
        section_theme = self._section_theme(section)
        new_main = section.safe_build_view(section_theme, self.lang)
        new_context = self._safe_context_for(section, section_theme)
        self._main_container.content = new_main
        self._context_container.content = new_context
        try:
            self._main_container.update()
        except Exception as exc:
            logger_service.log_exception("app", "refresh_main_update", exc)
        try:
            self._context_container.update()
        except Exception as exc:
            logger_service.log_exception("app", "refresh_context_update", exc)
        try:
            self.page.update()
        except Exception as exc:
            logger_service.log_exception("app", "refresh_page_update", exc)

    def toggle_theme(self) -> None:
        prev = self.theme_mode
        self.theme_mode = "light" if self.theme_mode == "dark" else "dark"
        try:
            self.page.theme_mode = (
                ft.ThemeMode.LIGHT if self.theme_mode == "light" else ft.ThemeMode.DARK
            )
        except Exception as exc:
            logger_service.log_exception("app", "toggle_theme_set_mode", exc)
        try:
            settings_store.set_theme_mode(self.theme_mode)
        except Exception as exc:
            logger_service.log_exception("app", "toggle_theme_persist", exc)
        logger_service.log_event(
            "INFO", "app", "toggle_theme", from_=prev, to=self.theme_mode
        )
        self._schedule_rebuild()

    def toggle_lang(self) -> None:
        prev = self.lang
        self.lang = "cs" if self.lang == "en" else "en"
        self.lang = normalize_lang(self.lang)
        try:
            settings_store.set_lang(self.lang)
        except Exception as exc:
            logger_service.log_exception("app", "toggle_lang_persist", exc)
        logger_service.log_event(
            "INFO", "app", "toggle_lang", from_=prev, to=self.lang
        )
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
        except Exception as exc:
            logger_service.log_exception("app", "schedule_rebuild_loop_lookup", exc)
            loop = None
        if loop is None:
            logger_service.log_event(
                "DEBUG", "app", "schedule_rebuild_sync"
            )
            try:
                self.build()
            except Exception as exc:
                logger_service.log_exception("app", "schedule_rebuild_sync_build", exc)
            return
        logger_service.log_event(
            "DEBUG", "app", "schedule_rebuild_async"
        )
        try:
            loop.call_soon_threadsafe(self._safe_rebuild)
        except Exception as exc:
            logger_service.log_exception("app", "schedule_rebuild_call_soon", exc)
            try:
                self.build()
            except Exception as exc2:
                logger_service.log_exception(
                    "app", "schedule_rebuild_fallback_build", exc2
                )

    def _safe_rebuild(self) -> None:
        logger_service.log_event("DEBUG", "app", "safe_rebuild_start")
        try:
            self.build()
        except Exception as exc:
            logger_service.log_exception("app", "safe_rebuild_build_failed", exc)
        try:
            self.page.update()
        except Exception as exc:
            logger_service.log_exception("app", "safe_rebuild_page_update", exc)

    def _section_theme(self, section: Optional[Section]) -> Theme:
        base_theme = get_theme(self.theme_mode)
        if section and section.accent:
            return base_theme.with_accent(section.accent)
        return base_theme

    def _build_context_for(self, section: Optional[Section], theme: Theme) -> ft.Control:
        if section and section.build_context:
            return section.build_context(theme, self.lang)
        if section and section.wide_layout:
            # Wide-layout sections want the right slot collapsed entirely
            # so the center body can use the full available width. A bare
            # ``ft.Container()`` has zero size and no border so the layout
            # row simply skips it.
            return ft.Container()
        return empty_context_panel(theme)

    def _safe_context_for(self, section: Optional[Section], theme: Theme) -> ft.Control:
        if section and section.build_context:
            return section.safe_build_context(theme, self.lang)
        if section and section.wide_layout:
            return ft.Container()
        return empty_context_panel(theme)

    def _resolve_section(self) -> Optional[Section]:
        section = SECTION_BY_KEY.get(self.active_section)
        if section is None and SECTIONS:
            section = SECTIONS[0]
        return section

    def build(self) -> None:
        logger_service.log_event(
            "DEBUG",
            "app",
            "build",
            section=self.active_section,
            lang=self.lang,
            theme_mode=self.theme_mode,
        )
        section = self._resolve_section()
        section_theme = self._section_theme(section)

        self.page.bgcolor = section_theme.bg

        main_view = (
            section.safe_build_view(section_theme, self.lang)
            if section
            else ft.Container()
        )
        context_view = self._safe_context_for(section, section_theme)

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
        try:
            self.page.update()
        except Exception as exc:
            logger_service.log_exception("app", "build_page_update", exc)
