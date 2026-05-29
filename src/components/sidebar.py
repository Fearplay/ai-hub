"""Left sidebar.

Renders the brand mark, the section list (read from the auto-discovered
registry), the secondary nav, the user card, and the language + theme
toggles. Adding a new section to the sidebar happens by creating a
folder under ``src/sections/`` - this file does not need editing.

Layout has three vertical zones so the content scrolls cleanly even on
short windows:

* **header** - logo only, fixed height at the top.
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
    QVBoxLayout,
)

from src.components.language_toggle import language_toggle
from src.components.nav_item import (
    NavItemHandle,
    ReorderHandle,
    nav_item_handle,
    reorderable_nav_item,
)
from src.components.profile_card import profile_card
from src.components.theme_toggle import theme_toggle
from src.i18n import t
from src.qt.icons import Icons
from src.qt.widgets import (
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
# Restyle the already-built sidebar to a new (per-section accent) theme
# without tearing the row tree down. Section navigation calls this so the
# logo tile, the active nav row, badges and the footer toggles pick up the
# new accent on the same frame as the centre column - otherwise the sidebar
# keeps the previous section's accent until the next full rebuild.
UpdateTheme = Callable[[Theme], None]


def _logo(theme: Theme, lang: str) -> tuple[QFrame, QFrame]:
    """Sidebar brand mark - icon tile + product name.

    Returns ``(frame, icon_box)`` so the caller can recolour the accent
    tile in place when the active section's accent changes.

    Previously rendered a trailing ``+`` glyph as a visual hook for the
    "new chat" action; that affordance is now gone because we removed
    the new-chat button entirely (the brand mark is purely decorative,
    no action lives next to it).
    """
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
    layout.addStretch(1)

    return frame, icon_box


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
) -> tuple[QFrame, SetActive, UpdateTheme]:
    primary_handles: dict[str, ReorderHandle] = {}
    secondary_handles: dict[str, NavItemHandle] = {}

    def _on_reorder(source_key: str, target_key: str, before: bool) -> None:
        if not _persist_reorder(source_key, target_key, before):
            return
        try:
            # Use the full ``_smart_rebuild`` (sidebar + section + context)
            # instead of just refreshing the centre column. Without this the
            # nav rows keep their pre-drop order until the user toggles the
            # language, which feels broken.
            from src.app import request_sidebar_refresh

            request_sidebar_refresh()
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
    # Just the brand mark now - the old "Nová konverzace" / "New chat"
    # button never had a target (the app has no global chat view) so
    # clicking it did nothing. Removing it leaves the sidebar focused
    # on the nav list.
    header = QFrame()
    header.setStyleSheet("background: transparent;")
    header_layout = vbox(spacing=14, margins=(20, 18, 20, 8))
    header.setLayout(header_layout)
    logo_frame, logo_icon_box = _logo(theme, lang)
    header_layout.addWidget(logo_frame)
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

    # Secondary nav (Dashboard / Settings) sits *directly under* the AI
    # module list, separated by a thin divider - per the user request the
    # Dashboard + Settings rows live right below "AI Životopis / Kariéra"
    # instead of being pushed to the very bottom of the sidebar.
    if SECONDARY_SECTIONS:
        sep_holder = QFrame()
        sep_holder.setStyleSheet("background: transparent;")
        sep_layout = vbox(spacing=0, margins=(4, 4, 4, 4))
        sep_holder.setLayout(sep_layout)
        sep_layout.addWidget(HSeparator(theme))
        middle_layout.addWidget(sep_holder)

        secondary_holder = QFrame()
        secondary_holder.setStyleSheet("background: transparent;")
        secondary_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
        secondary_holder.setLayout(secondary_layout)
        _build_secondary(secondary_layout)
        middle_layout.addWidget(secondary_holder)

    # Account card - sits *below* the Dashboard / Settings group ("the
    # profile goes under Settings"). Clicking it opens the (nav-hidden)
    # profile view; the name comes from Settings (empty placeholder until
    # the user sets one).
    profile_holder = QFrame()
    profile_holder.setStyleSheet("background: transparent;")
    profile_layout = vbox(spacing=0, margins=(0, 8, 0, 4))
    profile_holder.setLayout(profile_layout)
    profile_layout.addWidget(
        profile_card(
            theme,
            lang,
            on_open=lambda: on_section_change("my_profile"),
            on_settings=lambda: on_section_change("settings"),
        )
    )
    middle_layout.addWidget(profile_holder)

    # Flexible gap below everything keeps the module list + tools + account
    # card packed at the top; the footer toggles stay pinned to the bottom.
    middle_layout.addStretch(1)

    scroll.setWidget(middle)
    root.addWidget(scroll, 1)

    # footer ----------------------------------------------------------------
    # The account chip now lives at the bottom of the scrollable middle
    # (see ``profile_card`` above, just over the Dashboard / Settings
    # group); the footer keeps only the language + theme toggles pinned
    # to the very bottom.
    footer = QFrame()
    footer.setStyleSheet("background: transparent;")
    footer_layout = vbox(spacing=4, margins=(0, 6, 0, 12))
    footer.setLayout(footer_layout)

    footer_widgets: dict[str, QFrame] = {
        "lang": language_toggle(theme, lang, on_toggle=on_lang_toggle),
        "theme": theme_toggle(
            theme, lang, theme_mode=theme_mode, on_toggle=on_theme_toggle
        ),
    }
    footer_layout.addWidget(footer_widgets["lang"])
    footer_layout.addWidget(footer_widgets["theme"])
    root.addWidget(footer)

    # Mutable so the navigation callbacks below always restyle with the
    # accent of the *currently* active section, not the accent that was
    # frozen into this closure when the sidebar was first built.
    state = {"key": active_section, "theme": theme}

    def set_active(key: str) -> None:
        if key == state["key"]:
            return
        active_theme = state["theme"]
        prev = state["key"]
        if prev in primary_handles:
            primary_handles[prev].set_active(active_theme, active=False)
        elif prev in secondary_handles:
            secondary_handles[prev].set_active(active_theme, active=False)
        if key in primary_handles:
            primary_handles[key].set_active(active_theme, active=True)
        elif key in secondary_handles:
            secondary_handles[key].set_active(active_theme, active=True)
        state["key"] = key

    def update_theme(new_theme: Theme) -> None:
        """Recolour the live sidebar to ``new_theme`` (per-section accent).

        Restyles the logo tile, every nav row (active + inactive), the
        drag-drop hint colour and the footer toggles without rebuilding
        the row tree. Called from ``app.set_section`` so the sidebar and
        the centre column flip accent on the same frame.
        """
        try:
            state["theme"] = new_theme
            logo_icon_box.setStyleSheet(
                f"background-color: {new_theme.primary}; border-radius: 10px;"
            )
            active_key = state["key"]
            for k, handle in primary_handles.items():
                handle.set_active(new_theme, active=k == active_key)
            for k, handle in secondary_handles.items():
                handle.set_active(new_theme, active=k == active_key)

            old_lang = footer_widgets.get("lang")
            old_theme = footer_widgets.get("theme")
            new_lang = language_toggle(new_theme, lang, on_toggle=on_lang_toggle)
            new_theme_w = theme_toggle(
                new_theme, lang, theme_mode=theme_mode, on_toggle=on_theme_toggle
            )
            footer_layout.addWidget(new_lang)
            footer_layout.addWidget(new_theme_w)
            footer_widgets["lang"] = new_lang
            footer_widgets["theme"] = new_theme_w
            for old in (old_lang, old_theme):
                if old is not None:
                    footer_layout.removeWidget(old)
                    old.deleteLater()
        except Exception as exc:
            logger_service.log_exception("sidebar", "update_theme_failed", exc)

    return container, set_active, update_theme
