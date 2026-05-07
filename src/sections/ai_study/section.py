"""AI Study section registration."""

from __future__ import annotations

import flet as ft

from src.sections._base import Section
from src.sections.ai_study.context import build_context
from src.sections.ai_study.strings import STRINGS
from src.sections.ai_study.view import build_view


SECTION = Section(
    key="ai_study",
    icon=ft.Icons.SCHOOL_OUTLINED,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    build_context=build_context,
    order=70,
)
