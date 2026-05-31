"""Bridge between the shared career profile and AI Career's input state.

Reads the once-uploaded profile from :mod:`src.services.career_profile_store`
(a shared service - no cross-section import) and maps its raw sources into
this section's :data:`STATE` so the user does not have to re-upload their CV.
The mapping is opt-in (the setup-tab banner's "use it here" button) and the
upload zones stay editable, so a per-run override is always possible.
"""

from __future__ import annotations

from src.services import career_profile_store
from src.services import logger as logger_service
from src.sections.ai_career.state import STATE, UploadedFile


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
        logger_service.log_exception("ai_career.shared_profile", "has_shared_failed", exc)
        return False


def is_applied() -> bool:
    """True when the section's resume already matches the shared CV."""
    src = career_profile_store.resume_source()
    if not src:
        return False
    return bool(STATE.resume and STATE.resume.text and STATE.resume.text == src.get("text"))


def apply() -> None:
    """Map the shared profile's raw sources into AI Career's STATE."""
    try:
        resume = career_profile_store.resume_source()
        if resume:
            STATE.resume = _to_uploaded(resume)
        linkedin = career_profile_store.linkedin_source()
        if linkedin:
            STATE.linkedin = _to_uploaded(linkedin)
        github = career_profile_store.github_url()
        if github:
            STATE.github_url = github
            STATE.github_skip = False
        logger_service.log_event(
            "INFO", "ai_career.shared_profile", "apply_done",
            has_resume=bool(resume), has_linkedin=bool(linkedin), has_github=bool(github),
        )
    except Exception as exc:
        logger_service.log_exception("ai_career.shared_profile", "apply_failed", exc)


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
