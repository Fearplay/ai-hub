"""Right-hand context panel for AI Career (PySide6 port)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QSizePolicy,
    QWidget,
)

from src.components.context_panel import context_panel_shell
from src.components.section_card import section_card
from src.qt.icons import Icons
from src.qt.runtime import dispatch as runtime_dispatch
from src.qt.runtime import get_main_window
from src.qt.widgets import (
    BodyLabel,
    ClickFrame,
    IconLabel,
    IconOnlyButton,
    MutedLabel,
    SubtleLabel,
    custom_label,
    hbox,
    vbox,
)
from src.services import logger as logger_service
from src.services import settings_store
from src.services.cost_tracker import COST
from src.sections.ai_career.refs import REFS
from src.sections.ai_career.state import (
    MODE_CHAT,
    MODE_FORM,
    STATE,
    TAB_HISTORY,
    TAB_SETUP,
)
from src.sections.ai_career.strings import s
from src.theme import Theme


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception:
        return
    request_section_refresh()


_ACTIVITY_KEYS = {
    "ready": "ctx_activity_ready",
    "scraping": "ctx_activity_scraping",
    "parsing": "ctx_activity_parsing",
    "analyzing": "ctx_activity_analyzing",
    "followups": "ctx_activity_followups",
    "waiting_user": "ctx_activity_waiting_user",
    "generating": "ctx_activity_generating",
    "exporting": "ctx_activity_exporting",
    "error": "ctx_activity_error",
}


def _cost_body(theme: Theme, txt: dict) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    holder.setLayout(layout)

    provider_label = (
        settings_store.PROVIDER_OPENAI
        if settings_store.get_provider() == settings_store.PROVIDER_OPENAI
        else settings_store.PROVIDER_ANTHROPIC
    )
    model_label = settings_store.get_model()
    layout.addWidget(BodyLabel(
        txt["ctx_cost_calls_template"].format(calls=COST.calls, tokens=COST.tokens_total),
        theme=theme, size=13,
    ))
    layout.addWidget(BodyLabel(
        txt["ctx_cost_session_template"].format(cost=COST.cost_usd),
        theme=theme, size=13, weight=QFont.Weight.Bold,
    ))
    layout.addWidget(SubtleLabel(
        txt["ctx_provider_template"].format(provider=provider_label.title(), model=model_label),
        theme=theme, size=11, italic=True,
    ))
    return holder


def _activity_body(theme: Theme, txt: dict) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    holder.setLayout(layout)

    key = _ACTIVITY_KEYS.get(STATE.activity, "ctx_activity_ready")
    label = txt.get(key) or txt["ctx_activity_ready"]
    color = "#22C55E" if STATE.activity == "ready" else (
        "#EF4444" if STATE.activity == "error" else
        "#F59E0B" if STATE.activity == "waiting_user" else
        theme.primary
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
    return holder


def _attachments_body(theme: Theme, txt: dict) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=6, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    if not STATE.chat_attachments:
        layout.addWidget(MutedLabel(txt["chat_mode_no_attachments"], theme=theme, size=12))
        return holder
    for name in list(STATE.chat_attachments.keys()):
        row = QFrame()
        row.setStyleSheet(f"background-color: {theme.surface_2}; border-radius: 8px;")
        rl = hbox(spacing=8, margins=(8, 4, 4, 4))
        rl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        row.setLayout(rl)
        rl.addWidget(IconLabel(Icons.DESCRIPTION_OUTLINED, color=theme.primary, size=16))
        rl.addWidget(BodyLabel(name, theme=theme, size=12), 1)
        close = IconOnlyButton(Icons.CLOSE, color=theme.text_muted, size=14, bg_hover=theme.surface, tooltip=txt["resume_clear_btn"])
        close.clicked.connect(lambda _checked=False, n=name: _remove_attachment(n))
        rl.addWidget(close)
        layout.addWidget(row)
    return holder


def _remove_attachment(name_to_remove: str) -> None:
    STATE.chat_attachments.pop(name_to_remove, None)
    if REFS.rerender_context:
        REFS.rerender_context()


def _quick_actions_body(theme: Theme, lang: str, txt: dict) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    holder.setLayout(layout)

    def _row(icon: str, label: str, on_click) -> ClickFrame:
        row = ClickFrame()
        row.setStyleSheet(
            f"""
            ClickFrame {{
                background: transparent;
                border-radius: 8px;
            }}
            ClickFrame:hover {{
                background-color: {theme.surface_2};
            }}
            """
        )
        rl = hbox(spacing=10, margins=(8, 10, 8, 10))
        rl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        row.setLayout(rl)
        rl.addWidget(IconLabel(icon, color=theme.text_muted, size=16))
        rl.addWidget(BodyLabel(label, theme=theme, size=13), 1)
        rl.addWidget(IconLabel(Icons.CHEVRON_RIGHT, color=theme.text_muted, size=16))
        row.clicked.connect(on_click)
        return row

    def _new_run() -> None:
        STATE.reset_all()
        STATE.mode = MODE_FORM
        STATE.active_tab = TAB_SETUP
        _request_full_refresh()

    def _open_history() -> None:
        STATE.mode = MODE_FORM
        STATE.active_tab = TAB_HISTORY
        _request_full_refresh()

    def _open_how_to() -> None:
        from src.sections.ai_career.how_to import open_career_how_to
        open_career_how_to(get_main_window(), theme, lang)

    layout.addWidget(_row(Icons.POST_ADD, txt["ctx_qa_new_run"], _new_run))
    layout.addWidget(_row(Icons.HISTORY, txt["ctx_qa_show_history"], _open_history))
    layout.addWidget(_row(Icons.MENU_BOOK_OUTLINED, txt["ctx_qa_open_how_to"], _open_how_to))
    return holder


_PREV_UNSUBSCRIBE: dict[str, object] = {"fn": None}


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
            section_card(theme, icon=Icons.PAYMENTS_OUTLINED, title=txt["ctx_cost_title"], body=_cost_body(theme, txt)),
        ]
        if STATE.mode == MODE_CHAT:
            cards.append(section_card(theme, icon=Icons.DESCRIPTION_OUTLINED, title=txt["chat_mode_attached_docs_title"], body=_attachments_body(theme, txt)))
        cards.append(section_card(theme, icon=Icons.INSIGHTS_OUTLINED, title=txt["ctx_activity_title"], body=_activity_body(theme, txt)))
        cards.append(section_card(theme, icon=Icons.BOLT_OUTLINED, title=txt["ctx_quick_actions_title"], body=_quick_actions_body(theme, lang, txt)))
        shell = context_panel_shell(theme, *cards)
        panel_layout.addWidget(shell)

    def _on_cost_change() -> None:
        # COST updates can arrive from worker threads; re-render the
        # context panel on the GUI thread to avoid cross-thread Qt
        # warnings ("Cannot set parent, new parent is in a different thread").
        runtime_dispatch(_render)

    prev = _PREV_UNSUBSCRIBE.get("fn")
    if callable(prev):
        try:
            prev()
        except Exception as exc:
            logger_service.log_exception(
                "ai_career.context", "previous_unsubscribe_failed", exc,
            )
    _PREV_UNSUBSCRIBE["fn"] = COST.subscribe(_on_cost_change)
    REFS.rerender_context = _render

    _render()
    return panel_holder
