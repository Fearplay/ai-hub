"""Right-hand context panel for the AI Legal section.

Three cards stacked from top to bottom:

1. **Attached documents** - the click-to-browse / drop zone is the only
   way to attach a file. There is no separate upload button anymore -
   the dashed drop frame *is* the button. Once a document is parsed we
   render a small chip with its name + size below the zone.
2. **Document analysis** - the four stats (Summary / Risks / Important
   clauses / Recommendations) followed by a primary button that jumps
   the user to the Analysis tab.
3. **Quick actions** - same chevron-list pattern other sections use.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QSizePolicy,
    QStackedLayout,
    QWidget,
)

from src.components.context_panel import (
    context_panel_shell,
    quick_actions_column,
)
from src.components.document_chip import document_chip
from src.components.section_card import section_card
from src.qt.icons import Icons
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    ClickFrame,
    IconLabel,
    MutedLabel,
    PrimaryButton,
    custom_label,
    hbox,
    vbox,
    wrap_label_slot,
)
from src.services import logger as logger_service
from src.services.file_parser import ParsedFile
from src.sections.ai_legal import pipeline
from src.sections.ai_legal.data import context_quick_actions, context_stats
from src.sections.ai_legal.drop_zone import drop_zone
from src.sections.ai_legal.refs import REFS
from src.sections.ai_legal.state import STATE
from src.sections.ai_legal.strings import s
from src.theme import Theme


_STATUS_COLOR = {
    "ok": "#22C55E",
    "warn": "#F59E0B",
    "info": "#3B82F6",
}

_STATUS_ICON = {
    "ok": Icons.CHECK_CIRCLE,
    "warn": Icons.WARNING_AMBER_ROUNDED,
    "info": Icons.INFO,
}


def _analysis_stat_row(
    theme: Theme,
    *,
    icon: str,
    title: str,
    desc: str,
    status: str,
) -> QFrame:
    accent = _STATUS_COLOR.get(status, theme.text_muted)
    row = QFrame()
    row.setStyleSheet("background: transparent;")
    layout = hbox(spacing=10, margins=(4, 6, 4, 6))
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    row.setLayout(layout)

    badge = QFrame()
    badge.setFixedSize(28, 28)
    badge.setStyleSheet(
        f"background-color: {rgba(accent, 0.15)}; border-radius: 8px;"
    )
    bl = hbox(spacing=0, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setLayout(bl)
    bl.addWidget(IconLabel(icon, color=accent, size=16), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(badge)

    info = QFrame()
    info.setStyleSheet("background: transparent;")
    wrap_label_slot(info)
    info_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    info.setLayout(info_layout)
    info_layout.addWidget(BodyLabel(title, theme=theme, size=13, weight=QFont.Weight.DemiBold))
    info_layout.addWidget(MutedLabel(desc, theme=theme, size=11))
    layout.addWidget(info, 1)

    layout.addWidget(IconLabel(_STATUS_ICON.get(status, Icons.INFO), color=accent, size=18))
    return row


def _build_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    def _on_open_analysis() -> None:
        STATE.active_tab = 1
        if REFS.rerender_main is not None:
            REFS.rerender_main()

    def _on_file_resolved(file_dict: dict, parsed: ParsedFile) -> None:
        try:
            pipeline.attach_document(file_dict=file_dict, parsed=parsed)
        except Exception as exc:
            logger_service.log_exception(
                "ai_legal.context", "attach_document_failed", exc,
                name=file_dict.get("name", ""),
            )
            return
        if REFS.rerender_context is not None:
            REFS.rerender_context()
        if REFS.rerender_tab_body is not None:
            REFS.rerender_tab_body()

    docs_holder = QFrame()
    docs_holder.setStyleSheet("background: transparent;")
    docs_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    docs_holder.setLayout(docs_layout)

    docs_layout.addWidget(drop_zone(theme, lang, on_file_resolved=_on_file_resolved, height=120))

    if STATE.uploaded_file:
        f = STATE.uploaded_file
        docs_layout.addWidget(document_chip(theme, lang, name=f["name"], ext=f["type"], size=f["size"]))
    else:
        docs_layout.addWidget(MutedLabel(txt["ctx_no_doc"], theme=theme, size=12))

    documents_card = section_card(theme, icon=Icons.DESCRIPTION_OUTLINED, title=txt["ctx_attached_title"], body=docs_holder)

    analysis_holder = QFrame()
    analysis_holder.setStyleSheet("background: transparent;")
    analysis_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    analysis_holder.setLayout(analysis_layout)
    for stat in context_stats(lang):
        analysis_layout.addWidget(_analysis_stat_row(
            theme,
            icon=stat["icon"],
            title=stat["title"],
            desc=stat["desc"],
            status=stat["status"],
        ))
    btn = PrimaryButton(txt["ctx_show_detail_btn"], theme=theme)
    btn.clicked.connect(_on_open_analysis)
    analysis_layout.addWidget(btn)

    analysis_card = section_card(theme, icon=Icons.INSIGHTS_OUTLINED, title=txt["ctx_analysis_title"], body=analysis_holder)

    quick_actions_card = section_card(
        theme,
        icon=Icons.BOLT_OUTLINED,
        title=txt["ctx_quick_actions"],
        body=quick_actions_column(theme, context_quick_actions(lang)),
    )

    return context_panel_shell(theme, documents_card, analysis_card, quick_actions_card)


def build_context(theme: Theme, lang: str) -> QWidget:
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
