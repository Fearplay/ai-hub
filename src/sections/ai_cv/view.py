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
from src.qt.widgets import Pill, vbox
from src.sections.ai_cv import pipeline
from src.sections.ai_cv.data import SECTION_ICON
from src.sections.ai_cv.how_to import open_career_how_to
from src.sections.ai_cv.refs import REFS
from src.sections.ai_cv.state import (
    MODE_CHAT,
    MODE_FORM,
    STATE,
    TAB_DOCUMENTS,
    TAB_HISTORY,
    TAB_INTERVIEW,
    TAB_MATCH,
    TAB_SETUP,
)
from src.sections.ai_cv.strings import s
from src.sections.ai_cv.tab_chat import build_chat_tab
from src.sections.ai_cv.tab_documents import build_documents_tab
from src.sections.ai_cv.tab_history import build_history_tab
from src.sections.ai_cv.tab_match import build_match_tab
from src.sections.ai_cv.tab_mock_interview import build_mock_interview_tab
from src.sections.ai_cv.tab_setup import build_setup_tab
from src.services import handoff
from src.services import logger as logger_service
from src.services import store
from src.theme import Theme


def _refresh() -> None:
    from src.app import request_section_refresh
    request_section_refresh()


def _consume_handoff() -> None:
    """Pull a Job Search -> Career handoff (if any) into STATE.

    Job Search's "Tailor CV" action stashes the picked posting; we
    pre-fill the position fields and jump to the Form/Setup flow so the
    user lands ready to run.
    """
    payload = handoff.take("ai_cv")
    if not payload:
        return
    try:
        job_url = str(payload.get("job_url") or "").strip()
        job_text = str(payload.get("job_text") or "").strip()
        target_role = str(payload.get("job_title") or "").strip()
        if job_url:
            STATE.job_url = job_url
        if job_text:
            STATE.job_text = job_text
            STATE.job_text_source = "paste"
        if target_role:
            STATE.target_role = target_role
        STATE.mode = MODE_FORM
        STATE.active_tab = TAB_SETUP
        logger_service.log_event(
            "INFO", "ai_cv.view", "handoff_consumed",
            has_url=bool(job_url), has_text=bool(job_text), has_role=bool(target_role),
        )
    except Exception as exc:
        logger_service.log_exception("ai_cv.view", "handoff_consume_failed", exc)


def _open_in_explorer(path: str) -> None:
    if not path or not os.path.isdir(path):
        logger_service.log_event(
            "WARNING", "ai_cv.view", "open_in_explorer_no_path", path=str(path),
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
            "ai_cv.view", "open_in_explorer_failed", exc, path=path,
        )


def _show_message(message: str) -> None:
    if not message:
        return
    parent = get_main_window()
    try:
        QMessageBox.information(parent, "AI CV", message)
    except Exception as exc:
        logger_service.log_exception(
            "ai_cv.view", "show_message_failed", exc,
        )


def _navigate_tab(index: int) -> None:
    logger_service.log_event(
        "INFO", "ai_cv.view", "navigate_tab",
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
    if STATE.active_tab == TAB_INTERVIEW:
        return build_mock_interview_tab(theme, lang, on_request_rerender=_refresh)
    if STATE.active_tab == TAB_HISTORY:
        return build_history_tab(theme, lang, on_request_rerender=_refresh, on_navigate_tab=_navigate_tab)
    return build_setup_tab(theme, lang, on_request_rerender=_refresh)


def _mode_tabs(lang: str) -> list[str]:
    txt = s(lang)
    return [txt["mode_chat"], txt["mode_form"]]


def _stage_tabs(lang: str) -> list[str]:
    txt = s(lang)
    return [
        txt["tab_setup"],
        txt["tab_match"],
        txt["tab_documents"],
        txt["tab_interview"],
        txt["tab_history"],
    ]


def _stage_tab_enabled(index: int) -> bool:
    if index == TAB_MATCH:
        return STATE.has_results()
    if index == TAB_DOCUMENTS:
        return bool(STATE.documents or STATE.modern_cv_data)
    if index == TAB_INTERVIEW:
        # Available whenever the user has any profile material to ground
        # questions on (resume / LinkedIn / extracted candidate), or a
        # match result. Demo mode also opens it for showcasing.
        return bool(
            STATE.demo_mode
            or STATE.has_results()
            or STATE.candidate
            or (STATE.resume and STATE.resume.text)
            or (STATE.linkedin and STATE.linkedin.text)
        )
    if index == TAB_HISTORY:
        return bool(STATE.runs_history)
    return True


def build_view(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    # Keep the current language on REFS so background workers can resolve
    # the localized Activity-panel label (see ``CareerRefs._activity_label``).
    REFS.lang = lang
    _consume_handoff()
    try:
        STATE.runs_history = [
            run for run in store.list_runs()
            if (
                # New "ai_cv" runs plus legacy "ai_career" runs saved
                # before the section was renamed (no data is relocated).
                (getattr(run, "note", "") or "").strip().lower() in ("ai_cv", "ai_career")
                or "/outputs/ai_cv/" in (getattr(run, "folder", "") or "").replace("\\", "/").lower()
                or "/outputs/ai_career/" in (getattr(run, "folder", "") or "").replace("\\", "/").lower()
            )
        ]
    except Exception as exc:
        logger_service.log_exception(
            "ai_cv.view", "warm_history_failed", exc,
        )

    container = QFrame()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    def _on_help() -> None:
        open_career_how_to(get_main_window(), theme, lang)

    def _menu_new_run() -> None:
        logger_service.log_event("INFO", "ai_cv.view", "menu_new_run")
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
                "ai_cv.view", "menu_open_folder_ensure_dirs", exc,
            )
        section_root = str(store.section_runs_dir("ai_cv"))
        if os.path.isdir(section_root):
            _open_in_explorer(section_root)
            return
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
                    "ai_cv.view", "menu_save_full_worker", exc,
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

    def _menu_load_demo() -> None:
        logger_service.log_event("INFO", "ai_cv.view", "menu_load_demo")
        try:
            pipeline.load_demo()
        except Exception as exc:
            logger_service.log_exception(
                "ai_cv.view", "menu_load_demo_failed", exc,
            )
            return
        STATE.mode = MODE_FORM
        STATE.active_tab = TAB_MATCH
        _refresh()

    def _menu_clear_demo() -> None:
        logger_service.log_event("INFO", "ai_cv.view", "menu_clear_demo")
        try:
            pipeline.clear_demo()
        except Exception as exc:
            logger_service.log_exception(
                "ai_cv.view", "menu_clear_demo_failed", exc,
            )
            return
        STATE.active_tab = TAB_SETUP
        _refresh()

    has_docs = bool(STATE.documents or STATE.modern_cv_data)
    demo_menu_label = (
        txt["menu_demo_clear"] if STATE.demo_mode else txt["menu_demo_load"]
    )
    demo_menu_handler = _menu_clear_demo if STATE.demo_mode else _menu_load_demo

    menu_items: list[HeaderMenuItem] = [
        HeaderMenuItem(icon=Icons.POST_ADD, label=txt["menu_new_run"], on_click=_menu_new_run),
        HeaderMenuItem(icon=Icons.SAVE_OUTLINED, label=txt["menu_save_full"], on_click=_menu_save_full, enabled=has_docs),
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

    header_widget = header(
        theme,
        lang,
        icon=SECTION_ICON,
        title=txt["title"],
        subtitle=txt["subtitle"],
        on_help_click=_on_help,
        trailing=demo_pill,
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
            if not _stage_tab_enabled(index):
                logger_service.log_event(
                    "INFO", "ai_cv.view", "tab_blocked",
                    requested_tab=index,
                    has_match=STATE.has_results(),
                    has_documents=bool(STATE.documents or STATE.modern_cv_data),
                    history_count=len(STATE.runs_history or []),
                )
                return
            STATE.active_tab = index
            _refresh()

        stage_bar = tab_bar(
            theme,
            tabs=_stage_tabs(lang),
            active_index=STATE.active_tab,
            on_change=_on_stage_tab_change,
            enabled=[
                _stage_tab_enabled(TAB_SETUP),
                _stage_tab_enabled(TAB_MATCH),
                _stage_tab_enabled(TAB_DOCUMENTS),
                _stage_tab_enabled(TAB_INTERVIEW),
                _stage_tab_enabled(TAB_HISTORY),
            ],
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
