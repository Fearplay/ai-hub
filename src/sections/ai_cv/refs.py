"""Cross-thread refresh helpers for AI Career (PySide6 port).

Worker threads in `pipeline.py` mutate `STATE` and need the UI to repaint.
We route those repaints through `src.qt.runtime.dispatch`, which uses
`Qt.QueuedConnection` to run on the GUI thread.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from src.qt.lifecycle import CoalescedRefresh
from src.qt.runtime import dispatch as runtime_dispatch
from src.services import logger as logger_service
from src.services.activity_tracker import ACTIVITY
from src.sections.ai_cv.state import STATE
from src.sections.ai_cv.strings import s


# Maps a raw ``STATE.activity`` token onto the localized string key that
# describes it in the sidebar Activity panel. Run-stage tokens
# (``running`` / ``followups`` / ``match``) take priority over these and
# are handled separately in :meth:`CareerRefs._activity_label`.
_ACTIVITY_LABEL_KEYS = {
    "scraping": "ctx_activity_scraping",
    "parsing": "ctx_activity_parsing",
    "analyzing": "ctx_activity_analyzing",
    "followups": "ctx_activity_followups",
    "waiting_user": "ctx_activity_waiting_user",
    "generating": "ctx_activity_generating",
    "exporting": "ctx_activity_exporting",
    "error": "ctx_activity_error",
}


@dataclass
class CareerRefs:
    rerender_context: Optional[Callable[[], None]] = None
    page: Optional[Any] = None
    # Current UI language, refreshed by ``build_view`` so worker threads
    # can resolve the Activity-panel label without a Qt round-trip.
    lang: str = "en"
    _refresh: CoalescedRefresh = field(default_factory=CoalescedRefresh)

    def dispatch(self, callback: Callable[[], None]) -> None:
        try:
            runtime_dispatch(callback)
        except Exception as exc:
            logger_service.log_exception(
                "ai_cv.refs", "dispatch_failed", exc,
            )

    def _activity_label(self) -> str:
        """Localized progress text for the sidebar Activity panel.

        The granular progress ("Scoring the match...", "Generating...",
        ...) used to live inside a button label; it now surfaces here so
        the buttons can keep a stable caption. Returns ``""`` for the
        idle/ready state so the sidebar falls back to its generic
        per-category string.
        """
        try:
            txt = s(self.lang)
        except Exception:
            return ""
        stage = (STATE.run_stage or "").strip().lower()
        if stage == "running":
            return txt.get("footer_run_running", "")
        if stage == "followups":
            return txt.get("footer_run_followups_running", "")
        if stage == "match":
            return txt.get("footer_run_match_running", "")
        key = _ACTIVITY_LABEL_KEYS.get((STATE.activity or "").strip().lower())
        if key:
            return txt.get(key, "")
        return ""

    def request_context_refresh(self) -> None:
        # The right context panel was removed; this is now the chokepoint
        # that feeds the left-sidebar Activity indicator. Pipeline workers
        # and view handlers both call this after mutating STATE.activity.
        # We pass a granular localized label so the Activity panel - not a
        # button - shows what the section is currently doing.
        ACTIVITY.set_from_value(STATE.activity, label=self._activity_label())
        if self.rerender_context is None:
            return
        self._refresh.schedule(lambda: self.rerender_context)


REFS = CareerRefs()


def safe(callback: Optional[Callable[[], None]]) -> None:
    if callback is None:
        return
    try:
        callback()
    except Exception as exc:
        logger_service.log_exception(
            "ai_cv.refs", "safe_callback_failed", exc,
        )
