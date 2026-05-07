"""Favorites section registration (secondary nav)."""

from __future__ import annotations

import flet as ft

from src.sections._base import Section
from src.sections.favorites.strings import STRINGS
from src.sections.favorites.view import build_view


SECTION = Section(
    key="favorites",
    icon=ft.Icons.STAR_OUTLINE,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    order=30,
    badge="3",
    nav_group="secondary",
)
