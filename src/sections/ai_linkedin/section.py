"""AI LinkedIn section registration."""

from __future__ import annotations

from src.sections._base import Section
from src.sections.ai_linkedin.data import SECTION_ICON
from src.sections.ai_linkedin.strings import STRINGS
from src.sections.ai_linkedin.view import build_view


SECTION = Section(
    key="ai_linkedin",
    icon=SECTION_ICON,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    accent="#0A66C2",  # LinkedIn brand blue
    order=25,
)
