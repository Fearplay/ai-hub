"""URL → cleaned job-posting text.

The scraper has two layers:

1. **Site-specific dispatcher** for the Alma Career portals (jobs.cz,
   prace.cz, profesia.cz, profesia.sk). They share a common React shell
   where the actual job ad is wrapped in a few well-known elements, but
   the page also contains a long GDPR consent block that easily wins
   the "largest text" heuristic.

2. **Generic fallback** for everything else: pull HTML, drop nav/footer/
   scripts, score the candidates by length, and strip GDPR-flavoured
   paragraphs at the end.

Failure mode: this returns a :class:`ScrapeResult` with ``text=""`` and a
human-readable ``error`` so the UI can prompt the user to paste the text
manually instead of crashing the run.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional
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

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": _USER_AGENT, "Accept-Language": "en,cs;q=0.8"},
        ) as client:
            response = client.get(url)
            response.raise_for_status()
    except Exception as exc:
        return ScrapeResult(url=url, text="", title=None, error=f"Download failed: {exc}")

    host = (parsed.hostname or "").lower()
    text, title = _extract_with_bs4(response.text, host=host)
    if len(text) < 80:
        return ScrapeResult(
            url=url,
            text=text,
            title=title,
            error="Page is too short - likely JS-rendered. Paste the text manually.",
        )

    return ScrapeResult(url=url, text=text, title=title, error=None)
