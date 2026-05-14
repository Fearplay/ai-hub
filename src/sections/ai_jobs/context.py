"""AI Jobs - right-hand context panel.

Three stacked cards:

1. **Activity + cost** - dot indicator (ready / searching / extracting
   / verifying / saving / error), session token+cost line, current
   provider/model.
2. **Quick actions** - jump to setup / results / history / open
   output folder / how-to.
3. **Last search** - tiny summary of the last completed search (query,
   location, count, dropped). Empty-state copy when no search has
   run yet.

The panel is rerendered on demand through
:func:`REFS.request_context_refresh`. Workers in
:mod:`src.sections.ai_jobs.pipeline` mutate STATE then trigger the
refresh - they never touch widgets directly.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QSizePolicy, QWidget

from src.components.context_panel import (
    context_panel_shell,
    quick_action_row,
)
from src.components.section_card import section_card
from src.qt.icons import Icons
from src.qt.widgets import (
    BodyLabel,
    ClickFrame,
    IconLabel,
    MutedLabel,
    SubtleLabel,
    TitleLabel,
    custom_label,
    hbox,
    vbox,
)
from src.services import logger as logger_service
from src.services import settings_store, store
from src.services.cost_tracker import COST
from src.sections.ai_jobs.refs import REFS
from src.sections.ai_jobs.state import (
    STATE,
    TAB_HISTORY,
    TAB_RESULTS,
    TAB_SETUP,
)
from src.sections.ai_jobs.strings import s
from src.theme import Theme


_ACTIVITY_KEYS = {
    "ready": "ctx_activity_ready",
    "searching": "ctx_activity_searching",
    "extracting": "ctx_activity_extracting",
    "verifying": "ctx_activity_verifying",
    "saving": "ctx_activity_saving",
    "error": "ctx_activity_error",
}


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception as exc:
        logger_service.log_exception(
            "ai_jobs.context", "request_full_refresh_import", exc,
        )
        return
    request_section_refresh()


def _open_in_explorer(path: str) -> None:
    if not path or not os.path.isdir(path):
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
            "ai_jobs.context", "open_in_explorer_failed", exc, path=path,
        )


def _activity_body(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    holder.setLayout(layout)

    activity_key = _ACTIVITY_KEYS.get(STATE.activity, "ctx_activity_ready")
    label = txt.get(activity_key) or txt["ctx_activity_ready"]
    color = (
        "#22C55E" if STATE.activity == "ready"
        else ("#EF4444" if STATE.activity == "error" else theme.primary)
    )

    row = QFrame()
    row.setStyleSheet("background: transparent;")
    rl = hbox(spacing=8, margins=(0, 0, 0, 0))
    rl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    row.setLayout(rl)
    dot = QFrame()
    dot.setFixedSize(10, 10)
    dot.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
    rl.addWidget(dot)
    rl.addWidget(BodyLabel(label, theme=theme, size=13, weight=QFont.Weight.DemiBold), 1)
    layout.addWidget(row)

    if STATE.last_error and STATE.activity == "error":
        layout.addWidget(custom_label(STATE.last_error, color="#EF4444", size=11))

    provider = settings_store.get_provider()
    model_label = settings_store.get_model()
    layout.addWidget(BodyLabel(
        txt["ctx_cost_calls_template"].format(calls=COST.calls, tokens=COST.tokens_total),
        theme=theme, size=12,
    ))
    layout.addWidget(SubtleLabel(
        txt["ctx_cost_session_template"].format(cost=COST.cost_usd),
        theme=theme, size=11,
    ))
    layout.addWidget(SubtleLabel(
        txt["ctx_provider_template"].format(provider=provider.title(), model=model_label),
        theme=theme, size=11, italic=True,
    ))
    return holder


def _quick_actions_body(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    holder.setLayout(layout)

    actions: list[tuple[str, str, callable]] = [
        (Icons.MANAGE_SEARCH, txt["ctx_qa_new_search"], _action_new_search),
        (Icons.AUTO_AWESOME, txt["ctx_qa_open_results"], _action_open_results),
        (Icons.HISTORY, txt["ctx_qa_show_history"], _action_open_history),
        (Icons.FOLDER_OPEN, txt["ctx_qa_open_folder"], _action_open_folder),
        (Icons.MENU_BOOK_OUTLINED, txt["ctx_qa_open_how_to"], _action_open_how_to),
    ]

    for icon, label, handler in actions:
        row = quick_action_row(theme, icon, label)
        if isinstance(row, ClickFrame):
            row.clicked.connect(handler)
        layout.addWidget(row)
    return holder


def _last_run_body(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    holder.setLayout(layout)

    if not (STATE.last_query or STATE.results):
        layout.addWidget(SubtleLabel(txt["ctx_last_run_empty"], theme=theme, size=11, italic=True))
        return holder

    if STATE.last_query:
        layout.addWidget(BodyLabel(
            txt["results_query_template"].format(query=STATE.last_query),
            theme=theme, size=12,
        ))
    if STATE.last_location_label:
        layout.addWidget(SubtleLabel(
            txt["results_location_template"].format(location=STATE.last_location_label),
            theme=theme, size=11,
        ))
    layout.addWidget(SubtleLabel(
        txt["history_count_template"].format(count=len(STATE.results)),
        theme=theme, size=11,
    ))
    if STATE.last_dropped:
        layout.addWidget(SubtleLabel(
            txt["results_dropped_note_template"].format(count=STATE.last_dropped),
            theme=theme, size=11, italic=True,
        ))
    return holder


def _action_new_search() -> None:
    STATE.reset_results()
    STATE.active_tab = TAB_SETUP
    REFS.dispatch(_request_full_refresh)


def _action_open_results() -> None:
    STATE.active_tab = TAB_RESULTS
    REFS.dispatch(_request_full_refresh)


def _action_open_history() -> None:
    STATE.active_tab = TAB_HISTORY
    REFS.dispatch(_request_full_refresh)


def _action_open_folder() -> None:
    target = STATE.last_run_folder
    if not target or not os.path.isdir(target):
        try:
            store.ensure_dirs()
            target = str(store.runs_dir())
        except Exception as exc:
            logger_service.log_exception(
                "ai_jobs.context", "open_folder_ensure_dirs", exc,
            )
            return
    _open_in_explorer(target)


def _action_open_how_to() -> None:
    # Avoid an extra import-cycle by lazy-loading the dialog opener.
    from src.qt.runtime import get_main_window
    from src.sections.ai_jobs.how_to import open_jobs_how_to
    from src.theme import get_theme

    parent = get_main_window()
    if parent is None:
        return
    theme = get_theme(getattr(parent, "theme_mode", "dark"))
    lang = getattr(parent, "lang", "en")
    open_jobs_how_to(parent, theme, lang)


def build_context(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    panel_holder = QFrame()
    panel_holder.setStyleSheet("background: transparent;")
    panel_layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    panel_holder.setLayout(panel_layout)

    def _clear() -> None:
        while panel_layout.count():
            item = panel_layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _render() -> None:
        _clear()
        cards: list[QWidget] = [
            section_card(
                theme,
                icon=Icons.INSIGHTS_OUTLINED,
                title=txt["ctx_activity_title"],
                body=_activity_body(theme, lang),
            ),
            section_card(
                theme,
                icon=Icons.BOLT_OUTLINED,
                title=txt["ctx_quick_actions_title"],
                body=_quick_actions_body(theme, lang),
            ),
            section_card(
                theme,
                icon=Icons.HISTORY,
                title=txt["ctx_last_run_title"],
                body=_last_run_body(theme, lang),
            ),
        ]
        shell = context_panel_shell(theme, *cards)
        panel_layout.addWidget(shell)

    REFS.rerender_context = _render
    _render()
    return panel_holder
