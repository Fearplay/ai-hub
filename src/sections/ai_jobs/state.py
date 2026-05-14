"""Module-level singleton state for the AI Jobs section.

The Qt-side ``build_view`` rebuilds whenever the user changes language,
theme, or section; this dataclass holds everything that must survive
those rebuilds:

* the active tab,
* the user's search inputs (keywords, location, work-mode filter,
  number of results, optional CV / "about me" text / LinkedIn URL),
* the list of positions returned by the last search (already
  URL-verified),
* the activity badge / last error / last saved run folder,
* a small in-memory mirror of the on-disk history so the History tab
  refreshes without a synchronous file read.

Module-level singleton because section folders are isolated by design
(see [sections.mdc](.cursor/rules/sections.mdc)) - the AI Jobs section
never shares state with other sections.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# Tab indices in the main tab bar.
TAB_SETUP = 0
TAB_RESULTS = 1
TAB_HISTORY = 2


# Work-mode filter (radios under the location field).
WORK_MODE_ANY = "any"
WORK_MODE_REMOTE = "remote"
WORK_MODE_HYBRID = "hybrid"
WORK_MODE_ONSITE = "onsite"

WORK_MODES = (
    WORK_MODE_ANY,
    WORK_MODE_REMOTE,
    WORK_MODE_HYBRID,
    WORK_MODE_ONSITE,
)


# Default location preset (matches the first entry in
# :func:`src.sections.ai_jobs.data.location_presets`).
DEFAULT_LOCATION_PRESET = "any"


# Bounds for the "max results" spinner. The upper bound stays modest
# because every extra position adds an HTTP verification round-trip on
# top of the second LLM call, and most users skim ten results anyway.
MAX_RESULTS_MIN = 3
MAX_RESULTS_MAX = 25
MAX_RESULTS_DEFAULT = 10


@dataclass
class UploadedFile:
    """Mirror of the AI Career uploaded-file record.

    Kept local to the section so the ai_career state never has to be
    imported from here - sections are isolated.
    """

    path: str
    name: str
    ext: str
    size_bytes: int
    text: str


@dataclass
class JobsState:
    active_tab: int = TAB_SETUP

    # --- search inputs -------------------------------------------------
    keywords: str = ""
    location_preset: str = DEFAULT_LOCATION_PRESET
    location_custom: str = ""
    work_mode: str = WORK_MODE_ANY
    max_results: int = MAX_RESULTS_DEFAULT

    # Optional profile - any combination is allowed. The pipeline picks
    # whichever is non-empty when it builds the prompt.
    profile_text: str = ""
    profile_file: Optional[UploadedFile] = None
    linkedin_url: str = ""

    # --- last search result -------------------------------------------
    # Each entry is a dict with ``title``, ``company``, ``location``,
    # ``posted``, ``summary``, ``url``, ``source`` (matches the JSON
    # schema in ``schema.py``). Already URL-verified so the Results tab
    # does not have to filter on render.
    results: list[dict] = field(default_factory=list)
    summary: str = ""
    last_query: str = ""
    last_query_label: str = ""
    last_location_label: str = ""
    last_run_folder: str = ""
    last_search_at: str = ""
    last_dropped: int = 0  # how many AI hits failed URL verification

    # --- activity / persistence ---------------------------------------
    activity: str = "ready"  # "ready" | "searching" | "extracting" | "verifying" | "saving" | "error"
    last_error: str = ""

    # In-memory mirror of the on-disk history. Populated by
    # ``pipeline.save_html`` so the History tab refreshes without a
    # sync file read.
    runs_history: list[dict] = field(default_factory=list)

    # --- mutators -----------------------------------------------------

    def reset_results(self) -> None:
        self.results = []
        self.summary = ""
        self.last_query = ""
        self.last_query_label = ""
        self.last_location_label = ""
        self.last_run_folder = ""
        self.last_search_at = ""
        self.last_dropped = 0
        self.activity = "ready"
        self.last_error = ""

    def reset_inputs(self) -> None:
        self.keywords = ""
        self.location_preset = DEFAULT_LOCATION_PRESET
        self.location_custom = ""
        self.work_mode = WORK_MODE_ANY
        self.max_results = MAX_RESULTS_DEFAULT
        self.profile_text = ""
        self.profile_file = None
        self.linkedin_url = ""

    def reset_all(self) -> None:
        self.reset_results()
        self.reset_inputs()
        self.active_tab = TAB_SETUP

    # --- predicates ---------------------------------------------------

    def has_results(self) -> bool:
        return bool(self.results)

    def can_run(self) -> bool:
        """At least one of: keywords, profile text, profile file, LinkedIn URL."""
        return bool(
            self.keywords.strip()
            or self.profile_text.strip()
            or (self.profile_file and self.profile_file.text)
            or self.linkedin_url.strip()
        )


STATE = JobsState()
