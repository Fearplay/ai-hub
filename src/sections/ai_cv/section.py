"""AI CV section registration."""

from __future__ import annotations

from src.qt.icons import Icons
from src.sections._base import Section
from src.sections.ai_cv.strings import STRINGS
from src.sections.ai_cv.view import build_view


SECTION = Section(
    key="ai_cv",
    icon=Icons.ASSIGNMENT_IND_OUTLINED,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    # Violet accent (per request) - AI CV keeps the original purple
    # instead of the app-wide default blue.
    accent="#7C5CFC",
    order=20,
)
