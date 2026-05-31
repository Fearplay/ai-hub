"""AI LinkedIn - main center view (Chat + Builder modes) - PySide6 port.

Mirrors the Career section's layout pattern:

* Top header with the section icon, title, subtitle, ``?`` how-to and an
  overflow menu.
* Mode tab bar (Chat vs. Builder).
* In Chat mode the body is the LinkedIn voice chat.
* In Builder mode a four-tab bar (Setup / Sections / Output / History)
  drives the structured profile pipeline.
"""

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
from src.qt.widgets import Pill, vbox
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
from src.services import handoff
from src.services import logger as logger_service
from src.services import store
from src.theme import Theme


def _refresh() -> None:
    from src.app import request_section_refresh
    request_section_refresh()


def _consume_handoff() -> None:
    """Pull a Job Search -> LinkedIn handoff (if any) into STATE.

    Job Search's "Tune LinkedIn" action stashes the picked role; we add
    it to the target-roles list and jump to the Builder/Setup flow.
    """
    payload = handoff.take("ai_linkedin")
    if not payload:
        return
    try:
        role = str(payload.get("target_role") or "").strip()
        if role:
            roles = [r for r in (STATE.target_roles or []) if r.strip()]
            if role not in roles:
                roles.insert(0, role)
            STATE.target_roles = roles
            STATE.mode = MODE_BUILDER
            STATE.active_tab = TAB_SETUP
        logger_service.log_event(
            "INFO", "ai_linkedin.view", "handoff_consumed", has_role=bool(role),
        )
    except Exception as exc:
        logger_service.log_exception("ai_linkedin.view", "handoff_consume_failed", exc)


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


def _show_message(message: str) -> None:
    if not message:
        return
    parent = get_main_window()
    try:
        QMessageBox.information(parent, "AI LinkedIn", message)
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.view", "show_message_failed", exc,
        )


def _navigate_tab(index: int) -> None:
    logger_service.log_event(
        "INFO", "ai_linkedin.view", "navigate_tab",
        prev_mode=STATE.mode,
        prev_tab=STATE.active_tab,
        new_tab=index,
    )
    STATE.mode = MODE_BUILDER
    STATE.active_tab = index
    _refresh()


def _build_builder_body(theme: Theme, lang: str) -> QWidget:
    if STATE.active_tab == TAB_SECTIONS:
        return build_sections_tab(theme, lang, on_request_rerender=_refresh, on_navigate_tab=_navigate_tab)
    if STATE.active_tab == TAB_OUTPUT:
        return build_output_tab(theme, lang, on_request_rerender=_refresh, on_navigate_tab=_navigate_tab)
    if STATE.active_tab == TAB_HISTORY:
        return build_history_tab(theme, lang, on_request_rerender=_refresh, on_navigate_tab=_navigate_tab)
    return build_setup_tab(theme, lang, on_request_rerender=_refresh, on_navigate_tab=_navigate_tab)


def _builder_tab_enabled(index: int) -> bool:
    if index in {TAB_SECTIONS, TAB_OUTPUT}:
        return STATE.has_results()
    if index == TAB_HISTORY:
        return bool(STATE.runs_history)
    return True


def build_view(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    # Keep the current language on REFS so background workers can resolve
    # the localized sidebar Activity label (see ``LinkedInRefs``).
    REFS.lang = lang
    _consume_handoff()
    try:
        STATE.runs_history = [
            run for run in store.list_runs()
            if (getattr(run, "note", "") or "") == "ai_linkedin"
        ]
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.view", "warm_history_failed", exc,
        )

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    def _on_stage_tab_change(index: int) -> None:
        logger_service.log_event(
            "INFO", "ai_linkedin.view", "stage_tab_change",
            index=index, prev_tab=STATE.active_tab, mode=STATE.mode,
        )
        if STATE.mode != MODE_BUILDER:
            return
        if index == STATE.active_tab:
            return
        if not _builder_tab_enabled(index):
            logger_service.log_event(
                "INFO", "ai_linkedin.view", "tab_blocked",
                requested_tab=index,
                has_results=STATE.has_results(),
                history_count=len(STATE.runs_history or []),
            )
            return
        STATE.active_tab = index
        _refresh()

    def _on_mode_change(index: int) -> None:
        new_mode = MODE_CHAT if index == 0 else MODE_BUILDER
        logger_service.log_event(
            "INFO", "ai_linkedin.view", "mode_change",
            index=index, prev_mode=STATE.mode, new_mode=new_mode,
        )
        if new_mode == STATE.mode:
            return
        STATE.mode = new_mode
        _refresh()

    def _on_help() -> None:
        open_linkedin_how_to(get_main_window(), theme, lang)

    def _menu_new_build() -> None:
        logger_service.log_event("INFO", "ai_linkedin.view", "menu_new_build")
        STATE.reset_all()
        STATE.mode = MODE_BUILDER
        STATE.active_tab = TAB_SETUP
        _refresh()

    def _menu_open_history() -> None:
        logger_service.log_event("INFO", "ai_linkedin.view", "menu_open_history")
        STATE.mode = MODE_BUILDER
        STATE.active_tab = TAB_HISTORY
        _refresh()

    def _menu_open_folder() -> None:
        try:
            store.ensure_dirs()
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.view", "menu_open_folder_ensure_dirs", exc,
            )
        section_root = str(store.section_runs_dir("ai_linkedin"))
        outputs_root = section_root if os.path.isdir(section_root) else str(store.runs_dir())
        logger_service.log_event(
            "INFO", "ai_linkedin.view", "menu_open_folder", path=outputs_root,
        )
        if not os.path.isdir(outputs_root):
            _show_message(txt["history_empty_desc"])
            return
        _open_in_explorer(outputs_root)

    def _menu_save_full() -> None:
        if not STATE.has_results():
            logger_service.log_event(
                "WARNING", "ai_linkedin.view", "menu_save_full_empty",
            )
            _show_message(txt["error_no_inputs"])
            return
        logger_service.log_event(
            "INFO", "ai_linkedin.view", "menu_save_full_start",
            has_about=bool(STATE.about_variants),
            has_headlines=bool(STATE.headlines),
        )
        STATE.activity = "saving"
        STATE.last_error = ""
        REFS.request_context_refresh()
        runtime_dispatch(_refresh)

        def _worker() -> None:
            try:
                # refresh_ui=False: we rebuild once below; let the pipeline
                # leave Activity on the persistent "Profil uložen" state.
                result = pipeline.save_full_profile(refresh_ui=False)
            except Exception as exc:
                logger_service.log_exception(
                    "ai_linkedin.view", "menu_save_full_worker", exc,
                )
                result = None
            if result is not None:
                logger_service.log_event(
                    "INFO" if result.ok else "ERROR",
                    "ai_linkedin.view", "menu_save_full_done",
                    ok=result.ok, folder=result.folder, error=result.error,
                )
            if result is not None and result.ok:
                runtime_dispatch(lambda: _show_message(f"{txt['menu_save_full']}: {result.folder}"))
            runtime_dispatch(_refresh)

        threading.Thread(target=_worker, daemon=True).start()

    def _menu_how_to() -> None:
        open_linkedin_how_to(get_main_window(), theme, lang)

    def _menu_load_demo() -> None:
        logger_service.log_event("INFO", "ai_linkedin.view", "menu_load_demo")
        try:
            pipeline.load_demo()
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.view", "menu_load_demo_failed", exc,
            )
            return
        STATE.mode = MODE_BUILDER
        STATE.active_tab = TAB_OUTPUT
        _refresh()

    def _menu_clear_demo() -> None:
        logger_service.log_event("INFO", "ai_linkedin.view", "menu_clear_demo")
        try:
            pipeline.clear_demo()
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.view", "menu_clear_demo_failed", exc,
            )
            return
        STATE.active_tab = TAB_SETUP
        _refresh()

    has_results = STATE.has_results()
    demo_menu_label = (
        txt["menu_demo_clear"] if STATE.demo_mode else txt["menu_demo_load"]
    )
    demo_menu_handler = _menu_clear_demo if STATE.demo_mode else _menu_load_demo

    menu_items: list[HeaderMenuItem] = [
        HeaderMenuItem(icon=Icons.RESTART_ALT, label=txt["menu_new_build"], on_click=_menu_new_build),
        HeaderMenuItem(icon=Icons.SAVE_OUTLINED, label=txt["menu_save_full"], on_click=_menu_save_full, enabled=has_results),
        HeaderMenuItem(icon=Icons.FOLDER_OPEN, label=txt["menu_open_folder"], on_click=_menu_open_folder),
        HeaderMenuItem(icon=Icons.HISTORY, label=txt["menu_show_history"], on_click=_menu_open_history),
        HeaderMenuItem(icon=Icons.AUTO_AWESOME, label=demo_menu_label, on_click=demo_menu_handler),
        HeaderMenuItem(icon=Icons.MENU_BOOK_OUTLINED, label=txt["menu_how_to"], on_click=_menu_how_to),
    ]

    demo_pill = (
        Pill(text=txt["demo_pill"], bg="#F59E0B", fg="#FFFFFF")
        if STATE.demo_mode
        else None
    )

    layout.addWidget(header(
        theme, lang,
        icon=SECTION_ICON,
        title=txt["title"],
        subtitle=txt["subtitle"],
        on_help_click=_on_help,
        trailing=demo_pill,
        menu_items=menu_items,
    ))

    layout.addWidget(tab_bar(
        theme,
        tabs=mode_tabs(lang),
        active_index=0 if STATE.mode == MODE_CHAT else 1,
        on_change=_on_mode_change,
    ))

    if STATE.mode == MODE_BUILDER:
        layout.addWidget(tab_bar(
            theme,
            tabs=builder_tabs(lang),
            active_index=STATE.active_tab,
            on_change=_on_stage_tab_change,
            enabled=[
                _builder_tab_enabled(TAB_SETUP),
                _builder_tab_enabled(TAB_SECTIONS),
                _builder_tab_enabled(TAB_OUTPUT),
                _builder_tab_enabled(TAB_HISTORY),
            ],
        ))

    if STATE.mode == MODE_CHAT:
        body = build_chat_tab(
            theme, lang,
            on_request_rerender=_refresh,
            on_navigate_tab=_navigate_tab,
            on_switch_to_builder=_refresh,
        )
    else:
        body = _build_builder_body(theme, lang)

    layout.addWidget(body, 1)

    return container
