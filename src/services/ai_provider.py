"""Single entry point for OpenAI + Anthropic chat completions.

Sections never import ``openai`` or ``anthropic`` directly - they call
:func:`run` which handles:

* Provider + model lookup from :mod:`src.services.settings_store`.
* API key lookup from the OS keystore via :mod:`src.services.secrets`.
* No-hallucination policy clause prepended to every system prompt.
* Strict structured output (JSON schema) when the caller passes a schema -
  OpenAI uses ``response_format=json_schema``, Anthropic uses a forced
  tool_use call.
* Token / cost accounting routed into :data:`src.services.cost_tracker.COST`.

Errors are mapped onto :class:`ProviderError` so callers can show the user
something more useful than "openai.AuthenticationError".
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from src.services import secrets, settings_store
from src.services.cost_tracker import COST, estimate_cost


NO_HALLUCINATION_CLAUSE = (
    "STRICT POLICY (overrides every other instruction): "
    "Never invent facts, names, dates, metrics, employers, certifications, "
    "languages, contact details, projects, links, or quotes. "
    "Use only information present in the user-provided context. "
    "If a required fact is missing, leave the field empty or write "
    "\"unknown\" / \"neuvedeno\". Do not pad answers with generic filler. "
    "Mark any inference as such; do not present it as fact."
)


class ProviderError(RuntimeError):
    """Wraps SDK-specific exceptions in a single user-facing class."""


@dataclass
class ProviderResult:
    provider: str
    model: str
    text: str
    data: Optional[Any]
    tokens_in: int
    tokens_out: int
    cost_usd: float


def _resolve_provider_and_model(
    provider: Optional[str],
    model: Optional[str],
) -> tuple[str, str]:
    p = provider or settings_store.get_provider()
    if p not in (settings_store.PROVIDER_OPENAI, settings_store.PROVIDER_ANTHROPIC):
        p = settings_store.PROVIDER_OPENAI
    m = model or settings_store.get_model(p)
    return p, m


def _ensure_key(provider: str) -> str:
    name = (
        secrets.ANTHROPIC_API_KEY
        if provider == settings_store.PROVIDER_ANTHROPIC
        else secrets.OPENAI_API_KEY
    )
    key = secrets.get_secret(name)
    if not key:
        raise ProviderError(
            f"Missing API key for {provider!r}. Open Settings and save your key first."
        )
    return key


def _build_system(system: str, *, allow_no_clause: bool) -> str:
    if allow_no_clause:
        return system
    if not system.strip():
        return NO_HALLUCINATION_CLAUSE
    return f"{NO_HALLUCINATION_CLAUSE}\n\n---\n\n{system}"


def _try_parse_json(text: str) -> Optional[Any]:
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[: -3]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _run_openai(
    *,
    model: str,
    system: str,
    user: str,
    schema: Optional[dict],
    schema_name: str,
    max_output_tokens: int,
    temperature: float,
    api_key: str,
    enable_web_search: bool = False,
) -> tuple[str, Optional[Any], int, int]:
    try:
        from openai import OpenAI  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ProviderError(
            "The openai package is not installed. Run `pip install -r requirements.txt`."
        ) from exc

    client = OpenAI(api_key=api_key)

    # Web search is a Responses-API tool, not a Chat-Completions one.
    # When the caller asks for it we route through the Responses API
    # and let the model decide whether to call ``web_search_preview``.
    # We only do this when no JSON schema is requested (schemas need
    # the dedicated structured-output path on Chat Completions).
    if enable_web_search and schema is None:
        try:
            response = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                tools=[{"type": "web_search_preview"}],
                max_output_tokens=max_output_tokens,
                temperature=temperature,
            )
        except Exception as exc:
            raise ProviderError(f"OpenAI request failed: {exc}") from exc
        text = getattr(response, "output_text", "") or ""
        usage = getattr(response, "usage", None)
        tokens_in = getattr(usage, "input_tokens", 0) or 0
        tokens_out = getattr(usage, "output_tokens", 0) or 0
        return text, None, int(tokens_in), int(tokens_out)

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_completion_tokens": max_output_tokens,
        "temperature": temperature,
    }
    if schema is not None:
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": schema,
            },
        }

    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as exc:
        raise ProviderError(f"OpenAI request failed: {exc}") from exc

    choice = response.choices[0] if response.choices else None
    text = choice.message.content if choice and choice.message else ""
    text = text or ""
    data = _try_parse_json(text) if schema is not None else None

    usage = getattr(response, "usage", None)
    tokens_in = getattr(usage, "prompt_tokens", 0) or 0
    tokens_out = getattr(usage, "completion_tokens", 0) or 0
    return text, data, int(tokens_in), int(tokens_out)


def _run_anthropic(
    *,
    model: str,
    system: str,
    user: str,
    schema: Optional[dict],
    schema_name: str,
    max_output_tokens: int,
    temperature: float,
    api_key: str,
    enable_web_search: bool = False,
) -> tuple[str, Optional[Any], int, int]:
    try:
        from anthropic import Anthropic  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ProviderError(
            "The anthropic package is not installed. Run `pip install -r requirements.txt`."
        ) from exc

    client = Anthropic(api_key=api_key)

    kwargs: dict[str, Any] = {
        "model": model,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "max_tokens": max_output_tokens,
        "temperature": temperature,
    }
    if schema is not None:
        kwargs["tools"] = [
            {
                "name": schema_name,
                "description": (
                    "Return the requested structured payload. The arguments "
                    "object is the answer; do not return any free text."
                ),
                "input_schema": schema,
            }
        ]
        kwargs["tool_choice"] = {"type": "tool", "name": schema_name}
    elif enable_web_search:
        # Anthropic's hosted web-search tool. ``max_uses`` is capped at
        # 3 to keep per-turn cost predictable - one or two searches is
        # plenty for the kind of "what is today's S&P 500 close?"
        # question users would ask in the AI Finance chat.
        kwargs["tools"] = [
            {"type": "web_search_20250305", "name": "web_search", "max_uses": 3}
        ]

    try:
        response = client.messages.create(**kwargs)
    except Exception as exc:
        raise ProviderError(f"Anthropic request failed: {exc}") from exc

    text = ""
    data: Optional[Any] = None
    for block in getattr(response, "content", []) or []:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            text += getattr(block, "text", "") or ""
        elif block_type == "tool_use":
            tool_input = getattr(block, "input", None)
            if isinstance(tool_input, dict):
                data = tool_input
                if not text:
                    text = json.dumps(tool_input, ensure_ascii=False)

    usage = getattr(response, "usage", None)
    tokens_in = getattr(usage, "input_tokens", 0) or 0
    tokens_out = getattr(usage, "output_tokens", 0) or 0
    return text, data, int(tokens_in), int(tokens_out)


def run(
    *,
    system: str,
    user: str,
    schema: Optional[dict] = None,
    schema_name: str = "result",
    provider: Optional[str] = None,
    model: Optional[str] = None,
    max_output_tokens: int = 2000,
    temperature: float = 0.2,
    skip_no_hallucination_clause: bool = False,
    enable_web_search: bool = False,
) -> ProviderResult:
    """Single AI entry point for sections.

    ``schema`` should be a JSON Schema dict. When provided, the result's
    ``data`` will be the parsed object (and the model is forced into
    structured-output mode). Otherwise ``data`` is ``None`` and ``text``
    is plain prose / markdown.

    ``enable_web_search`` is an opt-in toggle (mirrors the user's
    Settings checkbox). When ``True`` the provider attaches its hosted
    web-search tool to the call so the model can answer "what is the
    current S&P 500 price?" style questions without the user pasting
    facts in by hand. Web search is **not** combined with structured
    outputs - the schema path already forces the model into a tool call
    of its own, so the flag is ignored when ``schema`` is provided.
    """
    provider_id, model_id = _resolve_provider_and_model(provider, model)
    api_key = _ensure_key(provider_id)

    full_system = _build_system(system, allow_no_clause=skip_no_hallucination_clause)

    if provider_id == settings_store.PROVIDER_ANTHROPIC:
        text, data, tokens_in, tokens_out = _run_anthropic(
            model=model_id,
            system=full_system,
            user=user,
            schema=schema,
            schema_name=schema_name,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            api_key=api_key,
            enable_web_search=enable_web_search,
        )
    else:
        text, data, tokens_in, tokens_out = _run_openai(
            model=model_id,
            system=full_system,
            user=user,
            schema=schema,
            schema_name=schema_name,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            api_key=api_key,
            enable_web_search=enable_web_search,
        )

    COST.record(
        provider=provider_id,
        model=model_id,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )

    return ProviderResult(
        provider=provider_id,
        model=model_id,
        text=text,
        data=data,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=estimate_cost(provider_id, model_id, tokens_in, tokens_out),
    )
