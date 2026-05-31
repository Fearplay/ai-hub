"""Unified career-profile JSON schema.

``CAREER_PROFILE_SCHEMA`` is a superset of AI Career's ``CANDIDATE_SCHEMA``
plus a few LinkedIn-flavoured fields (``headline``, ``industry``,
``online_links``). It is the single structured representation the "My
Profile" section extracts once and that AI Career / AI Job Search / AI
LinkedIn map into their own in-memory shapes.

Strict JSON-schema mode (OpenAI) rejects extra keys and requires every
property to be listed in ``required`` - so optional facts use the empty
string / empty array convention, never a missing key.
"""

from __future__ import annotations


CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")


CAREER_PROFILE_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "full_name",
        "headline",
        "industry",
        "contact",
        "summary",
        "technical_skills",
        "experiences",
        "education",
        "certifications",
        "languages",
        "projects",
        "online_links",
        "linkedin_present",
        "github_present",
    ],
    "properties": {
        "full_name": {"type": "string"},
        "headline": {
            "type": "string",
            "description": "Short professional headline, e.g. 'Senior QA Engineer'. Empty if unknown.",
        },
        "industry": {
            "type": "string",
            "description": "Primary industry/field. Empty if unknown.",
        },
        "contact": {
            "type": "object",
            "additionalProperties": False,
            "required": ["email", "phone", "location"],
            "properties": {
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "location": {"type": "string"},
            },
        },
        "summary": {
            "type": "string",
            "description": "2-4 sentences describing the person. No invented facts.",
        },
        "technical_skills": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Sorted by relevance; deduplicated across CZ/EN.",
        },
        "experiences": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["role", "company", "period", "employment_type", "location", "bullets"],
                "properties": {
                    "role": {"type": "string"},
                    "company": {"type": "string"},
                    "period": {"type": "string", "description": "e.g. 2022-2024 or 06/2022 - 09/2024."},
                    "employment_type": {
                        "type": "string",
                        "description": "Empty for full-time. Otherwise Internship, Contract, Part-time, Freelance.",
                    },
                    "location": {"type": "string"},
                    "bullets": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["institution", "degree", "period", "details"],
                "properties": {
                    "institution": {"type": "string"},
                    "degree": {"type": "string"},
                    "period": {"type": "string"},
                    "details": {"type": "string"},
                },
            },
        },
        "certifications": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "issuer", "period"],
                "properties": {
                    "name": {"type": "string"},
                    "issuer": {"type": "string"},
                    "period": {"type": "string"},
                },
            },
        },
        "languages": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "cefr"],
                "properties": {
                    "name": {"type": "string"},
                    "cefr": {
                        "type": "string",
                        "enum": list(CEFR_LEVELS) + [""],
                        "description": "CEFR only: A1/A2/B1/B2/C1/C2. Empty if unknown.",
                    },
                },
            },
        },
        "projects": {
            "type": "array",
            "maxItems": 6,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "period", "url", "bullets"],
                "properties": {
                    "name": {"type": "string"},
                    "period": {"type": "string"},
                    "url": {"type": "string"},
                    "bullets": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
        "online_links": {
            "type": "array",
            "maxItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["label", "url"],
                "properties": {
                    "label": {"type": "string"},
                    "url": {"type": "string"},
                },
            },
            "description": "Portfolio / website / LinkedIn / GitHub links present in the source. Never invent URLs.",
        },
        "linkedin_present": {"type": "boolean"},
        "github_present": {"type": "boolean"},
    },
}
