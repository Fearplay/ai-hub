"""Cross-thread refresh helpers for AI Career.

The section talks to LLMs / scrapes / writes files on daemon threads. Once
those workers mutate :data:`STATE`, the UI has to repaint, but in Flet
0.84 calling ``page.update()`` directly from a non-UI thread queues a
patch on the page's asyncio loop without forcing the loop to run a tick -
the user sees the redirect only after the next window event (focus,
resize, …). The fix is to bounce the work onto the loop via
``loop.call_soon_threadsafe`` so the patch ships immediately.

UI-thread callers can keep calling ``request_section_refresh()`` directly;
worker threads should go through ``REFS.dispatch(callback)`` so the
``page.update()`` lands on the right thread.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class CareerRefs:
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
        so the redirect / new tab body actually shows up without the
        user having to minimize / restore the window.

        Falls back to a synchronous call when the page or its loop is
        not available yet (e.g. during the very first render).
        """
        page = self.page
        if page is None:
            try:
                callback()
            except Exception:
                pass
            return
        loop = None
        try:
            loop = page.session.connection.loop
        except Exception:
            loop = None
        if loop is None:
            try:
                callback()
            except Exception:
                pass
            try:
                page.update()
            except Exception:
                pass
            return
        try:
            loop.call_soon_threadsafe(_run_and_flush, callback, page)
        except Exception:
            try:
                callback()
            except Exception:
                pass
            try:
                page.update()
            except Exception:
                pass


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
    except Exception:
        pass
    try:
        page.update()
    except Exception:
        pass


REFS = CareerRefs()


def safe(callback: Optional[Callable[[], None]]) -> None:
    """Call ``callback`` if non-None, swallowing exceptions."""
    if callback is None:
        return
    try:
        callback()
    except Exception:
        pass
