"""AI Finance - main center view (matches the design screenshot).

Chat tab keeps the donut + breakdown layout; the seven other tabs use
the shared mock helpers so every Finance topic feels populated even
before any AI is wired up.
"""

from __future__ import annotations

import math

import flet as ft
from flet import canvas as cv

from src.components.chat_input import chat_input
from src.components.chat_message import chat_message
from src.components.header import header
from src.components.mock_panel import mock_card_grid_panel, mock_form_panel
from src.components.tabbed_panel import tabbed_panel
from src.i18n import t
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


def _chat_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    user_msg = chat_message(
        theme,
        lang,
        avatar_icon=SECTION_ICON,
        role="user",
        time="10:28",
        text=txt["msg1_user"],
    )

    return ft.ListView(
        controls=[user_msg, _assistant_message(theme, lang)],
        spacing=22,
        padding=ft.padding.symmetric(horizontal=24, vertical=20),
        expand=True,
        auto_scroll=False,
    )


def _budget_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
        title=txt["budget_mock_title"],
        description=txt["budget_mock_desc"],
        fields=[
            {"label": txt["budget_field_income"], "hint": txt["budget_field_income_hint"]},
            {"label": txt["budget_field_savings"], "hint": txt["budget_field_savings_hint"]},
            {"label": txt["budget_field_essentials"], "hint": txt["budget_field_essentials_hint"], "multiline": True},
            {"label": txt["budget_field_lifestyle"], "hint": txt["budget_field_lifestyle_hint"]},
        ],
        examples=[txt["budget_example_1"], txt["budget_example_2"], txt["budget_example_3"]],
    )


def _invest_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=ft.Icons.TRENDING_UP,
        title=txt["invest_title"],
        description=txt["invest_desc"],
        fields=[
            {"label": txt["invest_field_amount"], "hint": txt["invest_field_amount_hint"]},
            {"label": txt["invest_field_horizon"], "hint": txt["invest_field_horizon_hint"]},
            {"label": txt["invest_field_risk"], "hint": txt["invest_field_risk_hint"]},
            {"label": txt["invest_field_focus"], "hint": txt["invest_field_focus_hint"]},
        ],
        examples=[txt["invest_example_1"], txt["invest_example_2"], txt["invest_example_3"]],
    )


def _analysis_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=ft.Icons.QUERY_STATS,
        title=txt["analysis_title"],
        description=txt["analysis_desc"],
        fields=[
            {"label": txt["analysis_field_period"], "hint": txt["analysis_field_period_hint"]},
            {"label": txt["analysis_field_focus"], "hint": txt["analysis_field_focus_hint"]},
            {"label": txt["analysis_field_goal"], "hint": txt["analysis_field_goal_hint"], "multiline": True},
        ],
        examples=[txt["analysis_example_1"], txt["analysis_example_2"], txt["analysis_example_3"]],
    )


def _taxes_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=ft.Icons.RECEIPT_LONG_OUTLINED,
        title=txt["taxes_title"],
        description=txt["taxes_desc"],
        fields=[
            {"label": txt["taxes_field_country"], "hint": txt["taxes_field_country_hint"]},
            {"label": txt["taxes_field_status"], "hint": txt["taxes_field_status_hint"]},
            {"label": txt["taxes_field_year"], "hint": txt["taxes_field_year_hint"]},
            {"label": txt["taxes_field_notes"], "hint": txt["taxes_field_notes_hint"], "multiline": True},
        ],
        examples=[txt["taxes_example_1"], txt["taxes_example_2"], txt["taxes_example_3"]],
    )


def _insurance_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=ft.Icons.SHIELD_OUTLINED,
        title=txt["insurance_title"],
        description=txt["insurance_desc"],
        fields=[
            {"label": txt["insurance_field_household"], "hint": txt["insurance_field_household_hint"]},
            {"label": txt["insurance_field_assets"], "hint": txt["insurance_field_assets_hint"]},
            {"label": txt["insurance_field_existing"], "hint": txt["insurance_field_existing_hint"]},
            {"label": txt["insurance_field_concerns"], "hint": txt["insurance_field_concerns_hint"], "multiline": True},
        ],
        examples=[txt["insurance_example_1"], txt["insurance_example_2"], txt["insurance_example_3"]],
    )


def _calculators_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    cards = [
        {
            "icon": ft.Icons.TIMELINE,
            "title": txt["calc_compound_title"],
            "description": txt["calc_compound_desc"],
            "action_label": t("show_all", lang),
            "color": "#22C55E",
        },
        {
            "icon": ft.Icons.HOME_OUTLINED,
            "title": txt["calc_mortgage_title"],
            "description": txt["calc_mortgage_desc"],
            "action_label": t("show_all", lang),
            "color": "#3B82F6",
        },
        {
            "icon": ft.Icons.PAYMENTS_OUTLINED,
            "title": txt["calc_loan_title"],
            "description": txt["calc_loan_desc"],
            "action_label": t("show_all", lang),
            "color": "#F59E0B",
        },
        {
            "icon": ft.Icons.ELDERLY,
            "title": txt["calc_retirement_title"],
            "description": txt["calc_retirement_desc"],
            "action_label": t("show_all", lang),
            "color": "#EF4444",
        },
        {
            "icon": ft.Icons.CURRENCY_EXCHANGE,
            "title": txt["calc_currency_title"],
            "description": txt["calc_currency_desc"],
            "action_label": t("show_all", lang),
            "color": "#0EA5E9",
        },
        {
            "icon": ft.Icons.SAVINGS_OUTLINED,
            "title": txt["calc_savings_title"],
            "description": txt["calc_savings_desc"],
            "action_label": t("show_all", lang),
            "color": "#A78BFA",
        },
    ]
    return mock_card_grid_panel(
        theme,
        lang,
        icon=ft.Icons.CALCULATE_OUTLINED,
        title=txt["calc_title"],
        description=txt["calc_desc"],
        cards=cards,
    )


def _templates_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    cards = [
        {
            "icon": ft.Icons.PIE_CHART_OUTLINE,
            "title": txt["fin_tpl_budget_title"],
            "description": txt["fin_tpl_budget_desc"],
            "action_label": txt["fin_tpl_use"],
            "color": "#22C55E",
        },
        {
            "icon": ft.Icons.SHOW_CHART,
            "title": txt["fin_tpl_invest_title"],
            "description": txt["fin_tpl_invest_desc"],
            "action_label": txt["fin_tpl_use"],
            "color": "#3B82F6",
        },
        {
            "icon": ft.Icons.CREDIT_CARD,
            "title": txt["fin_tpl_debt_title"],
            "description": txt["fin_tpl_debt_desc"],
            "action_label": txt["fin_tpl_use"],
            "color": "#F59E0B",
        },
        {
            "icon": ft.Icons.HEALTH_AND_SAFETY,
            "title": txt["fin_tpl_emergency_title"],
            "description": txt["fin_tpl_emergency_desc"],
            "action_label": txt["fin_tpl_use"],
            "color": "#EF4444",
        },
    ]
    return mock_card_grid_panel(
        theme,
        lang,
        icon=ft.Icons.GRID_VIEW_OUTLINED,
        title=txt["fin_tpl_title"],
        description=txt["fin_tpl_desc"],
        cards=cards,
    )


def build_view(theme: Theme, lang: str) -> ft.Column:
    txt = s(lang)

    panels = [
        _chat_panel(theme, lang),
        _budget_panel(theme, lang),
        _invest_panel(theme, lang),
        _analysis_panel(theme, lang),
        _taxes_panel(theme, lang),
        _insurance_panel(theme, lang),
        _calculators_panel(theme, lang),
        _templates_panel(theme, lang),
    ]

    return ft.Column(
        controls=[
            header(
                theme,
                lang,
                icon=SECTION_ICON,
                title=txt["title"],
                subtitle=txt["subtitle"],
            ),
            tabbed_panel(theme, tabs=tabs(lang), panels=panels),
            chat_input(theme, lang),
        ],
        spacing=0,
        expand=True,
        tight=True,
    )
