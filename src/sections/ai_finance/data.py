"""Mock data for the AI Finance section."""

from __future__ import annotations

from src.qt.icons import Icons
from src.sections.ai_finance.strings import s


SECTION_ICON = Icons.SAVINGS_OUTLINED

ACCENT = "#22C55E"
NEEDS_COLOR = "#22C55E"
WANTS_COLOR = "#3B82F6"
SAVING_COLOR = "#F59E0B"
TREND_UP = "#22C55E"
TREND_DOWN = "#EF4444"


def tabs(lang: str) -> list[str]:
    txt = s(lang)
    return [
        txt["tab_chat"],
        txt["tab_budget"],
        txt["tab_invest"],
        txt["tab_analysis"],
        txt["tab_taxes"],
        txt["tab_insurance"],
        txt["tab_calculators"],
        txt["tab_templates"],
    ]


def budget_donut(lang: str) -> list[dict]:
    """Three slices used by the donut chart and the legend on its right."""
    txt = s(lang)
    return [
        {
            "label": txt["needs_label"],
            "value": txt["needs_value"],
            "note": txt["needs_note"],
            "percent": 50,
            "color": NEEDS_COLOR,
        },
        {
            "label": txt["wants_label"],
            "value": txt["wants_value"],
            "note": txt["wants_note"],
            "percent": 30,
            "color": WANTS_COLOR,
        },
        {
            "label": txt["saving_label"],
            "value": txt["saving_value"],
            "note": txt["saving_note"],
            "percent": 20,
            "color": SAVING_COLOR,
        },
    ]


def budget_table(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {
            "icon": Icons.HOME_OUTLINED,
            "category": txt["row_housing"],
            "recommended": "30%",
            "amount": "13 500 Kč",
            "note": txt["row_housing_note"],
            "color": NEEDS_COLOR,
        },
        {
            "icon": Icons.RESTAURANT_OUTLINED,
            "category": txt["row_food"],
            "recommended": "10%",
            "amount": "4 500 Kč",
            "note": txt["row_food_note"],
            "color": NEEDS_COLOR,
        },
        {
            "icon": Icons.DIRECTIONS_CAR_OUTLINED,
            "category": txt["row_transport"],
            "recommended": "5%",
            "amount": "2 250 Kč",
            "note": txt["row_transport_note"],
            "color": NEEDS_COLOR,
        },
        {
            "icon": Icons.FAVORITE_BORDER,
            "category": txt["row_other_needs"],
            "recommended": "5%",
            "amount": "2 250 Kč",
            "note": txt["row_other_needs_note"],
            "color": NEEDS_COLOR,
        },
        {
            "icon": Icons.LOCAL_MALL_OUTLINED,
            "category": txt["row_wants"],
            "recommended": "30%",
            "amount": "13 500 Kč",
            "note": txt["row_wants_note"],
            "color": WANTS_COLOR,
        },
        {
            "icon": Icons.TRENDING_UP,
            "category": txt["row_saving"],
            "recommended": "20%",
            "amount": "9 000 Kč",
            "note": txt["row_saving_note"],
            "color": SAVING_COLOR,
        },
    ]


def assistant_actions(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"icon": Icons.EDIT_OUTLINED, "label": txt["action_edit_budget"]},
        {"icon": Icons.BAR_CHART, "label": txt["action_create_chart"]},
        {"icon": Icons.SAVINGS_OUTLINED, "label": txt["action_save_plan"]},
        {"icon": Icons.TRENDING_UP, "label": txt["action_invest_plan"]},
        {"icon": Icons.IOS_SHARE, "label": txt["action_export"]},
    ]


def quick_actions(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"icon": Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, "label": txt["quick_create_budget"]},
        {"icon": Icons.QUERY_STATS, "label": txt["quick_analyze_expenses"]},
        {"icon": Icons.TRENDING_UP, "label": txt["quick_invest_advice"]},
        {"icon": Icons.RECEIPT_LONG_OUTLINED, "label": txt["quick_tax_guide"]},
        {"icon": Icons.CALCULATE_OUTLINED, "label": txt["quick_calculators"]},
    ]


def market_tickers(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {
            "symbol": txt["ticker_sp500"],
            "icon": Icons.PUBLIC,
            "icon_color": "#3B82F6",
            "value": "5 278,40",
            "change": "+0,65%",
            "trend": "up",
            "spark": [4.0, 4.2, 4.1, 4.5, 4.4, 4.7, 4.9, 5.0, 5.1, 5.3],
        },
        {
            "symbol": txt["ticker_nasdaq"],
            "icon": Icons.MEMORY,
            "icon_color": "#0EA5E9",
            "value": "16 735,02",
            "change": "+0,84%",
            "trend": "up",
            "spark": [15.5, 15.7, 15.6, 16.0, 16.2, 16.1, 16.4, 16.5, 16.6, 16.7],
        },
        {
            "symbol": txt["ticker_dow"],
            "icon": Icons.ACCOUNT_BALANCE_OUTLINED,
            "icon_color": "#6366F1",
            "value": "38 885,10",
            "change": "-0,12%",
            "trend": "down",
            "spark": [39.2, 39.0, 39.1, 38.9, 39.0, 38.8, 38.95, 38.9, 38.95, 38.88],
        },
        {
            "symbol": txt["ticker_btc"],
            "icon": Icons.CURRENCY_BITCOIN,
            "icon_color": "#F59E0B",
            "value": "67 845,21",
            "change": "+2,35%",
            "trend": "up",
            "spark": [62.0, 63.5, 63.0, 64.2, 65.0, 66.0, 65.5, 66.8, 67.2, 67.8],
        },
        {
            "symbol": txt["ticker_eur"],
            "icon": Icons.EURO,
            "icon_color": "#94A3B8",
            "value": "24,85",
            "change": "-0,08%",
            "trend": "down",
            "spark": [25.1, 25.0, 24.95, 24.92, 24.88, 24.9, 24.87, 24.85, 24.86, 24.85],
        },
    ]


def recent_analyses(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"title": txt["analysis_1"], "time": txt["analysis_1_time"]},
        {"title": txt["analysis_2"], "time": txt["analysis_2_time"]},
        {"title": txt["analysis_3"], "time": txt["analysis_3_time"]},
        {"title": txt["analysis_4"], "time": txt["analysis_4_time"]},
    ]


def daily_tip(lang: str) -> dict:
    txt = s(lang)
    return {"title": txt["tip_title"], "text": txt["tip_text"]}
