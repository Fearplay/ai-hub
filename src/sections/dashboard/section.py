"""Dashboard section registration."""

from __future__ import annotations

from src.qt.icons import Icons
from src.sections._base import Section
from src.sections.dashboard.strings import STRINGS
from src.sections.dashboard.view import build_view


SECTION = Section(
    key="dashboard",
    icon=Icons.DASHBOARD_OUTLINED,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    order=10,
)
