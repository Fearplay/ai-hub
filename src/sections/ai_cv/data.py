"""Static metadata + demo seed for the AI Career section.

The :data:`DEMO_*` constants are curated mock payloads that match the
JSON Schemas in :mod:`src.sections.ai_cv.schema`. They power the
section's free, offline Demo mode (see ``pipeline.load_demo``) - turn
it on via the ``...`` header menu and every analysis tab populates
without sending a single token to the provider.

Persona: Senior QA Engineer applying to a Senior Test Automation
Engineer role at a fintech (TrustPay). The same persona shows up in
every demo so the Match / Documents / Modern CV cards reinforce each
other.
"""

from __future__ import annotations

from src.qt.icons import Icons


SECTION_ICON = Icons.ASSIGNMENT_IND_OUTLINED


DEMO_TARGET_ROLE = "Senior Test Automation Engineer"


# Matches ``schema.CANDIDATE_SCHEMA``.
DEMO_CANDIDATE: dict = {
    "full_name": "Jana Novakova",
    "contact": {
        "email": "jana.novakova@example.com",
        "phone": "+420 605 123 456",
        "location": "Prague, Czechia",
    },
    "summary": (
        "Senior QA engineer with 7 years of experience designing test "
        "frameworks for fintech and SaaS products. Comfortable owning "
        "release sign-off, mentoring two junior testers, and shipping "
        "Playwright + Pytest suites that block 95% of regressions before "
        "production."
    ),
    "technical_skills": [
        "Playwright",
        "Pytest",
        "Selenium",
        "Postman",
        "REST APIs",
        "GraphQL",
        "GitHub Actions",
        "GitLab CI",
        "Docker",
        "PostgreSQL",
        "Python",
        "TypeScript",
    ],
    "experiences": [
        {
            "role": "Senior QA Engineer",
            "company": "TrustPay",
            "period": "2022 - 2026",
            "employment_type": "",
            "location": "Prague",
            "bullets": [
                "Owned the Playwright + Pytest test pyramid for the "
                "merchant dashboard, lifting nightly green-build rate "
                "from 71% to 95%.",
                "Mentored two junior testers; both moved to mid-level "
                "within 12 months.",
                "Drove flaky-test triage and cut median CI runtime from "
                "38 to 14 minutes.",
            ],
        },
        {
            "role": "QA Engineer",
            "company": "Productboard",
            "period": "2019 - 2022",
            "employment_type": "",
            "location": "Prague",
            "bullets": [
                "Wrote ~600 Playwright E2E tests covering checkout, "
                "roadmap, and onboarding flows.",
                "Set up GitHub Actions matrix runs across Chromium, "
                "Firefox, and WebKit.",
            ],
        },
        {
            "role": "QA Tester",
            "company": "Inveo",
            "period": "2018 - 2019",
            "employment_type": "Internship",
            "location": "Brno",
            "bullets": [
                "Ran manual regression rounds for an insurance broker "
                "platform; logged 200+ reproducible defects in Jira.",
            ],
        },
    ],
    "education": [
        {
            "institution": "Masaryk University, Faculty of Informatics",
            "degree": "Bachelor's degree, Applied Informatics",
            "period": "2014 - 2018",
            "details": "Thesis on automated UI testing for banking apps.",
        },
    ],
    "certifications": [
        {
            "name": "ISTQB Advanced Test Automation Engineer",
            "issuer": "ISTQB",
            "period": "2023",
        },
    ],
    "languages": [
        {"name": "Czech", "cefr": "C2"},
        {"name": "English", "cefr": "C1"},
        {"name": "German", "cefr": "B1"},
    ],
    "projects": [
        {
            "name": "pw-checkout-kit",
            "period": "2024 - present",
            "bullets": [
                "Open-source Playwright kit for testing Stripe / Adyen "
                "checkout flows.",
                "120+ GitHub stars, used by 3 fintech teams.",
            ],
            "url": "https://github.com/jana-qa/pw-checkout-kit",
        },
    ],
    "linkedin_present": True,
    "github_present": True,
}


# Matches ``schema.JOB_SPEC_SCHEMA``.
DEMO_JOB_SPEC: dict = {
    "title": "Senior Test Automation Engineer",
    "company": "TrustPay",
    "location": "Prague (hybrid)",
    "seniority": "senior",
    "summary": (
        "Own the test automation strategy for the merchant payments "
        "platform. Lead a small QA guild, define standards for "
        "Playwright + Pytest, and partner with engineering to keep "
        "release cadence weekly."
    ),
    "must_have": [
        "5+ years of test automation in production",
        "Playwright or Cypress proficiency",
        "Pytest + Python",
        "CI pipelines (GitHub Actions or GitLab CI)",
        "Experience triaging flaky tests at scale",
    ],
    "nice_to_have": [
        "Performance testing with k6",
        "Contract testing (Pact)",
        "Fintech / payments domain background",
    ],
    "tools": [
        "Playwright",
        "Pytest",
        "Postman",
        "GitHub Actions",
        "Docker",
        "PostgreSQL",
    ],
    "soft_skills": [
        "Mentoring",
        "Cross-team communication",
        "Release ownership",
    ],
    "ats_keywords": [
        "Playwright",
        "Pytest",
        "Selenium",
        "CI/CD",
        "Python",
        "TypeScript",
        "REST",
        "GraphQL",
        "k6",
        "Pact",
    ],
    "compensation": "EUR 4 200 - 5 400 / month",
    "employment_type": "Full-time",
}


# Matches ``schema.MATCH_ANALYSIS_SCHEMA``.
DEMO_MATCH: dict = {
    "overall_score": 86,
    "verdict": "Strong fit. Two minor gaps to flag in the interview.",
    "categories": [
        {
            "name": "Test automation craft",
            "score": 92,
            "evidence": [
                "Owned the Playwright + Pytest pyramid at TrustPay",
                "Open-source pw-checkout-kit project",
            ],
        },
        {
            "name": "CI / DevOps",
            "score": 84,
            "evidence": [
                "Reduced CI runtime from 38 to 14 minutes",
                "Set up GitHub Actions matrix runs",
            ],
        },
        {
            "name": "Leadership",
            "score": 78,
            "evidence": [
                "Mentored two junior testers to mid-level",
            ],
        },
        {
            "name": "Performance / contract testing",
            "score": 58,
            "evidence": [
                "No production k6 / Pact experience listed",
            ],
        },
    ],
    "matches": [
        "Playwright + Pytest stack matches the must-have list 1:1",
        "Direct payments-domain experience at TrustPay",
        "Mentoring experience aligns with the QA guild lead expectation",
        "Reduced CI runtime - directly addresses 'flaky tests at scale'",
    ],
    "gaps": [
        "No k6 / performance testing on record",
        "No Pact / contract testing experience listed",
    ],
    "ats_keywords_present": [
        "Playwright",
        "Pytest",
        "Python",
        "TypeScript",
        "REST",
        "GraphQL",
    ],
    "ats_keywords_missing": [
        "k6",
        "Pact",
    ],
    "evidence_preview": [
        "TrustPay - Senior QA Engineer (2022 - 2026): lifted nightly "
        "green-build rate from 71% to 95%.",
        "TrustPay: cut median CI runtime from 38 to 14 minutes.",
        "Productboard - Wrote ~600 Playwright E2E tests across "
        "Chromium / Firefox / WebKit.",
        "Mentored two junior testers; both promoted within 12 months.",
        "pw-checkout-kit: open-source Playwright kit used by 3 fintech "
        "teams.",
    ],
    "interview_questions": [
        {
            "question": (
                "Walk me through how you reduced TrustPay's CI runtime "
                "from 38 to 14 minutes."
            ),
            "why_asked": (
                "The JD calls out 'experience triaging flaky tests at "
                "scale' - they want concrete proof you have done it."
            ),
            "suggested_answer": (
                "**Situation:** TrustPay's nightly Playwright suite was "
                "blocking releases at 38 minutes with ~20% flake rate. "
                "**Task:** halve the runtime without dropping coverage. "
                "**Action:** I introduced test sharding across 4 GitHub "
                "Actions runners, moved auth setup into a session-scoped "
                "fixture, and added a flake-quarantine tag so unstable "
                "tests gated separately. **Result:** runtime fell to 14 "
                "minutes and flake rate dropped to 4%."
            ),
        },
        {
            "question": "How would you approach introducing k6 here?",
            "why_asked": (
                "Performance testing is a nice-to-have - they want to "
                "see how you ramp on unfamiliar tooling."
            ),
            "suggested_answer": (
                "**Situation:** I would treat it as a 2-week spike. "
                "**Task:** build a baseline k6 script for the checkout "
                "endpoint. **Action:** lift the existing Pytest fixtures "
                "to feed k6 with real auth tokens, then wire k6 into "
                "the same GitHub Actions matrix and publish results to "
                "Grafana. **Result:** the team gets a repeatable "
                "perf-regression gate without adding another tool to "
                "the day-to-day workflow."
            ),
        },
        {
            "question": (
                "Tell me about a time you mentored a struggling teammate."
            ),
            "why_asked": (
                "QA guild lead is part of the role; they want to see "
                "your mentoring approach in detail."
            ),
            "suggested_answer": (
                "**Situation:** A junior tester at TrustPay was missing "
                "regressions during code review. **Task:** raise their "
                "confidence without slowing the team down. **Action:** I "
                "paired with them for two sprints, set up a private "
                "checklist of high-risk areas, and co-owned the next "
                "release sign-off. **Result:** they caught two critical "
                "checkout bugs in the following sprint and were promoted "
                "to mid-level six months later."
            ),
        },
        {
            "question": "How do you decide what NOT to automate?",
            "why_asked": (
                "Senior automation roles are about judgement, not just "
                "test count - they screen for ROI awareness."
            ),
            "suggested_answer": (
                "**Situation:** Early at Productboard I owned a 600-test "
                "Playwright suite, half of which never caught a real "
                "bug. **Task:** focus the suite on real risk. "
                "**Action:** I introduced a quarterly 'kill list' "
                "review - any test that had not failed for 6 months and "
                "was not covering a critical user flow got deleted. "
                "**Result:** suite shrank to ~380 tests, runtime "
                "dropped 25%, and signal-to-noise on red builds "
                "improved noticeably."
            ),
        },
        {
            "question": (
                "How would you partner with backend engineers on "
                "contract testing here?"
            ),
            "why_asked": (
                "Pact is listed as nice-to-have; this is a chance to "
                "show you understand cross-team contracts even without "
                "production Pact experience."
            ),
            "suggested_answer": (
                "**Situation:** I have not run Pact in production yet, "
                "but the principle of consumer-driven contracts is "
                "familiar from my Playwright API tests. **Task:** "
                "introduce Pact without slowing backend velocity. "
                "**Action:** I would start with one critical merchant "
                "endpoint, write the consumer contract from the "
                "Playwright suite, and pair with the backend lead on "
                "the provider verification step. **Result:** we get a "
                "tangible win on one endpoint before scaling, and the "
                "backend team sees the value before committing to the "
                "tooling."
            ),
        },
    ],
    "skill_gap_plan": [
        {
            "skill": "k6 performance testing",
            "action": (
                "Build a baseline checkout-endpoint k6 script and wire "
                "it into the existing CI matrix."
            ),
            "timeline_weeks": 4,
            "criticality": "important",
            "why_it_matters": (
                "TrustPay's JD lists k6 as a nice-to-have but the SRE "
                "team relies on perf regressions blocking deploys - "
                "the role will eventually be expected to own this."
            ),
            "learning_path": [
                "Read the k6 'First Test' + 'Thresholds' docs end-to-end.",
                "Port one existing Playwright login fixture to a k6 "
                "scenario.",
                "Publish a small public repo with a Grafana dashboard "
                "showing baseline + threshold breach.",
            ],
            "suggested_project": (
                "Open-source 'pw2k6' helper that exports Playwright "
                "auth state into a reusable k6 fixture."
            ),
        },
        {
            "skill": "Pact contract testing",
            "action": (
                "Stand up consumer-driven Pact tests for one merchant "
                "endpoint as a proof-of-concept."
            ),
            "timeline_weeks": 6,
            "criticality": "nice_to_have",
            "why_it_matters": (
                "Reduces integration breakage when backend services "
                "change, which is a recurring TrustPay pain point per "
                "the JD's 'weekly release cadence' note."
            ),
            "learning_path": [
                "Complete the official Pact 5-day workshop.",
                "Pair with a backend engineer on one verified contract.",
                "Document a team rollout plan in an ADR.",
            ],
            "suggested_project": (
                "Internal POC repo that introduces Pact for a single "
                "endpoint plus an ADR template the rest of the org can "
                "follow."
            ),
        },
    ],
}


# Markdown bodies for the ``DOC_*`` kinds. Short but realistic - they
# only have to look right in the preview pane, the real LLM output is
# 4-6 pages longer.
DEMO_DOCUMENTS: dict = {
    "tailored_cv": (
        "# Jana Novakova\n"
        "**Senior Test Automation Engineer** | Prague, CZ | jana.novakova@example.com | +420 605 123 456\n\n"
        "## Profile\n"
        "Senior QA engineer with 7 years of experience designing "
        "Playwright + Pytest automation for payments and SaaS products. "
        "Owned release sign-off, mentored two juniors to mid-level, "
        "and cut TrustPay CI runtime from 38 to 14 minutes.\n\n"
        "## Experience\n"
        "**Senior QA Engineer** - TrustPay (2022 - 2026)\n"
        "- Owned the Playwright + Pytest test pyramid, lifting nightly "
        "green-build rate from 71% to 95%.\n"
        "- Mentored two junior testers to mid-level within 12 months.\n"
        "- Reduced median CI runtime from 38 to 14 minutes through "
        "sharding + fixture rework.\n\n"
        "**QA Engineer** - Productboard (2019 - 2022)\n"
        "- Wrote ~600 Playwright E2E tests covering checkout, "
        "roadmap, and onboarding.\n"
        "- Set up GitHub Actions matrix runs across Chromium / Firefox "
        "/ WebKit.\n\n"
        "## Skills\n"
        "Playwright | Pytest | Selenium | Postman | Python | "
        "TypeScript | GitHub Actions | GitLab CI | Docker | PostgreSQL\n"
    ),
    "cover_letter": (
        "Dear TrustPay Hiring Team,\n\n"
        "I am applying for the Senior Test Automation Engineer role. "
        "Over the last four years at TrustPay I have owned the "
        "Playwright + Pytest test pyramid for the merchant dashboard, "
        "lifted nightly green-build rate from 71% to 95%, and cut CI "
        "runtime from 38 to 14 minutes through sharding and fixture "
        "rework.\n\n"
        "I am especially excited about leading the QA guild full-time: "
        "the two junior testers I mentored last year were both "
        "promoted to mid-level, and I would love to scale that "
        "approach across the broader team. My open-source "
        "pw-checkout-kit project is already used by three fintech "
        "teams, which I see as direct preparation for the cross-team "
        "test-strategy ownership the role calls for.\n\n"
        "I would welcome the chance to discuss how I can help TrustPay "
        "keep its weekly release cadence safe.\n\n"
        "Best regards,\n"
        "Jana Novakova"
    ),
    "match_report": (
        "# Match Report - 86 / 100\n\n"
        "**Verdict:** Strong fit, two minor gaps.\n\n"
        "## What aligns\n"
        "- Playwright + Pytest stack maps 1:1 to the must-have list.\n"
        "- Direct payments-domain experience at TrustPay itself.\n"
        "- Demonstrated CI runtime reduction (38 -> 14 minutes) "
        "addresses 'flaky tests at scale'.\n"
        "- Mentoring two juniors to mid-level supports the QA guild "
        "leadership expectation.\n\n"
        "## Gaps to flag\n"
        "- k6 / performance testing has no production track record yet.\n"
        "- Pact / contract testing is not on the CV.\n\n"
        "Both gaps are addressable inside the first quarter - see the "
        "Skill Gap Plan tab for a concrete 4 + 6 week plan."
    ),
    "interview_prep": (
        "# Interview Preparation\n\n"
        "## Likely areas\n"
        "1. **CI flake reduction** - bring concrete numbers and the "
        "TrustPay sharding example.\n"
        "2. **Mentoring approach** - the two-sprint pairing story is "
        "the strongest narrative.\n"
        "3. **Ramping on k6** - prepare a 2-week spike plan, not a "
        "defensive answer.\n"
        "4. **Cross-team contracts (Pact)** - acknowledge the gap, "
        "pitch the consumer-driven POC approach.\n\n"
        "## Questions to ask back\n"
        "- How does the QA guild currently report to engineering "
        "leadership?\n"
        "- What is the longest release-blocking flake of the last "
        "quarter and how was it resolved?\n"
        "- How much of the perf-testing roadmap is on the QA team vs. "
        "SRE?"
    ),
    "skill_gap": (
        "# Skill Gap Plan\n\n"
        "## 1. k6 performance testing (4 weeks, important)\n"
        "- Read the k6 'First Test' + 'Thresholds' docs.\n"
        "- Port one existing Playwright login fixture into a k6 "
        "scenario.\n"
        "- Publish a small public repo with a Grafana dashboard "
        "showing baseline + threshold breach.\n\n"
        "**Suggested project:** open-source 'pw2k6' helper that "
        "exports Playwright auth state into a reusable k6 fixture.\n\n"
        "## 2. Pact contract testing (6 weeks, nice to have)\n"
        "- Complete the official Pact 5-day workshop.\n"
        "- Pair with a backend engineer on one verified contract.\n"
        "- Document a team rollout plan in an ADR.\n\n"
        "**Suggested project:** internal POC introducing Pact for one "
        "merchant endpoint plus an ADR template the rest of the org "
        "can follow."
    ),
    "evidence": (
        "# Evidence summary\n\n"
        "## Source signals\n"
        "- **TrustPay** (2022 - 2026): owned test pyramid, lifted "
        "green-build rate from 71% to 95%.\n"
        "- **Productboard** (2019 - 2022): 600+ Playwright E2E tests, "
        "GitHub Actions matrix runs.\n"
        "- **pw-checkout-kit** (open-source): 120+ GitHub stars, used "
        "by 3 fintech teams.\n\n"
        "Demo mode: this evidence pane is normally aggregated from the "
        "candidate JSON + the live GitHub scrape."
    ),
}


# Matches ``schema.MODERN_CV_SCHEMA`` - the structured payload behind
# the fancy two-column Modern CV renderer.
DEMO_MODERN_CV_DATA: dict = {
    "full_name": "Jana Novakova",
    "role_headline": "Senior Test Automation Engineer",
    "role_subtitle": "QA guild lead - acting",
    "contact": {
        "location": "Prague, Czechia",
        "email": "jana.novakova@example.com",
        "phone": "+420 605 123 456",
    },
    "online_links": [
        {
            "icon": "in",
            "label": "linkedin.com/in/jana-qa",
            "url": "https://linkedin.com/in/jana-qa",
        },
        {
            "icon": "gh",
            "label": "github.com/jana-qa",
            "url": "https://github.com/jana-qa",
        },
    ],
    "skill_groups": [
        {
            "label": "Test automation",
            "tags": ["Playwright", "Pytest", "Selenium", "Postman"],
        },
        {
            "label": "CI / DevOps",
            "tags": ["GitHub Actions", "GitLab CI", "Docker"],
        },
        {
            "label": "Languages",
            "tags": ["Python", "TypeScript", "SQL"],
        },
    ],
    "languages": [
        {"name": "Czech", "level": "native"},
        {"name": "English", "level": "C1"},
        {"name": "German", "level": "B1"},
    ],
    "profile_summary": (
        "Senior QA engineer with 7 years of automation experience in "
        "**fintech and SaaS**. Owned the **Playwright + Pytest** test "
        "pyramid at TrustPay, lifted nightly green-build rate from "
        "**71% to 95%**, and mentored two juniors to mid-level. "
        "Acting **QA guild lead** since 2024, comfortable owning "
        "release sign-off and partnering with backend on contract "
        "boundaries."
    ),
    "leadership_highlights": [
        "**Lifted nightly green-build rate** from 71% to 95% at "
        "TrustPay",
        "**Cut median CI runtime** from 38 to 14 minutes through "
        "sharding + fixture rework",
        "**Mentored two junior testers** to mid-level within 12 months",
        "Open-source **pw-checkout-kit** used by 3 fintech teams",
    ],
    "experience": [
        {
            "role": "Senior QA Engineer",
            "period": "2022 - 2026",
            "company": "TrustPay",
            "context": "Merchant payments platform - Prague",
            "highlight_pills": ["Playwright", "Mentoring", "CI ownership"],
            "bullets": [
                "Owned the **Playwright + Pytest** test pyramid, "
                "lifting nightly green-build rate from **71% to 95%**.",
                "**Mentored two junior testers**; both promoted to "
                "mid-level within 12 months.",
                "**Cut median CI runtime** from 38 to 14 minutes via "
                "sharding + session-scoped auth fixtures.",
            ],
        },
        {
            "role": "QA Engineer",
            "period": "2019 - 2022",
            "company": "Productboard",
            "context": "Product roadmap SaaS - Prague",
            "highlight_pills": ["E2E", "Playwright", "Cross-browser"],
            "bullets": [
                "Wrote **~600 Playwright E2E tests** covering "
                "checkout, roadmap, and onboarding.",
                "Set up **GitHub Actions matrix runs** across "
                "Chromium / Firefox / WebKit.",
            ],
        },
    ],
    "projects": [
        {
            "name": "pw-checkout-kit",
            "description": (
                "Open-source Playwright kit for testing Stripe / "
                "Adyen checkout flows. **120+ GitHub stars**, used by "
                "3 fintech teams."
            ),
            "url": "https://github.com/jana-qa/pw-checkout-kit",
        },
    ],
    "education": [
        {
            "title": "Bachelor's, Applied Informatics",
            "sub": "Masaryk University, Faculty of Informatics",
            "period": "2014 - 2018",
        },
    ],
    "certifications": [
        {
            "year": "2023",
            "text": "ISTQB **Advanced Test Automation Engineer**",
        },
    ],
}
