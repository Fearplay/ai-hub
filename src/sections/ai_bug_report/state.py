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
TAB_HISTORY = 2


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

    # Follow-up clarifying questions (analogous to AI Career):
    # the AI inspects the description + attachments, and lists
    # gaps it would otherwise have to invent. ``followup_questions``
    # is the AI's output (filled by ``generate_followup_questions``);
    # ``followup_qa`` carries the user's answers back into the second
    # pass via ``prompts._format_followup_qa``. ``run_stage`` mirrors
    # AI Career's worker semantics so the footer button can show
    # "Generating..." while either phase is in flight.
    followup_questions: list[dict] = field(default_factory=list)
    followup_qa: list[dict] = field(default_factory=list)
    run_stage: str = ""

    # Cached list of saved runs (``RunSummary`` -> dict mapping). The
    # History tab calls ``pipeline.list_saved_runs()`` to refresh, then
    # caches the result here so the right-panel cost / activity badges
    # do not have to re-read ``history.json`` on every rebuild.
    runs_history: list[dict] = field(default_factory=list)

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
        self.followup_questions = []
        self.followup_qa = []


STATE = BugReportState()
