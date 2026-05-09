"""Language toggle row in the sidebar footer (icon + label + switch)."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QSizePolicy

from src.i18n import t
from src.qt.icons import Icons
from src.qt.theme import rgba
from src.qt.widgets import BodyLabel, IconLabel, hbox
from src.theme import Theme


class _PillSwitch(QFrame):
    """Small rounded pill switch (active: primary fill / inactive: border).

    Behaves like the slider toggle in the screenshots - a 36x20 capsule
    with a 16x16 dot that sits on the right when active.
    """

    def __init__(self, theme: Theme, *, active: bool, on_toggle: Callable[[], None]) -> None:
        super().__init__()
        self._theme = theme
        self._active = active
        self._on_toggle = on_toggle
        self.setFixedSize(36, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dot = QFrame(self)
        self._dot.setFixedSize(14, 14)
        self._render()

    def _render(self) -> None:
        bg = self._theme.primary if self._active else rgba(self._theme.text_muted, 0.30)
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {bg};
                border-radius: 10px;
            }}
            """
        )
        self._dot.setStyleSheet(
            "background-color: #FFFFFF; border-radius: 7px;"
        )
        x = 19 if self._active else 3
        self._dot.move(x, 3)

    def set_active(self, active: bool) -> None:
        if active == self._active:
            return
        self._active = active
        self._render()

    def mouseReleaseEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_toggle()
        super().mouseReleaseEvent(event)


def language_toggle(theme: Theme, lang: str, *, on_toggle: Callable[[], None]) -> QFrame:
    frame = QFrame()
    frame.setStyleSheet("background: transparent;")
    frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

    layout = hbox(spacing=10, margins=(20, 6, 20, 6))
    frame.setLayout(layout)

    icon = IconLabel(Icons.TRANSLATE, color=theme.text_muted, size=18)
    layout.addWidget(icon)

    label = BodyLabel(t("czech", lang), theme=theme, size=13)
    layout.addWidget(label, 1)

    switch = _PillSwitch(theme, active=lang == "cs", on_toggle=on_toggle)
    layout.addWidget(switch)

    return frame
