"""Chat tab for the AI Legal section.

The layout is intentionally minimal: an expanding messages area sits on
top, a compact bottom strip below the input keeps the four quick-action
chips reachable at all times. When ``STATE.chat_messages`` is empty the
messages area is a plain spacer and a single grey hint line appears
right above the input ("Type your request for the attached document.")
— the hint disappears as soon as the first message is sent.

All AI calls go through :mod:`src.sections.ai_legal.pipeline` so this
file only deals with rendering and routing user input.
"""

from __future__ import annotations

import threading
from typing import Callable

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

from src.qt.icons import Icons
from src.qt.runtime import dispatch as runtime_dispatch
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    ClickFrame,
    IconLabel,
    IconOnlyButton,
    MutedLabel,
    custom_label,
    hbox,
    vbox,
    wrap_label_slot,
)
from src.services import logger as logger_service
from src.sections.ai_legal import pipeline
from src.sections.ai_legal.data import (
    SECTION_ICON,
    chat_quick_actions,
)
from src.sections.ai_legal.refs import REFS
from src.sections.ai_legal.state import STATE
from src.sections.ai_legal.strings import s
from src.theme import Theme


_USER_BUBBLE_MAX = 420
_ASSISTANT_BUBBLE_MAX = 560


def _avatar_user(theme: Theme) -> QFrame:
    avatar = QFrame()
    avatar.setFixedSize(28, 28)
    avatar.setStyleSheet(f"background-color: {theme.primary_soft}; border-radius: 14px;")
    al = hbox(spacing=0, margins=(0, 0, 0, 0))
    al.setAlignment(Qt.AlignmentFlag.AlignCenter)
    avatar.setLayout(al)
    al.addWidget(IconLabel(Icons.PERSON, color="#FFFFFF", size=16),
                 alignment=Qt.AlignmentFlag.AlignCenter)
    return avatar


def _avatar_assistant(theme: Theme) -> QFrame:
    avatar = QFrame()
    avatar.setFixedSize(36, 36)
    avatar.setStyleSheet(f"background-color: {theme.primary}; border-radius: 10px;")
    al = hbox(spacing=0, margins=(0, 0, 0, 0))
    al.setAlignment(Qt.AlignmentFlag.AlignCenter)
    avatar.setLayout(al)
    al.addWidget(IconLabel(SECTION_ICON, color="#FFFFFF", size=18),
                 alignment=Qt.AlignmentFlag.AlignCenter)
    return avatar


def _attachment_chip(theme: Theme, lang: str, name: str) -> QFrame:
    txt = s(lang)
    chip = QFrame()
    chip.setStyleSheet("background-color: rgba(255, 255, 255, 0.18); border-radius: 6px;")
    layout = hbox(spacing=6, margins=(8, 4, 8, 4))
    chip.setLayout(layout)
    layout.addWidget(IconLabel(Icons.ATTACH_FILE, color="rgba(255, 255, 255, 0.85)", size=14))
    layout.addWidget(custom_label(
        f"{txt['chat_user_attachment_label']} {name}",
        color="rgba(255, 255, 255, 0.85)",
        size=12,
    ))
    return chip


def _user_bubble(theme: Theme, lang: str, msg) -> QWidget:
    bubble = QFrame()
    bubble.setStyleSheet(f"background-color: {theme.user_bubble}; border-radius: 14px;")
    bubble.setMaximumWidth(_USER_BUBBLE_MAX)
    bubble.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
    bubble_layout = vbox(spacing=8, margins=(14, 10, 14, 10))
    bubble.setLayout(bubble_layout)
    bubble_layout.addWidget(custom_label(
        msg.text,
        color=theme.user_bubble_text,
        size=14,
        selectable=True,
    ))
    if msg.attachment_name:
        bubble_layout.addWidget(_attachment_chip(theme, lang, msg.attachment_name))

    bubble_row = QFrame()
    bubble_row.setStyleSheet("background: transparent;")
    bl = hbox(spacing=10, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignBottom)
    bubble_row.setLayout(bl)
    bl.addStretch(1)
    bl.addWidget(bubble)
    bl.addWidget(_avatar_user(theme))

    inner = QFrame()
    inner.setStyleSheet("background: transparent;")
    inner_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    inner.setLayout(inner_layout)
    time_holder = QFrame()
    time_holder.setStyleSheet("background: transparent;")
    tl = hbox(spacing=0, margins=(0, 0, 44, 0))
    tl.setAlignment(Qt.AlignmentFlag.AlignRight)
    time_holder.setLayout(tl)
    tl.addStretch(1)
    tl.addWidget(MutedLabel(msg.time, theme=theme, size=11))
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


def _assistant_bubble(theme: Theme, lang: str, msg) -> QWidget:
    bubble = QFrame()
    bubble.setStyleSheet(f"background-color: {theme.assistant_bubble}; border-radius: 14px;")
    bubble.setMaximumWidth(_ASSISTANT_BUBBLE_MAX)
    bubble.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
    bubble_layout = vbox(spacing=8, margins=(16, 14, 16, 14))
    bubble.setLayout(bubble_layout)

    text = BodyLabel(msg.text, theme=theme, size=14, selectable=True)
    text.setTextFormat(Qt.TextFormat.MarkdownText)
    wrap_label_slot(text)
    bubble_layout.addWidget(text)

    body = QFrame()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)
    body_layout.addWidget(MutedLabel(msg.time, theme=theme, size=11))
    body_layout.addWidget(bubble)

    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    wl = QHBoxLayout(wrapper)
    wl.setContentsMargins(0, 0, 0, 0)
    wl.setSpacing(12)
    wl.setAlignment(Qt.AlignmentFlag.AlignTop)
    wl.addWidget(_avatar_assistant(theme))
    wl.addWidget(body, 1)
    return wrapper


def _action_chip(
    theme: Theme,
    *,
    icon: str,
    label: str,
    on_click: Callable[[], None],
) -> ClickFrame:
    """Compact pill chip used in the row above the input.

    The chip's text label intentionally turns off word-wrap (``setWordWrap(False)``):
    these are short single-word verbs (``Summarise`` / ``Find risks`` / …)
    that must stay on a single line for the chip-button affordance to
    work. The chip itself has no max-width so it sits at its natural
    content width and never clips.
    """
    chip = ClickFrame()
    chip.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 999px;
        }}
        ClickFrame:hover {{
            background-color: {theme.surface_2};
            border-color: {rgba(theme.primary, 0.45)};
        }}
        """
    )
    chip.setCursor(Qt.CursorShape.PointingHandCursor)
    chip.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
    layout = hbox(spacing=6, margins=(12, 6, 14, 6))
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    chip.setLayout(layout)
    layout.addWidget(IconLabel(icon, color=theme.primary, size=14))
    text = custom_label(label, color=theme.text, size=12, weight=QFont.Weight.DemiBold)
    text.setWordWrap(False)
    layout.addWidget(text)
    chip.clicked.connect(on_click)
    return chip


def _quick_actions_row(
    theme: Theme,
    lang: str,
    on_quick_action: Callable[[str], None],
) -> QFrame:
    """Single horizontal row of quick-action chips centred above the input.

    Always visible, regardless of whether the chat is empty or already
    has messages — clicking a chip immediately appends a user-style
    bubble with the chip's label and asks the AI provider with the
    matching detailed prompt.
    """
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    holder.setLayout(layout)
    layout.addStretch(1)
    for action in chat_quick_actions(lang):
        layout.addWidget(_action_chip(
            theme,
            icon=action["icon"],
            label=action["label"],
            on_click=lambda k=action["key"]: on_quick_action(k),
        ))
    layout.addStretch(1)
    return holder


def _interactive_input(
    theme: Theme,
    lang: str,
    on_send: Callable[[str], None],
) -> QFrame:
    txt = s(lang)
    holder = QFrame()
    holder.setObjectName("LegalChatInputBar")
    holder.setStyleSheet(
        f"""
        QFrame#LegalChatInputBar {{
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
    field.setPlaceholderText(txt["chat_input_placeholder"])
    field.setStyleSheet(
        f"""
        QLineEdit {{
            background: transparent;
            color: {theme.text};
            border: none;
            padding: 12px 8px;
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
    send_btn = IconOnlyButton(
        Icons.SEND,
        color="#FFFFFF",
        size=18,
        bg=theme.primary,
        bg_hover=theme.primary_hover,
        radius=10,
    )
    send_btn.setFixedSize(40, 40)
    send_btn.clicked.connect(_send)
    layout.addWidget(send_btn)
    return holder


def build_chat_tab(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    def _rerender() -> None:
        if REFS.rerender_tab_body is not None:
            REFS.rerender_tab_body()

    def _run_in_thread(target: Callable[[], None], name: str) -> None:
        def _wrapper() -> None:
            try:
                target()
            except Exception as exc:
                logger_service.log_exception(
                    "ai_legal.tab_chat", "worker_failed", exc, action=name,
                )
        threading.Thread(target=_wrapper, daemon=True, name=name).start()

    def _on_send(value: str) -> None:
        logger_service.log_event(
            "INFO", "ai_legal.tab_chat", "send_clicked",
            chars=len(value), has_doc=bool(STATE.attached_doc_text),
        )

        def _worker() -> None:
            pipeline.send_chat_message(user_text=value, output_lang=lang)
            runtime_dispatch(_rerender)

        _run_in_thread(_worker, "ai_legal_send_chat")
        _rerender()

    def _on_quick_action(key: str) -> None:
        logger_service.log_event(
            "INFO", "ai_legal.tab_chat", "quick_action_clicked",
            action=key, has_doc=bool(STATE.attached_doc_text),
        )

        def _worker() -> None:
            pipeline.run_quick_action(action_key=key, output_lang=lang)
            runtime_dispatch(_rerender)

        _run_in_thread(_worker, f"ai_legal_quick_action_{key}")
        _rerender()

    if STATE.chat_messages:
        messages_holder = QWidget()
        messages_holder.setStyleSheet(f"background-color: {theme.bg};")
        msgs_layout = vbox(spacing=22, margins=(24, 20, 24, 12))
        messages_holder.setLayout(msgs_layout)
        for msg in STATE.chat_messages:
            if msg.role == "user":
                msgs_layout.addWidget(_user_bubble(theme, lang, msg))
            else:
                msgs_layout.addWidget(_assistant_bubble(theme, lang, msg))
        msgs_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
        scroll.setWidget(messages_holder)
        layout.addWidget(scroll, 1)
    else:
        spacer = QWidget()
        spacer.setStyleSheet(f"background-color: {theme.bg};")
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(spacer, 1)

    bottom = QWidget()
    bottom.setStyleSheet(f"background-color: {theme.bg};")
    bottom_layout = vbox(spacing=10, margins=(24, 6, 24, 16))
    bottom.setLayout(bottom_layout)

    if not STATE.chat_messages:
        hint = MutedLabel(txt["chat_empty_prompt"], theme=theme, size=12)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_layout.addWidget(hint)

    bottom_layout.addWidget(_quick_actions_row(theme, lang, _on_quick_action))
    bottom_layout.addWidget(_interactive_input(theme, lang, _on_send))

    layout.addWidget(bottom)
    return container
