"""Reusable "How to use this assistant" modal.

Sections build a list of :class:`HowToSection` (an icon, a title, a body)
and pass it to :func:`open_how_to`. The dialog is rendered through Qt's
:class:`QDialog` (modal blocking, ESC-to-close), parented to the running
:class:`AIHubApp` main window so it always appears centred over the app.

Each section keeps its own per-language copy under ``how_to.py`` and the
``build_view`` header ``?`` button hooks straight into this helper.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.qt.dialog import BaseDialog
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    IconLabel,
    PrimaryButton,
    TitleLabel,
    hbox,
    vbox,
)
from src.qt.runtime import get_main_window
from src.theme import Theme


@dataclass(frozen=True)
class HowToSection:
    icon: str
    title: str
    body: str


def _section_block(theme: Theme, *, icon: str, title: str, body: str) -> QFrame:
    block = QFrame()
    block.setStyleSheet("background: transparent;")
    layout = hbox(spacing=12, margins=(0, 0, 0, 0))
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    block.setLayout(layout)

    icon_box = QFrame()
    icon_box.setFixedSize(34, 34)
    icon_box.setStyleSheet(
        f"background-color: {rgba(theme.primary, 0.14)}; border-radius: 10px;"
    )
    icon_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setLayout(icon_layout)
    icon_layout.addWidget(IconLabel(icon, color=theme.primary, size=18),
                          alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(icon_box)

    text_holder = QFrame()
    text_holder.setStyleSheet("background: transparent;")
    text_holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    text_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    text_holder.setLayout(text_layout)
    text_layout.addWidget(TitleLabel(title, theme=theme, size=14))
    body_label = BodyLabel(body, theme=theme, size=12, selectable=True)
    body_label.setStyleSheet(f"color: {theme.text_muted}; background: transparent;")
    text_layout.addWidget(body_label)
    layout.addWidget(text_holder, 1)

    return block


def how_to_dialog(
    theme: Theme,
    *,
    title: str,
    sections: Sequence[HowToSection],
    close_label: str,
    parent: QWidget | None = None,
) -> BaseDialog:
    parent_w = parent or get_main_window()
    dlg = BaseDialog(parent=parent_w, theme=theme, title=title, width=620)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
    scroll.setMinimumHeight(380)

    body = QFrame()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=18, margins=(4, 4, 4, 4))
    body.setLayout(body_layout)
    for section in sections:
        body_layout.addWidget(_section_block(theme, icon=section.icon, title=section.title, body=section.body))
    body_layout.addStretch(1)
    scroll.setWidget(body)

    dlg.body_layout.addWidget(scroll)

    close_btn = PrimaryButton(close_label, theme=theme)
    dlg.add_action(close_btn, role="accept")

    return dlg


def open_how_to(
    page,  # legacy positional arg kept for API compatibility (unused)
    theme: Theme,
    *,
    title: str,
    sections: Sequence[HowToSection],
    close_label: str,
) -> None:
    """Open the modal "How to use this assistant" dialog.

    The first positional argument used to be the Flet ``ft.Page`` we
    needed to host the dialog. It is now ignored - we look the active
    main window up via :func:`src.qt.runtime.get_main_window`. The
    parameter is kept so existing callers (every section's
    ``how_to.py``) keep compiling without edits.
    """
    parent = get_main_window()
    dlg = how_to_dialog(
        theme,
        title=title,
        sections=sections,
        close_label=close_label,
        parent=parent,
    )
    dlg.exec()
