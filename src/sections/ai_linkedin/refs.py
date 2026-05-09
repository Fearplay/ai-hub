"""Cross-thread refresh helpers for AI LinkedIn.

The section talks to LLMs / scrapes / writes files on daemon threads.
Once those workers mutate :data:`STATE`, the UI has to repaint, but in
Flet 0.84 calling ``page.update()`` directly from a non-UI thread queues
a patch on the page's asyncio loop without forcing the loop to run a
tick - the user sees the new state only after the next window event
(focus, resize, …). The fix is to bounce the work onto the loop via
``loop.call_soon_threadsafe`` so the patch ships immediately.

UI-thread callers can keep calling ``request_section_refresh()`` directly;
worker threads should go through ``REFS.dispatch(callback)`` so the
``page.update()`` lands on the right thread.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from src.services import logger as logger_service


@dataclass
class LinkedInRefs:
    """Cross-cutting handles shared between view + worker threads.

    * ``rerender_context`` - light right-hand-panel refresh used after
      activity / cost changes that don't need a full section rebuild.
    * ``page`` - the live ``ft.Page`` cached when the section first mounts
      so :meth:`dispatch` can find the asyncio loop without piping the
      page through every callback.
    """

    rerender_context: Optional[Callable[[], None]] = None
    page: Optional[Any] = None  # ft.Page once mounted

    def dispatch(self, callback: Callable[[], None]) -> None:
        """Run ``callback`` on the page's asyncio loop, then flush.

        Why not just call ``callback()`` followed by ``page.update()``?
        Because from a worker thread that pair only schedules a patch -
        the UI client doesn't repaint until the loop runs again. Routing
        through ``loop.call_soon_threadsafe`` wakes the loop immediately
        so the new tab / activity badge / generated card actually shows
        up without the user having to minimise / restore the window.

        Falls back to a synchronous call when the page or its loop is
        not available yet (e.g. during the very first render).
        """
        page = self.page
        if page is None:
            try:
                callback()
            except Exception as exc:
                logger_service.log_exception(
                    "ai_linkedin.refs", "dispatch_no_page_callback_failed", exc,
                )
            return
        loop = None
        try:
            loop = page.session.connection.loop
        except Exception:
            loop = None
        if loop is None:
            try:
                callback()
            except Exception as exc:
                logger_service.log_exception(
                    "ai_linkedin.refs", "dispatch_no_loop_callback_failed", exc,
                )
            try:
                page.update()
            except Exception as exc:
                logger_service.log_exception(
                    "ai_linkedin.refs", "dispatch_no_loop_update_failed", exc,
                )
            return
        try:
            loop.call_soon_threadsafe(_run_and_flush, callback, page)
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.refs", "dispatch_call_soon_failed", exc,
            )
            try:
                callback()
            except Exception as exc2:
                logger_service.log_exception(
                    "ai_linkedin.refs", "dispatch_fallback_callback_failed", exc2,
                )
            try:
                page.update()
            except Exception as exc2:
                logger_service.log_exception(
                    "ai_linkedin.refs", "dispatch_fallback_update_failed", exc2,
                )

    def request_context_refresh(self) -> None:
        """Request a right-hand context panel refresh from any thread.

        Always thread-safe: when ``rerender_context`` is ``None`` (the
        section has not finished mounting yet) we silently no-op
        instead of raising. When the page is available we route through
        :meth:`dispatch` so the worker thread's update lands on the UI
        loop within the same tick.
        """
        callback = self.rerender_context
        if callback is None:
            return
        if self.page is None:
            safe(callback)
            return
        self.dispatch(callback)


def _run_and_flush(callback: Callable[[], None], page: Any) -> None:
    """Helper executed on the UI loop: run callback, then ``page.update()``.

    The callback typically rebuilds the section (which mutates Flet
    controls). We follow up with an explicit ``page.update()`` so the
    patch is sent on the same loop tick - otherwise we would still rely
    on the auto-update that drops on the floor when there is no event
    handler in flight.
    """
    try:
        callback()
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.refs", "run_and_flush_callback_failed", exc,
        )
    try:
        page.update()
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.refs", "run_and_flush_page_update_failed", exc,
        )


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
