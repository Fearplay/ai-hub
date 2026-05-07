"""AI Documents section registration."""

from __future__ import annotations

import flet as ft

from src.sections._base import Section
from src.sections.ai_documents.strings import STRINGS
from src.sections.ai_documents.view import build_view


SECTION = Section(
    key="ai_documents",
    icon=ft.Icons.DESCRIPTION_OUTLINED,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    order=80,
)
