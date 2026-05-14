"""Static data for the AI Jobs section.

* :data:`SECTION_ICON` - icon used by the sidebar / header bar.
* :data:`ACCENT` - accent colour the shared header treats as the
  section's primary tone.
* :func:`tabs` - localised labels for the centre tab bar.
* :func:`location_presets` - the fixed list of location options shown in
  the setup dropdown. The first column is the preset id (saved on
  STATE), the second column is the human label, the third column is
  the canonical region string we feed to the prompt (so AI knows to
  e.g. only return EU postings). The "any" entry leaves the location
  field unconstrained, "custom" hands control over to a free-text
  field rendered next to the dropdown.
* :func:`work_modes` - localised labels for the radio group.
* :data:`PREFERRED_BOARDS` - a hint table the prompt builder appends as
  "preferuj tyto job-boardy" suggestions per region. The AI provider's
  hosted web search picks them up so we don't have to maintain
  region-specific scrapers.
"""

from __future__ import annotations

from src.qt.icons import Icons
from src.sections.ai_jobs.state import (
    WORK_MODE_ANY,
    WORK_MODE_HYBRID,
    WORK_MODE_ONSITE,
    WORK_MODE_REMOTE,
)
from src.sections.ai_jobs.strings import s


SECTION_ICON = Icons.MANAGE_SEARCH

# Picks a calmer indigo so the section sits visually between AI Career
# (default blue) and AI Legal (purple) - matches the "search the web"
# vibe without clashing with adjacent accents.
ACCENT = "#6366F1"


def tabs(lang: str) -> list[str]:
    txt = s(lang)
    return [
        txt["tab_setup"],
        txt["tab_results"],
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
