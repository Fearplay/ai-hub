"""JSON schemas for the AI LinkedIn structured outputs.

Each schema is used by exactly one ``ai_provider.run`` call inside
:mod:`src.sections.ai_linkedin.pipeline`. The schemas are intentionally
narrow; OpenAI's strict JSON-schema mode rejects extra fields. Keep
"unknown" / empty arrays / empty strings as the convention for missing
values - the no-hallucination clause forbids inventing them.
"""

from __future__ import annotations


CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")


EVIDENCE_ANCHOR_VALUES = (
    "resume",
    "linkedin_export",
    "github",
    "user_confirmed",
    "target_role",
    "missing_evidence",
)


AUDIENCE_VALUES = (
    "recruiter",
    "hiring_manager",
    "founder",
    "peer",
    "community",
    "general",
)


POST_KIND_VALUES = (
    "learning_update",
    "project_launch",
    "job_search",
    "recruiter_outreach",
    "networking",
    "comment",
)


# --- Profile extraction ------------------------------------------------


PROFILE_EXTRACT_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "full_name",
        "headline_current",
        "industry",
        "location",
        "contact",
        "summary",
        "experiences",
        "education",
        "certifications",
        "languages",
        "skills",
        "projects",
        "online_links",
        "linkedin_present",
        "github_present",
    ],
    "properties": {
        "full_name": {"type": "string"},
        "headline_current": {
            "type": "string",
            "description": (
                "Existing LinkedIn headline if the export had one,"
                " otherwise the role line from the resume header."
                " Empty when neither source provides one."
            ),
        },
        "industry": {"type": "string"},
        "location": {"type": "string"},
        "contact": {
            "type": "object",
            "additionalProperties": False,
            "required": ["email", "phone"],
            "properties": {
                "email": {"type": "string"},
                "phone": {"type": "string"},
            },
        },
        "summary": {
            "type": "string",
            "description": "2-4 sentences. Plain factual prose. No invented facts.",
        },
        "experiences": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "role",
                    "company",
                    "period",
                    "employment_type",
                    "location",
                    "bullets",
                    "evidence_anchor",
                ],
                "properties": {
                    "role": {"type": "string"},
                    "company": {"type": "string"},
                    "period": {"type": "string"},
                    "employment_type": {"type": "string"},
                    "location": {"type": "string"},
                    "bullets": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "evidence_anchor": {
                        "type": "string",
                        "enum": list(EVIDENCE_ANCHOR_VALUES),
                    },
                },
            },
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["institution", "degree", "period", "details", "evidence_anchor"],
                "properties": {
                    "institution": {"type": "string"},
                    "degree": {"type": "string"},
                    "period": {"type": "string"},
                    "details": {"type": "string"},
                    "evidence_anchor": {
                        "type": "string",
                        "enum": list(EVIDENCE_ANCHOR_VALUES),
                    },
                },
            },
        },
        "certifications": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "issuer", "year", "evidence_anchor"],
                "properties": {
                    "name": {"type": "string"},
                    "issuer": {"type": "string"},
                    "year": {"type": "string"},
                    "evidence_anchor": {
                        "type": "string",
                        "enum": list(EVIDENCE_ANCHOR_VALUES),
                    },
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
                    },
                },
            },
        },
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "category", "evidence_anchor"],
                "properties": {
                    "name": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["core", "tooling", "soft", "domain", "language"],
                    },
                    "evidence_anchor": {
                        "type": "string",
                        "enum": list(EVIDENCE_ANCHOR_VALUES),
                    },
                },
            },
        },
        "projects": {
            "type": "array",
            "maxItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "period", "description", "url", "evidence_anchor"],
                "properties": {
                    "name": {"type": "string"},
                    "period": {"type": "string"},
                    "description": {"type": "string"},
                    "url": {"type": "string"},
                    "evidence_anchor": {
                        "type": "string",
                        "enum": list(EVIDENCE_ANCHOR_VALUES),
                    },
                },
            },
        },
        "online_links": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["label", "url", "evidence_anchor"],
                "properties": {
                    "label": {"type": "string"},
                    "url": {"type": "string"},
                    "evidence_anchor": {
                        "type": "string",
                        "enum": list(EVIDENCE_ANCHOR_VALUES),
                    },
                },
            },
        },
        "linkedin_present": {"type": "boolean"},
        "github_present": {"type": "boolean"},
    },
}


# --- Headlines ---------------------------------------------------------


HEADLINES_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["variants"],
    "properties": {
        "variants": {
            "type": "array",
            "minItems": 3,
            "maxItems": 6,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "text",
                    "audience",
                    "char_count",
                    "evidence_anchors",
                    "focus",
                ],
                "properties": {
                    "text": {"type": "string"},
                    "audience": {
                        "type": "string",
                        "enum": list(AUDIENCE_VALUES),
                    },
                    "char_count": {"type": "integer", "minimum": 0, "maximum": 220},
                    "evidence_anchors": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "focus": {"type": "string"},
                },
            },
        },
    },
}


# --- About -------------------------------------------------------------


ABOUT_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "short_version",
        "medium_version",
        "long_version",
        "technical_version",
        "recruiter_version",
        "char_counts",
    ],
    "properties": {
        "short_version": {"type": "string"},
        "medium_version": {"type": "string"},
        "long_version": {"type": "string"},
        "technical_version": {"type": "string"},
        "recruiter_version": {"type": "string"},
        "char_counts": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "short_version",
                "medium_version",
                "long_version",
                "technical_version",
                "recruiter_version",
            ],
            "properties": {
                "short_version": {"type": "integer", "minimum": 0},
                "medium_version": {"type": "integer", "minimum": 0},
                "long_version": {"type": "integer", "minimum": 0},
                "technical_version": {"type": "integer", "minimum": 0},
                "recruiter_version": {"type": "integer", "minimum": 0},
            },
        },
    },
}


# --- Experience rewrite ------------------------------------------------


EXPERIENCE_REWRITE_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["roles"],
    "properties": {
        "roles": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "role",
                    "company",
                    "period",
                    "linkedin_description",
                    "bullets",
                    "suggested_skills",
                    "highlight",
                    "do_not_claim",
                    "evidence_anchors",
                ],
                "properties": {
                    "role": {"type": "string"},
                    "company": {"type": "string"},
                    "period": {"type": "string"},
                    "linkedin_description": {"type": "string"},
                    "bullets": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 6,
                        "items": {"type": "string"},
                    },
                    "suggested_skills": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["name", "evidence_anchor"],
                            "properties": {
                                "name": {"type": "string"},
                                "evidence_anchor": {
                                    "type": "string",
                                    "enum": list(EVIDENCE_ANCHOR_VALUES),
                                },
                            },
                        },
                    },
                    "highlight": {
                        "type": "array",
                        "maxItems": 4,
                        "items": {"type": "string"},
                    },
                    "do_not_claim": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "evidence_anchors": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
    },
}


# --- Education rewrite -------------------------------------------------


EDUCATION_REWRITE_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["entries"],
    "properties": {
        "entries": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "institution",
                    "degree",
                    "period",
                    "linkedin_description",
                    "relevant_coursework",
                    "connection_to_target",
                    "evidence_anchors",
                ],
                "properties": {
                    "institution": {"type": "string"},
                    "degree": {"type": "string"},
                    "period": {"type": "string"},
                    "linkedin_description": {"type": "string"},
                    "relevant_coursework": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "connection_to_target": {"type": "string"},
                    "evidence_anchors": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
    },
}


# --- Certifications ----------------------------------------------------


CERTIFICATIONS_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["existing", "recommended"],
    "properties": {
        "existing": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "name",
                    "issuer",
                    "year",
                    "linkedin_description",
                    "priority",
                    "target_role_links",
                    "evidence_anchor",
                ],
                "properties": {
                    "name": {"type": "string"},
                    "issuer": {"type": "string"},
                    "year": {"type": "string"},
                    "linkedin_description": {"type": "string"},
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                    "target_role_links": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "evidence_anchor": {
                        "type": "string",
                        "enum": list(EVIDENCE_ANCHOR_VALUES),
                    },
                },
            },
        },
        "recommended": {
            "type": "array",
            "maxItems": 5,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "issuer", "why_it_matters"],
                "properties": {
                    "name": {"type": "string"},
                    "issuer": {"type": "string"},
                    "why_it_matters": {"type": "string"},
                },
            },
        },
    },
}


# --- Skills ------------------------------------------------------------


_SKILL_ITEM = {
    "type": "object",
    "additionalProperties": False,
    "required": ["name", "category", "evidence_anchor", "evidence_quote", "reason"],
    "properties": {
        "name": {"type": "string"},
        "category": {
            "type": "string",
            "enum": ["core", "tooling", "soft", "domain", "language"],
        },
        "evidence_anchor": {
            "type": "string",
            "enum": list(EVIDENCE_ANCHOR_VALUES),
        },
        "evidence_quote": {"type": "string"},
        "reason": {"type": "string"},
    },
}


SKILLS_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["core", "to_verify", "to_learn", "do_not_claim"],
    "properties": {
        "core": {"type": "array", "items": _SKILL_ITEM},
        "to_verify": {"type": "array", "items": _SKILL_ITEM},
        "to_learn": {"type": "array", "items": _SKILL_ITEM},
        "do_not_claim": {"type": "array", "items": _SKILL_ITEM},
    },
}


# --- Featured ----------------------------------------------------------


FEATURED_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "minItems": 0,
            "maxItems": 10,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "kind",
                    "title",
                    "description",
                    "link",
                    "todo",
                    "evidence_anchor",
                ],
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": [
                            "github_project",
                            "portfolio_site",
                            "article",
                            "linkedin_post",
                            "certificate",
                            "app",
                            "video_demo",
                            "pdf_case_study",
                        ],
                    },
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "link": {"type": "string"},
                    "todo": {"type": "string"},
                    "evidence_anchor": {
                        "type": "string",
                        "enum": list(EVIDENCE_ANCHOR_VALUES),
                    },
                },
            },
        },
    },
}


# --- Projects ----------------------------------------------------------


PROJECTS_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["projects"],
    "properties": {
        "projects": {
            "type": "array",
            "maxItems": 6,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "title",
                    "description",
                    "technologies",
                    "candidate_role",
                    "period",
                    "link",
                    "suggested_skills",
                    "evidence_anchors",
                ],
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "technologies": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "candidate_role": {"type": "string"},
                    "period": {"type": "string"},
                    "link": {"type": "string"},
                    "suggested_skills": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "evidence_anchors": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
    },
}


# --- Services ----------------------------------------------------------


SERVICES_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["services", "skip_reason"],
    "properties": {
        "services": {
            "type": "array",
            "maxItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "name",
                    "short_description",
                    "why_credible",
                    "evidence_anchor",
                ],
                "properties": {
                    "name": {"type": "string"},
                    "short_description": {"type": "string"},
                    "why_credible": {"type": "string"},
                    "evidence_anchor": {
                        "type": "string",
                        "enum": list(EVIDENCE_ANCHOR_VALUES),
                    },
                },
            },
        },
        "skip_reason": {"type": "string"},
    },
}


# --- Courses -----------------------------------------------------------


COURSES_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["existing", "recommended"],
    "properties": {
        "existing": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "provider", "year", "evidence_anchor"],
                "properties": {
                    "title": {"type": "string"},
                    "provider": {"type": "string"},
                    "year": {"type": "string"},
                    "evidence_anchor": {
                        "type": "string",
                        "enum": list(EVIDENCE_ANCHOR_VALUES),
                    },
                },
            },
        },
        "recommended": {
            "type": "array",
            "maxItems": 6,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "title",
                    "provider",
                    "why_it_matters",
                    "estimated_hours",
                ],
                "properties": {
                    "title": {"type": "string"},
                    "provider": {"type": "string"},
                    "why_it_matters": {"type": "string"},
                    "estimated_hours": {"type": "integer", "minimum": 0},
                },
            },
        },
    },
}


# --- Recommendations ---------------------------------------------------


RECOMMENDATIONS_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["templates"],
    "properties": {
        "templates": {
            "type": "array",
            "minItems": 1,
            "maxItems": 6,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "recipient_type",
                    "suggested_recipient_label",
                    "message",
                    "follow_up",
                ],
                "properties": {
                    "recipient_type": {
                        "type": "string",
                        "enum": [
                            "manager",
                            "peer",
                            "direct_report",
                            "client",
                            "mentor",
                        ],
                    },
                    "suggested_recipient_label": {"type": "string"},
                    "message": {"type": "string"},
                    "follow_up": {"type": "string"},
                },
            },
        },
    },
}


# --- Posts -------------------------------------------------------------


POSTS_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["posts"],
    "properties": {
        "posts": {
            "type": "array",
            "minItems": 1,
            "maxItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "kind",
                    "title",
                    "body",
                    "char_count",
                    "hashtags",
                    "evidence_anchors",
                    "audience",
                    "parent_post_topic",
                ],
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": list(POST_KIND_VALUES),
                    },
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "char_count": {"type": "integer", "minimum": 0},
                    "hashtags": {
                        "type": "array",
                        "maxItems": 5,
                        "items": {"type": "string"},
                    },
                    "evidence_anchors": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "audience": {
                        "type": "string",
                        "enum": list(AUDIENCE_VALUES),
                    },
                    "parent_post_topic": {"type": "string"},
                },
            },
        },
    },
}


# --- Followup questions -----------------------------------------------


CLARIFY_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["questions"],
    "properties": {
        "questions": {
            "type": "array",
            "minItems": 0,
            "maxItems": 12,
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
                    "topic": {"type": "string"},
                    "question": {"type": "string"},
                    "rationale": {"type": "string"},
                    "options": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 6,
                        "items": {"type": "string"},
                    },
                    "multi_select": {"type": "boolean"},
                    "allow_free_text": {"type": "boolean"},
                },
            },
        },
    },
}
