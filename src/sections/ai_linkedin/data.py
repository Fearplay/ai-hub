"""Static metadata for the AI LinkedIn section.

The "live" helpers (``brand_profile_fields``, ``recent_runs``,
``quick_actions``) read from :data:`STATE` at call time and never
invent data. There is no demo / mock seed - every Output card is
populated by a real ``pipeline.run_full_profile_build`` call.
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


SECTION_ICON = Icons.HUB_OUTLINED


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
        title = entry.get("role") or txt["recent_default_title"]
        when = entry.get("timestamp") or ""
        out.append({"title": title, "time": when})
    if not out:
        out.append({"title": txt["recent_empty_title"], "time": ""})
    return out
