"""Right-hand panel scaffolding shared by every section view.

The actual cards are owned by each section in ``sections/<key>/context.py``.
This module gives you:

* :func:`context_panel_shell` - the outer container + scrollable column
  every section drops its cards into.
* :func:`empty_context_panel`  - default for sections without a custom panel.
* :func:`quick_action_row`     - reusable row used by quick-action cards.
* :func:`history_row`          - reusable row used by history cards.
* :func:`add_document_button`  - reusable purple "add document" button.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.i18n import t
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    ClickFrame,
    IconLabel,
    MutedLabel,
    hbox,
    vbox,
    wrap_label_slot,
)
from src.theme import Theme


def context_panel_shell(theme: Theme, *cards: QWidget) -> QFrame:
    container = QFrame()
    container.setObjectName("ContextPanel")
    container.setFixedWidth(336)
    container.setStyleSheet(
        f"""
        QFrame#ContextPanel {{
            background-color: {theme.bg};
            border-left: 1px solid {theme.border};
        }}
        """
    )

    outer = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(outer)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet("QScrollArea { background: transparent; }")
    outer.addWidget(scroll)

    inner = QFrame()
    inner.setStyleSheet("background: transparent;")
    inner_layout = vbox(spacing=16, margins=(16, 16, 16, 16))
    inner.setLayout(inner_layout)
    for card in cards:
        inner_layout.addWidget(card)
    inner_layout.addStretch(1)
    scroll.setWidget(inner)

    return container


def empty_context_panel(theme: Theme) -> QFrame:
    container = QFrame()
    container.setObjectName("EmptyContextPanel")
    container.setFixedWidth(336)
    container.setStyleSheet(
        f"""
        QFrame#EmptyContextPanel {{
            background-color: {theme.bg};
            border-left: 1px solid {theme.border};
        }}
        """
    )
    return container


def add_document_button(theme: Theme, lang: str) -> ClickFrame:
    btn = ClickFrame()
    btn.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {rgba(theme.primary, 0.10)};
            border: 1px solid {rgba(theme.primary, 0.20)};
            border-radius: 10px;
        }}
        ClickFrame:hover {{
            background-color: {rgba(theme.primary, 0.16)};
        }}
        """
    )
    layout = hbox(spacing=6, margins=(12, 12, 12, 12))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    btn.setLayout(layout)

    layout.addWidget(IconLabel("add", color=theme.primary, size=16))
    label = BodyLabel(t("add_document", lang), theme=theme, size=12)
    label.setStyleSheet(f"color: {theme.primary}; background: transparent;")
    layout.addWidget(label)

    return btn


def quick_action_row(theme: Theme, icon: str, label: str) -> ClickFrame:
    row = ClickFrame()
    row.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: transparent;
            border-radius: 8px;
        }}
        ClickFrame:hover {{
            background-color: {theme.surface_2};
        }}
        """
    )
    layout = hbox(spacing=10, margins=(8, 8, 8, 8))
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    row.setLayout(layout)
    layout.addWidget(IconLabel(icon, color=theme.text_muted, size=16))
    text = BodyLabel(label, theme=theme, size=12)
    wrap_label_slot(text)
    layout.addWidget(text, 1)
    layout.addWidget(IconLabel("chevron_right", color=theme.text_muted, size=16))
    return row


def history_row(
    theme: Theme,
    title: str,
    time: str,
    *,
    pinned: bool = False,
) -> ClickFrame:
    row = ClickFrame()
    row.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: transparent;
            border-radius: 6px;
        }}
        ClickFrame:hover {{
            background-color: {theme.surface_2};
        }}
        """
    )
    layout = vbox(spacing=2, margins=(4, 6, 4, 6))
    row.setLayout(layout)

    title_row = hbox(spacing=6, margins=(0, 0, 0, 0))
    title_label = BodyLabel(title, theme=theme, size=12)
    title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    title_row.addWidget(title_label, 1)
    if pinned:
        title_row.addWidget(IconLabel("push_pin", color=theme.primary, size=12))
    layout.addLayout(title_row)
    layout.addWidget(MutedLabel(time, theme=theme, size=11))
    return row


def quick_actions_column(theme: Theme, actions: Sequence[dict]) -> QFrame:
    container = QFrame()
    container.setStyleSheet("background: transparent;")
    layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    container.setLayout(layout)
    for a in actions:
        layout.addWidget(quick_action_row(theme, a["icon"], a["label"]))
    return container


def history_column(theme: Theme, items: Iterable[dict]) -> QFrame:
    container = QFrame()
    container.setStyleSheet("background: transparent;")
    layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    container.setLayout(layout)
    for h in items:
        layout.addWidget(
            history_row(theme, h["title"], h["time"], pinned=h.get("pinned", False))
        )
    return container
