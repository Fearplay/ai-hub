"""Prompt builders for the AI Jobs five-pass search flow.

Five prompts, one per pass (passes 1-2 are LLM, pass 3 is pure Python
URL verification, passes 4-5 are LLM again):

* :func:`build_search_prompt` is the **discovery** pass (Pass 1). It
  nudges the model to use its hosted web-search tool, expands the
  user's job title with synonyms / adjacent roles depending on the
  selected search mode, pins the location + age + work-mode
  constraints, and lists preferred boards. Returns ``(system, user)``.
* :func:`build_extraction_prompt` is the **structuring** pass (Pass 2).
  It feeds the discovery output back to the model with strict
  instructions to emit only positions whose URL was explicitly
  mentioned, in the exact :data:`schema.JOB_LISTINGS_SCHEMA` shape.
* :func:`build_match_prompt` is the per-position **scoring** pass
  (Pass 4). It compares one posting against the user's profile and
  returns :data:`schema.MATCH_SCHEMA` (match %, matched / missing
  skills, AI recommendation).
* :func:`build_skill_gap_prompt` is the aggregate **skill-gap** pass
  (Pass 5). One call that sees every position + the profile and emits
  :data:`schema.SKILL_GAP_SCHEMA` (top requirements, strong sides,
  missing skills, advice).

The discovery prompt is intentionally chatty - the model produces a
lot of context (board names, posting dates, salary hints) that helps
the extraction pass fill in the schema fields without a second web
roundtrip.
"""

from __future__ import annotations

import json
from typing import Any, Iterable, Optional

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


def _format_list(values: Iterable[str], *, fallback: str = "(none)") -> str:
    items = [v.strip() for v in (values or ()) if (v or "").strip()]
    return ", ".join(items) if items else fallback


def _split_lines(text: str) -> list[str]:
    """Split a multi-line textarea into trimmed non-empty lines."""
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


_SEARCH_MODE_HINTS: dict[str, str] = {
    "exact": (
        "STRICT MODE - keep the role title and required technologies "
        "verbatim. Do not invent synonyms. Drop postings that only "
        "match a related role."
    ),
    "smart": (
        "SMART MODE - cover the role under common synonyms (e.g. "
        "'QA Engineer' / 'Tester' / 'Quality Engineer' / 'SDET'). "
        "Group postings that are the same job under different titles."
    ),
    "broad": (
        "BROAD MODE - include adjacent roles in the same domain that "
        "the user could reasonably fit (e.g. for QA Engineer also "
        "show Test Automation Engineer, SDET, Performance Engineer). "
        "Still match the location and seniority."
    ),
    "discovery": (
        "CAREER DISCOVERY MODE - in addition to the requested role, "
        "surface 2-3 alternative directions that match the user's "
        "experience (e.g. for a senior backend developer also show "
        "Platform Engineer, Tech Lead, DevOps Engineer). Flag those "
        "as 'pivot' roles in the source field."
    ),
}


def _seniority_hint(level: str) -> str:
    level = (level or "any").strip().lower()
    if level == "any":
        return "Seniority filter: any level is acceptable."
    return (
        f"Seniority filter: postings must target the '{level}' level. "
        "Drop senior-only ads when the user is junior, and vice versa."
    )


def _format_followup_qa(qa_pairs: Optional[Iterable[dict]]) -> str:
    """Render answered follow-up questions for inclusion in downstream prompts.

    The block is appended to the user message of the discovery /
    extraction / match / skill-gap prompts so the model treats the
    user's clarifications as ground truth rather than something it
    might have to invent (no-hallucination clause).
    """
    qa_pairs = [p for p in (qa_pairs or []) if isinstance(p, dict)]
    if not qa_pairs:
        return ""
    lines: list[str] = ["=== ADDITIONAL CLARIFICATIONS FROM USER ==="]
    appended = False
    for pair in qa_pairs:
        topic = (pair.get("topic") or "").strip() or "-"
        question = (pair.get("question") or "").strip()
        answer = (pair.get("answer") or "").strip()
        if not answer:
            continue
        appended = True
        lines.append(f"- Topic: {topic}")
        if question:
            lines.append(f"  Q: {question}")
        lines.append(f"  A: {answer}")
    if not appended:
        return ""
    lines.append(
        "\nUse these clarifications as TRUTH when filtering, scoring, "
        "and writing recommendations. Do not contradict them. Do not "
        "invent additional facts beyond what the user stated above."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pass 0 - clarifying follow-up questions (optional)
# ---------------------------------------------------------------------------


FOLLOWUP_QUESTIONS_SYSTEM = (
    "You are a senior career coach screening a candidate's job-search "
    "brief BEFORE running the actual search. Your one job is to surface "
    "CLARIFYING QUESTIONS the user should answer first - things the "
    "search would otherwise have to guess at and might get wrong.\n\n"
    "Hard rules:\n"
    "* Ask only about ambiguities that would change which postings the "
    "search returns or how each posting is scored. Examples of GOOD "
    "questions:\n"
    "    - 'You listed Python in skills but no years - how many years "
    "of Python?' -> options ['<1', '1-3', '3-5', '5+'], "
    "multi_select=false, allow_free_text=false\n"
    "    - 'Are you open to hybrid work or strictly remote?' -> options "
    "['Remote only', 'Hybrid OK', 'Onsite OK'], multi_select=false, "
    "allow_free_text=true\n"
    "    - 'Which seniority should we target?' when the profile shows "
    "mixed signals -> options ['Junior', 'Medior', 'Senior', 'Lead'], "
    "multi_select=true, allow_free_text=false\n"
    "    - 'Do you require a minimum salary?' when none was given -> "
    "options ['<60k CZK', '60-90k CZK', '90k+ CZK', 'No preference'], "
    "multi_select=false, allow_free_text=true\n"
    "* Do NOT re-ask about fields the user EXPLICITLY set (a concrete "
    "location, selected sources, work-mode radio, contract types, age "
    "window, search mode). Re-asking an explicit input is annoying.\n"
    "* MUST-ASK gaps - always ask these when the brief marks them "
    "UNSPECIFIED, and treat them as higher priority than every other "
    "question:\n"
    "    - LOCATION: if the brief says the location is UNSPECIFIED, you "
    "MUST ask where the user wants to work (country / city, or whether "
    "remote is fine and in which region). Never silently assume "
    "worldwide - a user in Czechia does not want US-only postings.\n"
    "    - TARGET ROLE: if keywords / target role are UNSPECIFIED or "
    "too vague to search, you MUST ask which role(s) to look for.\n"
    "* Apart from the MUST-ASK gaps, do NOT ask filler questions just "
    "to hit a quota. Zero questions is acceptable ONLY when location "
    "and target role are both clear and the rest of the brief is "
    "coherent.\n"
    "* Output 0-8 questions total.\n"
    "* Each question must be a direct yes/no or 1-2 sentence question "
    "to the user ('you' / 'vy'), with a short rationale.\n"
    "* Topics must be short labels (1-3 words). No duplicate topics in "
    "the same response.\n\n"
    "ANSWER OPTIONS (every question must include them):\n"
    "* Always provide 2-6 short answer options the user can click on. "
    "Keep each option short - ideally 1-4 words, never a full sentence.\n"
    "* Set multi_select=true ONLY when several options can apply at "
    "once. Otherwise multi_select=false.\n"
    "* The UI always lets the user type their own answer, so set "
    "allow_free_text=true (set false only for a strict enumeration). "
    "For open MUST-ASK questions like location, offer a few example "
    "options (e.g. 'Prague', 'Czech Republic', 'Remote (EU)', 'Remote "
    "(worldwide)') and keep allow_free_text=true.\n\n"
    "LANGUAGE (HARD REQUIREMENT):\n"
    "* OUTPUT_LANGUAGE applies to topic, question, rationale AND every "
    "option. Never mix English options into a Czech question."
)


def build_followup_user(
    *,
    output_lang: str,
    keywords: str,
    location_label: str,
    location_specified: bool = True,
    work_mode: str,
    seniority: str,
    profile_text: str,
    profile_file_text: str,
    profile_file_name: str,
    linkedin_url: str,
    tech_skills: str,
    additional_experience: str,
    contract_types: Optional[Iterable[str]],
    excluded_keywords: str,
    excluded_companies: str,
    excluded_locations: str,
    salary_min: int,
    salary_currency: str,
    search_mode: str,
) -> str:
    """Compose the user message for the follow-up-questions call.

    Hands every brief field to the model in a digest so it can decide
    which gaps deserve a question. Same digest shape as the discovery
    user message minus the structural goals (max_results, target_active).
    """
    language = _localise(output_lang)
    contracts = _format_list(contract_types or (), fallback="any")
    profile_block = _profile_block(
        tech_skills=tech_skills,
        additional_experience=additional_experience,
        seniority=seniority,
        profile_text=profile_text,
        profile_file_text=profile_file_text,
        profile_file_name=profile_file_name,
        linkedin_url=linkedin_url,
    )

    lines: list[str] = [
        f"OUTPUT_LANGUAGE: {output_lang}",
        f"Reply in {language}.",
        "",
        "TASK: Read the user's job-search brief below and decide what "
        "clarifying questions you would ask BEFORE running the search. "
        "Return JSON matching the follow-up-questions schema. Empty "
        "array is acceptable when the brief is already coherent.",
        "",
        "# Brief",
        (
            f"Keywords / target role: {keywords.strip()}"
            if keywords.strip()
            else "Keywords / target role: UNSPECIFIED (the user typed no "
            "role - you MUST ask which role(s) to search for)"
        ),
        (
            f"Location: {location_label.strip()}"
            if location_specified and location_label.strip()
            else "Location: UNSPECIFIED (the user did not choose a place - "
            "you MUST ask where to search before running)"
        ),
        f"Work mode: {(work_mode or 'any').strip()}",
        f"Search mode: {(search_mode or 'smart').strip()}",
        f"Self-declared seniority: {(seniority or 'any').strip()}",
        f"Contract preference: {contracts}",
        (
            f"Salary preference: {int(salary_min)} {salary_currency}/month"
            if salary_min and salary_currency and salary_currency.lower() != "any"
            else "Salary preference: not specified"
        ),
    ]
    excluded = []
    if excluded_keywords.strip():
        excluded.append(f"keywords: {excluded_keywords.strip()}")
    if excluded_companies.strip():
        excluded.append(f"companies: {excluded_companies.strip()}")
    if excluded_locations.strip():
        excluded.append(f"locations: {excluded_locations.strip()}")
    if excluded:
        lines.append("Exclusions: " + "; ".join(excluded))
    else:
        lines.append("Exclusions: none")
    lines.append("")
    lines.append("# Profile")
    lines.append(profile_block)
    lines.append("")
    lines.append("Return only the questions JSON.")
    return "\n".join(lines)


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
    tech_skills: str = "",
    additional_experience: str = "",
    seniority: str = "any",
    excluded_keywords: str = "",
    excluded_companies: str = "",
    excluded_locations: str = "",
    excluded_work_types: Optional[Iterable[str]] = None,
    custom_source_urls: str = "",
    job_age_days: int = 0,
    contract_types: Optional[Iterable[str]] = None,
    search_mode: str = "smart",
    salary_min: int = 0,
    salary_currency: str = "any",
    excluded_urls: Optional[Iterable[str]] = None,
    target_active: int = 0,
    relaxed_pass: bool = False,
    followup_qa: Optional[Iterable[dict]] = None,
) -> tuple[str, str]:
    """Build the (system, user) prompt for the web-search discovery pass.

    The system message sets the model's role as a recruiter using live
    web search; the user message packs every input the user supplied
    plus the location / work-mode / age / salary / search-mode
    constraints, plus the exclusions and selected sources.
    """
    language = _localise(output_lang)
    boards = _format_boards(preferred_boards)
    ats_hints = _format_boards(ATS_AND_CAREER_PAGES)
    mode_hint = _SEARCH_MODE_HINTS.get(
        (search_mode or "smart").strip().lower(),
        _SEARCH_MODE_HINTS["smart"],
    )

    system = (
        "You are an expert recruiter using your web-search tool to find "
        "currently active job postings on the public web. You MUST call "
        "web search MULTIPLE TIMES with different queries (different "
        "boards, different role synonyms, different city/region "
        "wordings) to verify each posting is still live (URL returns a "
        "real listing, not a 'job no longer available' page) and was "
        "published or updated within roughly the last 60 days (or the "
        "explicit age window the user requested).\n\n"
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
        "- Respect the user's exclusion list: drop postings whose "
        "title / company / location / type matches any exclusion. "
        "When a posting otherwise looks great but matches an "
        "exclusion, mention it in the Notes block ('Hidden because: "
        "matches excluded keyword X') so the user can audit.\n"
        f"- {mode_hint}\n"
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
    if target_active > 0 and target_active < max_results:
        # Over-fetch: the user wants ``target_active`` postings they can
        # actually apply to; the pipeline will URL-verify each result
        # and many will turn out to be expired or 404'd. Casting a wider
        # net up front + trimming post-verification gives the user the
        # number they asked for instead of a half-dead list.
        user_lines.append(
            f"Goal: find UP TO {int(max_results)} candidate postings so the "
            f"caller can verify each URL and end up with at least "
            f"{int(target_active)} that are still ACTIVELY hiring. "
            "Prefer fresh, well-known boards over stale aggregator copies."
        )
    else:
        user_lines.append(f"Goal: find up to {int(max_results)} ACTIVE job postings.")
    user_lines.append("")

    if relaxed_pass:
        # Final fallback when the strict top-ups exhausted: explicitly
        # ask for "less relevant but still active" postings. The
        # pipeline already flags them ``is_relaxed=True`` so the UI can
        # warn the user; the prompt just makes sure the model uses the
        # extra leeway productively instead of returning more of the
        # same dead links it could not find before.
        user_lines.append("# RELAXED PASS (strict matches exhausted)")
        user_lines.append(
            "The strict search did NOT find enough active postings for the "
            "user's filters. Now broaden the search: keep the location, "
            "seniority, work-mode and salary filters, but ALLOW adjacent "
            "roles (e.g. for 'QA Engineer' also accept 'Test Automation "
            "Engineer', 'SDET', 'Quality Analyst', 'Software Engineer in "
            "Test'). If the location filter is a city, ALSO include nearby "
            "cities in the same metro / region (e.g. 'Brno' -> 'Brno + "
            "remote within the Czech Republic'). Postings must still be "
            "currently hiring; do NOT return closed listings just to fill "
            "the count."
        )
        user_lines.append("")

    # Already-seen URLs (top-up pass) ---------------------------------
    seen_urls = [u.strip() for u in (excluded_urls or ()) if (u or "").strip()]
    if seen_urls:
        user_lines.append("# URLs already returned (do NOT return these again)")
        user_lines.append(
            "The caller already has these postings - return DIFFERENT ones "
            "this time. Search different boards, different role synonyms, "
            "different cities if applicable, but stay within the same "
            "filters."
        )
        for u in seen_urls[:30]:
            user_lines.append(f"- {u}")
        if len(seen_urls) > 30:
            user_lines.append(f"... ({len(seen_urls) - 30} more, all already returned)")
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

    user_lines.append("# Seniority")
    user_lines.append(_seniority_hint(seniority))
    user_lines.append("")

    # Contract types ---------------------------------------------------
    contracts = [c for c in (contract_types or ()) if c]
    user_lines.append("# Contract types")
    if contracts:
        user_lines.append(
            "Prefer postings advertised as: " + ", ".join(contracts)
            + ". Drop postings that explicitly require a contract type NOT in this list."
        )
    else:
        user_lines.append("No contract-type preference.")
    user_lines.append("")

    # Job age ----------------------------------------------------------
    user_lines.append("# Posting age")
    if job_age_days and job_age_days > 0:
        user_lines.append(
            f"Only postings published or updated in the last {int(job_age_days)} days. "
            "Drop everything older."
        )
    else:
        user_lines.append("Any age is fine, but prefer fresher postings.")
    user_lines.append("")

    # Salary -----------------------------------------------------------
    user_lines.append("# Salary preference")
    if salary_min and salary_min > 0 and (salary_currency or "").lower() not in {"", "any"}:
        user_lines.append(
            f"Prefer postings advertising at least {int(salary_min)} {salary_currency} "
            "per month. Postings without a listed salary may still appear, but "
            "explicitly lower-paid postings must be dropped."
        )
    else:
        user_lines.append("No salary filter.")
    user_lines.append("")

    # Skills -----------------------------------------------------------
    if tech_skills.strip() or additional_experience.strip():
        user_lines.append("# User's skills / experience")
        if tech_skills.strip():
            user_lines.append(f"Technologies and tools: {tech_skills.strip()}")
        if additional_experience.strip():
            user_lines.append(f"Other experience: {additional_experience.strip()}")
        user_lines.append(
            "Prefer postings that overlap with these skills. Do NOT silently drop "
            "great postings that only partially overlap - score them lower instead."
        )
        user_lines.append("")

    # Exclusions -------------------------------------------------------
    excluded_keywords_clean = excluded_keywords.strip()
    excluded_companies_clean = excluded_companies.strip()
    excluded_locations_clean = excluded_locations.strip()
    excluded_types_list = [t for t in (excluded_work_types or ()) if t]
    has_exclusions = bool(
        excluded_keywords_clean
        or excluded_companies_clean
        or excluded_locations_clean
        or excluded_types_list
    )
    user_lines.append("# Exclusions (drop or flag)")
    if has_exclusions:
        if excluded_keywords_clean:
            user_lines.append(f"Skip postings whose title / description contains: {excluded_keywords_clean}")
        if excluded_companies_clean:
            user_lines.append(f"Skip postings from these companies: {excluded_companies_clean}")
        if excluded_locations_clean:
            user_lines.append(f"Skip postings whose primary location matches: {excluded_locations_clean}")
        if excluded_types_list:
            user_lines.append(
                "Skip postings advertised as: " + ", ".join(excluded_types_list)
            )
    else:
        user_lines.append("No exclusions provided.")
    user_lines.append("")

    # Sources ----------------------------------------------------------
    user_lines.append("# Suggested job boards to search (use AT LEAST 3 different ones)")
    user_lines.append(
        "Boards listed first are usually most relevant for the chosen region. "
        "Do NOT restrict yourself to LinkedIn - actively search the others too."
    )
    user_lines.append(boards)
    user_lines.append("")

    custom_urls = _split_lines(custom_source_urls)
    if custom_urls:
        user_lines.append("# User-supplied career page URLs (also search these)")
        user_lines.append(
            "Look at these pages first - the user trusts them and wants postings from there:"
        )
        for url in custom_urls[:10]:
            user_lines.append(f"- {url}")
        user_lines.append("")

    user_lines.append("# Also search direct company career pages / ATS-hosted boards")
    user_lines.append(
        "Many active postings only live on the company's own site or on an "
        "ATS subdomain. Examples to try:"
    )
    user_lines.append(ats_hints)
    user_lines.append("")

    # Profile chunks ---------------------------------------------------
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

    # Output format ----------------------------------------------------
    user_lines.append("# Output format")
    user_lines.append(
        "For each position you found via web search, write a short block in this "
        "exact shape (one block per posting, separated by a blank line):"
    )
    user_lines.append("")
    user_lines.append("- Title: <job title>")
    user_lines.append("- Company: <company>")
    user_lines.append("- Location: <city, country or Remote>")
    user_lines.append("- Posted: <human date, e.g. 'last week' or 'unknown'>")
    user_lines.append("- Posted ISO: <YYYY-MM-DD or empty>")
    user_lines.append("- Salary: <range with currency, or empty>")
    user_lines.append("- Contract: <hpp | ico | contract | dpp_dpc | internship | freelance | unknown>")
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
        "richest). If you skipped any postings because of the exclusion "
        "list, mention them briefly so the user can audit."
    )

    extras = _format_followup_qa(followup_qa)
    if extras:
        user_lines.append("")
        user_lines.append(extras)

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
    excluded_urls: Optional[Iterable[str]] = None,
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
        "- ``posted_date_iso`` must be empty when the recruiter notes "
        "did not give a real date.\n"
        "- ``salary_text`` must be empty when not stated. Do NOT invent "
        "or estimate salary numbers.\n"
        "- ``contract_type`` must be 'unknown' unless the notes "
        "explicitly say HPP / OSVC / contract / DPP / internship / "
        "freelance. Do NOT guess.\n"
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
    seen_urls = [u.strip() for u in (excluded_urls or ()) if (u or "").strip()]
    if seen_urls:
        user_lines.append(
            "Drop entries whose URL is in the following list (the caller "
            "already has them):"
        )
        for u in seen_urls[:30]:
            user_lines.append(f"- {u}")
    user_lines.append("")
    user_lines.append("--- recruiter notes start ---")
    user_lines.append(discovery_text or "(empty)")
    user_lines.append("--- recruiter notes end ---")

    return system, "\n".join(user_lines)


# ---------------------------------------------------------------------------
# Pass 4 - per-position match scoring
# ---------------------------------------------------------------------------


def _profile_block(
    *,
    tech_skills: str,
    additional_experience: str,
    seniority: str,
    profile_text: str,
    profile_file_text: str,
    profile_file_name: str,
    linkedin_url: str,
) -> str:
    """Bundle every user-side input into a single readable block.

    Both the match and the skill-gap passes feed off the same digest
    so the LLM sees identical context across the two passes. Trimmed
    to keep the per-position call cheap (we send this block N times in
    Pass 4).
    """
    lines: list[str] = []
    if tech_skills.strip():
        lines.append(f"Technologies / tools: {tech_skills.strip()}")
    if additional_experience.strip():
        lines.append(f"Other experience: {additional_experience.strip()}")
    if seniority and seniority.lower() != "any":
        lines.append(f"Self-declared seniority: {seniority}")
    if profile_text.strip():
        lines.append("Free-text bio:")
        lines.append(_truncate(profile_text, max_chars=1400))
    if profile_file_text.strip():
        label = profile_file_name or "uploaded CV"
        lines.append(f"CV / LinkedIn export ({label}):")
        lines.append(_truncate(profile_file_text, max_chars=2500))
    if linkedin_url.strip():
        lines.append(f"Public LinkedIn URL: {linkedin_url.strip()}")
    return "\n".join(lines) if lines else "(empty - user did not supply a profile)"


def build_match_prompt(
    *,
    output_lang: str,
    position: dict[str, Any],
    tech_skills: str = "",
    additional_experience: str = "",
    seniority: str = "any",
    profile_text: str = "",
    profile_file_text: str = "",
    profile_file_name: str = "",
    linkedin_url: str = "",
    followup_qa: Optional[Iterable[dict]] = None,
) -> tuple[str, str]:
    """Build the (system, user) prompt for the per-position scoring pass.

    The LLM only sees one posting at a time, which keeps the prompt
    short and lets us parallelise the calls. The schema in
    :data:`schema.MATCH_SCHEMA` pins the response shape.
    """
    language = _localise(output_lang)

    system = (
        "You are a hiring expert comparing one job posting against a "
        "candidate profile. Return ONLY the JSON the schema requires. "
        "Hard rules:\n"
        "- Be honest. If the user is missing core requirements the "
        "match score should be below 60. Reserve 80+ for postings the "
        "user could realistically land an interview for.\n"
        "- ``matched_skills`` lists ONLY things present in BOTH the "
        "posting and the profile. Never copy the user's whole skill "
        "list, only the overlap.\n"
        "- ``missing_skills`` lists ONLY requirements the posting "
        "EXPLICITLY asks for that the user did not clearly "
        "demonstrate. No generic filler ('communication skills', "
        "'team player') unless the posting names them.\n"
        "- ``recommendation`` is one or two short sentences, in plain "
        "language, in the user's chosen output language. No emojis, "
        "no salesy language, no 'You should definitely apply!!!'.\n"
        f"- Output language for prose: {language}. Skill labels and "
        "company names stay verbatim.\n"
    )

    posting_json = json.dumps(
        {
            "title": (position.get("title") or "").strip(),
            "company": (position.get("company") or "").strip(),
            "location": (position.get("location") or "").strip(),
            "summary": (position.get("summary") or "").strip(),
            "work_mode": (position.get("work_mode") or "unknown").strip(),
            "salary_text": (position.get("salary_text") or "").strip(),
            "contract_type": (position.get("contract_type") or "unknown").strip(),
            "source": (position.get("source") or "").strip(),
        },
        ensure_ascii=False,
        indent=2,
    )
    profile_block = _profile_block(
        tech_skills=tech_skills,
        additional_experience=additional_experience,
        seniority=seniority,
        profile_text=profile_text,
        profile_file_text=profile_file_text,
        profile_file_name=profile_file_name,
        linkedin_url=linkedin_url,
    )

    extras = _format_followup_qa(followup_qa)
    user = (
        "# Posting to score\n"
        f"{posting_json}\n\n"
        "# Candidate profile\n"
        f"{profile_block}\n"
    )
    if extras:
        user += f"\n{extras}\n"

    return system, user


# ---------------------------------------------------------------------------
# Pass 5 - aggregate skill-gap analysis
# ---------------------------------------------------------------------------


def build_skill_gap_prompt(
    *,
    output_lang: str,
    positions: list[dict[str, Any]],
    tech_skills: str = "",
    additional_experience: str = "",
    seniority: str = "any",
    profile_text: str = "",
    profile_file_text: str = "",
    profile_file_name: str = "",
    linkedin_url: str = "",
    followup_qa: Optional[Iterable[dict]] = None,
) -> tuple[str, str]:
    """Build the (system, user) prompt for the skill-gap aggregation.

    The LLM sees the entire position list (titles, companies,
    summaries, matched / missing skills from Pass 4) so it can spot
    recurring requirements. Returns :data:`schema.SKILL_GAP_SCHEMA`.
    """
    language = _localise(output_lang)

    system = (
        "You are a career coach comparing a candidate's profile against "
        "a batch of job postings. Return ONLY the JSON the schema "
        "requires. Hard rules:\n"
        "- ``top_required`` lists the most frequently required skills "
        "across the position set, sorted by ``count`` descending. "
        "Count one posting once per skill - do not double-count "
        "synonyms. Cap at 10.\n"
        "- ``user_strong`` is the intersection: skills the user "
        "clearly has AND that the postings frequently want. Cap at 8.\n"
        "- ``user_missing`` is the gap: skills the postings frequently "
        "want and the user did NOT clearly demonstrate. Cap at 8. No "
        "generic filler.\n"
        "- ``advice`` is 1-6 short paragraphs of concrete next steps "
        "(what to learn, what to highlight in the CV, which roles are "
        "safer bets). Each paragraph is one entry in the array. No "
        "lists of bullets inside a single entry.\n"
        f"- Output language for prose: {language}. Skill labels stay "
        "verbatim regardless of language.\n"
    )

    posting_digest: list[dict[str, Any]] = []
    for item in positions[:25]:
        posting_digest.append({
            "title": (item.get("title") or "").strip(),
            "company": (item.get("company") or "").strip(),
            "summary": _truncate((item.get("summary") or "").strip(), max_chars=400),
            "matched": list((item.get("matched_skills") or [])[:8]),
            "missing": list((item.get("missing_skills") or [])[:8]),
            "match_score": int(item.get("match_score") or 0),
        })

    posting_json = json.dumps(posting_digest, ensure_ascii=False, indent=2)
    profile_block = _profile_block(
        tech_skills=tech_skills,
        additional_experience=additional_experience,
        seniority=seniority,
        profile_text=profile_text,
        profile_file_text=profile_file_text,
        profile_file_name=profile_file_name,
        linkedin_url=linkedin_url,
    )

    extras = _format_followup_qa(followup_qa)
    user = (
        "# Positions found in this search\n"
        f"{posting_json}\n\n"
        "# Candidate profile\n"
        f"{profile_block}\n"
    )
    if extras:
        user += f"\n{extras}\n"

    return system, user
