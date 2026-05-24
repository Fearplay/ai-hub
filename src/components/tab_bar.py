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
    QScrollArea,
    QSizePolicy,
)

from src.qt.widgets import ClickFrame, custom_label, hbox, vbox
from src.theme import Theme


def _tab(
    theme: Theme,
    label: str,
    *,
    active: bool,
    enabled: bool = True,
    on_click: Optional[Callable[[], None]] = None,
) -> ClickFrame:
    container = ClickFrame()
    container.setStyleSheet("background: transparent; border: none;")
    container.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
    if on_click is None or not enabled:
        container.set_clickable(False)

    layout = vbox(spacing=0, margins=(12, 8, 12, 2))
    container.setLayout(layout)

    text_color = theme.text if active else theme.text_muted
    if not enabled:
        text_color = theme.text_subtle
    text_label = custom_label(label, color=text_color, size=13)
    font = QFont()
    font.setPixelSize(13)
    font.setWeight(QFont.Weight.DemiBold if active else QFont.Weight.Normal)
    text_label.setFont(font)
    text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    text_label.setWordWrap(False)
    layout.addWidget(text_label)

    underline = QFrame()
    underline.setFixedHeight(2)
    underline.setStyleSheet(
        f"background-color: {theme.primary if active and enabled else 'transparent'};"
        " border-radius: 1px;"
    )
    layout.addWidget(underline)

    if enabled and on_click is not None:
        container.clicked.connect(on_click)

    return container


def tab_bar(
    theme: Theme,
    *,
    tabs: Sequence[str],
    active_index: int = 0,
    on_change: Optional[Callable[[int], None]] = None,
    enabled: Optional[Sequence[bool]] = None,
) -> QFrame:
    bar = QFrame()
    bar.setObjectName("SectionTabBar")
    bar.setStyleSheet(
        f"""
        QFrame#SectionTabBar {{
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
    inner.setStyleSheet("background: transparent; border: none;")
    inner_layout = hbox(spacing=24, margins=(24, 6, 24, 6))
    inner.setLayout(inner_layout)

    active_tab: Optional[ClickFrame] = None
    enabled_flags = list(enabled or [True] * len(tabs))
    if len(enabled_flags) < len(tabs):
        enabled_flags.extend([True] * (len(tabs) - len(enabled_flags)))

    for i, label in enumerate(tabs):
        tab_enabled = bool(enabled_flags[i])
        if on_change is None or not tab_enabled:
            handler: Optional[Callable[[], None]] = None
        else:
            handler = lambda idx=i: on_change(idx)  # noqa: E731
        tab_handle = _tab(
            theme,
            label,
            active=i == active_index,
            enabled=tab_enabled,
            on_click=handler,
        )
        if i == active_index:
            active_tab = tab_handle
        inner_layout.addWidget(tab_handle)

    inner_layout.addStretch(1)
    scroll.setWidget(inner)

    # Center the active tab in the scroll viewport on the next event-loop
    # tick (after the geometry has settled). Without this, clicking the
    # rightmost tab (e.g. "Plan to fill gaps" in the Documents tab bar)
    # leaves the leftmost ones hidden because they were the only ones
    # visible before the rebuild.
    if active_tab is not None:
        def _scroll_to_active(scroll_area=scroll, target=active_tab) -> None:
            try:
                # PySide6 expects positional margins here; keyword args
                # (xMargin/yMargin) raise AttributeError on some builds.
                scroll_area.ensureWidgetVisible(target, 80, 0)
            except RuntimeError:
                # Tab bar rebuilt out from under us - the new instance
                # will run its own scroll-into-view. Safe to ignore.
                return

        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, _scroll_to_active)

    return bar
