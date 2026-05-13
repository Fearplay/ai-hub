"""AI Finance - center column orchestrator.

The view delegates each tab to its own ``tab_*.py`` module and keeps
itself thin: it owns the header (with the kebab menu + ``?`` button),
the section-wide tab bar, and the routing to the matching tab builder
based on ``STATE.active_tab``.

Per [ai-section.mdc](.cursor/rules/ai-section.mdc), the section is the
only place where AI-aware logic lives - we go through the shared
``ai_provider`` only via ``pipeline.py`` (kicked off from individual
tab builders). The Chat tab owns its own input bar, so the centre
column never renders a global chat composer here.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading

from PySide6.QtWidgets import QFrame, QMessageBox, QWidget

from src.components.header import HeaderMenuItem, header
from src.components.mock_panel import mock_card_grid_panel
from src.components.tab_bar import tab_bar
from src.qt.icons import Icons
from src.qt.runtime import dispatch as runtime_dispatch
from src.qt.runtime import get_main_window
from src.qt.widgets import vbox
from src.sections.ai_finance import pipeline
from src.sections.ai_finance.data import SECTION_ICON, tabs as tab_labels
from src.sections.ai_finance.how_to import open_finance_how_to
from src.sections.ai_finance.refs import REFS
from src.sections.ai_finance.state import (
    STATE,
    TAB_ANALYSIS,
    TAB_BUDGET,
    TAB_CALCULATORS,
    TAB_CHAT,
    TAB_INSURANCE,
    TAB_INVEST,
    TAB_TAXES,
    TAB_TEMPLATES,
)
from src.sections.ai_finance.strings import s
from src.sections.ai_finance.tab_analysis import build_analysis_tab
from src.sections.ai_finance.tab_budget import build_budget_tab
from src.sections.ai_finance.tab_calculators import build_calculators_tab
from src.sections.ai_finance.tab_chat import build_chat_tab
from src.sections.ai_finance.tab_insurance import build_insurance_tab
from src.sections.ai_finance.tab_invest import build_invest_tab
from src.sections.ai_finance.tab_taxes import build_taxes_tab
from src.services import logger as logger_service
from src.services import store
from src.theme import Theme


def _refresh() -> None:
    from src.app import request_section_refresh
    request_section_refresh()


def _open_in_explorer(path: str) -> None:
    if not path or not os.path.isdir(path):
        logger_service.log_event(
            "WARNING", "ai_finance.view", "open_in_explorer_no_path", path=str(path),
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
            "ai_finance.view", "open_in_explorer_failed", exc, path=path,
        )


def _show_message(message: str) -> None:
    if not message:
        return
    parent = get_main_window()
    try:
        QMessageBox.information(parent, "AI Finance", message)
    except Exception as exc:
        logger_service.log_exception(
            "ai_finance.view", "show_message_failed", exc,
        )


def _navigate_tab(index: int) -> None:
    if index == STATE.active_tab:
        return
    logger_service.log_event(
        "INFO", "ai_finance.view", "navigate_tab",
        prev_tab=STATE.active_tab,
        new_tab=index,
    )
    STATE.active_tab = index
    _refresh()


def _build_templates_panel(theme: Theme, lang: str) -> QWidget:
    """Static template grid - keeps the old four cards intact."""
    txt = s(lang)
    cards = [
        {
            "icon": Icons.PIE_CHART_OUTLINE,
            "title": txt["fin_tpl_budget_title"],
            "description": txt["fin_tpl_budget_desc"],
            "action_label": txt["fin_tpl_use"],
            "color": "#22C55E",
        },
        {
            "icon": Icons.SHOW_CHART,
            "title": txt["fin_tpl_invest_title"],
            "description": txt["fin_tpl_invest_desc"],
            "action_label": txt["fin_tpl_use"],
            "color": "#3B82F6",
        },
        {
            "icon": Icons.CREDIT_CARD,
            "title": txt["fin_tpl_debt_title"],
            "description": txt["fin_tpl_debt_desc"],
            "action_label": txt["fin_tpl_use"],
            "color": "#F59E0B",
        },
        {
            "icon": Icons.HEALTH_AND_SAFETY,
            "title": txt["fin_tpl_emergency_title"],
            "description": txt["fin_tpl_emergency_desc"],
            "action_label": txt["fin_tpl_use"],
            "color": "#EF4444",
        },
    ]
    return mock_card_grid_panel(
        theme,
        lang,
        icon=Icons.GRID_VIEW_OUTLINED,
        title=txt["fin_tpl_title"],
        description=txt["fin_tpl_desc"],
        cards=cards,
    )


def _build_tab_body(theme: Theme, lang: str) -> QWidget:
    tab = STATE.active_tab
    try:
        if tab == TAB_CHAT:
            return build_chat_tab(theme, lang, on_navigate=_navigate_tab)
        if tab == TAB_BUDGET:
            return build_budget_tab(theme, lang)
        if tab == TAB_INVEST:
            return build_invest_tab(theme, lang)
        if tab == TAB_ANALYSIS:
            return build_analysis_tab(theme, lang)
        if tab == TAB_TAXES:
            return build_taxes_tab(theme, lang)
        if tab == TAB_INSURANCE:
            return build_insurance_tab(theme, lang)
        if tab == TAB_CALCULATORS:
            return build_calculators_tab(theme, lang)
        if tab == TAB_TEMPLATES:
            return _build_templates_panel(theme, lang)
    except Exception as exc:
        logger_service.log_exception(
            "ai_finance.view", "build_tab_body_failed", exc, tab=tab,
        )
        raise
    return build_chat_tab(theme, lang, on_navigate=_navigate_tab)


def build_view(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    container = QFrame()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    def _on_help() -> None:
        open_finance_how_to(get_main_window(), theme, lang)

    def _menu_new_run() -> None:
        logger_service.log_event("INFO", "ai_finance.view", "menu_new_run")
        STATE.reset_all()
        STATE.active_tab = TAB_CHAT
        _refresh()

    def _menu_open_folder() -> None:
        try:
            store.ensure_dirs()
        except Exception as exc:
            logger_service.log_exception(
                "ai_finance.view", "menu_open_folder_ensure_dirs", exc,
            )
        outputs_root = str(store.runs_dir())
        if not os.path.isdir(outputs_root):
            _show_message(txt["menu_open_folder_no_run"])
            return
        _open_in_explorer(outputs_root)

    def _menu_save_full() -> None:
        if not STATE.has_any_analysis():
            _show_message(txt["menu_save_no_run"])
            return
        STATE.activity = "exporting"
        STATE.last_error = ""
        REFS.request_context_refresh()
        REFS.dispatch(_refresh)

        def _worker() -> None:
            try:
                result = pipeline.save_full_analysis(output_lang=lang)
            except Exception as exc:
                logger_service.log_exception(
                    "ai_finance.view", "menu_save_full_worker", exc,
                )
                result = None  # type: ignore[assignment]
            STATE.activity = "ready"
            REFS.request_context_refresh()
            if result is not None and result.ok:
                runtime_dispatch(
                    lambda: _show_message(txt["menu_save_done_template"].format(path=result.folder))
                )
            REFS.dispatch(_refresh)

        threading.Thread(target=_worker, daemon=True).start()

    def _menu_how_to() -> None:
        open_finance_how_to(get_main_window(), theme, lang)

    has_analyses = STATE.has_any_analysis()
    menu_items: list[HeaderMenuItem] = [
        HeaderMenuItem(
            icon=Icons.POST_ADD,
            label=txt["menu_new_run"],
            on_click=_menu_new_run,
        ),
        HeaderMenuItem(
            icon=Icons.SAVE_OUTLINED,
            label=txt["menu_save_full"],
            on_click=_menu_save_full,
            enabled=has_analyses,
        ),
        HeaderMenuItem(
            icon=Icons.FOLDER_OPEN,
            label=txt["menu_open_folder"],
            on_click=_menu_open_folder,
        ),
        HeaderMenuItem(
            icon=Icons.MENU_BOOK_OUTLINED,
            label=txt["menu_how_to"],
            on_click=_menu_how_to,
        ),
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

    def _on_tab_change(index: int) -> None:
        if index == STATE.active_tab:
            return
        logger_service.log_event(
            "INFO", "ai_finance.view", "tab_change",
            prev_tab=STATE.active_tab, new_tab=index,
        )
        STATE.active_tab = index
        try:
            _refresh()
        except Exception as exc:
            logger_service.log_exception(
                "ai_finance.view", "tab_change_failed", exc,
            )

    layout.addWidget(
        tab_bar(
            theme,
            tabs=tab_labels(lang),
            active_index=STATE.active_tab,
            on_change=_on_tab_change,
        )
    )

    layout.addWidget(_build_tab_body(theme, lang), 1)
    return container
