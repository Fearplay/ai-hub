"""AI Jobs - centre column orchestrator.

Same shape as :mod:`src.sections.ai_finance.view`: a thin
``build_view`` that owns the section header (with the ``?`` button
and the kebab menu) plus the tab bar, and delegates each tab's body
to a dedicated ``tab_*.py`` module.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from typing import Optional

from PySide6.QtWidgets import QFrame, QMessageBox, QWidget

from src.components.header import HeaderMenuItem, header
from src.components.tab_bar import tab_bar
from src.qt.icons import Icons
from src.qt.runtime import dispatch as runtime_dispatch
from src.qt.runtime import get_main_window
from src.qt.widgets import Pill, vbox
from src.sections.ai_jobs import pipeline
from src.sections.ai_jobs.data import SECTION_ICON, tabs as tab_labels
from src.sections.ai_jobs.how_to import open_jobs_how_to
from src.sections.ai_jobs.refs import REFS
from src.sections.ai_jobs.state import (
    STATE,
    TAB_APPLICATIONS,
    TAB_HISTORY,
    TAB_RESULTS,
    TAB_SETUP,
    TAB_SKILL_GAP,
)
from src.sections.ai_jobs.strings import s
from src.sections.ai_jobs.tab_applications import build_applications_tab
from src.sections.ai_jobs.tab_history import build_history_tab
from src.sections.ai_jobs.tab_results import build_results_tab
from src.sections.ai_jobs.tab_setup import build_setup_tab
from src.sections.ai_jobs.tab_skill_gap import build_skill_gap_tab
from src.services import applications_store
from src.services import logger as logger_service
from src.services import store
from src.theme import Theme


def _refresh() -> None:
    from src.app import request_section_refresh

    request_section_refresh()


def _open_in_explorer(path: str) -> None:
    if not path or not os.path.isdir(path):
        logger_service.log_event(
            "WARNING", "ai_jobs.view", "open_in_explorer_no_path", path=str(path),
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
            "ai_jobs.view", "open_in_explorer_failed", exc, path=path,
        )


def _show_message(message: str) -> None:
    if not message:
        return
    parent = get_main_window()
    try:
        QMessageBox.information(parent, "AI Job Search", message)
    except Exception as exc:
        logger_service.log_exception(
            "ai_jobs.view", "show_message_failed", exc,
        )


def _navigate_tab(index: int) -> None:
    if index == STATE.active_tab:
        return
    logger_service.log_event(
        "INFO", "ai_jobs.view", "navigate_tab",
        prev_tab=STATE.active_tab, new_tab=index,
    )
    STATE.active_tab = index
    _refresh()


def _build_tab_body(theme: Theme, lang: str) -> QWidget:
    tab = STATE.active_tab
    try:
        if tab == TAB_RESULTS:
            return build_results_tab(theme, lang)
        if tab == TAB_APPLICATIONS:
            return build_applications_tab(theme, lang)
        if tab == TAB_SKILL_GAP:
            return build_skill_gap_tab(theme, lang)
        if tab == TAB_HISTORY:
            return build_history_tab(theme, lang)
        return build_setup_tab(
            theme,
            lang,
            on_request_rerender=_refresh,
        )
    except Exception as exc:
        logger_service.log_exception(
            "ai_jobs.view", "build_tab_body_failed", exc, tab=tab,
        )
        raise


def _has_applications() -> bool:
    """Whether the tracker has at least one saved application.

    Drives the enabled state of the Applications tab - an empty tracker
    means there is nothing to show, so the tab stays disabled until the
    user saves a posting from the Results tab.
    """
    try:
        return applications_store.count() > 0
    except Exception as exc:
        logger_service.log_exception(
            "ai_jobs.view", "applications_count_failed", exc,
        )
        return False


def _tab_enabled(index: int) -> bool:
    if index == TAB_RESULTS:
        return STATE.has_results()
    if index == TAB_APPLICATIONS:
        return _has_applications()
    if index == TAB_SKILL_GAP:
        return STATE.has_skill_gap()
    if index == TAB_HISTORY:
        return bool(STATE.runs_history)
    return True


def build_view(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    pipeline.warm_runs_history_once()

    container = QFrame()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    def _on_help() -> None:
        open_jobs_how_to(get_main_window(), theme, lang)

    def _menu_new_search() -> None:
        logger_service.log_event("INFO", "ai_jobs.view", "menu_new_search")
        STATE.reset_results()
        STATE.active_tab = TAB_SETUP
        _refresh()

    def _menu_open_folder() -> None:
        try:
            store.ensure_dirs()
        except Exception as exc:
            logger_service.log_exception(
                "ai_jobs.view", "menu_open_folder_ensure_dirs", exc,
            )
        section_root = str(store.section_runs_dir("ai_jobs"))
        target = STATE.last_run_folder or (
            section_root if os.path.isdir(section_root) else str(store.runs_dir())
        )
        if not target or not os.path.isdir(target):
            _show_message(txt["menu_open_folder_no_run"])
            return
        _open_in_explorer(target)

    def _menu_save_html() -> None:
        if not STATE.has_results():
            _show_message(txt["menu_save_no_run"])
            return
        STATE.activity = "saving"
        STATE.last_error = ""
        REFS.request_context_refresh()

        def _worker() -> None:
            try:
                result = pipeline.save_html(output_lang=lang)
            except Exception as exc:
                logger_service.log_exception(
                    "ai_jobs.view", "menu_save_html_worker", exc,
                )
                runtime_dispatch(lambda: _show_message(
                    txt["results_save_failed_template"].format(error=exc)
                ))
                return
            if result.ok:
                runtime_dispatch(lambda: _show_message(
                    txt["results_save_done_template"].format(path=result.folder)
                ))
                runtime_dispatch(lambda: _open_in_explorer(result.folder))
            else:
                runtime_dispatch(lambda: _show_message(
                    txt["results_save_failed_template"].format(error=result.error)
                ))
            REFS.dispatch(_refresh)

        threading.Thread(target=_worker, daemon=True).start()

    def _menu_show_history() -> None:
        STATE.active_tab = TAB_HISTORY
        _refresh()

    def _menu_show_skill_gap() -> None:
        if not _tab_enabled(TAB_SKILL_GAP):
            return
        STATE.active_tab = TAB_SKILL_GAP
        _refresh()

    def _menu_load_demo() -> None:
        logger_service.log_event("INFO", "ai_jobs.view", "menu_load_demo")
        STATE.demo_mode = True
        if not STATE.can_run():
            STATE.keywords = "QA software engineer"
            STATE.tech_skills = "Python, API testing, Playwright, SQL"
            STATE.location_preset = "prague"
            STATE.output_language = "cs" if lang == "cs" else "en"
        result = pipeline.run_search(output_lang=lang)
        if not result.ok:
            _show_message(result.error)
            return
        STATE.active_tab = TAB_RESULTS
        _refresh()

    def _menu_clear_demo() -> None:
        logger_service.log_event("INFO", "ai_jobs.view", "menu_clear_demo")
        STATE.demo_mode = False
        STATE.reset_all()
        _refresh()

    def _menu_how_to() -> None:
        open_jobs_how_to(get_main_window(), theme, lang)

    has_results = STATE.has_results()
    menu_items: list[HeaderMenuItem] = [
        HeaderMenuItem(
            icon=Icons.MANAGE_SEARCH,
            label=txt["menu_new_search"],
            on_click=_menu_new_search,
        ),
        HeaderMenuItem(
            icon=Icons.SAVE_OUTLINED,
            label=txt["menu_save_html"],
            on_click=_menu_save_html,
            enabled=has_results,
        ),
        HeaderMenuItem(
            icon=Icons.INSIGHTS_OUTLINED,
            label=txt["menu_show_skill_gap"],
            on_click=_menu_show_skill_gap,
            enabled=STATE.has_skill_gap(),
        ),
        HeaderMenuItem(
            icon=Icons.AUTO_AWESOME,
            label=txt["menu_demo_clear"] if STATE.demo_mode else txt["menu_demo_load"],
            on_click=_menu_clear_demo if STATE.demo_mode else _menu_load_demo,
        ),
        HeaderMenuItem(
            icon=Icons.FOLDER_OPEN,
            label=txt["menu_open_folder"],
            on_click=_menu_open_folder,
        ),
        HeaderMenuItem(
            icon=Icons.HISTORY,
            label=txt["menu_show_history"],
            on_click=_menu_show_history,
        ),
        HeaderMenuItem(
            icon=Icons.MENU_BOOK_OUTLINED,
            label=txt["menu_how_to"],
            on_click=_menu_how_to,
        ),
    ]

    # Orange ``DEMO`` pill in the header trailing slot signals that
    # the current view is showing curated offline data, not a real
    # search. Matches the AI Bug Report / AI Doc Assistant pattern -
    # see ``.cursor/rules/ai-section.mdc`` for the shared demo affordance.
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

    def _on_tab_change(index: int) -> None:
        if index == STATE.active_tab:
            return
        if not _tab_enabled(index):
            logger_service.log_event(
                "INFO", "ai_jobs.view", "tab_blocked",
                requested_tab=index,
                has_results=STATE.has_results(),
                has_skill_gap=STATE.has_skill_gap(),
                history_count=len(STATE.runs_history or []),
            )
            return
        logger_service.log_event(
            "INFO", "ai_jobs.view", "tab_change",
            prev_tab=STATE.active_tab, new_tab=index,
        )
        STATE.active_tab = index
        try:
            _refresh()
        except Exception as exc:
            logger_service.log_exception(
                "ai_jobs.view", "tab_change_failed", exc,
            )

    layout.addWidget(
        tab_bar(
            theme,
            tabs=tab_labels(lang),
            active_index=STATE.active_tab,
            on_change=_on_tab_change,
            enabled=[
                _tab_enabled(TAB_SETUP),
                _tab_enabled(TAB_RESULTS),
                _tab_enabled(TAB_APPLICATIONS),
                _tab_enabled(TAB_SKILL_GAP),
                _tab_enabled(TAB_HISTORY),
            ],
        )
    )

    layout.addWidget(_build_tab_body(theme, lang), 1)
    return container
