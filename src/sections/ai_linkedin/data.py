"""Static metadata + demo seed for the AI LinkedIn section.

The "live" helpers (``brand_profile_fields``, ``recent_runs``,
``quick_actions``) read from :data:`STATE` at call time, with a
hand-curated fallback when the user has not run the pipeline yet.

The demo seed is what the section returns when the user toggles "Try
demo data" - hand-written profile / headlines / about / experience
JSONs so the entire flow (Setup -> Sections -> Output -> History) can
be explored without any AI call. Real runs replace these with
structured outputs from the pipeline.
"""

from __future__ import annotations

import flet as ft

from src.sections.ai_linkedin.state import (
    AUDIENCE_FOUNDER,
    AUDIENCE_HIRING,
    AUDIENCE_PEER,
    AUDIENCE_RECRUITER,
    POST_COMMENT,
    POST_JOB_SEARCH,
    POST_LEARNING_UPDATE,
    POST_NETWORKING,
    POST_PROJECT_LAUNCH,
    POST_RECRUITER_OUTREACH,
    SEC_ABOUT,
    SEC_CERTIFICATIONS,
    SEC_COURSES,
    SEC_EDUCATION,
    SEC_EXPERIENCE,
    SEC_FEATURED,
    SEC_HEADLINE,
    SEC_HONORS,
    SEC_LANGUAGES,
    SEC_POSTS,
    SEC_PROJECTS,
    SEC_PUBLICATIONS,
    SEC_RECOMMENDATIONS,
    SEC_SERVICES,
    SEC_SKILLS,
    SEC_VOLUNTEER,
    STATE,
    TONE_CONFIDENT_HONEST,
    TONE_JUNIOR_FRIENDLY,
    TONE_PROFESSIONAL,
    TONE_RECRUITER_FRIENDLY,
    TONE_SENIOR,
    TONE_SIMPLE,
    TONE_TECHNICAL,
)
from src.sections.ai_linkedin.strings import s


SECTION_ICON = ft.Icons.HUB_OUTLINED


# --- Tabs --------------------------------------------------------------


def mode_tabs(lang: str) -> list[str]:
    txt = s(lang)
    return [txt["mode_tab_chat"], txt["mode_tab_builder"]]


def builder_tabs(lang: str) -> list[str]:
    txt = s(lang)
    return [
        txt["builder_tab_setup"],
        txt["builder_tab_sections"],
        txt["builder_tab_output"],
        txt["builder_tab_history"],
    ]


# --- Audience / tone option lists -------------------------------------


def audience_options(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"key": AUDIENCE_RECRUITER, "label": txt["audience_recruiter"]},
        {"key": AUDIENCE_HIRING, "label": txt["audience_hiring"]},
        {"key": AUDIENCE_FOUNDER, "label": txt["audience_founder"]},
        {"key": AUDIENCE_PEER, "label": txt["audience_peer"]},
    ]


def tone_options(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"key": TONE_PROFESSIONAL, "label": txt["tone_professional"]},
        {"key": TONE_JUNIOR_FRIENDLY, "label": txt["tone_junior_friendly"]},
        {"key": TONE_SENIOR, "label": txt["tone_senior"]},
        {"key": TONE_CONFIDENT_HONEST, "label": txt["tone_confident_honest"]},
        {"key": TONE_TECHNICAL, "label": txt["tone_technical"]},
        {"key": TONE_SIMPLE, "label": txt["tone_simple"]},
        {"key": TONE_RECRUITER_FRIENDLY, "label": txt["tone_recruiter_friendly"]},
    ]


def section_picker_options(lang: str) -> list[dict]:
    """List of (id, label, hint, default-on) for the Sections checkbox grid."""
    txt = s(lang)
    return [
        {"key": SEC_HEADLINE, "label": txt["section_headline"], "hint": txt["section_headline_hint"], "default": True},
        {"key": SEC_ABOUT, "label": txt["section_about"], "hint": txt["section_about_hint"], "default": True},
        {"key": SEC_EXPERIENCE, "label": txt["section_experience"], "hint": txt["section_experience_hint"], "default": True},
        {"key": SEC_EDUCATION, "label": txt["section_education"], "hint": txt["section_education_hint"], "default": False},
        {"key": SEC_CERTIFICATIONS, "label": txt["section_certifications"], "hint": txt["section_certifications_hint"], "default": False},
        {"key": SEC_SKILLS, "label": txt["section_skills"], "hint": txt["section_skills_hint"], "default": True},
        {"key": SEC_FEATURED, "label": txt["section_featured"], "hint": txt["section_featured_hint"], "default": True},
        {"key": SEC_PROJECTS, "label": txt["section_projects"], "hint": txt["section_projects_hint"], "default": True},
        {"key": SEC_SERVICES, "label": txt["section_services"], "hint": txt["section_services_hint"], "default": False},
        {"key": SEC_COURSES, "label": txt["section_courses"], "hint": txt["section_courses_hint"], "default": False},
        {"key": SEC_RECOMMENDATIONS, "label": txt["section_recommendations"], "hint": txt["section_recommendations_hint"], "default": True},
        {"key": SEC_POSTS, "label": txt["section_posts"], "hint": txt["section_posts_hint"], "default": True},
    ]


def post_kind_options(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"key": POST_LEARNING_UPDATE, "label": txt["post_kind_learning_update"]},
        {"key": POST_PROJECT_LAUNCH, "label": txt["post_kind_project_launch"]},
        {"key": POST_JOB_SEARCH, "label": txt["post_kind_job_search"]},
        {"key": POST_RECRUITER_OUTREACH, "label": txt["post_kind_recruiter_outreach"]},
        {"key": POST_NETWORKING, "label": txt["post_kind_networking"]},
        {"key": POST_COMMENT, "label": txt["post_kind_comment"]},
    ]


# --- Quick actions / Brand profile / Recent runs ----------------------


def quick_actions(lang: str) -> list[dict]:
    """Five most-used actions surfaced in the right-hand panel."""
    txt = s(lang)
    return [
        {"key": "build_full", "icon": ft.Icons.AUTO_AWESOME, "label": txt["qa_build_full"]},
        {"key": "improve_headline", "icon": ft.Icons.TITLE, "label": txt["qa_improve_headline"]},
        {"key": "write_post", "icon": ft.Icons.EDIT_OUTLINED, "label": txt["qa_write_post"]},
        {"key": "show_history", "icon": ft.Icons.HISTORY, "label": txt["qa_show_history"]},
        {"key": "how_to", "icon": ft.Icons.HELP_OUTLINE, "label": txt["qa_how_to"]},
    ]


def brand_profile_fields(lang: str) -> list[dict]:
    """Live brand profile read from STATE; fallback to placeholder copy."""
    txt = s(lang)
    profile = STATE.extracted_profile or {}
    name = profile.get("full_name") or txt["brand_fallback_name"]
    role = profile.get("headline_current") or (
        STATE.target_roles[0] if STATE.target_roles else txt["brand_fallback_role"]
    )
    industry = profile.get("industry") or txt["brand_fallback_industry"]
    audience_label = _audience_label(STATE.audience, lang)
    tone_label = _tone_label(STATE.tone, lang)
    return [
        {"label": txt["brand_name_label"], "value": name},
        {"label": txt["brand_role_label"], "value": role},
        {"label": txt["brand_industry_label"], "value": industry},
        {"label": txt["brand_audience_label"], "value": audience_label},
        {"label": txt["brand_tone_label"], "value": tone_label, "chip": True},
    ]


def _audience_label(value: str, lang: str) -> str:
    for opt in audience_options(lang):
        if opt["key"] == value:
            return opt["label"]
    return value or "—"


def _tone_label(value: str, lang: str) -> str:
    for opt in tone_options(lang):
        if opt["key"] == value:
            return opt["label"]
    return value or "—"


def recent_runs(lang: str) -> list[dict]:
    """Recent saved profile builds rendered in the right panel."""
    txt = s(lang)
    out: list[dict] = []
    history = STATE.runs_history or []
    for entry in history[:5]:
        title = entry.get("role") or txt["recent_default_title"]
        when = entry.get("timestamp") or ""
        out.append({"title": title, "time": when})
    if not out:
        out.append({"title": txt["recent_empty_title"], "time": ""})
    return out


# ============================================================
# Demo dataset - hand-curated so the UI looks alive offline.
# ============================================================


DEMO_RESUME_TEXT = """\
Marek Bartoš
marek.bartos@email.cz | +420 777 555 333 | Praha
github.com/marekbartos

Profile
Senior Software QA Engineer with 6+ years of experience in manual and
automated testing, bug reporting, SQL, Git, and QA processes across
companies like Gen and Avast.

Experience
Senior Software QA Engineer - Gen (10/2022 - present)
- Designed and executed manual + automated test scenarios across
  desktop and web products.
- Reported and tracked defects via JIRA, partnered with developers
  during weekly bug-triage.
- Owned test plans for two product releases per quarter.

QA Engineer - Gen (01/2021 - 09/2022)
- Wrote regression tests in Python + pytest; helped move 40+ flaky
  tests under 1% flakiness.
- Co-built the team's automation onboarding doc.

Junior Software QA Engineer - Avast (04/2018 - 12/2020)
- Manual exploratory testing of consumer security apps; filed 200+
  high-quality bug reports.
- Set up Git workflow for the QA team's regression scripts.

Vývojář Python - CreatiWeb (06/2016 - 03/2018)
- Drobné Django CMS úpravy a údržba klientských projektů.

Education
Provozně ekonomická fakulta ČZU v Praze (2014 - 2017)
SPŠE Ječná, Praha (2010 - 2014)

Languages
Czech (native), English (advanced - C1), German (basic - A2)

Skills
Manual Testing, Test Cases, Bug Reporting, Regression Testing,
Exploratory Testing, JIRA, Git, SQL, Python, Playwright, Flutter,
Generative AI

Certifications
Artificial Intelligence with Machine Learning - Oracle (2024)
Java Programming - Oracle (2022)
"""


# --- Demo helpers ------------------------------------------------------


def demo_evidence_index() -> dict[str, list[str]]:
    return {
        "resume": [
            "Manual Testing", "Bug Reporting", "JIRA", "SQL", "Git",
            "Python", "Playwright", "Regression Testing",
        ],
        "linkedin_export": [],
        "github": ["Flutter"],
        "user_confirmed": ["Generative AI"],
        "missing_evidence": ["AI Tools"],
    }


def demo_profile(lang: str) -> dict:
    is_cs = lang == "cs"
    return {
        "full_name": "Marek Bartoš",
        "headline_current": (
            "Senior Software QA Engineer | Python · Playwright · Flutter |"
            " Building Practical QA Tools"
        ),
        "industry": _h("Software / QA Automation", "Software / QA automatizace", is_cs),
        "location": _h("Prague, Czech Republic", "Praha, Česko", is_cs),
        "contact": {
            "email": "marek.bartos@email.cz",
            "phone": "+420 777 555 333",
        },
        "summary": _h(
            "Senior Software QA Engineer with 6+ years of experience in"
            " manual and automated testing across consumer security and"
            " developer-tooling products.",
            "Senior Software QA Engineer s 6+ lety praxe v manuálním i"
            " automatizovaném testování napříč produkty pro spotřebitelskou"
            " bezpečnost a vývojářské nástroje.",
            is_cs,
        ),
        "experiences": [
            {
                "role": "Senior Software QA Engineer",
                "company": "Gen",
                "period": "10/2022 - present" if not is_cs else "10/2022 - dosud",
                "employment_type": "",
                "location": _h("Prague", "Praha", is_cs),
                "bullets": [
                    _h(
                        "Designed and executed manual + automated test scenarios across desktop and web products.",
                        "Navrhoval a spouštěl manuální i automatizované testy napříč desktop a web produkty.",
                        is_cs,
                    ),
                    _h(
                        "Reported and tracked defects via JIRA, partnered with developers during weekly bug-triage.",
                        "Reportoval a sledoval defekty v JIRA, spolupracoval s vývojáři na týdenním bug-triage.",
                        is_cs,
                    ),
                    _h(
                        "Owned test plans for two product releases per quarter.",
                        "Vlastnil test-plány pro dvě releasy produktu za kvartál.",
                        is_cs,
                    ),
                ],
                "evidence_anchor": "resume",
            },
            {
                "role": "QA Engineer",
                "company": "Gen",
                "period": "01/2021 - 09/2022",
                "employment_type": "",
                "location": _h("Prague", "Praha", is_cs),
                "bullets": [
                    _h(
                        "Wrote regression tests in Python + pytest; cut flakiness on 40+ tests below 1%.",
                        "Psal regresní testy v Pythonu + pytestu; snížil flakiness u 40+ testů pod 1 %.",
                        is_cs,
                    ),
                    _h(
                        "Co-built the automation onboarding doc for new QA hires.",
                        "Spoluvytvořil onboarding dokument k automatizaci pro nové QA.",
                        is_cs,
                    ),
                ],
                "evidence_anchor": "resume",
            },
            {
                "role": "Junior Software QA Engineer",
                "company": "Avast",
                "period": "04/2018 - 12/2020",
                "employment_type": "",
                "location": _h("Prague", "Praha", is_cs),
                "bullets": [
                    _h(
                        "Manual exploratory testing of consumer security apps; filed 200+ high-quality bug reports.",
                        "Manuální exploratorní testování spotřebitelských security aplikací; přes 200 kvalitních bug reportů.",
                        is_cs,
                    ),
                    _h(
                        "Set up the Git workflow for the QA team's regression scripts.",
                        "Nastavil Git workflow pro regresní skripty QA týmu.",
                        is_cs,
                    ),
                ],
                "evidence_anchor": "resume",
            },
            {
                "role": _h("Python Developer", "Vývojář Python", is_cs),
                "company": "CreatiWeb",
                "period": "06/2016 - 03/2018",
                "employment_type": "",
                "location": _h("Prague", "Praha", is_cs),
                "bullets": [
                    _h(
                        "Maintained small Django CMS sites for end clients.",
                        "Udržoval malé Django CMS weby pro koncové klienty.",
                        is_cs,
                    ),
                ],
                "evidence_anchor": "resume",
            },
        ],
        "education": [
            {
                "institution": "Provozně ekonomická fakulta ČZU v Praze",
                "degree": _h("Bachelor, Informatics", "Bakalář, Informatika", is_cs),
                "period": "2014 - 2017",
                "details": "",
                "evidence_anchor": "resume",
            },
            {
                "institution": "SPŠE Ječná, Praha",
                "degree": _h("Secondary tech school", "Střední průmyslová škola elektrotechnická", is_cs),
                "period": "2010 - 2014",
                "details": "",
                "evidence_anchor": "resume",
            },
        ],
        "certifications": [
            {
                "name": "Artificial Intelligence with Machine Learning",
                "issuer": "Oracle",
                "year": "2024",
                "evidence_anchor": "resume",
            },
            {
                "name": "Java Programming",
                "issuer": "Oracle",
                "year": "2022",
                "evidence_anchor": "resume",
            },
        ],
        "languages": [
            {"name": _h("Czech", "Čeština", is_cs), "cefr": "C2"},
            {"name": _h("English", "Angličtina", is_cs), "cefr": "C1"},
            {"name": _h("German", "Němčina", is_cs), "cefr": "A2"},
        ],
        "skills": [
            {"name": "Manual Testing", "category": "core", "evidence_anchor": "resume"},
            {"name": "Bug Reporting", "category": "core", "evidence_anchor": "resume"},
            {"name": "Regression Testing", "category": "core", "evidence_anchor": "resume"},
            {"name": "JIRA", "category": "tooling", "evidence_anchor": "resume"},
            {"name": "Git", "category": "tooling", "evidence_anchor": "resume"},
            {"name": "SQL", "category": "tooling", "evidence_anchor": "resume"},
            {"name": "Python", "category": "tooling", "evidence_anchor": "resume"},
            {"name": "Playwright", "category": "tooling", "evidence_anchor": "github"},
            {"name": "Flutter", "category": "tooling", "evidence_anchor": "github"},
            {"name": "Generative AI", "category": "domain", "evidence_anchor": "user_confirmed"},
            {"name": "AI Tools", "category": "domain", "evidence_anchor": "missing_evidence"},
        ],
        "projects": [
            {
                "name": "ApplyPilot AI",
                "period": "2024 - present" if not is_cs else "2024 - dosud",
                "description": _h(
                    "Python desktop app that turns job posts, resumes, LinkedIn exports and GitHub projects into tailored applications.",
                    "Python desktop aplikace, která mění inzeráty, životopisy, LinkedIn exporty a GitHub projekty na cílené aplikační materiály.",
                    is_cs,
                ),
                "url": "https://github.com/marekbartos/applypilot-ai",
                "evidence_anchor": "github",
            },
        ],
        "online_links": [
            {"label": "github.com/marekbartos", "url": "https://github.com/marekbartos", "evidence_anchor": "resume"},
        ],
        "linkedin_present": False,
        "github_present": True,
    }


def demo_headlines(lang: str) -> dict:
    is_cs = lang == "cs"
    variants = [
        {
            "text": "Senior Software QA Engineer | Python · Playwright · Flutter | Building Practical QA Tools",
            "audience": "recruiter",
            "char_count": 95,
            "evidence_anchors": ["resume", "github"],
            "focus": _h("recruiter-friendly", "recruiter-friendly", is_cs),
        },
        {
            "text": "Senior Software QA Engineer | QA Automation | Python · Playwright · GenAI Tools | Building practical software-quality tools",
            "audience": "recruiter",
            "char_count": 124,
            "evidence_anchors": ["resume", "github", "user_confirmed"],
            "focus": _h("keyword-rich", "keyword-rich", is_cs),
        },
        {
            "text": "Senior Software QA Engineer · 6+ years across Gen and Avast · Python + Playwright automation · Side projects in Flutter and GenAI tooling",
            "audience": "hiring_manager",
            "char_count": 145,
            "evidence_anchors": ["resume", "github"],
            "focus": _h("hiring-manager scope", "scope pro hiring managera", is_cs),
        },
        {
            "text": "QA engineer who likes shipping the test stack himself - Python automation, Playwright, plus side-project tooling for QA workflows",
            "audience": "peer",
            "char_count": 132,
            "evidence_anchors": ["resume", "github"],
            "focus": _h("peer-craft voice", "peer voice", is_cs),
        },
    ]
    return {"variants": variants}


def demo_about(lang: str) -> dict:
    is_cs = lang == "cs"
    short = _h(
        "Senior Software QA Engineer (6+ yrs across Gen and Avast). Python +"
        " Playwright automation, side projects in Flutter and GenAI tooling.",
        "Senior Software QA Engineer (6+ let v Gen a Avastu). Python +"
        " Playwright automatizace, side-projekty ve Flutteru a GenAI nástrojích.",
        is_cs,
    )
    medium = _h(
        "Senior Software QA Engineer with 6+ years across Gen (current) and"
        " Avast. I focus on practical QA - reliable regression suites, lean"
        " bug reporting, and tooling that the rest of the team actually uses."
        "\n\nOn the side I build small Python desktop tools (latest:"
        " ApplyPilot AI, GenAI app for job applications) and explore Flutter"
        " for cross-platform QA-friendly utilities.",
        "Senior Software QA Engineer s 6+ lety praxe v Gen (aktuálně) a"
        " Avastu. Soustředím se na praktické QA - spolehlivé regresní"
        " sady, sevřený bug reporting a nástroje, které zbytek týmu"
        " opravdu používá.\n\nVe volném čase stavím malé Python desktop"
        " nástroje (poslední: ApplyPilot AI, GenAI aplikace pro pracovní"
        " inzeráty) a zkouším Flutter pro multiplatformní QA pomocníky.",
        is_cs,
    )
    long_ = _h(
        "Senior Software QA Engineer with 6+ years of experience across"
        " consumer security (Avast) and developer-tooling products (Gen)."
        " My day is split between manual exploratory testing of new"
        " features, owning the regression suite (Python + Playwright), and"
        " bug-triage with the dev squads.\n\nI lead the test plan for two"
        " product releases per quarter and helped move 40+ flaky tests"
        " under 1% flakiness in our pytest suite. Side projects: ApplyPilot"
        " AI (Python + Pydantic), small Flutter utilities, and a couple of"
        " GenAI prototypes.\n\nOpen to: senior QA, QA automation lead,"
        " hybrid roles where I can write code and improve QA workflow.",
        "Senior Software QA Engineer s 6+ lety praxe ve spotřebitelské"
        " bezpečnosti (Avast) a vývojářských nástrojích (Gen). Den dělím"
        " mezi manuální exploratorní testování nových featur, vlastnictví"
        " regresní sady (Python + Playwright) a bug-triage se dev týmy."
        "\n\nVedu test-plány pro dvě releasy produktu za kvartál a pomohl"
        " jsem dostat 40+ flaky testů pod 1 % v pytest sadě. Side-projekty:"
        " ApplyPilot AI (Python + Pydantic), malé Flutter utility a pár"
        " GenAI prototypů.\n\nOpen to: senior QA, lead QA automatizace,"
        " hybridní role, kde můžu psát kód a zlepšovat QA workflow.",
        is_cs,
    )
    technical = _h(
        "Manual + automated QA across desktop and web. Python + pytest +"
        " Playwright; comfortable with Git workflows for QA scripts and SQL"
        " for data setup. Familiar with bug-triage in JIRA. Currently"
        " exploring Flutter and GenAI tooling for QA workflow.",
        "Manuální i automatické QA napříč desktop + web. Python + pytest"
        " + Playwright; pohodlně se cítím v Git workflow pro QA skripty a"
        " SQL pro data-setup. Bug-triage v JIRA. Aktuálně zkoumám Flutter"
        " a GenAI nástroje pro QA workflow.",
        is_cs,
    )
    recruiter_v = _h(
        "Senior Software QA Engineer | 6+ years | Python · Playwright ·"
        " pytest · JIRA · SQL · Git | side projects in Flutter and GenAI"
        " tooling | open to senior QA / QA automation lead roles in Prague"
        " or remote-friendly EU.",
        "Senior Software QA Engineer | 6+ let | Python · Playwright ·"
        " pytest · JIRA · SQL · Git | side-projekty ve Flutteru a GenAI"
        " nástrojích | open to senior QA / lead QA automatizace v Praze"
        " nebo remote-friendly EU.",
        is_cs,
    )
    return {
        "short_version": short,
        "medium_version": medium,
        "long_version": long_,
        "technical_version": technical,
        "recruiter_version": recruiter_v,
        "char_counts": {
            "short_version": len(short),
            "medium_version": len(medium),
            "long_version": len(long_),
            "technical_version": len(technical),
            "recruiter_version": len(recruiter_v),
        },
    }


def demo_experience_rewrites(lang: str) -> dict:
    is_cs = lang == "cs"
    return {
        "roles": [
            {
                "role": "Senior Software QA Engineer",
                "company": "Gen",
                "period": "10/2022 - present" if not is_cs else "10/2022 - dosud",
                "linkedin_description": _h(
                    "Senior QA on a multi-product squad covering desktop and web releases.",
                    "Senior QA v multi-produktovém týmu pokrývajícím desktop a web release.",
                    is_cs,
                ),
                "bullets": [
                    _h(
                        "Designed and executed manual + automated tests across desktop and web products.",
                        "Navrhoval a spouštěl manuální i automatizované testy napříč desktop a web produkty.",
                        is_cs,
                    ),
                    _h(
                        "Owned the regression suite in Python + pytest; cut flakiness on 40+ tests below 1%.",
                        "Vlastnil regresní sadu v Pythonu + pytestu; snížil flakiness u 40+ testů pod 1 %.",
                        is_cs,
                    ),
                    _h(
                        "Partnered with developers during weekly bug-triage in JIRA.",
                        "Spolupracoval s vývojáři na týdenním bug-triage v JIRA.",
                        is_cs,
                    ),
                    _h(
                        "Led test plans for two product releases per quarter.",
                        "Vedl test-plány pro dvě releasy produktu za kvartál.",
                        is_cs,
                    ),
                ],
                "suggested_skills": [
                    {"name": "Manual Testing", "evidence_anchor": "resume"},
                    {"name": "Test Plans", "evidence_anchor": "resume"},
                    {"name": "Python", "evidence_anchor": "resume"},
                    {"name": "pytest", "evidence_anchor": "resume"},
                    {"name": "JIRA", "evidence_anchor": "resume"},
                    {"name": "Bug Triage", "evidence_anchor": "resume"},
                ],
                "highlight": [_h("QA ownership", "QA ownership", is_cs), _h("Flakiness fix", "Fix flakiness", is_cs)],
                "do_not_claim": [
                    _h(
                        "No evidence for 'led a team of N' - source mentions only co-ownership.",
                        "Žádný důkaz pro 'vedl tým N lidí' - zdroj zmiňuje jen spoluvlastnictví.",
                        is_cs,
                    ),
                ],
                "evidence_anchors": ["resume"],
            },
            {
                "role": "QA Engineer",
                "company": "Gen",
                "period": "01/2021 - 09/2022",
                "linkedin_description": _h(
                    "QA contributor focused on regression coverage and onboarding tooling.",
                    "QA přispěvatel se zaměřením na regresní pokrytí a onboarding nástroje.",
                    is_cs,
                ),
                "bullets": [
                    _h(
                        "Wrote regression tests in Python + pytest; helped reduce flakiness on 40+ tests below 1%.",
                        "Psal regresní testy v Pythonu + pytestu; pomohl snížit flakiness u 40+ testů pod 1 %.",
                        is_cs,
                    ),
                    _h(
                        "Co-built the automation onboarding doc that cut new-hire ramp-up time by ~30%.",
                        "Spoluvytvořil onboarding dokument k automatizaci, který zkrátil ramp-up nových QA o ~30 %.",
                        is_cs,
                    ),
                ],
                "suggested_skills": [
                    {"name": "Python", "evidence_anchor": "resume"},
                    {"name": "pytest", "evidence_anchor": "resume"},
                    {"name": "Regression Testing", "evidence_anchor": "resume"},
                    {"name": "Documentation", "evidence_anchor": "resume"},
                ],
                "highlight": [_h("Onboarding", "Onboarding", is_cs)],
                "do_not_claim": [],
                "evidence_anchors": ["resume"],
            },
            {
                "role": "Junior Software QA Engineer",
                "company": "Avast",
                "period": "04/2018 - 12/2020",
                "linkedin_description": _h(
                    "First QA role on a consumer security app team.",
                    "První QA role v týmu spotřebitelské security aplikace.",
                    is_cs,
                ),
                "bullets": [
                    _h(
                        "Manual exploratory testing of consumer security apps; filed 200+ high-quality bug reports.",
                        "Manuální exploratorní testování spotřebitelských security aplikací; přes 200 kvalitních bug reportů.",
                        is_cs,
                    ),
                    _h(
                        "Set up the Git workflow for the QA team's regression scripts.",
                        "Nastavil Git workflow pro regresní skripty QA týmu.",
                        is_cs,
                    ),
                ],
                "suggested_skills": [
                    {"name": "Manual Testing", "evidence_anchor": "resume"},
                    {"name": "Exploratory Testing", "evidence_anchor": "resume"},
                    {"name": "Git", "evidence_anchor": "resume"},
                ],
                "highlight": [_h("Bug volume", "Objem bugů", is_cs)],
                "do_not_claim": [],
                "evidence_anchors": ["resume"],
            },
        ],
    }


def demo_education_rewrites(lang: str) -> dict:
    is_cs = lang == "cs"
    return {
        "entries": [
            {
                "institution": "Provozně ekonomická fakulta ČZU v Praze",
                "degree": _h("Bachelor, Informatics", "Bakalář, Informatika", is_cs),
                "period": "2014 - 2017",
                "linkedin_description": _h(
                    "Studied Informatics with a focus on technical and analytical foundations relevant to software testing, programming, databases and IT systems.",
                    "Studoval Informatiku se zaměřením na technické a analytické základy relevantní pro testování software, programování, databáze a IT systémy.",
                    is_cs,
                ),
                "relevant_coursework": ["Databáze", "Algoritmy", "OOP"],
                "connection_to_target": _h(
                    "Foundations for QA automation - SQL, OOP and analytical reasoning.",
                    "Základ pro QA automatizaci - SQL, OOP a analytické myšlení.",
                    is_cs,
                ),
                "evidence_anchors": ["resume"],
            },
            {
                "institution": "SPŠE Ječná, Praha",
                "degree": _h("Secondary tech school", "SPŠE", is_cs),
                "period": "2010 - 2014",
                "linkedin_description": _h(
                    "Tech-school education with a programming focus.",
                    "Středoškolské vzdělání s programátorským zaměřením.",
                    is_cs,
                ),
                "relevant_coursework": [],
                "connection_to_target": "",
                "evidence_anchors": ["resume"],
            },
        ],
    }


def demo_certifications(lang: str) -> dict:
    is_cs = lang == "cs"
    return {
        "existing": [
            {
                "name": "Artificial Intelligence with Machine Learning",
                "issuer": "Oracle",
                "year": "2024",
                "linkedin_description": _h(
                    "AI / ML foundations course - useful framing for the GenAI tooling I build on the side.",
                    "Základy AI / ML - užitečný rámec pro GenAI nástroje, které stavím vedle.",
                    is_cs,
                ),
                "priority": "high",
                "target_role_links": ["QA Automation Lead"],
                "evidence_anchor": "resume",
            },
            {
                "name": "Java Programming",
                "issuer": "Oracle",
                "year": "2022",
                "linkedin_description": _h(
                    "Java basics - relevant when working with JVM-based test stacks.",
                    "Základy Javy - užitečné, kdykoliv pracuju s JVM-based test stackem.",
                    is_cs,
                ),
                "priority": "medium",
                "target_role_links": ["Senior Software QA Engineer"],
                "evidence_anchor": "resume",
            },
        ],
        "recommended": [
            {
                "name": "ISTQB Foundation Level",
                "issuer": "ISTQB",
                "why_it_matters": _h(
                    "Recruiter-friendly QA baseline; widely recognised at the senior level.",
                    "Recruiter-friendly základ QA; široce uznávaný na senior úrovni.",
                    is_cs,
                ),
            },
            {
                "name": "Playwright Certification",
                "issuer": "Microsoft Learn",
                "why_it_matters": _h(
                    "Validates the Playwright work the candidate already does.",
                    "Validuje Playwright práci, kterou kandidát už dělá.",
                    is_cs,
                ),
            },
        ],
    }


def demo_skills_buckets(lang: str) -> dict:
    is_cs = lang == "cs"
    core = [
        {"name": "Manual Testing", "category": "core", "evidence_anchor": "resume", "evidence_quote": _h("6+ years across Gen and Avast", "6+ let v Gen a Avastu", is_cs), "reason": ""},
        {"name": "Bug Reporting", "category": "core", "evidence_anchor": "resume", "evidence_quote": _h("200+ filed reports at Avast", "200+ reportů v Avastu", is_cs), "reason": ""},
        {"name": "Regression Testing", "category": "core", "evidence_anchor": "resume", "evidence_quote": _h("40+ tests below 1% flakiness", "40+ testů pod 1 % flakiness", is_cs), "reason": ""},
        {"name": "Python", "category": "tooling", "evidence_anchor": "resume", "evidence_quote": _h("pytest regression suite", "regresní pytest sada", is_cs), "reason": ""},
        {"name": "Playwright", "category": "tooling", "evidence_anchor": "github", "evidence_quote": _h("automation in side project repo", "automatizace v side-projekt repu", is_cs), "reason": ""},
        {"name": "JIRA", "category": "tooling", "evidence_anchor": "resume", "evidence_quote": _h("weekly bug-triage", "týdenní bug-triage", is_cs), "reason": ""},
        {"name": "SQL", "category": "tooling", "evidence_anchor": "resume", "evidence_quote": _h("data setup for tests", "data-setup pro testy", is_cs), "reason": ""},
        {"name": "Git", "category": "tooling", "evidence_anchor": "resume", "evidence_quote": _h("QA workflow at Avast", "QA workflow v Avastu", is_cs), "reason": ""},
    ]
    to_verify = [
        {"name": "Flutter", "category": "tooling", "evidence_anchor": "github", "evidence_quote": _h("side project repo", "side-projekt repo", is_cs), "reason": _h("Confirm production usage before listing.", "Před uvedením potvrď produkční nasazení.", is_cs)},
        {"name": "Generative AI", "category": "domain", "evidence_anchor": "user_confirmed", "evidence_quote": "", "reason": _h("Add 1-2 short bullets to a featured project to back this.", "Přidej 1-2 krátké body k featured projektu, ať to máš podložené.", is_cs)},
    ]
    to_learn = [
        {"name": "TestRail", "category": "tooling", "evidence_anchor": "missing_evidence", "evidence_quote": "", "reason": _h("Common request in QA automation lead roles - take a 4-hour intro course.", "Často žádané u QA automation lead pozic - projeď 4hod intro kurz.", is_cs)},
        {"name": "GitHub Actions", "category": "tooling", "evidence_anchor": "missing_evidence", "evidence_quote": "", "reason": _h("Wire your Playwright suite into GitHub Actions to demonstrate CI literacy.", "Napoj Playwright sadu na GitHub Actions, aby bylo vidět CI literacy.", is_cs)},
    ]
    do_not_claim = [
        {"name": "AI Tools", "category": "domain", "evidence_anchor": "missing_evidence", "evidence_quote": "", "reason": _h("Vague keyword - replace with the specific tools you've shipped (e.g. 'GitHub Copilot', 'OpenAI API').", "Příliš vágní - nahraď konkrétními nástroji, které jsi nasadil ('GitHub Copilot', 'OpenAI API').", is_cs)},
    ]
    return {"core": core, "to_verify": to_verify, "to_learn": to_learn, "do_not_claim": do_not_claim}


def demo_featured(lang: str) -> dict:
    is_cs = lang == "cs"
    return {
        "items": [
            {
                "kind": "github_project",
                "title": "ApplyPilot AI",
                "description": _h(
                    "Python desktop GenAI app for tailoring resumes / cover letters / match reports / interview prep.",
                    "Python desktop GenAI aplikace na cílení životopisů, motivačních dopisů, match reportů a přípravy na pohovor.",
                    is_cs,
                ),
                "link": "https://github.com/marekbartos/applypilot-ai",
                "todo": "",
                "evidence_anchor": "github",
            },
            {
                "kind": "article",
                "title": _h("Playwright onboarding doc - lessons learned", "Playwright onboarding doc - lessons learned", is_cs),
                "description": _h(
                    "Short LinkedIn article from the QA automation onboarding doc you co-built at Gen.",
                    "Krátký LinkedIn článek z onboardingu k QA automatizaci, který jsi spoluvytvořil v Gen.",
                    is_cs,
                ),
                "link": "",
                "todo": _h(
                    "Paste the article URL once you publish it.",
                    "Po publikaci doplň URL článku.",
                    is_cs,
                ),
                "evidence_anchor": "resume",
            },
            {
                "kind": "certificate",
                "title": "Artificial Intelligence with Machine Learning - Oracle",
                "description": _h(
                    "Oracle AI/ML cert (2024) - relevant for the GenAI tooling positioning.",
                    "Oracle AI/ML cert (2024) - relevant pro GenAI nástroje.",
                    is_cs,
                ),
                "link": "",
                "todo": _h(
                    "Upload the certificate PDF to LinkedIn.",
                    "Nahraj PDF certifikátu na LinkedIn.",
                    is_cs,
                ),
                "evidence_anchor": "resume",
            },
        ],
    }


def demo_projects(lang: str) -> dict:
    is_cs = lang == "cs"
    return {
        "projects": [
            {
                "title": "ApplyPilot AI",
                "description": _h(
                    "Python desktop GenAI application that turns job postings, resumes, LinkedIn exports and GitHub projects into tailored application materials. Provider-agnostic, structured outputs, evidence-first generation.",
                    "Python desktop GenAI aplikace, která mění inzeráty, životopisy, LinkedIn exporty a GitHub projekty na cílené aplikační materiály. Provider-agnostic, strukturované výstupy, evidence-first generování.",
                    is_cs,
                ),
                "technologies": ["Python", "Pydantic", "OpenAI API", "Anthropic API", "DOCX export"],
                "candidate_role": _h("Solo developer + designer", "Sólo vývojář + designér", is_cs),
                "period": "2024 - present" if not is_cs else "2024 - dosud",
                "link": "https://github.com/marekbartos/applypilot-ai",
                "suggested_skills": ["Python", "GenAI", "Software Architecture", "JSON Schema"],
                "evidence_anchors": ["github"],
            },
            {
                "title": "Flutter QA Toolkit",
                "description": _h(
                    "Side project: small Flutter app collecting QA-related utilities (test-data generators, JIRA shortcut links).",
                    "Side projekt: malá Flutter aplikace s QA pomůckami (generátory testovacích dat, JIRA shortcut linky).",
                    is_cs,
                ),
                "technologies": ["Flutter", "Dart"],
                "candidate_role": _h("Solo developer", "Sólo vývojář", is_cs),
                "period": "2023",
                "link": "",
                "suggested_skills": ["Flutter", "Dart", "Mobile Tooling"],
                "evidence_anchors": ["github"],
            },
        ],
    }


def demo_services(lang: str, *, opt_in: bool) -> dict:
    is_cs = lang == "cs"
    if not opt_in:
        return {
            "services": [],
            "skip_reason": _h(
                "Candidate did not opt into LinkedIn Services. Toggle 'Offer services' in Setup if you want freelance suggestions.",
                "Kandidát neopt-inoval na LinkedIn služby. Zapni 'Nabízet služby' v Setup, pokud chceš návrhy pro freelance.",
                is_cs,
            ),
        }
    return {
        "services": [
            {
                "name": _h("QA Consulting", "QA konzultace", is_cs),
                "short_description": _h(
                    "Hands-on QA strategy + Python/Playwright automation for small product teams.",
                    "Hands-on QA strategie + Python/Playwright automatizace pro menší produktové týmy.",
                    is_cs,
                ),
                "why_credible": _h(
                    "6+ years of QA across Gen and Avast.",
                    "6+ let QA praxe v Gen a Avastu.",
                    is_cs,
                ),
                "evidence_anchor": "resume",
            },
        ],
        "skip_reason": "",
    }


def demo_courses(lang: str) -> dict:
    is_cs = lang == "cs"
    return {
        "existing": [],
        "recommended": [
            {
                "title": "Playwright for Python",
                "provider": "Microsoft Learn",
                "why_it_matters": _h(
                    "Validates Playwright knowledge with a name recruiters recognise.",
                    "Validuje Playwright znalost značkou, kterou recruiteři znají.",
                    is_cs,
                ),
                "estimated_hours": 8,
            },
            {
                "title": "API Testing with Postman",
                "provider": "Postman Academy",
                "why_it_matters": _h(
                    "Most QA-automation roles ask for API testing literacy.",
                    "Většina QA-automation rolí žádá API-testing literacy.",
                    is_cs,
                ),
                "estimated_hours": 6,
            },
        ],
    }


def demo_recommendations(lang: str) -> dict:
    is_cs = lang == "cs"
    return {
        "templates": [
            {
                "recipient_type": "manager",
                "suggested_recipient_label": _h("Manager from Gen", "Manažer z Gen", is_cs),
                "message": _h(
                    "Hi [Name], hope you're doing well. I'm refreshing my LinkedIn profile and would really appreciate a short recommendation that focuses on the regression-suite ownership and bug-triage rhythm we built together. Three-four sentences would be perfect; I can share a quick draft if it helps.",
                    "Ahoj [Jméno], doufám, že se ti daří. Aktualizuju LinkedIn profil a uvítal bych krátké doporučení zaměřené na vlastnictví regresní sady a bug-triage rytmus, který jsme spolu nastavili. Tři až čtyři věty stačí; klidně ti pošlu kostru.",
                    is_cs,
                ),
                "follow_up": _h(
                    "Hi [Name], gentle nudge - any chance you can drop a couple of lines this week?",
                    "Ahoj [Jméno], jen jemná připomínka - stihl bys pár vět během tohoto týdne?",
                    is_cs,
                ),
            },
            {
                "recipient_type": "peer",
                "suggested_recipient_label": _h("Peer engineer at Gen", "Kolega vývojář v Gen", is_cs),
                "message": _h(
                    "Hi [Name], could I ask for a short LinkedIn recommendation? Especially around how we collaborated on bug-triage and the Playwright migration - your perspective from the dev side would mean a lot.",
                    "Ahoj [Jméno], mohl bych tě poprosit o krátké LinkedIn doporučení? Zejména o tom, jak jsme spolupracovali na bug-triage a Playwright migraci - tvůj pohled z dev strany by hodně pomohl.",
                    is_cs,
                ),
                "follow_up": _h(
                    "Hi [Name], no rush - just confirming you saw the message.",
                    "Ahoj [Jméno], žádný spěch - jen kontroluju, jestli ti zpráva dorazila.",
                    is_cs,
                ),
            },
        ],
    }


def demo_posts(lang: str, kinds: list[str]) -> dict:
    is_cs = lang == "cs"
    pool = {
        POST_LEARNING_UPDATE: {
            "kind": POST_LEARNING_UPDATE,
            "title": _h("Playwright onboarding doc", "Playwright onboarding doc", is_cs),
            "body": _h(
                "Spent the last sprint co-writing the Playwright onboarding doc for new QA hires at Gen. The bit that surprised me: the friction was never 'how to write a selector' - it was figuring out how the team's CI runs your test, what the data-setup factories look like, and which assertions are blessed.\n\nWe restructured the doc as a 90-minute path: 1) clone, run, watch a single test pass, 2) write a tiny new test against a fixture, 3) wire it into the regression suite. New folks now pair-write their first PR on day three instead of week two.\n\nQuestion for fellow QA engineers: how do you measure 'good' onboarding for an automation suite?",
                "Poslední sprint jsme spolu psali Playwright onboarding pro nové QA v Genu. Co mě překvapilo: tření nikdy nebylo 'jak napsat selector' - bylo to o tom pochopit, jak tým spouští testy v CI, jak vypadají data-setup factories a které asserty jsou schválené.\n\nDokument jsme přepsali jako 90 min cestu: 1) clone, spustit, vidět jeden test projít, 2) napsat malý test proti fixture, 3) napojit ho na regresní sadu. Noví lidé teď párují svůj první PR třetí den místo druhého týdne.\n\nOtázka pro QA inženýry: jak měříte 'dobrý' onboarding na automatizační sadu?",
                is_cs,
            ),
            "char_count": 0,
            "hashtags": ["#qa", "#testautomation", "#playwright", "#onboarding"],
            "evidence_anchors": ["resume"],
            "audience": "peer",
            "parent_post_topic": "",
        },
        POST_PROJECT_LAUNCH: {
            "kind": POST_PROJECT_LAUNCH,
            "title": _h("ApplyPilot AI launch", "ApplyPilot AI launch", is_cs),
            "body": _h(
                "Shipped a v0 of ApplyPilot AI this weekend - a Python desktop GenAI app that turns a job posting, your CV, your LinkedIn export and your GitHub repos into a tailored application: structured CV, cover letter, match report, interview prep and a skill-gap plan.\n\nThree decisions I'm proud of:\n• Provider-agnostic core (OpenAI + Anthropic) so the user picks who they trust.\n• Strict JSON Schemas for every step - the LLM has to fit the contract or we reject the run.\n• Evidence-first prompts: if the source has no signal, we leave the field empty instead of inventing one.\n\nNext up: a LinkedIn profile builder mode (because I needed it myself). What features would you want from a tool like this?",
                "O víkendu jsem nasadil v0 ApplyPilot AI - Python desktop GenAI aplikaci, která z inzerátu, CV, LinkedIn exportu a GitHub repozitářů vyrobí cílenou aplikaci: strukturované CV, motivační dopis, match report, prep na pohovor a plán uzavření mezer.\n\nTři rozhodnutí, na která jsem hrdý:\n• Provider-agnostic core (OpenAI + Anthropic) - uživatel si vybere komu věří.\n• Striktní JSON schémata na každém kroku - LLM musí trefit kontrakt, jinak run odmítneme.\n• Evidence-first prompty: když zdroj nedává signál, pole necháme prázdné místo aby si LLM vymýšlel.\n\nPříště: režim pro LinkedIn profil (protože jsem to sám potřeboval). Jaké features byste od takového nástroje chtěli?",
                is_cs,
            ),
            "char_count": 0,
            "hashtags": ["#genai", "#python", "#sideproject", "#qa"],
            "evidence_anchors": ["github"],
            "audience": "peer",
            "parent_post_topic": "",
        },
        POST_JOB_SEARCH: {
            "kind": POST_JOB_SEARCH,
            "title": _h("Open to QA Automation Lead", "Open to QA Automation Lead", is_cs),
            "body": _h(
                "Quietly opening up: I'm exploring senior / lead QA Automation roles in Prague (or remote-friendly EU). 6+ years across Gen and Avast, Python + Playwright + pytest, hands-on with bug-triage and onboarding.\n\nWhat I'm looking for: small enough team to keep the test stack honest, big enough product to need real CI discipline. If your team is hiring or you know someone, I'd love a 20-minute chat.",
                "Pomalu otevírám: hledám senior / lead QA Automation role v Praze (nebo remote-friendly EU). 6+ let v Gen a Avastu, Python + Playwright + pytest, bug-triage a onboarding hands-on.\n\nCo hledám: dostatečně malý tým, aby šel test stack udržet poctivý, dostatečně velký produkt, aby potřeboval reálnou CI disciplínu. Pokud nabíráte nebo znáte někoho - rád si dám 20min hovor.",
                is_cs,
            ),
            "char_count": 0,
            "hashtags": ["#opentowork", "#qa", "#automation", "#hiring"],
            "evidence_anchors": ["resume", "user_confirmed"],
            "audience": "recruiter",
            "parent_post_topic": "",
        },
        POST_RECRUITER_OUTREACH: {
            "kind": POST_RECRUITER_OUTREACH,
            "title": _h("Outreach to QualityWorks", "Outreach na QualityWorks", is_cs),
            "body": _h(
                "Hi [Recruiter], I saw the QA Automation Lead opening at QualityWorks (the regression-suite-ownership bit caught my eye - that's most of what I've been doing at Gen for the last two years).\n\nQuick relevant context: I own a Python + Playwright regression suite, helped move 40+ flaky tests below 1%, and partner weekly with the dev squads on triage. On the side I build small Python tools (latest: ApplyPilot AI, a GenAI app for job applications).\n\nIf you have 15 minutes this week, I'd love to chat about the role - my CV is attached.",
                "Dobrý den [Recruiter], všiml jsem si vašeho otevření QA Automation Lead v QualityWorks (vlastnictví regresní sady mě zaujalo - tomu se v Genu věnuju poslední dva roky).\n\nKrátký relevantní kontext: vlastním Python + Playwright regresní sadu, pomohl jsem dostat 40+ flaky testů pod 1 % a týdně s dev týmy řeším triage. Vedle stavím malé Python nástroje (nejnovější: ApplyPilot AI, GenAI aplikace pro pracovní inzeráty).\n\nKdyž najdete tento týden 15 minut, rád si o roli popovídám - životopis je v příloze.",
                is_cs,
            ),
            "char_count": 0,
            "hashtags": [],
            "evidence_anchors": ["resume", "github"],
            "audience": "recruiter",
            "parent_post_topic": "",
        },
        POST_NETWORKING: {
            "kind": POST_NETWORKING,
            "title": _h("Networking note to a QA peer", "Networking poznámka QA kolegovi", is_cs),
            "body": _h(
                "Hi [Name], your Playwright thread on flaky tests this week was great - especially the part about banning hard-coded waits. We had a similar arc at Gen and got 40+ tests below 1% flakiness in a quarter; happy to compare notes if you'd like a 15-minute call.",
                "Ahoj [Jméno], tvůj Playwright thread o flaky testech tento týden byl výborný - hlavně část o zákazu hard-coded waits. Měli jsme v Genu podobný oblouk a dostali jsme 40+ testů pod 1 % flakiness za kvartál; klidně si zavoláme na 15 minut, jestli chceš porovnat poznámky.",
                is_cs,
            ),
            "char_count": 0,
            "hashtags": [],
            "evidence_anchors": ["resume"],
            "audience": "peer",
            "parent_post_topic": "",
        },
        POST_COMMENT: {
            "kind": POST_COMMENT,
            "title": _h("Comment on a Playwright post", "Komentář k Playwright postu", is_cs),
            "body": _h(
                "Strong take. We banned cy.wait + hard-coded ms after our flaky rate hit 12% - cy.intercept + named aliases brought it under 1% inside a quarter. Curious how you handle DB seeds; we lean on Cypress tasks today, considering a fixture-factory rewrite.",
                "Trefa. Zakázali jsme cy.wait + hard-coded ms, když naše flakiness dosáhla 12 % - cy.intercept + pojmenované aliasy to dostaly pod 1 % za kvartál. Jak řešíš DB seedy? My teď spoléháme na Cypress tasks, zvažujeme přepis na fixture-factory.",
                is_cs,
            ),
            "char_count": 0,
            "hashtags": [],
            "evidence_anchors": ["resume"],
            "audience": "peer",
            "parent_post_topic": _h("Playwright flaky test playbook", "Playwright flaky test playbook", is_cs),
        },
    }
    posts: list[dict] = []
    for k in kinds:
        post = pool.get(k)
        if not post:
            continue
        post["char_count"] = len(post["body"])
        posts.append(post)
    if not posts:
        for default_kind in (POST_LEARNING_UPDATE, POST_PROJECT_LAUNCH):
            post = pool.get(default_kind)
            if post:
                post["char_count"] = len(post["body"])
                posts.append(post)
    return {"posts": posts}


# --- Helpers -----------------------------------------------------------


def _h(en: str, cs: str, is_cs: bool) -> str:
    return cs if is_cs else en


# Note: section IDs SEC_LANGUAGES, SEC_VOLUNTEER, SEC_PUBLICATIONS,
# SEC_HONORS are imported above so the section_picker_options can
# stay in sync if the user later wants to surface them - the demo
# pipeline keeps them empty per the no-hallucination rule.
_USED_SECTION_IDS = (
    SEC_LANGUAGES,
    SEC_VOLUNTEER,
    SEC_PUBLICATIONS,
    SEC_HONORS,
)
