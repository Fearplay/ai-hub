"""Generic top bar of a section view (icon, title, subtitle, actions)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QMenu,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from src.i18n import t
from src.qt.icons import Icons, glyph, icon_font
from src.qt.widgets import (
    GhostButton,
    IconLabel,
    MutedLabel,
    TitleLabel,
    hbox,
    vbox,
)
from src.theme import Theme


HeaderClickHandler = Callable[[], None]


@dataclass(frozen=True)
class HeaderMenuItem:
    """One row in the section header's overflow menu.

    Sections build a list of these and pass them to :func:`header`. When
    ``on_click`` is ``None`` or ``enabled`` is False the item renders
    disabled (useful for "Open run folder" when no run exists yet).
    """

    icon: str
    label: str
    on_click: Optional[HeaderClickHandler] = None
    enabled: bool = True


def _category_icon(theme: Theme, icon: str) -> QFrame:
    box = QFrame()
    box.setFixedSize(44, 44)
    box.setStyleSheet(
        f"background-color: {theme.primary}; border-radius: 12px;"
    )
    layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    box.setLayout(layout)
    layout.addWidget(
        IconLabel(icon, color="#FFFFFF", size=22),
        alignment=Qt.AlignmentFlag.AlignCenter,
    )
    return box


def _menu_button(theme: Theme, menu_items: Sequence[HeaderMenuItem]) -> QWidget:
    btn = QToolButton()
    btn.setText(glyph(Icons.MORE_HORIZ))
    btn.setFont(icon_font(18))
    btn.setFixedSize(38, 38)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        f"""
        QToolButton {{
            background-color: {theme.surface};
            color: {theme.text};
            border: 1px solid {theme.border};
            border-radius: 10px;
        }}
        QToolButton:hover {{
            background-color: {theme.surface_2};
        }}
        QToolButton::menu-indicator {{
            image: none;
            width: 0;
            height: 0;
        }}
        """
    )
    if not menu_items:
        return btn

    menu = QMenu(btn)
    menu.setStyleSheet(
        f"""
        QMenu {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 10px;
            padding: 6px;
        }}
        QMenu::item {{
            background-color: transparent;
            color: {theme.text};
            padding: 8px 14px;
            border-radius: 6px;
        }}
        QMenu::item:selected {{
            background-color: {theme.surface_2};
        }}
        QMenu::item:disabled {{
            color: {theme.text_subtle};
        }}
        """
    )

    for item in menu_items:
        action = QAction(item.label, menu)
        # The Material Icons font isn't rendered as an image, so embed
        # the glyph as a small rendered pixmap so the menu shows an
        # icon next to each label.
        pix = _glyph_to_pixmap(item.icon, color=theme.text_muted, size=16)
        if pix is not None:
            action.setIcon(QIcon(pix))
        action.setEnabled(item.enabled and item.on_click is not None)
        if item.enabled and item.on_click is not None:
            action.triggered.connect(item.on_click)
        menu.addAction(action)

    btn.setMenu(menu)
    btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    return btn


def _glyph_to_pixmap(name: str, *, color: str, size: int) -> Optional[QPixmap]:
    """Render a Material Icons glyph to a transparent ``QPixmap`` for menus."""
    from PySide6.QtCore import QRect, Qt as QtCore_Qt
    from PySide6.QtGui import QColor, QPainter

    g = glyph(name)
    if not g or g == "?":
        return None
    pix = QPixmap(size, size)
    pix.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    painter.setFont(icon_font(size))
    painter.setPen(QColor(color))
    painter.drawText(QRect(0, 0, size, size), QtCore_Qt.AlignmentFlag.AlignCenter, g)
    painter.end()
    return pix


def header(
    theme: Theme,
    lang: str,
    *,
    icon: str,
    title: str,
    subtitle: Optional[str] = None,
    on_help_click: Optional[HeaderClickHandler] = None,
    trailing: Optional[QWidget] = None,
    menu_items: Optional[Sequence[HeaderMenuItem]] = None,
) -> QFrame:
    bar = QFrame()
    bar.setStyleSheet(f"background-color: {theme.bg};")
    bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

    row = hbox(spacing=14, margins=(24, 22, 24, 10))
    bar.setLayout(row)

    row.addWidget(_category_icon(theme, icon))

    text_col = QFrame()
    text_col.setStyleSheet("background: transparent;")
    text_col.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    text_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    text_col.setLayout(text_layout)
    text_layout.addWidget(TitleLabel(title, theme=theme, size=18, weight=QFont.Weight.Bold))
    if subtitle:
        text_layout.addWidget(MutedLabel(subtitle, theme=theme, size=12))
    row.addWidget(text_col, 1)

    if trailing is not None:
        row.addWidget(trailing)

    help_btn = GhostButton(
        t("how_to_use", lang),
        theme=theme,
        icon=Icons.MENU_BOOK_OUTLINED,
    )
    if on_help_click is not None:
        help_btn.clicked.connect(on_help_click)
    row.addWidget(help_btn)

    row.addWidget(_menu_button(theme, menu_items or []))

    return bar
