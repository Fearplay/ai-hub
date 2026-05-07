"""Module-level singleton state for the AI Legal section.

The whole app rebuilds on theme/lang/section changes (see
:meth:`src.app.AIHubApp.build`), so anything we want to survive those
rebuilds has to live outside ``build_view``. This singleton holds:

* which sub-tab the user last had open,
* what file (if any) they uploaded via drag-drop or the picker,
* their selected template / accent / font in the Templates tab,
* the running list of mock messages they typed into the Drafts tab,
* whether the Analýza tab is in *Document* or *Chat* presentation mode.

It is never imported across sections.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.sections.ai_legal.data import DEFAULT_UPLOADED_FILE


@dataclass
class LegalState:
    active_tab: int = 0
    uploaded_file: dict | None = field(default_factory=lambda: dict(DEFAULT_UPLOADED_FILE))
    selected_template: str = "modern"
    selected_color: str = "#7C5CFC"
    selected_font: str = "sans"
    analysis_view_mode: str = "document"
    drafts_messages: list[dict] = field(default_factory=list)


STATE = LegalState()
