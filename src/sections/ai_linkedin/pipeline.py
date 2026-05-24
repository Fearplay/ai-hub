"""Orchestration for the AI LinkedIn section.

The pipeline mirrors the structure used by :mod:`src.sections.ai_career.pipeline`
but speaks the LinkedIn voice: the first call extracts a normalised
LinkedIn profile JSON; every subsequent generator (headlines, about,
experience rewrite, skills buckets, featured, projects, services,
courses, recommendation requests, posts) consumes that JSON instead of
re-sending the raw resume / GitHub text - the main cost saver.

Three deterministic helpers (``build_completeness_checklist``,
``build_unsupported_claims_report``, ``compute_profile_score``) run on
top of the cached state without calling any provider, so the user gets
a profile-completeness verdict + an honest score for free.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from src.services import ai_provider, exporter, github_client, store
from src.services import logger as logger_service
from src.services.cost_tracker import COST
from src.sections.ai_linkedin import data as linkedin_data
from src.sections.ai_linkedin import prompts, schema, summary_html
from src.sections.ai_linkedin.refs import REFS, safe
from src.sections.ai_linkedin.state import (
    AUDIENCE_RECRUITER,
    DEFAULT_SECTIONS,
    POST_KINDS,
    POST_LEARNING_UPDATE,
    POST_PROJECT_LAUNCH,
    SEC_ABOUT,
    SEC_CERTIFICATIONS,
    SEC_CHECKLIST,
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
    TONE_PROFESSIONAL,
    ChatMessage,
)


# Public types ----------------------------------------------------------------


@dataclass
class PipelineResult:
    ok: bool
    error: str = ""


@dataclass
class SaveResult:
    ok: bool
    folder: str = ""
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
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.pipeline", "request_full_refresh_import", exc,
        )
        return
    request_section_refresh()


def _set_activity(value: str) -> None:
    """Update the right-hand activity badge from any thread.

    Routed through :meth:`REFS.request_context_refresh` so background
    workers can repaint the activity label without the user having to
    poke the window. See the matching helper in
    ``src.sections.ai_career.pipeline._set_activity`` for the rationale.
    """
    prev = STATE.activity
    STATE.activity = value
    if prev != value:
        logger_service.log_event(
            "INFO",
            "ai_linkedin.pipeline",
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
        "ERROR", "ai_linkedin.pipeline", "set_error", message=message,
    )
    return PipelineResult(ok=False, error=message)


# Demo seed -------------------------------------------------------------------


def load_demo() -> None:
    """Populate ``STATE`` with curated mock data, no AI calls.

    Called by the ``...`` header menu's "Show demo data" item. Copies
    the constants from :mod:`src.sections.ai_linkedin.data` so the
    user can explore every Output card without spending tokens. All
    AI-calling functions also check ``STATE.demo_mode`` and reseed the
    payload defensively, so even if the user kicks "Run profile build"
    while demo is on no provider call leaves the process.
    """
    logger_service.log_event(
        "INFO", "ai_linkedin.pipeline", "load_demo_start"
    )
    STATE.demo_mode = True
    STATE.target_roles = list(linkedin_data.DEMO_TARGET_ROLES)
    STATE.extracted_profile = copy.deepcopy(linkedin_data.DEMO_PROFILE)
    STATE.headlines = copy.deepcopy(linkedin_data.DEMO_HEADLINES)
    STATE.about_variants = copy.deepcopy(linkedin_data.DEMO_ABOUT)
    STATE.experience_rewrites = copy.deepcopy(linkedin_data.DEMO_EXPERIENCE_REWRITES)
    STATE.skills_buckets = copy.deepcopy(linkedin_data.DEMO_SKILLS_BUCKETS)
    STATE.featured = copy.deepcopy(linkedin_data.DEMO_FEATURED)
    STATE.projects = copy.deepcopy(linkedin_data.DEMO_PROJECTS)
    STATE.recommendation_messages = copy.deepcopy(
        linkedin_data.DEMO_RECOMMENDATION_MESSAGES
    )
    STATE.posts = copy.deepcopy(linkedin_data.DEMO_POSTS)
    STATE.completeness = copy.deepcopy(linkedin_data.DEMO_COMPLETENESS)
    STATE.unsupported_claims = copy.deepcopy(linkedin_data.DEMO_UNSUPPORTED_CLAIMS)
    STATE.profile_score = copy.deepcopy(linkedin_data.DEMO_PROFILE_SCORE)
    STATE.followup_questions = []
    STATE.followup_qa = []
    STATE.activity = "ready"
    STATE.last_error = ""
    STATE.run_stage = ""
    REFS.request_context_refresh()
    logger_service.log_state(
        "ai_linkedin.pipeline", "load_demo_state",
        has_profile=True,
        sections=8,
        score=STATE.profile_score.get("overall_score") if STATE.profile_score else None,
    )


def clear_demo() -> None:
    """Turn demo mode off and wipe the seeded payloads.

    Pairs with :func:`load_demo`. Resets every AI-derived field so the
    user starts from a clean Setup tab the next time they open the
    section, without leaking the curated Jana persona into a real run.
    """
    logger_service.log_event(
        "INFO", "ai_linkedin.pipeline", "clear_demo_start"
    )
    STATE.demo_mode = False
    STATE.reset_run()
    REFS.request_context_refresh()


def _resolve_targeting() -> tuple[list[str], str, str]:
    target_roles = [r for r in (STATE.target_roles or []) if r and r.strip()]
    audience = STATE.audience or AUDIENCE_RECRUITER
    tone = STATE.tone or TONE_PROFESSIONAL
    return target_roles, audience, tone


def _resolve_output_lang(lang: str) -> str:
    return (lang or "en").strip().lower() or "en"


# --- Step 0: input gathering -------------------------------------------------


def fetch_github_profile(value: str):
    """Best-effort GitHub fetch. Activity always returns to ``"ready"``."""
    if not value.strip():
        return None
    _set_activity("scraping")
    try:
        profile = github_client.fetch_profile(value)
    finally:
        _set_activity("ready")
    return profile


def _build_github_summary() -> str:
    if STATE.github_skip:
        return ""
    return prompts.serialize_github_summary(STATE.github_profile)


# --- Step 1: profile extraction ---------------------------------------------


def extract_profile(*, output_lang: str) -> PipelineResult:
    """Normalise resume + LinkedIn export + GitHub into a single JSON.

    The downstream generators (headlines / about / experience rewrite /
    skills / …) all read this JSON instead of re-sending raw text -
    that is the main cost saver.
    """
    output_lang = _resolve_output_lang(output_lang)
    target_roles, audience, tone = _resolve_targeting()

    logger_service.log_event(
        "INFO",
        "ai_linkedin.pipeline",
        "extract_profile_start",
        output_lang=output_lang,
        target_roles=len(target_roles),
        has_resume=bool(STATE.resume and STATE.resume.text),
        has_linkedin=bool(STATE.linkedin_export and STATE.linkedin_export.text),
        has_github=bool(STATE.github_profile),
        has_notes=bool(STATE.notes),
        demo_mode=STATE.demo_mode,
    )

    if STATE.demo_mode:
        STATE.extracted_profile = copy.deepcopy(linkedin_data.DEMO_PROFILE)
        STATE.evidence_index = _build_evidence_index_from_profile(
            STATE.extracted_profile
        )
        _set_activity("ready")
        logger_service.log_event(
            "INFO", "ai_linkedin.pipeline", "extract_profile_demo_done"
        )
        return PipelineResult(ok=True)

    if not (
        (STATE.resume and STATE.resume.text)
        or (STATE.linkedin_export and STATE.linkedin_export.text)
        or STATE.notes.strip()
    ):
        return _set_error(
            "Add a CV, a LinkedIn export or paste some notes before"
            " running the profile build."
        )

    _set_activity("extracting")
    user = prompts.build_profile_extract_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        resume_text=(STATE.resume.text if STATE.resume else ""),
        linkedin_text=(STATE.linkedin_export.text if STATE.linkedin_export else ""),
        github_summary=_build_github_summary(),
        notes=STATE.notes,
    )
    try:
        result = ai_provider.run(
            system=prompts.PROFILE_EXTRACT_SYSTEM,
            user=user,
            schema=schema.PROFILE_EXTRACT_SCHEMA,
            schema_name="linkedin_profile",
            max_output_tokens=4500,
        )
    except ai_provider.ProviderError as exc:
        logger_service.log_exception(
            "ai_linkedin.pipeline", "extract_profile_provider_error", exc,
        )
        return _set_error(str(exc))

    if not isinstance(result.data, dict):
        return _set_error("Provider did not return a profile JSON.")

    STATE.extracted_profile = result.data
    STATE.evidence_index = _build_evidence_index_from_profile(result.data)
    logger_service.log_event(
        "INFO",
        "ai_linkedin.pipeline",
        "extract_profile_done",
        skills=len(result.data.get("skills") or []),
        roles=len(result.data.get("experiences") or []),
    )
    return PipelineResult(ok=True)


def _build_evidence_index_from_profile(profile: dict) -> dict[str, list[str]]:
    """Bucket the profile into ``{evidence_anchor: [skill, ...]}``.

    Used by :func:`compute_profile_score` and the unsupported-claims
    report so the deterministic helpers don't need to walk the profile
    JSON over and over.
    """
    index: dict[str, list[str]] = {
        "resume": [],
        "linkedin_export": [],
        "github": [],
        "user_confirmed": [],
        "missing_evidence": [],
    }
    for skill in profile.get("skills") or []:
        if not isinstance(skill, dict):
            continue
        anchor = (skill.get("evidence_anchor") or "missing_evidence").strip()
        if anchor not in index:
            index[anchor] = []
        index[anchor].append(str(skill.get("name") or "").strip())
    return index


# --- Step 2: optional clarifying questions ----------------------------------


def generate_followup_questions(*, output_lang: str) -> PipelineResult:
    """Ask the LLM to surface profile gaps the candidate should clarify."""
    output_lang = _resolve_output_lang(output_lang)
    target_roles, audience, tone = _resolve_targeting()

    if STATE.demo_mode:
        # Demo persona's profile is already complete - no follow-ups
        # are needed, matching what a real perfect-fit run returns.
        STATE.followup_questions = []
        _set_activity("ready")
        logger_service.log_event(
            "INFO", "ai_linkedin.pipeline", "generate_followups_demo_done"
        )
        return PipelineResult(ok=True)

    if not STATE.extracted_profile:
        return _set_error("Extract the profile first.")

    _set_activity("analyzing")
    user = prompts.build_followup_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=STATE.extracted_profile,
    )
    try:
        result = ai_provider.run(
            system=prompts.FOLLOWUP_QUESTIONS_SYSTEM,
            user=user,
            schema=schema.CLARIFY_SCHEMA,
            schema_name="clarifying_questions",
            max_output_tokens=1200,
        )
    except ai_provider.ProviderError as exc:
        logger_service.log_exception(
            "ai_linkedin.pipeline", "generate_followups_provider_error", exc,
        )
        return _set_error(str(exc))
    if not isinstance(result.data, dict):
        return _set_error("Provider did not return a clarifying-questions JSON.")

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
    logger_service.log_event(
        "INFO",
        "ai_linkedin.pipeline",
        "generate_followups_done",
        questions=len(cleaned),
    )
    return PipelineResult(ok=True)


# --- Step 3: per-section generators -----------------------------------------


def _ensure_profile() -> Optional[PipelineResult]:
    if not STATE.extracted_profile:
        return _set_error("Extract the profile first.")
    return None


_DEMO_STATE_PAYLOADS: dict[str, str] = {
    "headlines": "DEMO_HEADLINES",
    "about_variants": "DEMO_ABOUT",
    "experience_rewrites": "DEMO_EXPERIENCE_REWRITES",
    "skills_buckets": "DEMO_SKILLS_BUCKETS",
    "featured": "DEMO_FEATURED",
    "projects": "DEMO_PROJECTS",
    "recommendation_messages": "DEMO_RECOMMENDATION_MESSAGES",
    "posts": "DEMO_POSTS",
}


def _generate_with_schema(
    *,
    section_id: str,
    system: str,
    user: str,
    section_schema: dict,
    schema_name: str,
    max_output_tokens: int = 2400,
    state_attr: str,
) -> PipelineResult:
    """Shared helper: log start, call provider, store result, log done."""
    logger_service.log_event(
        "INFO",
        "ai_linkedin.pipeline",
        "generate_section_start",
        section=section_id,
        demo_mode=STATE.demo_mode,
    )

    if STATE.demo_mode:
        # Reseed the curated payload for this section instead of
        # calling the provider. Sections that have no curated demo
        # constant (education / certifications / services / courses)
        # leave their existing value untouched, which is exactly what
        # the Output card expects (it just skips the missing card).
        const_name = _DEMO_STATE_PAYLOADS.get(state_attr)
        if const_name is not None:
            setattr(STATE, state_attr, copy.deepcopy(getattr(linkedin_data, const_name)))
        _set_activity("ready")
        logger_service.log_event(
            "INFO",
            "ai_linkedin.pipeline",
            "generate_section_demo_done",
            section=section_id,
            state_attr=state_attr,
        )
        return PipelineResult(ok=True)

    err = _ensure_profile()
    if err is not None:
        return err

    _set_activity("generating")
    try:
        result = ai_provider.run(
            system=system,
            user=user,
            schema=section_schema,
            schema_name=schema_name,
            max_output_tokens=max_output_tokens,
        )
    except ai_provider.ProviderError as exc:
        logger_service.log_exception(
            "ai_linkedin.pipeline",
            "generate_section_provider_error",
            exc,
            section=section_id,
        )
        return _set_error(str(exc))
    if not isinstance(result.data, dict):
        return _set_error(f"Provider did not return JSON for {section_id}.")
    setattr(STATE, state_attr, result.data)
    logger_service.log_event(
        "INFO",
        "ai_linkedin.pipeline",
        "generate_section_done",
        section=section_id,
        chars=len(json.dumps(result.data, ensure_ascii=False)),
    )
    return PipelineResult(ok=True)


def generate_headlines(*, output_lang: str) -> PipelineResult:
    output_lang = _resolve_output_lang(output_lang)
    target_roles, audience, tone = _resolve_targeting()
    user = prompts.build_headlines_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=STATE.extracted_profile,
    )
    return _generate_with_schema(
        section_id=SEC_HEADLINE,
        system=prompts.HEADLINES_SYSTEM,
        user=user,
        section_schema=schema.HEADLINES_SCHEMA,
        schema_name="linkedin_headlines",
        max_output_tokens=1500,
        state_attr="headlines",
    )


def generate_about(*, output_lang: str) -> PipelineResult:
    output_lang = _resolve_output_lang(output_lang)
    target_roles, audience, tone = _resolve_targeting()
    user = prompts.build_about_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=STATE.extracted_profile,
    )
    return _generate_with_schema(
        section_id=SEC_ABOUT,
        system=prompts.ABOUT_SYSTEM,
        user=user,
        section_schema=schema.ABOUT_SCHEMA,
        schema_name="linkedin_about",
        max_output_tokens=3500,
        state_attr="about_variants",
    )


def generate_experience_rewrites(*, output_lang: str) -> PipelineResult:
    output_lang = _resolve_output_lang(output_lang)
    target_roles, audience, tone = _resolve_targeting()
    user = prompts.build_experience_rewrite_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=STATE.extracted_profile,
    )
    return _generate_with_schema(
        section_id=SEC_EXPERIENCE,
        system=prompts.EXPERIENCE_REWRITE_SYSTEM,
        user=user,
        section_schema=schema.EXPERIENCE_REWRITE_SCHEMA,
        schema_name="linkedin_experience_rewrite",
        max_output_tokens=4500,
        state_attr="experience_rewrites",
    )


def generate_education_rewrites(*, output_lang: str) -> PipelineResult:
    output_lang = _resolve_output_lang(output_lang)
    target_roles, audience, tone = _resolve_targeting()
    user = prompts.build_education_rewrite_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=STATE.extracted_profile,
    )
    return _generate_with_schema(
        section_id=SEC_EDUCATION,
        system=prompts.EDUCATION_REWRITE_SYSTEM,
        user=user,
        section_schema=schema.EDUCATION_REWRITE_SCHEMA,
        schema_name="linkedin_education_rewrite",
        max_output_tokens=2500,
        state_attr="education_rewrites",
    )


def generate_certifications(*, output_lang: str) -> PipelineResult:
    output_lang = _resolve_output_lang(output_lang)
    target_roles, audience, tone = _resolve_targeting()
    user = prompts.build_certifications_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=STATE.extracted_profile,
    )
    return _generate_with_schema(
        section_id=SEC_CERTIFICATIONS,
        system=prompts.CERTIFICATIONS_REWRITE_SYSTEM,
        user=user,
        section_schema=schema.CERTIFICATIONS_SCHEMA,
        schema_name="linkedin_certifications",
        max_output_tokens=2500,
        state_attr="certifications_rewrites",
    )


def generate_skills_buckets(*, output_lang: str) -> PipelineResult:
    output_lang = _resolve_output_lang(output_lang)
    target_roles, audience, tone = _resolve_targeting()
    user = prompts.build_skills_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=STATE.extracted_profile,
    )
    return _generate_with_schema(
        section_id=SEC_SKILLS,
        system=prompts.SKILLS_SYSTEM,
        user=user,
        section_schema=schema.SKILLS_SCHEMA,
        schema_name="linkedin_skills",
        max_output_tokens=3500,
        state_attr="skills_buckets",
    )


def generate_featured(*, output_lang: str) -> PipelineResult:
    output_lang = _resolve_output_lang(output_lang)
    target_roles, audience, tone = _resolve_targeting()
    user = prompts.build_featured_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=STATE.extracted_profile,
    )
    return _generate_with_schema(
        section_id=SEC_FEATURED,
        system=prompts.FEATURED_SYSTEM,
        user=user,
        section_schema=schema.FEATURED_SCHEMA,
        schema_name="linkedin_featured",
        max_output_tokens=2500,
        state_attr="featured",
    )


def generate_projects(*, output_lang: str) -> PipelineResult:
    output_lang = _resolve_output_lang(output_lang)
    target_roles, audience, tone = _resolve_targeting()
    user = prompts.build_projects_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=STATE.extracted_profile,
    )
    return _generate_with_schema(
        section_id=SEC_PROJECTS,
        system=prompts.PROJECTS_SYSTEM,
        user=user,
        section_schema=schema.PROJECTS_SCHEMA,
        schema_name="linkedin_projects",
        max_output_tokens=3000,
        state_attr="projects",
    )


def generate_services(*, output_lang: str, opt_in: bool = False) -> PipelineResult:
    output_lang = _resolve_output_lang(output_lang)
    target_roles, audience, tone = _resolve_targeting()
    user = prompts.build_services_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=STATE.extracted_profile,
        opt_in=opt_in,
    )
    return _generate_with_schema(
        section_id=SEC_SERVICES,
        system=prompts.SERVICES_SYSTEM,
        user=user,
        section_schema=schema.SERVICES_SCHEMA,
        schema_name="linkedin_services",
        max_output_tokens=2000,
        state_attr="services",
    )


def generate_courses(*, output_lang: str) -> PipelineResult:
    output_lang = _resolve_output_lang(output_lang)
    target_roles, audience, tone = _resolve_targeting()
    user = prompts.build_courses_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=STATE.extracted_profile,
    )
    return _generate_with_schema(
        section_id=SEC_COURSES,
        system=prompts.COURSES_SYSTEM,
        user=user,
        section_schema=schema.COURSES_SCHEMA,
        schema_name="linkedin_courses",
        max_output_tokens=2000,
        state_attr="courses",
    )


def generate_recommendation_messages(*, output_lang: str) -> PipelineResult:
    output_lang = _resolve_output_lang(output_lang)
    target_roles, audience, tone = _resolve_targeting()
    user = prompts.build_recommendations_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=STATE.extracted_profile,
    )
    return _generate_with_schema(
        section_id=SEC_RECOMMENDATIONS,
        system=prompts.RECOMMENDATION_REQUEST_SYSTEM,
        user=user,
        section_schema=schema.RECOMMENDATIONS_SCHEMA,
        schema_name="linkedin_recommendations",
        max_output_tokens=2000,
        state_attr="recommendation_messages",
    )


def generate_posts(
    *, output_lang: str, post_kinds: Optional[list[str]] = None
) -> PipelineResult:
    output_lang = _resolve_output_lang(output_lang)
    target_roles, audience, tone = _resolve_targeting()
    kinds = list(post_kinds) if post_kinds else list(STATE.selected_post_kinds)
    if not kinds:
        kinds = [POST_LEARNING_UPDATE, POST_PROJECT_LAUNCH]
    kinds = [k for k in kinds if k in POST_KINDS]
    user = prompts.build_posts_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=STATE.extracted_profile,
        post_kinds=kinds,
    )
    return _generate_with_schema(
        section_id=SEC_POSTS,
        system=prompts.POSTS_SYSTEM,
        user=user,
        section_schema=schema.POSTS_SCHEMA,
        schema_name="linkedin_posts",
        max_output_tokens=3500,
        state_attr="posts",
    )


# --- Deterministic outputs (no LLM call) ------------------------------------


_PRIORITY_HIGH = "high"
_PRIORITY_MED = "medium"
_PRIORITY_LOW = "low"
_PRIORITY_SKIP = "skip"


def build_completeness_checklist() -> dict:
    """Compute a profile-completeness checklist purely from state."""
    profile = STATE.extracted_profile or {}
    items: list[dict] = []

    def add(key: str, label: str, priority: str, ok: bool, reason: str) -> None:
        items.append(
            {
                "key": key,
                "label": label,
                "priority": priority,
                "ok": bool(ok),
                "reason": reason,
            }
        )

    headlines_ok = bool(STATE.headlines and (STATE.headlines.get("variants") or []))
    add(
        SEC_HEADLINE,
        "Headline / motto",
        _PRIORITY_HIGH,
        headlines_ok,
        "Generate a recruiter-friendly headline." if not headlines_ok else "Headlines drafted.",
    )

    about_ok = bool(
        STATE.about_variants
        and (STATE.about_variants.get("medium_version") or "").strip()
    )
    add(
        SEC_ABOUT,
        "About / Intro",
        _PRIORITY_HIGH,
        about_ok,
        "Generate an About section in your tone." if not about_ok else "About section drafted.",
    )

    exp_ok = bool(
        STATE.experience_rewrites
        and (STATE.experience_rewrites.get("roles") or [])
    )
    add(
        SEC_EXPERIENCE,
        "Experience rewrite",
        _PRIORITY_HIGH,
        exp_ok,
        "Rewrite each role with bullets + skill tags." if not exp_ok else "Roles rewritten.",
    )

    skills_ok = bool(
        STATE.skills_buckets
        and (
            (STATE.skills_buckets.get("core") or [])
            or (STATE.skills_buckets.get("to_verify") or [])
        )
    )
    add(
        SEC_SKILLS,
        "Skills",
        _PRIORITY_HIGH,
        skills_ok,
        "Generate the 4-bucket skill plan." if not skills_ok else "Skills bucketed.",
    )

    featured_ok = bool(STATE.featured and (STATE.featured.get("items") or []))
    add(
        SEC_FEATURED,
        "Featured",
        _PRIORITY_MED,
        featured_ok,
        "Pick 3-5 portfolio-grade items." if not featured_ok else "Featured items proposed.",
    )

    projects_ok = bool(STATE.projects and (STATE.projects.get("projects") or []))
    add(
        SEC_PROJECTS,
        "Projects",
        _PRIORITY_MED,
        projects_ok,
        "Add LinkedIn projects with links." if not projects_ok else "Projects drafted.",
    )

    certs_ok = bool(
        STATE.certifications_rewrites
        and (STATE.certifications_rewrites.get("existing") or [])
    )
    has_certs_in_source = bool(profile.get("certifications"))
    if has_certs_in_source:
        add(
            SEC_CERTIFICATIONS,
            "Certifications",
            _PRIORITY_MED,
            certs_ok,
            "Rewrite cert descriptions." if not certs_ok else "Certifications rewritten.",
        )
    else:
        add(
            SEC_CERTIFICATIONS,
            "Certifications",
            _PRIORITY_SKIP,
            True,
            "No certifications in source - skip until you earn one.",
        )

    courses_ok = bool(
        STATE.courses
        and (
            (STATE.courses.get("existing") or [])
            or (STATE.courses.get("recommended") or [])
        )
    )
    add(
        SEC_COURSES,
        "Courses & training",
        _PRIORITY_LOW,
        courses_ok,
        "List courses or get a learning recommendation." if not courses_ok else "Courses listed.",
    )

    rec_ok = bool(
        STATE.recommendation_messages
        and (STATE.recommendation_messages.get("templates") or [])
    )
    add(
        SEC_RECOMMENDATIONS,
        "Request recommendations",
        _PRIORITY_MED,
        rec_ok,
        "Draft recommendation requests." if not rec_ok else "Templates drafted.",
    )

    posts_ok = bool(STATE.posts and (STATE.posts.get("posts") or []))
    add(
        SEC_POSTS,
        "Posts",
        _PRIORITY_MED,
        posts_ok,
        "Draft 1-2 posts to seed activity." if not posts_ok else "Posts drafted.",
    )

    services_ok = bool(STATE.services and (STATE.services.get("services") or []))
    add(
        SEC_SERVICES,
        "Services",
        _PRIORITY_LOW,
        services_ok,
        "Optional - only if you freelance." if not services_ok else "Services drafted.",
    )

    summary = {
        "items": items,
        "high_remaining": sum(
            1 for i in items if i["priority"] == _PRIORITY_HIGH and not i["ok"]
        ),
        "medium_remaining": sum(
            1 for i in items if i["priority"] == _PRIORITY_MED and not i["ok"]
        ),
        "low_remaining": sum(
            1 for i in items if i["priority"] == _PRIORITY_LOW and not i["ok"]
        ),
    }
    STATE.completeness = summary
    logger_service.log_event(
        "INFO",
        "ai_linkedin.pipeline",
        "completeness_built",
        items=len(items),
        high_left=summary["high_remaining"],
        medium_left=summary["medium_remaining"],
    )
    return summary


def build_unsupported_claims_report() -> dict:
    """Roll up every ``do_not_claim`` signal the AI surfaced."""
    rows: list[dict] = []

    profile = STATE.extracted_profile or {}
    for skill in profile.get("skills") or []:
        if not isinstance(skill, dict):
            continue
        if (skill.get("evidence_anchor") or "").strip() == "missing_evidence":
            rows.append(
                {
                    "kind": "skill_missing_evidence",
                    "label": str(skill.get("name") or ""),
                    "reason": "No evidence in your sources - confirm before claiming.",
                }
            )

    if STATE.experience_rewrites:
        for role in STATE.experience_rewrites.get("roles") or []:
            if not isinstance(role, dict):
                continue
            for note in role.get("do_not_claim") or []:
                if not str(note).strip():
                    continue
                rows.append(
                    {
                        "kind": "experience_filtered",
                        "label": str(role.get("role") or "")
                        + " @ "
                        + str(role.get("company") or ""),
                        "reason": str(note),
                    }
                )

    if STATE.skills_buckets:
        for skill in STATE.skills_buckets.get("do_not_claim") or []:
            if not isinstance(skill, dict):
                continue
            rows.append(
                {
                    "kind": "skill_do_not_claim",
                    "label": str(skill.get("name") or ""),
                    "reason": str(skill.get("reason") or ""),
                }
            )

    payload = {"rows": rows, "count": len(rows)}
    STATE.unsupported_claims = payload
    logger_service.log_event(
        "INFO",
        "ai_linkedin.pipeline",
        "unsupported_claims_built",
        rows=len(rows),
    )
    return payload


def compute_profile_score() -> dict:
    """Score 0-100 + a per-section breakdown.

    The score is deterministic: every section has a weight and a 0-1
    completion factor (set when the section was generated). The user
    sees the breakdown so they understand which 'unticks' would move
    the needle.
    """
    profile = STATE.extracted_profile or {}

    weights: list[tuple[str, str, int, float]] = []

    def coverage_for_skill_buckets() -> float:
        if not STATE.skills_buckets:
            return 0.0
        core = len(STATE.skills_buckets.get("core") or [])
        to_verify = len(STATE.skills_buckets.get("to_verify") or [])
        if core == 0:
            return 0.2 if to_verify else 0.0
        return min(1.0, 0.5 + 0.05 * core)

    headline_factor = 1.0 if STATE.headlines and (STATE.headlines.get("variants") or []) else 0.0
    about_factor = 1.0 if STATE.about_variants and (STATE.about_variants.get("medium_version") or "").strip() else 0.0
    exp_factor = 1.0 if STATE.experience_rewrites and (STATE.experience_rewrites.get("roles") or []) else 0.0
    skills_factor = coverage_for_skill_buckets()
    featured_factor = 1.0 if STATE.featured and (STATE.featured.get("items") or []) else 0.0
    projects_factor = 1.0 if STATE.projects and (STATE.projects.get("projects") or []) else 0.0
    certs_factor = 1.0 if profile.get("certifications") else 0.5
    posts_factor = 1.0 if STATE.posts and (STATE.posts.get("posts") or []) else 0.0
    languages_factor = 1.0 if profile.get("languages") else 0.0
    online_factor = 1.0 if profile.get("online_links") else 0.0

    weights = [
        (SEC_HEADLINE, "Headline", 12, headline_factor),
        (SEC_ABOUT, "About", 14, about_factor),
        (SEC_EXPERIENCE, "Experience", 18, exp_factor),
        (SEC_SKILLS, "Skills", 12, skills_factor),
        (SEC_FEATURED, "Featured", 10, featured_factor),
        (SEC_PROJECTS, "Projects", 8, projects_factor),
        (SEC_CERTIFICATIONS, "Certifications", 6, certs_factor),
        (SEC_POSTS, "Posts", 8, posts_factor),
        ("languages", "Languages", 6, languages_factor),
        ("online", "Online presence", 6, online_factor),
    ]

    breakdown: list[dict] = []
    score = 0.0
    for key, label, weight, factor in weights:
        contribution = weight * max(0.0, min(1.0, factor))
        score += contribution
        breakdown.append(
            {
                "key": key,
                "label": label,
                "weight": weight,
                "factor": round(factor, 2),
                "contribution": round(contribution, 1),
            }
        )

    payload = {
        "score": int(round(score)),
        "max": 100,
        "breakdown": breakdown,
    }
    STATE.profile_score = payload
    logger_service.log_event(
        "INFO",
        "ai_linkedin.pipeline",
        "profile_score_computed",
        score=payload["score"],
    )
    return payload


# --- Combined "Run profile build" entry point -------------------------------


_SECTION_RUNNERS: dict[str, Callable[..., PipelineResult]] = {
    SEC_HEADLINE: generate_headlines,
    SEC_ABOUT: generate_about,
    SEC_EXPERIENCE: generate_experience_rewrites,
    SEC_EDUCATION: generate_education_rewrites,
    SEC_CERTIFICATIONS: generate_certifications,
    SEC_SKILLS: generate_skills_buckets,
    SEC_FEATURED: generate_featured,
    SEC_PROJECTS: generate_projects,
    SEC_SERVICES: generate_services,
    SEC_COURSES: generate_courses,
    SEC_RECOMMENDATIONS: generate_recommendation_messages,
    SEC_POSTS: generate_posts,
}


@logger_service.timed_call("ai_linkedin.pipeline", "run_full_profile_build")
def run_full_profile_build(
    *,
    output_lang: str,
    selected_sections: Optional[set[str]] = None,
    on_step: Optional[Callable[[str], None]] = None,
) -> PipelineResult:
    """Sequentially extract the profile, then run every selected section.

    Wrapped in :func:`timed_call` so the build duration is visible in
    the debug log alongside the per-section start/done lines below.
    """
    output_lang = _resolve_output_lang(output_lang)
    STATE.last_error = ""

    sections = set(selected_sections or STATE.selected_sections or DEFAULT_SECTIONS)
    logger_service.log_state(
        "ai_linkedin.pipeline",
        "run_full_profile_build_state",
        output_lang=output_lang,
        sections=sorted(sections),
        demo_mode=STATE.demo_mode,
    )

    if STATE.demo_mode:
        # Re-seed the curated state in case the user toggled fields in
        # the Sections tab. No provider calls; the full Output cards
        # populate from ``data.DEMO_*``.
        load_demo()
        if on_step:
            for sec in ("profile", SEC_HEADLINE, SEC_ABOUT, SEC_EXPERIENCE,
                        SEC_SKILLS, SEC_FEATURED, SEC_PROJECTS,
                        SEC_RECOMMENDATIONS, SEC_POSTS, SEC_CHECKLIST):
                on_step(sec)
        _set_activity("ready")
        REFS.dispatch(_request_full_refresh)
        return PipelineResult(ok=True)

    res = extract_profile(output_lang=output_lang)
    if not res.ok:
        return res
    if on_step:
        on_step("profile")

    # Run sections in a stable display order so the Output tab paints
    # the cards in the same sequence the user expects.
    ordered = [
        SEC_HEADLINE,
        SEC_ABOUT,
        SEC_EXPERIENCE,
        SEC_EDUCATION,
        SEC_CERTIFICATIONS,
        SEC_SKILLS,
        SEC_FEATURED,
        SEC_PROJECTS,
        SEC_COURSES,
        SEC_RECOMMENDATIONS,
        SEC_SERVICES,
        SEC_POSTS,
    ]
    for sec in ordered:
        if sec not in sections:
            continue
        runner = _SECTION_RUNNERS.get(sec)
        if runner is None:
            continue
        res = runner(output_lang=output_lang)
        if not res.ok:
            return res
        if on_step:
            on_step(sec)

    if SEC_CHECKLIST in sections or True:  # always compute deterministic helpers
        _set_activity("scoring")
        build_completeness_checklist()
        build_unsupported_claims_report()
        compute_profile_score()
        if on_step:
            on_step(SEC_CHECKLIST)

    _set_activity("ready")
    REFS.dispatch(_request_full_refresh)
    logger_service.log_state(
        "ai_linkedin.pipeline",
        "run_full_profile_build_state_done",
        sections=sorted(sections),
        score=STATE.profile_score.get("overall_score") if STATE.profile_score else None,
    )
    return PipelineResult(ok=True)


# --- Chat mode --------------------------------------------------------------


def send_chat_message(*, output_lang: str, user_text: str) -> tuple[str, str]:
    """Synchronous chat turn for the Chat-mode UI.

    Returns ``(assistant_text, error)``. On success ``error`` is empty.
    The helper does not mutate ``STATE.chat_messages`` - the caller
    controls how the user/assistant bubbles are appended.
    """
    output_lang = _resolve_output_lang(output_lang)
    target_roles, audience, tone = _resolve_targeting()

    user_text = (user_text or "").strip()
    if not user_text:
        return "", "Empty message."

    logger_service.log_event(
        "INFO",
        "ai_linkedin.pipeline",
        "send_chat_start",
        output_lang=output_lang,
        chars=len(user_text),
        history=len(STATE.chat_messages),
        attachments=len(STATE.chat_attachments),
        demo_mode=STATE.demo_mode,
    )

    if STATE.demo_mode:
        reply_en = (
            "Demo mode is on, so I am not calling the provider. "
            "For Jana's profile I would suggest leading with the "
            "**TrustPay CI runtime win** (38 -> 14 min) in the "
            "headline and using the **medium About variant** as the "
            "starting point on the LinkedIn profile. Turn off Demo "
            "data in the section ... menu to ask the real AI coach."
        )
        reply_cs = (
            "Demo režim je zapnutý, takže nevolám AI. Pro Janin "
            "profil bych v headlinu zdůraznil/a **úsporu CI v TrustPay "
            "(38 -> 14 min)** a jako About použil/a **střední "
            "variantu**. Pokud chceš odpověď od skutečné AI, vypni "
            "Demo data v menu ... v sekci."
        )
        reply = reply_cs if (output_lang or "").lower().startswith("cs") else reply_en
        logger_service.log_event(
            "INFO", "ai_linkedin.pipeline", "send_chat_demo_done",
            reply_chars=len(reply),
        )
        return reply, ""

    history = [
        {"role": m.role, "text": m.text} for m in STATE.chat_messages
    ]
    user = prompts.build_chat_user_block(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=STATE.extracted_profile,
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
            "ai_linkedin.pipeline", "send_chat_provider_error", exc,
        )
        return "", str(exc)
    text = (result.text or "").strip()
    if not text:
        logger_service.log_event(
            "ERROR", "ai_linkedin.pipeline", "send_chat_empty_response",
        )
        return "", "Provider returned an empty response."
    logger_service.log_event(
        "INFO",
        "ai_linkedin.pipeline",
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
    """Append a message to the in-memory transcript."""
    label = time_label or datetime.now().strftime("%H:%M")
    STATE.chat_messages.append(
        ChatMessage(
            role=role,
            text=text,
            time=label,
            attachment_name=attachment_name,
        )
    )


# --- Save complete profile --------------------------------------------------


def _safe_write(path: Path, content: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        logger_service.log_exception(
            "ai_linkedin.pipeline", "save_write_failed", exc, path=str(path),
        )


def save_full_profile() -> SaveResult:
    """Persist every generated section + summary.json + history entry."""
    if not STATE.extracted_profile:
        logger_service.log_event(
            "WARNING", "ai_linkedin.pipeline", "save_full_no_profile",
        )
        return SaveResult(ok=False, error="no_profile")

    role = ""
    target_roles, audience, tone = _resolve_targeting()
    if target_roles:
        role = target_roles[0]
    folder_path = Path(store.new_run_dir(role or "linkedin-profile", section="ai_linkedin"))
    STATE.last_run_folder = str(folder_path)
    output_lang = _resolve_output_lang(STATE.output_lang)

    logger_service.log_event(
        "INFO",
        "ai_linkedin.pipeline",
        "save_full_start",
        folder=str(folder_path),
        role=role,
    )

    _set_activity("saving")

    # Refresh deterministic helpers in case the user saves before the
    # combined run finished them.
    if not STATE.completeness:
        build_completeness_checklist()
    if not STATE.unsupported_claims:
        build_unsupported_claims_report()
    if not STATE.profile_score:
        compute_profile_score()

    md_outputs = _render_section_markdown(output_lang)
    for filename, body in md_outputs.items():
        _safe_write(folder_path / filename, body)

    # Pretty HTML versions for human review.
    for filename, body in md_outputs.items():
        try:
            html_target = folder_path / (filename[: -3] + ".html")
            exporter.export_html(
                body, html_target, title=filename[3:-3].replace("_", " "),
                style="modern",
            )
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.pipeline", "export_html_failed", exc,
                filename=filename,
            )

    # Big composite HTML summary the user can email / archive.
    try:
        composite = summary_html.render_full_profile_html(
            extracted_profile=STATE.extracted_profile or {},
            headlines=STATE.headlines,
            about=STATE.about_variants,
            experience_rewrites=STATE.experience_rewrites,
            education_rewrites=STATE.education_rewrites,
            certifications_rewrites=STATE.certifications_rewrites,
            skills_buckets=STATE.skills_buckets,
            featured=STATE.featured,
            projects=STATE.projects,
            services=STATE.services,
            courses=STATE.courses,
            recommendation_messages=STATE.recommendation_messages,
            posts=STATE.posts,
            completeness=STATE.completeness,
            unsupported_claims=STATE.unsupported_claims,
            profile_score=STATE.profile_score,
            target_roles=target_roles,
            audience=audience,
            tone=tone,
            output_lang=output_lang,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        _safe_write(folder_path / "14_full_linkedin_profile.html", composite)
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.pipeline", "summary_html_failed", exc,
        )

    # Sidecar JSON so future tooling / "open in app" can rehydrate.
    try:
        store.write_json_file(
            folder_path,
            "summary.json",
            {
                "extracted_profile": STATE.extracted_profile,
                "headlines": STATE.headlines,
                "about_variants": STATE.about_variants,
                "experience_rewrites": STATE.experience_rewrites,
                "education_rewrites": STATE.education_rewrites,
                "certifications_rewrites": STATE.certifications_rewrites,
                "skills_buckets": STATE.skills_buckets,
                "featured": STATE.featured,
                "projects": STATE.projects,
                "services": STATE.services,
                "courses": STATE.courses,
                "recommendation_messages": STATE.recommendation_messages,
                "posts": STATE.posts,
                "completeness": STATE.completeness,
                "unsupported_claims": STATE.unsupported_claims,
                "profile_score": STATE.profile_score,
                "target_roles": target_roles,
                "audience": audience,
                "tone": tone,
                "output_lang": output_lang,
                "cost": {
                    "calls": COST.calls,
                    "tokens": COST.tokens_total,
                    "usd": COST.cost_usd,
                },
            },
        )
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.pipeline", "summary_json_failed", exc,
        )

    # History entry so the History tab + sidebar list pick up the run.
    try:
        score = int((STATE.profile_score or {}).get("score") or 0)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        docs_list = [name for name in md_outputs.keys()]
        summary = store.RunSummary(
            timestamp=timestamp,
            role=role,
            company="",
            overall_score=score,
            folder=str(folder_path),
            provider="",
            model="",
            cost_usd=float(COST.cost_usd),
            docs=docs_list,
            note="ai_linkedin",
        )
        store.append_run(summary)
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.pipeline", "save_full_history_append", exc,
        )

    _set_activity("ready")
    REFS.dispatch(_request_full_refresh)
    logger_service.log_event(
        "INFO",
        "ai_linkedin.pipeline",
        "save_full_done",
        folder=str(folder_path),
    )
    return SaveResult(ok=True, folder=str(folder_path))


def _render_section_markdown(output_lang: str) -> dict[str, str]:
    """Render each generated section as a markdown file ready for export.

    Filenames are numbered so they sort sensibly in the user's file
    browser. Returns ``{filename: body}``.
    """
    is_cs = output_lang == "cs"
    out: dict[str, str] = {}

    if STATE.headlines and (STATE.headlines.get("variants") or []):
        out["01_headline_variants.md"] = _render_headlines_md(STATE.headlines, is_cs)
    if STATE.about_variants:
        out["02_about_section.md"] = _render_about_md(STATE.about_variants, is_cs)
    if STATE.experience_rewrites and (STATE.experience_rewrites.get("roles") or []):
        out["03_experience_rewrite.md"] = _render_experience_md(
            STATE.experience_rewrites, is_cs
        )
    if STATE.skills_buckets:
        out["04_skills_recommendation.md"] = _render_skills_md(
            STATE.skills_buckets, is_cs
        )
    if STATE.featured and (STATE.featured.get("items") or []):
        out["05_featured_section.md"] = _render_featured_md(STATE.featured, is_cs)
    if STATE.projects and (STATE.projects.get("projects") or []):
        out["06_projects.md"] = _render_projects_md(STATE.projects, is_cs)
    if STATE.certifications_rewrites:
        out["07_certifications.md"] = _render_certifications_md(
            STATE.certifications_rewrites, is_cs
        )
    if STATE.education_rewrites and (STATE.education_rewrites.get("entries") or []):
        out["08_education.md"] = _render_education_md(
            STATE.education_rewrites, is_cs
        )
    if STATE.services and (
        (STATE.services.get("services") or []) or STATE.services.get("skip_reason")
    ):
        out["09_services.md"] = _render_services_md(STATE.services, is_cs)
    if STATE.recommendation_messages and (
        STATE.recommendation_messages.get("templates") or []
    ):
        out["10_recruiter_messages.md"] = _render_recommendations_md(
            STATE.recommendation_messages, is_cs
        )
    if STATE.posts and (STATE.posts.get("posts") or []):
        out["11_linkedin_posts.md"] = _render_posts_md(STATE.posts, is_cs)
    if STATE.completeness:
        out["12_profile_checklist.md"] = _render_checklist_md(
            STATE.completeness, STATE.profile_score, is_cs
        )
    if STATE.unsupported_claims and (STATE.unsupported_claims.get("rows") or []):
        out["13_unsupported_claims.md"] = _render_unsupported_md(
            STATE.unsupported_claims, is_cs
        )

    return out


def _h(en: str, cs: str, is_cs: bool) -> str:
    return cs if is_cs else en


def _render_headlines_md(payload: dict, is_cs: bool) -> str:
    lines = [
        f"# {_h('LinkedIn headline variants', 'Varianty LinkedIn headlinu', is_cs)}",
        "",
    ]
    for i, v in enumerate(payload.get("variants") or [], start=1):
        text = (v.get("text") or "").strip()
        chars = v.get("char_count")
        focus = (v.get("focus") or "").strip()
        audience = (v.get("audience") or "").strip()
        anchors = ", ".join(v.get("evidence_anchors") or [])
        lines.append(f"## {i}. {focus or audience or '—'} ({chars} chars)")
        lines.append("")
        lines.append(text)
        if anchors:
            lines.append("")
            lines.append(
                "_" + _h("Evidence:", "Důkazy:", is_cs) + " " + anchors + "_"
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_about_md(payload: dict, is_cs: bool) -> str:
    sections = [
        ("short_version", _h("Short", "Krátká", is_cs)),
        ("medium_version", _h("Medium", "Střední", is_cs)),
        ("long_version", _h("Long", "Dlouhá", is_cs)),
        ("technical_version", _h("Technical", "Technická", is_cs)),
        ("recruiter_version", _h("Recruiter-friendly", "Recruiter-friendly", is_cs)),
    ]
    char_counts = payload.get("char_counts") or {}
    lines = [
        f"# {_h('LinkedIn About / Intro', 'LinkedIn About / Úvod', is_cs)}",
        "",
    ]
    for key, label in sections:
        body = (payload.get(key) or "").strip()
        if not body:
            continue
        n = char_counts.get(key, len(body))
        lines.append(f"## {label} ({n} chars)")
        lines.append("")
        lines.append(body)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_experience_md(payload: dict, is_cs: bool) -> str:
    lines = [
        f"# {_h('Experience rewrite', 'Přepis zkušeností', is_cs)}",
        "",
    ]
    for role in payload.get("roles") or []:
        if not isinstance(role, dict):
            continue
        title = f"{role.get('role') or ''} - {role.get('company') or ''}".strip(" -")
        period = role.get("period") or ""
        lines.append(f"## {title} ({period})")
        desc = (role.get("linkedin_description") or "").strip()
        if desc:
            lines.append("")
            lines.append(desc)
        bullets = role.get("bullets") or []
        if bullets:
            lines.append("")
            for b in bullets:
                lines.append(f"- {b}")
        skills = role.get("suggested_skills") or []
        if skills:
            lines.append("")
            lines.append("**" + _h("Skills to attach:", "Skills k přiřazení:", is_cs) + "** " +
                         ", ".join(s.get("name") or "" for s in skills if isinstance(s, dict)))
        do_not = role.get("do_not_claim") or []
        if do_not:
            lines.append("")
            lines.append("**" + _h("Do NOT claim:", "NEUVÁDĚT:", is_cs) + "**")
            for note in do_not:
                lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_skills_md(payload: dict, is_cs: bool) -> str:
    lines = [
        f"# {_h('Skills recommendation', 'Doporučení skills', is_cs)}",
        "",
    ]
    buckets = [
        ("core", _h("Core - claim now", "Klíčové - uveď hned", is_cs)),
        ("to_verify", _h("Verify before claiming", "Ověř před uvedením", is_cs)),
        ("to_learn", _h("Learn next", "Naučit se příště", is_cs)),
        ("do_not_claim", _h("Do not claim", "Neuvádět", is_cs)),
    ]
    for key, label in buckets:
        items = payload.get(key) or []
        if not items:
            continue
        lines.append(f"## {label}")
        lines.append("")
        for s in items:
            if not isinstance(s, dict):
                continue
            name = s.get("name") or ""
            anchor = s.get("evidence_anchor") or ""
            quote = (s.get("evidence_quote") or "").strip()
            reason = (s.get("reason") or "").strip()
            line = f"- **{name}** _({anchor})_"
            if quote:
                line += f" - {quote}"
            elif reason:
                line += f" - {reason}"
            lines.append(line)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_featured_md(payload: dict, is_cs: bool) -> str:
    lines = [
        f"# {_h('Featured section suggestions', 'Návrhy na Featured sekci', is_cs)}",
        "",
    ]
    for item in payload.get("items") or []:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or ""
        kind = item.get("kind") or ""
        lines.append(f"## {title} _({kind})_")
        desc = (item.get("description") or "").strip()
        if desc:
            lines.append("")
            lines.append(desc)
        link = (item.get("link") or "").strip()
        if link:
            lines.append("")
            lines.append(f"[{link}]({link})")
        todo = (item.get("todo") or "").strip()
        if todo:
            lines.append("")
            lines.append(f"_{_h('TODO:', 'TODO:', is_cs)} {todo}_")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_projects_md(payload: dict, is_cs: bool) -> str:
    lines = [
        f"# {_h('Projects', 'Projekty', is_cs)}",
        "",
    ]
    for proj in payload.get("projects") or []:
        if not isinstance(proj, dict):
            continue
        lines.append(f"## {proj.get('title') or ''}")
        lines.append(f"_{proj.get('period') or ''}_")
        desc = (proj.get("description") or "").strip()
        if desc:
            lines.append("")
            lines.append(desc)
        techs = proj.get("technologies") or []
        if techs:
            lines.append("")
            lines.append("**" + _h("Stack:", "Stack:", is_cs) + "** " + ", ".join(techs))
        role = (proj.get("candidate_role") or "").strip()
        if role:
            lines.append("")
            lines.append("**" + _h("Your role:", "Tvoje role:", is_cs) + "** " + role)
        link = (proj.get("link") or "").strip()
        if link:
            lines.append("")
            lines.append(f"[{link}]({link})")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_certifications_md(payload: dict, is_cs: bool) -> str:
    lines = [
        f"# {_h('Certifications', 'Certifikace', is_cs)}",
        "",
    ]
    existing = payload.get("existing") or []
    if existing:
        lines.append(_h("## Existing", "## Stávající", is_cs))
        lines.append("")
        for cert in existing:
            if not isinstance(cert, dict):
                continue
            name = cert.get("name") or ""
            issuer = cert.get("issuer") or ""
            year = cert.get("year") or ""
            priority = cert.get("priority") or ""
            lines.append(f"- **{name}** ({issuer}, {year}) - {_h('priority', 'priorita', is_cs)}: {priority}")
            desc = (cert.get("linkedin_description") or "").strip()
            if desc:
                lines.append(f"  - {desc}")
        lines.append("")
    recommended = payload.get("recommended") or []
    if recommended:
        lines.append(_h("## Recommended (consider next)", "## Doporučené (zvaž jako další)", is_cs))
        lines.append("")
        for cert in recommended:
            if not isinstance(cert, dict):
                continue
            lines.append(
                f"- **{cert.get('name') or ''}** ({cert.get('issuer') or ''})"
                f" - {cert.get('why_it_matters') or ''}"
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_education_md(payload: dict, is_cs: bool) -> str:
    lines = [
        f"# {_h('Education rewrite', 'Přepis vzdělání', is_cs)}",
        "",
    ]
    for entry in payload.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        lines.append(f"## {entry.get('institution') or ''}")
        lines.append(f"_{entry.get('degree') or ''} ({entry.get('period') or ''})_")
        desc = (entry.get("linkedin_description") or "").strip()
        if desc:
            lines.append("")
            lines.append(desc)
        coursework = entry.get("relevant_coursework") or []
        if coursework:
            lines.append("")
            lines.append("**" + _h("Relevant coursework:", "Relevantní předměty:", is_cs) + "** " +
                         ", ".join(coursework))
        connection = (entry.get("connection_to_target") or "").strip()
        if connection:
            lines.append("")
            lines.append("_" + _h("Why it matters:", "Proč je to relevantní:", is_cs) + " " + connection + "_")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_services_md(payload: dict, is_cs: bool) -> str:
    lines = [
        f"# {_h('Services', 'Služby', is_cs)}",
        "",
    ]
    services = payload.get("services") or []
    if not services:
        skip = (payload.get("skip_reason") or "").strip()
        lines.append(skip or _h("Skip - candidate did not opt in.", "Vynech - kandidát neopt-inoval.", is_cs))
        lines.append("")
        return "\n".join(lines).strip() + "\n"
    for svc in services:
        if not isinstance(svc, dict):
            continue
        lines.append(f"## {svc.get('name') or ''}")
        desc = (svc.get("short_description") or "").strip()
        if desc:
            lines.append("")
            lines.append(desc)
        cred = (svc.get("why_credible") or "").strip()
        if cred:
            lines.append("")
            lines.append("_" + _h("Why credible:", "Proč věrohodné:", is_cs) + " " + cred + "_")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_recommendations_md(payload: dict, is_cs: bool) -> str:
    lines = [
        f"# {_h('Recommendation request templates', 'Šablony žádostí o doporučení', is_cs)}",
        "",
    ]
    for tpl in payload.get("templates") or []:
        if not isinstance(tpl, dict):
            continue
        lines.append(f"## {tpl.get('suggested_recipient_label') or '—'} _({tpl.get('recipient_type') or ''})_")
        body = (tpl.get("message") or "").strip()
        if body:
            lines.append("")
            lines.append(body)
        follow = (tpl.get("follow_up") or "").strip()
        if follow:
            lines.append("")
            lines.append("**" + _h("Follow-up:", "Follow-up:", is_cs) + "** " + follow)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_posts_md(payload: dict, is_cs: bool) -> str:
    lines = [
        f"# {_h('LinkedIn posts', 'LinkedIn posty', is_cs)}",
        "",
    ]
    for post in payload.get("posts") or []:
        if not isinstance(post, dict):
            continue
        kind = post.get("kind") or ""
        title = post.get("title") or ""
        lines.append(f"## [{kind}] {title}")
        chars = post.get("char_count")
        if chars is not None:
            lines.append(f"_{chars} chars_")
        body = (post.get("body") or "").strip()
        if body:
            lines.append("")
            lines.append(body)
        hashtags = post.get("hashtags") or []
        if hashtags:
            lines.append("")
            lines.append(" ".join(hashtags))
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_checklist_md(checklist: dict, score: dict | None, is_cs: bool) -> str:
    lines = [
        f"# {_h('Profile completeness checklist', 'Checklist úplnosti profilu', is_cs)}",
        "",
    ]
    if score:
        lines.append(
            "**" + _h("Profile score:", "Skóre profilu:", is_cs) + f"** {score.get('score', 0)}/100"
        )
        lines.append("")
    priority_labels = {
        _PRIORITY_HIGH: _h("High priority", "Vysoká priorita", is_cs),
        _PRIORITY_MED: _h("Medium priority", "Střední priorita", is_cs),
        _PRIORITY_LOW: _h("Low priority", "Nízká priorita", is_cs),
        _PRIORITY_SKIP: _h("Skip", "Vynechat", is_cs),
    }
    for prio in (_PRIORITY_HIGH, _PRIORITY_MED, _PRIORITY_LOW, _PRIORITY_SKIP):
        items = [i for i in (checklist.get("items") or []) if i.get("priority") == prio]
        if not items:
            continue
        lines.append(f"## {priority_labels[prio]}")
        for i in items:
            mark = "[x]" if i.get("ok") else "[ ]"
            lines.append(f"- {mark} **{i.get('label')}** - {i.get('reason')}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_unsupported_md(payload: dict, is_cs: bool) -> str:
    lines = [
        f"# {_h('Unsupported claims report', 'Report nepodložených tvrzení', is_cs)}",
        "",
        _h(
            "These items lack evidence in your sources. Confirm before"
            " adding them to your LinkedIn profile.",
            "Tyto body nemají oporu ve zdrojích. Před přidáním na LinkedIn"
            " si je ověř.",
            is_cs,
        ),
        "",
    ]
    for row in payload.get("rows") or []:
        if not isinstance(row, dict):
            continue
        lines.append(f"- **{row.get('label')}** _({row.get('kind')})_ - {row.get('reason')}")
    lines.append("")
    return "\n".join(lines).strip() + "\n"


