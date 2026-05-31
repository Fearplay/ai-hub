"""Extraction pipeline for the shared career profile.

One public step - :func:`build_profile` - reads the uploaded sources,
optionally fetches the GitHub summary, calls
:func:`src.services.ai_provider.run` once with the unified
``CAREER_PROFILE_SCHEMA`` and persists the result via
:mod:`src.services.career_profile_store`. Demo mode short-circuits the
provider call with a curated profile so the feature can be showcased
without spending tokens.
"""

from __future__ import annotations

import copy
from typing import Optional

from src.services import ai_provider, career_profile_store, github_client
from src.services import logger as logger_service
from src.sections.my_profile import data as profile_data
from src.sections.my_profile import prompts, schema
from src.sections.my_profile.refs import REFS
from src.sections.my_profile.state import STATE, UploadedFile


def _set_activity(activity: str) -> None:
    STATE.activity = activity
    REFS.request_context_refresh()


def _file_to_source(f: Optional[UploadedFile]) -> Optional[dict]:
    if f is None or not f.text:
        return None
    return {
        "path": f.path,
        "name": f.name,
        "ext": f.ext,
        "size_bytes": f.size_bytes,
        "text": f.text,
    }


def fetch_github():
    value = (STATE.github_url or "").strip()
    if not value or STATE.github_skip:
        return None
    _set_activity("scraping")
    profile = None
    try:
        profile = github_client.fetch_profile(value)
    except Exception as exc:
        logger_service.log_exception("my_profile.pipeline", "github_fetch_failed", exc)
    finally:
        _set_activity("ready")
    STATE.github_profile = profile
    return profile


def _build_github_summary() -> str:
    if STATE.github_skip:
        return ""
    return prompts.serialize_github_summary(STATE.github_profile)


def _persist(*, demo: bool) -> None:
    username = ""
    if STATE.github_profile is not None and getattr(STATE.github_profile, "ok", False):
        username = getattr(STATE.github_profile, "username", "") or ""
    sources = {
        "resume": _file_to_source(STATE.resume),
        "linkedin": _file_to_source(STATE.linkedin),
        "github_url": (STATE.github_url or "").strip(),
        "github_username": username,
        "github_summary": _build_github_summary(),
        "notes": (STATE.notes or "").strip(),
    }
    payload = {"demo": demo, "sources": sources, "profile": STATE.profile or {}}
    try:
        if not career_profile_store.save(payload):
            logger_service.log_event(
                "WARNING", "my_profile.pipeline", "persist_failed",
            )
    except Exception as exc:
        logger_service.log_exception("my_profile.pipeline", "persist_exception", exc)


def set_demo(enabled: bool) -> None:
    """Toggle demo preview without touching the persisted real profile.

    Enabling shows the curated demo profile in memory only; disabling
    restores whatever is on disk. The demo is only written to disk when
    the user explicitly hits "build" in demo mode (see
    :func:`build_profile`).
    """
    logger_service.log_event(
        "INFO", "my_profile.pipeline", "set_demo", enabled=enabled,
    )
    STATE.demo_mode = enabled
    STATE.last_error = ""
    if enabled:
        STATE.profile = copy.deepcopy(profile_data.DEMO_PROFILE)
    else:
        STATE.profile = career_profile_store.get_profile()
    _set_activity("ready")


def clear_profile() -> None:
    logger_service.log_event("INFO", "my_profile.pipeline", "clear_profile")
    STATE.demo_mode = False
    STATE.profile = None
    STATE.reset_inputs()
    try:
        career_profile_store.clear()
    except Exception as exc:
        logger_service.log_exception("my_profile.pipeline", "clear_store_failed", exc)
    _set_activity("ready")


@logger_service.timed_call("my_profile.pipeline", "build_profile")
def build_profile(*, output_lang: str) -> tuple[bool, str]:
    """Extract + persist the structured profile.

    Returns ``(ok, error_code_or_message)``. The view maps known error
    codes (``resume_missing`` / ``no_json``) to localised copy.
    """
    logger_service.log_event(
        "INFO", "my_profile.pipeline", "build_profile_start",
        output_lang=output_lang, demo_mode=STATE.demo_mode,
        has_resume=bool(STATE.resume and STATE.resume.text),
        has_linkedin=bool(STATE.linkedin and STATE.linkedin.text),
    )

    if STATE.demo_mode:
        STATE.profile = copy.deepcopy(profile_data.DEMO_PROFILE)
        _persist(demo=True)
        _set_activity("ready")
        logger_service.log_event(
            "INFO", "my_profile.pipeline", "build_profile_demo_done",
        )
        return True, ""

    if not STATE.resume or not STATE.resume.text:
        STATE.last_error = "resume_missing"
        _set_activity("error")
        return False, "resume_missing"

    if (
        (STATE.github_url or "").strip()
        and not STATE.github_skip
        and STATE.github_profile is None
    ):
        fetch_github()

    _set_activity("analyzing")
    user = prompts.build_profile_user(
        output_lang=output_lang,
        resume_text=STATE.resume.text,
        linkedin_text=(STATE.linkedin.text if STATE.linkedin else ""),
        github_summary=_build_github_summary(),
        notes=STATE.notes,
    )
    try:
        result = ai_provider.run(
            system=prompts.PROFILE_SYSTEM,
            user=user,
            schema=schema.CAREER_PROFILE_SCHEMA,
            schema_name="career_profile",
            max_output_tokens=3500,
        )
    except ai_provider.ProviderError as exc:
        logger_service.log_exception(
            "my_profile.pipeline", "build_profile_provider_error", exc,
        )
        STATE.last_error = str(exc)
        _set_activity("error")
        return False, str(exc)

    if not isinstance(result.data, dict):
        STATE.last_error = "no_json"
        _set_activity("error")
        return False, "no_json"

    profile = result.data
    profile["linkedin_present"] = bool(STATE.linkedin and STATE.linkedin.text)
    profile["github_present"] = bool(
        STATE.github_profile and getattr(STATE.github_profile, "ok", False)
    )
    STATE.profile = profile
    STATE.last_error = ""
    _persist(demo=False)
    _set_activity("ready")
    logger_service.log_event(
        "INFO", "my_profile.pipeline", "build_profile_done",
        skills=len(profile.get("technical_skills") or []),
        experiences=len(profile.get("experiences") or []),
    )
    return True, ""
