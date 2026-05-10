"""One row in the left sidebar.

Two flavors:

* :func:`nav_item` - simple builder that just returns a ``QWidget``. Use
  this if you only need a one-shot row that you do not plan to mutate.
* :func:`nav_item_handle` - returns the row plus references to the icon
  / text labels so callers can flip the active state without rebuilding
  (used by the sidebar to keep section clicks snappy).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from src.qt.theme import rgba
from src.qt.widgets import ClickFrame, IconLabel, Pill, hbox
from src.theme import Theme


def _badge_widget(theme: Theme, text: str) -> QWidget:
    """Render a sidebar nav badge.

    Short labels (<= 2 chars, e.g. notification counts) become a tight
    20x20 circle so the row stays balanced. Longer text falls back to
    the regular pill so we don't squeeze, e.g., "NEW" into a circle.
    """
    text = str(text)
    if len(text) <= 2:
        chip = QFrame()
        chip.setObjectName("NavBadge")
        chip.setFixedSize(20, 20)
        chip.setStyleSheet(
            f"QFrame#NavBadge {{ background-color: {theme.badge}; border-radius: 10px; }}"
        )
        layout = QVBoxLayout(chip)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        font = QFont()
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.DemiBold)
        label = QLabel(text)
        label.setFont(font)
        label.setStyleSheet("color: #FFFFFF; background: transparent;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        return chip
    return Pill(
        text=text,
        bg=theme.badge,
        fg="#FFFFFF",
        radius=10,
        padding=(2, 8, 2, 8),
    )


@dataclass
class NavItemHandle:
    container: ClickFrame
    icon: IconLabel
    text: QLabel

    def set_active(self, theme: Theme, *, active: bool) -> None:
        self.icon.set_color(theme.primary if active else theme.text_muted)
        self.text.setStyleSheet(
            f"color: {theme.text if active else theme.text_muted}; background: transparent;"
        )
        font = self.text.font()
        font.setWeight(QFont.Weight.DemiBold if active else QFont.Weight.Normal)
        self.text.setFont(font)
        bg = theme.primary_tint if active else "transparent"
        hover_bg = rgba(theme.primary, 0.10)
        self.container.setStyleSheet(
            f"""
            ClickFrame {{
                background-color: {bg};
                border-radius: 10px;
            }}
            ClickFrame:hover {{
                background-color: {hover_bg if not active else theme.primary_tint};
            }}
            """
        )


def nav_item_handle(
    theme: Theme,
    icon: str,
    label: str,
    *,
    active: bool = False,
    badge: Optional[str] = None,
    on_click: Optional[Callable[[], None]] = None,
) -> NavItemHandle:
    container = ClickFrame()
    container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
    layout: QHBoxLayout = hbox(spacing=12, margins=(12, 10, 12, 10))
    container.setLayout(layout)

    icon_color = theme.primary if active else theme.text_muted
    icon_label = IconLabel(icon, color=icon_color, size=20)
    layout.addWidget(icon_label)

    text_color = theme.text if active else theme.text_muted
    text_label = QLabel(label)
    font = QFont()
    font.setPixelSize(13)
    font.setWeight(QFont.Weight.DemiBold if active else QFont.Weight.Normal)
    text_label.setFont(font)
    text_label.setStyleSheet(f"color: {text_color}; background: transparent;")
    text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    text_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
    layout.addWidget(text_label, 1)

    if badge:
        layout.addWidget(_badge_widget(theme, badge))

    bg = theme.primary_tint if active else "transparent"
    hover_bg = rgba(theme.primary, 0.10) if not active else theme.primary_tint
    container.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {bg};
            border-radius: 10px;
        }}
        ClickFrame:hover {{
            background-color: {hover_bg};
        }}
        """
    )

    if on_click is not None:
        container.clicked.connect(on_click)

    return NavItemHandle(container=container, icon=icon_label, text=text_label)


def nav_item(
    theme: Theme,
    icon: str,
    label: str,
    *,
    active: bool = False,
    badge: Optional[str] = None,
    on_click: Optional[Callable[[], None]] = None,
) -> ClickFrame:
    return nav_item_handle(
        theme,
        icon,
        label,
        active=active,
        badge=badge,
        on_click=on_click,
    ).container
