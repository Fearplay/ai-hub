"""Reusable "How to use this assistant" modal.

Sections build a list of :class:`HowToSection` (an icon, a title, a body)
and pass it to :func:`open_how_to`. The dialog is rendered through
``page.show_dialog(...)`` (Flet 0.84+ API) so it survives section
switches and theme rebuilds.

Each section keeps its own per-language copy under ``how_to.py`` and
:func:`build_view`'s header ``?`` button hooks straight into this helper.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import flet as ft

from src.theme import Theme


@dataclass(frozen=True)
class HowToSection:
    icon: str
    title: str
    body: str


def _close_dialog(page: ft.Page) -> None:
    """Flet 0.84 uses page.pop_dialog(); older releases used page.close(dlg).

    Wrap in try/except so we don't crash if the API drifts again.
    """
    try:
        page.pop_dialog()
    except Exception:
        try:
            page.close(None)  # type: ignore[attr-defined]
        except Exception:
            pass


def _open_dialog(page: ft.Page, dialog: ft.AlertDialog) -> None:
    """Flet 0.84 uses page.show_dialog(dlg); older releases used page.open(dlg)."""
    try:
        page.show_dialog(dialog)
        return
    except AttributeError:
        pass
    try:
        page.open(dialog)  # type: ignore[attr-defined]
    except Exception:
        page.dialog = dialog  # type: ignore[attr-defined]
        try:
            page.update()
        except Exception:
            pass


def how_to_dialog(
    theme: Theme,
    *,
    title: str,
    sections: Sequence[HowToSection],
    close_label: str,
) -> ft.AlertDialog:
    section_blocks: list[ft.Control] = []
    for s in sections:
        section_blocks.append(
            ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Icon(s.icon, color=theme.primary, size=18),
                        width=34,
                        height=34,
                        bgcolor=ft.Colors.with_opacity(0.14, theme.primary),
                        border_radius=10,
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(
                                s.title,
                                color=theme.text,
                                size=14,
                                weight=ft.FontWeight.W_700,
                            ),
                            ft.Text(
                                s.body,
                                color=theme.text_muted,
                                size=12,
                                selectable=True,
                            ),
                        ],
                        spacing=4,
                        tight=True,
                        expand=True,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        )

    body = ft.Container(
        content=ft.Column(
            controls=section_blocks,
            spacing=18,
            tight=True,
            scroll=ft.ScrollMode.ADAPTIVE,
        ),
        width=560,
        padding=ft.padding.only(top=4, bottom=4),
    )

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=theme.surface,
        title=ft.Text(title, color=theme.text, size=18, weight=ft.FontWeight.W_700),
        content=body,
        actions=[
            ft.TextButton(
                content=ft.Text(
                    close_label,
                    color=ft.Colors.WHITE,
                    size=13,
                    weight=ft.FontWeight.W_600,
                ),
                style=ft.ButtonStyle(
                    bgcolor=theme.primary,
                    padding=ft.padding.symmetric(horizontal=18, vertical=10),
                ),
                on_click=lambda e: _close_dialog(e.page) if e.page else None,
            )
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dialog


def open_how_to(
    page: ft.Page,
    theme: Theme,
    *,
    title: str,
    sections: Sequence[HowToSection],
    close_label: str,
) -> None:
    dialog = how_to_dialog(theme, title=title, sections=sections, close_label=close_label)
    _open_dialog(page, dialog)
