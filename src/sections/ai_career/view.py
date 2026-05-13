"""AI Career - center column orchestrator (PySide6 port)."""

from __future__ import annotations

import os
import subprocess
import sys
import threading

from PySide6.QtWidgets import QFrame, QMessageBox, QWidget

from src.components.header import HeaderMenuItem, header
from src.components.tab_bar import tab_bar
from src.qt.icons import Icons
from src.qt.runtime import dispatch as runtime_dispatch
from src.qt.runtime import get_main_window
from src.qt.widgets import vbox
from src.sections.ai_career import pipeline
from src.sections.ai_career.data import SECTION_ICON
from src.sections.ai_career.how_to import open_career_how_to
from src.sections.ai_career.refs import REFS
from src.sections.ai_career.state import (
    MODE_CHAT,
    MODE_FORM,
    STATE,
    TAB_DOCUMENTS,
    TAB_HISTORY,
    TAB_MATCH,
    TAB_SETUP,
)
from src.sections.ai_career.strings import s
from src.sections.ai_career.tab_chat import build_chat_tab
from src.sections.ai_career.tab_documents import build_documents_tab
from src.sections.ai_career.tab_history import build_history_tab
from src.sections.ai_career.tab_match import build_match_tab
from src.sections.ai_career.tab_setup import build_setup_tab
from src.services import logger as logger_service
from src.services import store
from src.theme import Theme


def _refresh() -> None:
    from src.app import request_section_refresh
    request_section_refresh()


def _open_in_explorer(path: str) -> None:
    if not path or not os.path.isdir(path):
        logger_service.log_event(
            "WARNING", "ai_career.view", "open_in_explorer_no_path", path=str(path),
        )
        return
    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as exc:
        logger_service.log_exception(
            "ai_career.view", "open_in_explorer_failed", exc, path=path,
        )


def _show_message(message: str) -> None:
    if not message:
        return
    parent = get_main_window()
    try:
        QMessageBox.information(parent, "AI Career", message)
    except Exception as exc:
        logger_service.log_exception(
            "ai_career.view", "show_message_failed", exc,
        )


def _navigate_tab(index: int) -> None:
    logger_service.log_event(
        "INFO", "ai_career.view", "navigate_tab",
        prev_mode=STATE.mode,
        prev_tab=STATE.active_tab,
        new_tab=index,
    )
    STATE.mode = MODE_FORM
    STATE.active_tab = index
    _refresh()


def _build_form_tab_body(theme: Theme, lang: str) -> QWidget:
    if STATE.active_tab == TAB_MATCH:
        return build_match_tab(theme, lang, on_request_rerender=_refresh, on_navigate_tab=_navigate_tab)
    if STATE.active_tab == TAB_DOCUMENTS:
        return build_documents_tab(theme, lang, on_request_rerender=_refresh, on_navigate_tab=_navigate_tab)
    if STATE.active_tab == TAB_HISTORY:
        return build_history_tab(theme, lang, on_request_rerender=_refresh, on_navigate_tab=_navigate_tab)
    return build_setup_tab(theme, lang, on_request_rerender=_refresh)


def _mode_tabs(lang: str) -> list[str]:
    txt = s(lang)
    return [txt["mode_chat"], txt["mode_form"]]


def _stage_tabs(lang: str) -> list[str]:
    txt = s(lang)
    return [txt["tab_setup"], txt["tab_match"], txt["tab_documents"], txt["tab_history"]]


def build_view(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    container = QFrame()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    def _on_help() -> None:
        open_career_how_to(get_main_window(), theme, lang)

    def _menu_new_run() -> None:
        logger_service.log_event("INFO", "ai_career.view", "menu_new_run")
        STATE.reset_all()
        STATE.mode = MODE_FORM
        STATE.active_tab = TAB_SETUP
        _refresh()

    def _menu_open_history() -> None:
        STATE.mode = MODE_FORM
        STATE.active_tab = TAB_HISTORY
        _refresh()

    def _menu_open_folder() -> None:
        try:
            store.ensure_dirs()
        except Exception as exc:
            logger_service.log_exception(
                "ai_career.view", "menu_open_folder_ensure_dirs", exc,
            )
        outputs_root = str(store.runs_dir())
        if not os.path.isdir(outputs_root):
            _show_message(txt["menu_open_folder_no_run"])
            return
        _open_in_explorer(outputs_root)

    def _menu_save_full() -> None:
        if not STATE.documents and not STATE.modern_cv_data:
            _show_message(txt["menu_save_no_run"])
            return
        STATE.activity = "exporting"
        STATE.last_error = ""
        REFS.request_context_refresh()
        REFS.dispatch(_refresh)

        def _worker() -> None:
            try:
                result = pipeline.save_full_analysis()
            except Exception as exc:
                logger_service.log_exception(
                    "ai_career.view", "menu_save_full_worker", exc,
                )
                result = None  # type: ignore[assignment]
            STATE.activity = "ready"
            REFS.request_context_refresh()
            if result is not None and result.ok:
                runtime_dispatch(lambda: _show_message(txt["menu_save_done_template"].format(path=result.folder)))
            REFS.dispatch(_refresh)

        threading.Thread(target=_worker, daemon=True).start()

    def _menu_how_to() -> None:
        open_career_how_to(get_main_window(), theme, lang)

    has_docs = bool(STATE.documents or STATE.modern_cv_data)

    menu_items: list[HeaderMenuItem] = [
        HeaderMenuItem(icon=Icons.POST_ADD, label=txt["menu_new_run"], on_click=_menu_new_run),
        HeaderMenuItem(icon=Icons.SAVE_OUTLINED, label=txt["menu_save_full"], on_click=_menu_save_full, enabled=has_docs),
        HeaderMenuItem(icon=Icons.FOLDER_OPEN, label=txt["menu_open_folder"], on_click=_menu_open_folder),
        HeaderMenuItem(icon=Icons.HISTORY, label=txt["menu_show_history"], on_click=_menu_open_history),
        HeaderMenuItem(icon=Icons.MENU_BOOK_OUTLINED, label=txt["menu_how_to"], on_click=_menu_how_to),
    ]

    header_widget = header(
        theme,
        lang,
        icon=SECTION_ICON,
        title=txt["title"],
        subtitle=txt["subtitle"],
        on_help_click=_on_help,
        menu_items=menu_items,
    )
    layout.addWidget(header_widget)

    def _on_mode_change(index: int) -> None:
        new_mode = MODE_CHAT if index == 0 else MODE_FORM
        if new_mode == STATE.mode:
            return
        STATE.mode = new_mode
        _refresh()

    mode_bar = tab_bar(
        theme,
        tabs=_mode_tabs(lang),
        active_index=0 if STATE.mode == MODE_CHAT else 1,
        on_change=_on_mode_change,
    )
    layout.addWidget(mode_bar)

    if STATE.mode == MODE_FORM:
        def _on_stage_tab_change(index: int) -> None:
            if index == STATE.active_tab:
                return
            STATE.active_tab = index
            _refresh()

        stage_bar = tab_bar(
            theme,
            tabs=_stage_tabs(lang),
            active_index=STATE.active_tab,
            on_change=_on_stage_tab_change,
        )
        layout.addWidget(stage_bar)

    if STATE.mode == MODE_CHAT:
        body = build_chat_tab(
            theme, lang,
            on_request_rerender=_refresh,
            on_navigate_tab=_navigate_tab,
            on_switch_to_form=_refresh,
        )
    else:
        body = _build_form_tab_body(theme, lang)
    layout.addWidget(body, 1)

    return container
