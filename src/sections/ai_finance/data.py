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


# -- Demo-mode mocks ---------------------------------------------------
#
# Used by ``pipeline.*`` when ``STATE.demo_mode`` is True (per
# ``ai-section.mdc``: every paid-provider section MUST have demo data so
# users can showcase the feature without spending tokens). The numbers
# are fictional but internally consistent (income vs. splits / amounts
# add up correctly) so screenshots look plausible.


MOCK_BUDGET: dict = {
    "currency": "CZK",
    "income": 45000,
    "method": "50_30_20",
    "splits": {
        "needs": {"percent": 50, "amount": 22500, "label": "Needs"},
        "wants": {"percent": 30, "amount": 13500, "label": "Wants"},
        "saving": {"percent": 20, "amount": 9000, "label": "Saving"},
    },
    "breakdown": [
        {"category": "Housing", "group": "needs", "percent": 28, "amount": 12600, "note": "Rent + utilities"},
        {"category": "Food", "group": "needs", "percent": 14, "amount": 6300, "note": "Groceries + cooking"},
        {"category": "Transport", "group": "needs", "percent": 8, "amount": 3600, "note": "Public transit + occasional taxi"},
        {"category": "Subscriptions", "group": "wants", "percent": 5, "amount": 2250, "note": "Streaming + gym + cloud"},
        {"category": "Eating out", "group": "wants", "percent": 12, "amount": 5400, "note": "Restaurants + coffee"},
        {"category": "Hobbies", "group": "wants", "percent": 13, "amount": 5850, "note": "Travel + entertainment"},
        {"category": "Emergency fund", "group": "saving", "percent": 12, "amount": 5400, "note": "Until 3-month runway"},
        {"category": "Long-term saving", "group": "saving", "percent": 8, "amount": 3600, "note": "Retirement / index funds"},
    ],
    "warnings": [
        "Eating out + subscriptions sum to 17% of income - the wants bucket has little room left for travel.",
    ],
    "suggestions": [
        "Audit streaming subscriptions; one cancellation typically saves 200-300 Kč/mo.",
        "Automate the saving transfer the day salary lands so you do not 'see' the money in your account.",
    ],
    "summary": "A standard 50/30/20 split with a comfortable buffer in saving and a watchpoint on the wants bucket.",
}


MOCK_SAVINGS_PLAN: dict = {
    "currency": "CZK",
    "goal_amount": 120000,
    "current_savings": 30000,
    "monthly_contribution": 7500,
    "months_to_goal": 12,
    "percent_of_income": 16.7,
    "milestones": [
        {"label": "25%", "amount": 30000, "after_months": 0},
        {"label": "50%", "amount": 60000, "after_months": 4},
        {"label": "75%", "amount": 90000, "after_months": 8},
        {"label": "100%", "amount": 120000, "after_months": 12},
    ],
    "tips": [
        "Park the contribution in a high-yield savings account so inflation does not eat the runway.",
        "Set the monthly transfer the day after payday and forget about it.",
        "Once you hit 50% of the goal, raise the auto-transfer by 500 Kč.",
    ],
    "summary": "12 months at 7 500 Kč/mo gets you to a 120 000 Kč emergency fund with one starter milestone already done.",
}


MOCK_EXPENSE_ANALYSIS: dict = {
    "currency": "CZK",
    "period": "Last 30 days",
    "total_income": 45000,
    "total_expenses": 38200,
    "net_cash_flow": 6800,
    "categories": [
        {"name": "Housing", "amount": 12600, "percent_of_expenses": 33},
        {"name": "Food", "amount": 6300, "percent_of_expenses": 16},
        {"name": "Transport", "amount": 3600, "percent_of_expenses": 9},
        {"name": "Eating out", "amount": 5400, "percent_of_expenses": 14},
        {"name": "Subscriptions", "amount": 2250, "percent_of_expenses": 6},
        {"name": "Hobbies", "amount": 5850, "percent_of_expenses": 15},
        {"name": "Other", "amount": 2200, "percent_of_expenses": 7},
    ],
    "top_outflows": [
        {"label": "Rent", "amount": 11500, "note": "Monthly direct debit"},
        {"label": "Restaurant - weekend trip", "amount": 1800, "note": "One-off, not recurring"},
        {"label": "Streaming bundle", "amount": 540, "note": "4 services - candidate to trim"},
    ],
    "recurring": [
        {"label": "Rent", "monthly_amount": 11500, "category": "Housing"},
        {"label": "Phone + internet", "monthly_amount": 950, "category": "Housing"},
        {"label": "Gym", "monthly_amount": 690, "category": "Subscriptions"},
        {"label": "Streaming bundle", "monthly_amount": 540, "category": "Subscriptions"},
    ],
    "suggestions": [
        "Cancel one streaming service - even the cheapest one saves ~150 Kč/mo.",
        "Move 3 000 Kč of the leftover net cash flow straight into the emergency fund.",
        "Review the gym membership in 3 months if the visit count stays under 8/mo.",
    ],
    "summary": "Spending stays inside the budget with 6 800 Kč left over; subscriptions and eating out are the easiest leverage points.",
}


MOCK_INVESTMENT_SCENARIO: dict = {
    "currency": "CZK",
    "amount": 100000,
    "horizon_years": 5,
    "scenarios": [
        {
            "name": "Conservative",
            "risk_level": "conservative",
            "expected_annual_return_pct": 3,
            "projected_value": 115927,
            "allocation": [
                {"asset_class": "Cash / money market", "percent": 30},
                {"asset_class": "Short-term bonds", "percent": 50},
                {"asset_class": "Global equities", "percent": 20},
            ],
            "description": "Capital-preservation tilt with a small equity sleeve to keep up with inflation.",
        },
        {
            "name": "Moderate",
            "risk_level": "moderate",
            "expected_annual_return_pct": 5,
            "projected_value": 127628,
            "allocation": [
                {"asset_class": "Cash / money market", "percent": 10},
                {"asset_class": "Bonds (short + intermediate)", "percent": 40},
                {"asset_class": "Global equities", "percent": 45},
                {"asset_class": "Alternatives", "percent": 5},
            ],
            "description": "Balanced 50/50 between defensive and growth assets - the textbook all-weather mix.",
        },
        {
            "name": "Growth",
            "risk_level": "growth",
            "expected_annual_return_pct": 7,
            "projected_value": 140255,
            "allocation": [
                {"asset_class": "Bonds", "percent": 20},
                {"asset_class": "Global equities", "percent": 65},
                {"asset_class": "Real estate", "percent": 10},
                {"asset_class": "Alternatives", "percent": 5},
            ],
            "description": "Equity-heavy tilt - higher volatility but higher expected return over a 5+ year horizon.",
        },
    ],
    "diversification_note": "Spread equity across a global index rather than picking individual companies; rebalance once a year.",
    "risk_note": "Past returns do not predict future returns. Only invest money you do not need in the next 3 years.",
    "disclaimer": "Educational content, not licensed financial advice. Verify with a qualified advisor for your jurisdiction.",
}


MOCK_TAX_CHECKLIST: dict = {
    "country": "Czech Republic",
    "filing_status": "Employee",
    "year": "2025",
    "checklist": [
        {"title": "Collect employer T-form", "detail": "Potvrzeni o zdanitelnych prijmech for the year."},
        {"title": "Compile deductions", "detail": "Mortgage interest, life insurance, donations, child tax credit."},
        {"title": "Confirm advance tax payments", "detail": "Match payslips to the annual statement."},
        {"title": "Review one-off income", "detail": "Side gigs / rental / capital gains - declare separately."},
        {"title": "Submit return", "detail": "Either via employer or directly to the financial office."},
    ],
    "deadlines": [
        {"label": "Employer reconciliation request", "date_or_window": "mid-February"},
        {"label": "Standard filing deadline", "date_or_window": "early April"},
        {"label": "Filing via tax advisor", "date_or_window": "early July"},
    ],
    "documents_needed": [
        "Potvrzeni o zdanitelnych prijmech",
        "Mortgage interest confirmation",
        "Life insurance contract + payment proof",
        "Donation receipts",
        "Childcare expense proofs",
    ],
    "tips": [
        "If you have a mortgage, claim the interest deduction even when it is small - it adds up.",
        "Donations to registered NGOs are deductible up to 15% of taxable income.",
        "Couples with one child or more benefit from the daycare deduction (skolkovne).",
    ],
    "disclaimer": "Educational content - confirm specifics with a Czech tax advisor or the financial office for your situation.",
}


MOCK_INSURANCE_REVIEW: dict = {
    "household": "Single, 32, urban renter",
    "policies": [
        {"name": "Liability insurance (povinne ruceni)", "kind": "Auto", "limit_note": "Mandatory minimum", "premium_note": "~6 500 Kč/yr"},
        {"name": "Household contents", "kind": "Home", "limit_note": "Coverage 200 000 Kč", "premium_note": "~1 200 Kč/yr"},
    ],
    "coverage_gaps": [
        {"topic": "Income protection", "risk": "No coverage for long-term illness; one rent payment of buffer at most.", "severity": "high"},
        {"topic": "Travel insurance", "risk": "Missing for trips abroad - one ER visit can wipe out savings.", "severity": "medium"},
        {"topic": "Liability outside auto", "risk": "Personal liability cap is only 200 000 Kč - low for a city renter.", "severity": "medium"},
    ],
    "duplicates": [],
    "watch_outs": [
        "Check the household policy's exclusions for water damage caused by appliance leaks.",
        "Auto liability is the legal minimum - consider havarijni for a newer vehicle.",
    ],
    "suggestions": [
        "Quote an income-protection policy with 60-90 day waiting period and 24-month payout cap.",
        "Add travel insurance to any debit/credit card or buy an annual multi-trip policy.",
    ],
    "summary": "Two basic policies in place but the household is exposed on income and travel - both fixable for under 5 000 Kč/yr combined.",
    "disclaimer": "Educational content, not licensed insurance advice. Confirm with a broker for your jurisdiction.",
}


MOCK_TIP: dict = {
    "title": "Trim the streaming stack",
    "body": "You spend roughly 540 Kč/mo across 4 streaming services - that is over 6 500 Kč a year. Two services typically cover 90% of what people actually watch.",
    "next_step": "Pick the one streaming service you used least last month and cancel it today; redirect the saving to the emergency fund.",
    "category": "expenses",
}
