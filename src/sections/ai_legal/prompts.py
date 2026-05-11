"""System prompts + user-message builders for the AI Legal section.

Every assistant turn shares the same system prompt: a legal-aware
assistant that:

* never claims to be a lawyer,
* only uses information from the attached document (re-stating the
  global no-hallucination clause that :mod:`src.services.ai_provider`
  prepends),
* answers in the user's UI language (``output_lang`` arg).

User messages are built per-call. The chat history is folded into the
user message as a short conversation transcript so we don't have to
juggle multi-turn arrays per-provider. This keeps cost predictable -
each call sends the system prompt, the full document text, and the
running transcript.
"""

from __future__ import annotations

from typing import Iterable

from src.sections.ai_legal.data import (
    QUICK_ACTION_CHANGES,
    QUICK_ACTION_EXPLAIN,
    QUICK_ACTION_RISKS,
    QUICK_ACTION_SUMMARIZE,
)
from src.sections.ai_legal.state import ChatMessage


def system_prompt(output_lang: str) -> str:
    """Per-section system prompt.

    ``output_lang`` is ``"en"`` or ``"cs"`` so the LLM answers in the
    same language the user is reading the UI in.
    """
    if output_lang == "cs":
        return (
            "Jsi AI asistent pro orientaci v právních dokumentech. NEJSI advokát "
            "a tvé odpovědi nenahrazují právní poradenství. V každé delší "
            "odpovědi to alespoň jednou připomeň.\n\n"
            "Pravidla, která NIKDY neporušíš:\n"
            "1. Pracuj výhradně s textem dokumentu, který ti dal uživatel. "
            "Pokud informace v dokumentu chybí, řekni to. Nevymýšlej čísla, "
            "data, jména stran, sankce ani odkazy na konkrétní paragrafy.\n"
            "2. Odpovídej česky, srozumitelným běžným jazykem. Vyhýbej se "
            "právní hantýrce — když musíš použít odborný termín, hned ho "
            "v závorce vysvětli.\n"
            "3. Strukturuj odpovědi pomocí krátkých odstavců, odrážek a "
            "tučného zvýraznění klíčových slov (markdown).\n"
            "4. Pokud uživatel nepřiložil dokument, zdvořile řekni, ať jej "
            "přetáhne do pravého panelu, a nehádej obsah."
        )
    return (
        "You are an AI assistant helping a non-lawyer understand legal "
        "documents. You are NOT a lawyer and your answers do not replace "
        "legal advice. Remind the user of that at least once in any longer "
        "answer.\n\n"
        "Rules you MUST follow:\n"
        "1. Work strictly from the document text the user attached. If a "
        "piece of information is missing from the document, say so. Do "
        "not invent numbers, dates, party names, penalties, or references "
        "to specific statutes.\n"
        "2. Answer in plain English. Avoid legalese — when you must use a "
        "legal term, explain it in parentheses immediately.\n"
        "3. Structure answers with short paragraphs, bullet lists, and "
        "**bold** highlights for key terms (markdown).\n"
        "4. If the user has not attached a document yet, politely ask "
        "them to drop one into the right-hand panel; do not guess at the "
        "content."
    )


def _format_history(history: Iterable[ChatMessage], *, limit: int = 12) -> str:
    """Render the recent transcript as a short ``role: text`` log.

    We keep the last ``limit`` turns so the prompt does not balloon as
    the conversation grows. Attachment chips are omitted - the assistant
    already has the full document text in the same message.
    """
    messages = list(history)[-limit:]
    if not messages:
        return "(no prior messages)"
    lines: list[str] = []
    for m in messages:
        role = "User" if m.role == "user" else "Assistant"
        lines.append(f"{role}: {m.text.strip()}")
    return "\n".join(lines)


def _format_doc(doc_text: str, *, max_chars: int = 16000) -> str:
    """Truncate the document text to a safe size for prompt context.

    16 000 characters is roughly 4 000 tokens which fits comfortably
    alongside the system prompt + history + answer within typical model
    context windows (>= 8k). For very large documents the cutoff happens
    at the character boundary; the assistant is instructed in the
    prompt to mention the truncation if a question can't be answered
    with the visible chunk.
    """
    text = (doc_text or "").strip()
    if not text:
        return "(no document attached)"
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[... truncated; only the first portion of the document is shown ...]"


def build_chat_user(
    *,
    user_text: str,
    history: Iterable[ChatMessage],
    doc_text: str,
    doc_name: str,
    output_lang: str,
) -> str:
    """User message for free-form chat turns."""
    transcript = _format_history(history)
    doc = _format_doc(doc_text)
    if output_lang == "cs":
        return (
            f"# Aktuální dokument: {doc_name or '(žádný)'}\n\n"
            f"--- TEXT DOKUMENTU ---\n{doc}\n--- KONEC DOKUMENTU ---\n\n"
            f"# Předchozí konverzace\n{transcript}\n\n"
            f"# Nová otázka uživatele\n{user_text}\n\n"
            "Odpověz česky v markdownu. Pokud informace v dokumentu chybí, "
            "řekni to a nevymýšlej."
        )
    return (
        f"# Current document: {doc_name or '(none)'}\n\n"
        f"--- DOCUMENT TEXT ---\n{doc}\n--- END OF DOCUMENT ---\n\n"
        f"# Prior conversation\n{transcript}\n\n"
        f"# User's new question\n{user_text}\n\n"
        "Answer in English markdown. If the document does not contain the "
        "information, say so — do not invent it."
    )


_QUICK_ACTION_PROMPTS_EN: dict[str, str] = {
    QUICK_ACTION_SUMMARIZE: (
        "Summarise the attached legal document for someone who is not a lawyer. "
        "Cover: the parties, the subject of the agreement, key obligations, "
        "money / pricing, deadlines, and termination. End with one paragraph "
        "called 'Bottom line:' that states in plain English what this document "
        "actually means for the reader."
    ),
    QUICK_ACTION_RISKS: (
        "Read the attached document and list the risks for the party who would "
        "be signing it. For each risk: a short title, the clause it comes from, "
        "and why it is risky in plain English. Group risks into 'High', "
        "'Medium', 'Low'. If no real risks are present, say so."
    ),
    QUICK_ACTION_EXPLAIN: (
        "Pick the legal / technical terms from the attached document that a "
        "non-lawyer is most likely to miss, and explain each in one short "
        "paragraph. Quote the original wording in italics before each "
        "explanation."
    ),
    QUICK_ACTION_CHANGES: (
        "Suggest concrete edits to the attached document that would protect "
        "the reader's interests. For each suggestion: which clause, the "
        "current wording, the proposed wording, and one sentence explaining "
        "why the change is helpful. Do not invent clauses that are not in "
        "the document — only edit what is there."
    ),
}

_QUICK_ACTION_PROMPTS_CS: dict[str, str] = {
    QUICK_ACTION_SUMMARIZE: (
        "Shrň přiložený právní dokument pro člověka, který není právník. "
        "Pokryj: strany, předmět smlouvy, hlavní povinnosti, peníze / ceny, "
        "termíny a ukončení. Skonči odstavcem nazvaným 'Závěrem:', který "
        "běžným jazykem řekne, co tento dokument pro čtenáře doopravdy znamená."
    ),
    QUICK_ACTION_RISKS: (
        "Prostuduj přiložený dokument a sepiš rizika pro stranu, která by ho "
        "měla podepsat. U každého rizika: krátký název, klauzule odkud "
        "pochází, a proč je to riziko v běžné češtině. Rozděl rizika na "
        "'Vysoká', 'Střední', 'Nízká'. Pokud žádná reálná rizika neexistují, řekni to."
    ),
    QUICK_ACTION_EXPLAIN: (
        "Vyber z dokumentu právní a odborné pojmy, které by laik nejspíš "
        "nepochopil, a u každého ho v jednom krátkém odstavci vysvětli. "
        "Před každým vysvětlením uveď kurzívou původní formulaci."
    ),
    QUICK_ACTION_CHANGES: (
        "Navrhni konkrétní úpravy přiloženého dokumentu, které by ochránily "
        "zájmy čtenáře. U každé úpravy: která klauzule, současné znění, "
        "navržené znění, a jedna věta proč je to lepší. Nevymýšlej nová "
        "ujednání, která ve smlouvě nejsou — uprav jen to, co tam je."
    ),
}


def quick_action_instruction(action_key: str, *, output_lang: str) -> str:
    """The user-bubble text shown in chat when a quick-action chip is tapped.

    Mirrors the chip's visible label so the UI bubble matches the verb
    the user clicked. The longer, model-facing prompt is separate (see
    :func:`build_quick_action_user`).
    """
    from src.sections.ai_legal.strings import s

    label_keys = {
        QUICK_ACTION_SUMMARIZE: "chat_action_summarize",
        QUICK_ACTION_RISKS: "chat_action_risks",
        QUICK_ACTION_EXPLAIN: "chat_action_explain",
        QUICK_ACTION_CHANGES: "chat_action_changes",
    }
    txt = s(output_lang)
    return txt.get(label_keys.get(action_key, ""), "")


def build_quick_action_user(
    *,
    action_key: str,
    doc_text: str,
    doc_name: str,
    history: Iterable[ChatMessage],
    output_lang: str,
) -> str:
    """Compose the user message for a quick-action chip click.

    The model-facing instruction is much more detailed than the chip
    label (which is just "Summarise" / "Find risks" / …). We pass the
    document, the history, and the verbose instruction so the model has
    everything it needs.
    """
    table = _QUICK_ACTION_PROMPTS_CS if output_lang == "cs" else _QUICK_ACTION_PROMPTS_EN
    instruction = table.get(action_key) or table[QUICK_ACTION_SUMMARIZE]
    transcript = _format_history(history)
    doc = _format_doc(doc_text)
    if output_lang == "cs":
        return (
            f"# Aktuální dokument: {doc_name or '(žádný)'}\n\n"
            f"--- TEXT DOKUMENTU ---\n{doc}\n--- KONEC DOKUMENTU ---\n\n"
            f"# Předchozí konverzace\n{transcript}\n\n"
            f"# Pokyn\n{instruction}\n\n"
            "Odpověz česky v markdownu."
        )
    return (
        f"# Current document: {doc_name or '(none)'}\n\n"
        f"--- DOCUMENT TEXT ---\n{doc}\n--- END OF DOCUMENT ---\n\n"
        f"# Prior conversation\n{transcript}\n\n"
        f"# Instruction\n{instruction}\n\n"
        "Answer in English markdown."
    )
