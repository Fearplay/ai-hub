"""Generic top bar of a section view (icon, title, subtitle, actions)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Sequence

import flet as ft

from src.i18n import t
from src.theme import Theme


@dataclass(frozen=True)
class HeaderMenuItem:
    """One row in the section header's overflow menu.

    Sections build a list of these and pass them to :func:`header`. When
    ``on_click`` is None the item renders disabled (useful for "Open run
    folder" when no run exists yet).
    """

    icon: str
    label: str
    on_click: Optional[Callable[[ft.ControlEvent], None]] = None
    enabled: bool = True


def _category_icon(theme: Theme, icon: str) -> ft.Container:
    return ft.Container(
        content=ft.Icon(icon, color=ft.Colors.WHITE, size=22),
        width=44,
        height=44,
        bgcolor=theme.primary,
        border_radius=12,
        alignment=ft.Alignment.CENTER,
    )


def _help_button(
    theme: Theme,
    label: str,
    *,
    on_click: Optional[Callable[[ft.ControlEvent], None]] = None,
) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.MENU_BOOK_OUTLINED, color=theme.text, size=16),
                ft.Text(label, color=theme.text, size=13, weight=ft.FontWeight.W_500),
            ],
            spacing=8,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        bgcolor=theme.surface,
        border_radius=10,
        border=ft.border.all(1, theme.border),
        ink=True,
        on_click=on_click or (lambda e: None),
    )


def _menu_button(
    theme: Theme,
    menu_items: Sequence[HeaderMenuItem],
) -> ft.Control:
    """Render the overflow ("...") action.

    When the section provides menu items we wire up Flet's
    :class:`ft.PopupMenuButton` so clicks actually open something. When
    no items are provided we keep a static dot icon (the user has nothing
    meaningful to invoke yet, but we don't want the layout to jump).
    """
    if not menu_items:
        return ft.Container(
            content=ft.Icon(ft.Icons.MORE_HORIZ, color=theme.text_muted, size=18),
            width=38,
            height=38,
            bgcolor=theme.surface,
            border_radius=10,
            border=ft.border.all(1, theme.border),
            alignment=ft.Alignment.CENTER,
        )

    def _to_popup_item(item: HeaderMenuItem) -> ft.PopupMenuItem:
        row = ft.Row(
            controls=[
                ft.Icon(item.icon, color=theme.text_muted, size=16),
                ft.Text(
                    item.label,
                    color=theme.text if item.enabled else theme.text_subtle,
                    size=13,
                    weight=ft.FontWeight.W_500,
                ),
            ],
            spacing=10,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return ft.PopupMenuItem(
            content=row,
            on_click=item.on_click if item.enabled else None,
        )

    popup = ft.PopupMenuButton(
        content=ft.Container(
            content=ft.Icon(ft.Icons.MORE_HORIZ, color=theme.text, size=18),
            width=38,
            height=38,
            bgcolor=theme.surface,
            border_radius=10,
            border=ft.border.all(1, theme.border),
            alignment=ft.Alignment.CENTER,
        ),
        items=[_to_popup_item(item) for item in menu_items],
        bgcolor=theme.surface,
        tooltip="",
    )
    return popup


def header(
    theme: Theme,
    lang: str,
    *,
    icon: str,
    title: str,
    subtitle: Optional[str] = None,
    on_help_click: Optional[Callable[[ft.ControlEvent], None]] = None,
    trailing: Optional[ft.Control] = None,
    menu_items: Optional[Sequence[HeaderMenuItem]] = None,
) -> ft.Container:
    actions: list[ft.Control] = []
    if trailing is not None:
        actions.append(trailing)
    actions.append(_help_button(theme, t("how_to_use", lang), on_click=on_help_click))
    actions.append(_menu_button(theme, menu_items or []))

    return ft.Container(
        content=ft.Row(
            controls=[
                _category_icon(theme, icon),
                ft.Column(
                    controls=[
                        ft.Text(
                            title,
                            color=theme.text,
                            size=18,
                            weight=ft.FontWeight.W_700,
                        ),
                        ft.Text(
                            subtitle or "",
                            color=theme.text_muted,
                            size=12,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
                *actions,
            ],
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.only(left=24, right=24, top=22, bottom=10),
    )
