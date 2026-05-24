"""Generic top bar of a section view (icon, title, subtitle, actions)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from src.i18n import t
from src.qt.icons import Icons, qicon
from src.qt.widgets import (
    GhostButton,
    IconLabel,
    MutedLabel,
    TitleLabel,
    hbox,
    vbox,
    wrap_label_slot,
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


def _category_icon(theme: Theme, icon: str, *, compact: bool = False) -> QFrame:
    box = QFrame()
    if compact:
        box.setFixedSize(36, 36)
        radius = 10
        glyph_size = 18
    else:
        box.setFixedSize(44, 44)
        radius = 12
        glyph_size = 22
    box.setStyleSheet(
        f"background-color: {theme.primary}; border-radius: {radius}px;"
    )
    layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    box.setLayout(layout)
    layout.addWidget(
        IconLabel(icon, color="#FFFFFF", size=glyph_size),
        alignment=Qt.AlignmentFlag.AlignCenter,
    )
    return box


def _menu_button(theme: Theme, menu_items: Sequence[HeaderMenuItem]) -> QWidget:
    btn = QToolButton()
    # Glyph is drawn by the centred IconLabel child below — keeping the
    # native QToolButton text on top would render the glyph twice, so
    # we explicitly clear it.
    btn.setText("")
    btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
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
    glyph_label = IconLabel(Icons.MORE_HORIZ, color=theme.text, size=18, parent=btn)
    glyph_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    glyph_layout = QHBoxLayout(btn)
    glyph_layout.setContentsMargins(0, 0, 0, 0)
    glyph_layout.setSpacing(0)
    glyph_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    glyph_layout.addWidget(glyph_label, 0, Qt.AlignmentFlag.AlignCenter)

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
        # QtAwesome returns a ``QIcon`` we can hand straight to the
        # ``QAction`` - Qt picks the pixmap size on the fly based on
        # the menu's icon size, so we don't need to pre-rasterise.
        action.setIcon(qicon(item.icon, color=theme.text_muted))
        action.setEnabled(item.enabled and item.on_click is not None)
        if item.enabled and item.on_click is not None:
            action.triggered.connect(item.on_click)
        menu.addAction(action)

    btn.setMenu(menu)
    btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    return btn


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
    show_help_button: bool = True,
    show_menu_button: bool = True,
    compact: bool = False,
) -> QFrame:
    """Render the section's top bar.

    ``show_help_button`` / ``show_menu_button`` let sections (currently
    only AI Legal) hide the trailing GhostButton ("How to use this") and
    the ``...`` overflow menu. Defaults stay ``True`` so every other
    section keeps its current look.

    ``compact`` shrinks the vertical padding and the category icon so
    sections that need a denser layout (AI Legal again) can save
    vertical real estate for the content below the bar.
    """
    bar = QFrame()
    bar.setStyleSheet(f"background-color: {theme.bg};")
    bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    margins = (24, 12, 24, 6) if compact else (24, 18, 24, 12)
    spacing = 12 if compact else 14
    root = vbox(spacing=0, margins=margins)
    bar.setLayout(root)

    row = QFrame()
    row.setStyleSheet("background: transparent;")
    row_layout = hbox(spacing=spacing, margins=(0, 0, 0, 0))
    row_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    row.setLayout(row_layout)
    root.addWidget(row)

    icon_widget = _category_icon(theme, icon, compact=compact)
    row_layout.addWidget(icon_widget, 0, Qt.AlignmentFlag.AlignTop)

    title_col = QFrame()
    title_col.setStyleSheet("background: transparent;")
    wrap_label_slot(title_col)
    title_layout = vbox(spacing=4 if subtitle else 0, margins=(0, 0, 0, 0))
    title_col.setLayout(title_layout)
    title_size = 16 if compact else 18
    title_layout.addWidget(TitleLabel(title, theme=theme, size=title_size, weight=QFont.Weight.Bold))
    if subtitle:
        subtitle_label = MutedLabel(subtitle, theme=theme, size=12)
        subtitle_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        title_layout.addWidget(subtitle_label)
    row_layout.addWidget(title_col, 1, Qt.AlignmentFlag.AlignTop)

    actions = QFrame()
    actions.setStyleSheet("background: transparent;")
    actions_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    actions_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    actions.setLayout(actions_layout)
    if trailing is not None:
        actions_layout.addWidget(trailing)

    if show_help_button:
        help_btn = GhostButton(
            t("how_to_use", lang),
            theme=theme,
            icon=Icons.MENU_BOOK_OUTLINED,
        )
        if on_help_click is not None:
            help_btn.clicked.connect(on_help_click)
        actions_layout.addWidget(help_btn)

    # Only render the overflow ``...`` button when the section actually
    # has menu items - an empty popup is a dead affordance that the
    # user clicks expecting something to happen (see the screenshot
    # report that triggered this change).
    if show_menu_button and menu_items:
        actions_layout.addWidget(_menu_button(theme, menu_items))

    if actions_layout.count():
        row_layout.addWidget(actions, 0, Qt.AlignmentFlag.AlignTop)

    return bar
