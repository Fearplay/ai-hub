"""Bridge between the shared career profile and AI Job Search's inputs.

Maps the once-uploaded CV from :mod:`src.services.career_profile_store`
(a shared service) into Job Search's ``STATE.profile_file`` so the user does
not have to re-upload it. Opt-in via the setup-tab banner; the upload zone
stays editable for a per-run override.
"""

from __future__ import annotations

from src.services import career_profile_store
from src.services import logger as logger_service
from src.sections.ai_jobs.state import STATE, UploadedFile


def _to_uploaded(src: dict) -> UploadedFile:
    return UploadedFile(
        path=str(src.get("path") or ""),
        name=str(src.get("name") or ""),
        ext=str(src.get("ext") or ""),
        size_bytes=int(src.get("size_bytes") or 0),
        text=str(src.get("text") or ""),
    )


def has_shared() -> bool:
    try:
        return career_profile_store.has_profile()
    except Exception as exc:
        logger_service.log_exception("ai_jobs.shared_profile", "has_shared_failed", exc)
        return False


def is_applied() -> bool:
    src = career_profile_store.resume_source()
    if not src:
        return False
    return bool(
        STATE.profile_file
        and STATE.profile_file.text
        and STATE.profile_file.text == src.get("text")
    )


def apply() -> None:
    """Map the shared CV into Job Search's STATE.profile_file."""
    try:
        resume = career_profile_store.resume_source()
        if resume:
            STATE.profile_file = _to_uploaded(resume)
        logger_service.log_event(
            "INFO", "ai_jobs.shared_profile", "apply_done", has_resume=bool(resume),
        )
    except Exception as exc:
        logger_service.log_exception("ai_jobs.shared_profile", "apply_failed", exc)


def build_summary(txt: dict) -> str:
    parts: list[str] = []
    who = " \u00b7 ".join(
        p for p in (career_profile_store.display_name(), career_profile_store.headline()) if p
    )
    if who:
        parts.append(who)
    items: list[str] = []
    if career_profile_store.resume_source():
        items.append(txt["shared_item_cv"])
    if career_profile_store.linkedin_source():
        items.append(txt["shared_item_linkedin"])
    if career_profile_store.github_url():
        items.append(txt["shared_item_github"])
    if items:
        parts.append(txt["shared_includes"].format(items=", ".join(items)))
    return "\n".join(parts) if parts else txt["shared_summary_generic"]
