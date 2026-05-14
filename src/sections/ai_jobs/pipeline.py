"""Orchestration for the AI Jobs section.

Three stages drive every search:

1. **Discovery** - calls :func:`src.services.ai_provider.run` with
   ``enable_web_search=True`` and no schema. The provider's hosted
   web-search tool returns prose with live URLs.
2. **Extraction** - second :func:`ai_provider.run` call, this time
   with the strict :data:`src.sections.ai_jobs.schema.JOB_LISTINGS_SCHEMA`
   and the discovery prose as the user message. No web search this
   time. We get a clean ``positions`` list.
3. **Verification** - each URL is poked via
   :func:`src.services.job_scraper.scrape_job_posting` (httpx +
   Playwright fallback). Anything that returns 4xx, redirects to a
   "no longer available" page, or comes back near-empty is dropped
   silently. Survivors land on :data:`STATE.results`.

Then there is the optional :func:`save_html` exporter that renders the
results into a single styled HTML file inside ``outputs/jobs-...``.
"""

from __future__ import annotations

import html
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from src.services import ai_provider, job_scraper, settings_store, store
from src.services import logger as logger_service
from src.services.cost_tracker import COST
from src.sections.ai_jobs import data as jobs_data
from src.sections.ai_jobs import prompts, schema
from src.sections.ai_jobs.refs import REFS
from src.sections.ai_jobs.state import (
    MAX_RESULTS_DEFAULT,
    MAX_RESULTS_MAX,
    MAX_RESULTS_MIN,
    STATE,
    UploadedFile,
)


# Number of parallel HTTP verifications. Five is a sweet spot for the
# default 10 results - the LLM call dominates the wall clock anyway.
_VERIFY_WORKERS = 5

# Per-URL verification timeout. Generous enough for cold-start CDN
# responses, tight enough that 5x10 dead links won't freeze the UI.
_VERIFY_TIMEOUT = 12.0


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass
class PipelineResult:
    ok: bool
    error: str = ""
    folder: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _request_full_refresh() -> None:
    """Re-run ``build_view`` for the section on the GUI thread."""
    try:
        from src.app import request_section_refresh
    except Exception as exc:
        logger_service.log_exception(
            "ai_jobs.pipeline", "request_full_refresh_import", exc
        )
        return
    request_section_refresh()


def _set_activity(value: str) -> None:
    """Update the right-hand activity badge from any thread."""
    prev = STATE.activity
    STATE.activity = value
    if prev != value:
        logger_service.log_event(
            "INFO", "ai_jobs.pipeline", "activity_change",
            prev=prev, new=value,
        )
    REFS.request_context_refresh()


def _set_error(stage: str, message: str) -> PipelineResult:
    STATE.activity = "error"
    STATE.last_error = message
    REFS.request_context_refresh()
    logger_service.log_event(
        "ERROR", "ai_jobs.pipeline", f"{stage}_error", message=message,
    )
    return PipelineResult(ok=False, error=message)


def _resolve_lang(output_lang: str) -> str:
    code = (output_lang or "en").strip().lower()
    return code if code in {"en", "cs"} else "en"


def _clamp_max_results(value: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return MAX_RESULTS_DEFAULT
    if n < MAX_RESULTS_MIN:
        return MAX_RESULTS_MIN
    if n > MAX_RESULTS_MAX:
        return MAX_RESULTS_MAX
    return n


def _resolve_location(preset_id: str, custom_text: str) -> tuple[str, str]:
    """Return ``(canonical_query, human_label)`` for the location filter.

    ``preset_id == "custom"`` honours whatever the user typed; everything
    else looks up the entry in :func:`jobs_data.location_presets`. The
    ``query`` is what we feed the prompt, the ``label`` is what we show
    in the saved HTML / history.
    """
    custom_text = (custom_text or "").strip()
    if preset_id == "custom":
        return custom_text, custom_text or "Custom"

    for preset in jobs_data.location_presets("en"):
        if preset["id"] == preset_id:
            return preset["query"], preset["label"]
    return "", "Anywhere"


def _verify_url(url: str) -> Optional[str]:
    """Return ``url`` if the link is alive, else ``None``.

    We delegate to :mod:`src.services.job_scraper` so we share the
    httpx + Playwright fallback the AI Career section already trusts.
    Any URL that returns an error or comes back near-empty is dropped.
    The check is best-effort - if the scraper crashes we drop the URL
    rather than risk surfacing a dead link.
    """
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    try:
        result = job_scraper.scrape_job_posting(url, timeout=_VERIFY_TIMEOUT)
    except Exception as exc:
        logger_service.log_exception(
            "ai_jobs.pipeline", "verify_url_crashed", exc, url=url,
        )
        return None
    if not result.ok:
        logger_service.log_event(
            "INFO", "ai_jobs.pipeline", "verify_url_dropped",
            url=url, error=result.error or "empty",
        )
        return None
    return url


def _provider_call(
    *,
    stage: str,
    system: str,
    user: str,
    schema_dict: Optional[dict],
    schema_name: str,
    max_output_tokens: int,
    enable_web_search: bool,
) -> ai_provider.ProviderResult:
    logger_service.log_event(
        "INFO", "ai_jobs.pipeline", f"{stage}_start",
        web_search=enable_web_search, chars=len(user),
        has_schema=schema_dict is not None,
    )
    try:
        result = ai_provider.run(
            system=system,
            user=user,
            schema=schema_dict,
            schema_name=schema_name,
            max_output_tokens=max_output_tokens,
            enable_web_search=enable_web_search,
            temperature=0.2,
        )
    except ai_provider.ProviderError as exc:
        logger_service.log_exception(
            "ai_jobs.pipeline", f"{stage}_provider_error", exc,
        )
        raise
    except Exception as exc:
        logger_service.log_exception(
            "ai_jobs.pipeline", f"{stage}_unexpected_error", exc,
        )
        raise
    logger_service.log_event(
        "INFO", "ai_jobs.pipeline", f"{stage}_done",
        provider=result.provider, model=result.model,
        tokens_in=result.tokens_in, tokens_out=result.tokens_out,
    )
    return result


def _normalise_position(raw: Any) -> Optional[dict]:
    """Sanitise one schema item into the dict our UI expects.

    Trims whitespace, coerces missing strings to ``""``, and drops the
    record if the URL is structurally bad. The schema already enforces
    presence, but defensive parsing keeps the renderer simple.
    """
    if not isinstance(raw, dict):
        return None
    url = (raw.get("url") or "").strip()
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None
    return {
        "title": (raw.get("title") or "").strip() or "Untitled position",
        "company": (raw.get("company") or "").strip() or "unknown",
        "location": (raw.get("location") or "").strip(),
        "posted": (raw.get("posted") or "").strip(),
        "summary": (raw.get("summary") or "").strip(),
        "url": url,
        "source": (raw.get("source") or "").strip(),
        "work_mode": (raw.get("work_mode") or "unknown").strip().lower(),
    }


# ---------------------------------------------------------------------------
# Search pipeline
# ---------------------------------------------------------------------------


def run_search(*, output_lang: str) -> PipelineResult:
    """Run the full discovery -> extraction -> verification pipeline."""
    output_lang = _resolve_lang(output_lang)
    keywords = STATE.keywords.strip()
    profile_text = STATE.profile_text.strip()
    profile_file = STATE.profile_file
    profile_file_text = (profile_file.text if profile_file else "")
    profile_file_name = (profile_file.name if profile_file else "")
    linkedin_url = STATE.linkedin_url.strip()

    if not (keywords or profile_text or profile_file_text or linkedin_url):
        return _set_error("run_search", "No keywords, CV or bio provided.")

    location_query, location_label = _resolve_location(
        STATE.location_preset, STATE.location_custom,
    )
    boards = jobs_data.preferred_boards(STATE.location_preset)
    max_results = _clamp_max_results(STATE.max_results)
    work_mode = (STATE.work_mode or "any").strip().lower()

    # --- pass 1: discovery (web search) ------------------------------
    _set_activity("searching")
    STATE.last_error = ""
    STATE.last_query = keywords or (profile_text[:80] or profile_file_name)
    STATE.last_query_label = STATE.last_query
    STATE.last_location_label = location_label
    STATE.last_search_at = datetime.now().isoformat(timespec="seconds")
    STATE.last_dropped = 0
    STATE.results = []
    STATE.summary = ""

    try:
        search_system, search_user = prompts.build_search_prompt(
            output_lang=output_lang,
            keywords=keywords,
            location_query=location_query,
            location_label=location_label,
            work_mode=work_mode,
            max_results=max_results,
            profile_text=profile_text,
            profile_file_text=profile_file_text,
            profile_file_name=profile_file_name,
            linkedin_url=linkedin_url,
            preferred_boards=boards,
        )
        discovery = _provider_call(
            stage="discovery",
            system=search_system,
            user=search_user,
            schema_dict=None,
            schema_name="discovery",
            max_output_tokens=2500,
            enable_web_search=True,
        )
    except ai_provider.ProviderError as exc:
        return _set_error("discovery", str(exc))
    except Exception as exc:
        return _set_error("discovery", f"AI search call failed: {exc}")

    discovery_text = (discovery.text or "").strip()
    if not discovery_text:
        return _set_error(
            "discovery",
            "AI returned an empty response. Try again or adjust the keywords.",
        )

    # --- pass 2: extraction (strict JSON) ----------------------------
    _set_activity("extracting")
    try:
        extract_system, extract_user = prompts.build_extraction_prompt(
            output_lang=output_lang,
            discovery_text=discovery_text,
            location_query=location_query,
            work_mode=work_mode,
            max_results=max_results,
        )
        extraction = _provider_call(
            stage="extraction",
            system=extract_system,
            user=extract_user,
            schema_dict=schema.JOB_LISTINGS_SCHEMA,
            schema_name="job_listings",
            max_output_tokens=3000,
            enable_web_search=False,
        )
    except ai_provider.ProviderError as exc:
        return _set_error("extraction", str(exc))
    except Exception as exc:
        return _set_error("extraction", f"AI extraction call failed: {exc}")

    payload = extraction.data
    if not isinstance(payload, dict):
        return _set_error(
            "extraction",
            "AI returned a non-JSON payload. Try again or use a different model.",
        )

    raw_positions = payload.get("positions") or []
    summary_text = (payload.get("summary") or "").strip()

    cleaned: list[dict] = []
    seen_urls: set[str] = set()
    for raw in raw_positions:
        normalised = _normalise_position(raw)
        if not normalised:
            continue
        if normalised["url"] in seen_urls:
            continue
        seen_urls.add(normalised["url"])
        cleaned.append(normalised)
        if len(cleaned) >= max_results:
            break

    if not cleaned:
        STATE.summary = summary_text
        STATE.activity = "ready"
        REFS.request_context_refresh()
        logger_service.log_event(
            "INFO", "ai_jobs.pipeline", "search_zero_results",
            keywords=keywords, location_label=location_label,
        )
        return PipelineResult(ok=True)

    # --- pass 3: verification (parallel HTTP HEAD/GET) ---------------
    _set_activity("verifying")
    verified_urls: set[str] = set()
    with ThreadPoolExecutor(max_workers=_VERIFY_WORKERS) as pool:
        futures = {
            pool.submit(_verify_url, item["url"]): item["url"]
            for item in cleaned
        }
        for future in as_completed(futures):
            url = futures[future]
            try:
                kept = future.result()
            except Exception as exc:
                logger_service.log_exception(
                    "ai_jobs.pipeline", "verify_future_failed", exc, url=url,
                )
                kept = None
            if kept:
                verified_urls.add(kept)

    survivors = [item for item in cleaned if item["url"] in verified_urls]
    dropped = len(cleaned) - len(survivors)

    STATE.results = survivors
    STATE.summary = summary_text
    STATE.last_dropped = dropped
    STATE.activity = "ready"
    REFS.request_context_refresh()

    logger_service.log_event(
        "INFO", "ai_jobs.pipeline", "run_search_done",
        kept=len(survivors), dropped=dropped, keywords=keywords,
        location=location_label,
    )
    return PipelineResult(ok=True)


# ---------------------------------------------------------------------------
# HTML export
# ---------------------------------------------------------------------------


_HTML_CSS = """
:root {
  color-scheme: light dark;
  --bg: #0F172A;
  --surface: #1E293B;
  --surface-2: #273449;
  --text: #F8FAFC;
  --muted: #94A3B8;
  --accent: #6366F1;
  --accent-soft: rgba(99, 102, 241, 0.18);
  --border: rgba(148, 163, 184, 0.20);
}
@media (prefers-color-scheme: light) {
  :root {
    --bg: #F8FAFC;
    --surface: #FFFFFF;
    --surface-2: #F1F5F9;
    --text: #0F172A;
    --muted: #64748B;
    --accent: #4F46E5;
    --accent-soft: rgba(99, 102, 241, 0.10);
    --border: rgba(15, 23, 42, 0.10);
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  padding: 32px 16px 64px;
  line-height: 1.45;
}
.wrap {
  max-width: 880px;
  margin: 0 auto;
}
header.page {
  padding: 24px 28px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  margin-bottom: 24px;
}
header.page h1 {
  margin: 0 0 6px;
  font-size: 22px;
}
header.page p {
  margin: 4px 0;
  color: var(--muted);
  font-size: 13px;
}
.summary {
  background: var(--accent-soft);
  border-left: 3px solid var(--accent);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 24px;
  font-size: 14px;
  line-height: 1.55;
}
ul.positions {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 16px;
}
li.position {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 20px 24px;
}
li.position h2 {
  margin: 0 0 6px;
  font-size: 17px;
}
li.position h2 a {
  color: var(--text);
  text-decoration: none;
}
li.position h2 a:hover {
  color: var(--accent);
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  font-size: 12px;
  color: var(--muted);
  margin: 6px 0 12px;
}
.meta span {
  display: inline-flex;
  align-items: center;
}
.meta strong {
  color: var(--text);
  font-weight: 600;
  margin-right: 4px;
}
.position p.summary-line {
  margin: 0 0 14px;
  font-size: 14px;
}
.position .actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.position .actions a {
  display: inline-block;
  padding: 8px 14px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  background: var(--accent);
  color: #FFFFFF;
}
.position .actions a.secondary {
  background: var(--surface-2);
  color: var(--text);
  border: 1px solid var(--border);
}
.work-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  margin-left: 8px;
  vertical-align: middle;
}
footer.page {
  margin-top: 32px;
  text-align: center;
  font-size: 12px;
  color: var(--muted);
}
""".strip()


def _esc(value: Any) -> str:
    """HTML-escape a value, returning '' for None/empty."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _render_position(item: dict) -> str:
    work_mode = (item.get("work_mode") or "unknown").lower()
    work_pill = (
        f'<span class="work-pill">{_esc(work_mode)}</span>'
        if work_mode in {"remote", "hybrid", "onsite"}
        else ""
    )
    meta_parts: list[str] = []
    if item.get("company"):
        meta_parts.append(f"<span><strong>Company:</strong> {_esc(item['company'])}</span>")
    if item.get("location"):
        meta_parts.append(f"<span><strong>Location:</strong> {_esc(item['location'])}</span>")
    if item.get("posted"):
        meta_parts.append(f"<span><strong>Posted:</strong> {_esc(item['posted'])}</span>")
    if item.get("source"):
        meta_parts.append(f"<span><strong>Source:</strong> {_esc(item['source'])}</span>")
    meta_html = "".join(meta_parts)

    summary_html = (
        f'<p class="summary-line">{_esc(item["summary"])}</p>'
        if item.get("summary")
        else ""
    )

    return (
        '<li class="position">'
        f'<h2><a href="{_esc(item["url"])}" target="_blank" rel="noopener">'
        f'{_esc(item["title"])}</a>{work_pill}</h2>'
        f'<div class="meta">{meta_html}</div>'
        f'{summary_html}'
        '<div class="actions">'
        f'<a href="{_esc(item["url"])}" target="_blank" rel="noopener">Open posting</a>'
        f'<a class="secondary" href="{_esc(item["url"])}" target="_blank" rel="noopener">View URL</a>'
        '</div>'
        '</li>'
    )


def _render_html(*, query: str, location_label: str, summary: str, items: list[dict]) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    summary_block = (
        f'<section class="summary">{_esc(summary)}</section>'
        if (summary or "").strip()
        else ""
    )
    positions_html = "\n".join(_render_position(item) for item in items)
    title_text = f"Job search - {query}" if query else "Job search results"
    return (
        "<!doctype html>\n"
        "<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\" />\n"
        f"<title>{_esc(title_text)}</title>\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />\n"
        "<style>\n"
        + _HTML_CSS
        + "\n</style>\n"
        "</head>\n<body>\n"
        '<div class="wrap">\n'
        '<header class="page">\n'
        f'<h1>{_esc(title_text)}</h1>\n'
        f'<p><strong>Query:</strong> {_esc(query) or "&mdash;"}</p>\n'
        f'<p><strong>Location:</strong> {_esc(location_label) or "&mdash;"}</p>\n'
        f'<p><strong>Generated:</strong> {_esc(timestamp)} &middot; {_esc(len(items))} active position(s)</p>\n'
        '</header>\n'
        + summary_block + "\n"
        + '<ul class="positions">\n'
        + positions_html + "\n"
        + '</ul>\n'
        '<footer class="page">Generated by AI Hub - links verified at export time. They may go offline later.</footer>\n'
        '</div>\n'
        "</body>\n</html>\n"
    )


def save_html(*, output_lang: str) -> PipelineResult:
    """Persist the current results to a fresh ``outputs/jobs-...`` folder.

    Writes one ``results.html`` and a small ``summary.json`` mirroring
    the in-memory state (so the History tab can later list the search
    without re-running it). Appends a row to the global
    ``~/AI Hub/history.json`` so it shows up alongside other section
    runs.
    """
    output_lang = _resolve_lang(output_lang)
    if not STATE.has_results():
        return _set_error("save_html", "No results to save.")

    _set_activity("saving")
    try:
        run_dir = store.new_run_dir(role=STATE.last_query or "ai-jobs", company="search")
    except Exception as exc:
        return _set_error("save_html", f"Could not create output folder: {exc}")

    html_text = _render_html(
        query=STATE.last_query or STATE.last_query_label,
        location_label=STATE.last_location_label,
        summary=STATE.summary,
        items=STATE.results,
    )

    try:
        target = store.write_text_file(run_dir, "results.html", html_text)
    except Exception as exc:
        return _set_error("save_html", f"Could not write HTML file: {exc}")

    payload: dict[str, Any] = {
        "type": "ai_jobs",
        "created": datetime.now().isoformat(timespec="seconds"),
        "query": STATE.last_query,
        "location": STATE.last_location_label,
        "work_mode": STATE.work_mode,
        "max_results": STATE.max_results,
        "summary": STATE.summary,
        "dropped": STATE.last_dropped,
        "positions": STATE.results,
    }
    try:
        store.write_json_file(run_dir, "summary.json", payload)
    except Exception as exc:
        logger_service.log_exception(
            "ai_jobs.pipeline", "save_html_summary_failed", exc,
        )

    summary_record = store.RunSummary(
        timestamp=datetime.now().isoformat(timespec="seconds"),
        role=STATE.last_query or "AI Job Search",
        company=STATE.last_location_label or "",
        overall_score=len(STATE.results),
        folder=str(run_dir),
        provider=settings_store.get_provider(),
        model=settings_store.get_model(),
        cost_usd=0.0,
        docs=["results.html"],
        note="ai-jobs",
    )
    try:
        store.append_run(summary_record)
    except Exception as exc:
        logger_service.log_exception(
            "ai_jobs.pipeline", "save_html_history_failed", exc,
        )

    history_entry = {
        "timestamp": summary_record.timestamp,
        "query": STATE.last_query,
        "location": STATE.last_location_label,
        "count": len(STATE.results),
        "folder": str(run_dir),
    }
    STATE.runs_history.insert(0, history_entry)
    STATE.runs_history = STATE.runs_history[:50]
    STATE.last_run_folder = str(run_dir)
    STATE.activity = "ready"
    REFS.request_context_refresh()

    logger_service.log_event(
        "INFO", "ai_jobs.pipeline", "save_html_done",
        folder=str(run_dir), count=len(STATE.results), file=str(target),
    )
    return PipelineResult(ok=True, folder=str(run_dir))


# ---------------------------------------------------------------------------
# History helpers
# ---------------------------------------------------------------------------


def list_saved_runs() -> list[dict]:
    """Return jobs runs from disk, newest first.

    Reads ``~/AI Hub/history.json`` via :func:`store.list_runs` and
    keeps only entries whose ``note == "ai-jobs"`` (so we don't show
    AI Career / AI Finance runs in our History tab). Each entry is
    enriched with the in-folder ``summary.json`` data when available
    so the row can show "12 positions, Czech Republic".
    """
    out: list[dict] = []
    try:
        runs = store.list_runs()
    except Exception as exc:
        logger_service.log_exception(
            "ai_jobs.pipeline", "list_saved_runs_failed", exc,
        )
        return out

    for run in runs:
        if (run.note or "").strip().lower() != "ai-jobs":
            continue
        record: dict[str, Any] = {
            "timestamp": run.timestamp,
            "query": run.role,
            "location": run.company,
            "count": run.overall_score,
            "folder": run.folder,
        }
        try:
            summary = store.read_run_summary(run.folder) or {}
            if summary.get("query"):
                record["query"] = summary.get("query")
            if summary.get("location"):
                record["location"] = summary.get("location")
            positions = summary.get("positions") or []
            if positions:
                record["count"] = len(positions)
        except Exception as exc:
            logger_service.log_exception(
                "ai_jobs.pipeline", "list_saved_runs_summary_failed", exc,
                folder=run.folder,
            )
        out.append(record)
    return out


def delete_run(folder: str) -> bool:
    """Delete a saved run folder + remove it from history.json.

    Returns ``True`` when the disk delete succeeded. Errors are logged
    but never raised - the caller usually shows a toast on failure.
    """
    if not folder:
        return False
    target = Path(folder)
    success = True
    try:
        if target.exists():
            for child in target.glob("*"):
                try:
                    child.unlink()
                except Exception as exc:
                    logger_service.log_exception(
                        "ai_jobs.pipeline", "delete_run_unlink_failed", exc,
                        path=str(child),
                    )
                    success = False
            try:
                target.rmdir()
            except Exception as exc:
                logger_service.log_exception(
                    "ai_jobs.pipeline", "delete_run_rmdir_failed", exc,
                    path=str(target),
                )
                success = False
    except Exception as exc:
        logger_service.log_exception(
            "ai_jobs.pipeline", "delete_run_failed", exc, folder=folder,
        )
        success = False

    # Drop the matching row from the global history.json. We rewrite
    # the whole list because store does not expose a remove() helper.
    try:
        history_path = store.history_path()
        if history_path.exists():
            try:
                raw = json.loads(history_path.read_text(encoding="utf-8")) or []
            except json.JSONDecodeError:
                raw = []
            target_norm = folder.rstrip("\\/").strip()
            keep = [
                row for row in raw
                if (row.get("folder") or "").rstrip("\\/").strip() != target_norm
            ]
            if len(keep) != len(raw):
                history_path.parent.mkdir(parents=True, exist_ok=True)
                history_path.write_text(
                    json.dumps(keep, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
    except Exception as exc:
        logger_service.log_exception(
            "ai_jobs.pipeline", "delete_run_history_rewrite_failed", exc,
            folder=folder,
        )

    STATE.runs_history = [
        entry for entry in STATE.runs_history
        if entry.get("folder") != folder
    ]
    if STATE.last_run_folder == folder:
        STATE.last_run_folder = ""
    return success


_STARTUP_LOCK = threading.Lock()
_STARTUP_DONE: dict[str, bool] = {"hydrated": False}


def warm_runs_history_once() -> None:
    """Populate ``STATE.runs_history`` from disk on the first build.

    Idempotent - the lock + flag stop us from re-reading the JSON on
    every section refresh. Safe to call from the GUI thread; the disk
    read is small enough that we don't need to push it onto a worker.
    """
    if _STARTUP_DONE["hydrated"]:
        return
    with _STARTUP_LOCK:
        if _STARTUP_DONE["hydrated"]:
            return
        STATE.runs_history = list_saved_runs()
        _STARTUP_DONE["hydrated"] = True
