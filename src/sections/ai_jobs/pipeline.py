"""Orchestration for the AI Jobs section.

Five stages drive every search:

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
   silently.
4. **Scoring** - per-position match score (Pass 4). Each survived
   posting is sent to ``ai_provider.run`` with
   :data:`schema.MATCH_SCHEMA` and the user's profile. We attach the
   resulting ``match_score`` / ``matched_skills`` / ``missing_skills``
   / ``recommendation`` to the dict. Runs in a thread pool so the
   wall clock stays sane on 10+ positions.
5. **Skill gap** - aggregated analysis (Pass 5). One call that sees
   every scored position + the profile and emits
   :data:`schema.SKILL_GAP_SCHEMA`. Skipped when the user did not
   supply any profile material (nothing to compare against).

Then there is the optional :func:`save_html` exporter that renders the
results into a single rich HTML file inside ``outputs/jobs-...``.
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
from src.sections.ai_jobs.strings import s


# Number of parallel HTTP verifications. Five is a sweet spot for the
# default 10 results - the LLM call dominates the wall clock anyway.
_VERIFY_WORKERS = 5

# Per-URL verification timeout. Generous enough for cold-start CDN
# responses, tight enough that 5x10 dead links won't freeze the UI.
_VERIFY_TIMEOUT = 12.0

# Per-position scoring (Pass 4) workers. Same cap as the verifier -
# OpenAI / Anthropic both rate-limit on per-key concurrency, so 5
# in-flight calls is a safe ceiling for the default model tier.
_SCORE_WORKERS = 5

# Over-fetch tuning ----------------------------------------------------
# The user picks ``max_results`` (3-25) - that is the number of postings
# they want to be able to *apply* to. Many discovered URLs end up being
# expired or 404'd by Pass 3, so we ask the discovery / extraction
# passes for a wider net of candidates and trim post-verification.
#
# ``_CANDIDATE_OVERFETCH`` is the multiplier applied to the user's
# ``max_results`` to derive the candidate target. ``_CANDIDATE_CAP`` is
# the absolute ceiling so token costs stay sane for max_results=25.
_CANDIDATE_OVERFETCH = 2
_CANDIDATE_CAP = 40

# How many extra strict-mode discovery passes we are willing to spend
# per run when verification leaves us short of the user's target. We
# try up to three strict top-ups before falling back to the relaxed
# pass below - that matches the user contract "always try to hit the
# active target first, before broadening the search".
_MAX_TOPUP_ATTEMPTS = 3

# After the strict top-ups exhaust, we are allowed exactly one relaxed
# pass: search_mode is overridden to ``"broad"`` and the prompt asks
# the model to widen the geography / consider adjacent roles. The
# resulting postings are flagged ``is_relaxed=True`` so the UI can
# render a "Less relevant" pill - they still count toward the active
# target (per user contract: "if relevance has to drop, that's fine,
# still give me the number I asked for") but are surfaced as such.
_MAX_RELAXED_ATTEMPTS = 1

# Inactive-listings transparency cap. The user explicitly asked for
# closed listings to stay visible "so I can verify detection works",
# but we still need a hard ceiling so the page is never 50 cards long
# when an unlucky run returns mostly dead URLs. ``max_results`` is the
# natural ceiling - the closed-listings section is at most as tall as
# the active-listings section. ``_INACTIVE_FALLBACK_CAP`` kicks in for
# small targets (e.g. max_results=3 → still show up to 5 closed).
_INACTIVE_FALLBACK_CAP = 5


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


def _verify_listing(url: str) -> Optional[dict]:
    """Probe ``url`` and return a small dict describing its status.

    Returns ``None`` only when the URL is structurally bad or the
    scraper crashes hard (DNS failure, SSL error, etc.) so we have
    literally nothing to show the user.

    Otherwise returns ``{"url": str, "active": bool, "marker": str}``:

    * ``active=True`` and ``marker=""`` for live postings.
    * ``active=False`` and ``marker=<phrase>`` when the page is
      reachable but the listing itself is closed / expired / 404'd.
      We KEEP these results (per user direction: "marka them so I
      can evaluate") so the user can verify detection works on the
      Results tab; we just label them clearly.

    Detection sources (in order):

    1. **HTTP status** - 404 / 410 → ``"HTTP 404"`` / ``"HTTP 410"``.
       Skips 401 / 403 / 429 because those mean "blocked / rate
       limited", not "the job is gone".
    2. **Banner markers** in the cleaned body, page title, AND raw
       HTML text dump. The raw dump is essential because LinkedIn
       puts "Už nepřijímá žádosti" inside an ``<aside>`` that the
       cleaned-text extractor strips out.
    3. **Hard scrape failures** that returned empty text but no
       parseable error - we keep them with marker
       ``"unreachable"`` so the user sees why the link is suspect.
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

    status = result.status
    status_marker = ""
    if status == 404:
        status_marker = "HTTP 404"
    elif status == 410:
        status_marker = "HTTP 410"
    elif status is not None and 400 <= status < 500 and status not in (401, 403, 429):
        status_marker = f"HTTP {status}"

    body_marker = job_scraper.detect_inactive(
        result.text or "",
        title=result.title or "",
        raw_text=result.raw_text or "",
    ) or ""

    marker = body_marker or status_marker

    if not result.ok and not marker:
        # Hard failure (DNS / SSL / timeout). Keep the URL with an
        # "unreachable" badge instead of dropping silently.
        logger_service.log_event(
            "INFO", "ai_jobs.pipeline", "verify_url_unreachable",
            url=url, error=result.error or "empty", status=status,
        )
        return {"url": url, "active": False, "marker": "unreachable"}

    if marker:
        logger_service.log_event(
            "INFO", "ai_jobs.pipeline", "verify_url_inactive",
            url=url, marker=marker, status=status,
            via_status=bool(status_marker and not body_marker),
        )
    return {"url": url, "active": not marker, "marker": marker}


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
    contract = (raw.get("contract_type") or "unknown").strip().lower()
    if contract not in {
        "hpp", "ico", "contract", "dpp_dpc", "internship", "freelance", "unknown",
    }:
        contract = "unknown"
    return {
        "title": (raw.get("title") or "").strip() or "Untitled position",
        "company": (raw.get("company") or "").strip() or "unknown",
        "location": (raw.get("location") or "").strip(),
        "posted": (raw.get("posted") or "").strip(),
        "posted_date_iso": (raw.get("posted_date_iso") or "").strip(),
        "salary_text": (raw.get("salary_text") or "").strip(),
        "contract_type": contract,
        "summary": (raw.get("summary") or "").strip(),
        "url": url,
        "source": (raw.get("source") or "").strip(),
        "work_mode": (raw.get("work_mode") or "unknown").strip().lower(),
        # Pass 3 outputs (overwritten by the verifier when active-link
        # checks are enabled). Default to "active" so the UI does not
        # accidentally tag fresh extractions as expired before the
        # verification pass runs.
        "is_active": True,
        "inactive_reason": "",
        # Whether this row came from the relaxed broad-search pass that
        # fires when strict top-ups cannot reach ``target_active``.
        # ``False`` for the initial discovery and every strict top-up;
        # the relaxed pass below flips this to ``True`` post-extraction.
        "is_relaxed": False,
        # Pass 4 outputs (filled in later, default to empty for templating).
        "match_score": None,
        "matched_skills": [],
        "missing_skills": [],
        "recommendation": "",
    }


# ---------------------------------------------------------------------------
# Search pipeline
# ---------------------------------------------------------------------------


def _run_discovery_extraction(
    *,
    output_lang: str,
    keywords: str,
    location_query: str,
    location_label: str,
    work_mode: str,
    profile_text: str,
    profile_file_text: str,
    profile_file_name: str,
    linkedin_url: str,
    boards: list[str],
    tech_skills: str,
    additional_experience: str,
    seniority: str,
    excluded_keywords: str,
    excluded_companies: str,
    excluded_locations: str,
    excluded_work_types: tuple[str, ...],
    custom_source_urls: str,
    age_days: int,
    contract_types: tuple[str, ...],
    search_mode: str,
    salary_min: int,
    salary_currency: str,
    candidate_target: int,
    target_active: int,
    excluded_urls: tuple[str, ...] = (),
    stage_prefix: str = "",
    relaxed_pass: bool = False,
) -> tuple[list[dict], str]:
    """Run pass 1 (web-search discovery) + pass 2 (JSON extraction).

    Returns ``(cleaned_positions, summary_text)``. ``cleaned_positions``
    is already deduplicated and capped at ``candidate_target``.

    The same helper drives the initial discovery, the strict top-up
    passes (up to :data:`_MAX_TOPUP_ATTEMPTS`), and the single relaxed
    pass that fires after the strict top-ups exhaust. The differences
    are:

    - ``candidate_target`` controls how many candidates we ask for.
    - ``excluded_urls`` is the URLs the caller already has - the
      prompt asks the model to return DIFFERENT ones.
    - ``search_mode`` is whatever the user picked for strict passes
      and is forced to ``"broad"`` for the relaxed pass.
    - ``relaxed_pass=True`` adds an explicit "broaden to adjacent
      roles / nearby cities" instruction block to the prompt and is
      threaded into the post-extraction ``is_relaxed`` flag.

    Raises :class:`ai_provider.ProviderError` on hard provider failure
    so the caller can decide whether to short-circuit (initial pass)
    or just fall back to whatever it already has (top-up + relaxed
    passes both treat the failure as "no extra results").
    """
    discovery_stage = f"{stage_prefix}discovery" if stage_prefix else "discovery"
    extraction_stage = f"{stage_prefix}extraction" if stage_prefix else "extraction"

    search_system, search_user = prompts.build_search_prompt(
        output_lang=output_lang,
        keywords=keywords,
        location_query=location_query,
        location_label=location_label,
        work_mode=work_mode,
        max_results=candidate_target,
        target_active=target_active,
        profile_text=profile_text,
        profile_file_text=profile_file_text,
        profile_file_name=profile_file_name,
        linkedin_url=linkedin_url,
        preferred_boards=boards,
        tech_skills=tech_skills,
        additional_experience=additional_experience,
        seniority=seniority,
        excluded_keywords=excluded_keywords,
        excluded_companies=excluded_companies,
        excluded_locations=excluded_locations,
        excluded_work_types=excluded_work_types,
        custom_source_urls=custom_source_urls,
        job_age_days=age_days,
        contract_types=contract_types,
        search_mode=search_mode,
        salary_min=salary_min,
        salary_currency=salary_currency,
        excluded_urls=excluded_urls,
        relaxed_pass=relaxed_pass,
    )
    discovery = _provider_call(
        stage=discovery_stage,
        system=search_system,
        user=search_user,
        schema_dict=None,
        schema_name="discovery",
        max_output_tokens=3500,
        enable_web_search=True,
    )

    discovery_text = (discovery.text or "").strip()
    if not discovery_text:
        return [], ""

    extract_system, extract_user = prompts.build_extraction_prompt(
        output_lang=output_lang,
        discovery_text=discovery_text,
        location_query=location_query,
        work_mode=work_mode,
        max_results=candidate_target,
        excluded_urls=excluded_urls,
    )
    extraction = _provider_call(
        stage=extraction_stage,
        system=extract_system,
        user=extract_user,
        schema_dict=schema.JOB_LISTINGS_SCHEMA,
        schema_name="job_listings",
        max_output_tokens=4500,
        enable_web_search=False,
    )

    payload = extraction.data
    if not isinstance(payload, dict):
        raise ai_provider.ProviderError(
            "AI returned a non-JSON payload. Try again or use a different model."
        )

    raw_positions = payload.get("positions") or []
    summary_text = (payload.get("summary") or "").strip()

    excluded_set = {(u or "").strip() for u in (excluded_urls or ()) if u}
    cleaned: list[dict] = []
    seen_urls: set[str] = set(excluded_set)
    for raw in raw_positions:
        normalised = _normalise_position(raw)
        if not normalised:
            continue
        if normalised["url"] in seen_urls:
            continue
        seen_urls.add(normalised["url"])
        if relaxed_pass:
            normalised["is_relaxed"] = True
        cleaned.append(normalised)
        if len(cleaned) >= candidate_target:
            break
    return cleaned, summary_text


def _run_verification(cleaned: list[dict]) -> tuple[list[dict], int]:
    """Run pass 3 (parallel URL verification) on a candidate list.

    Returns ``(survivors, dropped)``. ``survivors`` keeps every item the
    verifier could decide on (active OR inactive) - each gets the
    ``is_active`` and ``inactive_reason`` fields populated. ``dropped``
    is the count of candidates the verifier returned ``None`` for (rare
    - usually means the scraper crashed hard before returning a verdict).
    """
    if not cleaned:
        return [], 0
    verified_status: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=_VERIFY_WORKERS) as pool:
        futures = {
            pool.submit(_verify_listing, item["url"]): item["url"]
            for item in cleaned
        }
        for future in as_completed(futures):
            url = futures[future]
            try:
                status = future.result()
            except Exception as exc:
                logger_service.log_exception(
                    "ai_jobs.pipeline", "verify_future_failed", exc, url=url,
                )
                status = None
            if status:
                verified_status[status["url"]] = status
    survivors: list[dict] = []
    for item in cleaned:
        status = verified_status.get(item["url"])
        if status is None:
            continue
        item["is_active"] = bool(status.get("active", True))
        item["inactive_reason"] = str(status.get("marker") or "")
        survivors.append(item)
    return survivors, len(cleaned) - len(survivors)


@logger_service.timed_call("ai_jobs.pipeline", "run_search")
def run_search(*, output_lang: str) -> PipelineResult:
    """Run the full discovery -> extraction -> verification -> scoring -> gap pipeline.

    The search uses **over-fetch + top-up** to give the user the count
    of *applicable* postings they asked for: the discovery + extraction
    passes ask for ``max_results * _CANDIDATE_OVERFETCH`` candidates
    (capped at ``_CANDIDATE_CAP``), URL verification splits them into
    active / inactive, and a follow-up discovery pass fires if active
    survivors are still below the target. The user never wants "15
    postings, 12 of them dead"; they want 15 they can apply to.
    """
    output_lang = jobs_data.resolve_output_language(
        picker_value=STATE.output_language,
        global_lang=output_lang,
    )

    keywords = STATE.keywords.strip()
    profile_text = STATE.profile_text.strip()
    profile_file = STATE.profile_file
    profile_file_text = (profile_file.text if profile_file else "")
    profile_file_name = (profile_file.name if profile_file else "")
    linkedin_url = STATE.linkedin_url.strip()
    tech_skills = STATE.tech_skills.strip()
    additional_experience = STATE.additional_experience.strip()

    if not STATE.can_run():
        return _set_error("run_search", "No keywords, CV, bio, LinkedIn URL, or skills provided.")

    location_query, location_label = _resolve_location(
        STATE.location_preset, STATE.location_custom,
    )
    boards = jobs_data.resolve_source_hints(
        selected_ids=STATE.selected_sources,
        location_preset_id=STATE.location_preset,
    )
    target_active = _clamp_max_results(STATE.max_results)
    candidate_target = min(target_active * _CANDIDATE_OVERFETCH, _CANDIDATE_CAP)
    work_mode = (STATE.work_mode or "any").strip().lower()
    age_days = jobs_data.job_age_days(STATE.job_age)

    # --- reset run-scoped state --------------------------------------
    _set_activity("searching")
    STATE.last_error = ""
    STATE.last_query = keywords or (profile_text[:80] or profile_file_name or tech_skills[:80])
    STATE.last_query_label = STATE.last_query
    STATE.last_location_label = location_label
    STATE.last_search_at = datetime.now().isoformat(timespec="seconds")
    STATE.last_dropped = 0
    STATE.last_inactive = 0
    STATE.results = []
    STATE.summary = ""
    STATE.skill_gap = {}

    common_args = dict(
        output_lang=output_lang,
        keywords=keywords,
        location_query=location_query,
        location_label=location_label,
        work_mode=work_mode,
        profile_text=profile_text,
        profile_file_text=profile_file_text,
        profile_file_name=profile_file_name,
        linkedin_url=linkedin_url,
        boards=list(boards),
        tech_skills=tech_skills,
        additional_experience=additional_experience,
        seniority=STATE.seniority,
        excluded_keywords=STATE.excluded_keywords,
        excluded_companies=STATE.excluded_companies,
        excluded_locations=STATE.excluded_locations,
        excluded_work_types=tuple(STATE.excluded_work_types),
        custom_source_urls=STATE.custom_source_urls,
        age_days=age_days,
        contract_types=tuple(STATE.contract_types),
        search_mode=STATE.search_mode,
        salary_min=int(STATE.salary_min or 0),
        salary_currency=STATE.salary_currency,
    )

    # --- pass 1 + 2: discovery + extraction --------------------------
    try:
        cleaned, summary_text = _run_discovery_extraction(
            **common_args,
            candidate_target=candidate_target,
            target_active=target_active,
            excluded_urls=(),
            stage_prefix="",
        )
    except ai_provider.ProviderError as exc:
        return _set_error("discovery", str(exc))
    except Exception as exc:
        return _set_error("discovery", f"AI search call failed: {exc}")

    if not cleaned:
        STATE.summary = summary_text
        STATE.activity = "ready"
        REFS.request_context_refresh()
        logger_service.log_event(
            "INFO", "ai_jobs.pipeline", "search_zero_results",
            keywords=keywords, location_label=location_label,
            candidate_target=candidate_target, target_active=target_active,
        )
        return PipelineResult(ok=True)

    logger_service.log_event(
        "INFO", "ai_jobs.pipeline", "discovery_pass_done",
        candidates=len(cleaned), candidate_target=candidate_target,
        target_active=target_active,
    )

    # --- pass 3: verification ---------------------------------------
    if STATE.verify_active_links:
        _set_activity("verifying")
        survivors, dropped = _run_verification(cleaned)
    else:
        survivors = cleaned
        for item in survivors:
            item.setdefault("is_active", True)
            item.setdefault("inactive_reason", "")
            item.setdefault("is_relaxed", False)
        dropped = 0
        logger_service.log_event(
            "INFO", "ai_jobs.pipeline", "verify_skipped_by_user",
        )

    # --- top-up: fire only if verification is on and we are short ---
    #
    # User contract:
    #   1. Try the strict filters first - up to ``_MAX_TOPUP_ATTEMPTS``
    #      extra passes asking for DIFFERENT URLs (the previous list
    #      is forwarded to the prompt as ``excluded_urls``).
    #   2. If we are still short, run ONE relaxed pass with
    #      ``search_mode="broad"`` AND a prompt hint that broadens the
    #      geography / accepts adjacent roles. Results from this pass
    #      are flagged ``is_relaxed=True`` so the UI labels them as
    #      "less relevant".
    #   3. Closed / inactive listings are never counted toward
    #      ``target_active``; they are surfaced separately with their
    #      own cap (``_INACTIVE_FALLBACK_CAP``).
    strict_attempts = 0
    relaxed_attempts = 0
    if STATE.verify_active_links:
        active_count = sum(1 for it in survivors if it.get("is_active", True))

        # Strict top-ups -------------------------------------------------
        while active_count < target_active and strict_attempts < _MAX_TOPUP_ATTEMPTS:
            strict_attempts += 1
            needed = target_active - active_count
            topup_target = min(needed * _CANDIDATE_OVERFETCH, _CANDIDATE_CAP)
            seen_urls = tuple(item["url"] for item in survivors)
            logger_service.log_event(
                "INFO", "ai_jobs.pipeline", "topup_start",
                attempt=strict_attempts, needed=needed,
                candidate_target=topup_target, already_seen=len(seen_urls),
            )
            _set_activity("searching")
            try:
                extra_cleaned, _extra_summary = _run_discovery_extraction(
                    **common_args,
                    candidate_target=topup_target,
                    target_active=needed,
                    excluded_urls=seen_urls,
                    stage_prefix=f"topup{strict_attempts}_",
                )
            except ai_provider.ProviderError as exc:
                logger_service.log_event(
                    "WARN", "ai_jobs.pipeline", "topup_provider_error",
                    attempt=strict_attempts, message=str(exc),
                )
                break
            except Exception as exc:
                logger_service.log_exception(
                    "ai_jobs.pipeline", "topup_unexpected_error", exc,
                    attempt=strict_attempts,
                )
                break

            if not extra_cleaned:
                logger_service.log_event(
                    "INFO", "ai_jobs.pipeline", "topup_no_new_candidates",
                    attempt=strict_attempts,
                )
                break

            _set_activity("verifying")
            extra_survivors, extra_dropped = _run_verification(extra_cleaned)
            survivors.extend(extra_survivors)
            dropped += extra_dropped
            extra_active = sum(1 for it in extra_survivors if it.get("is_active", True))
            active_count += extra_active
            logger_service.log_event(
                "INFO", "ai_jobs.pipeline", "topup_done",
                attempt=strict_attempts, candidates=len(extra_cleaned),
                survivors=len(extra_survivors), new_active=extra_active,
                running_active=active_count, target_active=target_active,
            )

        # Relaxed pass (single attempt, only if strict failed) ----------
        if active_count < target_active and relaxed_attempts < _MAX_RELAXED_ATTEMPTS:
            relaxed_attempts += 1
            needed = target_active - active_count
            relaxed_target = min(needed * _CANDIDATE_OVERFETCH, _CANDIDATE_CAP)
            seen_urls = tuple(item["url"] for item in survivors)
            logger_service.log_event(
                "INFO", "ai_jobs.pipeline", "relaxed_topup_start",
                strict_attempts=strict_attempts, needed=needed,
                candidate_target=relaxed_target, already_seen=len(seen_urls),
            )
            _set_activity("searching")
            # Force broad mode for the relaxed pass; we still feed the
            # original ``search_mode`` everywhere else so the strict
            # cycle behaves the way the user asked.
            relaxed_args = dict(common_args)
            relaxed_args["search_mode"] = "broad"
            try:
                relaxed_cleaned, _relaxed_summary = _run_discovery_extraction(
                    **relaxed_args,
                    candidate_target=relaxed_target,
                    target_active=needed,
                    excluded_urls=seen_urls,
                    stage_prefix="relaxed_",
                    relaxed_pass=True,
                )
            except ai_provider.ProviderError as exc:
                logger_service.log_event(
                    "WARN", "ai_jobs.pipeline", "relaxed_topup_provider_error",
                    message=str(exc),
                )
                relaxed_cleaned = []
            except Exception as exc:
                logger_service.log_exception(
                    "ai_jobs.pipeline", "relaxed_topup_unexpected_error", exc,
                )
                relaxed_cleaned = []

            if relaxed_cleaned:
                _set_activity("verifying")
                extra_survivors, extra_dropped = _run_verification(relaxed_cleaned)
                # Defensive: _run_discovery_extraction already flagged
                # everything from this pass as relaxed, but flag again
                # so logic does not break if a future caller mutates
                # the position dict in between.
                for item in extra_survivors:
                    item["is_relaxed"] = True
                survivors.extend(extra_survivors)
                dropped += extra_dropped
                extra_active = sum(1 for it in extra_survivors if it.get("is_active", True))
                active_count += extra_active
                logger_service.log_event(
                    "INFO", "ai_jobs.pipeline", "relaxed_topup_done",
                    candidates=len(relaxed_cleaned),
                    survivors=len(extra_survivors), new_active=extra_active,
                    running_active=active_count, target_active=target_active,
                )
            else:
                logger_service.log_event(
                    "INFO", "ai_jobs.pipeline", "relaxed_topup_no_new_candidates",
                )

    # --- split + trim before scoring (saves tokens) ------------------
    active_items = [it for it in survivors if it.get("is_active", True)]
    inactive_items = [it for it in survivors if not it.get("is_active", True)]

    # Inactive items are kept for transparency so the user can verify
    # that the dead-link detection actually works. The cap stops a bad
    # run from rendering a wall of red pills - we never show more
    # closed listings than the user's "active" target (with a small
    # floor so users who pick max_results=3 still see a few examples).
    inactive_cap = max(min(len(inactive_items), target_active), _INACTIVE_FALLBACK_CAP)
    inactive_cap = min(inactive_cap, len(inactive_items))

    # --- pass 4: per-position scoring (active items only) -----------
    # Inactive items are unactionable - paying for an LLM "match
    # analysis" on a closed posting is wasted spend. We still render
    # the card (with match_score=None) so the user sees the badge.
    if active_items and STATE.has_profile():
        _score_positions(
            active_items,
            output_lang=output_lang,
            tech_skills=tech_skills,
            additional_experience=additional_experience,
            profile_text=profile_text,
            profile_file_text=profile_file_text,
            profile_file_name=profile_file_name,
            linkedin_url=linkedin_url,
        )
    elif active_items:
        logger_service.log_event(
            "INFO", "ai_jobs.pipeline", "scoring_skipped_no_profile",
            survivors=len(active_items),
        )

    # Sort: strict matches first, relaxed matches next, then inactive.
    # Within each tier the primary key is the match score (desc) and
    # the tie-breaker is the posted date (desc). Python's stable-sort
    # guarantee lets us layer multiple sort() calls instead of writing
    # one giant key function.
    active_items.sort(
        key=lambda item: item.get("posted_date_iso") or "",
        reverse=True,
    )
    active_items.sort(
        key=lambda item: -(item.get("match_score") or -1),
    )
    # Strict (is_relaxed=False) ends up before relaxed (is_relaxed=True)
    # because Python sorts False < True in ascending order.
    active_items.sort(
        key=lambda item: bool(item.get("is_relaxed", False)),
    )
    inactive_items.sort(
        key=lambda item: item.get("posted_date_iso") or "",
        reverse=True,
    )

    kept_active = active_items[:target_active]
    kept_inactive = inactive_items[:inactive_cap]
    final_results = kept_active + kept_inactive
    inactive_count = len(kept_inactive)
    relaxed_count = sum(1 for it in kept_active if it.get("is_relaxed"))

    STATE.results = final_results
    STATE.summary = summary_text
    STATE.last_dropped = dropped
    STATE.last_inactive = inactive_count

    # --- pass 5: aggregate skill gap (uses kept active + shown inactive)
    if final_results and STATE.has_profile():
        _aggregate_skill_gap(
            final_results,
            output_lang=output_lang,
            tech_skills=tech_skills,
            additional_experience=additional_experience,
            profile_text=profile_text,
            profile_file_text=profile_file_text,
            profile_file_name=profile_file_name,
            linkedin_url=linkedin_url,
        )

    STATE.activity = "ready"
    REFS.request_context_refresh()

    logger_service.log_event(
        "INFO", "ai_jobs.pipeline", "run_search_done",
        kept=len(final_results),
        kept_active=len(kept_active),
        kept_relaxed=relaxed_count,
        kept_inactive=inactive_count,
        dropped=dropped,
        candidates_total=len(survivors) + dropped,
        target_active=target_active,
        candidate_target=candidate_target,
        strict_topup_attempts=strict_attempts,
        relaxed_topup_attempts=relaxed_attempts,
        keywords=keywords,
        location=location_label,
        scored=sum(1 for s in final_results if s.get("match_score") is not None),
        skill_gap_has_data=bool(STATE.skill_gap),
    )
    return PipelineResult(ok=True)


# ---------------------------------------------------------------------------
# Pass 4 helpers - per-position scoring
# ---------------------------------------------------------------------------


def _score_one_position(
    item: dict,
    *,
    output_lang: str,
    tech_skills: str,
    additional_experience: str,
    profile_text: str,
    profile_file_text: str,
    profile_file_name: str,
    linkedin_url: str,
) -> None:
    """Run Pass 4 for one position. Errors are logged but never raised."""
    try:
        system, user = prompts.build_match_prompt(
            output_lang=output_lang,
            position=item,
            tech_skills=tech_skills,
            additional_experience=additional_experience,
            seniority=STATE.seniority,
            profile_text=profile_text,
            profile_file_text=profile_file_text,
            profile_file_name=profile_file_name,
            linkedin_url=linkedin_url,
        )
        result = _provider_call(
            stage="match",
            system=system,
            user=user,
            schema_dict=schema.MATCH_SCHEMA,
            schema_name="job_match",
            max_output_tokens=600,
            enable_web_search=False,
        )
    except ai_provider.ProviderError as exc:
        logger_service.log_exception(
            "ai_jobs.pipeline", "match_provider_error", exc,
            url=item.get("url", ""),
        )
        return
    except Exception as exc:
        logger_service.log_exception(
            "ai_jobs.pipeline", "match_unexpected_error", exc,
            url=item.get("url", ""),
        )
        return

    payload = result.data if isinstance(result.data, dict) else {}
    try:
        score = int(payload.get("match_score") or 0)
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))

    item["match_score"] = score
    item["matched_skills"] = [str(x).strip() for x in (payload.get("matched_skills") or []) if str(x).strip()][:8]
    item["missing_skills"] = [str(x).strip() for x in (payload.get("missing_skills") or []) if str(x).strip()][:6]
    item["recommendation"] = (payload.get("recommendation") or "").strip()


def _score_positions(
    positions: list[dict],
    *,
    output_lang: str,
    tech_skills: str,
    additional_experience: str,
    profile_text: str,
    profile_file_text: str,
    profile_file_name: str,
    linkedin_url: str,
) -> None:
    """Score every position in parallel. Mutates ``positions`` in place."""
    _set_activity("scoring")
    if STATE.demo_mode:
        for item in positions:
            item["match_score"] = 80
            item["matched_skills"] = ["demo"]
            item["missing_skills"] = []
            item["recommendation"] = "Demo run - no provider call was made."
        return

    logger_service.log_event(
        "INFO", "ai_jobs.pipeline", "scoring_start",
        positions=len(positions), workers=_SCORE_WORKERS,
    )
    with ThreadPoolExecutor(max_workers=_SCORE_WORKERS) as pool:
        futures = [
            pool.submit(
                _score_one_position,
                item,
                output_lang=output_lang,
                tech_skills=tech_skills,
                additional_experience=additional_experience,
                profile_text=profile_text,
                profile_file_text=profile_file_text,
                profile_file_name=profile_file_name,
                linkedin_url=linkedin_url,
            )
            for item in positions
        ]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                logger_service.log_exception(
                    "ai_jobs.pipeline", "scoring_future_failed", exc,
                )

    logger_service.log_event(
        "INFO", "ai_jobs.pipeline", "scoring_done",
        positions=len(positions),
        scored=sum(1 for item in positions if item.get("match_score") is not None),
    )


# ---------------------------------------------------------------------------
# Pass 5 helpers - aggregate skill gap
# ---------------------------------------------------------------------------


def _aggregate_skill_gap(
    positions: list[dict],
    *,
    output_lang: str,
    tech_skills: str,
    additional_experience: str,
    profile_text: str,
    profile_file_text: str,
    profile_file_name: str,
    linkedin_url: str,
) -> None:
    """Run Pass 5 - populate :data:`STATE.skill_gap`."""
    _set_activity("gap_analysis")
    if STATE.demo_mode:
        STATE.skill_gap = {
            "top_required": [
                {"skill": "Python", "count": len(positions)},
                {"skill": "API testing", "count": max(1, len(positions) - 1)},
            ],
            "user_strong": ["Python", "API testing"],
            "user_missing": ["Docker", "Kubernetes"],
            "advice": [
                "Demo run - no provider call was made.",
                "In real runs this section lists 1-6 concrete next-step paragraphs.",
            ],
        }
        return

    try:
        system, user = prompts.build_skill_gap_prompt(
            output_lang=output_lang,
            positions=positions,
            tech_skills=tech_skills,
            additional_experience=additional_experience,
            seniority=STATE.seniority,
            profile_text=profile_text,
            profile_file_text=profile_file_text,
            profile_file_name=profile_file_name,
            linkedin_url=linkedin_url,
        )
        result = _provider_call(
            stage="skill_gap",
            system=system,
            user=user,
            schema_dict=schema.SKILL_GAP_SCHEMA,
            schema_name="skill_gap",
            max_output_tokens=1500,
            enable_web_search=False,
        )
    except ai_provider.ProviderError as exc:
        logger_service.log_exception(
            "ai_jobs.pipeline", "skill_gap_provider_error", exc,
        )
        STATE.skill_gap = {}
        return
    except Exception as exc:
        logger_service.log_exception(
            "ai_jobs.pipeline", "skill_gap_unexpected_error", exc,
        )
        STATE.skill_gap = {}
        return

    payload = result.data if isinstance(result.data, dict) else {}
    top_required = []
    for entry in (payload.get("top_required") or [])[:10]:
        if not isinstance(entry, dict):
            continue
        skill = (entry.get("skill") or "").strip()
        if not skill:
            continue
        try:
            count = int(entry.get("count") or 0)
        except (TypeError, ValueError):
            count = 0
        if count <= 0:
            continue
        top_required.append({"skill": skill, "count": count})

    STATE.skill_gap = {
        "top_required": top_required,
        "user_strong": [str(x).strip() for x in (payload.get("user_strong") or []) if str(x).strip()][:8],
        "user_missing": [str(x).strip() for x in (payload.get("user_missing") or []) if str(x).strip()][:8],
        "advice": [str(x).strip() for x in (payload.get("advice") or []) if str(x).strip()][:6],
    }


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
  --good: #22C55E;
  --good-soft: rgba(34, 197, 94, 0.16);
  --warn: #F59E0B;
  --warn-soft: rgba(245, 158, 11, 0.16);
  --danger: #EF4444;
  --danger-soft: rgba(239, 68, 68, 0.16);
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
.search-summary {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 18px 22px;
  margin-bottom: 24px;
}
.search-summary h2 {
  margin: 0 0 10px;
  font-size: 15px;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--muted);
}
.search-summary dl {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 6px 18px;
  margin: 0;
  font-size: 13px;
}
.search-summary dt {
  color: var(--muted);
  font-weight: 600;
}
.search-summary dd {
  margin: 0;
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
li.position.inactive {
  border-color: var(--danger-soft);
  opacity: 0.85;
}
li.position.inactive h2 a {
  color: var(--muted);
}
.inactive-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  background: var(--danger-soft);
  color: var(--danger);
  white-space: nowrap;
  margin-left: 8px;
}
.inactive-marker {
  display: block;
  margin: 4px 0 8px;
  font-size: 12px;
  color: var(--danger);
  font-style: italic;
}
li.position.relaxed {
  border-color: var(--warn-soft);
}
.relaxed-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  background: var(--warn-soft);
  color: var(--warn);
  white-space: nowrap;
  margin-left: 8px;
}
h2.inactive-section {
  margin: 32px 0 12px;
  font-size: 16px;
  letter-spacing: 0.4px;
  color: var(--muted);
  text-transform: uppercase;
}
li.position .title-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
li.position h2 {
  margin: 0 0 6px;
  font-size: 17px;
  flex: 1;
}
li.position h2 a {
  color: var(--text);
  text-decoration: none;
}
li.position h2 a:hover {
  color: var(--accent);
}
.match-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  background: var(--accent-soft);
  color: var(--accent);
  white-space: nowrap;
}
.match-pill.score-high {
  background: var(--good-soft);
  color: var(--good);
}
.match-pill.score-mid {
  background: var(--warn-soft);
  color: var(--warn);
}
.match-pill.score-low {
  background: var(--danger-soft);
  color: var(--danger);
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
.fit-block {
  margin: 12px 0 10px;
  padding: 12px 14px;
  background: var(--surface-2);
  border-radius: 10px;
  font-size: 13px;
}
.fit-block h3 {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.7px;
  color: var(--muted);
}
.skill-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.skill-chip {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}
.skill-chip.matched {
  background: var(--good-soft);
  color: var(--good);
}
.skill-chip.missing {
  background: var(--danger-soft);
  color: var(--danger);
}
.recommendation {
  margin: 10px 0 12px;
  padding: 12px 14px;
  background: var(--accent-soft);
  border-left: 3px solid var(--accent);
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.55;
}
.recommendation h3 {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.7px;
  color: var(--accent);
}
.skill-gap-section {
  margin-top: 32px;
  padding: 22px 24px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
}
.skill-gap-section h2 {
  margin: 0 0 6px;
  font-size: 18px;
}
.skill-gap-section p.lead {
  margin: 0 0 18px;
  color: var(--muted);
  font-size: 13px;
}
.skill-gap-section h3 {
  margin: 18px 0 8px;
  font-size: 14px;
  letter-spacing: 0.3px;
}
.skill-gap-section ol.top-required {
  margin: 0;
  padding-left: 22px;
  font-size: 13px;
  line-height: 1.7;
}
.skill-gap-section ol.top-required li {
  margin: 0;
}
.skill-gap-section ol.top-required .count {
  color: var(--muted);
  font-size: 12px;
  margin-left: 6px;
}
.skill-gap-section ul.advice {
  list-style: disc;
  margin: 0;
  padding-left: 22px;
  font-size: 13px;
  line-height: 1.55;
}
.skill-gap-section ul.advice li {
  margin: 4px 0;
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


def _score_class(score: Optional[int]) -> str:
    if score is None:
        return ""
    if score >= 75:
        return "score-high"
    if score >= 50:
        return "score-mid"
    return "score-low"


def _render_skill_chips(items: list[str], *, kind: str) -> str:
    chips = [
        f'<span class="skill-chip {kind}">{_esc(item)}</span>'
        for item in (items or [])
        if (item or "").strip()
    ]
    return f'<div class="skill-chips">{"".join(chips)}</div>' if chips else ""


def _render_position(item: dict, txt: dict) -> str:
    is_active = bool(item.get("is_active", True))
    is_relaxed = bool(item.get("is_relaxed", False))
    inactive_reason = (item.get("inactive_reason") or "").strip()

    work_mode = (item.get("work_mode") or "unknown").lower()
    work_pill = (
        f'<span class="work-pill">{_esc(work_mode)}</span>'
        if work_mode in {"remote", "hybrid", "onsite"}
        else ""
    )

    inactive_pill = ""
    inactive_note = ""
    if not is_active:
        inactive_pill = (
            f'<span class="inactive-pill" title="{_esc(txt["results_inactive_tooltip"])}">'
            f'{_esc(txt["results_inactive_pill"])}'
            "</span>"
        )
        if inactive_reason:
            inactive_note = (
                f'<span class="inactive-marker">"{_esc(inactive_reason)}"</span>'
            )

    relaxed_pill = ""
    if is_active and is_relaxed:
        relaxed_pill = (
            f'<span class="relaxed-pill" title="{_esc(txt["results_relaxed_tooltip"])}">'
            f'{_esc(txt["results_relaxed_pill"])}'
            "</span>"
        )

    score = item.get("match_score")
    match_pill = ""
    if isinstance(score, int):
        match_pill = (
            f'<span class="match-pill {_score_class(score)}">'
            f'{_esc(txt["html_match_pill_template"].format(score=score))}'
            "</span>"
        )

    meta_parts: list[str] = []
    if item.get("company"):
        meta_parts.append(f"<span><strong>{_esc(txt['results_meta_company'])}:</strong> {_esc(item['company'])}</span>")
    if item.get("location"):
        meta_parts.append(f"<span><strong>{_esc(txt['results_meta_location'])}:</strong> {_esc(item['location'])}</span>")
    if item.get("posted"):
        meta_parts.append(f"<span><strong>{_esc(txt['results_meta_posted'])}:</strong> {_esc(item['posted'])}</span>")
    if item.get("salary_text"):
        meta_parts.append(f"<span><strong>{_esc(txt['results_meta_salary'])}:</strong> {_esc(item['salary_text'])}</span>")
    contract = (item.get("contract_type") or "unknown")
    if contract and contract != "unknown":
        meta_parts.append(f"<span><strong>{_esc(txt['results_meta_contract'])}:</strong> {_esc(contract.upper())}</span>")
    if item.get("source"):
        meta_parts.append(f"<span><strong>{_esc(txt['results_meta_source'])}:</strong> {_esc(item['source'])}</span>")
    meta_html = "".join(meta_parts)

    summary_html = (
        f'<p class="summary-line">{_esc(item["summary"])}</p>'
        if item.get("summary")
        else ""
    )

    matched_block = ""
    matched = item.get("matched_skills") or []
    if matched:
        matched_block = (
            '<div class="fit-block">'
            f'<h3>{_esc(txt["html_matched_label"])}</h3>'
            f'{_render_skill_chips(matched, kind="matched")}'
            "</div>"
        )

    missing_block = ""
    missing = item.get("missing_skills") or []
    if missing:
        missing_block = (
            '<div class="fit-block">'
            f'<h3>{_esc(txt["html_missing_label"])}</h3>'
            f'{_render_skill_chips(missing, kind="missing")}'
            "</div>"
        )

    recommendation_block = ""
    rec = (item.get("recommendation") or "").strip()
    if rec:
        recommendation_block = (
            '<div class="recommendation">'
            f'<h3>{_esc(txt["html_recommendation_label"])}</h3>'
            f"<p>{_esc(rec)}</p>"
            "</div>"
        )

    classes = ["position"]
    if not is_active:
        classes.append("inactive")
    elif is_relaxed:
        classes.append("relaxed")
    li_class = " ".join(classes)
    return (
        f'<li class="{li_class}">'
        '<div class="title-row">'
        f'<h2><a href="{_esc(item["url"])}" target="_blank" rel="noopener">'
        f'{_esc(item["title"])}</a>{work_pill}{relaxed_pill}{inactive_pill}</h2>'
        f'{match_pill}'
        "</div>"
        f'{inactive_note}'
        f'<div class="meta">{meta_html}</div>'
        f'{summary_html}'
        f'{matched_block}'
        f'{missing_block}'
        f'{recommendation_block}'
        '<div class="actions">'
        f'<a href="{_esc(item["url"])}" target="_blank" rel="noopener">{_esc(txt["results_open_btn"])}</a>'
        f'<a class="secondary" href="{_esc(item["url"])}" target="_blank" rel="noopener">{_esc(item["url"])}</a>'
        '</div>'
        '</li>'
    )


def _render_search_summary(*, txt: dict, total: int) -> str:
    rows: list[str] = []

    def _row(label: str, value: str) -> None:
        if value:
            rows.append(f"<dt>{_esc(label)}</dt><dd>{_esc(value)}</dd>")

    _row(txt["html_search_summary_role"], STATE.last_query or STATE.keywords)
    _row(txt["html_search_summary_location"], STATE.last_location_label)
    _row(txt["html_search_summary_seniority"],
         STATE.seniority if STATE.seniority != "any" else "")
    _row(txt["html_search_summary_sources"],
         txt["summary_sources_count_template"].format(count=len(STATE.selected_sources))
         if STATE.selected_sources else txt["summary_sources_recommended"])
    _row(txt["html_search_summary_mode"], STATE.search_mode)
    if STATE.salary_min and STATE.salary_currency != "any":
        _row(txt["html_search_summary_salary"],
             txt["summary_salary_value_template"].format(amount=STATE.salary_min, currency=STATE.salary_currency))

    if not rows:
        return ""
    return (
        '<section class="search-summary">'
        f'<h2>{_esc(txt["html_search_summary_title"])}</h2>'
        f"<dl>{''.join(rows)}</dl>"
        "</section>"
    )


def _render_skill_gap(txt: dict, total: int) -> str:
    gap = STATE.skill_gap or {}
    if not gap:
        return ""

    parts: list[str] = []
    parts.append('<section class="skill-gap-section">')
    parts.append(f'<h2>{_esc(txt["html_skill_gap_title"])}</h2>')
    parts.append(f'<p class="lead">{_esc(txt["skill_gap_subtitle"])}</p>')

    top = gap.get("top_required") or []
    if top:
        parts.append(f'<h3>{_esc(txt["html_skill_gap_top"])}</h3>')
        parts.append('<ol class="top-required">')
        for entry in top:
            skill = entry.get("skill") or ""
            count = entry.get("count") or 0
            count_text = txt["html_skill_gap_count_template"].format(count=count, total=total)
            parts.append(
                f'<li>{_esc(skill)} <span class="count">{_esc(count_text)}</span></li>'
            )
        parts.append('</ol>')

    strong = gap.get("user_strong") or []
    if strong:
        parts.append(f'<h3>{_esc(txt["html_skill_gap_strong"])}</h3>')
        parts.append(_render_skill_chips(strong, kind="matched"))

    missing = gap.get("user_missing") or []
    if missing:
        parts.append(f'<h3>{_esc(txt["html_skill_gap_missing"])}</h3>')
        parts.append(_render_skill_chips(missing, kind="missing"))

    advice = gap.get("advice") or []
    if advice:
        parts.append(f'<h3>{_esc(txt["html_skill_gap_advice"])}</h3>')
        parts.append('<ul class="advice">')
        for line in advice:
            parts.append(f"<li>{_esc(line)}</li>")
        parts.append('</ul>')

    parts.append('</section>')
    return "".join(parts)


def _render_html(*, query: str, location_label: str, summary: str, items: list[dict], output_lang: str) -> str:
    txt = s(output_lang)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    summary_block = (
        f'<section class="summary">{_esc(summary)}</section>'
        if (summary or "").strip()
        else ""
    )

    # Split active vs inactive so the user gets a clear visual break
    # between live postings and dead listings (the latter still ship
    # so the user can verify our marker detection).
    active_items = [item for item in items if item.get("is_active", True)]
    inactive_items = [item for item in items if not item.get("is_active", True)]
    active_html = "\n".join(_render_position(item, txt) for item in active_items)
    inactive_section_html = ""
    if inactive_items:
        inactive_html = "\n".join(_render_position(item, txt) for item in inactive_items)
        inactive_section_html = (
            f'<h2 class="inactive-section">{_esc(txt["results_inactive_section_title"])} '
            f'({len(inactive_items)})</h2>\n'
            f'<ul class="positions">\n{inactive_html}\n</ul>\n'
        )

    search_summary_html = _render_search_summary(txt=txt, total=len(items))
    skill_gap_html = _render_skill_gap(txt, total=len(items))
    title_text = f"Job search - {query}" if query else "Job search results"
    counts_line = (
        f'{_esc(len(active_items))} active'
        + (f' &middot; {_esc(len(inactive_items))} closed' if inactive_items else '')
    )
    return (
        "<!doctype html>\n"
        f'<html lang="{_esc(output_lang)}">\n<head>\n'
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
        f'<p><strong>Generated:</strong> {_esc(timestamp)} &middot; {counts_line} position(s)</p>\n'
        '</header>\n'
        + search_summary_html + "\n"
        + summary_block + "\n"
        + '<ul class="positions">\n'
        + active_html + "\n"
        + '</ul>\n'
        + inactive_section_html
        + skill_gap_html + "\n"
        + '<footer class="page">Generated by AI Hub - links verified at export time. They may go offline later.</footer>\n'
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
    output_lang = jobs_data.resolve_output_language(
        picker_value=STATE.output_language,
        global_lang=output_lang,
    )
    if not STATE.has_results():
        return _set_error("save_html", "No results to save.")

    _set_activity("saving")
    try:
        run_dir = store.new_run_dir(
            role=STATE.last_query or "ai-jobs",
            company="search",
            section="ai_jobs",
        )
    except Exception as exc:
        return _set_error("save_html", f"Could not create output folder: {exc}")

    html_text = _render_html(
        query=STATE.last_query or STATE.last_query_label,
        location_label=STATE.last_location_label,
        summary=STATE.summary,
        items=STATE.results,
        output_lang=output_lang,
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
        "inactive": STATE.last_inactive,
        "positions": STATE.results,
        "skill_gap": STATE.skill_gap,
        "seniority": STATE.seniority,
        "search_mode": STATE.search_mode,
        "salary_min": STATE.salary_min,
        "salary_currency": STATE.salary_currency,
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
    """Populate ``STATE.runs_history`` + ``STATE.saved_profiles`` from disk.

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
        try:
            from src.sections.ai_jobs import profiles_store
            STATE.saved_profiles = profiles_store.list_profiles()
        except Exception as exc:
            logger_service.log_exception(
                "ai_jobs.pipeline", "warm_profiles_failed", exc,
            )
            STATE.saved_profiles = []
        _STARTUP_DONE["hydrated"] = True


def refresh_saved_profiles() -> None:
    """Re-read the saved profile list from disk.

    Called after profiles are saved / deleted / duplicated so the UI
    can mirror the on-disk state without restarting the app.
    """
    try:
        from src.sections.ai_jobs import profiles_store
        STATE.saved_profiles = profiles_store.list_profiles()
    except Exception as exc:
        logger_service.log_exception(
            "ai_jobs.pipeline", "refresh_saved_profiles_failed", exc,
        )
