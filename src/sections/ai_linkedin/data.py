"""Static metadata + demo seed for the AI LinkedIn section.

The "live" helpers (``brand_profile_fields``, ``recent_runs``,
``quick_actions``) read from :data:`STATE` at call time and never
invent data.

The :data:`DEMO_*` constants are curated mock payloads that match the
JSON Schemas in :mod:`src.sections.ai_linkedin.schema`. They power the
section's free, offline Demo mode (see ``pipeline.load_demo``) - turn
it on via the ``...`` header menu and every Output card populates
without sending a single token to the provider.

Persona: senior QA / Test Automation Engineer (same fictional Jana
Novakova used by AI Career so the docs reinforce each other).
"""

from __future__ import annotations

from src.qt.icons import Icons

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
    SEC_POSTS,
    SEC_PROJECTS,
    SEC_RECOMMENDATIONS,
    SEC_SERVICES,
    SEC_SKILLS,
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


SECTION_ICON = Icons.LINKEDIN


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
        {"key": "build_full", "icon": Icons.AUTO_AWESOME, "label": txt["qa_build_full"]},
        {"key": "improve_headline", "icon": Icons.TITLE, "label": txt["qa_improve_headline"]},
        {"key": "write_post", "icon": Icons.EDIT_OUTLINED, "label": txt["qa_write_post"]},
        {"key": "show_history", "icon": Icons.HISTORY, "label": txt["qa_show_history"]},
        {"key": "how_to", "icon": Icons.HELP_OUTLINE, "label": txt["qa_how_to"]},
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
        if isinstance(entry, dict):
            title = entry.get("role") or txt["recent_default_title"]
            when = entry.get("timestamp") or ""
        else:
            title = getattr(entry, "role", "") or txt["recent_default_title"]
            when = getattr(entry, "timestamp", "") or ""
        out.append({"title": title, "time": when})
    if not out:
        out.append({"title": txt["recent_empty_title"], "time": ""})
    return out


# ----------------------------------------------------------------------
# Demo seed
#
# The constants below feed :func:`src.sections.ai_linkedin.pipeline.load_demo`
# and the ``demo_mode`` short-circuits inside the pipeline. They
# represent ONE realistic build for the QA Engineer persona; every
# downstream Output card reads from these so the cross-card details
# stay consistent (same name, same employer, same skills).
# ----------------------------------------------------------------------


DEMO_TARGET_ROLES: list[str] = ["Senior Test Automation Engineer"]


DEMO_PROFILE: dict = {
    "full_name": "Jana Novakova",
    "headline_current": "Senior QA Engineer @ TrustPay",
    "industry": "FinTech",
    "location": "Prague, Czechia",
    "contact": {
        "email": "jana.novakova@example.com",
        "phone": "+420 605 123 456",
    },
    "summary": (
        "Senior QA engineer with 7 years of automation experience in "
        "fintech and SaaS. Owns the Playwright + Pytest pyramid at "
        "TrustPay, mentors juniors, and ships an open-source checkout "
        "kit."
    ),
    "experiences": [
        {
            "role": "Senior QA Engineer",
            "company": "TrustPay",
            "period": "2022 - present",
            "employment_type": "full_time",
            "location": "Prague",
            "bullets": [
                "Owned Playwright + Pytest pyramid, green-build rate 71% -> 95%.",
                "Mentored two juniors to mid-level.",
                "Cut median CI runtime 38 -> 14 minutes.",
            ],
            "evidence_anchor": "resume",
        },
        {
            "role": "QA Engineer",
            "company": "Productboard",
            "period": "2019 - 2022",
            "employment_type": "full_time",
            "location": "Prague",
            "bullets": [
                "Wrote ~600 Playwright E2E tests across checkout, "
                "roadmap, onboarding.",
                "Set up GitHub Actions matrix runs across Chromium, "
                "Firefox, WebKit.",
            ],
            "evidence_anchor": "resume",
        },
    ],
    "education": [
        {
            "institution": "Masaryk University, Faculty of Informatics",
            "degree": "Bachelor's, Applied Informatics",
            "period": "2014 - 2018",
            "details": "Thesis on automated UI testing for banking apps.",
            "evidence_anchor": "resume",
        },
    ],
    "certifications": [
        {
            "name": "ISTQB Advanced Test Automation Engineer",
            "issuer": "ISTQB",
            "year": "2023",
            "evidence_anchor": "resume",
        },
    ],
    "languages": [
        {"name": "Czech", "cefr": "C2"},
        {"name": "English", "cefr": "C1"},
        {"name": "German", "cefr": "B1"},
    ],
    "skills": [
        {"name": "Playwright", "category": "core", "evidence_anchor": "resume"},
        {"name": "Pytest", "category": "core", "evidence_anchor": "resume"},
        {"name": "Python", "category": "core", "evidence_anchor": "resume"},
        {"name": "TypeScript", "category": "core", "evidence_anchor": "resume"},
        {"name": "GitHub Actions", "category": "tooling", "evidence_anchor": "resume"},
        {"name": "Docker", "category": "tooling", "evidence_anchor": "resume"},
        {"name": "PostgreSQL", "category": "tooling", "evidence_anchor": "resume"},
        {"name": "Mentoring", "category": "soft", "evidence_anchor": "resume"},
        {"name": "Payments", "category": "domain", "evidence_anchor": "resume"},
    ],
    "projects": [
        {
            "name": "pw-checkout-kit",
            "period": "2024 - present",
            "description": (
                "Open-source Playwright kit for testing Stripe / Adyen "
                "checkout flows. 120+ stars, used by 3 fintech teams."
            ),
            "url": "https://github.com/jana-qa/pw-checkout-kit",
            "evidence_anchor": "github",
        },
    ],
    "online_links": [
        {
            "label": "LinkedIn",
            "url": "https://linkedin.com/in/jana-qa",
            "evidence_anchor": "linkedin_export",
        },
        {
            "label": "GitHub",
            "url": "https://github.com/jana-qa",
            "evidence_anchor": "github",
        },
    ],
    "linkedin_present": True,
    "github_present": True,
}


DEMO_HEADLINES: dict = {
    "variants": [
        {
            "text": (
                "Senior Test Automation Engineer | Playwright + Pytest | "
                "Cut TrustPay CI runtime 38 -> 14 min | Open-source "
                "pw-checkout-kit"
            ),
            "audience": "recruiter",
            "char_count": 138,
            "evidence_anchors": ["resume", "github"],
            "focus": "Quantitative wins",
        },
        {
            "text": (
                "QA guild lead @ TrustPay - Playwright, Pytest, k6 - "
                "mentored 2 juniors to mid-level"
            ),
            "audience": "hiring_manager",
            "char_count": 94,
            "evidence_anchors": ["resume"],
            "focus": "Leadership signal",
        },
        {
            "text": (
                "Test Automation Engineer | Open-source author "
                "(pw-checkout-kit) | Talks about Playwright + CI"
            ),
            "audience": "peer",
            "char_count": 109,
            "evidence_anchors": ["github"],
            "focus": "Community profile",
        },
    ],
}


DEMO_ABOUT: dict = {
    "short_version": (
        "Senior QA engineer (7 yrs) - Playwright + Pytest at TrustPay. "
        "I cut CI runtime 38 -> 14 min and mentored 2 juniors to "
        "mid-level. Open to senior automation roles."
    ),
    "medium_version": (
        "I am a senior QA engineer with 7 years of automation "
        "experience in fintech and SaaS. At TrustPay I own the "
        "Playwright + Pytest test pyramid for the merchant dashboard - "
        "we lifted nightly green-build rate from 71% to 95% and I "
        "mentored two juniors to mid-level within 12 months.\n\n"
        "Outside work I maintain pw-checkout-kit, an open-source "
        "Playwright kit used by 3 fintech teams. I am looking for "
        "senior automation roles where I can shape strategy across "
        "multiple squads."
    ),
    "long_version": (
        "I am a senior QA engineer with 7 years of automation "
        "experience across fintech and SaaS. My favourite kind of "
        "problem is the boring one nobody else wants to take: flaky "
        "tests, broken CI pipelines, deprecated fixtures, and the "
        "long tail of regression bugs that hide behind 'works on my "
        "machine'.\n\n"
        "At TrustPay I own the Playwright + Pytest test pyramid for "
        "the merchant dashboard. Working with the platform team, we "
        "lifted nightly green-build rate from 71% to 95% and cut "
        "median CI runtime from 38 to 14 minutes through sharding, "
        "session-scoped auth fixtures, and a flake quarantine pipeline. "
        "I have been mentoring two juniors who were both promoted to "
        "mid-level within 12 months.\n\n"
        "I write a lot about test architecture on LinkedIn (mostly "
        "Playwright and CI patterns) and maintain pw-checkout-kit, an "
        "open-source Playwright kit for Stripe / Adyen checkout "
        "flows used by 3 fintech teams.\n\n"
        "I am looking for senior automation roles where I can shape "
        "strategy across multiple squads, partner with engineering "
        "leadership, and keep mentoring."
    ),
    "technical_version": (
        "Senior QA engineer specialising in Playwright + Pytest test "
        "pyramids for fintech web apps. Stack: Python, TypeScript, "
        "GitHub Actions / GitLab CI, Docker, PostgreSQL. Comfortable "
        "with k6 (learning) and Pact (POC). Recent measurable wins: "
        "TrustPay nightly green-build 71% -> 95%, CI runtime 38 -> 14 "
        "min, two juniors promoted to mid-level, 600+ Playwright E2E "
        "tests at Productboard. Open-source author of pw-checkout-kit."
    ),
    "recruiter_version": (
        "Senior Test Automation Engineer (7 yrs in fintech / SaaS) "
        "open to roles in Prague or fully remote within EU. Owns the "
        "TrustPay Playwright + Pytest test pyramid, mentors juniors, "
        "and maintains the open-source pw-checkout-kit. Comfortable "
        "with full-time, four-day week, or contract."
    ),
    "char_counts": {
        "short_version": 168,
        "medium_version": 442,
        "long_version": 1280,
        "technical_version": 432,
        "recruiter_version": 318,
    },
}


DEMO_EXPERIENCE_REWRITES: dict = {
    "roles": [
        {
            "role": "Senior QA Engineer",
            "company": "TrustPay",
            "period": "2022 - present",
            "linkedin_description": (
                "Owning the test automation strategy for the merchant "
                "payments dashboard."
            ),
            "bullets": [
                "Owned the Playwright + Pytest test pyramid, lifting "
                "nightly green-build rate from 71% to 95%.",
                "Cut median CI runtime from 38 to 14 minutes via "
                "sharding + session-scoped auth fixtures.",
                "Mentored two junior testers; both promoted to "
                "mid-level within 12 months.",
            ],
            "suggested_skills": [
                {"name": "Playwright", "evidence_anchor": "resume"},
                {"name": "Pytest", "evidence_anchor": "resume"},
                {"name": "Mentoring", "evidence_anchor": "resume"},
            ],
            "do_not_claim": [
                "Production k6 ownership - currently a 2-week spike, "
                "not a long-term project.",
            ],
        },
        {
            "role": "QA Engineer",
            "company": "Productboard",
            "period": "2019 - 2022",
            "linkedin_description": (
                "Built end-to-end Playwright coverage for the product "
                "roadmap SaaS."
            ),
            "bullets": [
                "Wrote ~600 Playwright E2E tests across checkout, "
                "roadmap, and onboarding.",
                "Set up GitHub Actions matrix runs across Chromium, "
                "Firefox, and WebKit.",
            ],
            "suggested_skills": [
                {"name": "Playwright", "evidence_anchor": "resume"},
                {"name": "GitHub Actions", "evidence_anchor": "resume"},
            ],
            "do_not_claim": [],
        },
    ],
}


DEMO_SKILLS_BUCKETS: dict = {
    "core": [
        {"name": "Playwright", "category": "core", "evidence_anchor": "resume",
         "evidence_quote": "Owned the Playwright + Pytest test pyramid",
         "reason": "Listed in JD must-have."},
        {"name": "Pytest", "category": "core", "evidence_anchor": "resume",
         "evidence_quote": "Pytest fixtures + auth setup",
         "reason": "Listed in JD must-have."},
        {"name": "Python", "category": "core", "evidence_anchor": "resume",
         "evidence_quote": "Daily driver at TrustPay",
         "reason": "Listed in JD must-have."},
        {"name": "Mentoring", "category": "soft", "evidence_anchor": "resume",
         "evidence_quote": "Two juniors promoted to mid-level",
         "reason": "QA guild lead expectation."},
    ],
    "to_verify": [
        {"name": "TypeScript", "category": "core", "evidence_anchor": "resume",
         "evidence_quote": "Used in Playwright suite at Productboard",
         "reason": "Frequent but not headline."},
    ],
    "to_learn": [
        {"name": "k6", "category": "tooling", "evidence_anchor": "missing_evidence",
         "evidence_quote": "",
         "reason": "Nice-to-have on JD."},
        {"name": "Pact", "category": "tooling", "evidence_anchor": "missing_evidence",
         "evidence_quote": "",
         "reason": "Nice-to-have on JD."},
    ],
    "do_not_claim": [
        {"name": "GraphQL federation", "category": "core", "evidence_anchor": "missing_evidence",
         "evidence_quote": "",
         "reason": "Never mentioned in source material."},
    ],
}


DEMO_FEATURED: dict = {
    "items": [
        {
            "title": "pw-checkout-kit on GitHub",
            "description": (
                "Open-source Playwright kit for Stripe / Adyen "
                "checkout flows."
            ),
            "url": "https://github.com/jana-qa/pw-checkout-kit",
            "evidence_anchor": "github",
        },
        {
            "title": "PyConCZ 2025 talk - 'Killing flaky tests at scale'",
            "description": (
                "Walkthrough of the TrustPay flake-quarantine pipeline "
                "and the 38 -> 14 min CI runtime story."
            ),
            "url": "https://youtu.be/example",
            "evidence_anchor": "user_confirmed",
        },
    ],
}


DEMO_PROJECTS: dict = {
    "projects": [
        {
            "name": "pw-checkout-kit",
            "period": "2024 - present",
            "description": (
                "Open-source Playwright kit for testing Stripe / Adyen "
                "checkout flows. 120+ stars, used by 3 fintech teams."
            ),
            "url": "https://github.com/jana-qa/pw-checkout-kit",
            "evidence_anchor": "github",
        },
    ],
}


DEMO_RECOMMENDATION_MESSAGES: dict = {
    "templates": [
        {
            "audience": "former_manager",
            "subject": "Quick LinkedIn recommendation?",
            "body": (
                "Hi Pavel,\n\nWould you be open to writing a short "
                "LinkedIn recommendation focused on my work on the "
                "TrustPay test pyramid? Two-three sentences are "
                "plenty - happy to share a draft if helpful.\n\n"
                "Thanks,\nJana"
            ),
        },
        {
            "audience": "peer",
            "subject": "LinkedIn recommendation swap?",
            "body": (
                "Ahoj Tomas,\n\nIf you have a spare 10 minutes this "
                "week, would you be up for a quick LinkedIn "
                "recommendation swap? I'd focus on our pairing on the "
                "Playwright migration. Happy to write yours first.\n\n"
                "Jana"
            ),
        },
    ],
}


DEMO_POSTS: dict = {
    "posts": [
        {
            "kind": "learning_update",
            "title": "Killing flaky tests at scale",
            "body": (
                "Three things that finally moved the needle on our "
                "TrustPay Playwright suite:\n\n"
                "1. Session-scoped auth fixtures - stopped relogging "
                "for every test, shaved ~6 min off the matrix.\n"
                "2. Flake quarantine pipeline - unstable tests gate "
                "in a separate job so they cannot block deploys.\n"
                "3. Quarterly 'kill list' review - any test that has "
                "not failed for 6 months gets deleted on the spot.\n\n"
                "Result: nightly green-build rate went from 71% to "
                "95% and median CI runtime fell from 38 to 14 min. "
                "Happy to dig into any of these in the comments!"
            ),
            "hashtags": ["#Playwright", "#Pytest", "#CICD"],
        },
        {
            "kind": "project_launch",
            "title": "pw-checkout-kit v0.4 is out",
            "body": (
                "Just released pw-checkout-kit v0.4 - a Playwright "
                "kit for testing Stripe / Adyen checkout flows. "
                "v0.4 ships a Pytest plugin and ships a Pact "
                "consumer-side proof-of-concept. If you ship "
                "payments to production with Playwright, give it a "
                "spin and let me know what is missing!"
            ),
            "hashtags": ["#Playwright", "#fintech", "#opensource"],
        },
    ],
}


DEMO_COMPLETENESS: dict = {
    "items": [
        {"key": "headline", "label": "Headline is concise and signal-rich", "status": "ok",
         "note": "138 chars - within the 220 cap."},
        {"key": "about", "label": "About section has 5 length variants", "status": "ok",
         "note": ""},
        {"key": "skills", "label": "Skills bucketed (core / verify / learn / never)", "status": "ok",
         "note": ""},
        {"key": "experience", "label": "Top two roles rewritten in LinkedIn voice", "status": "ok",
         "note": ""},
        {"key": "featured", "label": "Featured section has 2 items", "status": "ok",
         "note": ""},
        {"key": "projects", "label": "Projects has at least one item with URL", "status": "ok",
         "note": ""},
        {"key": "recommendations", "label": "Two recommendation request drafts", "status": "ok",
         "note": ""},
        {"key": "posts", "label": "Posts queue has 2 starter posts", "status": "ok",
         "note": ""},
        {"key": "checklist", "label": "Languages + education + certifications filled", "status": "ok",
         "note": ""},
    ],
}


DEMO_UNSUPPORTED_CLAIMS: dict = {
    "rows": [
        {
            "claim": "Production k6 ownership",
            "source_section": "experience",
            "why_it_is_unsupported": (
                "JD lists k6 as nice-to-have; user has only run a "
                "2-week spike."
            ),
            "suggested_fix": (
                "Reword as 'Currently piloting k6 perf testing' "
                "instead of 'Owned k6 perf testing'."
            ),
        },
    ],
}


DEMO_PROFILE_SCORE: dict = {
    "overall_score": 84,
    "breakdown": [
        {"label": "Headline + About", "score": 92},
        {"label": "Experience", "score": 88},
        {"label": "Skills + endorsements", "score": 82},
        {"label": "Featured + Projects", "score": 78},
        {"label": "Recommendations", "score": 70},
    ],
    "summary": (
        "Strong baseline. Two quick wins: ask Pavel for a TrustPay "
        "recommendation and publish v0.5 of pw-checkout-kit so the "
        "Featured section has a recent timestamp."
    ),
}
