"""Static data for the AI Jobs section.

* :data:`SECTION_ICON` - icon used by the sidebar / header bar.
* :data:`ACCENT` - accent colour the shared header treats as the
  section's primary tone.
* :func:`tabs` - localised labels for the centre tab bar (Setup /
  Results / Skill gap / History).
* :func:`location_presets` - the fixed list of location options shown in
  the setup dropdown. The first column is the preset id (saved on
  STATE), the second column is the human label, the third column is
  the canonical region string we feed to the prompt (so AI knows to
  e.g. only return EU postings). The "any" entry leaves the location
  field unconstrained, "custom" hands control over to a free-text
  field rendered next to the dropdown.
* :func:`work_modes` - localised labels for the radio group.
* :func:`seniority_levels`, :func:`contract_types`, :func:`job_age_presets`,
  :func:`search_modes`, :func:`salary_currencies`,
  :func:`excluded_work_type_presets`, :func:`output_languages` -
  localised label tables for the new step cards (skills, exclusions,
  age, mode, salary, output language).
* :data:`SOURCES_CATALOG` + :func:`source_categories` - the user-driven
  sources picker. ~50 portals grouped into 7 categories (Recommended /
  Global / Remote / Europe / CZ-SK / Tech-Startup / Freelance). Each
  entry has a stable id used by ``STATE.selected_sources``.
* :data:`PREFERRED_BOARDS` - the legacy region -> board hint table.
  Kept as the fallback when the user did not pick anything explicit
  in the new Sources step.
"""

from __future__ import annotations

from src.qt.icons import Icons
from src.sections.ai_jobs.state import (
    AGE_24H,
    AGE_3D,
    AGE_7D,
    AGE_14D,
    AGE_30D,
    AGE_ANY,
    CONTRACT_CONTRACT,
    CONTRACT_DPP_DPC,
    CONTRACT_FREELANCE,
    CONTRACT_HPP,
    CONTRACT_ICO,
    CONTRACT_INTERNSHIP,
    CURRENCY_ANY,
    CURRENCY_CZK,
    CURRENCY_EUR,
    CURRENCY_GBP,
    CURRENCY_PLN,
    CURRENCY_USD,
    EXCLUDE_NIGHT,
    EXCLUDE_ONSITE_ONLY,
    EXCLUDE_SALES,
    EXCLUDE_UNPAID,
    MODE_BROAD,
    MODE_DISCOVERY,
    MODE_EXACT,
    MODE_SMART,
    OUTPUT_LANG_AUTO,
    OUTPUT_LANG_CS,
    OUTPUT_LANG_EN,
    SENIORITY_ANY,
    SENIORITY_JUNIOR,
    SENIORITY_LEAD,
    SENIORITY_MEDIOR,
    SENIORITY_SENIOR,
    WORK_MODE_ANY,
    WORK_MODE_HYBRID,
    WORK_MODE_ONSITE,
    WORK_MODE_REMOTE,
)
from src.sections.ai_jobs.strings import s


SECTION_ICON = Icons.PERSON_SEARCH_OUTLINED

# Picks a calmer indigo so the section sits visually between AI Career
# (default blue) and AI Legal (purple) - matches the "search the web"
# vibe without clashing with adjacent accents.
ACCENT = "#6366F1"


def tabs(lang: str) -> list[str]:
    txt = s(lang)
    return [
        txt["tab_setup"],
        txt["tab_results"],
        txt["tab_skill_gap"],
        txt["tab_history"],
    ]


# Location presets used by the dropdown in tab_setup. ``query`` is the
# canonical region string the prompt builder injects; "" means "do not
# constrain the location" and "custom" defers to the free-text field.
def location_presets(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"id": "any", "label": txt["loc_any"], "query": ""},
        {"id": "remote_world", "label": txt["loc_remote_world"], "query": "Remote (worldwide)"},
        {"id": "eu", "label": txt["loc_eu"], "query": "European Union"},
        {"id": "usa", "label": txt["loc_usa"], "query": "United States"},
        {"id": "uk", "label": txt["loc_uk"], "query": "United Kingdom"},
        {"id": "cz", "label": txt["loc_cz"], "query": "Czech Republic"},
        {"id": "sk", "label": txt["loc_sk"], "query": "Slovakia"},
        {"id": "de", "label": txt["loc_de"], "query": "Germany"},
        {"id": "at", "label": txt["loc_at"], "query": "Austria"},
        {"id": "pl", "label": txt["loc_pl"], "query": "Poland"},
        {"id": "praha", "label": txt["loc_praha"], "query": "Prague, Czech Republic"},
        {"id": "brno", "label": txt["loc_brno"], "query": "Brno, Czech Republic"},
        {"id": "ostrava", "label": txt["loc_ostrava"], "query": "Ostrava, Czech Republic"},
        {"id": "custom", "label": txt["loc_custom"], "query": ""},
    ]


def work_modes(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"id": WORK_MODE_ANY, "label": txt["mode_any"]},
        {"id": WORK_MODE_REMOTE, "label": txt["mode_remote"]},
        {"id": WORK_MODE_HYBRID, "label": txt["mode_hybrid"]},
        {"id": WORK_MODE_ONSITE, "label": txt["mode_onsite"]},
    ]


# Region -> preferred job boards. Plumbed straight into the prompt as
# "Search across these boards AND direct company career pages". The
# order is intentional: we put the **most diverse / region-specific**
# boards first so the model doesn't anchor on whatever name is at the
# top of the list (in earlier iterations LinkedIn was first and the
# model returned only LinkedIn URLs). LinkedIn is kept in every list
# but pushed to the end so it's a fallback, not the default.
#
# Direct company career pages (`<company>.com/careers`, `Greenhouse`,
# `Lever`, `Workable`, `SmartRecruiters`, `Personio`) are always
# enumerated by the prompt builder regardless of region, because
# many active postings live ONLY on the ATS / company site and never
# get syndicated to a board.
PREFERRED_BOARDS: dict[str, tuple[str, ...]] = {
    "any": (
        "Indeed",
        "Glassdoor",
        "ZipRecruiter",
        "Monster",
        "Welcome to the Jungle",
        "Wellfound (AngelList Talent)",
        "Hexjobs",
        "Go Onwards",
        "Built In",
        "SimplyHired",
        "LinkedIn Jobs",
    ),
    "eu": (
        "EURES (eures.europa.eu)",
        "Welcome to the Jungle",
        "StepStone",
        "Indeed (country domains)",
        "Hexjobs",
        "Go Onwards",
        "EUJOBS",
        "InfoJobs",
        "Glassdoor",
        "Monster Europe",
        "LinkedIn Jobs",
    ),
    "usa": (
        "Indeed",
        "ZipRecruiter",
        "Glassdoor",
        "Monster",
        "CareerBuilder",
        "SimplyHired",
        "Built In",
        "Dice (tech)",
        "Wellfound (startups)",
        "FlexJobs",
        "The Muse",
        "Lensa",
        "USAJOBS (federal)",
        "LinkedIn Jobs",
    ),
    "uk": (
        "Indeed UK",
        "Reed.co.uk",
        "TotalJobs",
        "CV-Library",
        "CWJobs (tech)",
        "Jobsite",
        "Adzuna UK",
        "Guardian Jobs",
        "Monster UK",
        "LinkedIn Jobs",
    ),
    "cz": (
        "jobs.cz",
        "prace.cz",
        "StartupJobs.cz",
        "JenPrace.cz",
        "Welcome to the Jungle (Czech Republic)",
        "Profesia.cz",
        "EasyJobs.cz",
        "IT.jobs.cz",
        "Pracomat.cz",
        "Indeed.cz",
        "LinkedIn Jobs",
    ),
    "sk": (
        "Profesia.sk",
        "Kariera.sk",
        "Jobs.sk",
        "Pracuj.sk",
        "ITrobot.sk",
        "Index.sme.sk",
        "EURES Slovakia",
        "LinkedIn Jobs",
    ),
    "de": (
        "StepStone",
        "Indeed Deutschland",
        "Xing Jobs",
        "Get In IT",
        "Stellenanzeigen.de",
        "Monster.de",
        "Jobware",
        "Jobs.de",
        "Karriere.de",
        "Honeypot (tech)",
        "LinkedIn Jobs",
    ),
    "at": (
        "karriere.at",
        "StepStone Austria",
        "Indeed Austria",
        "Der Standard Karriere",
        "Monster.at",
        "Jobs.at",
        "Willhaben Jobs",
        "EURES Austria",
        "LinkedIn Jobs",
    ),
    "pl": (
        "Pracuj.pl",
        "No Fluff Jobs",
        "JustJoin.IT",
        "OLX Praca",
        "GoldenLine",
        "GoWork",
        "InfoPraca",
        "RocketJobs.pl",
        "Indeed Polska",
        "LinkedIn Jobs",
    ),
    "praha": (
        "jobs.cz",
        "prace.cz",
        "StartupJobs.cz",
        "Welcome to the Jungle (Prague)",
        "JenPrace.cz",
        "IT.jobs.cz",
        "Indeed.cz",
        "Atmoskop",
        "EasyJobs.cz",
        "LinkedIn Jobs",
    ),
    "brno": (
        "jobs.cz",
        "prace.cz",
        "StartupJobs.cz",
        "JenPrace.cz",
        "Indeed.cz",
        "IT.jobs.cz",
        "Atmoskop",
        "LinkedIn Jobs",
    ),
    "ostrava": (
        "jobs.cz",
        "prace.cz",
        "JenPrace.cz",
        "Indeed.cz",
        "Atmoskop",
        "LinkedIn Jobs",
    ),
    "remote_world": (
        "We Work Remotely",
        "Remote OK",
        "Remotive",
        "Wellfound (remote filter)",
        "Working Nomads",
        "JustRemote",
        "FlexJobs",
        "NoDesk",
        "Jobspresso",
        "Authentic Jobs",
        "Remote.co",
        "Built In Remote",
        "EU Remote Jobs",
        "LinkedIn Jobs",
    ),
}


# Generic ATS / career-page hint appended to every prompt regardless of
# region - a huge slice of mid-senior postings never leaves these pages.
ATS_AND_CAREER_PAGES: tuple[str, ...] = (
    "direct company career pages (e.g. company.com/careers, /jobs, /work-with-us)",
    "Greenhouse-hosted boards (boards.greenhouse.io/<company>)",
    "Lever-hosted boards (jobs.lever.co/<company>)",
    "Workable-hosted boards (apply.workable.com/<company>)",
    "Ashby-hosted boards (jobs.ashbyhq.com/<company>)",
    "SmartRecruiters (jobs.smartrecruiters.com/<company>)",
    "Personio (jobs.personio.com/<company>)",
    "Recruitee-hosted boards (<company>.recruitee.com)",
    "Teamtailor-hosted boards (career.<company>.com)",
)


def preferred_boards(preset_id: str) -> tuple[str, ...]:
    """Return the suggested job boards for a preset id (or the global default)."""
    return PREFERRED_BOARDS.get(preset_id, PREFERRED_BOARDS["any"])


# ---------------------------------------------------------------------------
# Step 4 - seniority levels (pill buttons)
# ---------------------------------------------------------------------------


def seniority_levels(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"id": SENIORITY_ANY, "label": txt["seniority_any"]},
        {"id": SENIORITY_JUNIOR, "label": txt["seniority_junior"]},
        {"id": SENIORITY_MEDIOR, "label": txt["seniority_medior"]},
        {"id": SENIORITY_SENIOR, "label": txt["seniority_senior"]},
        {"id": SENIORITY_LEAD, "label": txt["seniority_lead"]},
    ]


# ---------------------------------------------------------------------------
# Step 5 - exclusion presets (multi-select pills)
# ---------------------------------------------------------------------------


def excluded_work_type_presets(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"id": EXCLUDE_NIGHT, "label": txt["exclude_night"]},
        {"id": EXCLUDE_SALES, "label": txt["exclude_sales"]},
        {"id": EXCLUDE_UNPAID, "label": txt["exclude_unpaid"]},
        {"id": EXCLUDE_ONSITE_ONLY, "label": txt["exclude_onsite_only"]},
    ]


# ---------------------------------------------------------------------------
# Step 6 - sources catalogue (chip-toggle grid grouped by category)
# ---------------------------------------------------------------------------


# Category ids used to group ``SOURCES_CATALOG`` in the UI. Keys are
# stable; labels come from ``strings.py``.
CATEGORY_RECOMMENDED = "recommended"
CATEGORY_GLOBAL = "global"
CATEGORY_REMOTE = "remote"
CATEGORY_EUROPE = "europe"
CATEGORY_CZ_SK = "cz_sk"
CATEGORY_TECH = "tech"
CATEGORY_FREELANCE = "freelance"

SOURCE_CATEGORY_ORDER: tuple[str, ...] = (
    CATEGORY_RECOMMENDED,
    CATEGORY_GLOBAL,
    CATEGORY_REMOTE,
    CATEGORY_EUROPE,
    CATEGORY_CZ_SK,
    CATEGORY_TECH,
    CATEGORY_FREELANCE,
)


# Catalogue of selectable sources. Stable ids are saved to
# ``STATE.selected_sources``. ``query_hint`` is the verbatim string we
# feed the discovery prompt - keeping it separate from ``label`` lets
# us localise the label without breaking the prompt contract.
SOURCES_CATALOG: tuple[dict, ...] = (
    # Recommended - default-on for first-time users; matches the
    # selected region in the legacy ``preferred_boards`` table.
    {"id": "recommended_for_region", "label_key": "src_recommended_for_region", "category": CATEGORY_RECOMMENDED, "query_hint": "Recommended boards for the selected region"},

    # Global -----------------------------------------------------------
    {"id": "linkedin_jobs", "label_key": "src_linkedin_jobs", "category": CATEGORY_GLOBAL, "query_hint": "LinkedIn Jobs (linkedin.com/jobs)"},
    {"id": "indeed", "label_key": "src_indeed", "category": CATEGORY_GLOBAL, "query_hint": "Indeed (indeed.com)"},
    {"id": "glassdoor", "label_key": "src_glassdoor", "category": CATEGORY_GLOBAL, "query_hint": "Glassdoor (glassdoor.com)"},
    {"id": "google_jobs", "label_key": "src_google_jobs", "category": CATEGORY_GLOBAL, "query_hint": "Google Jobs"},
    {"id": "jooble", "label_key": "src_jooble", "category": CATEGORY_GLOBAL, "query_hint": "Jooble (jooble.org)"},
    {"id": "talent_com", "label_key": "src_talent_com", "category": CATEGORY_GLOBAL, "query_hint": "Talent.com"},
    {"id": "monster", "label_key": "src_monster", "category": CATEGORY_GLOBAL, "query_hint": "Monster"},
    {"id": "careerbuilder", "label_key": "src_careerbuilder", "category": CATEGORY_GLOBAL, "query_hint": "CareerBuilder"},
    {"id": "ziprecruiter", "label_key": "src_ziprecruiter", "category": CATEGORY_GLOBAL, "query_hint": "ZipRecruiter (ziprecruiter.com)"},
    {"id": "simplyhired", "label_key": "src_simplyhired", "category": CATEGORY_GLOBAL, "query_hint": "SimplyHired (simplyhired.com)"},
    {"id": "adzuna", "label_key": "src_adzuna", "category": CATEGORY_GLOBAL, "query_hint": "Adzuna (adzuna.* country domains)"},
    {"id": "themuse", "label_key": "src_themuse", "category": CATEGORY_GLOBAL, "query_hint": "The Muse (themuse.com)"},

    # Remote -----------------------------------------------------------
    {"id": "we_work_remotely", "label_key": "src_we_work_remotely", "category": CATEGORY_REMOTE, "query_hint": "We Work Remotely (weworkremotely.com)"},
    {"id": "remote_ok", "label_key": "src_remote_ok", "category": CATEGORY_REMOTE, "query_hint": "Remote OK (remoteok.com)"},
    {"id": "remotive", "label_key": "src_remotive", "category": CATEGORY_REMOTE, "query_hint": "Remotive (remotive.com)"},
    {"id": "flexjobs", "label_key": "src_flexjobs", "category": CATEGORY_REMOTE, "query_hint": "FlexJobs (flexjobs.com)"},
    {"id": "working_nomads", "label_key": "src_working_nomads", "category": CATEGORY_REMOTE, "query_hint": "Working Nomads"},
    {"id": "himalayas", "label_key": "src_himalayas", "category": CATEGORY_REMOTE, "query_hint": "Himalayas (himalayas.app)"},
    {"id": "wttj", "label_key": "src_wttj", "category": CATEGORY_REMOTE, "query_hint": "Welcome to the Jungle / Otta"},
    {"id": "remote_co", "label_key": "src_remote_co", "category": CATEGORY_REMOTE, "query_hint": "Remote.co"},
    {"id": "justremote", "label_key": "src_justremote", "category": CATEGORY_REMOTE, "query_hint": "JustRemote (justremote.co)"},
    {"id": "nodesk", "label_key": "src_nodesk", "category": CATEGORY_REMOTE, "query_hint": "NoDesk (nodesk.co)"},
    {"id": "jobspresso", "label_key": "src_jobspresso", "category": CATEGORY_REMOTE, "query_hint": "Jobspresso (jobspresso.co)"},
    {"id": "fourdayweek", "label_key": "src_fourdayweek", "category": CATEGORY_REMOTE, "query_hint": "4 Day Week (4dayweek.io)"},

    # Europe -----------------------------------------------------------
    {"id": "eures", "label_key": "src_eures", "category": CATEGORY_EUROPE, "query_hint": "EURES (eures.europa.eu)"},
    {"id": "eurojobs", "label_key": "src_eurojobs", "category": CATEGORY_EUROPE, "query_hint": "Eurojobs"},
    {"id": "euraxess", "label_key": "src_euraxess", "category": CATEGORY_EUROPE, "query_hint": "Euraxess (euraxess.ec.europa.eu)"},
    {"id": "jobsinnetwork", "label_key": "src_jobsinnetwork", "category": CATEGORY_EUROPE, "query_hint": "Jobs in Network"},
    {"id": "europe_language_jobs", "label_key": "src_europe_language_jobs", "category": CATEGORY_EUROPE, "query_hint": "Europe Language Jobs"},
    {"id": "stepstone", "label_key": "src_stepstone", "category": CATEGORY_EUROPE, "query_hint": "StepStone (stepstone.com / .de / .fr)"},
    {"id": "pracuj_pl", "label_key": "src_pracuj_pl", "category": CATEGORY_EUROPE, "query_hint": "Pracuj.pl"},
    {"id": "xing_jobs", "label_key": "src_xing_jobs", "category": CATEGORY_EUROPE, "query_hint": "Xing Jobs (xing.com/jobs)"},
    {"id": "karriere_at", "label_key": "src_karriere_at", "category": CATEGORY_EUROPE, "query_hint": "karriere.at"},
    {"id": "reed_uk", "label_key": "src_reed_uk", "category": CATEGORY_EUROPE, "query_hint": "Reed.co.uk"},
    {"id": "totaljobs", "label_key": "src_totaljobs", "category": CATEGORY_EUROPE, "query_hint": "TotalJobs (totaljobs.com)"},

    # Czech Republic / Slovakia ---------------------------------------
    {"id": "jobs_cz", "label_key": "src_jobs_cz", "category": CATEGORY_CZ_SK, "query_hint": "jobs.cz"},
    {"id": "prace_cz", "label_key": "src_prace_cz", "category": CATEGORY_CZ_SK, "query_hint": "prace.cz"},
    {"id": "startupjobs_cz", "label_key": "src_startupjobs_cz", "category": CATEGORY_CZ_SK, "query_hint": "StartupJobs.cz"},
    {"id": "atmoskop", "label_key": "src_atmoskop", "category": CATEGORY_CZ_SK, "query_hint": "Atmoskop (atmoskop.cz)"},
    {"id": "dobra_prace", "label_key": "src_dobra_prace", "category": CATEGORY_CZ_SK, "query_hint": "Dobra prace (dobraprace.cz)"},
    {"id": "profesia_sk", "label_key": "src_profesia_sk", "category": CATEGORY_CZ_SK, "query_hint": "Profesia.sk"},
    {"id": "kariera_sk", "label_key": "src_kariera_sk", "category": CATEGORY_CZ_SK, "query_hint": "Kariera.sk"},
    {"id": "pretlak", "label_key": "src_pretlak", "category": CATEGORY_CZ_SK, "query_hint": "Pretlak.com"},
    {"id": "jenprace", "label_key": "src_jenprace", "category": CATEGORY_CZ_SK, "query_hint": "JenPrace.cz"},
    {"id": "it_jobs_cz", "label_key": "src_it_jobs_cz", "category": CATEGORY_CZ_SK, "query_hint": "IT.jobs.cz"},
    {"id": "pracomat", "label_key": "src_pracomat", "category": CATEGORY_CZ_SK, "query_hint": "Pracomat.cz"},
    {"id": "easyjobs_cz", "label_key": "src_easyjobs_cz", "category": CATEGORY_CZ_SK, "query_hint": "EasyJobs.cz"},
    {"id": "wttj_cz", "label_key": "src_wttj_cz", "category": CATEGORY_CZ_SK, "query_hint": "Welcome to the Jungle Czechia (welcometothejungle.com/en/companies?country=Czechia)"},
    {"id": "praca_sk", "label_key": "src_praca_sk", "category": CATEGORY_CZ_SK, "query_hint": "Praca.sk"},

    # Tech / Startup ---------------------------------------------------
    {"id": "wellfound", "label_key": "src_wellfound", "category": CATEGORY_TECH, "query_hint": "Wellfound / AngelList Talent (wellfound.com)"},
    {"id": "hn_who_is_hiring", "label_key": "src_hn_who_is_hiring", "category": CATEGORY_TECH, "query_hint": "Hacker News 'Who is hiring' threads"},
    {"id": "yc_jobs", "label_key": "src_yc_jobs", "category": CATEGORY_TECH, "query_hint": "Y Combinator Jobs (workatastartup.com)"},
    {"id": "github_hiring", "label_key": "src_github_hiring", "category": CATEGORY_TECH, "query_hint": "GitHub hiring posts (README hiring sections, /careers links from repos)"},
    {"id": "stackoverflow_companies", "label_key": "src_stackoverflow_companies", "category": CATEGORY_TECH, "query_hint": "Stack Overflow company pages"},
    {"id": "no_fluff_jobs", "label_key": "src_no_fluff_jobs", "category": CATEGORY_TECH, "query_hint": "No Fluff Jobs (nofluffjobs.com)"},
    {"id": "landing_jobs", "label_key": "src_landing_jobs", "category": CATEGORY_TECH, "query_hint": "Landing.jobs"},
    {"id": "honeypot", "label_key": "src_honeypot", "category": CATEGORY_TECH, "query_hint": "Honeypot (honeypot.io)"},
    {"id": "dice", "label_key": "src_dice", "category": CATEGORY_TECH, "query_hint": "Dice (dice.com)"},
    {"id": "builtin", "label_key": "src_builtin", "category": CATEGORY_TECH, "query_hint": "Built In (builtin.com)"},
    {"id": "justjoinit", "label_key": "src_justjoinit", "category": CATEGORY_TECH, "query_hint": "JustJoin.IT (justjoin.it)"},
    {"id": "otta", "label_key": "src_otta", "category": CATEGORY_TECH, "query_hint": "Otta (otta.com / app.welcometothejungle.com)"},
    {"id": "techstars_jobs", "label_key": "src_techstars_jobs", "category": CATEGORY_TECH, "query_hint": "Techstars Jobs (techstars.com/jobs)"},

    # Freelance / contracts -------------------------------------------
    {"id": "upwork", "label_key": "src_upwork", "category": CATEGORY_FREELANCE, "query_hint": "Upwork"},
    {"id": "freelancer", "label_key": "src_freelancer", "category": CATEGORY_FREELANCE, "query_hint": "Freelancer.com"},
    {"id": "fiverr", "label_key": "src_fiverr", "category": CATEGORY_FREELANCE, "query_hint": "Fiverr"},
    {"id": "toptal", "label_key": "src_toptal", "category": CATEGORY_FREELANCE, "query_hint": "Toptal"},
    {"id": "contra", "label_key": "src_contra", "category": CATEGORY_FREELANCE, "query_hint": "Contra (contra.com)"},
    {"id": "malt", "label_key": "src_malt", "category": CATEGORY_FREELANCE, "query_hint": "Malt (malt.com)"},
    {"id": "peopleperhour", "label_key": "src_peopleperhour", "category": CATEGORY_FREELANCE, "query_hint": "PeoplePerHour"},
    {"id": "arc_dev", "label_key": "src_arc_dev", "category": CATEGORY_FREELANCE, "query_hint": "Arc.dev (arc.dev)"},
    {"id": "gun_io", "label_key": "src_gun_io", "category": CATEGORY_FREELANCE, "query_hint": "Gun.io"},
    {"id": "guru", "label_key": "src_guru", "category": CATEGORY_FREELANCE, "query_hint": "Guru.com"},
)


def sources_catalog(lang: str) -> list[dict]:
    """Return the localised catalogue (label resolved per ``lang``)."""
    txt = s(lang)
    out: list[dict] = []
    for entry in SOURCES_CATALOG:
        out.append({
            "id": entry["id"],
            "label": txt.get(entry["label_key"], entry["query_hint"]),
            "category": entry["category"],
            "query_hint": entry["query_hint"],
        })
    return out


def source_categories(lang: str) -> list[dict]:
    """Return ``[{id, label, items: [<source>...]}]`` ordered for the UI."""
    txt = s(lang)
    catalog = sources_catalog(lang)
    grouped: dict[str, list[dict]] = {cat: [] for cat in SOURCE_CATEGORY_ORDER}
    for entry in catalog:
        grouped.setdefault(entry["category"], []).append(entry)
    return [
        {
            "id": cat,
            "label": txt.get(f"src_category_{cat}", cat.title()),
            "items": grouped.get(cat, []),
        }
        for cat in SOURCE_CATEGORY_ORDER
    ]


def resolve_source_hints(*, selected_ids: set[str], location_preset_id: str) -> list[str]:
    """Map ``STATE.selected_sources`` to the prompt-ready hint list.

    When the user did not pick anything (or only picked the
    "recommended" preset), we fall back to ``preferred_boards`` for the
    current region so the prompt still has something concrete. When
    the user picked individual sources, the recommended preset is
    expanded into the region boards as well so it composes rather than
    overrides.
    """
    if not selected_ids:
        return list(preferred_boards(location_preset_id))

    hints: list[str] = []
    seen: set[str] = set()

    def _push(value: str) -> None:
        if value and value not in seen:
            seen.add(value)
            hints.append(value)

    for entry in SOURCES_CATALOG:
        if entry["id"] in selected_ids and entry["id"] != "recommended_for_region":
            _push(entry["query_hint"])

    if "recommended_for_region" in selected_ids:
        for board in preferred_boards(location_preset_id):
            _push(board)

    return hints


# ---------------------------------------------------------------------------
# Step 7 - job-age presets (radio)
# ---------------------------------------------------------------------------


def job_age_presets(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"id": AGE_ANY, "label": txt["age_any"], "days": None},
        {"id": AGE_24H, "label": txt["age_24h"], "days": 1},
        {"id": AGE_3D, "label": txt["age_3d"], "days": 3},
        {"id": AGE_7D, "label": txt["age_7d"], "days": 7},
        {"id": AGE_14D, "label": txt["age_14d"], "days": 14},
        {"id": AGE_30D, "label": txt["age_30d"], "days": 30},
    ]


def job_age_days(preset_id: str) -> int:
    """Return the day-count for an age preset (or 0 for 'any')."""
    for entry in job_age_presets("en"):
        if entry["id"] == preset_id:
            return entry["days"] or 0
    return 0


# ---------------------------------------------------------------------------
# Step 8 - contract types (multi-select pills)
# ---------------------------------------------------------------------------


def contract_types(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"id": CONTRACT_HPP, "label": txt["contract_hpp"]},
        {"id": CONTRACT_ICO, "label": txt["contract_ico"]},
        {"id": CONTRACT_CONTRACT, "label": txt["contract_contract"]},
        {"id": CONTRACT_DPP_DPC, "label": txt["contract_dpp_dpc"]},
        {"id": CONTRACT_INTERNSHIP, "label": txt["contract_internship"]},
        {"id": CONTRACT_FREELANCE, "label": txt["contract_freelance"]},
    ]


# ---------------------------------------------------------------------------
# Step 9 - search modes (segmented buttons)
# ---------------------------------------------------------------------------


def search_modes(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"id": MODE_EXACT, "label": txt["mode_exact"], "desc": txt["mode_exact_desc"]},
        {"id": MODE_SMART, "label": txt["mode_smart"], "desc": txt["mode_smart_desc"]},
        {"id": MODE_BROAD, "label": txt["mode_broad"], "desc": txt["mode_broad_desc"]},
        {"id": MODE_DISCOVERY, "label": txt["mode_discovery"], "desc": txt["mode_discovery_desc"]},
    ]


# ---------------------------------------------------------------------------
# Step 10 - salary currency + output language
# ---------------------------------------------------------------------------


def salary_currencies(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"id": CURRENCY_ANY, "label": txt["currency_any"]},
        {"id": CURRENCY_CZK, "label": "CZK"},
        {"id": CURRENCY_EUR, "label": "EUR"},
        {"id": CURRENCY_USD, "label": "USD"},
        {"id": CURRENCY_GBP, "label": "GBP"},
        {"id": CURRENCY_PLN, "label": "PLN"},
    ]


def output_languages(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"id": OUTPUT_LANG_AUTO, "label": txt["output_lang_auto"]},
        {"id": OUTPUT_LANG_EN, "label": txt["output_lang_en"]},
        {"id": OUTPUT_LANG_CS, "label": txt["output_lang_cs"]},
    ]


def resolve_output_language(*, picker_value: str, global_lang: str) -> str:
    """Resolve the user's pick into a concrete language code.

    ``auto`` follows the global EN/CS toggle, anything else is used
    verbatim. We default to ``en`` if both are empty.
    """
    pick = (picker_value or OUTPUT_LANG_AUTO).strip().lower()
    if pick in {OUTPUT_LANG_EN, OUTPUT_LANG_CS}:
        return pick
    code = (global_lang or "en").strip().lower()
    return code if code in {"en", "cs"} else "en"
