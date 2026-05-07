"""Module-level state singleton for the AI Doc Assistant section.

The whole app rebuilds on theme/lang/section toggles, so anything that
should survive a rebuild (uploaded file, last action result, demo flag,
which tab is open) lives here, not inside ``build_view``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


TAB_UPLOAD = 0
TAB_ANALYZE = 1
TAB_OUTPUT = 2


ACTION_SUMMARY = "summary"
ACTION_QA = "qa"
ACTION_REWRITE = "rewrite"
ACTION_EXTRACT = "extract"

ACTIONS = (ACTION_SUMMARY, ACTION_QA, ACTION_REWRITE, ACTION_EXTRACT)


@dataclass
class UploadedDoc:
    path: str
    name: str
    ext: str
    size_bytes: int
    text: str


@dataclass
class DocAssistantState:
    active_tab: int = TAB_UPLOAD
    document: Optional[UploadedDoc] = None
    action: str = ACTION_SUMMARY

    qa_question: str = ""
    rewrite_passage: str = ""
    rewrite_tone: str = "neutral"

    last_result: Optional[dict] = None
    last_action: str = ""
    last_error: str = ""

    activity: str = "ready"
    demo_mode: bool = False

    def can_run(self) -> bool:
        if self.demo_mode:
            return True
        if not self.document or not self.document.text:
            return False
        if self.action == ACTION_QA and not self.qa_question.strip():
            return False
        if self.action == ACTION_REWRITE and not self.rewrite_passage.strip():
            return False
        return True

    def reset_result(self) -> None:
        self.last_result = None
        self.last_action = ""
        self.last_error = ""


STATE = DocAssistantState()
