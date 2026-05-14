"""JSON Schema for the AI Jobs structured-output extraction step.

The pipeline runs the search in two passes (see ``pipeline.py``):

1. A web-search pass with no schema. The provider's hosted web-search
   tool only fires when ``schema is None`` (per
   :mod:`src.services.ai_provider`), so we get free-form prose with
   live links that AI just discovered.
2. A second extraction pass that *does* pin the model down to this
   strict schema, fed the prose from pass #1 as the user message. No
   web search this time - we are only normalising data.

Keeping the schema narrow keeps token use low and matches the card
layout the Results tab actually renders.
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
                        "description": "When the posting went live, e.g. '2026-05-08' or 'last week'. Empty string if unknown.",
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
