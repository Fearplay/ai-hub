"""One chat bubble (user or assistant).

Sections drive this with the data they own. Custom rich content can be
injected via ``extra`` (any QWidget appended at the end of the bubble).
"""

from __future__ import annotations

from typing import Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.components.document_chip import file_badge
from src.i18n import t
from src.qt.icons import Icons
from src.qt.widgets import (
    AccentLabel,
    BodyLabel,
    ClickFrame,
    IconLabel,
    MutedLabel,
    custom_label,
    hbox,
    vbox,
)
from src.theme import Theme


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
    layout.addWidget(BodyLabel(label, theme=theme, size=11))
    return chip


def _attachment_card(theme: Theme, lang: str, attachment: dict) -> QFrame:
    card = QFrame()
    card.setObjectName("ChatAttachmentCard")
    card.setStyleSheet(
        f"""
        QFrame#ChatAttachmentCard {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 10px;
        }}
        """
    )
    layout = hbox(spacing=12, margins=(10, 10, 10, 10))
    card.setLayout(layout)
    layout.addWidget(file_badge(theme, attachment["type"], size=40))

    text_holder = QFrame()
    text_holder.setStyleSheet("background: transparent;")
    text_holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    text_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    text_holder.setLayout(text_layout)
    text_layout.addWidget(BodyLabel(attachment["name"], theme=theme, size=12))
    text_layout.addWidget(
        MutedLabel(f"{attachment['type']} \u2022 {attachment['size']}", theme=theme, size=11)
    )
    layout.addWidget(text_holder, 1)

    download_chip = ClickFrame()
    download_chip.setStyleSheet(
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
    chip_layout = hbox(spacing=6, margins=(10, 6, 10, 6))
    download_chip.setLayout(chip_layout)
    chip_layout.addWidget(BodyLabel(t("download", lang), theme=theme, size=11))
    chip_layout.addWidget(IconLabel(Icons.FILE_DOWNLOAD_OUTLINED, color=theme.text, size=14))
    layout.addWidget(download_chip)
    return card


def _bullet_row(theme: Theme, text: str, *, marker: str = "\u2022") -> QFrame:
    row = QFrame()
    row.setStyleSheet("background: transparent;")
    layout = hbox(spacing=6, margins=(0, 0, 0, 0))
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    row.setLayout(layout)

    bullet = QLabel(marker)
    bullet.setFixedWidth(18)
    bullet.setAlignment(Qt.AlignmentFlag.AlignCenter)
    color = theme.primary if marker != "\u2022" else theme.text
    bullet.setStyleSheet(f"color: {color}; background: transparent; font-weight: 700;")
    layout.addWidget(bullet)

    text_label = BodyLabel(text, theme=theme, size=13, selectable=True)
    text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    layout.addWidget(text_label, 1)
    return row


def _avatar(*, color: str, icon: str, size: int = 36) -> QFrame:
    box = QFrame()
    box.setFixedSize(size, size)
    radius = size // 2
    box.setStyleSheet(
        f"background-color: {color}; border-radius: {radius}px;"
    )
    layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    box.setLayout(layout)
    layout.addWidget(IconLabel(icon, color="#FFFFFF", size=int(size * 0.5)),
                     alignment=Qt.AlignmentFlag.AlignCenter)
    return box


def _user_message(theme: Theme, *, time: str, text: str) -> QWidget:
    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    outer = QHBoxLayout(wrapper)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.addStretch(1)

    col = QVBoxLayout()
    col.setSpacing(4)

    time_label = MutedLabel(time, theme=theme, size=11)
    time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
    col.addWidget(time_label, alignment=Qt.AlignmentFlag.AlignRight)

    bubble_row = QHBoxLayout()
    bubble_row.setSpacing(10)

    bubble = QFrame()
    bubble.setObjectName("ChatUserBubble")
    bubble.setStyleSheet(
        f"""
        QFrame#ChatUserBubble {{
            background-color: {theme.user_bubble};
            border-radius: 14px;
        }}
        """
    )
    bubble_layout = vbox(spacing=0, margins=(14, 10, 14, 10))
    bubble.setLayout(bubble_layout)
    body = custom_label(text or "", color=theme.user_bubble_text, size=13, selectable=True)
    bubble_layout.addWidget(body)
    bubble_row.addWidget(bubble)
    bubble_row.addWidget(_avatar(color=theme.primary_soft, icon=Icons.PERSON, size=28))
    col.addLayout(bubble_row)
    outer.addLayout(col)
    return wrapper


def _assistant_message(
    theme: Theme,
    lang: str,
    *,
    avatar_icon: str,
    time: str,
    text: Optional[str] = None,
    bullets: Optional[Sequence[str]] = None,
    bullet_marker: str = "\u2022",
    sections: Optional[Sequence[dict]] = None,
    footer: Optional[str] = None,
    actions: Optional[Sequence[dict]] = None,
    attachment: Optional[dict] = None,
    extra: Optional[QWidget] = None,
) -> QWidget:
    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    layout = QHBoxLayout(wrapper)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    layout.addWidget(_avatar(color=theme.primary, icon=avatar_icon, size=36))

    body_holder = QWidget()
    body_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    body_holder.setLayout(body_layout)

    body_layout.addWidget(MutedLabel(time, theme=theme, size=11))

    bubble = QFrame()
    bubble.setObjectName("ChatAssistantBubble")
    bubble.setStyleSheet(
        f"""
        QFrame#ChatAssistantBubble {{
            background-color: {theme.assistant_bubble};
            border-radius: 14px;
        }}
        """
    )
    bubble_layout = vbox(spacing=12, margins=(14, 14, 14, 14))
    bubble.setLayout(bubble_layout)

    if text:
        bubble_layout.addWidget(BodyLabel(text, theme=theme, size=13, selectable=True))

    if sections:
        for section in sections:
            heading_row = hbox(spacing=6, margins=(0, 0, 0, 0))
            heading_row.addWidget(IconLabel(section.get("icon", Icons.AUTO_AWESOME),
                                            color=theme.primary, size=14))
            heading_row.addWidget(AccentLabel(section["title"], theme=theme, size=12))
            block = vbox(spacing=8, margins=(0, 0, 0, 0))
            block.addLayout(heading_row)
            if section.get("text"):
                block.addWidget(BodyLabel(section["text"], theme=theme, size=13, selectable=True))
            for b in section.get("bullets") or []:
                block.addWidget(_bullet_row(theme, b, marker=section.get("marker", "\u2022")))
            holder = QFrame()
            holder.setStyleSheet("background: transparent;")
            holder.setLayout(block)
            bubble_layout.addWidget(holder)

    if bullets:
        for b in bullets:
            bubble_layout.addWidget(_bullet_row(theme, b, marker=bullet_marker))

    if footer:
        bubble_layout.addWidget(BodyLabel(footer, theme=theme, size=13, selectable=True))

    if extra is not None:
        bubble_layout.addWidget(extra)

    if attachment:
        bubble_layout.addWidget(_attachment_card(theme, lang, attachment))

    if actions:
        actions_holder = QFrame()
        actions_holder.setStyleSheet("background: transparent;")
        actions_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
        actions_holder.setLayout(actions_layout)
        for a in actions:
            actions_layout.addWidget(_action_chip(theme, a["icon"], a["label"]))
        actions_layout.addStretch(1)
        bubble_layout.addWidget(actions_holder)

    body_layout.addWidget(bubble)
    layout.addWidget(body_holder, 1)
    return wrapper


def chat_message(
    theme: Theme,
    lang: str,
    *,
    avatar_icon: str,
    role: str,
    time: str,
    text: Optional[str] = None,
    bullets: Optional[Sequence[str]] = None,
    bullet_marker: str = "\u2022",
    sections: Optional[Sequence[dict]] = None,
    footer: Optional[str] = None,
    actions: Optional[Sequence[dict]] = None,
    attachment: Optional[dict] = None,
    extra: Optional[QWidget] = None,
) -> QWidget:
    if role == "user":
        return _user_message(theme, time=time, text=text or "")
    return _assistant_message(
        theme,
        lang,
        avatar_icon=avatar_icon,
        time=time,
        text=text,
        bullets=bullets,
        bullet_marker=bullet_marker,
        sections=sections,
        footer=footer,
        actions=actions,
        attachment=attachment,
        extra=extra,
    )
