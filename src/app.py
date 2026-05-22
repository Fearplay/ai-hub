"""Application shell.

Owns three pieces of state - active section, theme mode, language - and
wires the auto-discovered section registry into the three-column layout.
This file should NOT reference any individual section by key. Adding a
new section happens by creating a folder under ``src/sections/`` (see
``src/sections/SECTION_TEMPLATE/``).

Section clicks do an in-place swap of the center + right panels (and
re-highlight the sidebar row) instead of rebuilding the whole window;
without this, the marketing/career sections feel sluggish to switch into
because the sidebar + heavy phone mockup get re-instantiated every time.
Theme and language toggles also use the same in-place swap (sidebar +
active section + context) instead of rebuilding the entire window -
:meth:`AIHubApp._smart_rebuild` is the single place that does it. The
:meth:`AIHubApp.build` path is only hit on the very first show.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QStackedLayout,
    QWidget,
)

from src.components.context_panel import empty_context_panel
from src.components.sidebar import SetActive, sidebar
from src.i18n import DEFAULT_LANG, normalize_lang
from src.qt import qss_for_theme
from src.qt import runtime as qt_runtime
from src.qt.window_chrome import apply_title_bar_theme
from src.sections import SECTION_BY_KEY, SECTIONS
from src.sections._base import Section
from src.services import logger as logger_service
from src.services import settings_store
from src.theme import Theme, get_theme


_active_app: Optional["AIHubApp"] = None


def request_section_refresh() -> None:
    """Re-run ``section.build_view()`` for the currently active section.

    Safe to call from any thread - the dispatcher in
    :mod:`src.qt.runtime` queues the work onto the GUI loop. Workers
    that prepared state on a daemon thread can call this directly
    without worrying about which thread is running.
    """
    if _active_app is None:
        logger_service.log_event(
            "WARNING", "app", "request_section_refresh_no_app"
        )
        return
    qt_runtime.dispatch(_active_app._refresh_active_section)


def request_sidebar_refresh() -> None:
    """Re-run the in-place sidebar + section rebuild on the GUI thread.

    Called after a sidebar drag-and-drop reorder so the new section
    order is reflected immediately. ``request_section_refresh`` only
    swaps the centre + right panels, which leaves the sidebar nav rows
    stale until the user happens to toggle the language. Routing the
    drop event through this helper takes the user-visible delay back
    down to one frame.

    Safe to call from any thread - dispatched onto the Qt loop via
    :mod:`src.qt.runtime`.
    """
    if _active_app is None:
        logger_service.log_event(
            "WARNING", "app", "request_sidebar_refresh_no_app"
        )
        return
    qt_runtime.dispatch(_active_app._smart_rebuild)


def get_active_window() -> Optional[QMainWindow]:
    """Return the live ``QMainWindow`` for the currently running app."""
    if _active_app is None:
        return None
    return _active_app


# Backwards-compat shim - some callers still import ``get_active_page``
# from when the framework was Flet. They expect "the live UI host", which
# is now the main window.
get_active_page = get_active_window


class AIHubApp(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.active_section: str = SECTIONS[0].key if SECTIONS else ""
        # Persisted preferences survive app restarts. ``settings_store``
        # falls back to sane defaults ("dark" / "en") on first launch.
        self.theme_mode: str = settings_store.get_theme_mode()
        self.lang: str = normalize_lang(settings_store.get_lang() or DEFAULT_LANG)

        self._main_holder: Optional[QWidget] = None
        self._main_layout: Optional[QStackedLayout] = None
        self._context_holder: Optional[QWidget] = None
        self._context_layout: Optional[QStackedLayout] = None
        self._sidebar_set_active: Optional[SetActive] = None
        self._main_widget: Optional[QWidget] = None
        self._context_widget: Optional[QWidget] = None
        self._central_layout: Optional[QHBoxLayout] = None
        self._sidebar_widget: Optional[QWidget] = None

        global _active_app
        _active_app = self
        qt_runtime.set_main_window(self)

        self._configure_window()
        logger_service.log_event(
            "INFO",
            "app",
            "boot",
            theme_mode=self.theme_mode,
            lang=self.lang,
            active_section=self.active_section,
            sections=len(SECTIONS),
        )

    # --- window setup -------------------------------------------------------

    def _configure_window(self) -> None:
        self.setWindowTitle("AI Hub")
        self.resize(1280, 820)
        # Keep enough room for the three-column shell plus document preview.
        self.setMinimumSize(1220, 760)

    def _apply_title_bar(self) -> None:
        """Recolour the OS title bar to match the active theme.

        Safe to call before ``show()`` (the helper short-circuits on a
        zero ``winId``) and from any thread that ends up on the GUI
        loop. We call it from ``showEvent`` so we always tint after Qt
        has materialised the HWND and again on every theme toggle.
        """
        try:
            apply_title_bar_theme(self, get_theme(self.theme_mode), self.theme_mode)
        except Exception as exc:
            logger_service.log_exception("app", "apply_title_bar_failed", exc)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._apply_title_bar()

    # --- public API (called by sections via this module) -------------------

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
            self._main_layout is None
            or self._context_layout is None
            or self._sidebar_set_active is None
        ):
            self.active_section = key
            self.build()
            return

        section = SECTION_BY_KEY[key]
        section_theme = self._section_theme(section)

        new_main = section.safe_build_view(section_theme, self.lang)
        new_context = self._safe_context_for(section, section_theme)

        self.active_section = key
        self._swap_main(new_main)
        self._swap_context(new_context)

        self._sidebar_set_active(key)
        self._apply_global_qss(section_theme)

    def _refresh_active_section(self) -> None:
        """Rebuild the currently active section's center + right column."""
        if self._main_layout is None or self._context_layout is None:
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
        self._swap_main(new_main)
        self._swap_context(new_context)

    def toggle_theme(self) -> None:
        prev = self.theme_mode
        self.theme_mode = "light" if self.theme_mode == "dark" else "dark"
        try:
            settings_store.set_theme_mode(self.theme_mode)
        except Exception as exc:
            logger_service.log_exception("app", "toggle_theme_persist", exc)
        logger_service.log_event(
            "INFO", "app", "toggle_theme", from_=prev, to=self.theme_mode
        )
        self._apply_title_bar()
        # Run the rebuild on the next event-loop tick so the toggle pill
        # repaints first - the click feels instantaneous even though the
        # rebuild itself takes a few hundred ms on heavy sections.
        qt_runtime.dispatch(self._smart_rebuild)

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
        qt_runtime.dispatch(self._smart_rebuild)

    # --- internals ---------------------------------------------------------

    def _section_theme(self, section: Optional[Section]) -> Theme:
        base_theme = get_theme(self.theme_mode)
        if section and section.accent:
            return base_theme.with_accent(section.accent)
        return base_theme

    def _safe_context_for(self, section: Optional[Section], theme: Theme) -> QWidget:
        if section and section.build_context:
            return section.safe_build_context(theme, self.lang)
        if section and section.wide_layout:
            return QWidget()
        return empty_context_panel(theme)

    def _resolve_section(self) -> Optional[Section]:
        section = SECTION_BY_KEY.get(self.active_section)
        if section is None and SECTIONS:
            section = SECTIONS[0]
        return section

    def _apply_global_qss(self, theme: Theme) -> None:
        qss = qss_for_theme(theme)
        try:
            QApplication.instance().setStyleSheet(qss)
        except Exception as exc:
            logger_service.log_exception("app", "apply_global_qss_failed", exc)

    def _swap_main(self, new_widget: QWidget) -> None:
        if self._main_layout is None:
            return
        if self._main_widget is not None:
            self._main_layout.removeWidget(self._main_widget)
            self._main_widget.deleteLater()
        self._main_widget = new_widget
        self._main_layout.addWidget(new_widget)
        self._main_layout.setCurrentWidget(new_widget)

    def _swap_context(self, new_widget: QWidget) -> None:
        if self._context_layout is None:
            return
        if self._context_widget is not None:
            self._context_layout.removeWidget(self._context_widget)
            self._context_widget.deleteLater()
        self._context_widget = new_widget
        self._context_layout.addWidget(new_widget)
        self._context_layout.setCurrentWidget(new_widget)

    def _swap_sidebar(self, new_widget: QWidget, set_active: SetActive) -> None:
        if self._central_layout is None:
            return
        if self._sidebar_widget is not None:
            self._central_layout.removeWidget(self._sidebar_widget)
            self._sidebar_widget.deleteLater()
        self._sidebar_widget = new_widget
        self._central_layout.insertWidget(0, new_widget)
        self._sidebar_set_active = set_active

    def _smart_rebuild(self) -> None:
        """In-place rebuild of sidebar + active section + context.

        Triggered by ``toggle_theme`` / ``toggle_lang``. Avoids
        recreating the central widget / outer layout (and the heavy
        ``QStackedLayout`` plumbing) so the click feels snappy even on
        the Career section's modern-CV renderer. Other sections are
        left dormant - they pick up the new lang / accent on their
        next ``set_section`` call which already runs ``safe_build_view``.
        """
        if (
            self._central_layout is None
            or self._main_layout is None
            or self._context_layout is None
        ):
            # First show: the central widget hasn't been built yet.
            self.build()
            return

        logger_service.log_event(
            "DEBUG", "app", "smart_rebuild",
            section=self.active_section, lang=self.lang, theme_mode=self.theme_mode,
        )

        section = self._resolve_section()
        section_theme = self._section_theme(section)
        self._apply_global_qss(section_theme)

        sidebar_widget, set_active = sidebar(
            section_theme,
            lang=self.lang,
            active_section=self.active_section,
            on_section_change=self.set_section,
            theme_mode=self.theme_mode,
            on_theme_toggle=self.toggle_theme,
            on_lang_toggle=self.toggle_lang,
        )
        self._swap_sidebar(sidebar_widget, set_active)

        new_main = (
            section.safe_build_view(section_theme, self.lang)
            if section
            else QWidget()
        )
        new_context = self._safe_context_for(section, section_theme)
        self._swap_main(new_main)
        self._swap_context(new_context)

        central = self.centralWidget()
        if central is not None:
            central.setStyleSheet(f"background-color: {section_theme.bg};")
        for holder in (self._main_holder, self._context_holder):
            if holder is not None:
                holder.setStyleSheet(f"background-color: {section_theme.bg};")

    # --- build -------------------------------------------------------------

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
        self._apply_global_qss(section_theme)

        main_view = (
            section.safe_build_view(section_theme, self.lang)
            if section
            else QWidget()
        )
        context_view = self._safe_context_for(section, section_theme)

        # Build the three-column layout from scratch on theme/lang
        # changes (the toggles affect every widget in the tree).
        central = QWidget()
        central.setStyleSheet(f"background-color: {section_theme.bg};")
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._central_layout = layout

        sidebar_widget, set_active = sidebar(
            section_theme,
            lang=self.lang,
            active_section=self.active_section,
            on_section_change=self.set_section,
            theme_mode=self.theme_mode,
            on_theme_toggle=self.toggle_theme,
            on_lang_toggle=self.toggle_lang,
        )
        self._sidebar_set_active = set_active
        self._sidebar_widget = sidebar_widget
        layout.addWidget(sidebar_widget)

        main_holder = QWidget()
        main_holder.setStyleSheet(f"background-color: {section_theme.bg};")
        main_stack = QStackedLayout(main_holder)
        main_stack.setContentsMargins(0, 0, 0, 0)
        main_stack.setSpacing(0)
        main_stack.addWidget(main_view)
        main_stack.setCurrentWidget(main_view)
        self._main_holder = main_holder
        self._main_layout = main_stack
        self._main_widget = main_view
        layout.addWidget(main_holder, 1)

        context_holder = QWidget()
        context_holder.setStyleSheet(f"background-color: {section_theme.bg};")
        context_stack = QStackedLayout(context_holder)
        context_stack.setContentsMargins(0, 0, 0, 0)
        context_stack.setSpacing(0)
        context_stack.addWidget(context_view)
        context_stack.setCurrentWidget(context_view)
        self._context_holder = context_holder
        self._context_layout = context_stack
        self._context_widget = context_view
        layout.addWidget(context_holder)

        self.setCentralWidget(central)

    # --- shutdown ----------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        logger_service.log_event("INFO", "app", "shutdown")
        super().closeEvent(event)
