"""Templates tab for the AI Legal section.

Two-column rich editor:

* Left  - selectors: 6 templates in a 3x2 grid, 12 colour swatches in
  3 rows of 4, 4 font choices, plus a special "Default - same format as
  input" card explaining the fallback option.
* Right - a live ``A4 preview`` that re-renders whenever any selector
  changes, showing how the document would look with the chosen
  template + accent colour + font.

All choices live in :class:`LegalState` so they survive switching to
another tab / theme / language.
"""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from src.sections.ai_legal.data import COLORS, fonts, templates
from src.sections.ai_legal.state import STATE
from src.sections.ai_legal.strings import s
from src.theme import Theme


def _section_title(theme: Theme, label: str) -> ft.Text:
    return ft.Text(
        label,
        color=theme.text_muted,
        size=11,
        weight=ft.FontWeight.W_700,
    )


def _template_thumb(theme: Theme, *, accent: str, weight: ft.FontWeight) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(height=4, width=44, bgcolor=accent, border_radius=2),
                ft.Container(height=2, width=64, bgcolor=ft.Colors.with_opacity(0.55, theme.text_muted), border_radius=1),
                ft.Container(height=2, width=58, bgcolor=ft.Colors.with_opacity(0.45, theme.text_muted), border_radius=1),
                ft.Container(height=2, width=52, bgcolor=ft.Colors.with_opacity(0.35, theme.text_muted), border_radius=1),
                ft.Container(height=2, width=64, bgcolor=ft.Colors.with_opacity(0.45, theme.text_muted), border_radius=1),
            ],
            spacing=4,
            tight=True,
        ),
        padding=10,
        height=82,
        width=78,
        bgcolor=theme.surface_2,
        border_radius=8,
        alignment=ft.Alignment.CENTER_LEFT,
    )


def _template_card(
    theme: Theme,
    *,
    template: dict,
    active: bool,
    accent: str,
    on_click: Callable[[ft.ControlEvent], None],
) -> ft.Container:
    border_color = theme.primary if active else theme.border
    border_width = 2 if active else 1
    title_row_children: list[ft.Control] = [
        ft.Text(
            template["label"],
            color=theme.text,
            size=13,
            weight=ft.FontWeight.W_700,
            expand=True,
        ),
    ]
    if active:
        title_row_children.append(
            ft.Icon(ft.Icons.CHECK_CIRCLE, color=theme.primary, size=16)
        )
    return ft.Container(
        content=ft.Column(
            controls=[
                _template_thumb(theme, accent=accent, weight=template["heading_weight"]),
                ft.Row(controls=title_row_children, spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Text(
                    template["desc"],
                    color=theme.text_muted,
                    size=11,
                    max_lines=2,
                ),
            ],
            spacing=8,
            tight=True,
        ),
        padding=12,
        bgcolor=theme.surface,
        border_radius=12,
        border=ft.border.all(border_width, border_color),
        ink=True,
        on_click=on_click,
        col={"xs": 6, "md": 4},
    )


def _color_swatch(
    theme: Theme,
    *,
    color: str,
    active: bool,
    on_click: Callable[[ft.ControlEvent], None],
) -> ft.Container:
    inner: ft.Control = ft.Container(
        content=ft.Icon(ft.Icons.CHECK, color=ft.Colors.WHITE, size=14)
        if active
        else None,
        width=32,
        height=32,
        bgcolor=color,
        border_radius=16,
        alignment=ft.Alignment.CENTER,
    )
    border_color = theme.primary if active else theme.border
    return ft.Container(
        content=inner,
        padding=2,
        bgcolor=ft.Colors.with_opacity(0.20, color) if active else "transparent",
        border_radius=18,
        border=ft.border.all(2, border_color),
        ink=True,
        on_click=on_click,
    )


def _font_row(
    theme: Theme,
    *,
    font: dict,
    active: bool,
    on_click: Callable[[ft.ControlEvent], None],
) -> ft.Container:
    border_color = theme.primary if active else theme.border
    border_width = 2 if active else 1
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Text(
                    font["label"],
                    color=theme.text,
                    size=13,
                    weight=ft.FontWeight.W_600,
                    font_family=font["family"],
                    expand=True,
                ),
                ft.Text(
                    s("en")["font_sample"],
                    color=theme.text_muted,
                    size=14,
                    font_family=font["family"],
                ),
                ft.Icon(
                    ft.Icons.CHECK_CIRCLE if active else ft.Icons.RADIO_BUTTON_UNCHECKED,
                    color=theme.primary if active else theme.text_subtle,
                    size=18,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        bgcolor=theme.surface,
        border_radius=10,
        border=ft.border.all(border_width, border_color),
        ink=True,
        on_click=on_click,
    )


def _default_card(
    theme: Theme,
    lang: str,
    *,
    active: bool,
    on_click: Callable[[ft.ControlEvent], None],
) -> ft.Container:
    txt = s(lang)
    accent = "#3B82F6"
    border_color = accent if active else theme.border
    border_width = 2 if active else 1
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.RESTART_ALT, color=accent, size=22),
                    width=44,
                    height=44,
                    bgcolor=ft.Colors.with_opacity(0.15, accent),
                    border_radius=10,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    controls=[
                        ft.Text(
                            txt["templates_section_default_title"],
                            color=theme.text,
                            size=14,
                            weight=ft.FontWeight.W_700,
                        ),
                        ft.Text(
                            txt["templates_section_default_desc"],
                            color=theme.text_muted,
                            size=12,
                            max_lines=2,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                    tight=True,
                ),
                ft.Icon(
                    ft.Icons.CHECK_CIRCLE if active else ft.Icons.RADIO_BUTTON_UNCHECKED,
                    color=accent if active else theme.text_subtle,
                    size=18,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=14,
        bgcolor=ft.Colors.with_opacity(0.06, accent),
        border_radius=12,
        border=ft.border.all(border_width, border_color),
        ink=True,
        on_click=on_click,
    )


def _selected_template(lang: str) -> dict:
    items = templates(lang)
    for tpl in items:
        if tpl["key"] == STATE.selected_template:
            return tpl
    return items[0]


def _selected_font(lang: str) -> dict:
    items = fonts(lang)
    for f in items:
        if f["key"] == STATE.selected_font:
            return f
    return items[0]


def _a4_preview(theme: Theme, lang: str) -> ft.Container:
    txt = s(lang)
    accent = STATE.selected_color
    is_default = STATE.selected_template == "default"
    template = _selected_template(lang) if not is_default else None
    font = _selected_font(lang)

    body_color = "#1E293B"
    muted_color = "#64748B"
    paper_color = "#FDFDFD"

    if is_default:
        accent = "#3B82F6"
        heading_size = 22
        heading_weight = ft.FontWeight.W_700
    else:
        heading_size = template["heading_size"] if template else 22
        heading_weight = template["heading_weight"] if template else ft.FontWeight.W_700

    paragraphs = [
        txt["preview_doc_paragraph_1"],
        txt["preview_doc_paragraph_2"],
        txt["preview_doc_paragraph_3"],
    ]

    column = ft.Column(
        controls=[
            ft.Container(
                height=6,
                width=92,
                bgcolor=accent,
                border_radius=3,
            ),
            ft.Text(
                txt["preview_doc_heading"],
                color=body_color,
                size=heading_size,
                weight=heading_weight,
                font_family=font["family"],
            ),
            ft.Text(
                txt["preview_doc_subheading"],
                color=accent,
                size=13,
                weight=ft.FontWeight.W_600,
                font_family=font["family"],
            ),
            ft.Container(height=4),
            *[
                ft.Text(
                    p,
                    color=body_color,
                    size=12,
                    font_family=font["family"],
                    selectable=True,
                )
                for p in paragraphs
            ],
            ft.Container(expand=True),
            ft.Row(
                controls=[
                    ft.Text(
                        txt["preview_doc_footer"],
                        color=muted_color,
                        size=10,
                        font_family=font["family"],
                    ),
                    ft.Container(expand=True),
                    ft.Container(
                        content=ft.Text(
                            STATE.selected_template.upper() if not is_default else "DEFAULT",
                            color=accent,
                            size=10,
                            weight=ft.FontWeight.W_700,
                            font_family=font["family"],
                        ),
                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                        bgcolor=ft.Colors.with_opacity(0.12, accent),
                        border_radius=4,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ],
        spacing=10,
        tight=False,
        expand=True,
    )

    return ft.Container(
        content=column,
        width=320,
        height=440,
        padding=ft.padding.symmetric(horizontal=24, vertical=22),
        bgcolor=paper_color,
        border_radius=10,
        border=ft.border.all(1, "#CBD5F5"),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=24,
            color=ft.Colors.with_opacity(0.20, ft.Colors.BLACK),
            offset=ft.Offset(0, 8),
        ),
    )


def _btn_primary(theme: Theme, label: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(label, color=ft.Colors.WHITE, size=13, weight=ft.FontWeight.W_600),
        padding=ft.padding.symmetric(horizontal=18, vertical=10),
        bgcolor=theme.primary,
        border_radius=10,
        ink=True,
        on_click=lambda e: None,
        alignment=ft.Alignment.CENTER,
    )


def _btn_secondary(theme: Theme, label: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(label, color=theme.text, size=13, weight=ft.FontWeight.W_500),
        padding=ft.padding.symmetric(horizontal=18, vertical=10),
        bgcolor=theme.surface,
        border_radius=10,
        border=ft.border.all(1, theme.border),
        ink=True,
        on_click=lambda e: None,
        alignment=ft.Alignment.CENTER,
    )


def build_templates_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Optional[Callable[[], None]] = None,
) -> ft.Container:
    txt = s(lang)

    def _trigger_rerender() -> None:
        if on_request_rerender is not None:
            on_request_rerender()

    def _set_template(key: str) -> None:
        if STATE.selected_template == key:
            return
        STATE.selected_template = key
        _trigger_rerender()

    def _set_color(color: str) -> None:
        if STATE.selected_color == color:
            return
        STATE.selected_color = color
        _trigger_rerender()

    def _set_font(key: str) -> None:
        if STATE.selected_font == key:
            return
        STATE.selected_font = key
        _trigger_rerender()

    template_grid = ft.ResponsiveRow(
        controls=[
            _template_card(
                theme,
                template=tpl,
                active=STATE.selected_template == tpl["key"],
                accent=STATE.selected_color,
                on_click=lambda e, k=tpl["key"]: _set_template(k),
            )
            for tpl in templates(lang)
        ],
        spacing=12,
        run_spacing=12,
    )

    color_swatches = ft.Row(
        controls=[
            _color_swatch(
                theme,
                color=c,
                active=STATE.selected_color == c,
                on_click=lambda e, color=c: _set_color(color),
            )
            for c in COLORS
        ],
        spacing=10,
        wrap=True,
        run_spacing=10,
    )

    font_list = ft.Column(
        controls=[
            _font_row(
                theme,
                font=f,
                active=STATE.selected_font == f["key"],
                on_click=lambda e, k=f["key"]: _set_font(k),
            )
            for f in fonts(lang)
        ],
        spacing=8,
        tight=True,
    )

    default_card = _default_card(
        theme,
        lang,
        active=STATE.selected_template == "default",
        on_click=lambda e: _set_template("default"),
    )

    left_column = ft.Column(
        controls=[
            _section_title(theme, txt["templates_section_styles"]),
            template_grid,
            ft.Container(height=4),
            _section_title(theme, txt["templates_section_color"]),
            color_swatches,
            ft.Container(height=4),
            _section_title(theme, txt["templates_section_font"]),
            font_list,
            ft.Container(height=4),
            default_card,
        ],
        spacing=10,
        tight=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True,
    )

    right_column = ft.Column(
        controls=[
            ft.Text(
                txt["preview_title"],
                color=theme.text_muted,
                size=11,
                weight=ft.FontWeight.W_700,
            ),
            ft.Row(
                controls=[_a4_preview(theme, lang)],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    _btn_primary(theme, txt["btn_apply_template"]),
                    _btn_secondary(theme, txt["btn_download_sample"]),
                ],
                spacing=10,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        ],
        spacing=14,
        tight=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    return ft.Container(
        content=ft.ResponsiveRow(
            controls=[
                ft.Container(
                    content=left_column,
                    col={"xs": 12, "md": 7},
                    padding=ft.padding.only(right=16),
                ),
                ft.Container(
                    content=right_column,
                    col={"xs": 12, "md": 5},
                ),
            ],
            spacing=18,
            run_spacing=18,
        ),
        padding=ft.padding.symmetric(horizontal=24, vertical=18),
        expand=True,
    )
