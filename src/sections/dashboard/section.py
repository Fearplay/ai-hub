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
    # The dashboard is an auxiliary entry point - it surfaces every
    # primary section as a card grid, but it is not itself an AI
    # feature. Living in the secondary nav (above Settings) keeps the
    # primary section list focused on the actual AI assistants while
    # the dashboard stays one click away. Secondary rows are not
    # drag-reorderable (see ``components/sidebar.py``), which matches
    # the user request that the dashboard never moves around.
    order=30,
    nav_group="secondary",
)
