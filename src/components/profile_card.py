"""Sidebar profile card (avatar + name + overflow menu).

Rendered below the secondary nav (Dashboard / Settings) near the bottom
of the sidebar. It replaces the old "My Profile" nav row - the section
itself is now ``hidden`` from the nav list and is reached by clicking
this card instead. The whole card is clickable (opens the profile
view); the trailing ``⋮`` button opens a small menu with quick links to
the profile and the settings section.

The display name comes from ``settings_store.get_profile_name()`` and is
**empty by default** - the card shows a muted "set your name" placeholder
until the user types one in Settings. There is no hard-coded mock name
and no subscription/plan line anymore.

The card intentionally uses neutral surface/border/text tokens (no
per-section accent) so the in-place accent restyle that runs on every
section switch never has to touch it - the avatar stays a calm grey
circle exactly like a real account chip.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QMenu, QSizePolicy

from src.i18n import t
from src.qt.icons import Icons
from src.qt.theme import rgba
from src.qt.widgets import (
    ClickFrame,
    IconLabel,
    IconOnlyButton,
    custom_label,
    hbox,
    vbox,
    wrap_label_slot,
)
from src.services import settings_store
from src.theme import Theme


def _themed_menu(theme: Theme) -> QMenu:
    menu = QMenu()
    menu.setStyleSheet(
        f"""
        QMenu {{
            background-color: {theme.surface};
            color: {theme.text};
            border: 1px solid {theme.border};
            border-radius: 10px;
            padding: 6px;
        }}
        QMenu::item {{
            padding: 8px 14px;
            border-radius: 6px;
        }}
        QMenu::item:selected {{
            background-color: {rgba(theme.primary, 0.18)};
            color: {theme.text};
        }}
        """
    )
    return menu


def profile_card(
    theme: Theme,
    lang: str,
    *,
    on_open: Callable[[], None],
    on_settings: Callable[[], None],
) -> QFrame:
    card = ClickFrame()
    card.setObjectName("ProfileCard")
    card.setStyleSheet(
        f"""
        ClickFrame#ProfileCard {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        ClickFrame#ProfileCard:hover {{
            border: 1px solid {rgba(theme.primary, 0.45)};
        }}
        """
    )
    card.clicked.connect(on_open)

    layout = hbox(spacing=10, margins=(10, 9, 8, 9))
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    card.setLayout(layout)

    avatar = QFrame()
    avatar.setFixedSize(38, 38)
    avatar.setStyleSheet(
        f"background-color: {theme.surface_2}; border-radius: 19px;"
    )
    avatar_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    avatar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    avatar.setLayout(avatar_layout)
    avatar_layout.addWidget(
        IconLabel(Icons.PERSON, color=theme.text_muted, size=22),
        alignment=Qt.AlignmentFlag.AlignCenter,
    )
    layout.addWidget(avatar)

    text_holder = QFrame()
    text_holder.setStyleSheet("background: transparent; border: none;")
    text_holder.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
    )
    text_layout = vbox(spacing=1, margins=(0, 0, 0, 0))
    text_holder.setLayout(text_layout)

    # Empty until the user sets it in Settings -> show a muted prompt
    # rather than a fake placeholder name.
    name = settings_store.get_profile_name()
    if name:
        name_label = custom_label(
            name, color=theme.text, size=13, weight=QFont.Weight.DemiBold
        )
    else:
        name_label = custom_label(
            t("profile_set_name", lang), color=theme.text_muted, size=13
        )
    wrap_label_slot(name_label)
    text_layout.addWidget(name_label)
    layout.addWidget(text_holder, 1)

    menu_btn = IconOnlyButton(
        Icons.MORE_VERT,
        color=theme.text_muted,
        size=18,
        bg_hover=theme.surface_2,
        tooltip=t("profile_menu_tooltip", lang),
    )

    def _open_menu() -> None:
        menu = _themed_menu(theme)
        act_profile = menu.addAction(t("my_profile", lang))
        act_settings = menu.addAction(t("settings", lang))
        chosen = menu.exec(menu_btn.mapToGlobal(QPoint(0, menu_btn.height() + 4)))
        if chosen is act_profile:
            on_open()
        elif chosen is act_settings:
            on_settings()

    menu_btn.clicked.connect(_open_menu)
    layout.addWidget(menu_btn, 0, Qt.AlignmentFlag.AlignVCenter)

    return card
