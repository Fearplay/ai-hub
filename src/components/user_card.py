"""User card shown in the sidebar footer (avatar + name + email)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy

from src.data.user import USER
from src.qt.icons import Icons
from src.qt.widgets import IconLabel, hbox, vbox
from src.theme import Theme


def user_card(theme: Theme) -> QFrame:
    frame = QFrame()
    frame.setObjectName("UserCard")
    frame.setStyleSheet(
        f"""
        QFrame#UserCard {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 10px;
        }}
        """
    )
    layout = hbox(spacing=10, margins=(10, 8, 10, 8))
    frame.setLayout(layout)

    avatar = QFrame()
    avatar.setFixedSize(36, 36)
    avatar.setStyleSheet(
        f"background-color: {theme.primary}; border-radius: 18px;"
    )
    avatar_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    avatar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    avatar.setLayout(avatar_layout)
    avatar_icon = IconLabel(Icons.PERSON, color="#FFFFFF", size=20)
    avatar_layout.addWidget(avatar_icon, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(avatar)

    text_col = vbox(spacing=2, margins=(0, 0, 0, 0))
    name_label = QLabel(USER.get("name", ""))
    name_font = QFont()
    name_font.setPixelSize(13)
    name_font.setWeight(QFont.Weight.DemiBold)
    name_label.setFont(name_font)
    name_label.setStyleSheet(f"color: {theme.text}; background: transparent;")
    text_col.addWidget(name_label)

    email_label = QLabel(USER.get("email", ""))
    email_font = QFont()
    email_font.setPixelSize(11)
    email_label.setFont(email_font)
    email_label.setStyleSheet(f"color: {theme.text_muted}; background: transparent;")
    text_col.addWidget(email_label)

    text_holder = QFrame()
    text_holder.setLayout(text_col)
    text_holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    text_holder.setStyleSheet("background: transparent;")
    layout.addWidget(text_holder, 1)

    chevron = IconLabel(Icons.KEYBOARD_ARROW_DOWN, color=theme.text_muted, size=18)
    layout.addWidget(chevron)

    return frame
