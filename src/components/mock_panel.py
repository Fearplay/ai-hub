"""Light mock panels for tabs that aren't wired to AI yet.

Two flavors:

* :func:`mock_form_panel`     - hero card + form fields + primary button.
  Used for "writer" / "generator" style tabs (Form mode, Social posts,
  Ads, Email campaigns, Budget, Summarise topic, ...).
* :func:`mock_card_grid_panel`- hero card + a wrap-grid of mock cards.
  Used for gallery-ish tabs (Templates, Quizzes, Calculators, Sources).

The chrome (hero card + scrollable body) is shared so every section feels
the same when you click between tabs.
"""

from __future__ import annotations

from typing import Optional, Sequence

import flet as ft

from src.i18n import t
from src.theme import Theme


def _hero_card(theme: Theme, *, icon: str, title: str, description: str) -> ft.Container:
    icon_box = ft.Container(
        content=ft.Icon(icon, color=ft.Colors.WHITE, size=20),
        width=44,
        height=44,
        bgcolor=theme.primary,
        border_radius=12,
        alignment=ft.Alignment.CENTER,
    )
    text_col = ft.Column(
        controls=[
            ft.Text(
                title,
                color=theme.text,
                size=16,
                weight=ft.FontWeight.W_700,
            ),
            ft.Text(
                description,
                color=theme.text_muted,
                size=12,
            ),
        ],
        spacing=4,
        tight=True,
        expand=True,
    )
    return ft.Container(
        content=ft.Row(
            controls=[icon_box, text_col],
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=16,
        bgcolor=ft.Colors.with_opacity(0.35, theme.primary_tint),
        border_radius=12,
        border=ft.border.all(1, ft.Colors.with_opacity(0.35, theme.primary)),
    )


def _in_preparation_pill(theme: Theme, lang: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.HOURGLASS_EMPTY_ROUNDED, color=theme.primary, size=14),
                ft.Text(
                    t("mock_in_preparation", lang),
                    color=theme.text_muted,
                    size=12,
                    italic=True,
                    expand=True,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        bgcolor=theme.surface,
        border_radius=10,
        border=ft.border.all(1, theme.border),
    )


def _text_field(theme: Theme, *, label: str, hint: str, multiline: bool = False) -> ft.Container:
    field = ft.TextField(
        hint_text=hint,
        hint_style=ft.TextStyle(color=theme.text_muted, size=13),
        text_style=ft.TextStyle(color=theme.text, size=13),
        border=ft.InputBorder.NONE,
        filled=False,
        bgcolor="transparent",
        cursor_color=theme.primary,
        content_padding=ft.padding.symmetric(horizontal=4, vertical=8),
        multiline=multiline,
        min_lines=3 if multiline else 1,
        max_lines=6 if multiline else 1,
        expand=True,
    )
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(label, color=theme.text_muted, size=11, weight=ft.FontWeight.W_500),
                ft.Container(
                    content=field,
                    padding=ft.padding.symmetric(horizontal=10, vertical=2),
                    bgcolor=theme.surface,
                    border_radius=10,
                    border=ft.border.all(1, theme.border),
                ),
            ],
            spacing=6,
            tight=True,
        ),
    )


def _primary_button(theme: Theme, label: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.WHITE, size=16),
                ft.Text(label, color=ft.Colors.WHITE, size=13, weight=ft.FontWeight.W_600),
            ],
            spacing=8,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=18, vertical=12),
        bgcolor=theme.primary,
        border_radius=10,
        ink=True,
        on_click=lambda e: None,
        alignment=ft.Alignment.CENTER,
    )


def _secondary_button(theme: Theme, label: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.BOOKMARK_BORDER, color=theme.text, size=16),
                ft.Text(label, color=theme.text, size=13, weight=ft.FontWeight.W_500),
            ],
            spacing=8,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=12),
        bgcolor=theme.surface,
        border_radius=10,
        border=ft.border.all(1, theme.border),
        ink=True,
        on_click=lambda e: None,
        alignment=ft.Alignment.CENTER,
    )


def _examples_card(theme: Theme, lang: str, examples: Sequence[str]) -> ft.Container:
    bullets = [
        ft.Row(
            controls=[
                ft.Icon(ft.Icons.AUTO_AWESOME, color=theme.primary, size=14),
                ft.Text(line, color=theme.text, size=12, expand=True, selectable=True),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
        for line in examples
    ]
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    t("mock_examples_title", lang),
                    color=theme.text_muted,
                    size=11,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Column(controls=bullets, spacing=8, tight=True),
            ],
            spacing=10,
            tight=True,
        ),
        padding=14,
        bgcolor=theme.surface,
        border_radius=12,
        border=ft.border.all(1, theme.border),
    )


def mock_form_panel(
    theme: Theme,
    lang: str,
    *,
    icon: str,
    title: str,
    description: str,
    fields: Sequence[dict],
    button_label: Optional[str] = None,
    secondary_label: Optional[str] = None,
    examples: Optional[Sequence[str]] = None,
) -> ft.Container:
    """Hero + form column. ``fields`` items: ``{"label", "hint", "multiline"?}``."""
    primary_label = button_label or t("mock_btn_generate", lang)
    save_label = secondary_label or t("mock_btn_save_draft", lang)

    field_controls = [
        _text_field(
            theme,
            label=f["label"],
            hint=f.get("hint", ""),
            multiline=bool(f.get("multiline", False)),
        )
        for f in fields
    ]

    actions_row = ft.Row(
        controls=[_primary_button(theme, primary_label), _secondary_button(theme, save_label)],
        spacing=10,
        wrap=True,
        run_spacing=10,
    )

    form_column = ft.Column(
        controls=[
            *field_controls,
            actions_row,
        ],
        spacing=14,
        tight=True,
        expand=True,
    )

    body_controls: list[ft.Control] = [ft.Container(content=form_column, expand=True)]
    if examples:
        body_controls.append(
            ft.Container(
                content=_examples_card(theme, lang, examples),
                width=240,
            )
        )

    body_row = ft.Row(
        controls=body_controls,
        spacing=18,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                _hero_card(theme, icon=icon, title=title, description=description),
                _in_preparation_pill(theme, lang),
                body_row,
            ],
            spacing=14,
            tight=True,
            scroll=ft.ScrollMode.ADAPTIVE,
            expand=True,
        ),
        padding=ft.padding.symmetric(horizontal=24, vertical=20),
        expand=True,
    )


def _grid_card(theme: Theme, card: dict) -> ft.Container:
    badge = ft.Container(
        content=ft.Icon(card["icon"], color=ft.Colors.WHITE, size=18),
        width=36,
        height=36,
        bgcolor=card.get("color") or theme.primary,
        border_radius=10,
        alignment=ft.Alignment.CENTER,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[badge],
                    spacing=0,
                    tight=True,
                ),
                ft.Text(
                    card["title"],
                    color=theme.text,
                    size=13,
                    weight=ft.FontWeight.W_600,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    card["description"],
                    color=theme.text_muted,
                    size=11,
                    max_lines=3,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Row(
                    controls=[
                        ft.Text(
                            card.get("action_label", ""),
                            color=theme.primary,
                            size=12,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Icon(ft.Icons.CHEVRON_RIGHT, color=theme.primary, size=14),
                    ],
                    spacing=2,
                    tight=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=10,
            tight=True,
        ),
        padding=14,
        bgcolor=theme.surface,
        border_radius=12,
        border=ft.border.all(1, theme.border),
        width=220,
        height=160,
        ink=True,
        on_click=lambda e: None,
    )


def mock_card_grid_panel(
    theme: Theme,
    lang: str,
    *,
    icon: str,
    title: str,
    description: str,
    cards: Sequence[dict],
) -> ft.Container:
    """Hero + responsive grid. ``cards`` items: ``{"icon", "title", "description", "action_label", "color"?}``."""
    grid = ft.Row(
        controls=[_grid_card(theme, card) for card in cards],
        spacing=14,
        wrap=True,
        run_spacing=14,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                _hero_card(theme, icon=icon, title=title, description=description),
                _in_preparation_pill(theme, lang),
                grid,
            ],
            spacing=14,
            tight=True,
            scroll=ft.ScrollMode.ADAPTIVE,
            expand=True,
        ),
        padding=ft.padding.symmetric(horizontal=24, vertical=20),
        expand=True,
    )
