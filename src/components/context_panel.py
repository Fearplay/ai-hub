"""Pravý sloupec - Kontext, Rychlé akce, Historie konverzace."""

from __future__ import annotations

import flet as ft

from src.components.document_chip import document_chip
from src.components.section_card import section_card
from src.data.mock import CONTEXT_DOCS, CONVO_HISTORY, QUICK_ACTIONS
from src.theme import Theme


def _add_document_button(theme: Theme) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.ADD, color=theme.primary, size=16),
                ft.Text(
                    "Přidat dokument",
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


def _quick_action_row(theme: Theme, icon: str, label: str) -> ft.Container:
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


def _history_row(theme: Theme, title: str, time: str) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    title,
                    color=theme.text,
                    size=13,
                    weight=ft.FontWeight.W_500,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    max_lines=1,
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


def context_panel(theme: Theme) -> ft.Container:
    docs_content = ft.Column(
        controls=[
            ft.Text(
                "Připojené dokumenty",
                color=theme.text_muted,
                size=11,
                weight=ft.FontWeight.W_500,
            ),
            *[
                document_chip(theme, d["name"], d["type"], d["size"])
                for d in CONTEXT_DOCS
            ],
            _add_document_button(theme),
        ],
        spacing=10,
        tight=True,
    )

    actions_content = ft.Column(
        controls=[
            _quick_action_row(theme, qa["icon"], qa["label"])
            for qa in QUICK_ACTIONS
        ],
        spacing=2,
        tight=True,
    )

    history_content = ft.Column(
        controls=[
            _history_row(theme, h["title"], h["time"])
            for h in CONVO_HISTORY
        ],
        spacing=4,
        tight=True,
    )

    cards = ft.Column(
        controls=[
            section_card(
                theme,
                ft.Icons.INFO_OUTLINE,
                "Kontext",
                docs_content,
                action_label="Spravovat",
            ),
            section_card(
                theme,
                ft.Icons.BOLT_OUTLINED,
                "Rychlé akce",
                actions_content,
            ),
            section_card(
                theme,
                ft.Icons.HISTORY,
                "Historie konverzace",
                history_content,
                action_label="Zobrazit vše",
            ),
        ],
        spacing=16,
        tight=True,
        scroll=ft.ScrollMode.ADAPTIVE,
    )

    return ft.Container(
        content=cards,
        width=336,
        padding=16,
        bgcolor=theme.bg,
        border=ft.border.only(left=ft.BorderSide(1, theme.border)),
    )
