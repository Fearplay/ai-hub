"""Static metadata + demo seed for the AI Career section.

The demo seed is what the section returns when the user toggles "Try demo
data" - a hand-written candidate / job / match triple so the entire flow
(Setup -> Match -> Documents -> History) can be explored without any AI
call. Real runs replace these with structured outputs from the pipeline.
"""

from __future__ import annotations

import flet as ft


SECTION_ICON = ft.Icons.WORK_OUTLINE


DEMO_RESUME_TEXT = """\
Jan Novák
jan.novak@email.cz | +420 777 123 456 | Praha
github.com/jannovak

Profile
Frontend developer with 4 years of experience building React + TypeScript
applications. Worked across e-commerce, fintech and internal tooling teams.

Experience
Frontend Developer - Acme Retail (08/2022 - present)
- Led the migration of the legacy AngularJS storefront to Next.js, cutting
  Time to Interactive by 38%.
- Co-owned the design system; shipped 24 reusable React components used
  by 6 product squads.
- Mentored two junior developers through their first quarter.

Junior Frontend Developer - StartHub s.r.o. (06/2020 - 07/2022)
- Built the customer dashboard in React + TypeScript for a fintech B2B
  product (4000 daily active users).
- Set up the CI pipeline (GitHub Actions, Cypress) used by 5 frontend
  engineers.

Education
Bachelor of Computer Science, Czech Technical University in Prague
(2017 - 2020)

Languages
Czech (native speaker), English (advanced - C1)

Skills
React, TypeScript, Next.js, Redux Toolkit, Cypress, Jest, GitHub Actions
"""


DEMO_JOB_TEXT = """\
Senior Frontend Engineer (React / TypeScript) - QualityWorks Praha

We are hiring a Senior Frontend Engineer to join our platform team in
Prague. You will own the customer dashboard, mentor a small frontend
guild, and partner with the design system team.

Must have:
- 5+ years of professional experience with React and TypeScript
- Strong understanding of state management (Redux, Zustand or similar)
- Hands-on experience with Next.js
- Experience leading or mentoring at least one engineer
- Good written and spoken English (B2 minimum)

Nice to have:
- Experience with design systems
- Familiarity with Cypress and end-to-end testing
- Czech language

Tools: React, TypeScript, Next.js, Redux Toolkit, Cypress, GitHub Actions,
Storybook, Figma.

Compensation: 95 000 - 130 000 CZK gross / month based on experience.
"""


def demo_candidate(lang: str) -> dict:
    if lang == "cs":
        return {
            "full_name": "Jan Novák",
            "contact": {
                "email": "jan.novak@email.cz",
                "phone": "+420 777 123 456",
                "location": "Praha",
            },
            "summary": (
                "Frontend developer s 4 lety praxe ve výstavbě aplikací v Reactu "
                "a TypeScriptu. Cíl: pozice Senior Frontend Engineer v platformovém týmu."
            ),
            "technical_skills": [
                "React",
                "TypeScript",
                "Next.js",
                "Redux Toolkit",
                "Cypress",
                "Jest",
                "GitHub Actions",
            ],
            "experiences": [
                {
                    "role": "Frontend Developer",
                    "company": "Acme Retail",
                    "period": "08/2022 - dosud",
                    "employment_type": "",
                    "location": "Praha",
                    "bullets": [
                        "Vedl migraci legacy AngularJS obchodu na Next.js; Time to Interactive klesl o 38 %.",
                        "Spoluvlastnil design systém - dodal 24 znovupoužitelných React komponent pro 6 produktových týmů.",
                        "Mentoroval dva juniorní vývojáře v jejich prvním kvartálu.",
                    ],
                },
                {
                    "role": "Junior Frontend Developer",
                    "company": "StartHub s.r.o.",
                    "period": "06/2020 - 07/2022",
                    "employment_type": "",
                    "location": "Praha",
                    "bullets": [
                        "Postavil zákaznický dashboard v Reactu + TypeScriptu pro fintech B2B produkt (4 000 DAU).",
                        "Nastavil CI pipeline (GitHub Actions, Cypress), kterou používá 5 frontend inženýrů.",
                    ],
                },
            ],
            "education": [
                {
                    "institution": "České vysoké učení technické v Praze",
                    "degree": "Bakalář, Informatika",
                    "period": "2017 - 2020",
                    "details": "",
                }
            ],
            "certifications": [],
            "languages": [
                {"name": "Čeština", "cefr": "C2"},
                {"name": "Angličtina", "cefr": "C1"},
            ],
            "projects": [],
            "linkedin_present": False,
            "github_present": True,
        }
    return {
        "full_name": "Jan Novák",
        "contact": {
            "email": "jan.novak@email.cz",
            "phone": "+420 777 123 456",
            "location": "Prague",
        },
        "summary": (
            "Frontend developer with 4 years of experience building React + "
            "TypeScript applications. Targeting a Senior Frontend Engineer role "
            "on a platform team."
        ),
        "technical_skills": [
            "React",
            "TypeScript",
            "Next.js",
            "Redux Toolkit",
            "Cypress",
            "Jest",
            "GitHub Actions",
        ],
        "experiences": [
            {
                "role": "Frontend Developer",
                "company": "Acme Retail",
                "period": "08/2022 - present",
                "employment_type": "",
                "location": "Prague",
                "bullets": [
                    "Led the migration of the legacy AngularJS storefront to Next.js, cutting Time to Interactive by 38%.",
                    "Co-owned the design system; shipped 24 reusable React components used by 6 product squads.",
                    "Mentored two junior developers through their first quarter.",
                ],
            },
            {
                "role": "Junior Frontend Developer",
                "company": "StartHub s.r.o.",
                "period": "06/2020 - 07/2022",
                "employment_type": "",
                "location": "Prague",
                "bullets": [
                    "Built the customer dashboard in React + TypeScript for a fintech B2B product (4000 daily active users).",
                    "Set up the CI pipeline (GitHub Actions, Cypress) used by 5 frontend engineers.",
                ],
            },
        ],
        "education": [
            {
                "institution": "Czech Technical University in Prague",
                "degree": "Bachelor of Computer Science",
                "period": "2017 - 2020",
                "details": "",
            }
        ],
        "certifications": [],
        "languages": [
            {"name": "Czech", "cefr": "C2"},
            {"name": "English", "cefr": "C1"},
        ],
        "projects": [],
        "linkedin_present": False,
        "github_present": True,
    }


def demo_job_spec(lang: str) -> dict:
    if lang == "cs":
        return {
            "title": "Senior Frontend Engineer (React / TypeScript)",
            "company": "QualityWorks",
            "location": "Praha",
            "seniority": "senior",
            "employment_type": "Plný úvazek",
            "summary": "Senior frontend pozice v platformovém týmu - vlastnictví zákaznického dashboardu a design systému.",
            "must_have": [
                "5+ let praxe s Reactem a TypeScriptem",
                "Silná znalost state managementu (Redux, Zustand)",
                "Praktická zkušenost s Next.js",
                "Mentoring alespoň jednoho inženýra",
                "Angličtina min. B2",
            ],
            "nice_to_have": [
                "Zkušenost s design systémem",
                "Cypress a end-to-end testy",
                "Čeština",
            ],
            "tools": ["React", "TypeScript", "Next.js", "Redux Toolkit", "Cypress", "GitHub Actions", "Storybook", "Figma"],
            "soft_skills": ["Mentoring", "Spolupráce s designery", "Komunikace v angličtině"],
            "ats_keywords": [
                "React",
                "TypeScript",
                "Next.js",
                "Redux Toolkit",
                "Cypress",
                "GitHub Actions",
                "Storybook",
                "Figma",
                "design system",
                "mentoring",
            ],
            "compensation": "95 000 - 130 000 Kč hrubého / měsíc",
        }
    return {
        "title": "Senior Frontend Engineer (React / TypeScript)",
        "company": "QualityWorks",
        "location": "Prague",
        "seniority": "senior",
        "employment_type": "Full-time",
        "summary": "Senior frontend role on the platform team - owns the customer dashboard and the design system collaboration.",
        "must_have": [
            "5+ years of professional experience with React and TypeScript",
            "Strong understanding of state management (Redux, Zustand)",
            "Hands-on experience with Next.js",
            "Mentoring at least one engineer",
            "Good written and spoken English (B2 minimum)",
        ],
        "nice_to_have": [
            "Experience with design systems",
            "Familiarity with Cypress and end-to-end testing",
            "Czech language",
        ],
        "tools": ["React", "TypeScript", "Next.js", "Redux Toolkit", "Cypress", "GitHub Actions", "Storybook", "Figma"],
        "soft_skills": ["Mentoring", "Design collaboration", "Communication in English"],
        "ats_keywords": [
            "React",
            "TypeScript",
            "Next.js",
            "Redux Toolkit",
            "Cypress",
            "GitHub Actions",
            "Storybook",
            "Figma",
            "design system",
            "mentoring",
        ],
        "compensation": "95 000 - 130 000 CZK gross / month",
    }


def demo_match(lang: str) -> dict:
    if lang == "cs":
        return {
            "overall_score": 72,
            "verdict": "Dobrá shoda - kandidát má 4/5 musí-mít, chybí Storybook a žádné Figma stopy.",
            "categories": [
                {
                    "name": "Technické dovednosti",
                    "score": 84,
                    "evidence": ["React + TypeScript napříč oběma rolemi", "Next.js v Acme migraci"],
                },
                {
                    "name": "Praxe",
                    "score": 65,
                    "evidence": ["4 roky praxe vs. 5+ roků v JD"],
                },
                {
                    "name": "Nástroje",
                    "score": 70,
                    "evidence": ["Cypress + GitHub Actions ano, Storybook neuvedeno"],
                },
                {
                    "name": "Mentoring & soft skills",
                    "score": 80,
                    "evidence": ["Mentoroval dva juniory", "Spolupráce s 6 produktovými týmy"],
                },
            ],
            "matches": [
                "React, TypeScript, Next.js a Redux Toolkit jsou potvrzené",
                "Cypress a GitHub Actions jsou v aktuální roli",
                "Mentoring juniorů je doložený",
            ],
            "gaps": [
                "5+ let praxe není splněno - kandidát má 4 roky",
                "Storybook a Figma se v životopise nikde neobjevují",
            ],
            "ats_keywords_present": [
                "React",
                "TypeScript",
                "Next.js",
                "Redux Toolkit",
                "Cypress",
                "GitHub Actions",
                "mentoring",
            ],
            "ats_keywords_missing": ["Storybook", "Figma", "design system"],
            "evidence_preview": [
                "Migrace AngularJS -> Next.js, TTI -38 %",
                "24 znovupoužitelných React komponent",
                "Mentoring dvou juniorů",
                "CI pipeline pro 5 inženýrů",
            ],
            "interview_questions": [
                "Jak byste navrhl postupné nahrazení komponent v existujícím design systému?",
                "Popište migraci z AngularJS na Next.js, kterou jste vedl. Co byste udělal jinak?",
                "Jak měříte úspěch mentoringu juniorního vývojáře?",
                "Kdy zvolíte Redux Toolkit a kdy Zustand?",
                "Jak píšete end-to-end testy v Cypressu, aby nebyly flaky?",
                "Co pro vás znamená dobrý design systém?",
            ],
            "skill_gap_plan": [
                {
                    "skill": "Storybook",
                    "action": "Projít oficiální Intro to Storybook tutorial a nasadit Storybook na 5 komponent ze svého boku design systému.",
                    "timeline_weeks": 3,
                },
                {
                    "skill": "Figma collaboration",
                    "action": "Domluvit shadow session s designérem v Acme; vyzkoušet auto-layout a tokens import.",
                    "timeline_weeks": 2,
                },
                {
                    "skill": "Praxe (5+ let)",
                    "action": "Doplnit profil o open-source contributions k Next.js / Redux Toolkit; zviditelnit 4 roky praxe + týmovou velikost odpovědnosti.",
                    "timeline_weeks": 6,
                },
            ],
        }
    return {
        "overall_score": 72,
        "verdict": "Strong fit - 4 out of 5 must-haves, missing Storybook and no Figma evidence.",
        "categories": [
            {
                "name": "Technical skills",
                "score": 84,
                "evidence": ["React + TypeScript across both roles", "Next.js in the Acme migration"],
            },
            {"name": "Experience", "score": 65, "evidence": ["4 years vs. 5+ years required"]},
            {
                "name": "Tools",
                "score": 70,
                "evidence": ["Cypress + GitHub Actions yes, Storybook missing"],
            },
            {
                "name": "Mentoring & soft skills",
                "score": 80,
                "evidence": ["Mentored two junior developers", "Worked with 6 product squads"],
            },
        ],
        "matches": [
            "React, TypeScript, Next.js and Redux Toolkit are evidenced",
            "Cypress and GitHub Actions used in the current role",
            "Mentoring juniors is documented",
        ],
        "gaps": [
            "5+ years of experience not yet met (candidate has 4)",
            "Storybook and Figma do not appear anywhere in the resume",
        ],
        "ats_keywords_present": [
            "React",
            "TypeScript",
            "Next.js",
            "Redux Toolkit",
            "Cypress",
            "GitHub Actions",
            "mentoring",
        ],
        "ats_keywords_missing": ["Storybook", "Figma", "design system"],
        "evidence_preview": [
            "AngularJS -> Next.js migration, TTI -38%",
            "24 reusable React components",
            "Mentored two junior developers",
            "CI pipeline used by 5 engineers",
        ],
        "interview_questions": [
            "How would you sequence component replacement in an existing design system?",
            "Walk me through the AngularJS -> Next.js migration you led. What would you do differently?",
            "How do you measure mentoring impact for a junior developer?",
            "When do you reach for Redux Toolkit vs. Zustand?",
            "How do you keep Cypress end-to-end tests from getting flaky?",
            "What does a good design system look like to you?",
        ],
        "skill_gap_plan": [
            {
                "skill": "Storybook",
                "action": "Finish the official Intro to Storybook tutorial and add Storybook to 5 components in your design-system slice.",
                "timeline_weeks": 3,
            },
            {
                "skill": "Figma collaboration",
                "action": "Schedule a shadow session with a designer at Acme and try auto-layout and token import.",
                "timeline_weeks": 2,
            },
            {
                "skill": "Years of experience (5+)",
                "action": "Add open-source contributions to Next.js / Redux Toolkit; reframe your 4 years to highlight scope and team size.",
                "timeline_weeks": 6,
            },
        ],
    }


DEMO_DOCUMENTS = {
    "tailored_cv": "_demo_tailored_cv",
    "modern_cv": "_demo_modern_cv",
    "cover_letter": "_demo_cover_letter",
    "match_report": "_demo_match_report",
    "interview_prep": "_demo_interview_prep",
    "skill_gap": "_demo_skill_gap",
}
