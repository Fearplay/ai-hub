"""AI LinkedIn section registration."""

from __future__ import annotations

from src.qt.icons import Icons
from src.sections._base import Section
from src.sections.ai_linkedin.context import build_context
from src.sections.ai_linkedin.strings import STRINGS
from src.sections.ai_linkedin.view import build_view


SECTION = Section(
    key="ai_linkedin",
    icon=Icons.ID_CARD,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    build_context=build_context,
    order=25,
)
