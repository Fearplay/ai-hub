"""Module-level singleton state for the AI Finance section.

The Qt-side ``build_view`` rebuilds whenever the user changes language,
theme, or section; this dataclass holds everything that must survive
those rebuilds:

* the active tab + sub-mode,
* the chat transcript and any attached statements (parsed plain text),
* every structured analysis we already paid tokens for (BudgetPlan,
  SavingsPlan, ExpenseAnalysis, InvestmentScenario, TaxChecklist,
  InsuranceReview),
* the activity badge / last error / last saved run folder,
* a small in-memory mirror of the on-disk history (so the right-hand
  "Recent analyses" card never needs a synchronous file read).

Module-level singleton because section folders are isolated by design
(see [sections.mdc](.cursor/rules/sections.mdc)) - the AI Finance
section never shares state with other sections.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# Tab indices in the main tab bar.
TAB_CHAT = 0
TAB_BUDGET = 1
TAB_INVEST = 2
TAB_ANALYSIS = 3
TAB_TAXES = 4
TAB_INSURANCE = 5
TAB_CALCULATORS = 6
TAB_TEMPLATES = 7


# Budget methods - 50/30/20 is the canonical one users see on the
# greeting bubble; everything else maps cleanly onto the BudgetPlan
# JSON returned by the LLM.
BUDGET_METHOD_50_30_20 = "50_30_20"
BUDGET_METHOD_60_20_20 = "60_20_20"
BUDGET_METHOD_70_20_10 = "70_20_10"
BUDGET_METHOD_ZERO_BASED = "zero_based"
BUDGET_METHOD_CUSTOM = "custom"

BUDGET_METHODS = (
    BUDGET_METHOD_50_30_20,
    BUDGET_METHOD_60_20_20,
    BUDGET_METHOD_70_20_10,
    BUDGET_METHOD_ZERO_BASED,
    BUDGET_METHOD_CUSTOM,
)


# Currency hints used by the calculators + budget tab. The user picks a
# default in the budget form; the rest of the calculators inherit it
# so a Czech user sees Kč throughout without re-typing it everywhere.
DEFAULT_CURRENCY_CS = "CZK"
DEFAULT_CURRENCY_EN = "USD"


@dataclass
class FinanceChatMessage:
    """One bubble in the AI Finance chat transcript."""

    role: str  # "user" | "assistant"
    text: str
    time: str
    attachment_name: str = ""


@dataclass
class FinanceState:
    active_tab: int = TAB_CHAT

    # Chat mode --------------------------------------------------------
    chat_messages: list[FinanceChatMessage] = field(default_factory=list)
    chat_attachments: dict[str, str] = field(default_factory=dict)
    chat_running: bool = False
    chat_last_error: str = ""

    # Structured analyses ----------------------------------------------
    # Each is the LLM-returned JSON for the matching schema in
    # ``schema.py``. We cache them on STATE so follow-up chat / refine
    # turns can pass the JSON without re-sending the raw upload.
    budget: Optional[dict] = None
    savings_plan: Optional[dict] = None
    expense_analysis: Optional[dict] = None
    investment_scenario: Optional[dict] = None
    tax_checklist: Optional[dict] = None
    insurance_review: Optional[dict] = None

    # Last form inputs - we replay them when the user re-enters the tab
    # so the form fields are pre-filled with their previous values.
    last_budget_input: dict = field(default_factory=dict)
    last_savings_input: dict = field(default_factory=dict)
    last_invest_input: dict = field(default_factory=dict)
    last_analysis_input: dict = field(default_factory=dict)
    last_tax_input: dict = field(default_factory=dict)
    last_insurance_input: dict = field(default_factory=dict)

    # Right-hand panel cache -------------------------------------------
    # ``markets`` holds the latest snapshot from
    # :func:`src.services.market_data.get_quotes`. When empty (or when
    # ``market_data_enabled`` is off / no tickers are configured) the
    # right-hand card shows an empty-state hint instead of mock data.
    markets: list[dict] = field(default_factory=list)
    markets_fetched_at: float = 0.0
    markets_loading: bool = False
    markets_error: str = ""

    # Activity + persistence -------------------------------------------
    activity: str = "ready"  # "ready" | "thinking" | "analyzing" | "generating" | "exporting" | "error"
    last_error: str = ""
    last_run_folder: str = ""

    # In-memory mirror of the on-disk history; populated by
    # ``pipeline.save_full_analysis`` so the right-hand card refreshes
    # without a sync file read.
    runs_history: list[dict] = field(default_factory=list)

    def reset_chat(self) -> None:
        self.chat_messages = []
        self.chat_attachments = {}
        self.chat_running = False
        self.chat_last_error = ""

    def reset_analyses(self) -> None:
        """Wipe every structured analysis - keep the chat + uploads."""
        self.budget = None
        self.savings_plan = None
        self.expense_analysis = None
        self.investment_scenario = None
        self.tax_checklist = None
        self.insurance_review = None
        self.activity = "ready"
        self.last_error = ""
        self.last_run_folder = ""

    def reset_all(self) -> None:
        self.reset_chat()
        self.reset_analyses()
        self.last_budget_input = {}
        self.last_savings_input = {}
        self.last_invest_input = {}
        self.last_analysis_input = {}
        self.last_tax_input = {}
        self.last_insurance_input = {}

    def has_any_analysis(self) -> bool:
        return any(
            getattr(self, attr) is not None
            for attr in (
                "budget",
                "savings_plan",
                "expense_analysis",
                "investment_scenario",
                "tax_checklist",
                "insurance_review",
            )
        )


STATE = FinanceState()
