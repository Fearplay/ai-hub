"""Module-level state singleton for the AI Bug Report section.

The section rebuilds on theme / language / section toggles, so anything
that should survive a rebuild (attachments, the last generated report,
demo flag, the currently visible tab) lives here, not inside
``build_view``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


TAB_INPUT = 0
TAB_PREVIEW = 1
TAB_EXPORT = 2


SEVERITY_VALUES = ("Critical", "High", "Medium", "Low")
PRIORITY_VALUES = ("P0", "P1", "P2", "P3")
REPRODUCIBILITY_VALUES = ("Always", "Sometimes", "Rare", "Once", "Unknown")


@dataclass
class ImageAttachment:
    """One screenshot / image attached by the user.

    ``bytes_data`` is read eagerly so the AI call (which sends the
    bytes to OpenAI / Anthropic vision) does not have to re-read the
    file later - the user might have deleted / moved it in the
    meantime.
    """

    path: str
    name: str
    ext: str
    size_bytes: int
    bytes_data: bytes
    mime: str


@dataclass
class DocAttachment:
    """One text-like attachment (log, JSON, PDF, DOCX, MD, HTML, ...).

    Parsed via :mod:`src.services.file_parser` into plain text so the
    AI prompt can include the body verbatim alongside the user-typed
    description.
    """

    path: str
    name: str
    ext: str
    size_bytes: int
    text: str


@dataclass
class BugReportState:
    active_tab: int = TAB_INPUT

    description: str = ""
    environment_hint: str = ""

    images: list[ImageAttachment] = field(default_factory=list)
    documents: list[DocAttachment] = field(default_factory=list)

    last_report: Optional[dict] = None
    last_error: str = ""

    last_run_folder: str = ""
    last_save_path: str = ""

    activity: str = "ready"
    demo_mode: bool = False

    def can_generate(self) -> bool:
        if self.demo_mode:
            return True
        if self.description.strip():
            return True
        if self.images:
            return True
        if self.documents:
            return True
        return False

    def reset_result(self) -> None:
        self.last_report = None
        self.last_error = ""
        self.last_save_path = ""


STATE = BugReportState()
