"""Cross-thread refresh helpers for AI LinkedIn (PySide6 port).

The section talks to LLMs / scrapes / writes files on daemon threads.
Once those workers mutate :data:`STATE`, the UI has to repaint, but
``QWidget.update()`` is not safe to call from a non-GUI thread. The
:class:`src.qt.runtime.UIDispatcher` solves that: we pass the callback
through ``Qt.QueuedConnection`` so it lands on the GUI thread within the
next event loop tick.

UI-thread callers can keep calling ``REFS.request_context_refresh()``
or ``REFS.dispatch(callback)`` directly; worker threads use the same
API and the underlying dispatcher routes the call to the GUI thread.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from src.qt.lifecycle import CoalescedRefresh
from src.qt.runtime import dispatch as runtime_dispatch
from src.services import logger as logger_service
from src.services.activity_tracker import ACTIVITY
from src.sections.ai_linkedin.state import STATE
from src.sections.ai_linkedin.strings import s


# Maps a raw ``STATE.activity`` token onto the localized string key that
# describes it in the sidebar Activity indicator. Without this the
# sidebar fell back to the generic "Pracuji..." string for every busy
# stage (image 5).
_ACTIVITY_LABEL_KEYS = {
    "scraping": "ctx_activity_scraping",
    "parsing": "ctx_activity_parsing",
    "extracting": "ctx_activity_extracting",
    "analyzing": "ctx_activity_analyzing",
    "generating": "ctx_activity_generating",
    "scoring": "ctx_activity_scoring",
    "saving": "ctx_activity_saving",
    "saved": "ctx_activity_saved",
    "error": "ctx_activity_error",
}


# While the build loop runs one section at a time we surface *which*
# section is being generated ("Generuji: Přepis zkušeností") by mapping
# the section key onto its Output-card title string.
_SECTION_TITLE_KEYS = {
    "headline": "output_headlines_title",
    "about": "output_about_title",
    "experience": "output_experience_title",
    "education": "output_education_title",
    "certifications": "output_certifications_title",
    "skills": "output_skills_title",
    "featured": "output_featured_title",
    "projects": "output_projects_title",
    "services": "output_services_title",
    "courses": "output_courses_title",
    "recommendations": "output_recommendations_title",
    "languages": "output_languages_title",
    "volunteer": "output_volunteer_title",
    "publications": "output_publications_title",
    "honors": "output_honors_title",
    "posts": "output_posts_title",
}


@dataclass
class LinkedInRefs:
    """Cross-cutting handles shared between view + worker threads."""

    rerender_context: Optional[Callable[[], None]] = None
    # Current UI language, refreshed by ``build_view`` so worker threads
    # can resolve the localized Activity label without a Qt round-trip.
    lang: str = "en"
    _refresh: CoalescedRefresh = field(default_factory=CoalescedRefresh)

    def dispatch(self, callback: Callable[[], None]) -> None:
        """Run ``callback`` on the GUI thread."""
        try:
            runtime_dispatch(callback)
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.refs", "dispatch_failed", exc,
            )

    def _activity_label(self) -> str:
        """Localized progress text for the sidebar Activity indicator.

        Returns ``""`` for the idle/ready state so the sidebar falls back
        to its generic per-category string.
        """
        try:
            txt = s(self.lang)
        except Exception:
            return ""
        activity = (STATE.activity or "").strip().lower()
        if activity == "generating":
            sec = (STATE.activity_section or "").strip().lower()
            title_key = _SECTION_TITLE_KEYS.get(sec)
            if title_key:
                name = txt.get(title_key, "")
                if name:
                    template = txt.get("ctx_activity_generating_named", "{name}")
                    return template.format(name=name)
        key = _ACTIVITY_LABEL_KEYS.get(activity)
        if key:
            return txt.get(key, "")
        return ""

    def request_context_refresh(self) -> None:
        """Feed the left-sidebar Activity indicator from any thread.

        The right context panel was removed; this remains the single
        chokepoint pipeline workers + view handlers call after mutating
        ``STATE.activity``, so it publishes that status - plus a granular
        localized label - to the global ``ACTIVITY`` tracker the sidebar
        subscribes to.
        """
        ACTIVITY.set_from_value(STATE.activity, label=self._activity_label())
        if self.rerender_context is None:
            return
        self._refresh.schedule(lambda: self.rerender_context)


REFS = LinkedInRefs()


def safe(callback: Optional[Callable[[], None]]) -> None:
    """Call ``callback`` if non-None, logging any exception."""
    if callback is None:
        return
    try:
        callback()
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.refs", "safe_callback_failed", exc,
        )
