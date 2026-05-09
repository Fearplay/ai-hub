"""How-to dialog content for the AI LinkedIn section."""

from __future__ import annotations

import flet as ft

from src.components.how_to_dialog import HowToSection, open_how_to
from src.sections.ai_linkedin.strings import s
from src.theme import Theme


def open_linkedin_how_to(page: ft.Page, theme: Theme, lang: str) -> None:
    txt = s(lang)
    sections = [
        HowToSection(
            icon=ft.Icons.AUTO_AWESOME,
            title=txt["howto_what_title"],
            body=txt["howto_what_text"],
        ),
        HowToSection(
            icon=ft.Icons.UPLOAD_FILE,
            title=txt["howto_prepare_title"],
            body=txt["howto_prepare_text"],
        ),
        HowToSection(
            icon=ft.Icons.TUNE,
            title=txt["howto_quality_title"],
            body=txt["howto_quality_text"],
        ),
        HowToSection(
            icon=ft.Icons.WARNING_AMBER_OUTLINED,
            title=txt["howto_wont_title"],
            body=txt["howto_wont_text"],
        ),
    ]
    open_how_to(
        page,
        theme,
        title=txt["howto_title"],
        sections=sections,
        close_label=txt["howto_close"],
    )
