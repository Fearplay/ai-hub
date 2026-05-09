"""Disclaimer pill shown in the AI Legal header (top-right corner).

The shared ``header`` component only knows about the icon, title,
subtitle and the menu / help buttons. The legal screenshot has an extra
"Important notice - this is not legal advice" panel pinned to the right
of the header. We render that as a small standalone control and stack
it next to the generic header in :mod:`src.sections.ai_legal.view` so we
don't have to widen the shared header API for a single section.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QSizePolicy

from src.qt.icons import Icons
from src.qt.theme import rgba
from src.qt.widgets import BodyLabel, IconLabel, MutedLabel, hbox, vbox
from src.sections.ai_legal.strings import s
from src.theme import Theme


def warning_pill(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    accent = "#F59E0B"

    pill = QFrame()
    pill.setFixedWidth(290)
    pill.setStyleSheet(
        f"""
        QFrame {{
            background-color: {rgba(accent, 0.08)};
            border: 1px solid {rgba(accent, 0.25)};
            border-radius: 10px;
        }}
        """
    )
    layout = hbox(spacing=10, margins=(12, 8, 12, 8))
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    pill.setLayout(layout)

    icon_box = QFrame()
    icon_box.setFixedSize(32, 32)
    icon_box.setStyleSheet(
        f"background-color: {rgba(accent, 0.15)}; border: none; border-radius: 8px;"
    )
    box_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    box_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setLayout(box_layout)
    box_layout.addWidget(IconLabel(Icons.SHIELD_OUTLINED, color=accent, size=18),
                         alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(icon_box)

    info = QFrame()
    info.setStyleSheet("background: transparent; border: none;")
    info.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    info_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    info.setLayout(info_layout)
    info_layout.addWidget(BodyLabel(txt["warning_pill_title"], theme=theme, size=12, weight=QFont.Weight.Bold))
    info_layout.addWidget(MutedLabel(txt["warning_pill_text"], theme=theme, size=11))
    layout.addWidget(info, 1)

    return pill
