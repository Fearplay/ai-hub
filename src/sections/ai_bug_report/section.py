"""AI Bug Report section registration.

Turns a description + screenshots + supporting docs into a polished
Word bug report (title, severity, STR, expected vs actual,
attachments). The auto-discovery in ``src.sections`` reads ``SECTION``.
"""

from __future__ import annotations

from src.qt.icons import Icons
from src.sections._base import Section
from src.sections.ai_bug_report.context import build_context
from src.sections.ai_bug_report.strings import STRINGS
from src.sections.ai_bug_report.view import build_view


SECTION = Section(
    key="ai_bug_report",
    icon=Icons.WARNING_AMBER_OUTLINED,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    build_context=build_context,
    order=90,
)
