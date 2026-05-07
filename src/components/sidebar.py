"""Left sidebar.

Renders the brand mark, the "new chat" button, the section list (read from
the auto-discovered registry), the secondary nav, the user card, and the
language + theme toggles. Adding a new section to the sidebar happens by
creating a folder under ``src/sections/`` - this file does not need editing.

Returns a tuple ``(container, set_active)``. The ``set_active`` callback
mutates the active row in place (icon color, text color/weight, background)
so changing sections does not rebuild the whole sidebar - that is what made
clicks feel sluggish before.
"""

from __future__ import annotations

from typing import Callable

import flet as ft

from src.components.language_toggle import language_toggle
from src.components.nav_item import NavItemHandle, nav_item_handle
from src.components.theme_toggle import theme_toggle
from src.components.user_card import user_card
from src.i18n import SECONDARY_NAV, t
from src.sections import SECTIONS
from src.theme import Theme


SetActive = Callable[[str], None]


def _logo(theme: Theme, lang: str) -> ft.Row:
    icon_box = ft.Container(
        content=ft.Icon(ft.Icons.PSYCHOLOGY_ALT_OUTLINED, color=ft.Colors.WHITE, size=22),
        width=38,
        height=38,
        bgcolor=theme.primary,
        border_radius=10,
        alignment=ft.Alignment.CENTER,
    )
    title = ft.Row(
        controls=[
            ft.Text(t("app_name", lang), color=theme.text, size=18, weight=ft.FontWeight.W_700),
            ft.Text("+", color=theme.primary, size=18, weight=ft.FontWeight.W_700),
        ],
        spacing=2,
        tight=True,
    )
    return ft.Row(
        controls=[icon_box, title],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _new_chat_button(theme: Theme, lang: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.ADD, color=ft.Colors.WHITE, size=18),
                ft.Text(
                    t("new_chat", lang),
                    color=ft.Colors.WHITE,
                    size=14,
                    weight=ft.FontWeight.W_600,
                    expand=True,
                ),
                ft.Text(
                    t("new_chat_shortcut", lang),
                    color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE),
                    size=11,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=theme.primary,
        padding=ft.padding.symmetric(horizontal=14, vertical=12),
        border_radius=10,
        ink=True,
        on_click=lambda e: None,
    )


def sidebar(
    theme: Theme,
    *,
    lang: str,
    active_section: str,
    on_section_change: Callable[[str], None],
    theme_mode: str,
    on_theme_toggle: Callable[[], None],
    on_lang_toggle: Callable[[], None],
) -> tuple[ft.Container, SetActive]:
    handles: dict[str, NavItemHandle] = {}

    primary_controls: list[ft.Control] = []
    for section in SECTIONS:
        handle = nav_item_handle(
            theme,
            section.icon,
            section.label(lang),
            active=section.key == active_section,
            badge=section.badge,
            on_click=lambda e, k=section.key: on_section_change(k),
        )
        handles[section.key] = handle
        primary_controls.append(handle.container)

    secondary_controls: list[ft.Control] = []
    for item in SECONDARY_NAV:
        handle = nav_item_handle(
            theme,
            item["icon"],
            t(item["label_key"], lang),
            active=item["key"] == active_section,
            badge=item.get("badge"),
            on_click=lambda e, k=item["key"]: on_section_change(k),
        )
        handles[item["key"]] = handle
        secondary_controls.append(handle.container)

    container = ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    content=_logo(theme, lang),
                    padding=ft.padding.symmetric(horizontal=20, vertical=20),
                ),
                ft.Container(
                    content=_new_chat_button(theme, lang),
                    padding=ft.padding.symmetric(horizontal=16),
                ),
                ft.Container(
                    content=ft.Column(controls=primary_controls, spacing=2, tight=True),
                    padding=ft.padding.only(left=12, right=12, top=18, bottom=4),
                ),
                ft.Container(
                    content=ft.Divider(color=theme.border, height=1, thickness=1),
                    padding=ft.padding.symmetric(horizontal=16, vertical=8),
                ),
                ft.Container(
                    content=ft.Column(controls=secondary_controls, spacing=2, tight=True),
                    padding=ft.padding.symmetric(horizontal=12, vertical=4),
                ),
                ft.Container(expand=True),
                ft.Container(
                    content=user_card(theme),
                    padding=ft.padding.only(left=12, right=12, top=8, bottom=8),
                ),
                language_toggle(theme, lang, on_toggle=on_lang_toggle),
                theme_toggle(theme, lang, theme_mode=theme_mode, on_toggle=on_theme_toggle),
                ft.Container(height=12),
            ],
            spacing=0,
            tight=True,
        ),
        width=280,
        bgcolor=theme.sidebar_bg,
        border=ft.border.only(right=ft.BorderSide(1, theme.border)),
    )

    current = {"key": active_section}

    def set_active(key: str) -> None:
        if key == current["key"]:
            return

        prev = current["key"]
        if prev in handles:
            handles[prev].set_active(theme, active=False)
            handles[prev].container.update()

        if key in handles:
            handles[key].set_active(theme, active=True)
            handles[key].container.update()

        current["key"] = key

    return container, set_active
