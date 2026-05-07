"""Orchestration for the AI Doc Assistant pipeline.

One public function per action. Each one short-circuits in demo mode
(per ``ai-section.mdc``) and otherwise calls
``src.services.ai_provider.run`` with the matching schema.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.services import ai_provider
from src.sections.ai_doc_assistant import prompts, schema
from src.sections.ai_doc_assistant.state import (
    ACTION_EXTRACT,
    ACTION_QA,
    ACTION_REWRITE,
    ACTION_SUMMARY,
    STATE,
)


@dataclass
class StepResult:
    ok: bool
    error: str = ""


_DEMO_RESULTS: dict[str, dict] = {
    ACTION_SUMMARY: {
        "tldr": (
            "The document is a 2026 GDPR-friendly automation engineer job ad "
            "for Kosik.cz. It hires for the AI/ML team, primarily building "
            "agentic n8n workflows on Azure AKS."
        ),
        "key_points": [
            "Role: Automation Engineer in the AI/ML team at Kosik.cz.",
            "Stack: n8n on AKS + Microsoft / Azure ecosystem.",
            "Main goal: scale a reusable AI automation layer for the company.",
            "Required Czech (excellent), English (B2).",
            "Office at metro Dejvicka, Prague.",
        ],
        "action_items": [
            "Reply through Jobs.cz with CV.",
            "Highlight automation, n8n, or Azure experience in cover letter.",
        ],
    },
    ACTION_QA: {
        "answer": "The role requires excellent Czech and B2 English.",
        "evidence": [
            "Cestina (Vyborna), Anglictina (Stredne pokrocila)",
        ],
        "confidence": "high",
    },
    ACTION_REWRITE: {
        "rewritten": (
            "We are looking for an Automation Engineer to join our AI/ML team. "
            "You will design agentic workflows in n8n on Azure AKS and ship "
            "reusable building blocks that let the rest of Kosik automate "
            "without queuing tickets."
        ),
        "changes": [
            "Replaced marketing buzzwords with a plain description of the work.",
            "Tightened the sentence structure for a more direct tone.",
        ],
    },
    ACTION_EXTRACT: {
        "facts": [
            {
                "label": "Position",
                "value": "Automation Engineer",
                "evidence": "Job title at the top of the posting.",
            },
            {
                "label": "Employer",
                "value": "Kosik.cz s.r.o.",
                "evidence": "Listed as the company on the job ad.",
            },
            {
                "label": "Location",
                "value": "Evropska 2758/11, Praha - Dejvice",
                "evidence": "Office address in the company info block.",
            },
            {
                "label": "Languages required",
                "value": "Czech (excellent), English (B2)",
                "evidence": "Cestina (Vyborna), Anglictina (Stredne pokrocila)",
            },
        ],
    },
}


def load_demo() -> None:
    STATE.last_result = dict(_DEMO_RESULTS[STATE.action])
    STATE.last_action = STATE.action
    STATE.last_error = ""
    STATE.activity = "ready"


def run_action(*, output_lang: str) -> StepResult:
    """Dispatch the active action to the provider with the matching schema."""
    if STATE.demo_mode:
        load_demo()
        return StepResult(ok=True)

    if STATE.document is None or not STATE.document.text:
        return StepResult(ok=False, error="No document loaded.")

    action = STATE.action
    doc_text = STATE.document.text
    doc_name = STATE.document.name

    user: str
    schema_dict: dict
    schema_name: str

    if action == ACTION_SUMMARY:
        user = prompts.build_summary_user(
            doc_name=doc_name, doc_text=doc_text, output_lang=output_lang
        )
        schema_dict = schema.SUMMARY_SCHEMA
        schema_name = "doc_summary"
    elif action == ACTION_QA:
        if not STATE.qa_question.strip():
            return StepResult(ok=False, error="Type a question first.")
        user = prompts.build_qa_user(
            doc_name=doc_name,
            doc_text=doc_text,
            question=STATE.qa_question,
            output_lang=output_lang,
        )
        schema_dict = schema.QA_SCHEMA
        schema_name = "doc_qa"
    elif action == ACTION_REWRITE:
        if not STATE.rewrite_passage.strip():
            return StepResult(ok=False, error="Paste a passage to rewrite.")
        user = prompts.build_rewrite_user(
            doc_name=doc_name,
            doc_text=doc_text,
            passage=STATE.rewrite_passage,
            tone=STATE.rewrite_tone or "neutral",
            output_lang=output_lang,
        )
        schema_dict = schema.REWRITE_SCHEMA
        schema_name = "doc_rewrite"
    elif action == ACTION_EXTRACT:
        user = prompts.build_extract_user(
            doc_name=doc_name, doc_text=doc_text, output_lang=output_lang
        )
        schema_dict = schema.EXTRACT_SCHEMA
        schema_name = "doc_extract"
    else:
        return StepResult(ok=False, error=f"Unknown action: {action!r}")

    try:
        result = ai_provider.run(
            system=prompts.SYSTEM_PROMPT,
            user=user,
            schema=schema_dict,
            schema_name=schema_name,
            max_output_tokens=2000,
            temperature=0.2,
        )
    except ai_provider.ProviderError as exc:
        STATE.last_error = str(exc)
        STATE.activity = "error"
        return StepResult(ok=False, error=str(exc))
    except Exception as exc:
        STATE.last_error = str(exc)
        STATE.activity = "error"
        return StepResult(ok=False, error=f"Run failed: {exc}")

    if not isinstance(result.data, dict):
        STATE.last_error = "AI did not return a structured payload."
        STATE.activity = "error"
        return StepResult(ok=False, error=STATE.last_error)

    STATE.last_result = result.data
    STATE.last_action = action
    STATE.last_error = ""
    STATE.activity = "ready"
    return StepResult(ok=True)


__all__ = ["StepResult", "load_demo", "run_action"]
