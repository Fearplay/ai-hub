"""Prompts for the AI Doc Assistant pipeline.

The system prompt re-states the global no-hallucination clause (the
``ai_provider`` already prepends the canonical version, but per
``ai-section.mdc`` every section also encodes its own domain rules in
``prompts.py``). Each user-message builder takes the structured inputs
the section already has and renders them as a single string.

Big documents are truncated to keep cost predictable. ``MAX_DOC_CHARS``
is roughly 80 k characters - long enough for a 50-page report, short
enough to stay well inside the 128 k token window of GPT-4o-mini /
Claude Haiku.
"""

from __future__ import annotations


MAX_DOC_CHARS = 80_000


DOC_ASSISTANT_RULES = """\
You are a precise document assistant. The user uploads ONE document and
asks one of four things: summarise, answer a question, rewrite a
passage, or extract facts. Follow these rules:

1. NO HALLUCINATION. Use only the document text the user provided. Never
   invent names, dates, numbers, quotes, or facts. If the document does
   not contain the answer, write "unknown" / "neuvedeno" and lower the
   confidence.

2. EVIDENCE FIRST. For every factual claim include a short verbatim
   quote from the document (or note "not in document"). The schema has
   an "evidence" field for this - fill it.

3. NO EXTERNAL CONTEXT. Do not pull facts from your training data. The
   user only wants what is in the document.

4. ONE OUTPUT LANGUAGE. Every human-readable string is in
   OUTPUT_LANGUAGE. Code, technology names, and proper nouns are
   exempt. Never mix CZ and EN within a section.

5. NO PADDING. Skip filler phrases like "Of course!", "Here is a
   summary:". Go straight to the structured payload.

6. RESPECT THE SCHEMA. Return one JSON object that matches the schema
   exactly. Never include extra fields, never wrap the answer in
   ```json fences.
"""


SYSTEM_PROMPT = DOC_ASSISTANT_RULES


def _truncate(text: str, max_chars: int = MAX_DOC_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    head = text[: max_chars - 200]
    return head + "\n\n[... document truncated to fit context window ...]"


def build_summary_user(*, doc_name: str, doc_text: str, output_lang: str) -> str:
    return (
        f"OUTPUT_LANGUAGE: {output_lang}\n"
        f"DOCUMENT NAME: {doc_name}\n\n"
        "TASK: Summarise the document below. Produce a concise TL;DR (1-3 "
        "sentences), up to 8 key points, and any action items the document "
        "asks for. Use the schema fields - no extra prose.\n\n"
        "--- DOCUMENT START ---\n"
        f"{_truncate(doc_text)}\n"
        "--- DOCUMENT END ---"
    )


def build_qa_user(
    *, doc_name: str, doc_text: str, question: str, output_lang: str
) -> str:
    return (
        f"OUTPUT_LANGUAGE: {output_lang}\n"
        f"DOCUMENT NAME: {doc_name}\n\n"
        f"USER QUESTION: {question}\n\n"
        "TASK: Answer the question using ONLY the document text. Return "
        "the answer, verbatim quotes from the document as evidence, and a "
        "confidence level (low / medium / high). If the document does not "
        "contain the answer, set confidence to \"low\" and the answer to "
        "\"unknown\" / \"neuvedeno\".\n\n"
        "--- DOCUMENT START ---\n"
        f"{_truncate(doc_text)}\n"
        "--- DOCUMENT END ---"
    )


def build_rewrite_user(
    *,
    doc_name: str,
    doc_text: str,
    passage: str,
    tone: str,
    output_lang: str,
) -> str:
    return (
        f"OUTPUT_LANGUAGE: {output_lang}\n"
        f"DOCUMENT NAME: {doc_name}\n"
        f"TARGET TONE: {tone}\n\n"
        "TASK: Rewrite the passage below for clarity and the requested "
        "tone. Keep the meaning and any concrete facts (names, numbers, "
        "dates) intact. Use the surrounding document only for context - "
        "do not add new facts that are not in the passage.\n\n"
        "--- PASSAGE START ---\n"
        f"{passage}\n"
        "--- PASSAGE END ---\n\n"
        "--- DOCUMENT (for context) START ---\n"
        f"{_truncate(doc_text, max_chars=40_000)}\n"
        "--- DOCUMENT END ---"
    )


def build_extract_user(*, doc_name: str, doc_text: str, output_lang: str) -> str:
    return (
        f"OUTPUT_LANGUAGE: {output_lang}\n"
        f"DOCUMENT NAME: {doc_name}\n\n"
        "TASK: Extract the most important factual data from the document "
        "and return it as a list of {label, value, evidence} rows. Focus "
        "on names, dates, deadlines, amounts, contacts, identifiers, and "
        "obligations. Skip filler. Each value must be a verbatim string "
        "from the document.\n\n"
        "--- DOCUMENT START ---\n"
        f"{_truncate(doc_text)}\n"
        "--- DOCUMENT END ---"
    )
