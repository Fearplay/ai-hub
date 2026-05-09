"""URL → cleaned job-posting text.

The scraper has three layers:

1. **Site-specific dispatcher** for the Alma Career portals (jobs.cz,
   prace.cz, profesia.cz, profesia.sk). They share a common React shell
   where the actual job ad is wrapped in a few well-known elements, but
   the page also contains a long GDPR consent block that easily wins
   the "largest text" heuristic.

2. **Generic httpx fetch + bs4 cleanup** for everything else: pull HTML,
   drop nav/footer/scripts, score the candidates by length, and strip
   GDPR-flavoured paragraphs at the end.

3. **Playwright fallback** when httpx returns 403 or near-empty text
   (typical of Cloudflare-shielded boards or React apps that hydrate the
   description client-side). We launch the user's installed Edge /
   Chrome / Firefox in headless mode via Playwright's ``channel=`` flag,
   render the page, and re-run the bs4 cleanup. No Chromium download
   required - the browser comes from the user's machine.

Failure mode: this returns a :class:`ScrapeResult` with ``text=""`` and a
human-readable ``error`` so the UI can prompt the user to paste the text
manually instead of crashing the run.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Callable, Optional
from urllib.parse import urlparse


_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36 ai-hub/0.1"
)


# Hosts that share the Alma Career platform layout.
_ALMA_HOSTS = (
    "jobs.cz",
    "www.jobs.cz",
    "prace.cz",
    "www.prace.cz",
    "profesia.cz",
    "www.profesia.cz",
    "profesia.sk",
    "www.profesia.sk",
)


# Selectors tried (in order) for Alma Career sites. The first non-empty match
# that survives the GDPR filter wins.
_ALMA_SELECTORS = (
    '[data-jobad="body"]',
    '[data-test*="jobad"]',
    'article[itemprop="description"]',
    '[itemprop="description"]',
    'div[class*="JobAd"]',
    'main [class*="Description"]',
    'main article',
    'main',
)


# Paragraphs containing any of these markers are dropped before we measure
# length (case-insensitive substring match). Keep the list narrow so we
# don't accidentally throw away real job text.
_GDPR_MARKERS = (
    "alma career",
    "osobní údaje",
    "osobni udaje",
    "přístup k osobním údajům",
    "pristup k osobnim udajum",
    "pro účely zaslání",
    "pro ucely zaslani",
    "souhlas se zpracováním",
    "souhlas se zpracovanim",
    "almacareer.com/gdpr",
    "ochranu osobních údajů",
    "ochranu osobnich udaju",
    "úřad pro ochranu",
    "urad pro ochranu",
    "zásady ochrany soukromí",
    "zasady ochrany soukromi",
    "podmínky používání",
    "podminky pouzivani",
    "menclova 2538",
    "pribinova 19",
    "we are a member of alma",
)


@dataclass
class ScrapeResult:
    url: str
    text: str
    title: Optional[str]
    error: Optional[str]

    @property
    def ok(self) -> bool:
        return bool(self.text) and not self.error


def _clean_lines(raw: str) -> str:
    lines = [line.strip() for line in raw.splitlines()]
    lines = [line for line in lines if line]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _strip_gdpr(text: str) -> str:
    """Drop paragraphs that look like a GDPR / cookie consent boilerplate."""
    if not text:
        return text
    paragraphs = re.split(r"\n{2,}", text)
    kept: list[str] = []
    for para in paragraphs:
        haystack = para.lower()
        if any(marker in haystack for marker in _GDPR_MARKERS):
            continue
        kept.append(para)
    return "\n\n".join(kept).strip()


def _extract_alma(soup) -> tuple[str, Optional[str]]:
    """Try Alma Career-specific selectors first, fall back to the generic flow."""
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    for selector in _ALMA_SELECTORS:
        for el in soup.select(selector):
            text = _clean_lines(el.get_text("\n"))
            text = _strip_gdpr(text)
            if len(text) >= 200:
                return text, title

    return "", title


def _extract_with_bs4(html: str, *, host: str) -> tuple[str, Optional[str]]:
    try:
        from bs4 import BeautifulSoup  # type: ignore[import-not-found]
    except ImportError:
        text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
        text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        return _strip_gdpr(_clean_lines(text)), None

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    if host in _ALMA_HOSTS:
        alma_text, alma_title = _extract_alma(soup)
        if alma_text:
            return alma_text, alma_title or title

    candidates: list = []
    for selector in ("main", "article", "[role=main]", "section"):
        for el in soup.select(selector):
            candidates.append(el)
    if not candidates:
        candidates.append(soup.body or soup)

    best_text = ""
    for el in candidates:
        text = _clean_lines(el.get_text("\n"))
        text = _strip_gdpr(text)
        if len(text) > len(best_text):
            best_text = text

    if not best_text:
        best_text = _strip_gdpr(_clean_lines((soup.body or soup).get_text("\n")))

    return best_text, title


def scrape_job_posting(url: str, *, timeout: float = 15.0) -> ScrapeResult:
    url = (url or "").strip()
    if not url:
        return ScrapeResult(url="", text="", title=None, error="Empty URL.")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return ScrapeResult(url=url, text="", title=None, error="URL must start with http(s)://")

    try:
        import httpx  # type: ignore[import-not-found]
    except ImportError:
        return ScrapeResult(
            url=url,
            text="",
            title=None,
            error="The httpx package is missing. Run pip install -r requirements.txt.",
        )

    host = (parsed.hostname or "").lower()
    http_status: Optional[int] = None
    http_error: Optional[str] = None
    text = ""
    title: Optional[str] = None

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": _USER_AGENT, "Accept-Language": "en,cs;q=0.8"},
        ) as client:
            response = client.get(url)
            http_status = response.status_code
            response.raise_for_status()
            text, title = _extract_with_bs4(response.text, host=host)
    except httpx.HTTPStatusError as exc:
        http_status = exc.response.status_code if exc.response is not None else None
        http_error = f"HTTP {http_status}" if http_status else str(exc)
    except Exception as exc:
        http_error = f"Download failed: {exc}"

    needs_fallback = (
        http_status == 403
        or (http_status is not None and 400 <= http_status < 600)
        or len(text) < 80
    )

    if needs_fallback:
        pw_text, pw_title, pw_error = _scrape_with_playwright(url, host=host, timeout=timeout)
        if pw_text and len(pw_text) >= 80:
            return ScrapeResult(url=url, text=pw_text, title=pw_title or title, error=None)
        # Playwright also failed - return whatever we have plus the
        # clearest error from either layer so the user knows why.
        if http_error and pw_error:
            error = f"{http_error}. Browser fallback: {pw_error}"
        elif http_error:
            error = http_error
        elif pw_error:
            error = pw_error
        elif text:
            error = "Page is too short - likely JS-rendered. Paste the text manually."
        else:
            error = "Could not download the page. Paste the text manually."
        return ScrapeResult(url=url, text=pw_text or text, title=pw_title or title, error=error)

    return ScrapeResult(url=url, text=text, title=title, error=None)


# ---------------------------------------------------------------------------
# Playwright fallback
# ---------------------------------------------------------------------------


# Filesystem hints for the rare case where Edge / Chrome don't register
# themselves as Playwright channels (custom installs, portable apps, ...).
# We only need ONE working executable per family - the loop below stops at
# the first hit.
_FIREFOX_HINTS_WIN = (
    r"C:\Program Files\Mozilla Firefox\firefox.exe",
    r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
)


def _find_firefox_exe() -> Optional[str]:
    env = os.environ.get("FIREFOX_EXE")
    if env and os.path.isfile(env):
        return env
    if os.name != "nt":
        return None
    for hint in _FIREFOX_HINTS_WIN:
        if os.path.isfile(hint):
            return hint
    return None


def _scrape_with_playwright(
    url: str,
    *,
    host: str,
    timeout: float,
) -> tuple[str, Optional[str], Optional[str]]:
    """Open ``url`` in a system browser via Playwright and return cleaned text.

    Returns ``(text, title, error)`` - ``text`` empty on failure, ``error``
    non-empty when no browser was reachable. The browsers are tried in
    order of likelihood on Windows: Edge (preinstalled), Chrome (very
    common), Firefox (fallback). Each attempt is timeboxed so a hung
    browser can't freeze the UI thread that called us.
    """
    try:
        # Imported lazily so missing playwright doesn't break the import
        # of this module - the httpx-only path still works.
        from playwright.sync_api import (  # type: ignore[import-not-found]
            Error as PlaywrightError,
            TimeoutError as PlaywrightTimeoutError,
            sync_playwright,
        )
    except ImportError:
        return "", None, "Playwright is not installed - run pip install -r requirements.txt."

    nav_timeout_ms = int(max(timeout, 15.0) * 1000)
    last_error: Optional[str] = None

    try:
        with sync_playwright() as pw:
            attempts: list[tuple[str, Callable[[], object]]] = [
                ("Edge", lambda: pw.chromium.launch(channel="msedge", headless=True)),
                ("Chrome", lambda: pw.chromium.launch(channel="chrome", headless=True)),
            ]
            firefox_exe = _find_firefox_exe()
            if firefox_exe:
                attempts.append(
                    (
                        "Firefox",
                        lambda exe=firefox_exe: pw.firefox.launch(
                            executable_path=exe, headless=True
                        ),
                    )
                )
            else:
                # Try the bundled Playwright Firefox in case the user did
                # run ``playwright install firefox`` at some point.
                attempts.append(("Firefox", lambda: pw.firefox.launch(headless=True)))

            for label, launch in attempts:
                browser = None
                try:
                    browser = launch()
                except PlaywrightError as exc:
                    last_error = f"{label}: {exc}".splitlines()[0]
                    continue
                try:
                    context = browser.new_context(user_agent=_USER_AGENT)
                    page = context.new_page()
                    page.set_default_navigation_timeout(nav_timeout_ms)
                    try:
                        page.goto(url, wait_until="domcontentloaded")
                        # Best-effort wait for late hydration; the catch
                        # below swallows the timeout because the page
                        # may already be fully rendered.
                        try:
                            page.wait_for_load_state(
                                "networkidle", timeout=nav_timeout_ms
                            )
                        except PlaywrightTimeoutError:
                            pass
                        html = page.content()
                    finally:
                        try:
                            context.close()
                        except Exception:
                            pass
                except PlaywrightTimeoutError as exc:
                    last_error = f"{label}: navigation timed out ({exc})".splitlines()[0]
                    continue
                except PlaywrightError as exc:
                    last_error = f"{label}: {exc}".splitlines()[0]
                    continue
                finally:
                    if browser is not None:
                        try:
                            browser.close()
                        except Exception:
                            pass

                text, title = _extract_with_bs4(html, host=host)
                if len(text) >= 80:
                    return text, title, None
                last_error = f"{label}: extracted only {len(text)} chars"
    except Exception as exc:
        return "", None, f"Browser fallback failed to start: {exc}"

    return "", None, last_error or "No system browser (Edge / Chrome / Firefox) reachable."
