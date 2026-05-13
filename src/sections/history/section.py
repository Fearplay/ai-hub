"""History section registration (secondary nav)."""

from __future__ import annotations

from src.qt.icons import Icons
from src.sections._base import Section
from src.sections.history.strings import STRINGS
from src.sections.history.view import build_view


SECTION = Section(
    key="history",
    icon=Icons.HISTORY,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    order=20,
    nav_group="secondary",
)
