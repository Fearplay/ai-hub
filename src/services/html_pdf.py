"""Render an HTML string to a printable A4 PDF via Playwright.

Used by the AI Career section to produce Modern CV + Cover Letter PDFs
that match the styled HTML preview pixel-for-pixel - the same self-
contained HTML the in-app preview uses gets shipped to the headless
browser, which prints it to PDF with backgrounds and CSS Paged Media
honoured.

Design goals (mirrored from ``applypilot-ai``):

* No mandatory ``playwright install`` step. We probe the user's existing
  Chrome, then Edge, then the bundled Chromium / Firefox.
* Lazy import. The ``playwright`` Python package is only imported when
  this module is actually used so the rest of the app boots even on a
  machine where Playwright was never set up.
* Fully headless. No browser window pops up; the user just sees the
  spinner and then the new files on disk.
* Best-effort. Failure raises :class:`PdfRendererUnavailableError` so
  callers can degrade gracefully (e.g. fall back to the legacy
  ``reportlab`` path) instead of breaking the whole save action.
"""

from __future__ import annotations

import logging
from contextlib import suppress
from pathlib import Path

logger = logging.getLogger(__name__)


#: Browser launch attempts in order. ``("chromium", "chrome")`` is the
#: user's installed Google Chrome via Playwright's ``channel=`` flag,
#: ``("chromium", "msedge")`` is Microsoft Edge (always present on
#: modern Windows), and ``("chromium", "")`` is the bundled Chromium
#: from ``playwright install`` if the user ran it. Firefox is the last
#: resort and only kicks in when none of the chromium variants work.
_CHANNEL_PREFERENCES: tuple[tuple[str, str], ...] = (
    ("chromium", "chrome"),
    ("chromium", "msedge"),
    ("chromium", ""),
    ("firefox", ""),
)


class PdfRendererUnavailableError(RuntimeError):
    """Raised when no usable browser is reachable through Playwright."""


def is_pdf_renderer_available() -> bool:
    """Cheap probe: is the ``playwright`` Python package importable?"""
    try:
        import playwright  # noqa: F401  - presence check only
    except ImportError:
        return False
    return True


def render_html_to_pdf(html: str, target: Path | str) -> Path:
    """Render ``html`` to an A4 PDF at ``target``.

    The HTML must be a fully self-contained document (inlined ``<style>``
    is the easy way; remote stylesheets / fonts are best-effort because
    we run the page with ``wait_until='domcontentloaded'`` and a short
    extra ``networkidle`` delay).

    Returns the resolved ``Path`` of the written PDF.

    Raises:
        PdfRendererUnavailableError: Playwright is not installed, or
            none of the supported browsers can be launched on this
            machine. Callers should catch this and fall back.
    """
    try:
        from playwright.sync_api import (  # noqa: PLC0415
            Error as PlaywrightError,
            sync_playwright,
        )
    except ImportError as exc:
        raise PdfRendererUnavailableError(
            "Playwright Python package is not installed. "
            "Run `pip install playwright` and (optionally) "
            "`playwright install chromium` to enable PDF export."
        ) from exc

    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    last_error: Exception | None = None

    with sync_playwright() as p:
        browser = None
        chosen_label = ""
        for kind, channel in _CHANNEL_PREFERENCES:
            launcher = getattr(p, kind, None)
            if launcher is None:
                continue
            try:
                if channel:
                    browser = launcher.launch(channel=channel, headless=True)
                    chosen_label = channel
                else:
                    browser = launcher.launch(headless=True)
                    chosen_label = kind
                logger.info(
                    "PDF renderer launched via kind=%s channel=%r",
                    kind,
                    channel or "<bundled>",
                )
                break
            except PlaywrightError as exc:
                last_error = exc
                logger.debug(
                    "PDF renderer launch failed for kind=%s channel=%r: %s",
                    kind,
                    channel,
                    exc,
                )
            except Exception as exc:  # pragma: no cover - safety net
                last_error = exc
                logger.debug(
                    "Unexpected error launching kind=%s channel=%r: %s",
                    kind,
                    channel,
                    exc,
                )

        if browser is None:
            hint = (
                "Could not launch any system browser through Playwright. "
                "Install Google Chrome or Microsoft Edge (recommended), or "
                "run `playwright install chromium` to get a bundled browser."
            )
            if last_error is not None:
                hint = f"{hint} Last error: {last_error}"
            raise PdfRendererUnavailableError(hint)

        try:
            context = browser.new_context()
            page = context.new_page()
            page.set_default_timeout(20_000)
            page.set_content(html, wait_until="domcontentloaded")
            with suppress(Exception):
                page.wait_for_load_state("networkidle", timeout=8_000)
            if not hasattr(page, "pdf"):
                raise PdfRendererUnavailableError(
                    "Selected browser does not expose a PDF printer. "
                    "Install Chrome / Edge or run `playwright install chromium`."
                )
            try:
                page.pdf(
                    path=str(target_path),
                    format="A4",
                    print_background=True,
                    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                    prefer_css_page_size=True,
                )
            except PlaywrightError as exc:
                raise PdfRendererUnavailableError(
                    f"PDF generation failed in browser={chosen_label}: {exc}"
                ) from exc
            logger.info(
                "PDF renderer wrote %s via browser=%s",
                target_path,
                chosen_label,
            )
        finally:
            with suppress(Exception):
                browser.close()

    return target_path


__all__ = [
    "PdfRendererUnavailableError",
    "is_pdf_renderer_available",
    "render_html_to_pdf",
]
