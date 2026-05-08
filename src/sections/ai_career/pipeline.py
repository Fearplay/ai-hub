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

from pathlib import Path

from src.services import ai_provider, exporter, github_client, job_scraper, store
from src.services.cost_tracker import COST
from src.sections.ai_career import data as career_data
from src.sections.ai_career import modern_cv_render, prompts, schema
from src.sections.ai_career.refs import REFS, safe
from src.sections.ai_career.state import (
    DOC_COVER_LETTER,
    DOC_EVIDENCE,
    DOC_INTERVIEW_PREP,
    DOC_MATCH_REPORT,
    DOC_MODERN_CV,
    DOC_SKILL_GAP,
    DOC_TAILORED_CV,
    ChatMessage,
    STATE,
    UploadedFile,
)


# Public types ----------------------------------------------------------------


@dataclass
class PipelineResult:
    ok: bool
    error: str = ""


def _request_full_refresh() -> None:
    """Re-run the section's ``build_view`` end-to-end.

    Lazy-imported so :mod:`src.app` does not load during section
    auto-discovery. Used by worker threads via :meth:`REFS.dispatch` to
    ensure the new tree is shipped to the client on the same loop tick
    instead of waiting for the next window event.
    """
    try:
        from src.app import request_section_refresh
    except Exception:
        return
    request_section_refresh()


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
    """Returns (text, error_message). Empty error means success.

    Activity is reset to ``"ready"`` whether the scrape succeeded or
    failed, so the right-hand context panel does not remain stuck on
    "Fetching..." once the request returns.
    """
    if not url.strip():
        return "", "URL is empty."
    _set_activity("scraping")
    try:
        result = job_scraper.scrape_job_posting(url)
    except Exception as exc:
        _set_activity("ready")
        return "", str(exc)
    if not result.ok:
        _set_activity("ready")
        return result.text, result.error or "Unknown scraping error."
    _set_activity("ready")
    return result.text, ""


def fetch_github_profile(value: str):
    if not value.strip():
        return None
    _set_activity("scraping")
    try:
        profile = github_client.fetch_profile(value)
    finally:
        _set_activity("ready")
    return profile


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
        raw_options = q.get("options") or []
        options = [
            str(opt).strip()
            for opt in raw_options
            if isinstance(opt, (str, int, float)) and str(opt).strip()
        ]
        cleaned.append(
            {
                "topic": topic,
                "question": question,
                "rationale": (q.get("rationale") or "").strip(),
                "options": options,
                "multi_select": bool(q.get("multi_select", False)),
                "allow_free_text": bool(q.get("allow_free_text", True)),
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
    # MODERN_CV is intentionally NOT in this map - it goes through
    # ``generate_modern_cv_data`` (structured JSON, custom renderer),
    # not the markdown-document path.
    DOC_COVER_LETTER: prompts.COVER_LETTER_SYSTEM,
    DOC_MATCH_REPORT: prompts.MATCH_REPORT_SYSTEM,
    DOC_INTERVIEW_PREP: prompts.INTERVIEW_PREP_SYSTEM,
    DOC_SKILL_GAP: prompts.SKILL_GAP_SYSTEM,
}


def generate_all_documents(*, output_lang: str) -> PipelineResult:
    """Generate every visible document in one batch.

    Used by the "Generate documents" button on the Match tab so the user
    arrives at the Documents tab with every section already populated
    instead of having to click Generate per-tab.

    The Evidence document is built deterministically from the match
    JSON's ``evidence_preview`` and the GitHub repo summary - there is
    no LLM prompt for it, which is why it lives outside the per-kind
    LLM loop. When GitHub data is missing the Evidence tab stays
    empty (the UI shows a "lock" placeholder instead of fabricating
    signals).
    """
    # Markdown documents only here. Modern CV uses a structured JSON
    # payload + custom renderer so we run it through its own helper.
    kinds = [
        DOC_TAILORED_CV,
        DOC_COVER_LETTER,
        DOC_MATCH_REPORT,
        DOC_INTERVIEW_PREP,
        DOC_SKILL_GAP,
    ]

    for kind in kinds:
        res = generate_document(kind, output_lang=output_lang)
        if not res.ok:
            return res

    res = generate_modern_cv_data(output_lang=output_lang)
    if not res.ok:
        return res

    if (
        STATE.candidate
        and STATE.candidate.get("github_present")
        and not STATE.github_skip
    ):
        evidence_md = build_evidence_document(output_lang=output_lang)
        if evidence_md:
            STATE.documents[DOC_EVIDENCE] = evidence_md

    STATE.activity = "ready"
    safe(REFS.rerender_context)
    REFS.dispatch(_request_full_refresh)
    return PipelineResult(ok=True)


def generate_modern_cv_data(*, output_lang: str) -> PipelineResult:
    """Run the Modern CV JSON generator and store the result on STATE.

    Demo mode short-circuits with a hand-curated payload built from
    :mod:`src.sections.ai_career.data` so the offline showcase renders
    the same fancy two-column layout without a network call.
    """
    if STATE.demo_mode:
        STATE.modern_cv_data = career_data.demo_modern_cv(output_lang)
        REFS.dispatch(_request_full_refresh)
        return PipelineResult(ok=True)

    if not (STATE.candidate and STATE.job_spec and STATE.match):
        return _set_error("Run analysis before generating the Modern CV.")

    _set_activity("generating")
    user = prompts.build_modern_cv_user(
        output_lang=output_lang,
        candidate=STATE.candidate,
        job_spec=STATE.job_spec,
        match=STATE.match,
    )
    try:
        result = ai_provider.run(
            system=prompts.MODERN_CV_DATA_SYSTEM,
            user=user,
            schema=schema.MODERN_CV_SCHEMA,
            schema_name="modern_cv",
            max_output_tokens=3500,
        )
    except ai_provider.ProviderError as exc:
        return _set_error(str(exc))
    if not isinstance(result.data, dict):
        return _set_error("Provider did not return a Modern CV JSON.")
    STATE.modern_cv_data = result.data
    STATE.activity = "ready"
    safe(REFS.rerender_context)
    REFS.dispatch(_request_full_refresh)
    return PipelineResult(ok=True)


def refine_modern_cv(*, output_lang: str, problems: list[str]) -> PipelineResult:
    """Re-run the Modern CV JSON generator with the candidate's problems."""
    cleaned = [p for p in problems if p and p.strip()]
    if not cleaned:
        return _set_error("Add at least one problem before refining.")

    if STATE.demo_mode:
        # Demo mode: shallow tag the existing payload so the user sees a
        # change without sending tokens.
        if STATE.modern_cv_data is None:
            STATE.modern_cv_data = career_data.demo_modern_cv(output_lang)
        existing = STATE.modern_cv_data
        existing.setdefault("leadership_highlights", []).insert(
            0,
            "**Demo refinement:** would address the listed problems.",
        )
        REFS.dispatch(_request_full_refresh)
        return PipelineResult(ok=True)

    if not (STATE.candidate and STATE.job_spec and STATE.match):
        return _set_error("Run analysis before refining the Modern CV.")

    _set_activity("generating")
    user = prompts.build_modern_cv_user(
        output_lang=output_lang,
        candidate=STATE.candidate,
        job_spec=STATE.job_spec,
        match=STATE.match,
        current_payload=STATE.modern_cv_data,
        problems=cleaned,
    )
    try:
        result = ai_provider.run(
            system=prompts.MODERN_CV_DATA_REFINE_SYSTEM,
            user=user,
            schema=schema.MODERN_CV_SCHEMA,
            schema_name="modern_cv",
            max_output_tokens=3500,
        )
    except ai_provider.ProviderError as exc:
        return _set_error(str(exc))
    if not isinstance(result.data, dict):
        return _set_error("Provider did not return a refined Modern CV JSON.")
    STATE.modern_cv_data = result.data
    STATE.activity = "ready"
    safe(REFS.rerender_context)
    REFS.dispatch(_request_full_refresh)
    return PipelineResult(ok=True)


def build_evidence_document(*, output_lang: str) -> str:
    """Synthesise the Evidence document from existing structured data.

    Pulls the ``evidence_preview`` snippets that the match-analysis call
    already returned, plus a short summary of the candidate's top GitHub
    repos. No new LLM call - we already paid for these signals upstream
    and the doc is just a readable rollup so the candidate can attach
    it when they want to back up claims in their CV.
    """
    is_cs = output_lang == "cs"
    match = STATE.match or {}
    candidate = STATE.candidate or {}
    profile = STATE.github_profile

    raw_lines = match.get("evidence_preview") or []
    bullets = [str(line).strip() for line in raw_lines if str(line).strip()]

    role = ""
    company = ""
    job = STATE.job_spec or {}
    if job:
        role = str(job.get("title") or "")
        company = str(job.get("company") or "")

    parts: list[str] = []
    if is_cs:
        parts.append("# Doložené body shody")
        if role and company:
            parts.append(f"_Pro pozici **{role}** ve společnosti **{company}**._")
        elif role:
            parts.append(f"_Pro pozici **{role}**._")
        if bullets:
            parts.append("\n## Důkazy z rozhovoru")
            parts.extend(f"- {b}" for b in bullets)
    else:
        parts.append("# Evidence pack")
        if role and company:
            parts.append(f"_For the **{role}** role at **{company}**._")
        elif role:
            parts.append(f"_For the **{role}** role._")
        if bullets:
            parts.append("\n## Match evidence")
            parts.extend(f"- {b}" for b in bullets)

    if profile is not None and getattr(profile, "ok", False):
        repos = getattr(profile, "repos", []) or []
        if repos:
            heading = (
                "## Veřejné GitHub repozitáře"
                if is_cs
                else "## Public GitHub repositories"
            )
            parts.append("\n" + heading)
            for repo in repos[:6]:
                name = getattr(repo, "name", "") or ""
                url = getattr(repo, "url", "") or ""
                desc = (getattr(repo, "description", "") or "").strip()
                stars = int(getattr(repo, "stars", 0) or 0)
                langs = ", ".join((getattr(repo, "languages", []) or [])[:3])
                line = f"- [{name}]({url})" if url else f"- {name}"
                meta = []
                if langs:
                    meta.append(langs)
                if stars:
                    meta.append(("⭐ " if not is_cs else "Hvězdy: ") + str(stars))
                if meta:
                    line += f" — {' · '.join(meta)}"
                if desc:
                    line += f"\n  {desc}"
                parts.append(line)

    skills = candidate.get("skills") if candidate else None
    if isinstance(skills, list) and skills:
        heading = "## Klíčové dovednosti z CV" if is_cs else "## Key skills from the CV"
        parts.append("\n" + heading)
        joined = ", ".join(str(sk).strip() for sk in skills if str(sk).strip())
        if joined:
            parts.append(joined)

    if len(parts) <= 1:
        # Nothing useful to render - return empty so the UI keeps the
        # "no evidence" placeholder instead of an awkward stub.
        return ""

    return "\n".join(parts).strip() + "\n"


def generate_document(kind: str, *, output_lang: str) -> PipelineResult:
    if kind == DOC_EVIDENCE:
        text = build_evidence_document(output_lang=output_lang)
        if not text:
            return _set_error("No evidence available - load GitHub data first.")
        STATE.documents[DOC_EVIDENCE] = text
        STATE.activity = "ready"
        safe(REFS.rerender_context)
        REFS.dispatch(_request_full_refresh)
        return PipelineResult(ok=True)

    if kind == DOC_MODERN_CV:
        # Modern CV is structured JSON + custom renderer (teal sidebar
        # layout); the markdown-document path doesn't apply here.
        return generate_modern_cv_data(output_lang=output_lang)

    if kind not in _DOC_SYSTEM_BY_KIND:
        return _set_error(f"Unknown document kind: {kind}")
    if STATE.demo_mode:
        STATE.documents[kind] = _demo_document(kind, output_lang)
        REFS.dispatch(_request_full_refresh)
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
    safe(REFS.rerender_context)
    REFS.dispatch(_request_full_refresh)
    return PipelineResult(ok=True)


# Step 5: refine an existing document ----------------------------------------


def refine_document(
    kind: str,
    *,
    output_lang: str,
    problems: list[str],
) -> PipelineResult:
    if kind == DOC_MODERN_CV:
        # Modern CV: regenerate the JSON payload from scratch with the
        # candidate's notes applied, then re-render. There is no
        # markdown body to patch in place.
        return refine_modern_cv(output_lang=output_lang, problems=problems)

    if kind not in _DOC_SYSTEM_BY_KIND:
        return _set_error(f"Unknown document kind: {kind}")
    current = STATE.documents.get(kind, "")
    if not current:
        return _set_error("Generate the document before refining it.")

    if STATE.demo_mode:
        appended = "\n\n_(Demo refinement: would address the listed problems.)_"
        STATE.documents[kind] = current + appended
        REFS.dispatch(_request_full_refresh)
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
    safe(REFS.rerender_context)
    REFS.dispatch(_request_full_refresh)
    return PipelineResult(ok=True)


# Chat-mode -------------------------------------------------------------------


def send_chat_message(
    *,
    output_lang: str,
    user_text: str,
) -> tuple[str, str]:
    """Synchronous chat turn for the Chat-mode UI.

    Returns ``(assistant_text, error)``. On success ``error`` is empty;
    on failure ``assistant_text`` is empty and the caller renders the
    error in-place. The helper itself does **not** mutate
    ``STATE.chat_messages`` - the caller controls how the user/assistant
    bubbles are appended (so the UI thread can show the user bubble
    immediately and only append the assistant bubble after the network
    call returns).
    """
    user_text = (user_text or "").strip()
    if not user_text:
        return "", "Empty message."

    if STATE.demo_mode:
        # Echo a short canned reply so the demo flow is fully offline.
        # We intentionally do NOT touch the cost tracker here - demo
        # mode promises 0 spend.
        canned = _demo_chat_reply(user_text, output_lang)
        return canned, ""

    history = [
        {"role": m.role, "text": m.text}
        for m in STATE.chat_messages
    ]
    user = prompts.build_chat_user_block(
        output_lang=output_lang,
        history=history,
        attachments=dict(STATE.chat_attachments),
        user_text=user_text,
    )
    try:
        result = ai_provider.run(
            system=prompts.CHAT_MODE_SYSTEM,
            user=user,
            schema=None,
            max_output_tokens=900,
            temperature=0.4,
        )
    except ai_provider.ProviderError as exc:
        return "", str(exc)
    text = (result.text or "").strip()
    if not text:
        return "", "Provider returned an empty response."
    return text, ""


def _demo_chat_reply(user_text: str, lang: str) -> str:
    """Tiny canned replies so the Chat mode is usable in Demo mode."""
    is_cs = lang == "cs"
    lower = user_text.lower()

    if any(token in lower for token in ("cv", "životopis", "zivotopis", "resume")):
        if is_cs:
            return (
                "Jasně, pomůžu ti s životopisem. V Demo režimu jen předvádím "
                "tok aplikace, takže odpovídám předvyplněnými větami. Pro "
                "skutečné CV na míru přepni na **Formulářový režim** - "
                "vlož inzerát, životopis a klikni na Spustit analýzu."
            )
        return (
            "Sure, I can help with your CV. We're in Demo mode so this is "
            "a canned reply showing the chat flow. For a real tailored "
            "CV, switch to **Form mode** - drop the job posting, your "
            "resume, and click Run analysis."
        )
    if any(token in lower for token in ("cover", "motivační", "motivacni", "letter")):
        if is_cs:
            return (
                "Pro motivační dopis bych potřeboval inzerát a krátce tvoje "
                "klíčové výsledky. V Demo režimu jen ukazuju, jak vypadá "
                "konverzace. Pro skutečný dopis přepni na Formulářový "
                "režim a vyplň STEP 1 a STEP 2."
            )
        return (
            "For a cover letter I'd need the job posting and a one-line "
            "summary of your top wins. We're in Demo mode so this is a "
            "scripted reply - for a real letter switch to Form mode "
            "and fill in STEP 1 and STEP 2."
        )
    if any(token in lower for token in ("interview", "pohovor")):
        if is_cs:
            return (
                "Na pohovor obvykle pomůže projít si 5-7 typických otázek, "
                "připravit STAR příběh ke každé a 3-5 otázek pro vás na konci. "
                "V Demo režimu odpovídám předvyplněnými větami - pro reálnou "
                "přípravu spusť analýzu ve Formulářovém režimu."
            )
        return (
            "For an interview, walk through 5-7 likely questions, draft a "
            "STAR story for each, and prepare 3-5 questions for them at the "
            "end. We're in Demo mode so this is a canned reply - for the "
            "real prep run the analysis in Form mode."
        )
    if is_cs:
        return (
            "Jsem tady, abych ti pomohl s životopisem, motivačním dopisem, "
            "přípravou na pohovor a analýzou inzerátu. Co tě zajímá? "
            "(Demo režim - odpovídám předvyplněnými větami; pro reálnou "
            "AI vypni Demo režim v Nastavení a přidej API klíč.)"
        )
    return (
        "I'm here to help with CVs, cover letters, interview prep and "
        "job-posting analysis. What do you want to work on? "
        "(Demo mode - I'm replying with scripted text; turn off Demo "
        "mode in Settings and add an API key for real AI replies.)"
    )


def append_chat_message(
    role: str,
    text: str,
    *,
    time_label: str = "",
    attachment_name: str = "",
) -> None:
    """Append a message to the in-memory transcript.

    Centralised so the Chat view, the Demo seed, and any future history
    restore all use the same dataclass.
    """
    from datetime import datetime

    label = time_label or datetime.now().strftime("%H:%M")
    STATE.chat_messages.append(
        ChatMessage(
            role=role,
            text=text,
            time=label,
            attachment_name=attachment_name,
        )
    )


# Save complete analysis ------------------------------------------------------


_DOC_FILE_BASENAMES: dict[str, str] = {
    DOC_TAILORED_CV: "Tailored_CV",
    DOC_MODERN_CV: "Modern_CV",
    DOC_COVER_LETTER: "Cover_Letter",
    DOC_MATCH_REPORT: "Match_Report",
    DOC_INTERVIEW_PREP: "Interview_Prep",
    DOC_SKILL_GAP: "Skill_Gap_Plan",
    DOC_EVIDENCE: "Evidence_Report",
}

_EXPORT_PLAN: dict[str, tuple[str, ...]] = {
    DOC_TAILORED_CV: ("html", "pdf"),
    # Modern CV runs through ``modern_cv_render`` directly (HTML + PDF +
    # JSON sidecar) so it is intentionally absent from the markdown
    # export plan loop above.
    DOC_COVER_LETTER: ("pdf",),
    DOC_MATCH_REPORT: ("html", "md"),
    DOC_INTERVIEW_PREP: ("html", "md"),
    DOC_SKILL_GAP: ("html", "md"),
    DOC_EVIDENCE: ("html", "md"),
}

_MODERN_STYLE_DOCS: frozenset[str] = frozenset({DOC_MODERN_CV, DOC_COVER_LETTER})


@dataclass
class SaveResult:
    ok: bool
    folder: str = ""
    error: str = ""


def save_full_analysis() -> SaveResult:
    """Persist every generated document + a summary.json + history entry.

    Used by both the Documents footer ("Save complete analysis") button
    and the section header menu's "Save full analysis" item. The on-disk
    layout matches what the History tab expects so "Open in app" still
    rehydrates the run later.
    """
    if not STATE.documents and not STATE.modern_cv_data:
        return SaveResult(ok=False, error="no_documents")

    role = ""
    if STATE.job_spec:
        role = str(STATE.job_spec.get("title") or "")
    if STATE.last_run_folder and Path(STATE.last_run_folder).is_dir():
        folder_path = Path(STATE.last_run_folder)
    else:
        folder_path = Path(store.new_run_dir(role or "ai-career-run"))
        STATE.last_run_folder = str(folder_path)

    for kind, body_text in STATE.documents.items():
        if not body_text:
            continue
        formats = _EXPORT_PLAN.get(kind, ("md", "pdf"))
        basename = _DOC_FILE_BASENAMES.get(kind, kind)
        title = basename.replace("_", " ")
        style = "modern" if kind in _MODERN_STYLE_DOCS else "ats"
        for fmt in formats:
            try:
                if fmt == "md":
                    exporter.export_markdown(body_text, folder_path / f"{basename}.md")
                elif fmt == "html":
                    exporter.export_html(
                        body_text,
                        folder_path / f"{basename}.html",
                        title=title,
                        style=style,
                    )
                elif fmt == "docx":
                    exporter.export_docx(
                        body_text, folder_path / f"{basename}.docx", title=title
                    )
                elif fmt == "pdf":
                    exporter.export_pdf(
                        body_text,
                        folder_path / f"{basename}.pdf",
                        title=title,
                        style=style,
                    )
            except RuntimeError:
                # Optional dep (e.g. python-docx) is missing on this
                # machine. Skip this format and keep going.
                continue

    # Modern CV - structured payload + custom two-column renderer.
    if STATE.modern_cv_data:
        basename = _DOC_FILE_BASENAMES.get(DOC_MODERN_CV, "Modern_CV")
        try:
            (folder_path / f"{basename}.html").write_text(
                modern_cv_render.render_html(STATE.modern_cv_data),
                encoding="utf-8",
            )
        except Exception:
            pass
        try:
            modern_cv_render.render_pdf(
                STATE.modern_cv_data, folder_path / f"{basename}.pdf"
            )
        except Exception:
            pass
        try:
            import json as _json

            (folder_path / f"{basename}.json").write_text(
                _json.dumps(STATE.modern_cv_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    candidate = STATE.candidate or {}
    job_spec = STATE.job_spec or {}
    match = STATE.match or {}
    try:
        store.write_json_file(
            folder_path,
            "summary.json",
            {
                "candidate": candidate,
                "job_spec": job_spec,
                "match": match,
                "cost": {
                    "calls": COST.calls,
                    "tokens": COST.tokens_total,
                    "usd": COST.cost_usd,
                },
            },
        )
    except Exception:
        pass

    try:
        from datetime import datetime

        company = ""
        if STATE.job_spec:
            company = str(STATE.job_spec.get("company") or "")
        score = int((STATE.match or {}).get("overall_score") or 0)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        # Modern CV ships outside the markdown ``STATE.documents`` dict
        # but still belongs in the History entry so the user can see it
        # in the saved-run breakdown.
        docs_list = list(STATE.documents.keys())
        if STATE.modern_cv_data and DOC_MODERN_CV not in docs_list:
            docs_list.append(DOC_MODERN_CV)
        summary = store.RunSummary(
            timestamp=timestamp,
            role=role,
            company=company,
            overall_score=score,
            folder=str(folder_path),
            provider=("demo" if STATE.demo_mode else ""),
            model=("demo" if STATE.demo_mode else ""),
            cost_usd=0.0 if STATE.demo_mode else float(COST.cost_usd),
            docs=docs_list,
        )
        store.append_run(summary)
    except Exception:
        pass

    return SaveResult(ok=True, folder=str(folder_path))


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
    # Markdown-document kinds only - Modern CV gets the structured
    # payload below so the fancy two-column renderer has data to draw.
    STATE.documents = {kind: _demo_document(kind, output_lang) for kind in _DOC_SYSTEM_BY_KIND}
    STATE.modern_cv_data = career_data.demo_modern_cv(output_lang)
    STATE.activity = "ready"
    safe(REFS.rerender_context)
    REFS.dispatch(_request_full_refresh)


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
