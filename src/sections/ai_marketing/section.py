"""AI Marketing section registration."""

from __future__ import annotations

from src.qt.icons import Icons
from src.sections._base import Section
from src.sections.ai_marketing.strings import STRINGS
from src.sections.ai_marketing.view import build_view


SECTION = Section(
    key="ai_marketing",
    icon=Icons.CAMPAIGN_OUTLINED,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    order=50,
    hidden=True,
)
