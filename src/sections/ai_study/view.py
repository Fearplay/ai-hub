"""AI Study - placeholder for now."""

from __future__ import annotations

import flet as ft

from src.components.placeholder import placeholder_view
from src.sections.ai_study.strings import s
from src.theme import Theme


def build_view(theme: Theme, lang: str) -> ft.Control:
    return placeholder_view(theme, lang, title=s(lang)["title"])
