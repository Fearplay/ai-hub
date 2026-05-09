"""Analysis tab for the AI Legal section.

Two presentation modes that share the same mock data
(:func:`src.sections.ai_legal.data.analysis_findings`):

* ``document`` - polished read-only summary with green / yellow / blue
  cards.
* ``chat`` - the same findings spread across a chain of assistant chat
  bubbles.

The toggle between the two persists in :class:`LegalState` so users
keep their choice when switching tabs / theme / language.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.qt.icons import Icons
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    ClickFrame,
    IconLabel,
    MutedLabel,
    Pill,
    TitleLabel,
    custom_label,
    hbox,
    vbox,
)
from src.sections.ai_legal.data import (
    SECTION_ICON,
    analysis_findings,
    analysis_markdown,
)
from src.sections.ai_legal.state import STATE
from src.sections.ai_legal.strings import s
from src.theme import Theme


_OK_COLOR = "#22C55E"
_RISK_COLOR = "#F97316"
_INFO_COLOR = "#3B82F6"


def _segmented_button(
    theme: Theme,
    label: str,
    *,
    active: bool,
    on_click: Callable[[], None],
) -> ClickFrame:
    chip = ClickFrame()
    chip.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {theme.primary if active else 'transparent'};
            border-radius: 8px;
        }}
        ClickFrame:hover {{
            background-color: {theme.primary if active else theme.surface_2};
        }}
        """
    )
    layout = hbox(spacing=0, margins=(14, 8, 14, 8))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    chip.setLayout(layout)
    color = "#FFFFFF" if active else theme.text_muted
    layout.addWidget(custom_label(label, color=color, size=12, weight=QFont.Weight.DemiBold))
    chip.clicked.connect(on_click)
    return chip


def _view_toggle(
    theme: Theme,
    lang: str,
    on_change: Callable[[str], None],
) -> QFrame:
    txt = s(lang)
    mode = STATE.analysis_view_mode
    holder = QFrame()
    holder.setStyleSheet(
        f"""
        QFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 10px;
        }}
        """
    )
    layout = hbox(spacing=4, margins=(4, 4, 4, 4))
    holder.setLayout(layout)
    layout.addWidget(_segmented_button(theme, txt["analysis_view_document"], active=mode == "document", on_click=lambda: on_change("document")))
    layout.addWidget(_segmented_button(theme, txt["analysis_view_chat"], active=mode == "chat", on_click=lambda: on_change("chat")))
    return holder


def _findings_card(
    theme: Theme,
    *,
    icon: str,
    title: str,
    items: list[str],
    accent: str,
) -> QFrame:
    card = QFrame()
    card.setStyleSheet(
        f"""
        QFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 14px;
        }}
        """
    )
    layout = vbox(spacing=10, margins=(16, 16, 16, 16))
    card.setLayout(layout)

    head = QFrame()
    head.setStyleSheet("background: transparent; border: none;")
    head_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    head_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    head.setLayout(head_layout)

    badge = QFrame()
    badge.setFixedSize(32, 32)
    badge.setStyleSheet(
        f"background-color: {rgba(accent, 0.15)}; border: none; border-radius: 8px;"
    )
    bl = hbox(spacing=0, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setLayout(bl)
    bl.addWidget(IconLabel(icon, color=accent, size=18), alignment=Qt.AlignmentFlag.AlignCenter)
    head_layout.addWidget(badge)

    title_label = TitleLabel(title, theme=theme, size=14, weight=QFont.Weight.Bold)
    title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    head_layout.addWidget(title_label, 1)

    head_layout.addWidget(Pill(text=str(len(items)), bg=rgba(accent, 0.18), fg=accent))
    layout.addWidget(head)

    for item in items:
        row = QFrame()
        row.setStyleSheet("background: transparent; border: none;")
        row_layout = hbox(spacing=0, margins=(2, 0, 0, 0))
        row_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        row.setLayout(row_layout)

        dot = QFrame()
        dot.setFixedSize(6, 6)
        dot.setStyleSheet(f"background-color: {accent}; border-radius: 3px;")
        dot_holder = QFrame()
        dot_holder.setStyleSheet("background: transparent; border: none;")
        dh = vbox(spacing=0, margins=(0, 8, 10, 0))
        dot_holder.setLayout(dh)
        dh.addWidget(dot)
        row_layout.addWidget(dot_holder)

        text_label = BodyLabel(item, theme=theme, size=13, selectable=True)
        text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row_layout.addWidget(text_label, 1)
        layout.addWidget(row)

    return card


def _document_view(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    findings = analysis_findings(lang)

    inner = QWidget()
    inner.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=16, margins=(24, 20, 24, 20))
    inner.setLayout(layout)

    title_holder = QFrame()
    title_holder.setStyleSheet("background: transparent;")
    title_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    title_holder.setLayout(title_layout)
    title_layout.addWidget(TitleLabel(txt["analysis_doc_title"], theme=theme, size=18, weight=QFont.Weight.Bold))
    title_layout.addWidget(MutedLabel(txt["analysis_doc_subtitle"], theme=theme, size=13))
    layout.addWidget(title_holder)

    cards_row = QFrame()
    cards_row.setStyleSheet("background: transparent;")
    cards_layout = hbox(spacing=14, margins=(0, 0, 0, 0))
    cards_row.setLayout(cards_layout)
    cards_layout.addWidget(_findings_card(theme, icon=Icons.CHECK_CIRCLE_OUTLINED, title=txt["analysis_correct_title"], items=findings["right"], accent=_OK_COLOR), 1)
    cards_layout.addWidget(_findings_card(theme, icon=Icons.WARNING_AMBER_OUTLINED, title=txt["analysis_wrong_title"], items=findings["risk"], accent=_RISK_COLOR), 1)
    layout.addWidget(cards_row)

    layout.addWidget(_findings_card(theme, icon=Icons.LIGHTBULB_OUTLINE, title=txt["analysis_recommendations_title"], items=findings["recommendations"], accent=_INFO_COLOR))

    md_card = QFrame()
    md_card.setStyleSheet(
        f"""
        QFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 14px;
        }}
        """
    )
    md_layout = vbox(spacing=0, margins=(18, 18, 18, 18))
    md_card.setLayout(md_layout)
    md_text = BodyLabel(analysis_markdown(lang), theme=theme, size=13, selectable=True)
    md_text.setTextFormat(Qt.TextFormat.MarkdownText)
    md_layout.addWidget(md_text)
    layout.addWidget(md_card)
    layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(inner)
    return scroll


def _chat_avatar(theme: Theme) -> QFrame:
    avatar = QFrame()
    avatar.setFixedSize(36, 36)
    avatar.setStyleSheet(f"background-color: {theme.primary}; border-radius: 10px;")
    al = hbox(spacing=0, margins=(0, 0, 0, 0))
    al.setAlignment(Qt.AlignmentFlag.AlignCenter)
    avatar.setLayout(al)
    al.addWidget(IconLabel(SECTION_ICON, color="#FFFFFF", size=18),
                 alignment=Qt.AlignmentFlag.AlignCenter)
    return avatar


def _chat_bubble(
    theme: Theme,
    *,
    intro: str,
    items: list[str],
    accent: str,
    icon: str,
    time: str,
    bullet_marker: str = "\u2022",
) -> QWidget:
    bubble = QFrame()
    bubble.setStyleSheet(f"background-color: {theme.assistant_bubble}; border-radius: 14px;")
    bubble_layout = vbox(spacing=8, margins=(14, 14, 14, 14))
    bubble.setLayout(bubble_layout)

    head = QFrame()
    head.setStyleSheet("background: transparent;")
    head_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    head_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    head.setLayout(head_layout)
    head_layout.addWidget(IconLabel(icon, color=accent, size=18))
    title = BodyLabel(intro, theme=theme, size=14, weight=QFont.Weight.Bold)
    title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    head_layout.addWidget(title, 1)
    bubble_layout.addWidget(head)

    for item in items:
        row = QFrame()
        row.setStyleSheet("background: transparent;")
        row_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
        row_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        row.setLayout(row_layout)
        row_layout.addWidget(custom_label(bullet_marker, color=accent, size=14, weight=QFont.Weight.Bold))
        text = BodyLabel(item, theme=theme, size=14, selectable=True)
        text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row_layout.addWidget(text, 1)
        bubble_layout.addWidget(row)

    body = QFrame()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)
    body_layout.addWidget(MutedLabel(time, theme=theme, size=11))
    body_layout.addWidget(bubble)

    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    wl = QHBoxLayout(wrapper)
    wl.setContentsMargins(0, 0, 0, 0)
    wl.setSpacing(12)
    wl.setAlignment(Qt.AlignmentFlag.AlignTop)
    wl.addWidget(_chat_avatar(theme))
    wl.addWidget(body, 1)
    return wrapper


def _chat_action_chip(theme: Theme, icon: str, label: str) -> ClickFrame:
    chip = ClickFrame()
    chip.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 8px;
        }}
        ClickFrame:hover {{
            background-color: {theme.surface_2};
        }}
        """
    )
    layout = hbox(spacing=6, margins=(10, 6, 10, 6))
    chip.setLayout(layout)
    layout.addWidget(IconLabel(icon, color=theme.primary, size=14))
    layout.addWidget(BodyLabel(label, theme=theme, size=12, weight=QFont.Weight.Medium))
    return chip


def _chat_view(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    findings = analysis_findings(lang)

    inner = QWidget()
    inner.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=22, margins=(24, 20, 24, 20))
    inner.setLayout(layout)

    intro_bubble = QFrame()
    intro_bubble.setStyleSheet(f"background-color: {theme.assistant_bubble}; border-radius: 14px;")
    ib_layout = vbox(spacing=0, margins=(14, 14, 14, 14))
    intro_bubble.setLayout(ib_layout)
    ib_layout.addWidget(BodyLabel(txt["analysis_chat_intro"], theme=theme, size=14, selectable=True))

    intro_body = QFrame()
    intro_body.setStyleSheet("background: transparent;")
    ibody_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    intro_body.setLayout(ibody_layout)
    ibody_layout.addWidget(MutedLabel("11:14", theme=theme, size=11))
    ibody_layout.addWidget(intro_bubble)

    intro_wrapper = QWidget()
    intro_wrapper.setStyleSheet("background: transparent;")
    iw_layout = QHBoxLayout(intro_wrapper)
    iw_layout.setContentsMargins(0, 0, 0, 0)
    iw_layout.setSpacing(12)
    iw_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    iw_layout.addWidget(_chat_avatar(theme))
    iw_layout.addWidget(intro_body, 1)

    layout.addWidget(intro_wrapper)
    layout.addWidget(_chat_bubble(theme, intro=txt["analysis_correct_title"], items=findings["right"], accent=_OK_COLOR, icon=Icons.CHECK_CIRCLE_OUTLINED, time="11:14"))
    layout.addWidget(_chat_bubble(theme, intro=txt["analysis_wrong_title"], items=findings["risk"], accent=_RISK_COLOR, icon=Icons.WARNING_AMBER_OUTLINED, time="11:15"))
    layout.addWidget(_chat_bubble(theme, intro=txt["analysis_recommendations_title"], items=findings["recommendations"], accent=_INFO_COLOR, icon=Icons.LIGHTBULB_OUTLINE, time="11:15"))

    actions_row = QFrame()
    actions_row.setStyleSheet("background: transparent;")
    actions_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    actions_row.setLayout(actions_layout)
    actions_layout.addWidget(_chat_action_chip(theme, Icons.PICTURE_AS_PDF, txt["analysis_chat_action_export"]))
    actions_layout.addWidget(_chat_action_chip(theme, Icons.FORWARD_TO_INBOX, txt["analysis_chat_action_email"]))
    actions_layout.addStretch(1)
    layout.addWidget(actions_row)
    layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(inner)
    return scroll


def build_analysis_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Optional[Callable[[], None]] = None,
) -> QWidget:
    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    def _switch_mode(mode: str) -> None:
        if mode == STATE.analysis_view_mode:
            return
        STATE.analysis_view_mode = mode
        if on_request_rerender is not None:
            on_request_rerender()

    toggle_row = QFrame()
    toggle_row.setStyleSheet(f"background-color: {theme.bg};")
    toggle_layout = hbox(spacing=0, margins=(24, 14, 24, 4))
    toggle_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
    toggle_row.setLayout(toggle_layout)
    toggle_layout.addWidget(_view_toggle(theme, lang, _switch_mode))

    layout.addWidget(toggle_row)
    if STATE.analysis_view_mode == "document":
        layout.addWidget(_document_view(theme, lang), 1)
    else:
        layout.addWidget(_chat_view(theme, lang), 1)
    return container
