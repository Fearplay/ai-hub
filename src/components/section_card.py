"""Reusable section card (icon + title + body) for the right context panel."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QSizePolicy, QWidget

from src.qt.theme import rgba
from src.qt.widgets import (
    Card,
    IconLabel,
    MutedLabel,
    TitleLabel,
    hbox,
    vbox,
)
from src.theme import Theme


def section_card(
    theme: Theme,
    *,
    icon: str,
    title: str,
    description: Optional[str] = None,
    body: Optional[QWidget] = None,
) -> QFrame:
    card = Card(
        bg=theme.surface,
        border_color=theme.border,
        radius=14,
        padding=(16, 16, 16, 16),
    )
    layout = card.content_layout
    layout.setSpacing(12)

    head_row = hbox(spacing=10, margins=(0, 0, 0, 0))

    icon_box = QFrame()
    icon_box.setFixedSize(30, 30)
    icon_box.setStyleSheet(
        f"background-color: {rgba(theme.primary, 0.14)}; border-radius: 8px;"
    )
    icon_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setLayout(icon_layout)
    icon_layout.addWidget(
        IconLabel(icon, color=theme.primary, size=16),
        alignment=Qt.AlignmentFlag.AlignCenter,
    )
    head_row.addWidget(icon_box)

    text_holder = QFrame()
    text_holder.setStyleSheet("background: transparent;")
    text_holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    text_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    text_holder.setLayout(text_layout)
    text_layout.addWidget(TitleLabel(title, theme=theme, size=14))
    if description:
        text_layout.addWidget(MutedLabel(description, theme=theme, size=11))
    head_row.addWidget(text_holder, 1)

    layout.addLayout(head_row)

    if body is not None:
        layout.addWidget(body)

    return card
