"""Prompts for the AI Bug Report pipeline.

The system prompt re-states the global no-hallucination clause for the
QA domain (the ``ai_provider`` already prepends the canonical version,
but per ``ai-section.mdc`` every section also encodes its own domain
rules in ``prompts.py``). The user-message builder serialises the
description, environment hints, and any attached document text into a
single prompt; image attachments are sent as vision content blocks via
``ai_provider.run(..., images=...)``.

Large attached documents are truncated to keep cost predictable.
"""

from __future__ import annotations

from typing import Iterable


MAX_DOC_CHARS = 40_000


BUG_REPORT_RULES = """\
You are a senior QA engineer who turns rough user reports into clean,
actionable bug tickets. You receive a free-form description, optional
environment hints, an optional list of supporting documents (logs,
specs, JSON), and zero or more screenshots (vision input). Your job is
to return ONE JSON object matching the bug-report schema exactly.

Follow these rules strictly:

1. NO HALLUCINATION OF VERIFIABLE FACTS. Do not invent stack traces,
   ticket IDs, user names, e-mail addresses, exact version numbers,
   timestamps, or quotes from logs that are not present in the inputs.
   If a verifiable fact is missing, leave the matching environment
   field as an empty string.

2. INFER WHEN HELPFUL, MARK INFERENCES. The user often forgets to
   write the obvious. You SHOULD infer:
   - a concise title from the inputs (even when none was provided),
   - the steps to reproduce from a description / a single screenshot,
   - the expected vs actual result from what the UI in the screenshot
     looks like vs what the user complains about,
   - severity / priority / reproducibility from impact + frequency
     wording.
   When you infer a non-trivial detail, mention it in
   "additional_notes" with the word "(inferred)" so the reader knows
   to verify. Never invent verifiable facts (rule 1 wins).

3. ALWAYS PRODUCE A COMPLETE REPORT. ``title``, ``summary``,
   ``severity``, ``priority``, ``reproducibility``, at least 1 step,
   ``expected_result`` and ``actual_result`` must always be non-empty.
   If the inputs are truly minimal, use a generic but plausible
   reconstruction and call it out in "additional_notes".

4. SEVERITY GUIDE.
   - Critical = data loss, security, total outage, blocked release.
   - High     = blocks a primary user flow, no workaround.
   - Medium   = degraded behaviour, workaround exists.
   - Low      = cosmetic, typo, minor friction.

5. STEPS = IMPERATIVE, ONE ACTION PER LINE. "Open <url>", "Click
   Save", "Wait 3 seconds", "Observe the spinner". Never combine two
   actions in one step. Never include preamble like "First, ...".

6. ONE OUTPUT LANGUAGE. Every human-readable string is in
   OUTPUT_LANGUAGE. Technology names, product names, file paths, and
   code identifiers stay in their original form. Never mix CZ and EN
   inside a single field.

7. ATTACHMENTS SUMMARY. Produce one short line per attachment in the
   order they were provided. Use "Screenshot N:" prefix for images and
   "Document N:" for text-like attachments so the reader can match the
   summary back to the file list.

8. NO FILLER. Skip "Of course!", "Here is the bug report:", etc. Return
   the JSON object directly - no prose, no markdown fences.
"""


SYSTEM_PROMPT = BUG_REPORT_RULES


def _truncate(text: str, max_chars: int = MAX_DOC_CHARS) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    head = text[: max_chars - 200]
    return head + "\n\n[... attachment truncated to fit context window ...]"


def _render_documents(documents: Iterable[dict]) -> str:
    """Serialise text-like attachments into one prompt block.

    ``documents`` is an iterable of ``{"name", "ext", "text"}`` dicts
    (the call site converts ``DocAttachment`` objects). Each document
    is wrapped in begin/end markers so the model can address them
    individually in ``attachments_summary``.
    """
    blocks: list[str] = []
    for idx, doc in enumerate(documents, start=1):
        name = doc.get("name") or f"document_{idx}"
        ext = doc.get("ext") or "txt"
        text = _truncate(doc.get("text") or "")
        if not text.strip():
            continue
        blocks.append(
            f"--- DOCUMENT {idx} START (name: {name}, type: .{ext}) ---\n"
            f"{text}\n"
            f"--- DOCUMENT {idx} END ---"
        )
    if not blocks:
        return ""
    return "\n\n".join(blocks)


def build_bug_report_user(
    *,
    description: str,
    environment_hint: str,
    documents: list[dict],
    image_count: int,
    output_lang: str,
) -> str:
    """Compose the user message string sent to the AI.

    ``image_count`` is the number of screenshots passed alongside via
    ``ai_provider.run(images=...)``. We mention it explicitly so the
    model knows how many ``Screenshot N:`` lines belong in
    ``attachments_summary`` and can match them by index.
    """
    description = (description or "").strip()
    environment_hint = (environment_hint or "").strip()
    docs_block = _render_documents(documents)

    parts: list[str] = [
        f"OUTPUT_LANGUAGE: {output_lang}",
        "",
        "TASK: Produce one JSON object matching the bug-report schema. "
        "Use the description + screenshots + supporting documents below. "
        "Infer reasonable values for any missing field and mark "
        "inferences in additional_notes. Never invent verifiable facts.",
        "",
        f"NUMBER OF ATTACHED SCREENSHOTS: {int(image_count)}",
    ]
    if environment_hint:
        parts.extend(
            [
                "",
                "ENVIRONMENT HINTS (user-supplied, may be incomplete):",
                environment_hint,
            ]
        )
    parts.extend(
        [
            "",
            "--- USER DESCRIPTION START ---",
            description or "(no description was typed; rely on screenshots / documents)",
            "--- USER DESCRIPTION END ---",
        ]
    )
    if docs_block:
        parts.extend(["", docs_block])
    return "\n".join(parts)
