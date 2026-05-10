"""Chat tab for the AI Legal section.

Replicates the screenshot: user asks about ``smlouva_o_dilo.pdf``,
assistant replies with a structured bubble (numbered sections + a
"What it means" callout). The shared :func:`chat_message` doesn't
support callouts mid-bubble, so we hand-build the assistant message
similar to ``ai_marketing.view._assistant_message``.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.components.chat_input import chat_input
from src.qt.icons import Icons
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    ClickFrame,
    IconLabel,
    MutedLabel,
    custom_label,
    hbox,
    vbox,
)
from src.sections.ai_legal.data import (
    SECTION_ICON,
    chat_quick_actions,
)
from src.sections.ai_legal.state import STATE
from src.sections.ai_legal.strings import s
from src.theme import Theme


def _user_attachment_chip(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    file_info = STATE.uploaded_file or {"name": "smlouva_o_dilo.pdf", "type": "PDF"}
    chip = QFrame()
    chip.setStyleSheet(
        f"background-color: rgba(255, 255, 255, 0.18); border-radius: 6px;"
    )
    layout = hbox(spacing=6, margins=(8, 4, 8, 4))
    chip.setLayout(layout)
    layout.addWidget(IconLabel(Icons.ATTACH_FILE, color="rgba(255, 255, 255, 0.85)", size=14))
    layout.addWidget(custom_label(
        f"{txt['chat_user_attachment_label']} {file_info['name']}",
        color="rgba(255, 255, 255, 0.85)",
        size=12,
    ))
    return chip


def _user_bubble(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    bubble = QFrame()
    bubble.setStyleSheet(f"background-color: {theme.user_bubble}; border-radius: 14px;")
    bubble.setFixedWidth(380)
    bubble_layout = vbox(spacing=8, margins=(14, 10, 14, 10))
    bubble.setLayout(bubble_layout)
    bubble_layout.addWidget(custom_label(
        txt["chat_user_question"],
        color=theme.user_bubble_text,
        size=14,
        selectable=True,
    ))
    bubble_layout.addWidget(_user_attachment_chip(theme, lang))

    avatar = QFrame()
    avatar.setFixedSize(28, 28)
    avatar.setStyleSheet(f"background-color: {theme.primary_soft}; border-radius: 14px;")
    al = hbox(spacing=0, margins=(0, 0, 0, 0))
    al.setAlignment(Qt.AlignmentFlag.AlignCenter)
    avatar.setLayout(al)
    al.addWidget(IconLabel(Icons.PERSON, color="#FFFFFF", size=16),
                 alignment=Qt.AlignmentFlag.AlignCenter)

    bubble_row = QFrame()
    bubble_row.setStyleSheet("background: transparent;")
    bl = hbox(spacing=10, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignBottom)
    bubble_row.setLayout(bl)
    bl.addWidget(bubble)
    bl.addWidget(avatar)

    inner = QFrame()
    inner.setStyleSheet("background: transparent;")
    inner_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    inner_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
    inner.setLayout(inner_layout)
    time_holder = QFrame()
    time_holder.setStyleSheet("background: transparent;")
    tl = hbox(spacing=0, margins=(0, 0, 4, 0))
    tl.setAlignment(Qt.AlignmentFlag.AlignRight)
    time_holder.setLayout(tl)
    tl.addWidget(MutedLabel(txt["chat_user_time"], theme=theme, size=11))
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


def _callout_box(theme: Theme, *, label: str, text: str) -> QFrame:
    accent = "#F59E0B"
    box = QFrame()
    box.setObjectName("LegalChatCalloutBox")
    box.setStyleSheet(
        f"""
        QFrame#LegalChatCalloutBox {{
            background-color: {rgba(accent, 0.10)};
            border: 1px solid {rgba(accent, 0.22)};
            border-radius: 10px;
        }}
        """
    )
    layout = hbox(spacing=10, margins=(12, 12, 12, 12))
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    box.setLayout(layout)
    layout.addWidget(IconLabel(Icons.INFO_OUTLINE, color=accent, size=16))
    info = QFrame()
    info.setStyleSheet("background: transparent; border: none;")
    info_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    info.setLayout(info_layout)
    info_layout.addWidget(BodyLabel(label, theme=theme, size=12, weight=QFont.Weight.Bold))
    info_layout.addWidget(MutedLabel(text, theme=theme, size=12))
    layout.addWidget(info, 1)
    return box


def _section_block(
    theme: Theme,
    *,
    title: str,
    text: str,
    callout: Optional[tuple[str, str]] = None,
    bullets: Optional[list[str]] = None,
) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    layout.addWidget(BodyLabel(title, theme=theme, size=14, weight=QFont.Weight.Bold, selectable=True))
    layout.addWidget(BodyLabel(text, theme=theme, size=14, selectable=True))
    if callout is not None:
        layout.addWidget(_callout_box(theme, label=callout[0], text=callout[1]))
    if bullets:
        bullet_holder = QFrame()
        bullet_holder.setStyleSheet("background: transparent;")
        bullet_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
        bullet_holder.setLayout(bullet_layout)
        for bullet in bullets:
            row = QFrame()
            row.setStyleSheet("background: transparent;")
            row_layout = hbox(spacing=0, margins=(4, 0, 0, 0))
            row_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            row.setLayout(row_layout)
            dot = QFrame()
            dot.setFixedSize(6, 6)
            dot.setStyleSheet(f"background-color: {theme.primary}; border-radius: 3px;")
            dot_holder = QFrame()
            dot_holder.setStyleSheet("background: transparent;")
            dh = vbox(spacing=0, margins=(0, 8, 8, 0))
            dot_holder.setLayout(dh)
            dh.addWidget(dot)
            row_layout.addWidget(dot_holder)
            text_label = BodyLabel(bullet, theme=theme, size=14, selectable=True)
            text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            row_layout.addWidget(text_label, 1)
            bullet_layout.addWidget(row)
        layout.addWidget(bullet_holder)
    return holder


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


def _assistant_bubble(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    bubble = QFrame()
    bubble.setStyleSheet(f"background-color: {theme.assistant_bubble}; border-radius: 14px;")
    bubble_layout = vbox(spacing=14, margins=(16, 16, 16, 16))
    bubble.setLayout(bubble_layout)
    bubble_layout.addWidget(BodyLabel(txt["chat_assistant_intro"], theme=theme, size=14, selectable=True))
    bubble_layout.addWidget(_section_block(
        theme,
        title=txt["chat_section1_title"],
        text=txt["chat_section1_text"],
        callout=(txt["chat_callout_label"], txt["chat_callout_text"]),
    ))
    bubble_layout.addWidget(_section_block(
        theme,
        title=txt["chat_section2_title"],
        text=txt["chat_section2_text"],
        bullets=[
            txt["chat_section2_bullet1"],
            txt["chat_section2_bullet2"],
            txt["chat_section2_bullet3"],
        ],
    ))

    actions = QFrame()
    actions.setStyleSheet("background: transparent;")
    actions_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    actions.setLayout(actions_layout)
    for action in chat_quick_actions(lang):
        actions_layout.addWidget(_action_chip(theme, action["icon"], action["label"]))
    actions_layout.addStretch(1)

    avatar = QFrame()
    avatar.setFixedSize(36, 36)
    avatar.setStyleSheet(f"background-color: {theme.primary}; border-radius: 10px;")
    al = hbox(spacing=0, margins=(0, 0, 0, 0))
    al.setAlignment(Qt.AlignmentFlag.AlignCenter)
    avatar.setLayout(al)
    al.addWidget(IconLabel(SECTION_ICON, color="#FFFFFF", size=18),
                 alignment=Qt.AlignmentFlag.AlignCenter)

    body = QFrame()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)
    body_layout.addWidget(MutedLabel(txt["chat_assistant_time"], theme=theme, size=11))
    body_layout.addWidget(bubble)
    body_layout.addWidget(actions)

    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    wl = QHBoxLayout(wrapper)
    wl.setContentsMargins(0, 0, 0, 0)
    wl.setSpacing(12)
    wl.setAlignment(Qt.AlignmentFlag.AlignTop)
    wl.addWidget(avatar)
    wl.addWidget(body, 1)
    return wrapper


def build_chat_tab(theme: Theme, lang: str) -> QWidget:
    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    messages_holder = QWidget()
    messages_holder.setStyleSheet(f"background-color: {theme.bg};")
    msgs_layout = vbox(spacing=22, margins=(24, 20, 24, 20))
    messages_holder.setLayout(msgs_layout)
    msgs_layout.addWidget(_user_bubble(theme, lang))
    msgs_layout.addWidget(_assistant_bubble(theme, lang))
    msgs_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(messages_holder)

    layout.addWidget(scroll, 1)
    layout.addWidget(chat_input(theme, lang))
    return container
