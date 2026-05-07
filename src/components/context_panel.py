"""Right-hand panel scaffolding shared by every section view.

The actual cards are owned by each section in ``sections/<key>/context.py``.
This module gives you:

* :func:`context_panel_shell` - the outer container + scrollable column
  every section drops its cards into.
* :func:`empty_context_panel`  - default for sections without a custom panel.
* :func:`quick_action_row`     - reusable row used by quick-action cards.
* :func:`history_row`          - reusable row used by history cards.
* :func:`add_document_button`  - reusable purple "add document" button.
"""

from __future__ import annotations

from typing import Sequence

import flet as ft

from src.i18n import t
from src.theme import Theme


def context_panel_shell(theme: Theme, *cards: ft.Control) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=list(cards),
            spacing=16,
            tight=True,
            scroll=ft.ScrollMode.ADAPTIVE,
        ),
        width=336,
        padding=16,
        bgcolor=theme.bg,
        border=ft.border.only(left=ft.BorderSide(1, theme.border)),
    )


def empty_context_panel(theme: Theme) -> ft.Container:
    return ft.Container(
        width=336,
        bgcolor=theme.bg,
        border=ft.border.only(left=ft.BorderSide(1, theme.border)),
    )


def add_document_button(theme: Theme, lang: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.ADD, color=theme.primary, size=16),
                ft.Text(
                    t("add_document", lang),
                    color=theme.primary,
                    size=13,
                    weight=ft.FontWeight.W_500,
                ),
            ],
            spacing=6,
            alignment=ft.MainAxisAlignment.CENTER,
            tight=True,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=12),
        bgcolor=ft.Colors.with_opacity(0.10, theme.primary),
        border_radius=10,
        border=ft.border.all(1, ft.Colors.with_opacity(0.20, theme.primary)),
        ink=True,
        on_click=lambda e: None,
        alignment=ft.Alignment.CENTER,
    )


def quick_action_row(theme: Theme, icon: str, label: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=theme.text_muted, size=16),
                ft.Text(
                    label,
                    color=theme.text,
                    size=13,
                    expand=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    max_lines=1,
                ),
                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=theme.text_muted, size=16),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=8, vertical=10),
        border_radius=8,
        ink=True,
        on_click=lambda e: None,
    )


def history_row(
    theme: Theme,
    title: str,
    time: str,
    *,
    pinned: bool = False,
) -> ft.Container:
    title_row_children: list[ft.Control] = [
        ft.Text(
            title,
            color=theme.text,
            size=13,
            weight=ft.FontWeight.W_500,
            expand=True,
            overflow=ft.TextOverflow.ELLIPSIS,
            max_lines=1,
        ),
    ]
    if pinned:
        title_row_children.append(
            ft.Icon(ft.Icons.PUSH_PIN, color=theme.primary, size=12)
        )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=title_row_children,
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(time, color=theme.text_muted, size=11),
            ],
            spacing=2,
            tight=True,
        ),
        padding=ft.padding.symmetric(horizontal=4, vertical=6),
        border_radius=6,
        ink=True,
        on_click=lambda e: None,
    )


def quick_actions_column(
    theme: Theme,
    actions: Sequence[dict],
) -> ft.Column:
    return ft.Column(
        controls=[quick_action_row(theme, a["icon"], a["label"]) for a in actions],
        spacing=2,
        tight=True,
    )


def history_column(
    theme: Theme,
    items: Sequence[dict],
) -> ft.Column:
    return ft.Column(
        controls=[
            history_row(theme, h["title"], h["time"], pinned=h.get("pinned", False))
            for h in items
        ],
        spacing=4,
        tight=True,
    )
