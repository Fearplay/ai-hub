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
to return ONE JSON object matching the bug-report schema exactly. The
object contains a ``scenarios`` array: use one scenario for one bug, or
several scenarios when the inputs clearly describe multiple distinct
failures.

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

3. DETECT ONE OR MORE SCENARIOS. Do not force unrelated failures into
   one ticket. Split into multiple ``scenarios`` when the user describes
   different flows, different affected pages, different errors, or
   different expected/actual outcomes. Keep one scenario when all inputs
   describe the same underlying bug from different angles. Every scenario
   must have ``title``, ``summary``, ``severity``, ``priority``,
   ``reproducibility``, at least 1 step, ``expected_result`` and
   ``actual_result`` non-empty. If the inputs are truly minimal, use a
   generic but plausible reconstruction and call it out in
   "additional_notes".

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


FOLLOWUP_QUESTIONS_SYSTEM = (
    BUG_REPORT_RULES
    + "\n\nTASK: Read the user's free-form description, optional "
    "environment hints, attached screenshots and supporting documents. "
    "Then surface CLARIFYING QUESTIONS the user should answer BEFORE "
    "we generate the structured bug report. Rules:\n\n"
    "* Ask only about facts you would otherwise have to INVENT to fill "
    "the schema. The schema requires title, summary, severity, "
    "priority, reproducibility, environment (browser/os/device/"
    "app_version/url), preconditions, steps, expected vs actual, "
    "attachments_summary, additional_notes.\n"
    "* Do NOT ask about things that are obviously visible in the "
    "screenshots or already in the description. The user typed those "
    "for a reason - asking again is annoying.\n"
    "* Examples of GOOD questions:\n"
    "    - 'How often does this happen?' when the description does not "
    "mention frequency -> options ['Always', 'Sometimes', 'Once'], "
    "multi_select=false, allow_free_text=false\n"
    "    - 'Which browser / version?' when the screenshots do not show "
    "a browser chrome -> options ['Chrome', 'Firefox', 'Edge', "
    "'Safari'], multi_select=false, allow_free_text=true\n"
    "    - 'Does it block your work or is there a workaround?' when "
    "the user did not state impact -> options ['Blocks me', "
    "'Workaround exists', 'Cosmetic'], multi_select=false, "
    "allow_free_text=true\n"
    "    - 'Which user role hits this?' when role might matter -> "
    "options ['Admin', 'Standard user', 'Guest', 'All'], "
    "multi_select=true, allow_free_text=true\n"
    "* Output 0-8 questions total. Zero is fine - it means the inputs "
    "are already enough. Do NOT ask filler questions just to hit a "
    "quota.\n"
    "* Each question must be a direct yes/no or 1-2 sentence question "
    "to the user ('you' / 'vy'), with a short rationale tied to the "
    "schema field it would feed.\n"
    "* Topics must be short labels (1-3 words). No duplicate topics in "
    "the same response.\n\n"
    "ANSWER OPTIONS (every question must include them):\n"
    "* Always provide 2-6 short answer options the user can click on. "
    "Keep each option short - ideally 1-4 words, never a full "
    "sentence.\n"
    "* Set multi_select=true ONLY when several options can apply at "
    "once. Otherwise multi_select=false.\n"
    "* Set allow_free_text=true unless the options clearly enumerate "
    "every possible answer.\n\n"
    "LANGUAGE (HARD REQUIREMENT):\n"
    "* OUTPUT_LANGUAGE applies to topic, question, rationale AND every "
    "option. Never mix English options into a Czech question."
)


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


def build_followup_user(
    *,
    description: str,
    environment_hint: str,
    documents: list[dict],
    image_count: int,
    output_lang: str,
) -> str:
    """Compose the user message for the follow-up-questions call.

    Same inputs as the main bug-report call so the model sees exactly
    what the user submitted; the system prompt steers it toward asking
    only about gaps rather than producing the full report.
    """
    description = (description or "").strip()
    environment_hint = (environment_hint or "").strip()
    docs_block = _render_documents(documents)

    parts: list[str] = [
        f"OUTPUT_LANGUAGE: {output_lang}",
        "",
        "TASK: Read the inputs and decide what clarifying questions you "
        "would ask BEFORE filing the structured bug report. Return JSON "
        "matching the follow-up-questions schema. Empty array is "
        "acceptable when the inputs are already enough.",
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
    parts.extend(["", "Return only the questions JSON."])
    return "\n".join(parts)


def _format_followup_qa(qa_pairs: list[dict]) -> str:
    """Render answered follow-up questions for the bug-report prompt."""
    if not qa_pairs:
        return ""
    lines: list[str] = ["=== ADDITIONAL CLARIFICATIONS FROM USER ==="]
    for pair in qa_pairs:
        topic = (pair.get("topic") or "").strip() or "-"
        question = (pair.get("question") or "").strip()
        answer = (pair.get("answer") or "").strip()
        if not answer:
            continue
        lines.append(f"- Topic: {topic}")
        if question:
            lines.append(f"  Q: {question}")
        lines.append(f"  A: {answer}")
    if len(lines) == 1:
        return ""
    lines.append(
        "\nUse these clarifications as TRUTH when filling the report. "
        "Do not contradict them. Do not add facts beyond what the user "
        "stated above."
    )
    return "\n".join(lines)


def build_bug_report_user(
    *,
    description: str,
    environment_hint: str,
    documents: list[dict],
    image_count: int,
    output_lang: str,
    followup_qa: list[dict] | None = None,
) -> str:
    """Compose the user message string sent to the AI.

    ``image_count`` is the number of screenshots passed alongside via
    ``ai_provider.run(images=...)``. We mention it explicitly so the
    model knows how many ``Screenshot N:`` lines belong in
    ``attachments_summary`` and can match them by index. ``followup_qa``
    carries the answers to the optional clarifying-questions step so
    the model can treat them as ground truth.
    """
    description = (description or "").strip()
    environment_hint = (environment_hint or "").strip()
    docs_block = _render_documents(documents)

    parts: list[str] = [
        f"OUTPUT_LANGUAGE: {output_lang}",
        "",
        "TASK: Produce one JSON object matching the bug-report schema. "
        "Use the description + screenshots + supporting documents below. "
        "The object must contain a scenarios[] array. Put exactly one "
        "scenario there when all inputs describe one bug; split into "
        "multiple scenarios when the inputs describe separate failures. "
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
    extras = _format_followup_qa(followup_qa or [])
    if extras:
        parts.extend(["", extras])
    return "\n".join(parts)
