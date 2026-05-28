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

import copy
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional

from pathlib import Path

from src.services import ai_provider, exporter, github_client, job_scraper, store
from src.services import logger as logger_service
from src.services.cost_tracker import COST
from src.sections.ai_career import data as career_data
from src.sections.ai_career import modern_cv_render, prompts, schema, themes
from src.sections.ai_career.refs import REFS
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
)


# Public types ----------------------------------------------------------------


@dataclass
class PipelineResult:
    ok: bool
    error: str = ""


# Text post-processing --------------------------------------------------------


def _clean_ai_text(text: str) -> str:
    """Replace em-dash (U+2014) and en-dash (U+2013) with a plain hyphen.

    LLMs love peppering their output with ``—`` even when the prompt
    asks for ASCII; users report the dashes look out of place against
    the rest of the codebase (headings, hand-written fragments) which
    all use ``-``. Normalising here means the saved Markdown / HTML /
    PDF files match what the user sees in the preview without us
    having to chase every prompt template.

    Spaces around the dash are preserved (`"A - B"` in, `"A - B"` out;
    `"A—B"` becomes `"A-B"`).
    """
    if not text:
        return text
    return text.replace("\u2014", "-").replace("\u2013", "-")


def _clean_ai_json(payload: Any) -> Any:
    """Recursively apply :func:`_clean_ai_text` to every string in a JSON-y tree.

    The Modern CV payload, Candidate / JobSpec / MatchAnalysis JSONs
    all flow through this so the dash normalisation reaches structured
    output too (the user spotted em-dashes in the Modern CV preview
    and the "Save complete analysis" output).
    """
    if isinstance(payload, str):
        return _clean_ai_text(payload)
    if isinstance(payload, list):
        return [_clean_ai_json(item) for item in payload]
    if isinstance(payload, dict):
        return {key: _clean_ai_json(value) for key, value in payload.items()}
    return payload


def _request_full_refresh() -> None:
    """Re-run the section's ``build_view`` end-to-end.

    Lazy-imported so :mod:`src.app` does not load during section
    auto-discovery. Used by worker threads via :meth:`REFS.dispatch` to
    ensure the new tree is shipped to the client on the same loop tick
    instead of waiting for the next window event.
    """
    try:
        from src.app import request_section_refresh
    except Exception as exc:
        logger_service.log_exception(
            "ai_career.pipeline", "request_full_refresh_import", exc
        )
        return
    request_section_refresh()


def _set_activity(value: str) -> None:
    """Update the right-hand activity badge from any thread.

    The pipeline is mostly called on background daemon threads (so the
    UI stays responsive while the LLM call is in flight). Routing the
    refresh through :meth:`REFS.request_context_refresh` guarantees the
    new badge is shown immediately - on the UI loop tick - instead of
    being queued behind whatever the user does next. Without this the
    user saw a stale "Ready" label even though the worker was busy.
    """
    prev = STATE.activity
    STATE.activity = value
    if prev != value:
        logger_service.log_event(
            "INFO",
            "ai_career.pipeline",
            "activity_change",
            prev=prev,
            new=value,
        )
    REFS.request_context_refresh()


def _set_error(message: str) -> PipelineResult:
    STATE.activity = "error"
    STATE.last_error = message
    REFS.request_context_refresh()
    logger_service.log_event(
        "ERROR", "ai_career.pipeline", "set_error", message=message
    )
    return PipelineResult(ok=False, error=message)


# Demo seed -------------------------------------------------------------------


def load_demo() -> None:
    """Populate ``STATE`` with curated mock data, no AI calls.

    Used by the ``...`` header menu's "Show demo data" item. Copies the
    constants from :mod:`src.sections.ai_career.data` so the user can
    explore Match / Documents / Modern CV without spending tokens.
    The pipeline functions all check ``STATE.demo_mode`` first and
    short-circuit to the same constants, so even if the user clicks
    "Run analysis" while demo is on no provider call is made.
    """
    logger_service.log_event(
        "INFO", "ai_career.pipeline", "load_demo_start"
    )
    STATE.demo_mode = True
    STATE.target_role = career_data.DEMO_TARGET_ROLE
    STATE.candidate = copy.deepcopy(career_data.DEMO_CANDIDATE)
    STATE.job_spec = copy.deepcopy(career_data.DEMO_JOB_SPEC)
    STATE.match = copy.deepcopy(career_data.DEMO_MATCH)
    STATE.modern_cv_data = copy.deepcopy(career_data.DEMO_MODERN_CV_DATA)
    STATE.documents = copy.deepcopy(career_data.DEMO_DOCUMENTS)
    STATE.followup_questions = []
    STATE.followup_qa = []
    STATE.refine_problems.clear()
    STATE.activity = "ready"
    STATE.last_error = ""
    STATE.run_stage = ""
    REFS.request_context_refresh()
    logger_service.log_state(
        "ai_career.pipeline", "load_demo_state",
        has_candidate=True,
        has_job_spec=True,
        has_match=True,
        docs=len(STATE.documents),
    )


def clear_demo() -> None:
    """Turn demo mode off and wipe the seeded payloads.

    Pairs with :func:`load_demo`. Resets every AI-derived field so the
    user starts from a clean Setup tab the next time they open the
    section, without leaking the curated TrustPay persona into a real
    run.
    """
    logger_service.log_event(
        "INFO", "ai_career.pipeline", "clear_demo_start"
    )
    STATE.demo_mode = False
    STATE.reset_run()
    REFS.request_context_refresh()


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
        # Demo mode is free + offline. Reseed the curated Candidate
        # JSON so users can "rerun" Setup without leaking tokens.
        logger_service.log_event(
            "INFO", "ai_career.pipeline", "extract_candidate_demo_done"
        )
        STATE.candidate = copy.deepcopy(career_data.DEMO_CANDIDATE)
        _set_activity("ready")
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
    STATE.candidate = _clean_ai_json(result.data)
    STATE.candidate["linkedin_present"] = bool(STATE.linkedin and STATE.linkedin.text)
    STATE.candidate["github_present"] = bool(STATE.github_profile and STATE.github_profile.ok)
    return PipelineResult(ok=True)


# Step 2: job spec extraction -------------------------------------------------


def extract_job_spec(*, output_lang: str) -> PipelineResult:
    if STATE.demo_mode:
        logger_service.log_event(
            "INFO", "ai_career.pipeline", "extract_job_spec_demo_done"
        )
        STATE.job_spec = copy.deepcopy(career_data.DEMO_JOB_SPEC)
        _set_activity("ready")
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
    STATE.job_spec = _clean_ai_json(result.data)
    return PipelineResult(ok=True)


# Step 2.5: optional follow-up questions -------------------------------------


def generate_followup_questions(*, output_lang: str) -> PipelineResult:
    """Ask the LLM to surface gaps that the candidate should clarify.

    Stores the result in ``STATE.followup_questions``. Returns success even
    when the AI emits zero questions - that is a valid outcome and means
    the resume already covers the job description.
    """
    if STATE.demo_mode:
        # Demo persona is already aligned with the job spec, so no
        # follow-ups are needed. Returning an empty list short-circuits
        # the "Ask follow-up questions" modal in the same way the LLM
        # would on a perfect-fit run.
        STATE.followup_questions = []
        _set_activity("ready")
        logger_service.log_event(
            "INFO", "ai_career.pipeline", "generate_followups_demo_done"
        )
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
        topic = _clean_ai_text((q.get("topic") or "").strip())
        question = _clean_ai_text((q.get("question") or "").strip())
        if not topic or not question:
            continue
        raw_options = q.get("options") or []
        options = [
            _clean_ai_text(str(opt).strip())
            for opt in raw_options
            if isinstance(opt, (str, int, float)) and str(opt).strip()
        ]
        cleaned.append(
            {
                "topic": topic,
                "question": question,
                "rationale": _clean_ai_text((q.get("rationale") or "").strip()),
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
        logger_service.log_event(
            "INFO", "ai_career.pipeline", "analyze_match_demo_done"
        )
        STATE.match = copy.deepcopy(career_data.DEMO_MATCH)
        _set_activity("ready")
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
        # The match schema carries the categories table, ATS bag,
        # 5-12 interview questions (each with rationale + STAR answer)
        # and the skill-gap plan (with learning path + portfolio
        # project per gap). At 3500 output tokens the LLM regularly
        # truncates the JSON mid-string and the parser raises
        # "Provider did not return a MatchAnalysis JSON". 8000 leaves
        # comfortable headroom on a typical run while still capping
        # the worst-case spend.
        result = ai_provider.run(
            system=prompts.MATCH_ANALYSIS_SYSTEM,
            user=user,
            schema=schema.MATCH_ANALYSIS_SCHEMA,
            schema_name="match_analysis",
            max_output_tokens=8000,
        )
    except ai_provider.ProviderError as exc:
        return _set_error(str(exc))
    if not isinstance(result.data, dict):
        return _set_error("Provider did not return a MatchAnalysis JSON.")
    STATE.match = _clean_ai_json(result.data)
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

    _set_activity("generating")
    for kind in kinds:
        res = generate_document(
            kind,
            output_lang=output_lang,
            refresh_ui=False,
            keep_activity=True,
        )
        if not res.ok:
            return res

    res = generate_modern_cv_data(
        output_lang=output_lang,
        refresh_ui=False,
        keep_activity=True,
    )
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

    _set_activity("ready")
    REFS.dispatch(_request_full_refresh)
    return PipelineResult(ok=True)


def generate_modern_cv_data(
    *,
    output_lang: str,
    refresh_ui: bool = True,
    keep_activity: bool = False,
) -> PipelineResult:
    """Run the Modern CV JSON generator and store the result on STATE."""
    if STATE.demo_mode:
        STATE.modern_cv_data = copy.deepcopy(career_data.DEMO_MODERN_CV_DATA)
        if not keep_activity:
            _set_activity("ready")
        if refresh_ui:
            REFS.request_context_refresh()
            REFS.dispatch(_request_full_refresh)
        logger_service.log_event(
            "INFO", "ai_career.pipeline", "generate_modern_cv_demo_done"
        )
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
    STATE.modern_cv_data = _clean_ai_json(result.data)
    if not keep_activity:
        _set_activity("ready")
    if refresh_ui:
        REFS.request_context_refresh()
        REFS.dispatch(_request_full_refresh)
    return PipelineResult(ok=True)


def refine_modern_cv(
    *,
    output_lang: str,
    problems: list[str],
    refresh_ui: bool = True,
    keep_activity: bool = False,
) -> PipelineResult:
    """Re-run the Modern CV JSON generator with the candidate's problems."""
    cleaned = [p for p in problems if p and p.strip()]
    if not cleaned:
        return _set_error("Add at least one problem before refining.")

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
    STATE.modern_cv_data = _clean_ai_json(result.data)
    if not keep_activity:
        _set_activity("ready")
    if refresh_ui:
        REFS.request_context_refresh()
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
                    line += f" - {' · '.join(meta)}"
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


def generate_document(
    kind: str,
    *,
    output_lang: str,
    refresh_ui: bool = True,
    keep_activity: bool = False,
) -> PipelineResult:
    logger_service.log_event(
        "INFO",
        "ai_career.pipeline",
        "generate_document_start",
        kind=kind,
        output_lang=output_lang,
        demo_mode=STATE.demo_mode,
    )
    if STATE.demo_mode:
        # Map the document kind onto the curated markdown body and
        # short-circuit. Modern CV stays special-cased below so the
        # JSON renderer keeps owning the layout.
        if kind == DOC_MODERN_CV:
            return generate_modern_cv_data(
                output_lang=output_lang,
                refresh_ui=refresh_ui,
                keep_activity=keep_activity,
            )
        demo_body = career_data.DEMO_DOCUMENTS.get(kind, "")
        if demo_body:
            STATE.documents[kind] = demo_body
        if not keep_activity:
            _set_activity("ready")
        if refresh_ui:
            REFS.request_context_refresh()
            REFS.dispatch(_request_full_refresh)
        logger_service.log_event(
            "INFO",
            "ai_career.pipeline",
            "generate_document_demo_done",
            kind=kind,
            chars=len(demo_body),
        )
        return PipelineResult(ok=True)

    if kind == DOC_EVIDENCE:
        text = build_evidence_document(output_lang=output_lang)
        if not text:
            return _set_error("No evidence available - load GitHub data first.")
        STATE.documents[DOC_EVIDENCE] = text
        if not keep_activity:
            _set_activity("ready")
        if refresh_ui:
            REFS.request_context_refresh()
            REFS.dispatch(_request_full_refresh)
        logger_service.log_event(
            "INFO",
            "ai_career.pipeline",
            "generate_document_done",
            kind=kind,
            chars=len(text),
        )
        return PipelineResult(ok=True)

    if kind == DOC_MODERN_CV:
        # Modern CV is structured JSON + custom renderer (teal sidebar
        # layout); the markdown-document path doesn't apply here.
        return generate_modern_cv_data(
            output_lang=output_lang,
            refresh_ui=refresh_ui,
            keep_activity=keep_activity,
        )

    if kind not in _DOC_SYSTEM_BY_KIND:
        return _set_error(f"Unknown document kind: {kind}")
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
        logger_service.log_exception(
            "ai_career.pipeline",
            "generate_document_provider_error",
            exc,
            kind=kind,
        )
        return _set_error(str(exc))
    text = _clean_ai_text((result.text or "").strip())
    if not text:
        return _set_error("Provider returned an empty document.")
    STATE.documents[kind] = text
    if not keep_activity:
        _set_activity("ready")
    if refresh_ui:
        REFS.request_context_refresh()
        REFS.dispatch(_request_full_refresh)
    logger_service.log_event(
        "INFO",
        "ai_career.pipeline",
        "generate_document_done",
        kind=kind,
        chars=len(text),
    )
    return PipelineResult(ok=True)


# Step 5: refine an existing document ----------------------------------------


def refine_document(
    kind: str,
    *,
    output_lang: str,
    problems: list[str],
    refresh_ui: bool = True,
    keep_activity: bool = False,
) -> PipelineResult:
    logger_service.log_event(
        "INFO",
        "ai_career.pipeline",
        "refine_document_start",
        kind=kind,
        output_lang=output_lang,
        problems=len([p for p in problems if p.strip()]),
        demo_mode=STATE.demo_mode,
    )
    if STATE.demo_mode:
        # In demo mode we ignore the typed problems and re-seed the
        # curated doc so the user always sees the polished sample
        # instead of an awkward "refined" no-op.
        if kind == DOC_MODERN_CV:
            STATE.modern_cv_data = copy.deepcopy(career_data.DEMO_MODERN_CV_DATA)
        else:
            demo_body = career_data.DEMO_DOCUMENTS.get(kind, "")
            if demo_body:
                STATE.documents[kind] = demo_body
        if not keep_activity:
            _set_activity("ready")
        if refresh_ui:
            REFS.request_context_refresh()
            REFS.dispatch(_request_full_refresh)
        logger_service.log_event(
            "INFO", "ai_career.pipeline", "refine_document_demo_done",
            kind=kind,
        )
        return PipelineResult(ok=True)

    if kind == DOC_MODERN_CV:
        # Modern CV: regenerate the JSON payload from scratch with the
        # candidate's notes applied, then re-render. There is no
        # markdown body to patch in place.
        return refine_modern_cv(
            output_lang=output_lang,
            problems=problems,
            refresh_ui=refresh_ui,
            keep_activity=keep_activity,
        )

    if kind not in _DOC_SYSTEM_BY_KIND:
        return _set_error(f"Unknown document kind: {kind}")
    current = STATE.documents.get(kind, "")
    if not current:
        return _set_error("Generate the document before refining it.")
    cleaned_problems = [p for p in problems if p.strip()]

    _set_activity("generating")
    user = prompts.build_refine_user(
        output_lang=output_lang,
        document_kind=kind,
        document_text=current,
        problems=cleaned_problems,
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
        logger_service.log_exception(
            "ai_career.pipeline",
            "refine_document_provider_error",
            exc,
            kind=kind,
        )
        return _set_error(str(exc))
    text = _clean_ai_text((result.text or "").strip())
    if not text:
        return _set_error("Provider returned an empty refined document.")
    STATE.documents[kind] = text
    if not keep_activity:
        _set_activity("ready")
    if refresh_ui:
        REFS.request_context_refresh()
        REFS.dispatch(_request_full_refresh)
    logger_service.log_event(
        "INFO",
        "ai_career.pipeline",
        "refine_document_done",
        kind=kind,
        chars=len(text),
    )
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

    logger_service.log_event(
        "INFO",
        "ai_career.pipeline",
        "send_chat_start",
        output_lang=output_lang,
        chars=len(user_text),
        history=len(STATE.chat_messages),
        attachments=len(STATE.chat_attachments),
        demo_mode=STATE.demo_mode,
    )

    if STATE.demo_mode:
        # Templated demo answer. We do not hit the provider, but the
        # reply is shaped like a coach: 1-2 sentences acknowledging the
        # question + a generic next step grounded in the curated
        # persona, plus a reminder that demo mode is offline.
        reply_en = (
            "Demo mode is on, so I am not calling the provider - "
            "the answer below is canned for **Jana's** profile.\n\n"
            "About your question: based on Jana's TrustPay experience "
            "(Playwright + Pytest pyramid, CI runtime cut from 38 to "
            "14 minutes) I would emphasise the **leadership track "
            "record** and the **k6 spike plan** when answering. Turn "
            "off Demo data in the section ... menu to ask the real "
            "AI coach."
        )
        reply_cs = (
            "Demo režim je zapnutý, takže nevolám AI - odpověď je "
            "připravená pro **Janin profil**.\n\n"
            "K tvojí otázce: vzhledem k Janině práci v TrustPay "
            "(Playwright + Pytest pyramida, snížení CI z 38 na 14 "
            "minut) bych zdůraznil/a **vedení malého týmu** a "
            "připravený **k6 spike plán**. Pokud chceš odpověď od "
            "skutečné AI, vypni Demo data v menu ... v sekci."
        )
        reply = reply_cs if (output_lang or "").lower().startswith("cs") else reply_en
        logger_service.log_event(
            "INFO", "ai_career.pipeline", "send_chat_demo_done",
            reply_chars=len(reply),
        )
        return reply, ""

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
        logger_service.log_exception(
            "ai_career.pipeline", "send_chat_provider_error", exc
        )
        return "", str(exc)
    text = _clean_ai_text((result.text or "").strip())
    if not text:
        logger_service.log_event(
            "ERROR", "ai_career.pipeline", "send_chat_empty_response"
        )
        return "", "Provider returned an empty response."
    logger_service.log_event(
        "INFO",
        "ai_career.pipeline",
        "send_chat_done",
        reply_chars=len(text),
    )
    return text, ""


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


# Mock Interview --------------------------------------------------------------


def _interview_candidate_context() -> str:
    """Best-available candidate grounding for the interview prompt.

    Prefers the structured Candidate JSON (cheapest + richest); falls
    back to the raw resume / LinkedIn text when the user has not run the
    Form analysis yet. Returns ``""`` when there is nothing to ground on
    (the prompt then asks broader questions).
    """
    if STATE.candidate:
        try:
            return json.dumps(STATE.candidate, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            logger_service.log_exception(
                "ai_career.pipeline", "interview_candidate_json_failed", exc,
            )
    bits: list[str] = []
    if STATE.resume and STATE.resume.text:
        bits.append(STATE.resume.text)
    if STATE.linkedin and STATE.linkedin.text:
        bits.append("LinkedIn export:\n" + STATE.linkedin.text)
    return "\n\n".join(bits)


def _interview_job_context() -> str:
    if STATE.job_spec:
        try:
            return json.dumps(STATE.job_spec, ensure_ascii=False)
        except (TypeError, ValueError):
            pass
    return (STATE.job_text or "").strip()


def _interview_target_role() -> str:
    if STATE.target_role:
        return STATE.target_role
    if isinstance(STATE.job_spec, dict):
        title = (STATE.job_spec.get("title") or "").strip()
        if title:
            return title
    return ""


def _interview_transcript() -> list[dict]:
    """Map the stored interview messages into prompt-ready turns."""
    role_map = {"question": "interviewer", "answer": "candidate", "feedback": "coach"}
    out: list[dict] = []
    for msg in STATE.interview_messages:
        kind = msg.get("kind")
        role = role_map.get(kind)
        if role is None:
            continue
        if kind == "feedback":
            text = (msg.get("text") or "").strip()
            improved = (msg.get("improved") or "").strip()
            if improved:
                text = f"{text}\nModel answer: {improved}" if text else f"Model answer: {improved}"
        else:
            text = (msg.get("text") or "").strip()
        if not text:
            continue
        out.append({"role": role, "text": text})
    return out


def _demo_interview_turn(*, output_lang: str, is_opening: bool, question_count: int) -> dict:
    cs = (output_lang or "").lower().startswith("cs")
    if is_opening:
        return {
            "feedback": "", "strengths": [], "gaps": [], "improved_answer": "",
            "question_focus": "Behavioural - quality" if not cs else "Behaviorální - kvalita",
            "next_question": (
                "Tell me about a time you improved the reliability of a test suite. "
                "What was the situation and what did you do?"
                if not cs else
                "Popiš situaci, kdy jsi zlepšil/a spolehlivost testovací sady. "
                "Jaká byla situace a co jsi udělal/a?"
            ),
            "done": False,
        }
    done = question_count >= 5
    if cs:
        return {
            "feedback": "Demo režim: odpověď nevolá AI. Dobrý začátek, ale chybí měřitelný výsledek (R ze STAR).",
            "strengths": ["Jasně popsaná situace", "Konkrétní akce"],
            "gaps": ["Doplň měřitelný výsledek", "Zmiň dopad na tým"],
            "improved_answer": "V TrustPay jsem [insert metric] ... výsledkem bylo zkrácení CI z 38 na 14 minut.",
            "question_focus": "Technické - automatizace",
            "next_question": "" if done else "Jak bys navrhl/a strategii pro flaky testy?",
            "done": done,
        }
    return {
        "feedback": "Demo mode: no AI was called. Solid start, but the answer is missing a measurable Result (the R in STAR).",
        "strengths": ["Clear situation", "Concrete actions"],
        "gaps": ["Add a measurable result", "Mention the impact on the team"],
        "improved_answer": "At TrustPay I [insert metric] ... which cut CI runtime from 38 to 14 minutes.",
        "question_focus": "Technical - automation",
        "next_question": "" if done else "How would you design a strategy for flaky tests?",
        "done": done,
    }


def interview_turn(
    *,
    output_lang: str,
    candidate_answer: str,
    is_opening: bool,
) -> tuple[dict, str]:
    """Run one Mock Interview turn.

    Returns ``(turn, error)``. ``turn`` is the structured InterviewTurn
    dict (feedback / strengths / gaps / improved_answer / next_question /
    question_focus / done). On failure ``turn`` is ``{}`` and ``error`` is
    a human-readable message the caller renders in-place.
    """
    question_count = sum(1 for m in STATE.interview_messages if m.get("kind") == "question")
    logger_service.log_event(
        "INFO", "ai_career.pipeline", "interview_turn_start",
        output_lang=output_lang, is_opening=is_opening,
        questions_so_far=question_count, demo_mode=STATE.demo_mode,
    )

    if STATE.demo_mode:
        turn = _demo_interview_turn(
            output_lang=output_lang, is_opening=is_opening, question_count=question_count,
        )
        logger_service.log_event(
            "INFO", "ai_career.pipeline", "interview_turn_demo_done",
            done=turn.get("done"),
        )
        return turn, ""

    user = prompts.build_interview_user(
        output_lang=output_lang,
        target_role=_interview_target_role(),
        candidate_context=_interview_candidate_context(),
        job_context=_interview_job_context(),
        transcript=_interview_transcript(),
        candidate_answer=candidate_answer,
        is_opening=is_opening,
    )
    try:
        result = ai_provider.run(
            system=prompts.INTERVIEW_SYSTEM,
            user=user,
            schema=schema.INTERVIEW_TURN_SCHEMA,
            schema_name="interview_turn",
            max_output_tokens=900,
            temperature=0.5,
        )
    except ai_provider.ProviderError as exc:
        logger_service.log_exception(
            "ai_career.pipeline", "interview_turn_provider_error", exc,
        )
        return {}, str(exc)
    except Exception as exc:
        logger_service.log_exception(
            "ai_career.pipeline", "interview_turn_unexpected_error", exc,
        )
        return {}, str(exc) or "unexpected error"

    payload = result.data if isinstance(result.data, dict) else {}
    if not payload:
        logger_service.log_event(
            "ERROR", "ai_career.pipeline", "interview_turn_empty_response",
        )
        return {}, "Provider returned an empty response."

    turn = {
        "feedback": _clean_ai_text((payload.get("feedback") or "").strip()),
        "strengths": [str(x).strip() for x in (payload.get("strengths") or []) if str(x).strip()][:4],
        "gaps": [str(x).strip() for x in (payload.get("gaps") or []) if str(x).strip()][:4],
        "improved_answer": _clean_ai_text((payload.get("improved_answer") or "").strip()),
        "next_question": _clean_ai_text((payload.get("next_question") or "").strip()),
        "question_focus": (payload.get("question_focus") or "").strip(),
        "done": bool(payload.get("done")),
    }
    logger_service.log_event(
        "INFO", "ai_career.pipeline", "interview_turn_done",
        done=turn["done"], has_question=bool(turn["next_question"]),
        feedback_chars=len(turn["feedback"]),
    )
    return turn, ""


def append_interview_message(kind: str, **fields) -> None:
    """Append a turn to the in-memory interview transcript."""
    entry = {"kind": kind, "time": datetime.now().strftime("%H:%M")}
    entry.update(fields)
    STATE.interview_messages.append(entry)


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


def _candidate_contact_for_cover_letter() -> tuple[str, dict]:
    """Pull the candidate name + contact bag for the Cover Letter banner.

    Prefers the Modern CV payload (canonical, hand-curated by the LLM
    from the candidate JSON) then falls back to the candidate JSON
    directly when the Modern CV step has not been run.
    """
    name = ""
    contact: dict[str, str] = {}
    if isinstance(STATE.modern_cv_data, dict):
        name = str(STATE.modern_cv_data.get("full_name") or "")
        cd = STATE.modern_cv_data.get("contact") or {}
        if isinstance(cd, dict):
            contact = {
                "location": str(cd.get("location") or ""),
                "email": str(cd.get("email") or ""),
                "phone": str(cd.get("phone") or ""),
            }
    if not name and isinstance(STATE.candidate, dict):
        name = str(STATE.candidate.get("full_name") or "")
        if not contact:
            cd = STATE.candidate.get("contact") or {}
            if isinstance(cd, dict):
                contact = {
                    "location": str(cd.get("location") or ""),
                    "email": str(cd.get("email") or ""),
                    "phone": str(cd.get("phone") or ""),
                }
    return name, contact


def _export_cover_letter(
    body_text: str,
    target: Path,
    *,
    theme: themes.ResumeTheme,
    output_lang: str,
) -> Path:
    """Write the Cover Letter HTML + PDF using the active palette.

    Imports the html_pdf service lazily so the rest of the pipeline
    keeps working when Playwright is missing (in that case the caller
    catches the exception and falls back to the legacy reportlab
    renderer).
    """
    from src.services import html_pdf

    name, contact = _candidate_contact_for_cover_letter()
    cover_html = themes.render_cover_letter_html(
        body_text,
        candidate_name=name,
        candidate_contact=contact,
        theme=theme,
        output_lang=output_lang,
    )
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    html_target = target.with_suffix(".html")
    try:
        html_target.write_text(cover_html, encoding="utf-8")
    except Exception as exc:
        logger_service.log_exception(
            "ai_career.pipeline", "export_cover_letter_html_write_failed", exc,
            target=str(html_target),
        )

    try:
        html_pdf.render_html_to_pdf(cover_html, target)
    except html_pdf.PdfRendererUnavailableError as exc:
        raise RuntimeError(
            "Playwright PDF export is unavailable on this machine. "
            "Install Google Chrome / Microsoft Edge or run "
            "`playwright install chromium` to enable PDF export. "
            f"({exc})"
        ) from exc
    return target


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

    Each call rolls a **fresh** run folder under ``outputs/`` even if a
    previous save just happened: the user expects two clicks of "Save
    complete analysis" to produce two timestamped snapshots, not a
    silent overwrite. ``store.new_run_dir`` already disambiguates
    same-second collisions with a numeric suffix (``-2``, ``-3``, ...).
    Per-document export buttons in :mod:`src.sections.ai_career.tab_documents`
    keep coalescing into the same run folder via ``_ensure_run_folder``,
    so individual MD/PDF exports of the same analysis still land in one
    place.
    """
    if not STATE.documents and not STATE.modern_cv_data:
        logger_service.log_event(
            "WARNING", "ai_career.pipeline", "save_full_no_documents"
        )
        return SaveResult(ok=False, error="no_documents")

    role = ""
    company = ""
    if STATE.job_spec:
        role = str(STATE.job_spec.get("title") or "")
        company = str(STATE.job_spec.get("company") or "")
    folder_path = Path(store.new_run_dir(role or "ai-career-run", company, section="ai_career"))
    STATE.last_run_folder = str(folder_path)
    logger_service.log_event(
        "INFO",
        "ai_career.pipeline",
        "save_full_start",
        folder=str(folder_path),
        role=role,
        documents=len(STATE.documents),
        has_modern_cv=bool(STATE.modern_cv_data),
    )

    output_lang = (STATE.document_output_lang or "en").strip().lower() or "en"
    theme_state = STATE.modern_cv_theme or {}
    active_theme = themes.resolve_theme(
        theme_state.get("palette"), theme_state.get("layout")
    )

    for kind, body_text in STATE.documents.items():
        if not body_text:
            continue
        formats = _EXPORT_PLAN.get(kind, ("md", "pdf"))
        basename = _DOC_FILE_BASENAMES.get(kind, kind)
        title = basename.replace("_", " ")
        style = "modern" if kind in _MODERN_STYLE_DOCS else "ats"

        # Cover letter goes through the themed HTML -> Playwright path
        # so the printed PDF picks up the user's chosen palette
        # (matching the Modern CV side panel) instead of the legacy
        # mono-grey reportlab template.
        if kind == DOC_COVER_LETTER:
            cover_lang = output_lang
            try:
                _export_cover_letter(
                    body_text,
                    folder_path / f"{basename}.pdf",
                    theme=active_theme,
                    output_lang=cover_lang,
                )
            except Exception as exc:
                # Fall back to the legacy renderer if Playwright is not
                # reachable. The user still gets a PDF; it just won't
                # carry the chosen accent colour.
                logger_service.log_exception(
                    "ai_career.pipeline",
                    "save_full_cover_letter_themed_failed",
                    exc,
                    folder=str(folder_path),
                )
                try:
                    exporter.export_pdf(
                        body_text,
                        folder_path / f"{basename}.pdf",
                        title=title,
                        style=style,
                    )
                except RuntimeError as exc2:
                    logger_service.log_exception(
                        "ai_career.pipeline",
                        "save_full_cover_letter_fallback_failed",
                        exc2,
                        folder=str(folder_path),
                    )
            continue

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
            except RuntimeError as exc:
                # Optional dep (e.g. python-docx) is missing on this
                # machine. Skip this format and keep going - log the
                # specific format so the user can install the
                # dependency if they want that output.
                logger_service.log_event(
                    "WARNING",
                    "ai_career.pipeline",
                    "save_full_format_unavailable",
                    kind=kind,
                    fmt=fmt,
                    error=str(exc),
                )
                continue

    # Modern CV - structured payload + custom two-column renderer.
    if STATE.modern_cv_data:
        basename = _DOC_FILE_BASENAMES.get(DOC_MODERN_CV, "Modern_CV")
        try:
            (folder_path / f"{basename}.html").write_text(
                modern_cv_render.render_html(
                    STATE.modern_cv_data, output_lang=output_lang
                ),
                encoding="utf-8",
            )
        except Exception as exc:
            logger_service.log_exception(
                "ai_career.pipeline", "save_full_modern_cv_html_failed", exc,
                folder=str(folder_path),
            )
        try:
            modern_cv_render.render_pdf(
                STATE.modern_cv_data,
                folder_path / f"{basename}.pdf",
                output_lang=output_lang,
            )
        except Exception as exc:
            logger_service.log_exception(
                "ai_career.pipeline", "save_full_modern_cv_pdf_failed", exc,
                folder=str(folder_path),
            )
        try:
            import json as _json

            (folder_path / f"{basename}.json").write_text(
                _json.dumps(STATE.modern_cv_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            logger_service.log_exception(
                "ai_career.pipeline", "save_full_modern_cv_json_failed", exc,
                folder=str(folder_path),
            )

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
                "modern_cv_theme": {
                    "palette": active_theme.palette_slug,
                    "layout": active_theme.layout_slug,
                },
                "cost": {
                    "calls": COST.calls,
                    "tokens": COST.tokens_total,
                    "usd": COST.cost_usd,
                },
            },
        )
    except Exception as exc:
        logger_service.log_exception(
            "ai_career.pipeline", "save_full_summary_json_failed", exc,
            folder=str(folder_path),
        )

    # Rich one-pager summary - assembled deterministically from the
    # already-cached match analysis + tailored CV + cover letter so the
    # user gets the entire application packet (match report, CV, cover
    # letter, interview prep, skill gap plan) in one HTML file. No
    # extra LLM calls.
    try:
        from datetime import datetime as _dt

        summary_html = exporter.build_summary_html(
            candidate=candidate,
            job_spec=job_spec,
            match=match,
            theme=active_theme,
            output_lang=output_lang,
            documents=dict(STATE.documents),
            timestamp=_dt.now().strftime("%Y-%m-%d %H:%M"),
        )
        (folder_path / "summary.html").write_text(summary_html, encoding="utf-8")
    except Exception as exc:
        logger_service.log_exception(
            "ai_career.pipeline", "save_full_summary_html_failed", exc,
            folder=str(folder_path),
        )

    try:
        from datetime import datetime

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
            provider="",
            model="",
            cost_usd=float(COST.cost_usd),
            docs=docs_list,
            note="ai_career",
        )
        store.append_run(summary)
    except Exception as exc:
        logger_service.log_exception(
            "ai_career.pipeline", "save_full_history_append", exc
        )

    logger_service.log_event(
        "INFO",
        "ai_career.pipeline",
        "save_full_done",
        folder=str(folder_path),
    )
    return SaveResult(ok=True, folder=str(folder_path))


# Combined "Run analysis" entry point ----------------------------------------


@logger_service.timed_call("ai_career.pipeline", "run_full_analysis")
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

    Wrapped in :func:`timed_call` so the debug log shows
    ``run_full_analysis_start`` / ``..._done`` with ``elapsed_ms`` -
    handy when the user complains that "Run analysis" felt slow.
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
    REFS.request_context_refresh()
    logger_service.log_state(
        "ai_career.pipeline", "run_full_analysis_state",
        activity=STATE.activity,
        has_candidate=bool(STATE.candidate),
        has_job_spec=bool(STATE.job_spec),
        has_match=bool(STATE.match),
    )
    return PipelineResult(ok=True)

