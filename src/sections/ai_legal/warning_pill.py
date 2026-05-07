"""Disclaimer pill shown in the AI Legal header (top-right corner).

The shared ``header`` component only knows about the icon, title,
subtitle and the menu / help buttons. The legal screenshot has an extra
"Important notice — this is not legal advice" panel pinned to the right
of the header. We render that as a small standalone control and stack
it next to the generic header in :mod:`src.sections.ai_legal.view` so we
don't have to widen the shared header API for a single section.
"""

from __future__ import annotations

import flet as ft

from src.sections.ai_legal.strings import s
from src.theme import Theme


def warning_pill(theme: Theme, lang: str) -> ft.Container:
    txt = s(lang)
    accent = "#F59E0B"
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.SHIELD_OUTLINED,
                        color=accent,
                        size=18,
                    ),
                    width=32,
                    height=32,
                    bgcolor=ft.Colors.with_opacity(0.15, accent),
                    border_radius=8,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    controls=[
                        ft.Text(
                            txt["warning_pill_title"],
                            color=theme.text,
                            size=12,
                            weight=ft.FontWeight.W_700,
                        ),
                        ft.Text(
                            txt["warning_pill_text"],
                            color=theme.text_muted,
                            size=11,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=2,
                    tight=True,
                    expand=True,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=290,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        bgcolor=ft.Colors.with_opacity(0.08, accent),
        border=ft.border.all(1, ft.Colors.with_opacity(0.25, accent)),
        border_radius=10,
    )
