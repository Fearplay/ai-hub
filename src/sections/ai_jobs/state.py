"""Module-level singleton state for the AI Jobs section.

The Qt-side ``build_view`` rebuilds whenever the user changes language,
theme, or section; this dataclass holds everything that must survive
those rebuilds:

* the active tab,
* the user's search inputs (twelve step cards: keywords, profile,
  location, technologies + seniority, exclusions, sources picker,
  job age, work-mode + contract + result count filters, search mode,
  salary + output language),
* the list of positions returned by the last search (already
  URL-verified and match-scored),
* the aggregated skill-gap analysis,
* the activity badge / last error / last saved run folder,
* an in-memory mirror of the on-disk history + saved-profile list so
  the tabs refresh without a synchronous file read.

Module-level singleton because section folders are isolated by design
(see [sections.mdc](.cursor/rules/sections.mdc)) - the AI Jobs section
never shares state with other sections.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# Tab indices in the main tab bar. ``Skill gap`` slots in between
# ``Results`` and ``History`` because it depends on the result list -
# putting it next to History keeps the flow "Setup -> Results -> what
# is missing -> past runs".
TAB_SETUP = 0
TAB_RESULTS = 1
TAB_APPLICATIONS = 2
TAB_SKILL_GAP = 3
TAB_HISTORY = 4


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


# Seniority levels offered as pill buttons in step 4 (technologies).
SENIORITY_ANY = "any"
SENIORITY_JUNIOR = "junior"
SENIORITY_MEDIOR = "medior"
SENIORITY_SENIOR = "senior"
SENIORITY_LEAD = "lead"

SENIORITY_LEVELS = (
    SENIORITY_ANY,
    SENIORITY_JUNIOR,
    SENIORITY_MEDIOR,
    SENIORITY_SENIOR,
    SENIORITY_LEAD,
)


# Contract types - multi-select pills in the extended filters step.
CONTRACT_HPP = "hpp"
CONTRACT_ICO = "ico"
CONTRACT_CONTRACT = "contract"
CONTRACT_DPP_DPC = "dpp_dpc"
CONTRACT_INTERNSHIP = "internship"
CONTRACT_FREELANCE = "freelance"

CONTRACT_TYPES = (
    CONTRACT_HPP,
    CONTRACT_ICO,
    CONTRACT_CONTRACT,
    CONTRACT_DPP_DPC,
    CONTRACT_INTERNSHIP,
    CONTRACT_FREELANCE,
)


# Excluded work-type pills (multi-select).
EXCLUDE_NIGHT = "night"
EXCLUDE_SALES = "sales"
EXCLUDE_UNPAID = "unpaid"
EXCLUDE_ONSITE_ONLY = "onsite_only"

EXCLUDED_WORK_TYPES = (
    EXCLUDE_NIGHT,
    EXCLUDE_SALES,
    EXCLUDE_UNPAID,
    EXCLUDE_ONSITE_ONLY,
)


# Job-age presets (radio).
AGE_ANY = "any"
AGE_24H = "24h"
AGE_3D = "3d"
AGE_7D = "7d"
AGE_14D = "14d"
AGE_30D = "30d"

JOB_AGE_PRESETS = (AGE_ANY, AGE_24H, AGE_3D, AGE_7D, AGE_14D, AGE_30D)


# Search mode - drives how aggressive the discovery prompt is when
# expanding synonyms / adjacent roles.
MODE_EXACT = "exact"
MODE_SMART = "smart"
MODE_BROAD = "broad"
MODE_DISCOVERY = "discovery"

SEARCH_MODES = (MODE_EXACT, MODE_SMART, MODE_BROAD, MODE_DISCOVERY)


# Salary currencies (combobox). ``any`` means "do not filter".
CURRENCY_ANY = "any"
CURRENCY_CZK = "CZK"
CURRENCY_EUR = "EUR"
CURRENCY_USD = "USD"
CURRENCY_GBP = "GBP"
CURRENCY_PLN = "PLN"

SALARY_CURRENCIES = (
    CURRENCY_ANY,
    CURRENCY_CZK,
    CURRENCY_EUR,
    CURRENCY_USD,
    CURRENCY_GBP,
    CURRENCY_PLN,
)


# Output language for the AI prose - default tracks the global lang
# toggle, but the user can pin Czech or English explicitly.
OUTPUT_LANG_AUTO = "auto"
OUTPUT_LANG_EN = "en"
OUTPUT_LANG_CS = "cs"

OUTPUT_LANGUAGES = (OUTPUT_LANG_AUTO, OUTPUT_LANG_EN, OUTPUT_LANG_CS)


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

    # --- step 1: keywords ---------------------------------------------
    keywords: str = ""

    # --- step 2: profile (any combination is allowed) -----------------
    profile_text: str = ""
    profile_file: Optional[UploadedFile] = None
    linkedin_url: str = ""

    # --- step 3: location ---------------------------------------------
    location_preset: str = DEFAULT_LOCATION_PRESET
    location_custom: str = ""

    # --- step 4: technologies + seniority -----------------------------
    tech_skills: str = ""
    additional_experience: str = ""
    seniority: str = SENIORITY_ANY

    # --- step 5: exclusions -------------------------------------------
    excluded_keywords: str = ""
    excluded_companies: str = ""
    excluded_locations: str = ""
    excluded_work_types: set[str] = field(default_factory=set)

    # --- step 6: sources ----------------------------------------------
    # IDs come from :func:`src.sections.ai_jobs.data.sources_catalog`.
    # When the set is empty the pipeline falls back to the regional
    # ``preferred_boards()`` recommendations.
    selected_sources: set[str] = field(default_factory=set)
    custom_source_urls: str = ""

    # --- step 7: job age ----------------------------------------------
    job_age: str = AGE_ANY
    verify_active_links: bool = True
    show_without_date: bool = True

    # --- step 8: work-mode + contract + result count ------------------
    work_mode: str = WORK_MODE_ANY
    contract_types: set[str] = field(default_factory=set)
    max_results: int = MAX_RESULTS_DEFAULT

    # --- step 9: search mode ------------------------------------------
    search_mode: str = MODE_SMART

    # --- step 10: salary + output language ----------------------------
    salary_min: int = 0
    salary_currency: str = CURRENCY_ANY
    output_language: str = OUTPUT_LANG_AUTO

    # --- last search result -------------------------------------------
    # Each entry is a dict with ``title``, ``company``, ``location``,
    # ``posted``, ``posted_date_iso``, ``salary_text``, ``contract_type``,
    # ``summary``, ``url``, ``source``, ``work_mode``, ``is_active``,
    # ``inactive_reason`` (Pass 3 verifier output), and (after Pass 4)
    # ``match_score``, ``matched_skills``, ``missing_skills``,
    # ``recommendation``. Already URL-verified so the Results tab does
    # not have to filter on render. ``is_active=False`` postings stay
    # in the list so the user can review them - they are just sorted
    # to the bottom and tagged with the "No longer hiring" pill.
    results: list[dict] = field(default_factory=list)
    summary: str = ""
    last_query: str = ""
    last_query_label: str = ""
    last_location_label: str = ""
    last_run_folder: str = ""
    last_search_at: str = ""
    last_dropped: int = 0  # how many AI hits failed URL verification
    last_inactive: int = 0  # how many survivors are still listed but closed

    # Cross-run "new since last run" tagging (see ``seen_urls.py``).
    # ``last_new_count`` is how many of the current results were never
    # surfaced in an earlier run for this search; ``show_new_only`` is
    # the Results-tab filter toggle that hides previously-seen postings.
    last_new_count: int = 0
    show_new_only: bool = False

    # Aggregated skill-gap analysis. Populated by Pass 5 of the
    # pipeline. Shape:
    #   {"top_required": [{"skill": str, "count": int}, ...],
    #    "user_strong": [str, ...],
    #    "user_missing": [str, ...],
    #    "advice": [str, ...]}
    skill_gap: dict = field(default_factory=dict)

    # --- activity / persistence ---------------------------------------
    # Activity values:
    #   "ready" | "searching" | "extracting" | "verifying"
    #   "scoring" | "gap_analysis" | "saving" | "error"
    activity: str = "ready"
    last_error: str = ""

    # In-memory mirror of the on-disk history. Populated by
    # ``pipeline.save_html`` so the History tab refreshes without a
    # sync file read.
    runs_history: list[dict] = field(default_factory=list)

    # In-memory mirror of the saved search profiles (Step 12). Filled
    # from ``profiles_store`` on the first build.
    saved_profiles: list[dict] = field(default_factory=list)

    # Scroll position memory for the tabs that own a QScrollArea.
    # Every chip / checkbox / filter click triggers a section rebuild
    # (see ``src.app.request_section_refresh``) which throws away the
    # old scroll widget; without these the user's view jumps back to
    # the top on every interaction. Restored via ``QTimer.singleShot``
    # right after ``build_*_tab`` materialises the new scroll area.
    setup_scroll_pos: int = 0
    results_scroll_pos: int = 0

    # Demo mode flag - set by future smoke tests / docs runs. When
    # ``True`` the pipeline returns curated mock data without spending
    # tokens. The UI does not expose a toggle yet, but the pipeline
    # respects it per ``.cursor/rules/ai-section.mdc``.
    demo_mode: bool = False

    # Follow-up clarifying questions (analogous to AI Career):
    # Pass 0 inspects the user's profile + criteria and lists 0-8
    # questions about ambiguities (seniority mismatch, missing
    # remote/salary preference, "you said Python but not how many
    # years" etc.). The modal opens BEFORE Pass 1 (discovery) so the
    # search prompt - and every later prompt - can include the user's
    # clarifications as ground truth. Skipped when
    # ``settings_store.get_ask_followups()`` is False or when the AI
    # produces zero questions.
    followup_questions: list[dict] = field(default_factory=list)
    followup_qa: list[dict] = field(default_factory=list)

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
        self.last_inactive = 0
        self.last_new_count = 0
        self.show_new_only = False
        self.skill_gap = {}
        self.activity = "ready"
        self.last_error = ""
        self.followup_questions = []
        self.followup_qa = []
        # The Results tab is empty after a reset - sending the user to
        # an old scroll position would either clamp to 0 anyway or
        # restore a confusing offset. Reset explicitly for clarity.
        self.results_scroll_pos = 0

    def reset_inputs(self) -> None:
        # Wiping every field also wipes the user's place in the form -
        # they are starting over so jumping back to the top is correct.
        self.setup_scroll_pos = 0
        self.keywords = ""
        self.profile_text = ""
        self.profile_file = None
        self.linkedin_url = ""
        self.location_preset = DEFAULT_LOCATION_PRESET
        self.location_custom = ""
        self.tech_skills = ""
        self.additional_experience = ""
        self.seniority = SENIORITY_ANY
        self.excluded_keywords = ""
        self.excluded_companies = ""
        self.excluded_locations = ""
        self.excluded_work_types = set()
        self.selected_sources = set()
        self.custom_source_urls = ""
        self.job_age = AGE_ANY
        self.verify_active_links = True
        self.show_without_date = True
        self.work_mode = WORK_MODE_ANY
        self.contract_types = set()
        self.max_results = MAX_RESULTS_DEFAULT
        self.search_mode = MODE_SMART
        self.salary_min = 0
        self.salary_currency = CURRENCY_ANY
        self.output_language = OUTPUT_LANG_AUTO

    def reset_all(self) -> None:
        self.reset_results()
        self.reset_inputs()
        self.active_tab = TAB_SETUP

    # --- predicates ---------------------------------------------------

    def has_results(self) -> bool:
        return bool(self.results)

    def active_results_count(self) -> int:
        """Return the count of postings the user can actually apply to.

        Excludes anything the URL verifier marked ``is_active=False``
        (404s, expired postings, "no longer accepting applications"
        banners, …) so the headline number on the Results tab and in
        the right-hand context panel matches what the user is allowed
        to act on. Closed listings are still rendered in the list -
        they just sort to the bottom and do not contribute to the
        "X active openings" badge.
        """
        return sum(1 for item in self.results if item.get("is_active", True))

    def has_skill_gap(self) -> bool:
        return bool(self.skill_gap)

    def has_profile(self) -> bool:
        """True when the user provided any profile material.

        Used to decide whether the skill-gap pass makes sense - we
        only score against the user when we actually have a CV / bio
        / LinkedIn to compare against.
        """
        return bool(
            self.profile_text.strip()
            or (self.profile_file and self.profile_file.text)
            or self.linkedin_url.strip()
            or self.tech_skills.strip()
            or self.additional_experience.strip()
        )

    def can_run(self) -> bool:
        """At least one of: keywords, profile text, profile file, LinkedIn URL, skills."""
        return bool(
            self.keywords.strip()
            or self.profile_text.strip()
            or (self.profile_file and self.profile_file.text)
            or self.linkedin_url.strip()
            or self.tech_skills.strip()
        )


STATE = JobsState()
