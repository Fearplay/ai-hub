"""AI Finance - right-hand context panel.

Four cards:

1. Rychlé akce - 5 link-style rows with chevrons.
2. Přehled trhů - 5 ticker rows with inline sparklines (canvas Path).
3. Nedávné analýzy - 4 history-like rows.
4. Tip dne - icon + paragraph.
"""

from __future__ import annotations

import flet as ft
from flet import canvas as cv

from src.components.context_panel import context_panel_shell, history_row, quick_action_row
from src.components.section_card import section_card
from src.sections.ai_finance.data import (
    TREND_DOWN,
    TREND_UP,
    daily_tip,
    market_tickers,
    quick_actions,
    recent_analyses,
)
from src.sections.ai_finance.strings import s
from src.theme import Theme


SPARK_WIDTH = 64
SPARK_HEIGHT = 26


def _quick_actions_card(theme: Theme, lang: str) -> ft.Container:
    txt = s(lang)
    rows = [quick_action_row(theme, a["icon"], a["label"]) for a in quick_actions(lang)]
    return section_card(
        theme,
        ft.Icons.BOLT_OUTLINED,
        txt["quick_title"],
        ft.Column(controls=rows, spacing=2, tight=True),
    )


def _sparkline(values: list[float], *, color: str) -> cv.Canvas:
    if not values:
        return cv.Canvas(shapes=[], width=SPARK_WIDTH, height=SPARK_HEIGHT)

    lo = min(values)
    hi = max(values)
    span = (hi - lo) or 1.0

    margin_y = 3
    plot_h = SPARK_HEIGHT - 2 * margin_y
    step_x = SPARK_WIDTH / max(1, len(values) - 1)

    elements: list[cv.Path.PathElement] = []
    for i, v in enumerate(values):
        x = i * step_x
        y = margin_y + (1 - (v - lo) / span) * plot_h
        if i == 0:
            elements.append(cv.Path.MoveTo(x, y))
        else:
            elements.append(cv.Path.LineTo(x, y))

    line = cv.Path(
        elements=elements,
        paint=ft.Paint(
            color=color,
            style=ft.PaintingStyle.STROKE,
            stroke_width=1.6,
            stroke_cap=ft.StrokeCap.ROUND,
            stroke_join=ft.StrokeJoin.ROUND,
        ),
    )
    return cv.Canvas(shapes=[line], width=SPARK_WIDTH, height=SPARK_HEIGHT)


def _ticker_row(theme: Theme, ticker: dict) -> ft.Container:
    trend_color = TREND_UP if ticker["trend"] == "up" else TREND_DOWN

    icon_box = ft.Container(
        content=ft.Icon(ticker["icon"], color=ft.Colors.WHITE, size=14),
        width=28,
        height=28,
        bgcolor=ticker["icon_color"],
        border_radius=8,
        alignment=ft.Alignment.CENTER,
    )

    name_value = ft.Column(
        controls=[
            ft.Text(
                ticker["symbol"],
                color=theme.text,
                size=12,
                weight=ft.FontWeight.W_600,
                overflow=ft.TextOverflow.ELLIPSIS,
                max_lines=1,
            ),
            ft.Text(
                ticker["value"],
                color=theme.text_muted,
                size=11,
                weight=ft.FontWeight.W_500,
            ),
        ],
        spacing=2,
        tight=True,
        expand=True,
    )

    spark = _sparkline(ticker["spark"], color=trend_color)

    change = ft.Text(
        ticker["change"],
        color=trend_color,
        size=11,
        weight=ft.FontWeight.W_700,
    )

    return ft.Container(
        content=ft.Row(
            controls=[icon_box, name_value, spark, change],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=4, vertical=6),
        border_radius=8,
        ink=True,
        on_click=lambda e: None,
    )


def _markets_card(theme: Theme, lang: str) -> ft.Container:
    txt = s(lang)
    rows = [_ticker_row(theme, t) for t in market_tickers(lang)]
    content = ft.Column(controls=rows, spacing=4, tight=True)
    return section_card(
        theme,
        ft.Icons.SHOW_CHART,
        txt["markets_title"],
        content,
        action_label=txt["markets_show_detail"],
    )


def _analyses_card(theme: Theme, lang: str) -> ft.Container:
    txt = s(lang)
    rows = [
        history_row(theme, item["title"], item["time"])
        for item in recent_analyses(lang)
    ]
    content = ft.Column(controls=rows, spacing=4, tight=True)
    return section_card(
        theme,
        ft.Icons.HISTORY,
        txt["analyses_title"],
        content,
        action_label=txt["analyses_show_all"],
    )


def _tip_card(theme: Theme, lang: str) -> ft.Container:
    tip = daily_tip(lang)
    body = ft.Text(
        tip["text"],
        color=theme.text,
        size=12,
        selectable=True,
    )
    return section_card(
        theme,
        ft.Icons.LIGHTBULB_OUTLINE,
        tip["title"],
        body,
    )


def build_context(theme: Theme, lang: str) -> ft.Container:
    return context_panel_shell(
        theme,
        _quick_actions_card(theme, lang),
        _markets_card(theme, lang),
        _analyses_card(theme, lang),
        _tip_card(theme, lang),
    )
