"""JSON schemas for the AI Doc Assistant structured outputs.

OpenAI's strict JSON-schema mode rejects extra fields, so each schema
declares ``additionalProperties: false`` and lists every required key.
The pipeline picks the schema that matches the chosen action.
"""

from __future__ import annotations


SUMMARY_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["tldr", "key_points", "action_items"],
    "properties": {
        "tldr": {
            "type": "string",
            "description": "1-3 sentences in OUTPUT_LANGUAGE summarising the document.",
        },
        "key_points": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Up to 8 bullet points with the most important facts.",
        },
        "action_items": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Concrete tasks the document asks for or implies. Empty array "
                "if the document does not call for any action."
            ),
        },
    },
}


QA_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answer", "evidence", "confidence"],
    "properties": {
        "answer": {
            "type": "string",
            "description": (
                "The answer in OUTPUT_LANGUAGE. If the document does not "
                "contain the information, write \"unknown\" / \"neuvedeno\" "
                "and set confidence to \"low\"."
            ),
        },
        "evidence": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Verbatim quotes from the document that support the answer.",
        },
        "confidence": {
            "type": "string",
            "enum": ["low", "medium", "high"],
        },
    },
}


REWRITE_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["rewritten", "changes"],
    "properties": {
        "rewritten": {
            "type": "string",
            "description": "The rewritten passage in OUTPUT_LANGUAGE.",
        },
        "changes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Short notes about what was changed and why.",
        },
    },
}


EXTRACT_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["facts"],
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["label", "value", "evidence"],
                "properties": {
                    "label": {
                        "type": "string",
                        "description": "Short label, e.g. \"Deadline\", \"Total amount\".",
                    },
                    "value": {
                        "type": "string",
                        "description": "Verbatim value from the document.",
                    },
                    "evidence": {
                        "type": "string",
                        "description": "Surrounding sentence or short context.",
                    },
                },
            },
        },
    },
}


SCHEMA_BY_ACTION: dict = {
    "summary": SUMMARY_SCHEMA,
    "qa": QA_SCHEMA,
    "rewrite": REWRITE_SCHEMA,
    "extract": EXTRACT_SCHEMA,
}
