"""Module-level singleton state for the AI Legal section.

The whole app rebuilds on theme/lang/section changes (see
:meth:`src.app.AIHubApp.build`), so anything we want to survive those
rebuilds has to live outside ``build_view``. This singleton holds:

* which sub-tab the user last had open,
* what file (if any) they uploaded via drag-drop or the picker, plus
  the extracted plain-text body that the AI prompts feed on,
* their selected template / accent / font in the Templates tab,
* the running list of chat messages (real conversation, not a mock),
* whether the Analýza tab is in *Document* or *Chat* presentation mode,
* whether demo mode is on (no API calls; mock answers from data.py),
* what the current background activity is (for the right-hand badge).

It is never imported across sections.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChatMessage:
    """One bubble inside the AI Legal chat tab.

    ``role`` is ``"user"`` or ``"assistant"``; ``time`` is a ``"HH:MM"``
    string for the bubble timestamp; ``attachment_name`` is optional and,
    when set, renders the small attached-file chip next to the user
    bubble (used the first time the user sends a message after dropping
    a document).
    """

    role: str
    text: str
    time: str
    attachment_name: str = ""


@dataclass
class LegalState:
    active_tab: int = 0
    uploaded_file: Optional[dict] = None
    attached_doc_text: str = ""
    selected_template: str = "modern"
    selected_color: str = "#7C5CFC"
    selected_font: str = "sans"
    analysis_view_mode: str = "document"
    drafts_messages: list[dict] = field(default_factory=list)
    chat_messages: list[ChatMessage] = field(default_factory=list)
    demo_mode: bool = False
    activity: str = "ready"
    last_error: str = ""
    attachment_announced: bool = False


STATE = LegalState()
