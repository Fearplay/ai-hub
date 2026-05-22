"""AI Business section registration."""

from __future__ import annotations

from src.qt.icons import Icons
from src.sections._base import Section
from src.sections.ai_business.strings import STRINGS
from src.sections.ai_business.view import build_view


SECTION = Section(
    key="ai_business",
    icon=Icons.BUSINESS_CENTER_OUTLINED,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    order=40,
    hidden=True,
)
