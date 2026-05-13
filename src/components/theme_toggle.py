"""Theme toggle row in the sidebar footer (icon + label + switch)."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QSizePolicy

from src.components.language_toggle import _PillSwitch  # reuse the same pill widget
from src.i18n import t
from src.qt.icons import Icons
from src.qt.widgets import BodyLabel, IconLabel, hbox
from src.theme import Theme


def theme_toggle(
    theme: Theme,
    lang: str,
    *,
    theme_mode: str,
    on_toggle: Callable[[], None],
) -> QFrame:
    frame = QFrame()
    frame.setStyleSheet("background: transparent;")
    frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

    layout = hbox(spacing=10, margins=(20, 6, 20, 6))
    frame.setLayout(layout)

    icon_name = Icons.AUTO_AWESOME if theme_mode == "light" else Icons.AUTO_AWESOME
    icon = IconLabel(icon_name, color=theme.text_muted, size=18)
    layout.addWidget(icon)

    label_key = "dark_mode" if theme_mode == "light" else "dark_mode"
    label = BodyLabel(t(label_key, lang), theme=theme, size=13)
    layout.addWidget(label, 1)

    switch = _PillSwitch(theme, active=theme_mode == "dark", on_toggle=on_toggle)
    layout.addWidget(switch)

    return frame
