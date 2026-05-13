"""Drafts tab for the AI Legal section.

The user dictates rewrites in plain Czech / English; without an LLM
backend we mock the assistant by appending a static reply each time
they send. The crucial bit is the inline A4 preview embedded inside
the first assistant bubble - a paper-like rounded ``QFrame`` with
the rewritten text.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.qt.effects import apply_drop_shadow
from src.qt.icons import Icons
from src.qt.theme import rgba
from src.qt.widgets import (
    AccentLabel,
    BodyLabel,
    ClickFrame,
    IconLabel,
    IconOnlyButton,
    MutedLabel,
    custom_label,
    hbox,
    vbox,
)
from src.sections.ai_legal.data import (
    SECTION_ICON,
    drafts_diff,
    drafts_preview_paragraphs,
    drafts_quick_actions,
)
from src.sections.ai_legal.state import STATE
from src.sections.ai_legal.strings import s
from src.theme import Theme


def _avatar(theme: Theme) -> QFrame:
    avatar = QFrame()
    avatar.setFixedSize(36, 36)
    avatar.setStyleSheet(f"background-color: {theme.primary}; border-radius: 10px;")
    al = hbox(spacing=0, margins=(0, 0, 0, 0))
    al.setAlignment(Qt.AlignmentFlag.AlignCenter)
    avatar.setLayout(al)
    al.addWidget(IconLabel(SECTION_ICON, color="#FFFFFF", size=18),
                 alignment=Qt.AlignmentFlag.AlignCenter)
    return avatar


def _user_avatar(theme: Theme) -> QFrame:
    avatar = QFrame()
    avatar.setFixedSize(28, 28)
    avatar.setStyleSheet(f"background-color: {theme.primary_soft}; border-radius: 14px;")
    al = hbox(spacing=0, margins=(0, 0, 0, 0))
    al.setAlignment(Qt.AlignmentFlag.AlignCenter)
    avatar.setLayout(al)
    al.addWidget(IconLabel(Icons.PERSON, color="#FFFFFF", size=16),
                 alignment=Qt.AlignmentFlag.AlignCenter)
    return avatar


def _action_chip(theme: Theme, icon: str, label: str) -> ClickFrame:
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


def _a4_preview(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    paper = QFrame()
    paper.setStyleSheet(
        """
        QFrame {
            background-color: #F8FAFC;
            border: 1px solid #CBD5F5;
            border-radius: 8px;
        }
        """
    )
    apply_drop_shadow(paper, blur=14, offset=(0, 4), color="#000000", alpha=0.18)
    layout = vbox(spacing=8, margins=(22, 20, 22, 20))
    paper.setLayout(layout)

    accent_bar = QFrame()
    accent_bar.setFixedSize(64, 4)
    accent_bar.setStyleSheet(f"background-color: {theme.primary}; border-radius: 2px; border: none;")
    layout.addWidget(accent_bar)

    layout.addWidget(custom_label(txt["preview_doc_heading"], color="#0F172A", size=18, weight=QFont.Weight.Bold))
    layout.addWidget(custom_label(txt["preview_doc_subheading"], color="#475569", size=12, weight=QFont.Weight.DemiBold))

    for p in drafts_preview_paragraphs(lang):
        layout.addWidget(custom_label(p, color="#0F172A", size=11, selectable=True))

    layout.addSpacing(4)
    layout.addWidget(custom_label(txt["preview_doc_footer"], color="#94A3B8", size=10))
    return paper


def _open_full_button(theme: Theme, lang: str) -> ClickFrame:
    txt = s(lang)
    btn = ClickFrame()
    btn.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {rgba(theme.primary, 0.10)};
            border-radius: 8px;
        }}
        ClickFrame:hover {{
            background-color: {rgba(theme.primary, 0.18)};
        }}
        """
    )
    layout = hbox(spacing=6, margins=(12, 8, 12, 8))
    btn.setLayout(layout)
    layout.addWidget(IconLabel(Icons.OPEN_IN_FULL, color=theme.primary, size=14))
    layout.addWidget(AccentLabel(txt["drafts_preview_open"], theme=theme, size=12, weight=QFont.Weight.DemiBold))
    return btn


def _initial_assistant_bubble(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    preview_block = QFrame()
    preview_block.setStyleSheet("background: transparent;")
    preview_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    preview_block.setLayout(preview_layout)

    head = QFrame()
    head.setStyleSheet("background: transparent;")
    head_layout = hbox(spacing=6, margins=(0, 0, 0, 0))
    head_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    head.setLayout(head_layout)
    head_layout.addWidget(IconLabel(Icons.ARTICLE_OUTLINED, color=theme.primary, size=16))
    head_layout.addWidget(AccentLabel(txt["drafts_preview_title"], theme=theme, size=13, weight=QFont.Weight.Bold))
    head_layout.addStretch(1)
    preview_layout.addWidget(head)

    preview_layout.addWidget(_a4_preview(theme, lang))

    open_row = QFrame()
    open_row.setStyleSheet("background: transparent;")
    open_row_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    open_row_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
    open_row.setLayout(open_row_layout)
    open_row_layout.addStretch(1)
    open_row_layout.addWidget(_open_full_button(theme, lang))
    preview_layout.addWidget(open_row)

    bubble = QFrame()
    bubble.setStyleSheet(f"background-color: {theme.assistant_bubble}; border-radius: 14px;")
    bubble_layout = vbox(spacing=14, margins=(16, 16, 16, 16))
    bubble.setLayout(bubble_layout)
    bubble_layout.addWidget(BodyLabel(txt["drafts_assistant_intro"], theme=theme, size=14, selectable=True))
    bubble_layout.addWidget(preview_block)

    actions = QFrame()
    actions.setStyleSheet("background: transparent;")
    actions_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    actions.setLayout(actions_layout)
    for action in drafts_quick_actions(lang):
        actions_layout.addWidget(_action_chip(theme, action["icon"], action["label"]))
    actions_layout.addStretch(1)

    body = QFrame()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)
    body_layout.addWidget(MutedLabel(txt["drafts_assistant_time"], theme=theme, size=11))
    body_layout.addWidget(bubble)
    body_layout.addWidget(actions)

    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    wl = QHBoxLayout(wrapper)
    wl.setContentsMargins(0, 0, 0, 0)
    wl.setSpacing(12)
    wl.setAlignment(Qt.AlignmentFlag.AlignTop)
    wl.addWidget(_avatar(theme))
    wl.addWidget(body, 1)
    return wrapper


def _user_bubble(theme: Theme, time: str, text: str) -> QWidget:
    bubble = QFrame()
    bubble.setStyleSheet(f"background-color: {theme.user_bubble}; border-radius: 14px;")
    bubble_layout = vbox(spacing=0, margins=(14, 10, 14, 10))
    bubble.setLayout(bubble_layout)
    bubble_layout.addWidget(custom_label(text, color=theme.user_bubble_text, size=14, selectable=True))

    bubble_row = QFrame()
    bubble_row.setStyleSheet("background: transparent;")
    bl = hbox(spacing=10, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignBottom)
    bubble_row.setLayout(bl)
    bl.addWidget(bubble)
    bl.addWidget(_user_avatar(theme))

    inner = QFrame()
    inner.setStyleSheet("background: transparent;")
    inner_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    inner.setLayout(inner_layout)
    time_holder = QFrame()
    time_holder.setStyleSheet("background: transparent;")
    tl = hbox(spacing=0, margins=(0, 0, 4, 0))
    tl.setAlignment(Qt.AlignmentFlag.AlignRight)
    time_holder.setLayout(tl)
    tl.addWidget(MutedLabel(time, theme=theme, size=11))
    inner_layout.addWidget(time_holder)
    inner_layout.addWidget(bubble_row, 0, Qt.AlignmentFlag.AlignRight)

    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    wl = QHBoxLayout(wrapper)
    wl.setContentsMargins(0, 0, 0, 0)
    wl.setSpacing(0)
    wl.addStretch(1)
    wl.addWidget(inner)
    return wrapper


def _diff_assistant_bubble(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    diff_items = drafts_diff(lang)

    bubble = QFrame()
    bubble.setStyleSheet(f"background-color: {theme.assistant_bubble}; border-radius: 14px;")
    bubble_layout = vbox(spacing=8, margins=(14, 14, 14, 14))
    bubble.setLayout(bubble_layout)
    bubble_layout.addWidget(BodyLabel(txt["drafts_assistant_diff_intro"], theme=theme, size=14, weight=QFont.Weight.DemiBold, selectable=True))

    for item in diff_items:
        row = QFrame()
        row.setStyleSheet("background: transparent;")
        row_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
        row_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        row.setLayout(row_layout)
        row_layout.addWidget(IconLabel(Icons.CHECK_CIRCLE_OUTLINED, color="#22C55E", size=16))
        text = BodyLabel(item, theme=theme, size=14, selectable=True)
        text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row_layout.addWidget(text, 1)
        bubble_layout.addWidget(row)

    body = QFrame()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)
    body_layout.addWidget(MutedLabel("11:09", theme=theme, size=11))
    body_layout.addWidget(bubble)

    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    wl = QHBoxLayout(wrapper)
    wl.setContentsMargins(0, 0, 0, 0)
    wl.setSpacing(12)
    wl.setAlignment(Qt.AlignmentFlag.AlignTop)
    wl.addWidget(_avatar(theme))
    wl.addWidget(body, 1)
    return wrapper


def _mock_assistant_bubble(theme: Theme, lang: str, time: str) -> QWidget:
    txt = s(lang)
    bubble = QFrame()
    bubble.setStyleSheet(f"background-color: {theme.assistant_bubble}; border-radius: 14px;")
    bubble_layout = vbox(spacing=0, margins=(14, 14, 14, 14))
    bubble.setLayout(bubble_layout)
    text = BodyLabel(txt["drafts_mock_response"], theme=theme, size=14, selectable=True)
    font = QFont(text.font())
    font.setItalic(True)
    text.setFont(font)
    bubble_layout.addWidget(text)

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
    wl.addWidget(_avatar(theme))
    wl.addWidget(body, 1)
    return wrapper


def _format_now() -> str:
    return datetime.now().strftime("%H:%M")


def _interactive_input(
    theme: Theme,
    lang: str,
    on_send: Callable[[str], None],
) -> QFrame:
    txt = s(lang)
    holder = QFrame()
    holder.setObjectName("LegalDraftsInputBar")
    holder.setStyleSheet(
        f"""
        QFrame#LegalDraftsInputBar {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        """
    )
    layout = hbox(spacing=8, margins=(8, 4, 8, 4))
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    holder.setLayout(layout)

    field = QLineEdit()
    field.setPlaceholderText(txt["drafts_mock_user_label"] + "...")
    field.setStyleSheet(
        f"""
        QLineEdit {{
            background: transparent;
            color: {theme.text};
            border: none;
            padding: 12px 4px;
            selection-background-color: {rgba(theme.primary, 0.30)};
            font-size: 14px;
        }}
        """
    )
    layout.addWidget(field, 1)

    def _send() -> None:
        value = field.text().strip()
        if not value:
            return
        field.clear()
        on_send(value)

    field.returnPressed.connect(_send)
    send_btn = IconOnlyButton(Icons.SEND, color="#FFFFFF", size=18, bg=theme.primary, bg_hover=theme.primary_hover, radius=10)
    send_btn.setFixedSize(40, 40)
    send_btn.clicked.connect(_send)
    layout.addWidget(send_btn)
    return holder


def build_drafts_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Optional[Callable[[], None]] = None,
) -> QWidget:
    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    messages_holder = QWidget()
    messages_holder.setStyleSheet(f"background-color: {theme.bg};")
    msgs_layout = vbox(spacing=22, margins=(24, 20, 24, 20))
    messages_holder.setLayout(msgs_layout)

    msgs_layout.addWidget(_initial_assistant_bubble(theme, lang))
    msgs_layout.addWidget(_user_bubble(theme, s(lang)["drafts_user_time"], s(lang)["drafts_user_message"]))
    msgs_layout.addWidget(_diff_assistant_bubble(theme, lang))

    for entry in STATE.drafts_messages:
        if entry["role"] == "user":
            msgs_layout.addWidget(_user_bubble(theme, entry["time"], entry["text"]))
        else:
            msgs_layout.addWidget(_mock_assistant_bubble(theme, lang, entry["time"]))
    msgs_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(messages_holder)

    layout.addWidget(scroll, 1)

    def _on_send(value: str) -> None:
        time = _format_now()
        STATE.drafts_messages.append({"role": "user", "text": value, "time": time})
        STATE.drafts_messages.append({"role": "assistant", "text": "", "time": time})
        if on_request_rerender is not None:
            on_request_rerender()

    input_wrapper = QFrame()
    input_wrapper.setStyleSheet(f"background-color: {theme.bg};")
    input_layout = hbox(spacing=0, margins=(24, 12, 24, 12))
    input_wrapper.setLayout(input_layout)
    input_layout.addWidget(_interactive_input(theme, lang, _on_send))
    layout.addWidget(input_wrapper)
    return container
