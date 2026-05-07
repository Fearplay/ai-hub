"""Per-session token + dollar accounting.

A single in-memory singleton aggregates LLM usage across all sections so
the right-side context panel can show "X calls · Y tokens · $Z" the way
ApplyPilot did. The tracker subscribes can rerender the panel after each
provider call by registering a listener via :func:`subscribe`.

Cost numbers come from :func:`estimate_cost` which uses 2026 public list
pricing for OpenAI and Anthropic. Pricing is opinionated, not exact: the
goal is to keep the user roughly informed, not to invoice them.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, Iterable


# 2026 list prices, USD per 1M tokens (input / output).
_OPENAI_PRICES: dict[str, tuple[float, float]] = {
    "gpt-5.4-mini": (0.25, 2.00),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5-nano": (0.05, 0.40),
    "gpt-5.4": (1.25, 10.00),
    "gpt-5.5": (3.00, 15.00),
}

_ANTHROPIC_PRICES: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-7": (5.00, 25.00),
}


def estimate_cost(provider: str, model: str, tokens_in: int, tokens_out: int) -> float:
    table = _ANTHROPIC_PRICES if provider == "anthropic" else _OPENAI_PRICES
    price_in, price_out = table.get(model, (0.0, 0.0))
    return (tokens_in / 1_000_000.0) * price_in + (tokens_out / 1_000_000.0) * price_out


@dataclass
class CostTracker:
    calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    listeners: list[Callable[[], None]] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def tokens_total(self) -> int:
        return self.tokens_in + self.tokens_out

    def record(
        self,
        *,
        provider: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
    ) -> None:
        with self._lock:
            self.calls += 1
            self.tokens_in += max(0, int(tokens_in))
            self.tokens_out += max(0, int(tokens_out))
            self.cost_usd += estimate_cost(provider, model, tokens_in, tokens_out)
            listeners = list(self.listeners)
        for listener in listeners:
            try:
                listener()
            except Exception:
                pass

    def reset(self) -> None:
        with self._lock:
            self.calls = 0
            self.tokens_in = 0
            self.tokens_out = 0
            self.cost_usd = 0.0
            listeners = list(self.listeners)
        for listener in listeners:
            try:
                listener()
            except Exception:
                pass

    def subscribe(self, listener: Callable[[], None]) -> Callable[[], None]:
        with self._lock:
            self.listeners.append(listener)

        def _unsub() -> None:
            with self._lock:
                if listener in self.listeners:
                    self.listeners.remove(listener)

        return _unsub


COST = CostTracker()


def known_models(provider: str) -> Iterable[str]:
    if provider == "anthropic":
        return tuple(_ANTHROPIC_PRICES.keys())
    return tuple(_OPENAI_PRICES.keys())
