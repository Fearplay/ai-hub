"""Module-level singleton state for the AI LinkedIn section.

The whole app rebuilds on theme/lang/section changes; persistent state has
to live outside ``build_view``. This singleton holds:

* the user's uploaded inputs (resume + optional LinkedIn export +
  GitHub username/url),
* target roles, audience and tone the candidate is aiming for,
* the extracted normalised LinkedIn profile (canonical JSON we feed
  every downstream call so we never re-send the raw resume text),
* every section the LinkedIn builder can produce: headlines, About
  variants, experience rewrites, skills buckets, featured items,
  projects, services, courses, recommendation messages, posts,
  completeness checklist, unsupported claims report, profile score,
* chat-mode transcript + attachments,
* the activity / run-stage flags powering the right-hand context
  panel and the cost / history sidecar,
* the demo-mode flag so the showcase flow works without an API key.

Each section keeps its own state singleton — no shared module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# Top-level mode - the section header tab bar switches between Chat and
# Builder. Chat is a free-form conversation with the LinkedIn voice
# expert; Builder runs the structured profile pipeline.
MODE_CHAT = "chat"
MODE_BUILDER = "builder"


# Sub-tabs inside the Builder mode.
TAB_SETUP = 0
TAB_SECTIONS = 1
TAB_OUTPUT = 2
TAB_HISTORY = 3


# Section IDs the builder can produce. Used both as keys in the picker
# (which sections to generate) and as anchors in the output tab.
SEC_HEADLINE = "headline"
SEC_ABOUT = "about"
SEC_EXPERIENCE = "experience"
SEC_EDUCATION = "education"
SEC_CERTIFICATIONS = "certifications"
SEC_SKILLS = "skills"
SEC_FEATURED = "featured"
SEC_PROJECTS = "projects"
SEC_SERVICES = "services"
SEC_COURSES = "courses"
SEC_RECOMMENDATIONS = "recommendations"
SEC_LANGUAGES = "languages"
SEC_VOLUNTEER = "volunteer"
SEC_PUBLICATIONS = "publications"
SEC_HONORS = "honors"
SEC_POSTS = "posts"
SEC_CHECKLIST = "checklist"


SECTION_IDS: tuple[str, ...] = (
    SEC_HEADLINE,
    SEC_ABOUT,
    SEC_EXPERIENCE,
    SEC_EDUCATION,
    SEC_CERTIFICATIONS,
    SEC_SKILLS,
    SEC_FEATURED,
    SEC_PROJECTS,
    SEC_SERVICES,
    SEC_COURSES,
    SEC_RECOMMENDATIONS,
    SEC_LANGUAGES,
    SEC_VOLUNTEER,
    SEC_PUBLICATIONS,
    SEC_HONORS,
    SEC_POSTS,
    SEC_CHECKLIST,
)


# Default preset: everything that needs an LLM call. Languages /
# volunteer / publications / honors are deterministic checklists that
# the UI always renders; they are not gated by the "what to generate"
# picker.
DEFAULT_SECTIONS: tuple[str, ...] = (
    SEC_HEADLINE,
    SEC_ABOUT,
    SEC_EXPERIENCE,
    SEC_SKILLS,
    SEC_FEATURED,
    SEC_PROJECTS,
    SEC_RECOMMENDATIONS,
    SEC_POSTS,
    SEC_CHECKLIST,
)


# Audience presets - who the LinkedIn profile should resonate with.
AUDIENCE_RECRUITER = "recruiter"
AUDIENCE_HIRING = "hiring_manager"
AUDIENCE_FOUNDER = "founder"
AUDIENCE_PEER = "peer"

AUDIENCE_OPTIONS: tuple[str, ...] = (
    AUDIENCE_RECRUITER,
    AUDIENCE_HIRING,
    AUDIENCE_FOUNDER,
    AUDIENCE_PEER,
)


# Tone presets - how the copy should read.
TONE_PROFESSIONAL = "professional"
TONE_JUNIOR_FRIENDLY = "junior_friendly"
TONE_SENIOR = "senior"
TONE_CONFIDENT_HONEST = "confident_honest"
TONE_TECHNICAL = "technical"
TONE_SIMPLE = "simple"
TONE_RECRUITER_FRIENDLY = "recruiter_friendly"

TONE_OPTIONS: tuple[str, ...] = (
    TONE_PROFESSIONAL,
    TONE_JUNIOR_FRIENDLY,
    TONE_SENIOR,
    TONE_CONFIDENT_HONEST,
    TONE_TECHNICAL,
    TONE_SIMPLE,
    TONE_RECRUITER_FRIENDLY,
)


# Post kinds the Posts generator supports. Each maps to a system-prompt
# variant inside ``prompts.py``.
POST_LEARNING_UPDATE = "learning_update"
POST_PROJECT_LAUNCH = "project_launch"
POST_JOB_SEARCH = "job_search"
POST_RECRUITER_OUTREACH = "recruiter_outreach"
POST_NETWORKING = "networking"
POST_COMMENT = "comment"

POST_KINDS: tuple[str, ...] = (
    POST_LEARNING_UPDATE,
    POST_PROJECT_LAUNCH,
    POST_JOB_SEARCH,
    POST_RECRUITER_OUTREACH,
    POST_NETWORKING,
    POST_COMMENT,
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
    message; the parsed text lives on :data:`LinkedInState.chat_attachments`
    so prompts can reference it without re-reading the disk.
    """

    role: str
    text: str
    time: str
    attachment_name: str = ""


@dataclass
class LinkedInState:
    mode: str = MODE_CHAT
    active_tab: int = TAB_SETUP

    # --- Inputs --------------------------------------------------------
    resume: Optional[UploadedFile] = None
    linkedin_export: Optional[UploadedFile] = None
    github_url: str = ""
    github_skip: bool = False
    github_profile: Any = None  # GitHubProfile | None

    # Free-form text the user pasted instead of (or in addition to) a
    # file - notes about the current role, what they want to highlight
    # next, etc. Always trimmed before sending.
    notes: str = ""

    # --- Targeting -----------------------------------------------------
    target_roles: list[str] = field(default_factory=list)
    audience: str = AUDIENCE_RECRUITER
    tone: str = TONE_PROFESSIONAL
    output_lang: str = ""  # "" means follow current UI language

    # Whether the pipeline should ask clarifying questions before the
    # first generation pass. The same dialog the AI Career section
    # already uses is cloned into this folder so the UX is consistent.
    ask_followups: bool = False

    # --- Section picker (which AI calls to run) ------------------------
    selected_sections: set[str] = field(default_factory=lambda: set(DEFAULT_SECTIONS))

    # --- Extracted normalised profile ---------------------------------
    extracted_profile: Optional[dict] = None

    # --- Generated outputs --------------------------------------------
    headlines: Optional[dict] = None
    about_variants: Optional[dict] = None
    experience_rewrites: Optional[dict] = None
    education_rewrites: Optional[dict] = None
    certifications_rewrites: Optional[dict] = None
    skills_buckets: Optional[dict] = None
    featured: Optional[dict] = None
    projects: Optional[dict] = None
    services: Optional[dict] = None
    courses: Optional[dict] = None
    recommendation_messages: Optional[dict] = None
    posts: Optional[dict] = None

    # Selected post kinds for the Posts generator. The user can tick
    # which kinds to produce in the Sections tab.
    selected_post_kinds: set[str] = field(
        default_factory=lambda: {
            POST_LEARNING_UPDATE,
            POST_PROJECT_LAUNCH,
        }
    )

    # Deterministic outputs (no LLM) ----------------------------------
    completeness: Optional[dict] = None
    unsupported_claims: Optional[dict] = None
    profile_score: Optional[dict] = None

    # Evidence index: maps a claim / skill to where we saw it
    # ("resume", "linkedin_export", "github", "user_confirmed",
    # "missing"). Populated as a side effect of the extraction step.
    evidence_index: dict[str, list[str]] = field(default_factory=dict)

    # --- Followups (clarifying questions) ------------------------------
    followup_questions: list[dict] = field(default_factory=list)
    followup_qa: list[dict] = field(default_factory=list)

    # --- Chat-mode transcript -----------------------------------------
    chat_messages: list[ChatMessage] = field(default_factory=list)
    chat_attachments: dict[str, str] = field(default_factory=dict)
    chat_running: bool = False
    chat_last_error: str = ""

    # --- UX flags ------------------------------------------------------
    activity: str = "ready"  # "ready" | "scraping" | "parsing" | "extracting" | "analyzing" | "generating" | "scoring" | "saving" | "error"
    run_stage: str = ""  # "" | "demo" | "running" | "followups" | "saving"
    last_error: str = ""
    last_run_folder: str = ""

    demo_mode: bool = False
    runs_history: list[dict] = field(default_factory=list)

    # Vertical scroll position of the Setup tab's QScrollArea, kept
    # across the full section rebuild that fires every time the user
    # drops a file / toggles a checkbox / etc. Without this, the tab
    # snaps back to the top after every ``rebuild()``, which is jarring
    # when the user is mid-scroll deep inside step 2 / step 3.
    setup_scroll_y: int = 0

    # --- Reset helpers -------------------------------------------------

    def reset_run(self) -> None:
        """Wipe analysis-derived state; keep uploaded files + targeting."""
        self.extracted_profile = None
        self.headlines = None
        self.about_variants = None
        self.experience_rewrites = None
        self.education_rewrites = None
        self.certifications_rewrites = None
        self.skills_buckets = None
        self.featured = None
        self.projects = None
        self.services = None
        self.courses = None
        self.recommendation_messages = None
        self.posts = None
        self.completeness = None
        self.unsupported_claims = None
        self.profile_score = None
        self.evidence_index = {}
        self.followup_questions = []
        self.followup_qa = []
        self.activity = "ready"
        self.run_stage = ""
        self.last_error = ""
        self.last_run_folder = ""

    def reset_chat(self) -> None:
        """Wipe the Chat-mode transcript and attachments."""
        self.chat_messages = []
        self.chat_attachments = {}
        self.chat_running = False
        self.chat_last_error = ""

    def reset_all(self) -> None:
        """Hard wipe used by the "New profile build" menu / quick action."""
        self.reset_run()
        self.reset_chat()
        self.resume = None
        self.linkedin_export = None
        self.github_url = ""
        self.github_skip = False
        self.github_profile = None
        self.notes = ""
        self.target_roles = []
        self.audience = AUDIENCE_RECRUITER
        self.tone = TONE_PROFESSIONAL
        self.output_lang = ""
        self.ask_followups = False
        self.selected_sections = set(DEFAULT_SECTIONS)
        self.selected_post_kinds = {
            POST_LEARNING_UPDATE,
            POST_PROJECT_LAUNCH,
        }
        self.demo_mode = False

    # --- Convenience predicates ---------------------------------------

    def has_results(self) -> bool:
        return bool(self.extracted_profile)

    def can_run(self) -> bool:
        if self.demo_mode:
            return True
        return bool(
            self.target_roles
            and (
                (self.resume and self.resume.text)
                or (self.linkedin_export and self.linkedin_export.text)
                or self.notes.strip()
            )
        )


STATE = LinkedInState()
