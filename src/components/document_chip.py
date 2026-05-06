"""Řádek se souborem (PDF/DOCX) - používá se v Kontextu i jako příloha."""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from src.theme import Theme


def file_type_color(theme: Theme, ext: str) -> str:
    return theme.file_pdf if ext.upper() == "PDF" else theme.file_docx


def file_type_icon(ext: str) -> str:
    return ft.Icons.PICTURE_AS_PDF if ext.upper() == "PDF" else ft.Icons.DESCRIPTION


def file_badge(theme: Theme, ext: str, *, size: int = 36) -> ft.Container:
    return ft.Container(
        content=ft.Icon(file_type_icon(ext), color=ft.Colors.WHITE, size=int(size * 0.5)),
        width=size,
        height=size,
        bgcolor=file_type_color(theme, ext),
        border_radius=8,
        alignment=ft.Alignment.CENTER,
    )


def document_chip(
    theme: Theme,
    name: str,
    ext: str,
    size: str,
    *,
    on_remove: Optional[Callable[[ft.ControlEvent], None]] = None,
) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                file_badge(theme, ext),
                ft.Column(
                    controls=[
                        ft.Text(
                            name,
                            color=theme.text,
                            size=13,
                            weight=ft.FontWeight.W_500,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            max_lines=1,
                        ),
                        ft.Text(
                            f"{ext.upper()} • {size}",
                            color=theme.text_muted,
                            size=11,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_color=theme.text_muted,
                    icon_size=16,
                    on_click=on_remove,
                    tooltip="Odebrat",
                    style=ft.ButtonStyle(
                        padding=ft.padding.all(4),
                    ),
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        bgcolor=theme.surface_2,
        border_radius=10,
    )
