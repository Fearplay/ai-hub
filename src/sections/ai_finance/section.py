"""AI Finance section registration."""

from __future__ import annotations

from src.qt.icons import Icons
from src.sections._base import Section
from src.sections.ai_finance.context import build_context
from src.sections.ai_finance.data import ACCENT
from src.sections.ai_finance.strings import STRINGS
from src.sections.ai_finance.view import build_view


SECTION = Section(
    key="ai_finance",
    icon=Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    build_context=build_context,
    accent=ACCENT,
    order=60,
)
