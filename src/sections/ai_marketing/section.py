"""AI Marketing section registration."""

from __future__ import annotations

import flet as ft

from src.sections._base import Section
from src.sections.ai_marketing.context import build_context
from src.sections.ai_marketing.strings import STRINGS
from src.sections.ai_marketing.view import build_view


SECTION = Section(
    key="ai_marketing",
    icon=ft.Icons.CAMPAIGN_OUTLINED,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    build_context=build_context,
    order=50,
)
