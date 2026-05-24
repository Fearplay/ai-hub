"""How-to dialog content for the AI Bug Report section.

Wires the section's per-language strings into the generic
:func:`src.components.how_to_dialog.open_how_to` helper.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget

from src.components.how_to_dialog import HowToSection, open_how_to
from src.qt.icons import Icons
from src.sections.ai_bug_report.strings import s
from src.theme import Theme


def open_bug_report_how_to(parent: Optional[QWidget], theme: Theme, lang: str) -> None:
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
