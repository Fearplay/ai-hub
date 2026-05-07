"""Orchestration for the AI Career section.

Three structured-output calls drive the bulk of the analysis:

1. ``extract_candidate`` - resume text (+ optional LinkedIn / GitHub)
   -> :class:`Candidate JSON <src.sections.ai_career.schema.CANDIDATE_SCHEMA>`.
2. ``extract_job_spec`` - scraped or pasted job text -> ``JobSpec JSON``.
3. ``analyze_match`` - candidate + job spec -> ``MatchAnalysis JSON``
   including interview questions and a skill-gap plan.

Each per-document generator (Tailored CV, Cover Letter, …) is a small
follow-up call whose only input is the three structured JSONs - we never
re-send raw resume text after step 1, which is the main cost saver.

In Demo mode the pipeline returns curated mock data without calling any
provider, so the entire UI flow can be explored offline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from src.services import ai_provider, github_client, job_scraper
from src.sections.ai_career import data as career_data
from src.sections.ai_career import prompts, schema
from src.sections.ai_career.refs import REFS, safe
from src.sections.ai_career.state import (
    DOC_COVER_LETTER,
    DOC_INTERVIEW_PREP,
    DOC_MATCH_REPORT,
    DOC_MODERN_CV,
    DOC_SKILL_GAP,
    DOC_TAILORED_CV,
    STATE,
    UploadedFile,
)


# Public types ----------------------------------------------------------------


@dataclass
class PipelineResult:
    ok: bool
    error: str = ""


def _set_activity(value: str) -> None:
    STATE.activity = value
    safe(REFS.rerender_context)


def _set_error(message: str) -> PipelineResult:
    STATE.activity = "error"
    STATE.last_error = message
    safe(REFS.rerender_context)
    return PipelineResult(ok=False, error=message)


# Step 0: input gathering -----------------------------------------------------


def fetch_job_text(url: str) -> tuple[str, str]:
    """Returns (text, error_message). Empty error means success."""
    if not url.strip():
        return "", "URL is empty."
    _set_activity("scraping")
    result = job_scraper.scrape_job_posting(url)
    if not result.ok:
        return result.text, result.error or "Unknown scraping error."
    return result.text, ""


def fetch_github_profile(value: str):
    if not value.strip():
        return None
    _set_activity("scraping")
    return github_client.fetch_profile(value)


# Step 1: candidate extraction ------------------------------------------------


def _build_github_summary() -> str:
    if STATE.github_skip:
        return ""
    return prompts.serialize_github_summary(STATE.github_profile)


def extract_candidate(
    *,
    output_lang: str,
    target_role: str = "",
) -> PipelineResult:
    if STATE.demo_mode:
        STATE.candidate = career_data.demo_candidate(output_lang)
        return PipelineResult(ok=True)

    if not STATE.resume or not STATE.resume.text:
        return _set_error("Resume is missing.")

    _set_activity("analyzing")
    user = prompts.build_candidate_user(
        output_lang=output_lang,
        target_role=target_role or STATE.target_role,
        resume_text=STATE.resume.text,
        linkedin_text=(STATE.linkedin.text if STATE.linkedin else ""),
        github_summary=_build_github_summary(),
    )
    try:
        result = ai_provider.run(
            system=prompts.CANDIDATE_EXTRACTION_SYSTEM,
            user=user,
            schema=schema.CANDIDATE_SCHEMA,
            schema_name="candidate",
            max_output_tokens=3500,
        )
    except ai_provider.ProviderError as exc:
        return _set_error(str(exc))

    if not isinstance(result.data, dict):
        return _set_error("Provider did not return a Candidate JSON.")
    STATE.candidate = result.data
    STATE.candidate["linkedin_present"] = bool(STATE.linkedin and STATE.linkedin.text)
    STATE.candidate["github_present"] = bool(STATE.github_profile and STATE.github_profile.ok)
    return PipelineResult(ok=True)


# Step 2: job spec extraction -------------------------------------------------


def extract_job_spec(*, output_lang: str) -> PipelineResult:
    if STATE.demo_mode:
        STATE.job_spec = career_data.demo_job_spec(output_lang)
        return PipelineResult(ok=True)

    if not STATE.job_text:
        return _set_error("Job text is empty.")

    _set_activity("analyzing")
    user = prompts.build_job_spec_user(output_lang=output_lang, job_text=STATE.job_text)
    try:
        result = ai_provider.run(
            system=prompts.JOB_SPEC_EXTRACTION_SYSTEM,
            user=user,
            schema=schema.JOB_SPEC_SCHEMA,
            schema_name="job_spec",
            max_output_tokens=2000,
        )
    except ai_provider.ProviderError as exc:
        return _set_error(str(exc))
    if not isinstance(result.data, dict):
        return _set_error("Provider did not return a JobSpec JSON.")
    STATE.job_spec = result.data
    return PipelineResult(ok=True)


# Step 2.5: optional follow-up questions -------------------------------------


def generate_followup_questions(*, output_lang: str) -> PipelineResult:
    """Ask the LLM to surface gaps that the candidate should clarify.

    Stores the result in ``STATE.followup_questions``. Returns success even
    when the AI emits zero questions - that is a valid outcome and means
    the resume already covers the job description.
    """
    if STATE.demo_mode:
        STATE.followup_questions = []
        return PipelineResult(ok=True)

    if not STATE.candidate or not STATE.job_spec:
        return _set_error("Run candidate + job spec extraction first.")

    _set_activity("followups")
    user = prompts.build_followup_user(
        output_lang=output_lang,
        candidate=STATE.candidate,
        job_spec=STATE.job_spec,
    )
    try:
        result = ai_provider.run(
            system=prompts.FOLLOWUP_QUESTIONS_SYSTEM,
            user=user,
            schema=schema.FOLLOWUP_QUESTIONS_SCHEMA,
            schema_name="clarifying_questions",
            max_output_tokens=1200,
        )
    except ai_provider.ProviderError as exc:
        return _set_error(str(exc))
    if not isinstance(result.data, dict):
        return _set_error("Provider did not return a follow-up questions JSON.")
    questions = result.data.get("questions") or []
    cleaned: list[dict] = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        topic = (q.get("topic") or "").strip()
        question = (q.get("question") or "").strip()
        if not topic or not question:
            continue
        cleaned.append(
            {
                "topic": topic,
                "question": question,
                "rationale": (q.get("rationale") or "").strip(),
            }
        )
    STATE.followup_questions = cleaned
    return PipelineResult(ok=True)


# Step 3: match analysis ------------------------------------------------------


def analyze_match(*, output_lang: str) -> PipelineResult:
    if STATE.demo_mode:
        STATE.match = career_data.demo_match(output_lang)
        return PipelineResult(ok=True)

    if not STATE.candidate or not STATE.job_spec:
        return _set_error("Run candidate + job spec extraction first.")

    _set_activity("analyzing")
    user = prompts.build_match_user(
        output_lang=output_lang,
        candidate=STATE.candidate,
        job_spec=STATE.job_spec,
        followup_qa=STATE.followup_qa,
    )
    try:
        result = ai_provider.run(
            system=prompts.MATCH_ANALYSIS_SYSTEM,
            user=user,
            schema=schema.MATCH_ANALYSIS_SCHEMA,
            schema_name="match_analysis",
            max_output_tokens=3500,
        )
    except ai_provider.ProviderError as exc:
        return _set_error(str(exc))
    if not isinstance(result.data, dict):
        return _set_error("Provider did not return a MatchAnalysis JSON.")
    STATE.match = result.data
    return PipelineResult(ok=True)


# Step 4: per-document generation --------------------------------------------


_DOC_SYSTEM_BY_KIND: dict[str, str] = {
    DOC_TAILORED_CV: prompts.TAILORED_CV_SYSTEM,
    DOC_MODERN_CV: prompts.MODERN_CV_SYSTEM,
    DOC_COVER_LETTER: prompts.COVER_LETTER_SYSTEM,
    DOC_MATCH_REPORT: prompts.MATCH_REPORT_SYSTEM,
    DOC_INTERVIEW_PREP: prompts.INTERVIEW_PREP_SYSTEM,
    DOC_SKILL_GAP: prompts.SKILL_GAP_SYSTEM,
}


def generate_document(kind: str, *, output_lang: str) -> PipelineResult:
    if kind not in _DOC_SYSTEM_BY_KIND:
        return _set_error(f"Unknown document kind: {kind}")
    if STATE.demo_mode:
        STATE.documents[kind] = _demo_document(kind, output_lang)
        safe(REFS.rerender_documents)
        return PipelineResult(ok=True)

    if not (STATE.candidate and STATE.job_spec and STATE.match):
        return _set_error("Run analysis before generating documents.")

    _set_activity("generating")
    system = _DOC_SYSTEM_BY_KIND[kind]
    user = prompts.build_document_user(
        output_lang=output_lang,
        candidate=STATE.candidate,
        job_spec=STATE.job_spec,
        match=STATE.match,
    )
    try:
        result = ai_provider.run(
            system=system,
            user=user,
            schema=None,
            max_output_tokens=2400,
            temperature=0.3,
        )
    except ai_provider.ProviderError as exc:
        return _set_error(str(exc))
    text = (result.text or "").strip()
    if not text:
        return _set_error("Provider returned an empty document.")
    STATE.documents[kind] = text
    STATE.activity = "ready"
    safe(REFS.rerender_documents)
    safe(REFS.rerender_context)
    return PipelineResult(ok=True)


# Step 5: refine an existing document ----------------------------------------


def refine_document(
    kind: str,
    *,
    output_lang: str,
    problems: list[str],
) -> PipelineResult:
    if kind not in _DOC_SYSTEM_BY_KIND:
        return _set_error(f"Unknown document kind: {kind}")
    current = STATE.documents.get(kind, "")
    if not current:
        return _set_error("Generate the document before refining it.")

    if STATE.demo_mode:
        appended = "\n\n_(Demo refinement: would address the listed problems.)_"
        STATE.documents[kind] = current + appended
        safe(REFS.rerender_documents)
        return PipelineResult(ok=True)

    _set_activity("generating")
    user = prompts.build_refine_user(
        output_lang=output_lang,
        document_kind=kind,
        document_text=current,
        problems=[p for p in problems if p.strip()],
    )
    try:
        result = ai_provider.run(
            system=prompts.REFINE_SYSTEM,
            user=user,
            schema=None,
            max_output_tokens=2400,
            temperature=0.3,
        )
    except ai_provider.ProviderError as exc:
        return _set_error(str(exc))
    text = (result.text or "").strip()
    if not text:
        return _set_error("Provider returned an empty refined document.")
    STATE.documents[kind] = text
    STATE.activity = "ready"
    safe(REFS.rerender_documents)
    safe(REFS.rerender_context)
    return PipelineResult(ok=True)


# Combined "Run analysis" entry point ----------------------------------------


def run_full_analysis(
    *,
    output_lang: str,
    target_role: str = "",
    on_step: Optional[Callable[[str], None]] = None,
) -> PipelineResult:
    """Sequentially extract candidate, job spec, and match analysis.

    ``on_step`` is invoked after each successful step with one of
    ``"candidate"`` / ``"job_spec"`` / ``"match"``. Failure short-circuits
    the chain and returns the original error.
    """
    STATE.last_error = ""

    res = extract_candidate(output_lang=output_lang, target_role=target_role)
    if not res.ok:
        return res
    if on_step:
        on_step("candidate")

    res = extract_job_spec(output_lang=output_lang)
    if not res.ok:
        return res
    if on_step:
        on_step("job_spec")

    res = analyze_match(output_lang=output_lang)
    if not res.ok:
        return res
    if on_step:
        on_step("match")

    STATE.activity = "ready"
    safe(REFS.rerender_context)
    return PipelineResult(ok=True)


# Demo helpers ----------------------------------------------------------------


def load_demo(*, output_lang: str) -> None:
    """Pre-populate state with the demo seed for an offline showcase."""
    STATE.demo_mode = True
    STATE.target_role = (
        "Senior Frontend Engineer (React / TypeScript)" if output_lang == "en" else
        "Senior Frontend Engineer (React / TypeScript)"
    )
    STATE.job_url = "https://example.com/jobs/senior-frontend-engineer"
    STATE.job_text = career_data.DEMO_JOB_TEXT
    STATE.job_text_source = "demo"
    STATE.resume = UploadedFile(
        path="(demo)",
        name="Jan_Novak_CV.pdf",
        ext="pdf",
        size_bytes=156_000,
        text=career_data.DEMO_RESUME_TEXT,
    )
    STATE.linkedin = None
    STATE.github_skip = True
    STATE.github_profile = None
    STATE.candidate = career_data.demo_candidate(output_lang)
    STATE.job_spec = career_data.demo_job_spec(output_lang)
    STATE.match = career_data.demo_match(output_lang)
    STATE.documents = {kind: _demo_document(kind, output_lang) for kind in _DOC_SYSTEM_BY_KIND}
    STATE.activity = "ready"
    safe(REFS.rerender_main)
    safe(REFS.rerender_context)


def _demo_document(kind: str, lang: str) -> str:
    """Hand-written markdown documents that match the demo candidate / job."""
    is_cs = lang == "cs"
    if kind == DOC_TAILORED_CV:
        if is_cs:
            return _DEMO_TAILORED_CV_CS
        return _DEMO_TAILORED_CV_EN
    if kind == DOC_MODERN_CV:
        if is_cs:
            return _DEMO_MODERN_CV_CS
        return _DEMO_MODERN_CV_EN
    if kind == DOC_COVER_LETTER:
        if is_cs:
            return _DEMO_COVER_LETTER_CS
        return _DEMO_COVER_LETTER_EN
    if kind == DOC_MATCH_REPORT:
        if is_cs:
            return _DEMO_MATCH_REPORT_CS
        return _DEMO_MATCH_REPORT_EN
    if kind == DOC_INTERVIEW_PREP:
        if is_cs:
            return _DEMO_INTERVIEW_PREP_CS
        return _DEMO_INTERVIEW_PREP_EN
    if kind == DOC_SKILL_GAP:
        if is_cs:
            return _DEMO_SKILL_GAP_CS
        return _DEMO_SKILL_GAP_EN
    return ""


_DEMO_TAILORED_CV_EN = """\
# Jan Novák
jan.novak@email.cz | +420 777 123 456 | Prague
github.com/jannovak

## Professional summary
Frontend developer with 4 years of experience targeting a Senior Frontend Engineer role on a React + TypeScript platform team. Track record of leading framework migrations, owning a design system slice, and mentoring juniors.

## Technical skills
- Frontend: React, TypeScript, Next.js, Redux Toolkit
- Quality: Cypress, Jest
- Tooling: GitHub Actions

## Work experience

### Frontend Developer - Acme Retail (08/2022 - present)
- Led the migration of the legacy AngularJS storefront to Next.js, cutting Time to Interactive by 38%.
- Co-owned the design system; shipped 24 reusable React components used by 6 product squads.
- Mentored two junior developers through their first quarter.

### Junior Frontend Developer - StartHub s.r.o. (06/2020 - 07/2022)
- Built the customer dashboard in React + TypeScript for a fintech B2B product (4000 daily active users).
- Set up the CI pipeline (GitHub Actions, Cypress) used by 5 frontend engineers.

## Education

### Bachelor of Computer Science - Czech Technical University in Prague (2017 - 2020)

## Languages (CEFR)
- Czech (C2)
- English (C1)
"""


_DEMO_TAILORED_CV_CS = """\
# Jan Novák
jan.novak@email.cz | +420 777 123 456 | Praha
github.com/jannovak

## Profesní shrnutí
Frontend developer se 4 lety praxe; cílem je pozice Senior Frontend Engineer v platformovém týmu (React + TypeScript). Mám zkušenosti s vedením frameworkových migrací, vlastnictvím design systému a mentoringem juniorů.

## Technické dovednosti
- Frontend: React, TypeScript, Next.js, Redux Toolkit
- Quality: Cypress, Jest
- Tooling: GitHub Actions

## Pracovní zkušenosti

### Frontend Developer - Acme Retail (08/2022 - dosud)
- Vedl migraci legacy AngularJS obchodu na Next.js; Time to Interactive klesl o 38 %.
- Spoluvlastnil design systém - dodal 24 znovupoužitelných React komponent pro 6 produktových týmů.
- Mentoroval dva juniorní vývojáře v jejich prvním kvartálu.

### Junior Frontend Developer - StartHub s.r.o. (06/2020 - 07/2022)
- Postavil zákaznický dashboard v Reactu + TypeScriptu pro fintech B2B produkt (4 000 DAU).
- Nastavil CI pipeline (GitHub Actions, Cypress), kterou používá 5 frontend inženýrů.

## Vzdělání

### Bakalář, Informatika - České vysoké učení technické v Praze (2017 - 2020)

## Jazyky (CEFR)
- Čeština (C2)
- Angličtina (C1)
"""


_DEMO_MODERN_CV_EN = """\
# Jan Novák - Frontend Engineer
jan.novak@email.cz | Prague | github.com/jannovak

Senior-track frontend developer with 4 years of React + TypeScript experience and a habit of leaving codebases more boring than I found them.

## Recent work
**Acme Retail - Frontend Developer (08/2022 - present)**
Migrated AngularJS to Next.js (-38% TTI). Owned 24 design-system components used by 6 squads. Mentored two juniors.

**StartHub - Junior Frontend Developer (06/2020 - 07/2022)**
Built the customer dashboard for a fintech B2B (4000 DAU). Set up the team's CI pipeline.

## Tools
React · TypeScript · Next.js · Redux Toolkit · Cypress · Jest · GitHub Actions

## Education
BSc Computer Science, Czech Technical University in Prague (2017 - 2020)

## Languages
Czech (C2) · English (C1)
"""


_DEMO_MODERN_CV_CS = """\
# Jan Novák - Frontend Engineer
jan.novak@email.cz | Praha | github.com/jannovak

Frontend developer 4 roky praxe, React + TypeScript, baví mě nechávat kód nudnější, než jsem ho našel.

## Aktuální praxe
**Acme Retail - Frontend Developer (08/2022 - dosud)**
Migroval jsem AngularJS na Next.js (-38 % TTI). Vlastnil 24 komponent v design systému pro 6 týmů. Mentoroval dva juniory.

**StartHub - Junior Frontend Developer (06/2020 - 07/2022)**
Postavil zákaznický dashboard pro fintech B2B (4 000 DAU). Nastavil týmovou CI pipeline.

## Nástroje
React · TypeScript · Next.js · Redux Toolkit · Cypress · Jest · GitHub Actions

## Vzdělání
Bc., Informatika, ČVUT v Praze (2017 - 2020)

## Jazyky
Čeština (C2) · Angličtina (C1)
"""


_DEMO_COVER_LETTER_EN = """\
Dear QualityWorks team,

When I read that QualityWorks is hiring a Senior Frontend Engineer to own the customer dashboard and partner with the design-system team, the role read like a mirror of what I have spent the last two years doing at Acme Retail. I would love to bring that work to a platform with the technical ambition you describe in your engineering blog.

At Acme I led the migration of a 9-year-old AngularJS storefront to Next.js. Time to Interactive dropped by 38% on the homepage and we cut bundle size in half - the kind of quiet win that makes the support team's life better, which is what I value about platform work. Alongside that I co-own the design-system slice, where I have shipped 24 reusable React components used by six product squads. The collaboration ritual I built with two junior developers is what convinced me I want a senior role explicitly: I notice I learn faster when I have to teach.

QualityWorks's recent push toward Storybook-driven design tokens is exactly the next step I want to make. I have not yet shipped Storybook in production - that is the only must-have I am missing - and I am putting that gap on my roadmap regardless of how this conversation goes.

I would welcome the chance to talk. You can reach me at jan.novak@email.cz or +420 777 123 456.

Thank you for your time,
Jan Novák
"""


_DEMO_COVER_LETTER_CS = """\
Vážený týme QualityWorks,

když jsem si přečetl, že hledáte Senior Frontend Engineera, který bude vlastnit zákaznický dashboard a spolupracovat s týmem design systému, pozice se přesně potkala s tím, čemu se poslední dva roky věnuji v Acme Retail. Rád bych tuhle práci přinesl do týmu s technickou ambicí, kterou popisujete na svém engineering blogu.

V Acme jsem vedl migraci 9 let staré AngularJS aplikace na Next.js. Time to Interactive na hlavní stránce kleslo o 38 % a zmenšili jsme bundle na polovinu - tichá výhra, kterou ocení supportní tým, a to je to, co mě na platformové práci baví. Současně spoluvlastním část design systému - dodal jsem 24 znovupoužitelných React komponent, které používá 6 produktových týmů. Rituál mentoringu, který jsem si nastavil se dvěma juniory, mě přesvědčil, že chci konkrétně seniorskou roli: všiml jsem si, že se učím rychleji, když musím učit.

Posun QualityWorks směrem ke Storybook-driven design tokens je přesně další krok, který chci udělat. Storybook jsem ještě v produkci nenasadil - to je jediné must-have, které mi chybí - a tu mezeru si dávám do roadmapy bez ohledu na to, jak tento rozhovor dopadne.

Rád si o tom popovídám. Zastihnete mě na jan.novak@email.cz nebo +420 777 123 456.

Děkuji za váš čas,
Jan Novák
"""


_DEMO_MATCH_REPORT_EN = """\
# Match report - Senior Frontend Engineer @ QualityWorks

**Overall fit: 72 / 100** - strong fit, two minor gaps.

## Score by category
- **Technical skills: 84/100** - React + TypeScript across both roles, Next.js in the Acme migration.
- **Experience: 65/100** - 4 years vs. 5+ required.
- **Tools: 70/100** - Cypress and GitHub Actions yes; Storybook missing.
- **Mentoring & soft skills: 80/100** - mentored two juniors, worked with 6 product squads.

## Matches
- React, TypeScript, Next.js and Redux Toolkit are evidenced
- Cypress and GitHub Actions used in the current role
- Mentoring juniors is documented

## Gaps
- 5+ years of experience not yet met (you have 4)
- Storybook and Figma do not appear anywhere in the resume

## ATS keyword coverage
- **Present:** React, TypeScript, Next.js, Redux Toolkit, Cypress, GitHub Actions, mentoring
- **Missing:** Storybook, Figma, design system
"""


_DEMO_MATCH_REPORT_CS = """\
# Report shody - Senior Frontend Engineer @ QualityWorks

**Celková shoda: 72 / 100** - silná shoda, dvě drobné mezery.

## Skóre po kategoriích
- **Technické dovednosti: 84/100** - React + TypeScript v obou rolích, Next.js v Acme migraci.
- **Praxe: 65/100** - 4 roky vs. 5+ požadovaných.
- **Nástroje: 70/100** - Cypress a GitHub Actions ano; Storybook chybí.
- **Mentoring & soft skills: 80/100** - mentoroval dva juniory, spolupráce s 6 produktovými týmy.

## Shody
- React, TypeScript, Next.js a Redux Toolkit jsou potvrzené
- Cypress a GitHub Actions v aktuální roli
- Mentoring juniorů je doložený

## Mezery
- 5+ let praxe není splněno (máte 4)
- Storybook a Figma se v životopise nikde neobjevují

## Pokrytí ATS klíčových slov
- **Přítomno:** React, TypeScript, Next.js, Redux Toolkit, Cypress, GitHub Actions, mentoring
- **Chybí:** Storybook, Figma, design system
"""


_DEMO_INTERVIEW_PREP_EN = """\
# Interview prep - Senior Frontend Engineer @ QualityWorks

## Likely interview questions
1. How would you sequence component replacement in an existing design system?
2. Walk me through the AngularJS -> Next.js migration. What would you do differently?
3. How do you measure mentoring impact for a junior developer?
4. When do you reach for Redux Toolkit vs. Zustand?
5. How do you keep Cypress end-to-end tests from getting flaky?
6. What does a good design system look like to you?

## Suggested talking points
- Use the AngularJS -> Next.js migration as your headline story (Situation, Task, Action, Result).
- For the mentoring question, reference the two junior developers and the rituals you built (weekly 1:1, code-review pairing).
- For Storybook, be honest: not yet in production, but here is the plan you're shipping.

## Questions to ask the interviewer
1. How is the design-system team staffed today, and how does ownership move between platform and product squads?
2. What does the current Time to Interactive look like on the customer dashboard?
3. What would the first 90 days look like for this role?
4. How does QualityWorks measure frontend engineering impact?
5. What is the team's relationship with the product designers in Figma?
"""


_DEMO_INTERVIEW_PREP_CS = """\
# Příprava na pohovor - Senior Frontend Engineer @ QualityWorks

## Pravděpodobné otázky u pohovoru
1. Jak byste navrhl postupné nahrazení komponent v existujícím design systému?
2. Popište migraci z AngularJS na Next.js. Co byste udělal jinak?
3. Jak měříte úspěch mentoringu juniorního vývojáře?
4. Kdy zvolíte Redux Toolkit a kdy Zustand?
5. Jak píšete Cypress end-to-end testy, aby nebyly flaky?
6. Co pro vás znamená dobrý design systém?

## Doporučené body do odpovědí
- Migraci z AngularJS na Next.js použij jako hlavní příběh (Situace, Úkol, Akce, Výsledek).
- U otázky na mentoring zmiň dva juniory a rituály, které jsi nastavil (týdenní 1:1, párování při review).
- U Storybooku buď upřímný: zatím ne v produkci, ale tady je plán, co děláš.

## Otázky pro pohovorujícího
1. Jak je dnes obsazený tým design systému a jak se pohybuje vlastnictví mezi platformou a produktovými týmy?
2. Jak vypadá aktuální Time to Interactive na zákaznickém dashboardu?
3. Co by bylo cílem prvních 90 dní v této roli?
4. Jak QualityWorks měří dopad frontend engineeringu?
5. Jaký je vztah týmu s produktovými designéry v Figmě?
"""


_DEMO_SKILL_GAP_EN = """\
# Skill-gap closing plan

### Storybook
- Action: Finish the official Intro to Storybook tutorial and add Storybook to 5 components in your design-system slice.
- Timeline: ~3 weeks
- Why it matters: QualityWorks lists Storybook as a tool requirement and is migrating tokens through it.
- Evidence to build: Public repo with the 5 components in Storybook plus a short blog post about it.

### Figma collaboration
- Action: Schedule a shadow session with a designer at Acme; try auto-layout and token import.
- Timeline: ~2 weeks
- Why it matters: Bridging design and engineering is part of the QualityWorks role.
- Evidence to build: One Figma file you co-edited, even if small.

### Years of experience (5+)
- Action: Add open-source contributions to Next.js / Redux Toolkit; reframe your 4 years to highlight scope and team size.
- Timeline: ~6 weeks
- Why it matters: The job description is firm on 5+ years; visible scope offsets the headline number.
- Evidence to build: Two merged PRs to a top-200 frontend OSS repo.
"""


_DEMO_SKILL_GAP_CS = """\
# Plán uzavření mezer

### Storybook
- Akce: Projít oficiální Intro to Storybook tutorial a nasadit Storybook na 5 komponent ze svého boku design systému.
- Časový rámec: ~3 týdny
- Proč je to důležité: QualityWorks má Storybook v požadavcích a migruje přes něj tokens.
- Co dodat jako důkaz: Veřejný repozitář s 5 komponentami v Storybooku plus krátký blog post.

### Figma collaboration
- Akce: Domluvit shadow session s designérem v Acme; vyzkoušet auto-layout a tokens import.
- Časový rámec: ~2 týdny
- Proč je to důležité: Most mezi designem a engineeringem je součástí role.
- Co dodat jako důkaz: Jeden Figma soubor, který jsi co-editoval, klidně malý.

### Praxe (5+ let)
- Akce: Doplnit profil o open-source contributions k Next.js / Redux Toolkit; přerámovat 4 roky tak, aby vynikla šíře odpovědnosti.
- Časový rámec: ~6 týdnů
- Proč je to důležité: JD je tvrdý na 5+ let; viditelná šíře odpovědnosti to vyrovnává.
- Co dodat jako důkaz: Dva mergnuté PR do top-200 frontend OSS repozitáře.
"""
