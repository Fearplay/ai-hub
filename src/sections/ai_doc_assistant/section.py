"""AI Doc Assistant section registration.

Sits next to the simpler ``ai_documents`` placeholder in the sidebar.
This is the "version B" with a real AI pipeline (summarise / Q&A /
rewrite / extract) backed by ``src.services.ai_provider``.
"""

from __future__ import annotations

from src.qt.icons import Icons
from src.sections._base import Section
from src.sections.ai_doc_assistant.strings import STRINGS
from src.sections.ai_doc_assistant.view import build_view


SECTION = Section(
    key="ai_doc_assistant",
    icon=Icons.AUTO_STORIES_OUTLINED,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    order=85,
    nav_group="primary",
)
