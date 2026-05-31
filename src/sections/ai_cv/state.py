"""Module-level singleton state for the AI Career section.

The whole app rebuilds on theme/lang/section changes; persistent state has
to live outside ``build_view``. This singleton holds:

* the user's uploaded files (resume + optional LinkedIn export),
* job posting URL + scraped/pasted text,
* GitHub profile (or skip flag),
* extracted Candidate / JobSpec / MatchAnalysis JSONs,
* the generated documents keyed by kind,
* per-document refine "problem" notes,
* which tab + which document tab the user last had open,
* whether the run is in Demo mode,
* the last-saved run folder for "Reveal in folder",
* which **mode** is active (the structured Form flow vs. the
  conversational Chat flow) and the chat transcript / attachments for
  the Chat mode.

Each section keeps its own state singleton - no shared module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# Tab indices in the main tab bar.
TAB_SETUP = 0
TAB_MATCH = 1
TAB_DOCUMENTS = 2
TAB_INTERVIEW = 3
TAB_HISTORY = 4


# Top-level mode (Chat vs. Form). Each mode has its own UI; the "Form"
# mode is the original Setup -> Match -> Documents -> History flow,
# while "Chat" surfaces the same HR-expert assistant as a free-form
# conversation. Users switch between modes via the tab bar in the
# section header.
MODE_FORM = "form"
MODE_CHAT = "chat"


# Document kinds (sub-tabs in tab_documents.py).
DOC_TAILORED_CV = "tailored_cv"
DOC_MODERN_CV = "modern_cv"
DOC_COVER_LETTER = "cover_letter"
DOC_MATCH_REPORT = "match_report"
DOC_INTERVIEW_PREP = "interview_prep"
DOC_SKILL_GAP = "skill_gap"
DOC_EVIDENCE = "evidence"

DOC_KINDS = (
    DOC_TAILORED_CV,
    DOC_MODERN_CV,
    DOC_COVER_LETTER,
    DOC_MATCH_REPORT,
    DOC_INTERVIEW_PREP,
    DOC_SKILL_GAP,
    DOC_EVIDENCE,
)


@dataclass
class UploadedFile:
    path: str
    name: str
    ext: str
    size_bytes: int
    text: str


@dataclass
class ChatMessage:
    """One bubble in the Chat-mode conversation.

    ``role`` is ``"user"`` or ``"assistant"``. ``time`` is a short HH:MM
    label rendered above the bubble. ``attachment_name`` is the file
    name (display only) when the user attached a document with the
    message; the parsed text lives on :data:`CareerState.chat_attachments`
    so prompts can reference it without re-reading the disk.
    """

    role: str
    text: str
    time: str
    attachment_name: str = ""


@dataclass
class CareerState:
    mode: str = MODE_FORM
    active_tab: int = TAB_SETUP
    active_document: str = DOC_TAILORED_CV
    # Preferred language for generated/refined documents ("en" | "cs").
    # Empty means "follow current UI language".
    document_output_lang: str = ""

    # Chat-mode transcript. ``chat_attachments`` keys are file names
    # (matching ``ChatMessage.attachment_name``) and values are the
    # parsed plain-text body, so the same upload can be referenced by
    # several prompts without re-reading the disk.
    chat_messages: list[ChatMessage] = field(default_factory=list)
    chat_attachments: dict[str, str] = field(default_factory=dict)
    chat_running: bool = False
    chat_last_error: str = ""

    # Mock Interview transcript (TAB_INTERVIEW). Each entry is a dict:
    #   {"kind": "question"|"answer"|"feedback", "text": str, "time": str,
    #    "focus": str,                 # question only - short topic tag
    #    "strengths": [str], "gaps": [str], "improved": str}  # feedback only
    # The interviewer/coach turns come from ``pipeline.interview_turn``;
    # the candidate turns are appended by the tab when the user answers.
    interview_messages: list[dict] = field(default_factory=list)
    interview_running: bool = False
    interview_last_error: str = ""
    interview_done: bool = False

    job_url: str = ""
    job_text: str = ""
    job_text_source: str = ""  # "scrape" | "paste"

    resume: Optional[UploadedFile] = None
    linkedin: Optional[UploadedFile] = None

    github_url: str = ""
    github_skip: bool = False
    github_profile: Any = None  # GitHubProfile | None

    candidate: Optional[dict] = None
    job_spec: Optional[dict] = None
    match: Optional[dict] = None
    # Structured payload backing the fancy two-column Modern CV (teal
    # sidebar, leadership banner, project cards). Lives outside
    # ``documents`` because it is a JSON dict, not a markdown blob.
    modern_cv_data: Optional[dict] = None

    # Active palette + layout for the Modern CV / Cover Letter render.
    # The Documents tab's ``Change colour`` / ``Change layout`` cycle
    # buttons mutate this in place and re-render the preview without
    # touching ``modern_cv_data``. Persisted in the saved ``summary.json``
    # so re-opening a run from History reuses the same theme.
    modern_cv_theme: dict[str, str] = field(
        default_factory=lambda: {"palette": "teal", "layout": "two_column_sidebar"}
    )

    # Optional clarifying-question step. Empty when the user did not opt in
    # (Settings -> "Ask follow-up questions before each run") or the AI saw
    # no gaps worth asking about. Each followup_qa entry is
    # ``{topic, question, rationale, answer}`` - empty answer = the user
    # skipped that question.
    followup_questions: list[dict] = field(default_factory=list)
    followup_qa: list[dict] = field(default_factory=list)

    documents: dict[str, str] = field(default_factory=dict)
    refine_problems: dict[str, list[str]] = field(default_factory=dict)
    # The "Opravit dokument" panel on the Documents tab is collapsible so
    # the document preview gets the full height. Collapsed by default once
    # a document exists; forced open while no document has been generated
    # yet so the user can always reach the generate button.
    refine_open: bool = False

    activity: str = "ready"  # "ready" | "scraping" | "parsing" | "analyzing" | "generating" | "exporting" | "error"
    last_error: str = ""
    last_run_folder: str = ""
    target_role: str = ""
    # When True the pipeline short-circuits every AI call and returns
    # curated mock data from ``data.DEMO_*``. The orange ``DEMO`` pill
    # in the section header signals it to the user. Toggled via the
    # ``...`` overflow menu - see ``view.py``.
    demo_mode: bool = False

    # Footer "Run analysis" stage. Lives on STATE so the disabled state
    # survives the full section rebuild that fires after each pipeline
    # step (scrape, extract, follow-ups, match). One of:
    # "" (idle) | "running" | "followups" | "match".
    run_stage: str = ""

    runs_history: list[dict] = field(default_factory=list)

    def reset_run(self) -> None:
        """Wipe analysis-derived state; keep uploaded files."""
        self.candidate = None
        self.job_spec = None
        self.match = None
        self.modern_cv_data = None
        self.document_output_lang = ""
        self.followup_questions = []
        self.followup_qa = []
        self.documents.clear()
        self.refine_problems.clear()
        self.activity = "ready"
        self.last_error = ""
        self.last_run_folder = ""
        self.run_stage = ""
        self.reset_interview()

    def reset_chat(self) -> None:
        """Wipe the Chat-mode transcript and attachments."""
        self.chat_messages = []
        self.chat_attachments = {}
        self.chat_running = False
        self.chat_last_error = ""

    def reset_interview(self) -> None:
        """Wipe the Mock Interview transcript."""
        self.interview_messages = []
        self.interview_running = False
        self.interview_last_error = ""
        self.interview_done = False

    def reset_all(self) -> None:
        """Hard wipe used by the "New analysis" menu / quick action.

        Clears every input the user might have entered (job posting,
        resume, LinkedIn, GitHub URL / token preference, target role) on
        top of :meth:`reset_run` and :meth:`reset_chat`. The
        ``last_run_folder`` is intentionally cleared inside ``reset_run``
        so "Save complete analysis" creates a fresh folder for the next
        run.
        """
        self.reset_run()
        self.reset_chat()
        self.job_url = ""
        self.job_text = ""
        self.job_text_source = ""
        self.resume = None
        self.linkedin = None
        self.github_url = ""
        self.github_skip = False
        self.github_profile = None
        self.target_role = ""
        self.demo_mode = False

    def has_results(self) -> bool:
        return self.match is not None

    def can_run(self) -> bool:
        # Demo mode skips the input gate so users can press
        # "Run analysis" with no resume / no job posting and watch the
        # pipeline play back the curated payloads from
        # ``data.DEMO_*`` (still no AI calls).
        if self.demo_mode:
            return True
        return bool(self.resume and self.resume.text and self.job_text)


STATE = CareerState()
