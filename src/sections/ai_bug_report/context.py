"""Right-hand context panel for the AI Bug Report section.

Three cards:

* **Activity** - live status dot reflecting ``STATE.activity``
  (ready / generating / saving / error). Worker threads call
  ``REFS.request_context_refresh()`` so the dot turns over the next
  GUI tick instead of waiting for the user to click something.
* **Attachments** - quick "X screenshots / Y documents" tally so the
  user knows what is staged before generation.
* **Session cost** - shared ``COST`` counter (calls / tokens / $) and
  the current provider / model.
* **Last save** - path of the most recently saved Word run, when there
  is one. Clicking is intentionally not wired - the Export tab handles
  "Open output folder" with the full button affordance.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QStackedLayout, QWidget

from src.components.context_panel import context_panel_shell
from src.components.section_card import section_card
from src.qt.icons import Icons
from src.qt.widgets import (
    BodyLabel,
    MutedLabel,
    SubtleLabel,
    custom_label,
    hbox,
    vbox,
)
from src.services import settings_store
from src.services.cost_tracker import COST
from src.sections.ai_bug_report.refs import REFS
from src.sections.ai_bug_report.state import STATE
from src.sections.ai_bug_report.strings import s
from src.theme import Theme


_ACTIVITY_KEYS = {
    "ready": "ctx_activity_ready",
    "generating": "ctx_activity_generating",
    "saving": "ctx_activity_saving",
    "error": "ctx_activity_error",
}


def _activity_body(theme: Theme, txt: dict) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    holder.setLayout(layout)

    key = _ACTIVITY_KEYS.get(STATE.activity, "ctx_activity_ready")
    label = txt.get(key) or txt["ctx_activity_ready"]
    color = (
        "#22C55E"
        if STATE.activity == "ready"
        else (
            "#EF4444"
            if STATE.activity == "error"
            else theme.primary
        )
    )

    row = QFrame()
    row.setStyleSheet("background: transparent;")
    row_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    row_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    row.setLayout(row_layout)

    dot_holder = QFrame()
    dot_holder.setStyleSheet("background: transparent;")
    dot_layout = vbox(spacing=0, margins=(0, 4, 0, 0))
    dot_holder.setLayout(dot_layout)
    dot = QFrame()
    dot.setFixedSize(10, 10)
    dot.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
    dot_layout.addWidget(dot)
    row_layout.addWidget(dot_holder)
    row_layout.addWidget(
        BodyLabel(label, theme=theme, size=13, weight=QFont.Weight.DemiBold), 1
    )
    layout.addWidget(row)

    if STATE.last_error and STATE.activity == "error":
        layout.addWidget(custom_label(STATE.last_error, color="#EF4444", size=11, selectable=True))
    return holder


def _attachments_body(theme: Theme, txt: dict) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    if not STATE.images and not STATE.documents:
        layout.addWidget(MutedLabel(txt["ctx_attachments_empty"], theme=theme, size=12))
        return holder
    layout.addWidget(
        BodyLabel(
            txt["ctx_attachments_template"].format(
                images=len(STATE.images), docs=len(STATE.documents)
            ),
            theme=theme,
            size=13,
        )
    )
    return holder


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
    layout.addWidget(
        BodyLabel(
            txt["ctx_cost_calls_template"].format(
                calls=COST.calls, tokens=COST.tokens_total
            ),
            theme=theme,
            size=13,
        )
    )
    layout.addWidget(
        BodyLabel(
            txt["ctx_cost_session_template"].format(cost=COST.cost_usd),
            theme=theme,
            size=13,
            weight=QFont.Weight.Bold,
        )
    )
    layout.addWidget(
        SubtleLabel(
            txt["ctx_provider_template"].format(
                provider=provider_label.title(), model=model_label
            ),
            theme=theme,
            size=11,
            italic=True,
        )
    )
    return holder


def _last_save_body(theme: Theme, txt: dict) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    if not STATE.last_save_path:
        layout.addWidget(MutedLabel(txt["ctx_last_save_empty"], theme=theme, size=12))
    else:
        layout.addWidget(BodyLabel(STATE.last_save_path, theme=theme, size=12, selectable=True))
    return holder


def _build_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    return context_panel_shell(
        theme,
        section_card(
            theme,
            icon=Icons.BOLT_OUTLINED,
            title=txt["ctx_activity_title"],
            body=_activity_body(theme, txt),
        ),
        section_card(
            theme,
            icon=Icons.UPLOAD_FILE,
            title=txt["ctx_attachments_title"],
            body=_attachments_body(theme, txt),
        ),
        section_card(
            theme,
            icon=Icons.QUERY_STATS,
            title=txt["ctx_cost_title"],
            body=_cost_body(theme, txt),
        ),
        section_card(
            theme,
            icon=Icons.SAVE_OUTLINED,
            title=txt["ctx_last_save_title"],
            body=_last_save_body(theme, txt),
        ),
    )


def build_context(theme: Theme, lang: str) -> QWidget:
    """Stacked-layout shell so the pipeline can rebuild the panel in place.

    The pipeline calls ``REFS.request_context_refresh()`` from worker
    threads after mutating ``STATE.activity`` / ``STATE.last_error``;
    the queued ``_rerender_context`` then swaps the inner widget on the
    GUI thread without re-parenting the outer holder, which keeps the
    sidebar layout stable.
    """
    holder = QWidget()
    holder.setStyleSheet("background: transparent;")
    stack = QStackedLayout(holder)
    stack.setContentsMargins(0, 0, 0, 0)
    stack.addWidget(_build_panel(theme, lang))

    def _rerender_context() -> None:
        while stack.count():
            w = stack.widget(0)
            stack.removeWidget(w)
            w.deleteLater()
        stack.addWidget(_build_panel(theme, lang))

    REFS.rerender_context = _rerender_context
    return holder
