"""JSON schemas for the AI Career structured outputs.

Three schemas, used by :mod:`src.sections.ai_career.pipeline`:

* :data:`CANDIDATE_SCHEMA` - the structured representation of the user
  produced from the uploaded CV (+ optional LinkedIn export + GitHub).
* :data:`JOB_SPEC_SCHEMA` - the structured representation of the job
  posting after scraping.
* :data:`MATCH_ANALYSIS_SCHEMA` - the comparison output: score per category,
  matches, gaps, ATS keywords, interview questions and a skill-gap plan.

The schemas are intentionally narrow; OpenAI's strict JSON-schema mode
rejects extra fields. Keep "unknown" / "neuvedeno" as the convention for
missing values - the no-hallucination clause forbids inventing them.
"""

from __future__ import annotations


CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
SENIORITY_LEVELS = ("junior", "mid", "senior", "lead", "unknown")


CANDIDATE_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "full_name",
        "contact",
        "summary",
        "experiences",
        "education",
        "certifications",
        "languages",
        "projects",
        "technical_skills",
        "linkedin_present",
        "github_present",
    ],
    "properties": {
        "full_name": {"type": "string"},
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
            "description": "2-4 sentences describing the candidate. No invented facts.",
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
                "required": ["role", "company", "period", "bullets", "employment_type", "location"],
                "properties": {
                    "role": {"type": "string"},
                    "company": {"type": "string"},
                    "period": {"type": "string", "description": "Required. e.g. 2022-2024 or 06/2022 - 09/2024."},
                    "employment_type": {
                        "type": "string",
                        "description": "Empty for full-time. Otherwise e.g. Internship, Contract, Part-time, Freelance.",
                    },
                    "location": {"type": "string"},
                    "bullets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "At least 2 bullets per role unless the source had fewer.",
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
                    "institution": {"type": "string", "description": "Required and non-empty."},
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
                        "description": "CEFR only: A1/A2/B1/B2/C1/C2. Empty if unknown - never 'Native' or 'Fluent'.",
                    },
                },
            },
        },
        "projects": {
            "type": "array",
            "maxItems": 5,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "period", "bullets", "url"],
                "properties": {
                    "name": {"type": "string"},
                    "period": {"type": "string"},
                    "bullets": {"type": "array", "items": {"type": "string"}},
                    "url": {"type": "string"},
                },
            },
        },
        "linkedin_present": {"type": "boolean"},
        "github_present": {"type": "boolean"},
    },
}


JOB_SPEC_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "title",
        "company",
        "location",
        "seniority",
        "summary",
        "must_have",
        "nice_to_have",
        "tools",
        "soft_skills",
        "ats_keywords",
        "compensation",
        "employment_type",
    ],
    "properties": {
        "title": {"type": "string"},
        "company": {"type": "string"},
        "location": {"type": "string"},
        "seniority": {
            "type": "string",
            "enum": list(SENIORITY_LEVELS),
        },
        "summary": {"type": "string"},
        "must_have": {"type": "array", "items": {"type": "string"}},
        "nice_to_have": {"type": "array", "items": {"type": "string"}},
        "tools": {"type": "array", "items": {"type": "string"}},
        "soft_skills": {"type": "array", "items": {"type": "string"}},
        "ats_keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Exact terminology from the JD - case preserved.",
        },
        "compensation": {"type": "string"},
        "employment_type": {"type": "string"},
    },
}


FOLLOWUP_QUESTIONS_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["questions"],
    "properties": {
        "questions": {
            "type": "array",
            "minItems": 0,
            "maxItems": 12,
            "description": (
                "0-12 clarifying questions about JD requirements that the "
                "candidate's documents do not clearly answer. Empty array "
                "when nothing is unclear."
            ),
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["topic", "question", "rationale"],
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Short label - 1-3 words, e.g. 'Python', 'Team lead'.",
                    },
                    "question": {
                        "type": "string",
                        "description": (
                            "Direct question to the candidate (you / vy). "
                            "Answerable in 1-2 sentences."
                        ),
                    },
                    "rationale": {
                        "type": "string",
                        "description": "One short sentence: why we are asking, tied to the JD.",
                    },
                },
            },
        },
    },
}


MATCH_ANALYSIS_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "overall_score",
        "verdict",
        "categories",
        "matches",
        "gaps",
        "ats_keywords_present",
        "ats_keywords_missing",
        "evidence_preview",
        "interview_questions",
        "skill_gap_plan",
    ],
    "properties": {
        "overall_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "verdict": {
            "type": "string",
            "description": "One sentence summary - e.g. 'Strong fit, two minor gaps'.",
        },
        "categories": {
            "type": "array",
            "minItems": 3,
            "maxItems": 5,
            "description": "3-5 dynamic categories named for this role (e.g. 'Digital marketing', 'Analytics', 'Soft skills').",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "score", "evidence"],
                "properties": {
                    "name": {"type": "string"},
                    "score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "matches": {"type": "array", "items": {"type": "string"}},
        "gaps": {"type": "array", "items": {"type": "string"}},
        "ats_keywords_present": {"type": "array", "items": {"type": "string"}},
        "ats_keywords_missing": {"type": "array", "items": {"type": "string"}},
        "evidence_preview": {
            "type": "array",
            "items": {"type": "string"},
            "description": "5-10 short snippets quoting (or paraphrasing) the candidate evidence per match.",
        },
        "interview_questions": {
            "type": "array",
            "minItems": 5,
            "maxItems": 12,
            "items": {"type": "string"},
        },
        "skill_gap_plan": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["skill", "action", "timeline_weeks"],
                "properties": {
                    "skill": {"type": "string"},
                    "action": {"type": "string"},
                    "timeline_weeks": {"type": "integer", "minimum": 1, "maximum": 52},
                },
            },
        },
    },
}
