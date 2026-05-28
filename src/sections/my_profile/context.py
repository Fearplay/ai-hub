"""Right-hand context panel for My Profile.

Two read-only cards:

* **Profile status** - whether a profile is saved / demo / empty, plus the
  live activity pill (``ready`` / ``scraping`` / ``analyzing`` / ``error``)
  so the user sees the extraction progress.
* **Open in** - jump straight into the sections that consume this profile
  (AI Career / AI Job Search / AI LinkedIn).

The pipeline runs on a worker thread and calls
``REFS.request_context_refresh()``; we wire ``REFS.rerender_context`` to a
GUI-thread ``_render`` closure (mirroring ``ai_career``) so the activity
pill repaints without a full section rebuild.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QWidget

from src.components.context_panel import (
    context_panel_shell,
    quick_action_row,
)
from src.components.section_card import section_card
from src.qt.icons import Icons
from src.qt.lifecycle import is_widget_alive, on_destroyed
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    IconLabel,
    MutedLabel,
    Pill,
    hbox,
    vbox,
    wrap_label_slot,
)
from src.services import logger as logger_service
from src.sections.my_profile.refs import REFS
from src.sections.my_profile.state import STATE
from src.sections.my_profile.strings import s
from src.theme import Theme


def _open_section_key(key: str) -> None:
    try:
        from src.app import get_active_window
    except Exception as exc:
        logger_service.log_exception(
            "my_profile.context", "open_section_import_failed", exc, key=key,
        )
        return
    window = get_active_window()
    if window is None:
        return
    try:
        window.set_section(key)
    except Exception as exc:
        logger_service.log_exception(
            "my_profile.context", "open_section_failed", exc, key=key,
        )


_ACTIVITY_STYLE = {
    "ready": ("ctx_activity_ready", "#22C55E"),
    "scraping": ("ctx_activity_scraping", "#3B82F6"),
    "analyzing": ("ctx_activity_analyzing", "#7C5CFC"),
    "error": ("ctx_activity_error", "#EF4444"),
}


def _status_body(theme: Theme, txt: dict) -> QWidget:
    body = QFrame()
    body.setStyleSheet("background: transparent;")
    layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    body.setLayout(layout)

    if STATE.demo_mode:
        status_text, dot = txt["ctx_status_demo"], "#F59E0B"
    elif STATE.profile is not None:
        status_text, dot = txt["ctx_status_ready"], "#22C55E"
    else:
        status_text, dot = txt["ctx_status_none"], theme.text_muted

    status_row = QFrame()
    status_row.setStyleSheet("background: transparent;")
    sr = hbox(spacing=8, margins=(0, 0, 0, 0))
    sr.setAlignment(Qt.AlignmentFlag.AlignTop)
    status_row.setLayout(sr)
    sr.addWidget(IconLabel(Icons.CIRCLE, color=dot, size=10), 0, Qt.AlignmentFlag.AlignTop)
    label = BodyLabel(status_text, theme=theme, size=12)
    wrap_label_slot(label)
    sr.addWidget(label, 1)
    layout.addWidget(status_row)

    key, color = _ACTIVITY_STYLE.get(STATE.activity, _ACTIVITY_STYLE["ready"])
    activity_row = QFrame()
    activity_row.setStyleSheet("background: transparent;")
    ar = hbox(spacing=8, margins=(0, 0, 0, 0))
    ar.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    activity_row.setLayout(ar)
    ar.addWidget(MutedLabel(txt["ctx_activity_title"], theme=theme, size=11))
    ar.addStretch(1)
    ar.addWidget(Pill(text=txt[key], bg=rgba(color, 0.16), fg=color))
    layout.addWidget(activity_row)
    return body


def _open_in_body(theme: Theme, lang: str, txt: dict) -> QWidget:
    body = QFrame()
    body.setStyleSheet("background: transparent;")
    layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    body.setLayout(layout)

    targets = (
        (Icons.ASSIGNMENT_IND_OUTLINED, txt["ctx_open_career"], "ai_career"),
        (Icons.WORK_OUTLINE, txt["ctx_open_jobs"], "ai_jobs"),
        (Icons.LINKEDIN, txt["ctx_open_linkedin"], "ai_linkedin"),
    )
    for icon, label, key in targets:
        row = quick_action_row(theme, icon, label)
        row.clicked.connect(lambda _=False, k=key: _open_section_key(k))
        layout.addWidget(row)
    return body


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
        try:
            _clear()
            cards = [
                section_card(
                    theme, icon=Icons.ID_CARD, title=txt["ctx_status_title"],
                    body=_status_body(theme, txt),
                ),
                section_card(
                    theme, icon=Icons.OPEN_IN_NEW, title=txt["ctx_actions_title"],
                    body=_open_in_body(theme, lang, txt),
                ),
            ]
            panel_layout.addWidget(context_panel_shell(theme, *cards))
        except Exception as exc:
            logger_service.log_exception("my_profile.context", "render_failed", exc)

    _render()
    REFS.rerender_context = _render

    def _on_destroyed() -> None:
        if REFS.rerender_context is _render:
            REFS.rerender_context = None

    on_destroyed(panel_holder, _on_destroyed)
    return panel_holder
