"""Section constants + curated demo profile for My Profile.

``DEMO_PROFILE`` lets users explore the section (and the downstream
Career / Jobs / LinkedIn wiring) without spending any tokens. It matches
:data:`src.sections.my_profile.schema.CAREER_PROFILE_SCHEMA`.
"""

from __future__ import annotations

from src.qt.icons import Icons


SECTION_ICON = Icons.ID_CARD
ACCENT = "#14B8A6"  # teal - distinct from Career/Jobs/LinkedIn/Finance


DEMO_PROFILE: dict = {
    "full_name": "Jana Novakova",
    "headline": "Senior QA Engineer",
    "industry": "Software / Fintech",
    "contact": {
        "email": "jana.novakova@example.com",
        "phone": "+420 777 123 456",
        "location": "Praha, Czech Republic",
    },
    "summary": (
        "Senior QA engineer with 7 years across fintech and e-commerce. "
        "Builds Playwright + pytest automation suites, owns release quality "
        "gates, and mentors junior testers. Comfortable bridging manual "
        "exploratory testing and CI-driven automation."
    ),
    "technical_skills": [
        "Playwright", "pytest", "Selenium", "Python", "TypeScript",
        "REST API testing", "Postman", "CI/CD (GitHub Actions)", "SQL",
        "Docker", "JIRA", "TestRail",
    ],
    "experiences": [
        {
            "role": "Senior QA Engineer",
            "company": "TrustPay",
            "period": "2021-2026",
            "employment_type": "",
            "location": "Praha",
            "bullets": [
                "Owned end-to-end automation for the payments dashboard (Playwright + pytest), cutting regression time from 2 days to 3 hours.",
                "Introduced contract testing for 12 internal APIs, catching 30+ breaking changes before release.",
                "Mentored 3 junior testers and ran the weekly bug-triage with product + engineering.",
            ],
        },
        {
            "role": "QA Engineer",
            "company": "Rohlik Group",
            "period": "2018-2021",
            "employment_type": "",
            "location": "Praha",
            "bullets": [
                "Built the first Selenium suite for the checkout flow.",
                "Wrote and maintained 400+ manual test cases in TestRail.",
            ],
        },
    ],
    "education": [
        {
            "institution": "Czech Technical University in Prague",
            "degree": "Bc. Software Engineering",
            "period": "2015-2018",
            "details": "Focus on software testing and databases.",
        },
    ],
    "certifications": [
        {"name": "ISTQB Certified Tester - Foundation Level", "issuer": "ISTQB", "period": "2019"},
    ],
    "languages": [
        {"name": "Czech", "cefr": "C2"},
        {"name": "English", "cefr": "C1"},
        {"name": "German", "cefr": "B1"},
    ],
    "projects": [
        {
            "name": "playwright-fintech-suite",
            "period": "2023",
            "url": "https://github.com/jananovak/playwright-fintech-suite",
            "bullets": [
                "Open-source starter kit for fintech E2E tests with sample CI.",
            ],
        },
    ],
    "online_links": [
        {"label": "LinkedIn", "url": "https://www.linkedin.com/in/jana-novakova"},
        {"label": "GitHub", "url": "https://github.com/jananovak"},
    ],
    "linkedin_present": True,
    "github_present": True,
}
