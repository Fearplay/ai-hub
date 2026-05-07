"""AI Legal section registration."""

from __future__ import annotations

import flet as ft

from src.sections._base import Section
from src.sections.ai_legal.strings import STRINGS
from src.sections.ai_legal.view import build_view


SECTION = Section(
    key="ai_legal",
    icon=ft.Icons.GAVEL_OUTLINED,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    order=30,
)
