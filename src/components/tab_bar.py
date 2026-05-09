"""Generic tab bar under the header.

Renders a horizontal row of tab labels with a 2 px underline beneath the
active one. Sections that need real navigation pass ``on_change`` with
the clicked index; sections without it (decorative bars) just see the
visual underline. Long bars scroll horizontally inside a ``QScrollArea``.
"""

from __future__ import annotations

from typing import Callable, Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QSizePolicy,
)

from src.qt.widgets import ClickFrame, hbox, vbox
from src.theme import Theme


def _tab(
    theme: Theme,
    label: str,
    *,
    active: bool,
    on_click: Optional[Callable[[], None]] = None,
) -> ClickFrame:
    container = ClickFrame()
    container.setStyleSheet("background: transparent;")
    container.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
    if on_click is None:
        container.set_clickable(False)

    layout = vbox(spacing=0, margins=(12, 8, 12, 2))
    container.setLayout(layout)

    text_label = QLabel(label)
    font = QFont()
    font.setPixelSize(13)
    font.setWeight(QFont.Weight.DemiBold if active else QFont.Weight.Normal)
    text_label.setFont(font)
    text_label.setStyleSheet(
        f"color: {theme.text if active else theme.text_muted}; background: transparent;"
    )
    text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(text_label)

    underline = QFrame()
    underline.setFixedHeight(2)
    underline.setStyleSheet(
        f"background-color: {theme.primary if active else 'transparent'};"
        " border-radius: 1px;"
    )
    layout.addWidget(underline)

    if on_click is not None:
        container.clicked.connect(on_click)

    return container


def tab_bar(
    theme: Theme,
    *,
    tabs: Sequence[str],
    active_index: int = 0,
    on_change: Optional[Callable[[int], None]] = None,
) -> QFrame:
    bar = QFrame()
    bar.setStyleSheet(
        f"""
        QFrame {{
            background-color: {theme.bg};
            border-bottom: 1px solid {theme.border};
        }}
        """
    )
    bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

    outer = hbox(spacing=0, margins=(0, 0, 0, 0))
    bar.setLayout(outer)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
    outer.addWidget(scroll)

    inner = QFrame()
    inner.setStyleSheet("background: transparent;")
    inner_layout = hbox(spacing=24, margins=(24, 4, 24, 4))
    inner.setLayout(inner_layout)

    for i, label in enumerate(tabs):
        if on_change is None:
            handler: Optional[Callable[[], None]] = None
        else:
            handler = lambda idx=i: on_change(idx)  # noqa: E731
        inner_layout.addWidget(_tab(theme, label, active=i == active_index, on_click=handler))

    inner_layout.addStretch(1)
    scroll.setWidget(inner)

    return bar
