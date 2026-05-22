"""Static data for the AI Finance section.

The AI Finance section keeps every section-specific lookup here:

* the section icon used by the sidebar / header,
* the colour palette used by the donut chart and category badges,
* the **seed list of Yahoo Finance tickers** the live Markets card
  defaults to on the user's first launch (the user can then edit the
  list via the right-hand `Upravit` button - see
  :mod:`src.sections.ai_finance.context`),
* the tab labels, quick-action items and template-card copy that
  surface in the centre column.

There is no demo / mock data here anymore - the section starts in an
empty state and only paints what the AI returned for the user's actual
inputs (see :mod:`src.sections.ai_finance.pipeline`).
"""

from __future__ import annotations

from src.qt.icons import Icons
from src.sections.ai_finance.strings import s


SECTION_ICON = Icons.ACCOUNT_BALANCE_WALLET_OUTLINED

ACCENT = "#22C55E"
NEEDS_COLOR = "#22C55E"
WANTS_COLOR = "#3B82F6"
SAVING_COLOR = "#F59E0B"
TREND_UP = "#22C55E"
TREND_DOWN = "#EF4444"


# Yahoo Finance symbols used by :mod:`src.services.market_data`. We
# default to US indices + BTC + EUR/CZK because that is a sensible
# first-launch mix for both English and Czech users. The list is the
# initial seed for ``settings_store.get_finance_tickers()`` - users can
# add / remove symbols via the Markets card editor and the change is
# persisted in ``settings.json``.
DEFAULT_TICKERS: tuple[tuple[str, str, str], ...] = (
    # (yahoo symbol, friendly label, icon-bg colour)
    ("^GSPC", "S&P 500", "#3B82F6"),
    ("^IXIC", "NASDAQ", "#0EA5E9"),
    ("^DJI", "DOW JONES", "#6366F1"),
    ("BTC-USD", "BTC / USD", "#F59E0B"),
    ("EURCZK=X", "EUR / CZK", "#94A3B8"),
)


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


def quick_actions(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"icon": Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, "label": txt["quick_create_budget"]},
        {"icon": Icons.QUERY_STATS, "label": txt["quick_analyze_expenses"]},
        {"icon": Icons.TRENDING_UP, "label": txt["quick_invest_advice"]},
        {"icon": Icons.RECEIPT_LONG_OUTLINED, "label": txt["quick_tax_guide"]},
        {"icon": Icons.CALCULATE_OUTLINED, "label": txt["quick_calculators"]},
    ]


def market_default_symbols() -> list[str]:
    return [symbol for symbol, _name, _color in DEFAULT_TICKERS]


def market_meta_for(symbol: str) -> tuple[str, str]:
    """Return (friendly_name, icon_bg_color) for a default ticker.

    Falls back to the symbol itself when an unknown symbol comes back
    from the live fetch (the user might have customised the list).
    """
    for sym, name, color in DEFAULT_TICKERS:
        if sym == symbol:
            return name, color
    return symbol, "#94A3B8"
