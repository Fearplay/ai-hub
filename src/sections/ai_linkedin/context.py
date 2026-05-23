"""Right-hand context panel for AI LinkedIn (PySide6 port)."""

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
from src.qt.lifecycle import is_widget_alive, on_destroyed
from src.qt.runtime import dispatch as runtime_dispatch
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    ClickFrame,
    IconLabel,
    IconOnlyButton,
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
from src.sections.ai_linkedin.data import (
    brand_profile_fields,
    quick_actions,
    recent_runs,
)
from src.sections.ai_linkedin.refs import REFS
from src.sections.ai_linkedin.state import (
    MODE_CHAT,
    MODE_BUILDER,
    STATE,
    TAB_HISTORY,
    TAB_SETUP,
)
from src.sections.ai_linkedin.strings import s
from src.theme import Theme


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.context", "request_full_refresh_import", exc,
        )
        return
    request_section_refresh()


_ACTIVITY_KEYS = {
    "ready": "ctx_activity_ready",
    "scraping": "ctx_activity_scraping",
    "parsing": "ctx_activity_parsing",
    "extracting": "ctx_activity_extracting",
    "analyzing": "ctx_activity_analyzing",
    "generating": "ctx_activity_generating",
    "scoring": "ctx_activity_scoring",
    "saving": "ctx_activity_saving",
    "error": "ctx_activity_error",
}


def _brief_field(theme: Theme, *, label: str, value: str, chip: bool = False) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    layout.addWidget(MutedLabel(label, theme=theme, size=11, weight=QFont.Weight.Medium))

    if chip:
        chip_w = QFrame()
        chip_w.setStyleSheet(
            f"background-color: {rgba(theme.primary, 0.18)}; border-radius: 12px;"
        )
        cl = hbox(spacing=0, margins=(10, 4, 10, 4))
        chip_w.setLayout(cl)
        chip_w.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        cl.addWidget(BodyLabel(value, theme=theme, size=12, weight=QFont.Weight.Medium))
        chip_row = QFrame()
        chip_row.setStyleSheet("background: transparent;")
        crl = hbox(spacing=0, margins=(0, 0, 0, 0))
        crl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        chip_row.setLayout(crl)
        crl.addWidget(chip_w)
        crl.addStretch(1)
        layout.addWidget(chip_row)
    else:
        layout.addWidget(BodyLabel(value, theme=theme, size=13, weight=QFont.Weight.Medium))
    return holder


def _brief_content(theme: Theme, lang: str) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=12, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    for field in brand_profile_fields(lang):
        layout.addWidget(_brief_field(theme, label=field["label"], value=field["value"], chip=field.get("chip", False)))
    return holder


def _activity_body(theme: Theme, txt: dict) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=6, margins=(0, 0, 0, 0))
    holder.setLayout(layout)

    key = _ACTIVITY_KEYS.get(STATE.activity, "ctx_activity_ready")
    label = txt.get(key) or txt["ctx_activity_ready"]
    color = "#22C55E" if STATE.activity == "ready" else (
        "#EF4444" if STATE.activity == "error" else theme.primary
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
        layout.addWidget(MutedLabel("—", theme=theme, size=12))
        return holder

    for name in list(STATE.chat_attachments.keys()):
        row = QFrame()
        row.setStyleSheet(f"background-color: {theme.surface_2}; border-radius: 8px;")
        rl = hbox(spacing=8, margins=(8, 4, 4, 4))
        rl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        row.setLayout(rl)
        rl.addWidget(IconLabel(Icons.DESCRIPTION_OUTLINED, color=theme.primary, size=16))
        rl.addWidget(BodyLabel(name, theme=theme, size=12), 1)
        close = IconOnlyButton(Icons.CLOSE, color=theme.text_muted, size=14, bg_hover=theme.surface)
        close.clicked.connect(lambda _checked=False, n=name: _remove_attachment(n))
        rl.addWidget(close)
        layout.addWidget(row)
    return holder


def _remove_attachment(name: str) -> None:
    STATE.chat_attachments.pop(name, None)
    if REFS.rerender_context:
        try:
            REFS.rerender_context()
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.context", "remove_attachment_rerender_failed", exc,
            )


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

    def _new_build() -> None:
        STATE.reset_all()
        STATE.mode = MODE_BUILDER
        STATE.active_tab = TAB_SETUP
        _request_full_refresh()

    def _improve_headline() -> None:
        from src.sections.ai_linkedin.state import SEC_HEADLINE
        STATE.mode = MODE_BUILDER
        STATE.active_tab = TAB_SETUP
        STATE.selected_sections = {SEC_HEADLINE}
        _request_full_refresh()

    def _write_post() -> None:
        from src.sections.ai_linkedin.state import SEC_POSTS
        STATE.mode = MODE_BUILDER
        STATE.active_tab = TAB_SETUP
        STATE.selected_sections = {SEC_POSTS}
        _request_full_refresh()

    def _open_history() -> None:
        STATE.mode = MODE_BUILDER
        STATE.active_tab = TAB_HISTORY
        _request_full_refresh()

    def _open_how_to() -> None:
        from src.qt.runtime import get_main_window
        from src.sections.ai_linkedin.how_to import open_linkedin_how_to
        open_linkedin_how_to(get_main_window(), theme, lang)

    handlers = {
        "build_full": _new_build,
        "improve_headline": _improve_headline,
        "write_post": _write_post,
        "show_history": _open_history,
        "how_to": _open_how_to,
    }

    for action in quick_actions(lang):
        handler = handlers.get(action["key"])
        if handler is None:
            continue
        layout.addWidget(_row(action["icon"], action["label"], handler))
    return holder


def _recent_body(theme: Theme, lang: str) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    holder.setLayout(layout)

    runs = recent_runs(lang)
    if not runs:
        layout.addWidget(MutedLabel("—", theme=theme, size=12))
        return holder
    for entry in runs:
        item = QFrame()
        item.setStyleSheet("background: transparent; border-radius: 6px;")
        il = vbox(spacing=2, margins=(4, 6, 4, 6))
        item.setLayout(il)
        il.addWidget(BodyLabel(entry["title"], theme=theme, size=12, weight=QFont.Weight.DemiBold))
        il.addWidget(MutedLabel(entry.get("time") or "—", theme=theme, size=11))
        layout.addWidget(item)
    return holder


def _cost_body(theme: Theme) -> QFrame:
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
    layout.addWidget(BodyLabel(f"{COST.calls} calls · {COST.tokens_total} tokens", theme=theme, size=13))
    layout.addWidget(BodyLabel(f"~ ${COST.cost_usd:.4f}", theme=theme, size=13, weight=QFont.Weight.Bold))
    layout.addWidget(SubtleLabel(f"{provider_label.title()} · {model_label}", theme=theme, size=11, italic=True))
    return holder


_PREV_UNSUBSCRIBE: dict[str, object] = {"fn": None}


def build_context(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    panel_holder = QFrame()
    panel_holder.setStyleSheet("background: transparent;")
    panel_layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    panel_holder.setLayout(panel_layout)

    def _clear() -> None:
        if not is_widget_alive(panel_holder):
            return
        while panel_layout.count():
            item = panel_layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _render() -> None:
        if not is_widget_alive(panel_holder):
            return
        _clear()
        cards: list[QWidget] = [
            section_card(theme, icon=Icons.PERSON_OUTLINE, title=txt["ctx_brand_title"], body=_brief_content(theme, lang)),
            section_card(theme, icon=Icons.RADIO_BUTTON_CHECKED, title=txt["ctx_activity_title"], body=_activity_body(theme, txt)),
        ]
        if STATE.mode == MODE_CHAT:
            cards.append(section_card(theme, icon=Icons.ATTACH_FILE, title=txt["ctx_attachments_title"], body=_attachments_body(theme, txt)))
        cards.append(section_card(theme, icon=Icons.BOLT_OUTLINED, title=txt["ctx_quick_actions_title"], body=_quick_actions_body(theme, lang, txt)))
        cards.append(section_card(theme, icon=Icons.HISTORY, title=txt["ctx_recent_title"], body=_recent_body(theme, lang)))
        cards.append(section_card(theme, icon=Icons.PAYMENTS_OUTLINED, title=txt["ctx_cost_title"], body=_cost_body(theme)))
        shell = context_panel_shell(theme, *cards)
        panel_layout.addWidget(shell)

    def _on_cost_change() -> None:
        # COST.subscribe fires from worker threads (any AI provider
        # call). We MUST hop to the GUI thread before mutating widgets
        # - direct ``_render()`` here is a Qt threading violation.
        runtime_dispatch(_render)

    prev = _PREV_UNSUBSCRIBE.get("fn")
    if callable(prev):
        try:
            prev()
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.context", "cost_unsubscribe_failed", exc,
            )
    _PREV_UNSUBSCRIBE["fn"] = COST.subscribe(_on_cost_change)
    REFS.rerender_context = _render

    def _on_panel_destroyed() -> None:
        if REFS.rerender_context is _render:
            REFS.rerender_context = None
        prev_fn = _PREV_UNSUBSCRIBE.get("fn")
        if callable(prev_fn):
            try:
                prev_fn()
            finally:
                _PREV_UNSUBSCRIBE["fn"] = None

    on_destroyed(panel_holder, _on_panel_destroyed)

    try:
        store.list_runs()
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.context", "list_runs_warmup_failed", exc,
        )

    _render()
    return panel_holder
