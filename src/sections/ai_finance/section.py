"""AI Finance section registration."""

from __future__ import annotations

from src.sections._base import Section
from src.sections.ai_finance.data import ACCENT, SECTION_ICON
from src.sections.ai_finance.strings import STRINGS
from src.sections.ai_finance.view import build_view


SECTION = Section(
    key="ai_finance",
    icon=SECTION_ICON,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    accent=ACCENT,
    order=60,
)
