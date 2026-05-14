"""How-to dialog content for the AI Jobs section.

Mirrors :mod:`src.sections.ai_career.how_to` - three short blocks
explaining what the section does, what to give it, and how to keep
costs sane. The localised copy lives in ``strings.py`` so swapping the
EN/CS toggle re-renders the dialog without touching this file.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget

from src.components.how_to_dialog import HowToSection, open_how_to
from src.qt.icons import Icons
from src.sections.ai_jobs.strings import s
from src.theme import Theme


def open_jobs_how_to(parent: Optional[QWidget], theme: Theme, lang: str) -> None:
    txt = s(lang)
    sections = [
        HowToSection(
            icon=Icons.AUTO_AWESOME,
            title=txt["how_to_section_what"],
            body=txt["how_to_what_text"],
        ),
        HowToSection(
            icon=Icons.UPLOAD_FILE,
            title=txt["how_to_section_inputs"],
            body=txt["how_to_inputs_text"],
        ),
        HowToSection(
            icon=Icons.TUNE,
            title=txt["how_to_section_quality"],
            body=txt["how_to_quality_text"],
        ),
    ]
    open_how_to(
        parent,
        theme,
        title=txt["how_to_title"],
        sections=sections,
        close_label=txt["how_to_close"],
    )
