"""AI LinkedIn - main center view (Chat + Builder modes).

Mirrors the Career section's layout pattern:

* Top header with the section icon, title, subtitle, ``?`` how-to and an
  overflow menu (New build / Save complete profile / Open run folder /
  Show history / How to use).
* Mode tab bar (Chat vs. Builder).
* In Chat mode the body is the LinkedIn voice chat (analogous to
  AI Career's chat mode).
* In Builder mode a four-tab bar (Setup / Sections / Output / History)
  drives the structured profile pipeline.

State persists in :data:`STATE` so theme / language toggles never throw
away the in-flight build. Re-renders go through ``request_section_refresh``
and worker threads dispatch via :class:`REFS`.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading

import flet as ft

from src.components.header import HeaderMenuItem, header
from src.components.tab_bar import tab_bar
from src.sections.ai_linkedin import pipeline
from src.sections.ai_linkedin.data import SECTION_ICON, builder_tabs, mode_tabs
from src.sections.ai_linkedin.how_to import open_linkedin_how_to
from src.sections.ai_linkedin.refs import REFS, safe
from src.sections.ai_linkedin.state import (
    MODE_BUILDER,
    MODE_CHAT,
    STATE,
    TAB_HISTORY,
    TAB_OUTPUT,
    TAB_SECTIONS,
    TAB_SETUP,
)
from src.sections.ai_linkedin.strings import s
from src.sections.ai_linkedin.tab_chat import build_chat_tab
from src.sections.ai_linkedin.tab_history import build_history_tab
from src.sections.ai_linkedin.tab_output import build_output_tab
from src.sections.ai_linkedin.tab_sections import build_sections_tab
from src.sections.ai_linkedin.tab_setup import build_setup_tab
from src.services import logger as logger_service
from src.services import store
from src.theme import Theme


def _refresh() -> None:
    """Trigger a full section rebuild via the app shell.

    Imported lazily so this module can be imported during section
    auto-discovery without forcing :mod:`src.app` to load first.
    """
    from src.app import request_section_refresh

    request_section_refresh()


def _open_in_explorer(path: str) -> None:
    if not path or not os.path.isdir(path):
        logger_service.log_event(
            "WARNING", "ai_linkedin.view", "open_in_explorer_no_path",
            path=str(path),
        )
        return
    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        logger_service.log_event(
            "INFO", "ai_linkedin.view", "open_in_explorer", path=path,
        )
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.view", "open_in_explorer_failed", exc, path=path,
        )


def _show_snack(page: ft.Page | None, message: str) -> None:
    if page is None or not message:
        return
    try:
        page.snack_bar = ft.SnackBar(content=ft.Text(message))
        page.snack_bar.open = True
        page.update()
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.view", "show_snack_failed", exc,
        )


def _build_builder_body(theme: Theme, lang: str) -> ft.Control:
    if STATE.active_tab == TAB_SECTIONS:
        return build_sections_tab(
            theme,
            lang,
            on_request_rerender=_refresh,
            on_navigate_tab=_navigate_tab,
        )
    if STATE.active_tab == TAB_OUTPUT:
        return build_output_tab(
            theme,
            lang,
            on_request_rerender=_refresh,
            on_navigate_tab=_navigate_tab,
        )
    if STATE.active_tab == TAB_HISTORY:
        return build_history_tab(
            theme,
            lang,
            on_request_rerender=_refresh,
            on_navigate_tab=_navigate_tab,
        )
    return build_setup_tab(
        theme,
        lang,
        on_request_rerender=_refresh,
        on_navigate_tab=_navigate_tab,
    )


def _navigate_tab(index: int) -> None:
    """Programmatic navigation hook handed to child tabs."""
    logger_service.log_event(
        "INFO",
        "ai_linkedin.view",
        "navigate_tab",
        prev_mode=STATE.mode,
        prev_tab=STATE.active_tab,
        new_tab=index,
    )
    STATE.mode = MODE_BUILDER
    STATE.active_tab = index
    _refresh()


def build_view(theme: Theme, lang: str) -> ft.Column:
    txt = s(lang)

    def _capture_page() -> None:
        try:
            from src.app import get_active_page
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.view", "capture_page_import_failed", exc,
            )
            return
        page = get_active_page()
        if page is not None:
            REFS.page = page

    def _on_stage_tab_change(index: int) -> None:
        logger_service.log_event(
            "INFO",
            "ai_linkedin.view",
            "stage_tab_change",
            index=index,
            prev_tab=STATE.active_tab,
            mode=STATE.mode,
        )
        if STATE.mode != MODE_BUILDER:
            logger_service.log_event(
                "DEBUG", "ai_linkedin.view", "stage_tab_ignored_mode",
                mode=STATE.mode,
            )
            return
        if index == STATE.active_tab:
            return
        STATE.active_tab = index
        _refresh()

    def _on_mode_change(index: int) -> None:
        new_mode = MODE_CHAT if index == 0 else MODE_BUILDER
        logger_service.log_event(
            "INFO",
            "ai_linkedin.view",
            "mode_change",
            index=index,
            prev_mode=STATE.mode,
            new_mode=new_mode,
        )
        if new_mode == STATE.mode:
            return
        STATE.mode = new_mode
        _refresh()

    mode_tab_bar = tab_bar(
        theme,
        tabs=mode_tabs(lang),
        active_index=0 if STATE.mode == MODE_CHAT else 1,
        on_change=_on_mode_change,
    )
    if STATE.mode == MODE_CHAT:
        stage_tab_bar_control: ft.Control = ft.Container(height=0)
    else:
        stage_tab_bar_control = tab_bar(
            theme,
            tabs=builder_tabs(lang),
            active_index=STATE.active_tab,
            on_change=_on_stage_tab_change,
        )

    if STATE.mode == MODE_CHAT:
        body_control: ft.Control = build_chat_tab(
            theme,
            lang,
            on_request_rerender=_refresh,
            on_navigate_tab=_navigate_tab,
            on_switch_to_builder=_refresh,
        )
    else:
        body_control = _build_builder_body(theme, lang)

    content_holder = ft.Container(content=body_control, expand=True)
    _capture_page()

    def _on_help(e: ft.ControlEvent) -> None:
        if e.page is None:
            return
        REFS.page = e.page
        open_linkedin_how_to(e.page, theme, lang)

    def _menu_new_build(_e: ft.ControlEvent) -> None:
        logger_service.log_event("INFO", "ai_linkedin.view", "menu_new_build")
        STATE.reset_all()
        STATE.mode = MODE_BUILDER
        STATE.active_tab = TAB_SETUP
        _refresh()

    def _menu_open_history(_e: ft.ControlEvent) -> None:
        logger_service.log_event("INFO", "ai_linkedin.view", "menu_open_history")
        STATE.mode = MODE_BUILDER
        STATE.active_tab = TAB_HISTORY
        _refresh()

    def _menu_open_folder(e: ft.ControlEvent) -> None:
        page = e.page
        if page is not None:
            REFS.page = page
        try:
            store.ensure_dirs()
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.view", "menu_open_folder_ensure_dirs", exc,
            )
        outputs_root = str(store.runs_dir())
        logger_service.log_event(
            "INFO", "ai_linkedin.view", "menu_open_folder", path=outputs_root,
        )
        if not os.path.isdir(outputs_root):
            _show_snack(page, txt["history_empty_desc"])
            return
        _open_in_explorer(outputs_root)

    def _menu_save_full(e: ft.ControlEvent) -> None:
        page = e.page
        if page is not None:
            REFS.page = page
        if not STATE.has_results():
            logger_service.log_event(
                "WARNING", "ai_linkedin.view", "menu_save_full_empty",
            )
            _show_snack(page, txt["error_no_inputs"])
            return
        logger_service.log_event(
            "INFO",
            "ai_linkedin.view",
            "menu_save_full_start",
            has_about=bool(STATE.about_variants),
            has_headlines=bool(STATE.headlines),
        )
        STATE.activity = "saving"
        STATE.last_error = ""
        safe(REFS.rerender_context)
        REFS.dispatch(_refresh)

        def _worker() -> None:
            try:
                result = pipeline.save_full_profile()
            except Exception as exc:
                logger_service.log_exception(
                    "ai_linkedin.view", "menu_save_full_worker", exc,
                )
                result = None  # type: ignore[assignment]
            STATE.activity = "ready"
            REFS.request_context_refresh()
            if result is not None:
                logger_service.log_event(
                    "INFO" if result.ok else "ERROR",
                    "ai_linkedin.view",
                    "menu_save_full_done",
                    ok=result.ok,
                    folder=result.folder,
                    error=result.error,
                )
            if result is not None and result.ok and page is not None:
                try:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(
                            f"{txt['menu_save_full']}: {result.folder}"
                        ),
                    )
                    page.snack_bar.open = True
                except Exception as exc:
                    logger_service.log_exception(
                        "ai_linkedin.view", "menu_save_full_snack", exc,
                    )
            REFS.dispatch(_refresh)

        threading.Thread(target=_worker, daemon=True).start()

    def _menu_how_to(e: ft.ControlEvent) -> None:
        if e.page is None:
            return
        REFS.page = e.page
        open_linkedin_how_to(e.page, theme, lang)

    has_results = STATE.has_results()

    menu_items: list[HeaderMenuItem] = [
        HeaderMenuItem(
            icon=ft.Icons.RESTART_ALT,
            label=txt["menu_new_build"],
            on_click=_menu_new_build,
        ),
        HeaderMenuItem(
            icon=ft.Icons.SAVE_OUTLINED,
            label=txt["menu_save_full"],
            on_click=_menu_save_full,
            enabled=has_results,
        ),
        HeaderMenuItem(
            icon=ft.Icons.FOLDER_OPEN,
            label=txt["menu_open_folder"],
            on_click=_menu_open_folder,
        ),
        HeaderMenuItem(
            icon=ft.Icons.HISTORY,
            label=txt["menu_show_history"],
            on_click=_menu_open_history,
        ),
        HeaderMenuItem(
            icon=ft.Icons.MENU_BOOK_OUTLINED,
            label=txt["menu_how_to"],
            on_click=_menu_how_to,
        ),
    ]

    demo_pill: ft.Control | None = None
    if STATE.demo_mode:
        demo_pill = ft.Container(
            content=ft.Text(
                txt["demo_pill"],
                color=ft.Colors.WHITE,
                size=11,
                weight=ft.FontWeight.W_700,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
            bgcolor="#F59E0B",
            border_radius=10,
            tooltip=txt["demo_pill_tooltip"],
        )

    header_control = header(
        theme,
        lang,
        icon=SECTION_ICON,
        title=txt["title"],
        subtitle=txt["subtitle"],
        on_help_click=_on_help,
        trailing=demo_pill,
        menu_items=menu_items,
    )

    return ft.Column(
        controls=[
            header_control,
            mode_tab_bar,
            stage_tab_bar_control,
            content_holder,
        ],
        spacing=0,
        expand=True,
        tight=True,
    )
