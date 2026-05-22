"""JSON Schemas for the AI Jobs structured-output passes.

The pipeline runs the search in five passes (see ``pipeline.py``):

1. A web-search pass with no schema. The provider's hosted web-search
   tool only fires when ``schema is None`` (per
   :mod:`src.services.ai_provider`), so we get free-form prose with
   live links that AI just discovered.
2. An **extraction** pass pinned to :data:`JOB_LISTINGS_SCHEMA`. Fed
   the prose from pass #1, no web search this time - we are only
   normalising data into the dict the UI renders.
3. **URL verification** - a pure Python pass with no LLM call.
4. A per-position **scoring** pass pinned to :data:`MATCH_SCHEMA`.
   Compares one job posting against the user's profile and returns a
   match score plus matched / missing skills plus a 1-2 sentence AI
   recommendation. Cheap, schema-only, no web search.
5. An aggregate **skill-gap** pass pinned to :data:`SKILL_GAP_SCHEMA`.
   One call that summarises the recurring requirements across all
   positions and produces actionable advice for the user.

Keeping the schemas narrow keeps token use low and matches the dict
shape the on-screen card / HTML renderer expects.
"""

from __future__ import annotations


JOB_LISTINGS_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["positions", "summary"],
    "properties": {
        "positions": {
            "type": "array",
            "description": "List of unique active job postings. Drop duplicates and any posting whose URL is missing.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "title",
                    "company",
                    "location",
                    "posted",
                    "posted_date_iso",
                    "salary_text",
                    "contract_type",
                    "summary",
                    "url",
                    "source",
                    "work_mode",
                ],
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Exact job title as shown in the posting.",
                    },
                    "company": {
                        "type": "string",
                        "description": "Hiring company name. Use 'unknown' if the posting genuinely does not name one.",
                    },
                    "location": {
                        "type": "string",
                        "description": "City + country (or 'Remote'). Must match the user's requested location filter.",
                    },
                    "posted": {
                        "type": "string",
                        "description": "Human-readable when the posting went live, e.g. 'last week', '3 days ago'. Empty string if unknown.",
                    },
                    "posted_date_iso": {
                        "type": "string",
                        "description": "ISO date of the posting (YYYY-MM-DD) when known, else empty string. Used to sort by freshness.",
                    },
                    "salary_text": {
                        "type": "string",
                        "description": "Salary range as advertised, e.g. '70 000-95 000 CZK / month' or 'EUR 60k-80k'. Empty string when not listed.",
                    },
                    "contract_type": {
                        "type": "string",
                        "enum": [
                            "hpp",
                            "ico",
                            "contract",
                            "dpp_dpc",
                            "internship",
                            "freelance",
                            "unknown",
                        ],
                        "description": "Contract type the posting advertises (use 'unknown' when not stated).",
                    },
                    "summary": {
                        "type": "string",
                        "description": "1-2 sentences describing the role responsibilities and key required skills.",
                    },
                    "url": {
                        "type": "string",
                        "description": "Direct URL to the posting. Must start with http:// or https:// and link to the application page (not a search results page).",
                    },
                    "source": {
                        "type": "string",
                        "description": "Job board or company career site the posting was found on (e.g. 'LinkedIn Jobs', 'jobs.cz', 'company careers page').",
                    },
                    "work_mode": {
                        "type": "string",
                        "enum": ["remote", "hybrid", "onsite", "unknown"],
                        "description": "Work setup as advertised by the posting.",
                    },
                },
            },
        },
        "summary": {
            "type": "string",
            "description": "1-3 sentences summarising the overall match between the user's brief and the postings found (e.g. trends, salary expectations, what to focus on).",
        },
    },
}


# ---------------------------------------------------------------------------
# Pass 4 - per-position match scoring
# ---------------------------------------------------------------------------


MATCH_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["match_score", "matched_skills", "missing_skills", "recommendation"],
    "properties": {
        "match_score": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
            "description": (
                "Overall fit between the user's profile and the posting, "
                "0 (no overlap) to 100 (textbook match). Be honest - if the "
                "user only has 2 of 6 required skills the score should reflect that."
            ),
        },
        "matched_skills": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Concrete skills / experiences the user has that the posting "
                "explicitly asks for. Use short labels (e.g. 'Python', 'API testing'). "
                "Maximum 8 entries. Never invent skills the posting did not mention."
            ),
        },
        "missing_skills": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Skills the posting requires that the user did NOT clearly "
                "demonstrate. Maximum 6 entries. Stay grounded in the posting "
                "text - do not invent generic requirements."
            ),
        },
        "recommendation": {
            "type": "string",
            "description": (
                "One or two sentences for the user: highlight what they should "
                "emphasise in their CV when applying for this role, and whether "
                "it is worth a shot. No fluff, no salesy language."
            ),
        },
    },
}


# ---------------------------------------------------------------------------
# Pass 5 - aggregate skill-gap analysis across all positions
# ---------------------------------------------------------------------------


SKILL_GAP_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["top_required", "user_strong", "user_missing", "advice"],
    "properties": {
        "top_required": {
            "type": "array",
            "description": (
                "Most frequently requested skills across the position set, "
                "sorted by ``count`` descending. Maximum 10 entries."
            ),
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["skill", "count"],
                "properties": {
                    "skill": {
                        "type": "string",
                        "description": "Short skill label, e.g. 'Docker', 'API testing'.",
                    },
                    "count": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "How many positions in the result set asked for this skill.",
                    },
                },
            },
        },
        "user_strong": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Skills the user clearly has that are in high demand. "
                "Maximum 8 entries. Stay grounded in the user's profile material."
            ),
        },
        "user_missing": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Skills in high demand the user does NOT yet demonstrate. "
                "Maximum 8 entries. No generic filler - only things that "
                "appear in multiple postings."
            ),
        },
        "advice": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Concrete actions for the user: what to learn next, what to "
                "highlight in the CV, which roles are the safest bets. "
                "1-6 short paragraphs (each one item in this array)."
            ),
        },
    },
}
