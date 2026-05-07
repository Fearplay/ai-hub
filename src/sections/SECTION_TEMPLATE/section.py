"""Section registration. The auto-discovery in ``src.sections`` reads ``SECTION``."""

from __future__ import annotations

import flet as ft

from src.sections._base import Section
from src.sections.SECTION_TEMPLATE.strings import STRINGS
from src.sections.SECTION_TEMPLATE.view import build_view


SECTION = Section(
    key="my_section",
    icon=ft.Icons.STAR_OUTLINE,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    order=100,
)
