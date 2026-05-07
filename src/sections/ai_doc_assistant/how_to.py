"""How-to dialog content for the AI Doc Assistant section.

Wires the section's per-language strings into the generic
:func:`src.components.how_to_dialog.open_how_to` helper.
"""

from __future__ import annotations

import flet as ft

from src.components.how_to_dialog import HowToSection, open_how_to
from src.sections.ai_doc_assistant.strings import s
from src.theme import Theme


def open_doc_assistant_how_to(page: ft.Page, theme: Theme, lang: str) -> None:
    txt = s(lang)
    sections = [
        HowToSection(
            icon=ft.Icons.AUTO_AWESOME,
            title=txt["how_to_section_what"],
            body=txt["how_to_what_text"],
        ),
        HowToSection(
            icon=ft.Icons.UPLOAD_FILE,
            title=txt["how_to_section_inputs"],
            body=txt["how_to_inputs_text"],
        ),
        HowToSection(
            icon=ft.Icons.TUNE,
            title=txt["how_to_section_quality"],
            body=txt["how_to_quality_text"],
        ),
    ]
    open_how_to(
        page,
        theme,
        title=txt["how_to_title"],
        sections=sections,
        close_label=txt["how_to_close"],
    )
