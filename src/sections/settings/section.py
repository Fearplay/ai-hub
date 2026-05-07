"""Settings section registration (secondary nav)."""

from __future__ import annotations

import flet as ft

from src.sections._base import Section
from src.sections.settings.strings import STRINGS
from src.sections.settings.view import build_view


SECTION = Section(
    key="settings",
    icon=ft.Icons.SETTINGS_OUTLINED,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    order=40,
    nav_group="secondary",
)
