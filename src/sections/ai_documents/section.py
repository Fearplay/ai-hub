"""AI Documents section registration."""

from __future__ import annotations

from src.qt.icons import Icons
from src.sections._base import Section
from src.sections.ai_documents.strings import STRINGS
from src.sections.ai_documents.view import build_view


SECTION = Section(
    key="ai_documents",
    icon=Icons.DESCRIPTION_OUTLINED,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    order=80,
    hidden=True,
)
