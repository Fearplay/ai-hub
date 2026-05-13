"""Orchestration for the AI Legal section.

Three public functions cover everything the UI needs:

* :func:`attach_document` - stores the parsed document text + metadata
  on :data:`src.sections.ai_legal.state.STATE` and adds a small
  "I've read X" bubble so the user knows the AI now has the document.
* :func:`send_chat_message` - free-form user turn. Appends a user
  bubble, calls :func:`src.services.ai_provider.run`, appends an
  assistant bubble.
* :func:`run_quick_action` - the four quick-action chips. Appends a
  user bubble with the chip label, then asks the model with a detailed
  per-action instruction.

Every call:

* checks :attr:`LegalState.demo_mode`; in demo mode returns a canned
  reply without ever hitting an API,
* logs ``*_start`` and matching ``*_done`` / ``*_failed`` lines via
  :mod:`src.services.logger` so failures show up in Settings -> Debug
  logs,
* updates ``STATE.activity`` and pings the right-hand context panel
  through :data:`src.sections.ai_legal.refs.REFS` so the activity badge
  reflects what the section is doing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.services import ai_provider
from src.services import logger as logger_service
from src.services.file_parser import ParsedFile
from src.sections.ai_legal import prompts, schema
from src.sections.ai_legal.refs import REFS
from src.sections.ai_legal.state import ChatMessage, STATE
from src.sections.ai_legal.strings import s


def _now_label() -> str:
    return datetime.now().strftime("%H:%M")


def _set_activity(value: str) -> None:
    """Update ``STATE.activity`` and refresh the right-hand panel.

    Routed through :meth:`LegalRefs.request_context_refresh` (when
    available) so the badge repaints on the next GUI tick regardless of
    which thread changed the value.
    """
    prev = STATE.activity
    STATE.activity = value
    if prev != value:
        logger_service.log_event(
            "INFO", "ai_legal.pipeline", "activity_change",
            prev=prev, new=value,
        )
    cb = getattr(REFS, "request_context_refresh", None)
    if callable(cb):
        try:
            cb()
        except Exception as exc:
            logger_service.log_exception(
                "ai_legal.pipeline", "activity_refresh_failed", exc,
            )
    else:
        rerender = getattr(REFS, "rerender_context", None)
        if callable(rerender):
            try:
                rerender()
            except Exception as exc:
                logger_service.log_exception(
                    "ai_legal.pipeline", "activity_rerender_failed", exc,
                )


def _append(message: ChatMessage) -> None:
    STATE.chat_messages.append(message)


def attach_document(*, file_dict: dict, parsed: ParsedFile) -> None:
    """Store a freshly-parsed document on STATE and announce it in chat.

    Called from :func:`src.sections.ai_legal.context._on_file_resolved`.
    The display chip (``STATE.uploaded_file``) and the prompt fuel
    (``STATE.attached_doc_text``) are populated together so they can
    never get out of sync.
    """
    name = file_dict.get("name", "")
    ext = (parsed.ext or "").lower()
    char_count = len(parsed.text or "")
    logger_service.log_event(
        "INFO", "ai_legal.pipeline", "attach_document_start",
        name=name, ext=ext, chars=char_count,
    )
    STATE.uploaded_file = file_dict
    STATE.attached_doc_text = parsed.text or ""
    STATE.attachment_announced = False
    STATE.last_error = ""

    if not STATE.attachment_announced:
        txt = s("cs")  # the announcement text is short; both langs share template
        # We don't know the UI language here - the chat tab passes lang
        # when rendering, but the bubble is read-only text. Pick CS/EN
        # based on which one the user is reading by inspecting any
        # prior message; otherwise default to English to avoid mojibake.
        lang_guess = "en"
        if STATE.chat_messages:
            # No-op heuristic, but keeps the door open for future
            # propagation of user-language preference into pipeline.
            lang_guess = "en"
        txt = s(lang_guess)
        announcement = txt["chat_attached_announcement"].format(name=name)
        _append(ChatMessage(
            role="assistant",
            text=announcement,
            time=_now_label(),
        ))
        STATE.attachment_announced = True

    logger_service.log_event(
        "INFO", "ai_legal.pipeline", "attach_document_done",
        name=name, chars=char_count,
    )


def _demo_reply(*, doc_name: str, doc_chars: int, output_lang: str) -> str:
    txt = s(output_lang)
    return txt["chat_demo_reply_template"].format(
        name=doc_name or "?",
        chars=doc_chars,
    )


def _require_document(output_lang: str) -> Optional[str]:
    """Return a localised warning if no document is attached, else None."""
    if STATE.attached_doc_text.strip():
        return None
    txt = s(output_lang)
    return txt["chat_no_document_warning"]


def send_chat_message(*, user_text: str, output_lang: str) -> tuple[str, str]:
    """Process a free-form user turn end-to-end.

    Returns ``(assistant_text, error_message)``; ``error_message`` is
    empty on success. The function appends both the user bubble and the
    assistant bubble (or an error bubble) to ``STATE.chat_messages`` so
    the caller only needs to re-render the chat view.
    """
    user_text = (user_text or "").strip()
    if not user_text:
        return "", "Empty message."

    now = _now_label()
    name = (STATE.uploaded_file or {}).get("name", "")
    attachment_name = ""
    if name and not STATE.attachment_announced:
        # First message after the announcement still shows the chip so
        # the user sees the file they attached on their very first turn.
        attachment_name = name

    _append(ChatMessage(
        role="user", text=user_text, time=now, attachment_name=attachment_name,
    ))

    warning = _require_document(output_lang)
    if warning is not None:
        _append(ChatMessage(role="assistant", text=warning, time=_now_label()))
        logger_service.log_event(
            "WARNING", "ai_legal.pipeline", "send_chat_no_document",
            chars=len(user_text),
        )
        return warning, ""

    doc_chars = len(STATE.attached_doc_text)
    logger_service.log_event(
        "INFO", "ai_legal.pipeline", "send_chat_start",
        output_lang=output_lang, chars=len(user_text),
        demo_mode=STATE.demo_mode, history=len(STATE.chat_messages),
        doc_chars=doc_chars,
    )
    _set_activity("thinking")

    if STATE.demo_mode:
        reply = _demo_reply(doc_name=name, doc_chars=doc_chars, output_lang=output_lang)
        _append(ChatMessage(role="assistant", text=reply, time=_now_label()))
        _set_activity("ready")
        logger_service.log_event(
            "INFO", "ai_legal.pipeline", "send_chat_demo_done",
            chars=len(reply),
        )
        return reply, ""

    system = prompts.system_prompt(output_lang)
    user = prompts.build_chat_user(
        user_text=user_text,
        history=STATE.chat_messages[:-1],  # exclude the user bubble we just appended
        doc_text=STATE.attached_doc_text,
        doc_name=name,
        output_lang=output_lang,
    )

    try:
        result = ai_provider.run(
            system=system,
            user=user,
            schema=schema.CHAT_SCHEMA,
            schema_name="legal_chat",
            max_output_tokens=1500,
            temperature=0.2,
        )
    except ai_provider.ProviderError as exc:
        message = str(exc)
        STATE.last_error = message
        _set_activity("error")
        txt = s(output_lang)
        rendered = f"{txt['chat_error_prefix']} {message}"
        _append(ChatMessage(role="assistant", text=rendered, time=_now_label()))
        logger_service.log_exception(
            "ai_legal.pipeline", "send_chat_provider_error", exc,
            chars=len(user_text),
        )
        return "", message
    except Exception as exc:  # safety net for unexpected SDK bugs
        message = str(exc)
        STATE.last_error = message
        _set_activity("error")
        txt = s(output_lang)
        rendered = f"{txt['chat_error_prefix']} {message}"
        _append(ChatMessage(role="assistant", text=rendered, time=_now_label()))
        logger_service.log_exception(
            "ai_legal.pipeline", "send_chat_unexpected_error", exc,
        )
        return "", message

    assistant_text = (result.text or "").strip()
    if not assistant_text:
        txt = s(output_lang)
        assistant_text = (
            "Promiňte, AI nevrátila žádnou odpověď. Zkuste to znovu nebo "
            "zkontrolujte API klíč v Nastavení."
            if output_lang == "cs"
            else "Sorry, the AI returned an empty response. Try again or check the API key in Settings."
        )
    _append(ChatMessage(role="assistant", text=assistant_text, time=_now_label()))
    _set_activity("ready")
    logger_service.log_event(
        "INFO", "ai_legal.pipeline", "send_chat_done",
        chars=len(assistant_text),
        tokens_in=result.tokens_in, tokens_out=result.tokens_out,
        cost_usd=round(result.cost_usd, 6),
    )
    return assistant_text, ""


def run_quick_action(*, action_key: str, output_lang: str) -> tuple[str, str]:
    """Run one of the four chat quick-action chips.

    Appends a user-style bubble showing the chip label so the
    conversation stays readable, then calls the AI provider with a
    longer per-action instruction.
    """
    label = prompts.quick_action_instruction(action_key, output_lang=output_lang)
    if not label:
        logger_service.log_event(
            "WARNING", "ai_legal.pipeline", "quick_action_unknown",
            action=action_key,
        )
        return "", f"Unknown action: {action_key!r}"

    now = _now_label()
    name = (STATE.uploaded_file or {}).get("name", "")
    attachment_name = name if name and not STATE.attachment_announced else ""

    _append(ChatMessage(
        role="user", text=label, time=now, attachment_name=attachment_name,
    ))

    warning = _require_document(output_lang)
    if warning is not None:
        _append(ChatMessage(role="assistant", text=warning, time=_now_label()))
        logger_service.log_event(
            "WARNING", "ai_legal.pipeline", "quick_action_no_document",
            action=action_key,
        )
        return warning, ""

    doc_chars = len(STATE.attached_doc_text)
    logger_service.log_event(
        "INFO", "ai_legal.pipeline", "quick_action_start",
        action=action_key, output_lang=output_lang,
        demo_mode=STATE.demo_mode, history=len(STATE.chat_messages),
        doc_chars=doc_chars,
    )
    _set_activity("thinking")

    if STATE.demo_mode:
        reply = _demo_reply(doc_name=name, doc_chars=doc_chars, output_lang=output_lang)
        _append(ChatMessage(role="assistant", text=reply, time=_now_label()))
        _set_activity("ready")
        logger_service.log_event(
            "INFO", "ai_legal.pipeline", "quick_action_demo_done",
            action=action_key, chars=len(reply),
        )
        return reply, ""

    system = prompts.system_prompt(output_lang)
    user = prompts.build_quick_action_user(
        action_key=action_key,
        doc_text=STATE.attached_doc_text,
        doc_name=name,
        history=STATE.chat_messages[:-1],
        output_lang=output_lang,
    )

    try:
        result = ai_provider.run(
            system=system,
            user=user,
            schema=schema.QUICK_ACTION_SCHEMA,
            schema_name="legal_quick_action",
            max_output_tokens=1800,
            temperature=0.2,
        )
    except ai_provider.ProviderError as exc:
        message = str(exc)
        STATE.last_error = message
        _set_activity("error")
        txt = s(output_lang)
        rendered = f"{txt['chat_error_prefix']} {message}"
        _append(ChatMessage(role="assistant", text=rendered, time=_now_label()))
        logger_service.log_exception(
            "ai_legal.pipeline", "quick_action_provider_error", exc,
            action=action_key,
        )
        return "", message
    except Exception as exc:
        message = str(exc)
        STATE.last_error = message
        _set_activity("error")
        txt = s(output_lang)
        rendered = f"{txt['chat_error_prefix']} {message}"
        _append(ChatMessage(role="assistant", text=rendered, time=_now_label()))
        logger_service.log_exception(
            "ai_legal.pipeline", "quick_action_unexpected_error", exc,
            action=action_key,
        )
        return "", message

    assistant_text = (result.text or "").strip()
    if not assistant_text:
        assistant_text = (
            "Promiňte, AI nevrátila žádnou odpověď."
            if output_lang == "cs"
            else "Sorry, the AI returned an empty response."
        )
    _append(ChatMessage(role="assistant", text=assistant_text, time=_now_label()))
    _set_activity("ready")
    logger_service.log_event(
        "INFO", "ai_legal.pipeline", "quick_action_done",
        action=action_key, chars=len(assistant_text),
        tokens_in=result.tokens_in, tokens_out=result.tokens_out,
        cost_usd=round(result.cost_usd, 6),
    )
    return assistant_text, ""


def reset_chat() -> None:
    """Wipe chat history and the attached document.

    Used by the "new chat" button in the sidebar / any future reset
    affordance.
    """
    logger_service.log_event(
        "INFO", "ai_legal.pipeline", "reset_chat",
        messages=len(STATE.chat_messages),
        had_doc=bool(STATE.attached_doc_text),
    )
    STATE.chat_messages = []
    STATE.uploaded_file = None
    STATE.attached_doc_text = ""
    STATE.attachment_announced = False
    STATE.last_error = ""
    STATE.activity = "ready"
