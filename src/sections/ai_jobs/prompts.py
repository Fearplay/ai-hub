"""Prompt builders for the AI Jobs two-pass search flow.

Two prompts, one per pass:

* :func:`build_search_prompt` is the **discovery** pass. It nudges the
  model to use its hosted web-search tool, expands the user's job
  title with synonyms, pins the location, and lists preferred boards
  per region as soft hints. Returns a ``(system, user)`` tuple.
* :func:`build_extraction_prompt` is the **structuring** pass. It feeds
  the discovery output back to the model with strict instructions to
  emit only positions whose URL was explicitly mentioned, no
  hallucinated entries.

The discovery prompt is intentionally chatty - the model produces a
lot of context (board names, posting dates, salary hints) that helps
the extraction pass fill in the schema fields without a second web
roundtrip.
"""

from __future__ import annotations

from typing import Iterable, Optional

from src.sections.ai_jobs.data import ATS_AND_CAREER_PAGES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _truncate(text: str, *, max_chars: int) -> str:
    """Trim long profile text so the prompt stays within sane token budgets.

    The user's full CV can hit ~10k characters; we only need a snapshot
    so the model can pick the right synonyms and seniority. Anything
    over ``max_chars`` is cut on a word boundary with an ellipsis so
    the model doesn't see a half-word at the seam.
    """
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    snippet = text[: max_chars]
    cut = snippet.rfind(" ")
    if cut > max_chars * 0.7:
        snippet = snippet[:cut]
    return snippet.rstrip() + "..."


def _format_boards(boards: Iterable[str]) -> str:
    boards = [b for b in boards if b]
    if not boards:
        return "no preference"
    return ", ".join(boards)


def _localise(language_code: str) -> str:
    """Map ``en`` / ``cs`` to the verbose label the LLM needs in the prompt."""
    code = (language_code or "").strip().lower()
    if code == "cs":
        return "Czech"
    return "English"


# ---------------------------------------------------------------------------
# Pass 1 - discovery (web search, no schema)
# ---------------------------------------------------------------------------


def build_search_prompt(
    *,
    output_lang: str,
    keywords: str,
    location_query: str,
    location_label: str,
    work_mode: str,
    max_results: int,
    profile_text: str,
    profile_file_text: str,
    profile_file_name: str,
    linkedin_url: str,
    preferred_boards: Iterable[str],
) -> tuple[str, str]:
    """Build the (system, user) prompt for the web-search discovery pass.

    The system message sets the model's role as a recruiter using live
    web search; the user message packs every input the user supplied
    plus the location / work-mode constraints.
    """
    language = _localise(output_lang)
    boards = _format_boards(preferred_boards)
    ats_hints = _format_boards(ATS_AND_CAREER_PAGES)

    system = (
        "You are an expert recruiter using your web-search tool to find "
        "currently active job postings on the public web. You MUST call "
        "web search MULTIPLE TIMES with different queries (different "
        "boards, different role synonyms, different city/region "
        "wordings) to verify each posting is still live (URL returns a "
        "real listing, not a 'job no longer available' page) and was "
        "published or updated within roughly the last 60 days.\n\n"
        "Hard rules:\n"
        "- NEVER invent a URL. If you cannot find the direct posting "
        "URL via web search, drop the result.\n"
        "- The URL must point to the actual job ad (application page), "
        "NOT to a search-results page or a company homepage.\n"
        "- SOURCE DIVERSITY IS MANDATORY: the final list MUST come from "
        "AT LEAST 3 different sources. Do NOT return only LinkedIn "
        "Jobs results. Do NOT let any single source contribute more "
        "than ~40% of the list. If a region has region-specific boards "
        "(e.g. jobs.cz / prace.cz for Czechia, StepStone for Germany, "
        "Pracuj.pl for Poland), prioritise those over global aggregators.\n"
        "- Search direct company career pages and ATS-hosted boards in "
        "addition to job aggregators - many mid-senior postings never "
        "leave the company's own /careers page.\n"
        "- Match the requested location strictly. If the user asked "
        "for 'Prague', do not include postings whose only office is "
        "in Brno or Berlin.\n"
        "- Match the work-mode filter when one is given (remote / "
        "hybrid / on-site).\n"
        "- Expand the role title with common synonyms and adjacent "
        "roles in the same domain (e.g. 'QA Engineer' = 'Tester' = "
        "'Quality Engineer' = 'SDET'). Cover the same job under "
        "different titles, not different jobs.\n"
        "- Use the listed boards as a starting point but feel free to "
        "search niche boards relevant to the role (e.g. Dice / "
        "StackOverflow Jobs / Honeypot for tech, Mediabistro for "
        "media, Idealist for non-profits). Do NOT invent boards that "
        "do not exist.\n"
        "- Output only the user's requested language for prose, but "
        "keep job titles, company names and city names verbatim.\n"
    )

    user_lines: list[str] = []
    user_lines.append(f"Reply in {language}.")
    user_lines.append(f"Goal: find up to {int(max_results)} ACTIVE job postings.")
    user_lines.append("")

    user_lines.append("# Role / keywords")
    if keywords.strip():
        user_lines.append(keywords.strip())
    else:
        user_lines.append(
            "(none provided - infer the role from the profile material below "
            "and pick the best fit)"
        )
    user_lines.append("")

    user_lines.append("# Location filter")
    if location_query.strip():
        user_lines.append(
            f"Location must match: {location_query.strip()} "
            f"(user-facing label: {location_label.strip() or location_query.strip()})."
        )
        user_lines.append(
            "Do NOT include postings outside this region. Remote-only postings "
            "are acceptable when the requested location is 'Remote' or worldwide."
        )
    else:
        user_lines.append(
            "No location restriction - look anywhere, but mention the city/country "
            "of each posting."
        )
    user_lines.append("")

    user_lines.append("# Work mode")
    work_mode = (work_mode or "any").strip().lower()
    if work_mode in {"remote", "hybrid", "onsite"}:
        user_lines.append(f"Only postings advertised as {work_mode}.")
    else:
        user_lines.append("Any work mode is fine.")
    user_lines.append("")

    user_lines.append("# Suggested job boards to search (use AT LEAST 3 different ones)")
    user_lines.append(
        "Boards listed first are usually most relevant for the chosen region. "
        "Do NOT restrict yourself to LinkedIn - actively search the others too."
    )
    user_lines.append(boards)
    user_lines.append("")
    user_lines.append("# Also search direct company career pages / ATS-hosted boards")
    user_lines.append(
        "Many active postings only live on the company's own site or on an "
        "ATS subdomain. Examples to try:"
    )
    user_lines.append(ats_hints)
    user_lines.append("")

    profile_chunks: list[str] = []
    if profile_text.strip():
        profile_chunks.append(
            "## Free-text bio supplied by the user\n"
            f"{_truncate(profile_text, max_chars=2500)}"
        )
    if profile_file_text.strip():
        label = profile_file_name or "uploaded CV"
        profile_chunks.append(
            f"## CV / LinkedIn export ({label})\n"
            f"{_truncate(profile_file_text, max_chars=4500)}"
        )
    if linkedin_url.strip():
        profile_chunks.append(
            "## Public LinkedIn URL (for context only - do not assume you can "
            "scrape private fields)\n"
            f"{linkedin_url.strip()}"
        )
    if profile_chunks:
        user_lines.append("# Candidate profile")
        user_lines.append("")
        user_lines.extend(profile_chunks)
        user_lines.append("")

    user_lines.append("# Output format")
    user_lines.append(
        "For each position you found via web search, write a short block in this "
        "exact shape (one block per posting, separated by a blank line):"
    )
    user_lines.append("")
    user_lines.append("- Title: <job title>")
    user_lines.append("- Company: <company>")
    user_lines.append("- Location: <city, country or Remote>")
    user_lines.append("- Posted: <date or 'unknown'>")
    user_lines.append("- Work mode: <remote | hybrid | onsite | unknown>")
    user_lines.append("- Source: <board or career-page name where you found it>")
    user_lines.append("- URL: <https://...>")
    user_lines.append("- Summary: <1-2 sentences>")
    user_lines.append("")
    user_lines.append(
        "Reminder before you write the list: count the unique sources you "
        "are about to use. If you only have ONE source (e.g. all LinkedIn), "
        "go back and search at least 2 more boards or career pages first. "
        "The user explicitly does not want a single-source result."
    )
    user_lines.append("")
    user_lines.append(
        "End with a 'Notes:' line containing 1-3 sentences summarising "
        "the trends across the postings you found (salary range hints, "
        "common requirements, market saturation, which sources were "
        "richest)."
    )

    return system, "\n".join(user_lines)


# ---------------------------------------------------------------------------
# Pass 2 - extraction (strict JSON schema, no web search)
# ---------------------------------------------------------------------------


def build_extraction_prompt(
    *,
    output_lang: str,
    discovery_text: str,
    location_query: str,
    work_mode: str,
    max_results: int,
) -> tuple[str, str]:
    """Build the (system, user) prompt for the JSON-schema structuring pass.

    Feeds the prose from the discovery pass back in and asks the model
    to emit only the positions that already had a real URL. No new web
    look-ups are needed - the schema is the entire contract.
    """
    language = _localise(output_lang)
    work_mode = (work_mode or "any").strip().lower()

    system = (
        "You are a strict JSON normaliser. Convert the recruiter notes the "
        "user pastes into the JSON schema EXACTLY. Hard rules:\n"
        "- Drop any entry whose URL is missing, empty, or does not start "
        "with http:// or https://.\n"
        "- Drop duplicates (same URL or same title+company combo).\n"
        "- PRESERVE the 'source' value from the recruiter notes verbatim "
        "(e.g. 'jobs.cz', 'StepStone', 'Greenhouse - boards.greenhouse.io/"
        "acme'). Do NOT collapse every entry to 'LinkedIn Jobs' just "
        "because LinkedIn is well known. If the recruiter notes do not "
        "specify a source, infer it from the URL hostname (e.g. "
        "'jobs.lever.co/foo' -> 'Lever (foo)') instead of guessing.\n"
        "- Use 'unknown' for fields the recruiter did not provide. "
        "Never invent company names, dates, or links.\n"
        "- Keep summaries short (1-2 sentences). Trim recruiter "
        "boilerplate like 'apply now' or 'send your CV to'.\n"
        f"- Write all prose in {language}. Job titles, company names "
        "and city names stay verbatim regardless of language.\n"
    )

    user_lines: list[str] = []
    user_lines.append(f"Convert the following recruiter notes into the schema. Cap at {int(max_results)} positions.")
    user_lines.append("")
    if location_query.strip():
        user_lines.append(
            f"Location filter (drop postings outside this region): {location_query.strip()}"
        )
    if work_mode in {"remote", "hybrid", "onsite"}:
        user_lines.append(f"Work-mode filter (drop postings that do not match): {work_mode}")
    user_lines.append("")
    user_lines.append("--- recruiter notes start ---")
    user_lines.append(discovery_text or "(empty)")
    user_lines.append("--- recruiter notes end ---")

    return system, "\n".join(user_lines)
