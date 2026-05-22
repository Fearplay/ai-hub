"""AI Jobs section registration.

Auto-discovered by :mod:`src.sections` - no edits to ``app.py`` or
``sidebar.py`` are needed. ``order=25`` puts the section right above
AI Career (order 30) since the typical journey is "find a posting"
-> "tailor your CV to it".
"""

from __future__ import annotations

from src.sections._base import Section
from src.sections.ai_jobs.context import build_context
from src.sections.ai_jobs.data import ACCENT, SECTION_ICON
from src.sections.ai_jobs.strings import STRINGS
from src.sections.ai_jobs.view import build_view


SECTION = Section(
    key="ai_jobs",
    icon=SECTION_ICON,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    build_context=build_context,
    accent=ACCENT,
    order=25,
)
