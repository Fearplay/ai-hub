"""JSON schema for the AI Bug Report structured output.

OpenAI's strict JSON-schema mode rejects extra fields and requires every
property to be listed in ``required``, so the schema below uses
``additionalProperties: false`` and an exhaustive ``required`` list. The
``environment`` sub-object is also strict so the model cannot smuggle in
fields the DOCX writer doesn't know how to render.

The values for ``severity``, ``priority``, and ``reproducibility`` are
fixed enums - the AI must pick one of the listed values, never invent
a new one. ``Unknown`` is allowed for reproducibility so the model has
an honest "I could not tell" answer instead of inventing "Always".

Optional fields (``environment`` keys, ``preconditions``, ``additional_notes``)
default to empty strings / empty arrays when the AI has nothing
concrete to fill them with - the no-hallucination clause forbids
making up versions / URLs / preconditions.
"""

from __future__ import annotations


SEVERITY_ENUM = ["Critical", "High", "Medium", "Low"]
PRIORITY_ENUM = ["P0", "P1", "P2", "P3"]
REPRODUCIBILITY_ENUM = ["Always", "Sometimes", "Rare", "Once", "Unknown"]


FOLLOWUP_QUESTIONS_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["questions"],
    "properties": {
        "questions": {
            "type": "array",
            "minItems": 0,
            "maxItems": 8,
            "description": (
                "0-8 clarifying questions about the bug that the user's "
                "description / screenshots / logs do not clearly answer. "
                "Empty array when the inputs are already enough to file "
                "a confident bug report."
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
                        "description": (
                            "Short label - 1-3 words, e.g. 'Browser', "
                            "'Reproducibility', 'Network'."
                        ),
                    },
                    "question": {
                        "type": "string",
                        "description": (
                            "Direct question to the user (you / vy). "
                            "Answerable in 1-2 sentences. Asked because "
                            "the inputs do not let the AI answer it "
                            "without inventing facts."
                        ),
                    },
                    "rationale": {
                        "type": "string",
                        "description": (
                            "One short sentence: why we are asking and "
                            "which schema field it would feed."
                        ),
                    },
                    "options": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 6,
                        "items": {"type": "string"},
                        "description": (
                            "2-6 short, plausible answer options the user "
                            "can pick from. Examples for 'Does it happen "
                            "every time?': ['Always', 'Sometimes', 'Once']. "
                            "Make options mutually exclusive when "
                            "multi_select=false; multi_select=true means "
                            "several can apply. Always written in "
                            "OUTPUT_LANGUAGE."
                        ),
                    },
                    "multi_select": {
                        "type": "boolean",
                        "description": (
                            "True when several options can apply at once "
                            "(e.g. 'Which network layers showed errors?'). "
                            "False for single-choice questions."
                        ),
                    },
                    "allow_free_text": {
                        "type": "boolean",
                        "description": (
                            "True when the user may add an 'Other' answer "
                            "with their own short text. Default to true "
                            "unless the options clearly enumerate every "
                            "possible answer."
                        ),
                    },
                },
            },
        },
    },
}


BUG_SCENARIO_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "title",
        "summary",
        "severity",
        "priority",
        "reproducibility",
        "environment",
        "preconditions",
        "steps_to_reproduce",
        "expected_result",
        "actual_result",
        "additional_notes",
    ],
    "properties": {
        "title": {
            "type": "string",
            "description": (
                "Concise 6-12 word title in OUTPUT_LANGUAGE. Starts with the "
                "affected area, then describes the failure (e.g. "
                "'Profile Save button stays in loading state on Chrome 124')."
            ),
        },
        "summary": {
            "type": "string",
            "description": (
                "1-3 sentences in OUTPUT_LANGUAGE summarising what is broken "
                "and the user impact."
            ),
        },
        "severity": {
            "type": "string",
            "enum": SEVERITY_ENUM,
            "description": (
                "Critical = data loss / outage; High = blocks a primary flow; "
                "Medium = degraded but workaround exists; Low = cosmetic."
            ),
        },
        "priority": {
            "type": "string",
            "enum": PRIORITY_ENUM,
            "description": (
                "P0 = fix immediately; P1 = next release; P2 = backlog soon; "
                "P3 = nice to have."
            ),
        },
        "reproducibility": {
            "type": "string",
            "enum": REPRODUCIBILITY_ENUM,
            "description": (
                "Always / Sometimes / Rare / Once / Unknown. Use Unknown when "
                "the inputs don't say."
            ),
        },
        "environment": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "browser",
                "os",
                "device",
                "app_version",
                "url",
            ],
            "properties": {
                "browser": {
                    "type": "string",
                    "description": (
                        "Browser + version when known (e.g. 'Chrome 124.0'). "
                        "Empty string when not mentioned anywhere."
                    ),
                },
                "os": {
                    "type": "string",
                    "description": "OS + version. Empty string when unknown.",
                },
                "device": {
                    "type": "string",
                    "description": (
                        "Device type ('Desktop', 'iPhone 14 Pro', 'Galaxy "
                        "S22'). Empty string when unknown."
                    ),
                },
                "app_version": {
                    "type": "string",
                    "description": (
                        "App / build version when visible in the inputs. "
                        "Empty string when unknown."
                    ),
                },
                "url": {
                    "type": "string",
                    "description": (
                        "Affected URL or in-app route. Empty string when "
                        "unknown."
                    ),
                },
            },
        },
        "preconditions": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Each entry is one precondition that must hold before the "
                "steps are executed (logged-in user, specific role, prepared "
                "data, ...). Empty array when none."
            ),
        },
        "steps_to_reproduce": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Numbered steps in OUTPUT_LANGUAGE. Each entry is one "
                "imperative action ('Open https://...', 'Click Save'). "
                "Always at least 1 step - infer the most likely flow from "
                "the description / screenshots if the user did not list them."
            ),
        },
        "expected_result": {
            "type": "string",
            "description": (
                "What should happen after the last step, in OUTPUT_LANGUAGE. "
                "Always non-empty - infer the reasonable expected behaviour "
                "from the UI in the screenshots if the user did not say."
            ),
        },
        "actual_result": {
            "type": "string",
            "description": (
                "What actually happens, in OUTPUT_LANGUAGE. Always non-empty "
                "- describe what is visible in the attached screenshots / log."
            ),
        },
        "additional_notes": {
            "type": "string",
            "description": (
                "Optional 1-3 sentences with anything else worth flagging "
                "(likely root cause guess marked as inferred, related "
                "tickets the user mentioned, workarounds). Empty string "
                "when nothing to add."
            ),
        },
    },
}


BUG_REPORT_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "title",
        "summary",
        "scenarios",
        "attachments_summary",
        "additional_notes",
    ],
    "properties": {
        "title": {
            "type": "string",
            "description": (
                "Concise 6-12 word title for the whole report in "
                "OUTPUT_LANGUAGE. If there is one scenario, this may match "
                "that scenario title. If there are several, summarise the "
                "affected feature or theme."
            ),
        },
        "summary": {
            "type": "string",
            "description": (
                "1-3 sentences in OUTPUT_LANGUAGE summarising all detected "
                "bug scenarios and the overall user impact."
            ),
        },
        "scenarios": {
            "type": "array",
            "minItems": 1,
            "maxItems": 8,
            "description": (
                "One entry per distinct bug scenario found in the user's "
                "description, screenshots, logs, or documents. Use one "
                "scenario when everything describes the same bug. Split into "
                "multiple scenarios when the inputs clearly describe separate "
                "failures, separate flows, or separate expected/actual outcomes."
            ),
            "items": BUG_SCENARIO_SCHEMA,
        },
        "attachments_summary": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "One line per attached image or document, describing what "
                "it shows ('Screenshot 1: profile page with Save button in "
                "spinner state'). Empty array when no attachments. Use the "
                "same order as the user provided them."
            ),
        },
        "additional_notes": {
            "type": "string",
            "description": (
                "Optional 1-3 sentences with report-level notes that apply "
                "across scenarios. Mark inferred non-trivial details with "
                "the word '(inferred)'. Empty string when nothing to add."
            ),
        },
    },
}
