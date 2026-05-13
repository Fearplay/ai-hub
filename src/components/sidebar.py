"""Left sidebar.

Renders the brand mark, the "new chat" button, the section list (read from
the auto-discovered registry), the secondary nav, the user card, and the
language + theme toggles. Adding a new section to the sidebar happens by
creating a folder under ``src/sections/`` - this file does not need editing.

Layout has three vertical zones so the content scrolls cleanly even on
short windows:

* **header** - logo + "+ New chat" button, fixed height at the top.
* **middle** - primary nav, divider, secondary nav. Wrapped in a scrolling
  ``QScrollArea`` so long section lists never push the footer off-screen.
* **footer** - user card, language toggle, theme toggle, fixed at the
  bottom.

Returns a tuple ``(QFrame, set_active)``. The ``set_active`` callback
mutates the active row in place (icon color, text color/weight, background)
so changing sections does not rebuild the whole sidebar - that is what made
clicks feel sluggish before.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
)

from src.components.language_toggle import language_toggle
from src.components.nav_item import (
    NavItemHandle,
    ReorderHandle,
    nav_item_handle,
    reorderable_nav_item,
)
from src.components.theme_toggle import theme_toggle
from src.components.user_card import user_card
from src.i18n import t
from src.qt.icons import Icons
from src.qt.widgets import (
    ClickFrame,
    HSeparator,
    IconLabel,
    hbox,
    vbox,
)
from src.sections import (
    PRIMARY_SECTIONS,
    SECONDARY_SECTIONS,
    reload_primary_order,
)
from src.services import logger as logger_service
from src.services import settings_store
from src.theme import Theme


SetActive = Callable[[str], None]


def _logo(theme: Theme, lang: str) -> QFrame:
    frame = QFrame()
    frame.setStyleSheet("background: transparent;")
    layout = hbox(spacing=12, margins=(0, 0, 0, 0))
    frame.setLayout(layout)

    icon_box = QFrame()
    icon_box.setFixedSize(38, 38)
    icon_box.setStyleSheet(
        f"background-color: {theme.primary}; border-radius: 10px;"
    )
    icon_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setLayout(icon_layout)
    icon = IconLabel(Icons.PSYCHOLOGY_ALT_OUTLINED, color="#FFFFFF", size=22)
    icon_layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(icon_box)

    name = QLabel(t("app_name", lang))
    name_font = QFont()
    name_font.setPixelSize(17)
    name_font.setWeight(QFont.Weight.Bold)
    name.setFont(name_font)
    name.setStyleSheet(f"color: {theme.text}; background: transparent;")
    layout.addWidget(name)

    plus = QLabel("+")
    plus_font = QFont()
    plus_font.setPixelSize(17)
    plus_font.setWeight(QFont.Weight.Bold)
    plus.setFont(plus_font)
    plus.setStyleSheet(f"color: {theme.primary}; background: transparent;")
    layout.addWidget(plus)
    layout.addStretch(1)

    return frame


def _new_chat_button(theme: Theme, lang: str) -> ClickFrame:
    btn = ClickFrame()
    btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
    btn.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {theme.primary};
            border-radius: 10px;
        }}
        ClickFrame:hover {{
            background-color: {theme.primary_hover};
        }}
        """
    )
    layout = hbox(spacing=8, margins=(14, 12, 14, 12))
    btn.setLayout(layout)

    icon = IconLabel(Icons.ADD, color="#FFFFFF", size=18)
    layout.addWidget(icon)

    label = QLabel(t("new_chat", lang))
    font = QFont()
    font.setPixelSize(13)
    font.setWeight(QFont.Weight.DemiBold)
    label.setFont(font)
    label.setStyleSheet("color: #FFFFFF; background: transparent;")
    layout.addWidget(label, 1)

    shortcut = QLabel(t("new_chat_shortcut", lang))
    shortcut_font = QFont()
    shortcut_font.setPixelSize(11)
    shortcut.setFont(shortcut_font)
    shortcut.setStyleSheet("color: rgba(255,255,255,0.7); background: transparent;")
    layout.addWidget(shortcut)

    return btn


def _persist_reorder(source_key: str, target_key: str, before: bool) -> bool:
    """Compute and save the new primary section order after a drop.

    Returns ``True`` when the order actually changed. The sidebar
    rebuild is then triggered by the caller via
    :func:`src.app.request_section_refresh`.
    """
    current = [s.key for s in PRIMARY_SECTIONS]
    if source_key not in current or target_key not in current:
        return False
    current.remove(source_key)
    insert_at = current.index(target_key) + (0 if before else 1)
    current.insert(insert_at, source_key)
    try:
        settings_store.set_sidebar_order(current)
    except Exception as exc:
        logger_service.log_exception(
            "sidebar", "persist_reorder_failed", exc,
            source=source_key, target=target_key, before=before,
        )
        return False
    reload_primary_order()
    logger_service.log_event(
        "INFO", "sidebar", "reorder_done",
        source=source_key, target=target_key, before=before,
        order=current,
    )
    return True


def sidebar(
    theme: Theme,
    *,
    lang: str,
    active_section: str,
    on_section_change: Callable[[str], None],
    theme_mode: str,
    on_theme_toggle: Callable[[], None],
    on_lang_toggle: Callable[[], None],
) -> tuple[QFrame, SetActive]:
    primary_handles: dict[str, ReorderHandle] = {}
    secondary_handles: dict[str, NavItemHandle] = {}

    def _on_reorder(source_key: str, target_key: str, before: bool) -> None:
        if not _persist_reorder(source_key, target_key, before):
            return
        try:
            from src.app import request_section_refresh

            request_section_refresh()
        except Exception as exc:
            logger_service.log_exception(
                "sidebar", "reorder_refresh_failed", exc,
            )

    def _build_primary(into_layout: QVBoxLayout) -> None:
        for section in PRIMARY_SECTIONS:
            handle = reorderable_nav_item(
                theme,
                section.icon,
                section.label(lang),
                section_key=section.key,
                active=section.key == active_section,
                badge=section.badge,
                on_click=lambda k=section.key: on_section_change(k),
                on_reorder=_on_reorder,
            )
            primary_handles[section.key] = handle
            into_layout.addWidget(handle.container)

    def _build_secondary(into_layout: QVBoxLayout) -> None:
        for section in SECONDARY_SECTIONS:
            handle = nav_item_handle(
                theme,
                section.icon,
                section.label(lang),
                active=section.key == active_section,
                badge=section.badge,
                on_click=lambda k=section.key: on_section_change(k),
            )
            secondary_handles[section.key] = handle
            into_layout.addWidget(handle.container)

    container = QFrame()
    container.setObjectName("Sidebar")
    container.setFixedWidth(280)
    container.setStyleSheet(
        f"""
        QFrame#Sidebar {{
            background-color: {theme.sidebar_bg};
            border-right: 1px solid {theme.border};
        }}
        """
    )
    root = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(root)

    # header ----------------------------------------------------------------
    header = QFrame()
    header.setStyleSheet("background: transparent;")
    header_layout = vbox(spacing=14, margins=(20, 18, 20, 8))
    header.setLayout(header_layout)
    header_layout.addWidget(_logo(theme, lang))
    new_btn = _new_chat_button(theme, lang)
    header_layout.addWidget(new_btn)
    root.addWidget(header)

    # middle (scrollable) ---------------------------------------------------
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet("QScrollArea { background: transparent; }")

    middle = QFrame()
    middle.setStyleSheet("background: transparent;")
    middle_layout = vbox(spacing=4, margins=(12, 10, 12, 8))
    middle.setLayout(middle_layout)

    primary_holder = QFrame()
    primary_holder.setStyleSheet("background: transparent;")
    primary_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    primary_holder.setLayout(primary_layout)
    _build_primary(primary_layout)
    middle_layout.addWidget(primary_holder)

    if SECONDARY_SECTIONS:
        sep_holder = QFrame()
        sep_holder.setStyleSheet("background: transparent;")
        sep_layout = vbox(spacing=0, margins=(4, 6, 4, 4))
        sep_holder.setLayout(sep_layout)
        sep_layout.addWidget(HSeparator(theme))
        middle_layout.addWidget(sep_holder)

        secondary_holder = QFrame()
        secondary_holder.setStyleSheet("background: transparent;")
        secondary_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
        secondary_holder.setLayout(secondary_layout)
        _build_secondary(secondary_layout)
        middle_layout.addWidget(secondary_holder)

    middle_layout.addStretch(1)
    scroll.setWidget(middle)
    root.addWidget(scroll, 1)

    # footer ----------------------------------------------------------------
    footer = QFrame()
    footer.setStyleSheet("background: transparent;")
    footer_layout = vbox(spacing=4, margins=(0, 6, 0, 12))
    footer.setLayout(footer_layout)

    user_holder = QFrame()
    user_holder.setStyleSheet("background: transparent;")
    user_holder_layout = vbox(spacing=0, margins=(12, 4, 12, 6))
    user_holder.setLayout(user_holder_layout)
    user_holder_layout.addWidget(user_card(theme))
    footer_layout.addWidget(user_holder)

    footer_layout.addWidget(language_toggle(theme, lang, on_toggle=on_lang_toggle))
    footer_layout.addWidget(
        theme_toggle(theme, lang, theme_mode=theme_mode, on_toggle=on_theme_toggle)
    )
    root.addWidget(footer)

    current = {"key": active_section}

    def set_active(key: str) -> None:
        if key == current["key"]:
            return
        prev = current["key"]
        if prev in primary_handles:
            primary_handles[prev].set_active(theme, active=False)
        elif prev in secondary_handles:
            secondary_handles[prev].set_active(theme, active=False)
        if key in primary_handles:
            primary_handles[key].set_active(theme, active=True)
        elif key in secondary_handles:
            secondary_handles[key].set_active(theme, active=True)
        current["key"] = key

    return container, set_active
