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
                {
                    "question": "Jak byste navrhl postupné nahrazení komponent v existujícím design systému?",
                    "why_asked": "Pozice explicitně zahrnuje vlastnictví části design systému; chtějí ověřit, že umíte zavádět změny inkrementálně bez breaking changes pro 6 produktových týmů.",
                    "suggested_answer": "Začal bych mapou závislostí (Situation: 24 komponent, 6 týmů). Cíl: vyměnit 1 komponentu týdně s pojistkou (Task). Akce: přidat novou komponentu s feature flagem, pokrýt Storybookem a vizuálním regression testem, párovat s vlastníkem každého týmu na migrační PR (Action). Výsledek v Acme: nahradili jsme 8 komponent za kvartál bez výpadku v produkci a bez paralelní udržby (Result).",
                },
                {
                    "question": "Popište migraci z AngularJS na Next.js, kterou jste vedl. Co byste udělal jinak?",
                    "why_asked": "Hlavní headline příběh - chtějí vědět, jestli za hlavičkou stojí reálné rozhodování a metriky.",
                    "suggested_answer": "Situation: 9 let starý AngularJS storefront, TTI 4.2 s. Task: snížit TTI a uvolnit tým z legacy údržby. Action: micro-frontend architektura (Module Federation), shadow rollout na 5 % uživatelů, server components pro produktové stránky. Result: TTI -38 % na hlavní stránce, bundle size -50 %. Co bych udělal jinak: dříve nasadil Lighthouse CI - první 2 sprinty nám utíkaly regrese, které jsme objevili až ve staging.",
                },
                {
                    "question": "Jak měříte úspěch mentoringu juniorního vývojáře?",
                    "why_asked": "Senior role v platformovém týmu zahrnuje růst dvou juniorů - hledají strukturovaný přístup, ne intuici.",
                    "suggested_answer": "Mentoroval jsem dva juniory přes první kvartál v Acme (Situation/Task). Action: týdenní 1:1 s jasnými cíli, code-review pairing 2x týdně, vlastnictví malé komponenty od PR po release. Měřil jsem time-to-first-merged-PR (cíl <2 týdny), pokrytí review komentářů (klesá do 4. týdne), a feedback od techleadů produktových týmů. Result: oba juniori se po 12 týdnech stali samostatnými vlastníky komponent v design systému (Result).",
                },
                {
                    "question": "Kdy zvolíte Redux Toolkit a kdy Zustand?",
                    "why_asked": "Praktická architektonická otázka - chtějí vědět, jestli sáhnete po Reduxu reflexivně, nebo umíte odhadnout cenu komplexity.",
                    "suggested_answer": "Redux Toolkit volím tam, kde chci striktní auditovatelnost mutací (formulář s 12+ kroky, finanční tok) - RTK Query jsem nasadil v Acme pro 30+ endpointů a hodilo se jednotné cache + invalidace. Zustand sahám pro lokální UI state, kde nepotřebuji middleware ani devtools - např. modal stack v dashboardu. Klíčové kritérium: kolik dat sdílí 3+ vzdálené komponenty? Pod tu hranici jde kontext nebo Zustand.",
                },
                {
                    "question": "Jak píšete end-to-end testy v Cypressu, aby nebyly flaky?",
                    "why_asked": "QualityWorks má v JD Cypress jako must-have - chtějí ověřit, že máte zkušenost s běžnou bolestí (flaky tests), ne jen happy path.",
                    "suggested_answer": "V StartHubu jsme měli 12 % flaky rate, dostali jsme to pod 1 % (Result). Action: 1) zakázal cy.wait s pevnými millis, nahradil cy.intercept + cy.wait('@alias'), 2) data setup přes API/factory místo UI flow (zrychlilo to suite o 40 %), 3) každý test začíná čistým seedem databáze přes Cypress task, 4) screenshoty při failure + retries=2 jen v CI, ne lokálně. Klíč: flaky test = chyba v testu nebo v aplikaci, nikdy 'jen znova'.",
                },
                {
                    "question": "Co pro vás znamená dobrý design systém?",
                    "why_asked": "Otevřená otázka - chtějí vidět, jestli máte vlastní názor a odlišujete tokens / komponenty / patterns.",
                    "suggested_answer": "Dobrý design systém má tři vrstvy: tokens (barvy, spacing, type scale), primitives (Button, Input - bezstátní, accessible) a patterns (FormField, DataTable - composable). Měřím ho podle adopční křivky: kolik produktových týmů migrovalo jakou vrstvu a za jak dlouho. V Acme dnes 6 týmů používá tokens + primitives, na patterns míří první 2 - to je zdravý poměr. Špatný design systém je ten, kde každý tým vlastní svou kopii Buttonu, protože jim ta sdílená neseděla.",
                },
            ],
            "skill_gap_plan": [
                {
                    "skill": "Storybook",
                    "action": "Projít oficiální Intro to Storybook tutorial a nasadit Storybook na 5 komponent ze svého boku design systému.",
                    "timeline_weeks": 3,
                    "criticality": "critical",
                    "why_it_matters": "QualityWorks v JD označuje Storybook jako must-have a aktivně přes něj migruje design tokens. Bez něj odpadnete v technickém kole.",
                    "learning_path": [
                        "Dokončit oficiální Storybook 8 'Intro to Storybook' tutorial v Reactu.",
                        "Přidat Storybook konfiguraci do svého open-source repozitáře 'react-design-bits'.",
                        "Napsat stories pro 5 komponent: Button, Input, Modal, Toast, FormField (controls + actions + a11y addon).",
                        "Nasadit static build na GitHub Pages a propojit z README.",
                        "Napsat krátký blog post / LinkedIn post 'Migrating a 24-component design system to Storybook' s odkazy.",
                    ],
                    "suggested_project": "Veřejný GitHub repo 'react-design-bits' s 5 komponentami pokrytými Storybook 8, GitHub Pages deploy, README s gif demo a krátkým blog postem o procesu.",
                },
                {
                    "skill": "Figma collaboration",
                    "action": "Domluvit shadow session s designérem v Acme; vyzkoušet auto-layout a tokens import.",
                    "timeline_weeks": 2,
                    "criticality": "important",
                    "why_it_matters": "Most mezi designem a engineeringem je v JD QualityWorks zmíněn dvakrát. Bez praktické zkušenosti budete znít teoreticky.",
                    "learning_path": [
                        "Domluvit 60min shadow session s designérem v Acme tento týden.",
                        "Projít Figma 'Auto-layout fundamentals' kurz (oficiální, ~90 min).",
                        "Replikovat 1 komponentu z Storybook repa v Figmě s auto-layoutem a variants.",
                        "Vyzkoušet Tokens Studio plugin: exportovat tokens z Figmy do JSONu a importovat do Storybooku.",
                    ],
                    "suggested_project": "Jeden Figma soubor (může být malý) co-editovaný s designérem - 1 komponenta s auto-layoutem + variants + design tokens propojené přes Tokens Studio do Storybook repa.",
                },
                {
                    "skill": "Praxe (5+ let)",
                    "action": "Doplnit profil o open-source contributions k Next.js / Redux Toolkit; zviditelnit 4 roky praxe + týmovou velikost odpovědnosti.",
                    "timeline_weeks": 6,
                    "criticality": "important",
                    "why_it_matters": "JD je pevný na 5+ let. Viditelný open-source impact + šíře odpovědnosti (24 komponent, 6 týmů, 2 juniori) headline číslo nahrazuje, ale bez toho recruiter většinou neoponuje.",
                    "learning_path": [
                        "Označit 3 dobré first-issue tickety v Next.js / Redux Toolkit / TanStack Query.",
                        "Mergnout 1 PR (typo / docs / malý bug) jako warm-up.",
                        "Vybrat 1 reálný feature ticket (typicky labeled 'help wanted') a mergnout PR do 4 týdnů.",
                        "Aktualizovat LinkedIn 'Open to' + headline na 'Senior Frontend Engineer · React + TypeScript · 4y, 6 squads, design-system owner'.",
                        "Přepsat 'Acme Retail' bullet body na metriky šíře (#komponent, #týmů, #DAU), ne jen výkonu.",
                    ],
                    "suggested_project": "Dva mergnuté PRs do top-200 frontend OSS repa (např. Next.js example, Redux Toolkit docs typo + funkční fix). Linky v životopise i LinkedInu.",
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
            {
                "question": "How would you sequence component replacement in an existing design system?",
                "why_asked": "The role explicitly includes co-owning a design-system slice; they want to see that you can ship change incrementally without breaking the 6 product squads that depend on it.",
                "suggested_answer": "Situation: 24 components used by 6 squads. Task: swap legacy Buttons for the new design-token-driven version with zero breakage. Action: I'd map dependencies first, ship the new component behind a feature flag, cover it with Storybook stories + visual regression tests, and pair with each squad's tech lead on the migration PR. Result at Acme: we replaced 8 components in a quarter with no production incident and no parallel maintenance.",
            },
            {
                "question": "Walk me through the AngularJS -> Next.js migration you led. What would you do differently?",
                "why_asked": "This is your headline story - they want to know there is real decision-making and metrics behind the bullet point.",
                "suggested_answer": "Situation: 9-year-old AngularJS storefront, TTI 4.2s. Task: cut TTI and free the team from legacy maintenance. Action: micro-frontend architecture (Module Federation), shadow rollout to 5% of traffic, server components for product pages. Result: TTI -38% on the homepage, bundle size -50%. What I'd do differently: stand up Lighthouse CI on day one - the first two sprints leaked regressions we caught only at staging.",
            },
            {
                "question": "How do you measure mentoring impact for a junior developer?",
                "why_asked": "A senior platform role at QualityWorks includes growing two juniors - they want a structured approach, not a feel-good answer.",
                "suggested_answer": "I mentored two juniors through their first quarter at Acme. Action: weekly 1:1 with explicit goals, code-review pairing twice a week, ownership of one small component from PR to release. Metrics I tracked: time-to-first-merged-PR (target <2 weeks), review-comment density (it falls by week 4), and feedback from product squad tech leads. Result: by week 12 both juniors owned a component in the design system without code-review hand-holding.",
            },
            {
                "question": "When do you reach for Redux Toolkit vs. Zustand?",
                "why_asked": "Practical architecture probe - they want to know whether you reach for Redux reflexively or can weigh complexity.",
                "suggested_answer": "I pick Redux Toolkit when I need strict, auditable mutations - a 12-step form, a finance flow - and RTK Query when 30+ endpoints share cache + invalidation rules (which is what we shipped at Acme). I reach for Zustand on local UI state where I don't need middleware or devtools - modal stack, side-panel toggles. Heuristic: how many distant components actually share this data? Below three, context or Zustand is enough.",
            },
            {
                "question": "How do you keep Cypress end-to-end tests from getting flaky?",
                "why_asked": "QualityWorks lists Cypress as a must-have - they want to know you've fought the common pain (flaky tests), not just the happy path.",
                "suggested_answer": "At StartHub our flaky rate was 12%; we got it under 1%. Actions: 1) banned cy.wait with hard-coded ms, replaced with cy.intercept + cy.wait('@alias'), 2) data setup via API factories instead of UI flow (40% faster suite), 3) each test starts with a fresh DB seed via a Cypress task, 4) screenshot on failure + retries=2 in CI only, never local. Mindset: a flaky test is a bug in the test or in the app - never 'just rerun'.",
            },
            {
                "question": "What does a good design system look like to you?",
                "why_asked": "Open-ended probe - they want to see if you have a personal opinion and can distinguish tokens / primitives / patterns.",
                "suggested_answer": "Three layers: tokens (colour, spacing, type scale), primitives (Button, Input - stateless, accessible), and patterns (FormField, DataTable - composable). I measure it by adoption: how many product squads consumed which layer and how fast. At Acme today 6 squads use tokens + primitives, the first 2 are starting on patterns - that's a healthy ramp. A bad design system is one where every squad ships its own Button because the shared one didn't fit.",
            },
        ],
        "skill_gap_plan": [
            {
                "skill": "Storybook",
                "action": "Finish the official Intro to Storybook tutorial and add Storybook to 5 components in your design-system slice.",
                "timeline_weeks": 3,
                "criticality": "critical",
                "why_it_matters": "QualityWorks lists Storybook as a must-have in the JD and is actively migrating tokens through it. Without it you risk being filtered at the technical screen.",
                "learning_path": [
                    "Finish the official Storybook 8 'Intro to Storybook' tutorial in React.",
                    "Add Storybook config to your open-source repo 'react-design-bits'.",
                    "Write stories for 5 components: Button, Input, Modal, Toast, FormField (controls + actions + a11y addon).",
                    "Deploy the static build to GitHub Pages and link it in the repo README.",
                    "Publish a short blog / LinkedIn post 'Migrating a 24-component design system to Storybook' linking the demo.",
                ],
                "suggested_project": "Public GitHub repo 'react-design-bits' with 5 components covered by Storybook 8, GitHub Pages deploy, README with a gif demo and a short blog post about the process.",
            },
            {
                "skill": "Figma collaboration",
                "action": "Schedule a shadow session with a designer at Acme and try auto-layout and token import.",
                "timeline_weeks": 2,
                "criticality": "important",
                "why_it_matters": "Bridging design and engineering shows up twice in the QualityWorks JD. Without practical experience your answers will sound theoretical.",
                "learning_path": [
                    "Book a 60-minute shadow session with a designer at Acme this week.",
                    "Walk through Figma's 'Auto-layout fundamentals' (~90 min, official).",
                    "Recreate one component from your Storybook repo in Figma with auto-layout + variants.",
                    "Try the Tokens Studio plugin: export tokens from Figma to JSON and import them into Storybook.",
                ],
                "suggested_project": "One Figma file (small is fine) co-edited with a designer - one component with auto-layout + variants + design tokens piped through Tokens Studio into the Storybook repo.",
            },
            {
                "skill": "Years of experience (5+)",
                "action": "Add open-source contributions to Next.js / Redux Toolkit; reframe your 4 years to highlight scope and team size.",
                "timeline_weeks": 6,
                "criticality": "important",
                "why_it_matters": "The JD is firm on 5+ years. Visible open-source impact plus scope (24 components, 6 squads, 2 juniors) offsets the headline number, but without it recruiters seldom argue your case.",
                "learning_path": [
                    "Tag 3 good first-issue tickets across Next.js / Redux Toolkit / TanStack Query.",
                    "Merge 1 small PR (typo / docs / minor bug) as a warm-up.",
                    "Pick one real feature ticket (labelled 'help wanted') and merge a PR within 4 weeks.",
                    "Update LinkedIn 'Open to' + headline to 'Senior Frontend Engineer · React + TypeScript · 4y, 6 squads, design-system owner'.",
                    "Rewrite the Acme Retail bullets to lead with scope metrics (#components, #squads, #DAU), not just performance numbers.",
                ],
                "suggested_project": "Two merged PRs into a top-200 frontend OSS repo (e.g. a Next.js example + a Redux Toolkit docs typo + functional fix). Link them from your CV and LinkedIn.",
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


def demo_modern_cv(lang: str) -> dict:
    """Hand-curated Modern CV payload that drives the fancy two-column view."""
    if lang == "cs":
        return {
            "full_name": "Jan Novák",
            "role_headline": "Senior Frontend Engineer",
            "role_subtitle": "React + TypeScript · platformový tým",
            "contact": {
                "location": "Praha, Česko",
                "email": "jan.novak@email.cz",
                "phone": "+420 777 123 456",
            },
            "online_links": [
                {"icon": "gh", "label": "github.com/jannovak", "url": "https://github.com/jannovak"},
            ],
            "skill_groups": [
                {"label": "Frontend core", "tags": ["React", "TypeScript", "Next.js", "Redux Toolkit"]},
                {"label": "Quality", "tags": ["Cypress", "Jest"]},
                {"label": "Tooling & CI", "tags": ["GitHub Actions"]},
                {"label": "Design system", "tags": ["Component design", "Tokens"]},
                {"label": "Spolupráce", "tags": ["Mentoring", "Code review", "Spolupráce s designery"]},
            ],
            "languages": [
                {"name": "Čeština", "level": "C2"},
                {"name": "Angličtina", "level": "C1"},
            ],
            "profile_summary": (
                "**Frontend developer se 4 lety praxe** v Reactu a TypeScriptu. "
                "Cílí na pozici **Senior Frontend Engineer** v platformovém týmu. "
                "Vedl **migraci AngularJS storefrontu na Next.js** v Acme Retail "
                "se snížením **Time to Interactive o 38 %**. Spoluvlastní část design "
                "systému - dodal **24 znovupoužitelných React komponent** používaných "
                "**6 produktovými týmy**. Mentoroval **dva juniorní vývojáře** v jejich "
                "prvním kvartálu."
            ),
            "leadership_highlights": [
                "**Vedl migraci** legacy AngularJS storefrontu na **Next.js** (TTI -38 %)",
                "**Spoluvlastník** 24 komponent design systému pro **6 produktových týmů**",
                "**Mentoring** dvou juniorních vývojářů během prvního kvartálu",
                "Nastavil **CI pipeline (GitHub Actions + Cypress)** pro 5 inženýrů",
            ],
            "experience": [
                {
                    "role": "Frontend Developer",
                    "period": "08/2022 - dosud",
                    "company": "Acme Retail",
                    "context": "· Praha",
                    "highlight_pills": ["Next.js migrace", "Design systém", "Mentoring"],
                    "bullets": [
                        "**Vedl migraci legacy AngularJS storefrontu** na **Next.js**; **Time to Interactive klesl o 38 %**.",
                        "**Spoluvlastnil design systém** - dodal **24 znovupoužitelných React komponent** používaných **6 produktovými týmy**.",
                        "**Mentoroval dva juniorní vývojáře** v jejich prvním kvartálu - týdenní 1:1 a párové review.",
                    ],
                },
                {
                    "role": "Junior Frontend Developer",
                    "period": "06/2020 - 07/2022",
                    "company": "StartHub s.r.o.",
                    "context": "· Praha · Fintech B2B",
                    "highlight_pills": ["React + TypeScript", "CI/CD"],
                    "bullets": [
                        "Postavil **zákaznický dashboard** v **Reactu + TypeScriptu** pro fintech B2B produkt (**4 000 DAU**).",
                        "Nastavil **CI pipeline (GitHub Actions, Cypress)**, kterou používá **5 frontend inženýrů**.",
                    ],
                },
            ],
            "projects": [],
            "education": [
                {
                    "title": "Bakalář, Informatika",
                    "sub": "České vysoké učení technické v Praze",
                    "period": "2017 - 2020",
                },
            ],
            "certifications": [],
        }
    return {
        "full_name": "Jan Novák",
        "role_headline": "Senior Frontend Engineer",
        "role_subtitle": "React + TypeScript · platform work",
        "contact": {
            "location": "Prague, Czech Republic",
            "email": "jan.novak@email.cz",
            "phone": "+420 777 123 456",
        },
        "online_links": [
            {"icon": "gh", "label": "github.com/jannovak", "url": "https://github.com/jannovak"},
        ],
        "skill_groups": [
            {"label": "Frontend core", "tags": ["React", "TypeScript", "Next.js", "Redux Toolkit"]},
            {"label": "Quality", "tags": ["Cypress", "Jest"]},
            {"label": "Tooling & CI", "tags": ["GitHub Actions"]},
            {"label": "Design system", "tags": ["Component design", "Tokens"]},
            {"label": "Collaboration", "tags": ["Mentoring", "Code review", "Designer pairing"]},
        ],
        "languages": [
            {"name": "Czech", "level": "C2"},
            {"name": "English", "level": "C1"},
        ],
        "profile_summary": (
            "**Frontend developer with 4 years of experience** in React and "
            "TypeScript, targeting a **Senior Frontend Engineer** role on a "
            "platform team. Led the **AngularJS-to-Next.js migration** at Acme "
            "Retail with a **38% Time to Interactive cut**. Co-owns the design "
            "system slice - shipped **24 reusable React components** used across "
            "**6 product squads**. Mentored **two junior developers** through "
            "their first quarter."
        ),
        "leadership_highlights": [
            "**Led the AngularJS to Next.js migration** (Time to Interactive -38%)",
            "**Co-owner** of 24 design-system components used by **6 product squads**",
            "**Mentored** two junior developers through their first quarter",
            "Set up the **CI pipeline (GitHub Actions + Cypress)** for 5 engineers",
        ],
        "experience": [
            {
                "role": "Frontend Developer",
                "period": "08/2022 - present",
                "company": "Acme Retail",
                "context": "· Prague",
                "highlight_pills": ["Next.js migration", "Design system", "Mentoring"],
                "bullets": [
                    "**Led the migration of the legacy AngularJS storefront** to **Next.js**, cutting **Time to Interactive by 38%**.",
                    "**Co-owned the design system slice** - shipped **24 reusable React components** used by **6 product squads**.",
                    "**Mentored two junior developers** through their first quarter (weekly 1:1, code-review pairing).",
                ],
            },
            {
                "role": "Junior Frontend Developer",
                "period": "06/2020 - 07/2022",
                "company": "StartHub s.r.o.",
                "context": "· Prague · Fintech B2B",
                "highlight_pills": ["React + TypeScript", "CI/CD"],
                "bullets": [
                    "Built the **customer dashboard** in **React + TypeScript** for a fintech B2B product (**4,000 DAU**).",
                    "Set up the **CI pipeline (GitHub Actions, Cypress)** used by **5 frontend engineers**.",
                ],
            },
        ],
        "projects": [],
        "education": [
            {
                "title": "Bachelor of Computer Science",
                "sub": "Czech Technical University in Prague",
                "period": "2017 - 2020",
            },
        ],
        "certifications": [],
    }
