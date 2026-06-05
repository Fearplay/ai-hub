"""JSON schemas for the AI Career structured outputs.

Three schemas, used by :mod:`src.sections.ai_cv.pipeline`:

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
                "required": [
                    "topic",
                    "question",
                    "rationale",
                    "options",
                    "multi_select",
                    "allow_free_text",
                ],
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
                    "options": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 6,
                        "items": {"type": "string"},
                        "description": (
                            "2-6 short, plausible answer options the candidate "
                            "can pick from. Examples for 'Have you used n8n?': "
                            "['Yes, several workflows', 'Just tried it', 'No']. "
                            "Make options mutually exclusive when multi_select=false; "
                            "when multi_select=true the user can pick several. "
                            "Always written in OUTPUT_LANGUAGE."
                        ),
                    },
                    "multi_select": {
                        "type": "boolean",
                        "description": (
                            "True when several options can apply at once "
                            "(e.g. 'Which Azure services have you used?'). "
                            "False for binary / single-choice questions "
                            "(e.g. 'Have you led a team?')."
                        ),
                    },
                    "allow_free_text": {
                        "type": "boolean",
                        "description": (
                            "True when the candidate may add an 'Other' answer "
                            "with their own short text. Default to true unless "
                            "the options clearly enumerate every possible answer."
                        ),
                    },
                },
            },
        },
    },
}


MODERN_CV_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "full_name",
        "role_headline",
        "role_subtitle",
        "contact",
        "online_links",
        "skill_groups",
        "languages",
        "profile_summary",
        "leadership_highlights",
        "experience",
        "projects",
        "education",
        "certifications",
    ],
    "properties": {
        "full_name": {"type": "string"},
        "role_headline": {
            "type": "string",
            "description": (
                "Big single-line role headline shown in the sidebar under "
                "the name. Example: 'Senior Software QA Engineer'."
            ),
        },
        "role_subtitle": {
            "type": "string",
            "description": (
                "Optional one-line role qualifier (acting lead, squad size, "
                "scope). Empty string if nothing relevant."
            ),
        },
        "contact": {
            "type": "object",
            "additionalProperties": False,
            "required": ["location", "email", "phone"],
            "properties": {
                "location": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
            },
        },
        "online_links": {
            "type": "array",
            "description": (
                "Sidebar 'Online' links. Only emit entries whose URL was "
                "actually present in the source - never invent. Each row "
                "is icon-letter + display label + url."
            ),
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["icon", "label", "url"],
                "properties": {
                    "icon": {
                        "type": "string",
                        "description": (
                            "Short visible marker rendered before the link "
                            "in the sidebar. Examples: 'in' (LinkedIn), "
                            "'gh' (GitHub), '>' (portfolio), 'app' (app), "
                            "'+' (other)."
                        ),
                    },
                    "label": {"type": "string"},
                    "url": {"type": "string"},
                },
            },
        },
        "skill_groups": {
            "type": "array",
            "description": (
                "Skill chips grouped by domain. Group labels are short "
                "(2-4 words). Tags are 1-3 words each. Order groups by "
                "relevance to the target role, most relevant first."
            ),
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["label", "tags"],
                "properties": {
                    "label": {"type": "string"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
        "languages": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "level"],
                "properties": {
                    "name": {"type": "string"},
                    "level": {
                        "type": "string",
                        "description": (
                            "Free-form short label for visual rendering. "
                            "Prefer CEFR (A1-C2) or 'native'/'passive' "
                            "when explicit in the source."
                        ),
                    },
                },
            },
        },
        "profile_summary": {
            "type": "string",
            "description": (
                "Rich paragraph (~80-160 words) that opens the main column. "
                "Use **bold** Markdown around the 5-10 highest-impact "
                "phrases (role title, employers, scope numbers, key "
                "outcomes). Plain text otherwise; no headings, no bullets."
            ),
        },
        "leadership_highlights": {
            "type": "array",
            "description": (
                "4-6 short, scannable wins shown in a banner under the "
                "summary. Each line uses **bold** Markdown around the "
                "quantitative or signature phrase. Empty array when the "
                "candidate has no leadership signal yet."
            ),
            "items": {"type": "string"},
        },
        "experience": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "role",
                    "period",
                    "company",
                    "context",
                    "highlight_pills",
                    "bullets",
                ],
                "properties": {
                    "role": {"type": "string"},
                    "period": {"type": "string"},
                    "company": {"type": "string"},
                    "context": {
                        "type": "string",
                        "description": (
                            "Italic subtitle next to the company name. "
                            "Examples: '(Norton · Avast · AVG · CCleaner)' "
                            "or '· Prague · Data Trust Services team'. "
                            "Empty string if there's nothing to add."
                        ),
                    },
                    "highlight_pills": {
                        "type": "array",
                        "description": (
                            "0-5 short tag pills shown above the bullets "
                            "summarising the role's signature themes. "
                            "Each pill is 1-3 words."
                        ),
                        "items": {"type": "string"},
                    },
                    "bullets": {
                        "type": "array",
                        "description": (
                            "2-6 outcome-focused bullets. Use **bold** "
                            "Markdown around the achievement phrase or "
                            "quantitative result inside each bullet."
                        ),
                        "items": {"type": "string"},
                    },
                },
            },
        },
        "projects": {
            "type": "array",
            "maxItems": 6,
            "description": (
                "Side-projects / personal projects shown as project "
                "cards. Only include entries that are actually backed by "
                "the candidate's source data."
            ),
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "description", "url"],
                "properties": {
                    "name": {"type": "string"},
                    "description": {
                        "type": "string",
                        "description": (
                            "1-3 sentences. Use **bold** Markdown around "
                            "the most important phrase (product name, "
                            "outcome, scope)."
                        ),
                    },
                    "url": {"type": "string"},
                },
            },
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "sub", "period"],
                "properties": {
                    "title": {"type": "string"},
                    "sub": {
                        "type": "string",
                        "description": "Italic subtitle: institution + faculty.",
                    },
                    "period": {"type": "string"},
                },
            },
        },
        "certifications": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["year", "text"],
                "properties": {
                    "year": {"type": "string"},
                    "text": {
                        "type": "string",
                        "description": (
                            "Issuer + course / certification name. Use "
                            "**bold** Markdown around the actual program "
                            "name when it stands out."
                        ),
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
            "description": (
                "Likely questions an interviewer would ask, with the rationale "
                "they would have for asking and a suggested STAR-style answer "
                "the candidate can adapt."
            ),
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["question", "why_asked", "suggested_answer"],
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The interview question itself.",
                    },
                    "why_asked": {
                        "type": "string",
                        "description": (
                            "1-2 sentences explaining what the interviewer is "
                            "trying to learn by asking this. Tied to the job "
                            "spec, not generic best-practice."
                        ),
                    },
                    "suggested_answer": {
                        "type": "string",
                        "description": (
                            "A 60-120 word draft answer in STAR shape using "
                            "evidence from the candidate JSON; avoid invented "
                            "facts."
                        ),
                    },
                },
            },
        },
        "skill_gap_plan": {
            "type": "array",
            "description": (
                "Concrete plan to close gaps the recruiter / interviewer is "
                "likely to flag, with criticality, rationale, learning path, "
                "and a portfolio-able project the candidate can build."
            ),
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "skill",
                    "action",
                    "timeline_weeks",
                    "criticality",
                    "why_it_matters",
                    "learning_path",
                    "suggested_project",
                ],
                "properties": {
                    "skill": {"type": "string"},
                    "action": {
                        "type": "string",
                        "description": "One-line summary of the action.",
                    },
                    "timeline_weeks": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 52,
                    },
                    "criticality": {
                        "type": "string",
                        "enum": ["critical", "important", "nice_to_have"],
                        "description": (
                            "How blocking the gap is. ``critical`` = the role "
                            "explicitly requires it; ``important`` = strongly "
                            "preferred; ``nice_to_have`` = differentiator."
                        ),
                    },
                    "why_it_matters": {
                        "type": "string",
                        "description": (
                            "1-2 sentences explaining the role-specific "
                            "consequence of leaving this gap unaddressed."
                        ),
                    },
                    "learning_path": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 6,
                        "items": {"type": "string"},
                        "description": (
                            "Ordered concrete steps (course / book / repo / "
                            "exercise) the candidate should take. Each step "
                            "is one short imperative line."
                        ),
                    },
                    "suggested_project": {
                        "type": "string",
                        "description": (
                            "A small, portfolio-able project the candidate "
                            "can build to prove the skill - 1-2 sentences "
                            "describing scope and visible outcome."
                        ),
                    },
                },
            },
        },
    },
}


# One turn of the Mock Interview simulator. The model plays both the
# interviewer (asks the next tailored question) and the coach (grades the
# candidate's previous answer against the STAR method). ``feedback`` /
# ``strengths`` / ``gaps`` / ``improved_answer`` are empty on the very
# first turn (there is no answer to grade yet); ``next_question`` is empty
# only when ``done`` is true.
INTERVIEW_TURN_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "feedback",
        "strengths",
        "gaps",
        "improved_answer",
        "next_question",
        "question_focus",
        "done",
    ],
    "properties": {
        "feedback": {
            "type": "string",
            "description": (
                "2-4 sentence STAR critique of the candidate's previous "
                "answer. Empty string on the opening turn."
            ),
        },
        "strengths": {
            "type": "array",
            "maxItems": 4,
            "items": {"type": "string"},
            "description": "What the answer did well (STAR). Empty on the opening turn.",
        },
        "gaps": {
            "type": "array",
            "maxItems": 4,
            "items": {"type": "string"},
            "description": (
                "Missing STAR elements / weak spots, each a short imperative "
                "line. Empty on the opening turn."
            ),
        },
        "improved_answer": {
            "type": "string",
            "description": (
                "A rewritten model answer grounded ONLY in the candidate's "
                "evidence. Use [insert metric] placeholders rather than "
                "inventing numbers. Empty on the opening turn."
            ),
        },
        "next_question": {
            "type": "string",
            "description": (
                "The next interview question, tailored to the role and the "
                "candidate's background. Empty only when done is true."
            ),
        },
        "question_focus": {
            "type": "string",
            "description": (
                "Short tag for the next question's theme, e.g. "
                "'Behavioural - leadership' / 'Technical - testing'."
            ),
        },
        "done": {
            "type": "boolean",
            "description": (
                "True when the interviewer decides to wrap up (after ~6 "
                "questions or when the candidate asks to stop)."
            ),
        },
    },
}
