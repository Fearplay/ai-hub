"""AI Finance - main center view (matches the design screenshot)."""

from __future__ import annotations

import math

import flet as ft
from flet import canvas as cv

from src.components.chat_input import chat_input
from src.components.chat_message import chat_message
from src.components.header import header
from src.components.tab_bar import tab_bar
from src.sections.ai_finance.data import (
    SECTION_ICON,
    assistant_actions,
    budget_donut,
    budget_table,
    tabs,
)
from src.sections.ai_finance.strings import s
from src.theme import Theme


DONUT_SIZE = 180
DONUT_STROKE = 22


def _donut_arc(*, color: str, start: float, sweep: float) -> cv.Arc:
    inset = DONUT_STROKE / 2 + 2
    bound = DONUT_SIZE - 2 * inset
    return cv.Arc(
        x=inset,
        y=inset,
        width=bound,
        height=bound,
        start_angle=start,
        sweep_angle=sweep,
        paint=ft.Paint(
            color=color,
            style=ft.PaintingStyle.STROKE,
            stroke_width=DONUT_STROKE,
            stroke_cap=ft.StrokeCap.BUTT,
        ),
    )


def _donut_chart(theme: Theme, slices: list[dict]) -> ft.Stack:
    track = cv.Arc(
        x=DONUT_STROKE / 2 + 2,
        y=DONUT_STROKE / 2 + 2,
        width=DONUT_SIZE - 2 * (DONUT_STROKE / 2 + 2),
        height=DONUT_SIZE - 2 * (DONUT_STROKE / 2 + 2),
        start_angle=0,
        sweep_angle=2 * math.pi,
        paint=ft.Paint(
            color=theme.surface_2,
            style=ft.PaintingStyle.STROKE,
            stroke_width=DONUT_STROKE,
        ),
    )

    arcs: list[cv.Shape] = [track]
    angle = -math.pi / 2  # start at the top
    total = sum(slc["percent"] for slc in slices) or 1
    for slc in slices:
        sweep = (slc["percent"] / total) * 2 * math.pi
        arcs.append(_donut_arc(color=slc["color"], start=angle, sweep=sweep - 0.012))
        angle += sweep

    canvas = cv.Canvas(shapes=arcs, width=DONUT_SIZE, height=DONUT_SIZE)
    return canvas


def _donut_with_caption(theme: Theme, lang: str, slices: list[dict]) -> ft.Stack:
    txt = s(lang)
    caption = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    txt["donut_caption_top"],
                    color=theme.text,
                    size=18,
                    weight=ft.FontWeight.W_700,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    txt["donut_caption_bottom"],
                    color=theme.text_muted,
                    size=11,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=2,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=DONUT_SIZE,
        height=DONUT_SIZE,
        alignment=ft.Alignment.CENTER,
    )

    return ft.Stack(
        controls=[_donut_chart(theme, slices), caption],
        width=DONUT_SIZE,
        height=DONUT_SIZE,
    )


def _legend_row(theme: Theme, slc: dict) -> ft.Row:
    dot = ft.Container(
        width=10,
        height=10,
        bgcolor=slc["color"],
        border_radius=5,
    )
    label_col = ft.Column(
        controls=[
            ft.Text(
                slc["label"],
                color=theme.text,
                size=13,
                weight=ft.FontWeight.W_600,
            ),
            ft.Text(
                slc["note"],
                color=theme.text_muted,
                size=11,
                overflow=ft.TextOverflow.ELLIPSIS,
                max_lines=1,
            ),
        ],
        spacing=2,
        tight=True,
        expand=True,
    )
    value = ft.Text(
        slc["value"],
        color=theme.text,
        size=13,
        weight=ft.FontWeight.W_600,
    )
    return ft.Row(
        controls=[dot, label_col, value],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _legend(theme: Theme, slices: list[dict]) -> ft.Column:
    return ft.Column(
        controls=[_legend_row(theme, slc) for slc in slices],
        spacing=14,
        tight=True,
        expand=True,
    )


def _budget_block(theme: Theme, lang: str) -> ft.Column:
    txt = s(lang)
    slices = budget_donut(lang)

    heading = ft.Row(
        controls=[
            ft.Icon(ft.Icons.PIE_CHART_OUTLINE, color=theme.primary, size=16),
            ft.Text(
                txt["budget_title"],
                color=theme.primary,
                size=14,
                weight=ft.FontWeight.W_700,
            ),
        ],
        spacing=6,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    subtitle = ft.Text(txt["budget_subtitle"], color=theme.text_muted, size=12)

    body = ft.Row(
        controls=[
            _donut_with_caption(theme, lang, slices),
            ft.Container(content=_legend(theme, slices), expand=True),
        ],
        spacing=18,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    return ft.Column(
        controls=[heading, subtitle, body],
        spacing=10,
        tight=True,
    )


def _table_cell(text: str, *, color: str, weight: ft.FontWeight, size: int = 12, expand: int = 1) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            text,
            color=color,
            size=size,
            weight=weight,
            overflow=ft.TextOverflow.ELLIPSIS,
            max_lines=1,
        ),
        expand=expand,
        padding=ft.padding.symmetric(horizontal=2, vertical=2),
    )


def _table_header(theme: Theme, lang: str) -> ft.Container:
    txt = s(lang)
    return ft.Container(
        content=ft.Row(
            controls=[
                _table_cell(txt["col_category"], color=theme.text_muted, weight=ft.FontWeight.W_600, expand=4),
                _table_cell(txt["col_recommended"], color=theme.text_muted, weight=ft.FontWeight.W_600, expand=2),
                _table_cell(txt["col_amount"], color=theme.text_muted, weight=ft.FontWeight.W_600, expand=3),
                _table_cell(txt["col_note"], color=theme.text_muted, weight=ft.FontWeight.W_600, expand=4),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.only(left=4, right=4, top=8, bottom=8),
        border=ft.border.only(bottom=ft.BorderSide(1, theme.border)),
    )


def _table_row(theme: Theme, row: dict) -> ft.Container:
    category_cell = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(row["icon"], color=row["color"], size=14),
                ft.Text(
                    row["category"],
                    color=row["color"],
                    size=12,
                    weight=ft.FontWeight.W_600,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    max_lines=1,
                ),
            ],
            spacing=6,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        expand=4,
        padding=ft.padding.symmetric(horizontal=2, vertical=2),
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                category_cell,
                _table_cell(row["recommended"], color=theme.text, weight=ft.FontWeight.W_500, expand=2),
                _table_cell(row["amount"], color=theme.text, weight=ft.FontWeight.W_500, expand=3),
                _table_cell(row["note"], color=theme.text_muted, weight=ft.FontWeight.W_400, expand=4),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.only(left=4, right=4, top=10, bottom=10),
        border=ft.border.only(bottom=ft.BorderSide(1, theme.border)),
    )


def _breakdown_block(theme: Theme, lang: str) -> ft.Column:
    txt = s(lang)
    rows = [_table_row(theme, row) for row in budget_table(lang)]

    return ft.Column(
        controls=[
            ft.Text(
                txt["breakdown_title"],
                color=theme.primary,
                size=13,
                weight=ft.FontWeight.W_700,
            ),
            ft.Container(
                content=ft.Column(
                    controls=[_table_header(theme, lang), *rows],
                    spacing=0,
                    tight=True,
                ),
                bgcolor=theme.surface,
                border_radius=10,
                border=ft.border.all(1, theme.border),
                padding=ft.padding.symmetric(horizontal=10, vertical=2),
            ),
        ],
        spacing=10,
        tight=True,
    )


def _action_chip(theme: Theme, icon: str, label: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=theme.primary, size=14),
                ft.Text(label, color=theme.text, size=12, weight=ft.FontWeight.W_500),
            ],
            spacing=6,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        bgcolor=theme.surface,
        border_radius=20,
        border=ft.border.all(1, theme.border),
        ink=True,
        on_click=lambda e: None,
    )


def _assistant_message(theme: Theme, lang: str) -> ft.Row:
    txt = s(lang)

    bubble = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(txt["msg2_intro"], color=theme.text, size=14, selectable=True),
                _budget_block(theme, lang),
                _breakdown_block(theme, lang),
            ],
            spacing=18,
            tight=True,
        ),
        padding=18,
        bgcolor=theme.assistant_bubble,
        border_radius=14,
    )

    actions_row = ft.Row(
        controls=[_action_chip(theme, a["icon"], a["label"]) for a in assistant_actions(lang)],
        spacing=8,
        wrap=True,
        run_spacing=8,
    )

    avatar = ft.Container(
        content=ft.Icon(SECTION_ICON, color=ft.Colors.WHITE, size=18),
        width=36,
        height=36,
        bgcolor=theme.primary,
        border_radius=10,
        alignment=ft.Alignment.CENTER,
    )

    body = ft.Column(
        controls=[
            ft.Container(
                content=ft.Text("10:28", color=theme.text_muted, size=11),
                padding=ft.padding.only(left=4),
            ),
            bubble,
            actions_row,
        ],
        spacing=10,
        expand=True,
        tight=True,
    )

    return ft.Row(
        controls=[avatar, body],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def build_view(theme: Theme, lang: str) -> ft.Column:
    txt = s(lang)

    user_msg = chat_message(
        theme,
        lang,
        avatar_icon=SECTION_ICON,
        role="user",
        time="10:28",
        text=txt["msg1_user"],
    )

    messages_list = ft.ListView(
        controls=[
            user_msg,
            _assistant_message(theme, lang),
        ],
        spacing=22,
        padding=ft.padding.symmetric(horizontal=24, vertical=20),
        expand=True,
        auto_scroll=False,
    )

    return ft.Column(
        controls=[
            header(
                theme,
                lang,
                icon=SECTION_ICON,
                title=txt["title"],
                subtitle=txt["subtitle"],
            ),
            tab_bar(theme, tabs=tabs(lang), active_index=0),
            messages_list,
            chat_input(theme, lang),
        ],
        spacing=0,
        expand=True,
        tight=True,
    )
