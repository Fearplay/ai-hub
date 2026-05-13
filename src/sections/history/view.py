"""History - placeholder for now.

Once Phase 2 lands, this section will list cross-section AI runs from
``~/AI Hub/history.json``. AI Career already keeps its own per-section
History tab, so this view stays a coming-soon placeholder for now.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from src.components.placeholder import placeholder_view
from src.sections.history.strings import s
from src.services import logger as logger_service
from src.theme import Theme


def build_view(theme: Theme, lang: str) -> QWidget:
    try:
        return placeholder_view(theme, lang, title=s(lang)["title"])
    except Exception as exc:
        logger_service.log_exception("history.view", "build_view_failed", exc)
        raise
