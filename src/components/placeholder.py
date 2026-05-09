"""Centred "this section is being prepared" panel.

Used by sections that have not been wired to a real backend yet
(Dashboard, AI Business, AI Documents, …). Keeps the section folder
minimal and the visual style consistent.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy, QWidget

from src.i18n import t
from src.qt.widgets import IconLabel, MutedLabel, TitleLabel, vbox
from src.qt.icons import Icons
from src.theme import Theme


def placeholder_view(theme: Theme, lang: str, *, title: str, subtitle: Optional[str] = None) -> QWidget:
    container = QWidget()
    container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    container.setStyleSheet(f"background-color: {theme.bg};")

    layout = vbox(spacing=14, margins=(40, 60, 40, 60))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    container.setLayout(layout)

    icon = IconLabel(Icons.HOURGLASS_EMPTY_ROUNDED, color=theme.text_muted, size=48)
    layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignHCenter)

    title_label = TitleLabel(title, theme=theme, size=20)
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)

    body = MutedLabel(subtitle or t("coming_soon", lang), theme=theme, size=13)
    body.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(body, alignment=Qt.AlignmentFlag.AlignHCenter)

    return container
