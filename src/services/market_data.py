"""Live market data via ``yfinance`` for the AI Finance section.

Why a dedicated service?

* yfinance hits public Yahoo Finance endpoints with no API key and no
  user identification. We keep the call site in one place so we can
  document this once (in the README / Settings tooltip) and never leak
  user data.
* A 60-second in-memory cache keeps the section responsive without
  spamming Yahoo on every right-panel rebuild.
* The kill-switch in :mod:`src.services.settings_store`
  (``market_data_enabled``) lets privacy-minded users turn off all
  outbound network traffic from the section with one toggle - the
  service then returns ``[]`` and the caller falls back to its mock
  ticker list.

The service is import-light: yfinance itself is imported lazily on
first call so a failed import (no network at build time, library not
installed) never blocks app startup. All exceptions are logged via
:mod:`src.services.logger` so the user can find out why the markets
card is empty without digging into a console.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional, Sequence

from src.services import logger as logger_service
from src.services import settings_store


CACHE_TTL_SECONDS = 60


@dataclass
class Quote:
    """One ticker snapshot used by the right-hand Markets card."""

    symbol: str
    name: str
    last: float
    change_pct: float
    trend: str  # "up" | "down" | "flat"
    spark: list[float]


_LOCK = threading.Lock()
_QUOTE_CACHE: dict[str, tuple[float, Quote]] = {}
_FX_CACHE: dict[str, tuple[float, float]] = {}


def _now() -> float:
    return time.monotonic()


def _trend_from_change(change_pct: float) -> str:
    if change_pct > 0.05:
        return "up"
    if change_pct < -0.05:
        return "down"
    return "flat"


def _import_yfinance():
    try:
        import yfinance  # type: ignore[import-not-found]

        return yfinance
    except Exception as exc:
        logger_service.log_exception(
            "market_data", "yfinance_import_failed", exc,
        )
        return None


def _fetch_single(yf, symbol: str, *, friendly_name: str = "") -> Optional[Quote]:
    """Pull last close + % change + a tiny spark for one symbol.

    Tries ``Ticker.history(period="5d", interval="1d")`` first because
    it returns enough datapoints for the sparkline and consistently
    works across stocks / indices / FX / crypto. Falls back to
    ``download(...)`` for symbols Yahoo only exposes via batch
    endpoints.
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="14d", interval="1d", auto_adjust=False)
        if hist is None or hist.empty:
            return None
        closes = [float(v) for v in hist["Close"].tolist() if v == v]
        if not closes:
            return None
        # Spark = last ~12 closes, oldest -> newest, so the sparkline
        # widget reads left-to-right like a normal chart.
        spark = closes[-12:]
        last = closes[-1]
        prev = closes[-2] if len(closes) >= 2 else last
        if prev:
            change_pct = (last - prev) / prev * 100.0
        else:
            change_pct = 0.0
        info_name = ""
        try:
            info_name = str(ticker.info.get("shortName") or ticker.info.get("longName") or "")
        except Exception:
            info_name = ""
        return Quote(
            symbol=symbol,
            name=info_name or friendly_name or symbol,
            last=float(last),
            change_pct=float(change_pct),
            trend=_trend_from_change(float(change_pct)),
            spark=spark,
        )
    except Exception as exc:
        logger_service.log_exception(
            "market_data", "fetch_single_failed", exc, symbol=symbol,
        )
        return None


def get_quotes(
    symbols: Sequence[str],
    *,
    name_hints: Optional[dict[str, str]] = None,
) -> list[Quote]:
    """Return cached or freshly-fetched quotes for the given symbols.

    ``name_hints`` lets the caller suggest a friendly display name per
    symbol (e.g. ``{"^GSPC": "S&P 500"}``) when Yahoo's ``shortName``
    is verbose or missing.

    Returns an empty list when:

    * the global ``market_data_enabled`` toggle is off,
    * yfinance is not installed, or
    * every requested symbol failed to fetch.
    """
    if not symbols:
        return []
    if not settings_store.get_market_data_enabled():
        return []
    yf = _import_yfinance()
    if yf is None:
        return []

    hints = name_hints or {}
    now = _now()
    out: list[Quote] = []
    for raw_symbol in symbols:
        symbol = str(raw_symbol).strip()
        if not symbol:
            continue
        with _LOCK:
            cached = _QUOTE_CACHE.get(symbol)
        if cached and (now - cached[0]) < CACHE_TTL_SECONDS:
            out.append(cached[1])
            continue
        quote = _fetch_single(yf, symbol, friendly_name=hints.get(symbol, ""))
        if quote is None:
            # Keep returning the previous value (if any) for graceful
            # degradation - one failed fetch should not blank the card.
            if cached:
                out.append(cached[1])
            continue
        with _LOCK:
            _QUOTE_CACHE[symbol] = (now, quote)
        out.append(quote)
    logger_service.log_event(
        "INFO", "market_data", "get_quotes_done",
        requested=len(symbols),
        returned=len(out),
    )
    return out


def get_fx(pair: str) -> Optional[float]:
    """Return the latest FX rate for a Yahoo currency pair.

    ``pair`` follows the Yahoo convention ``"USDCZK=X"`` /
    ``"EURUSD=X"``. Cached for 60 seconds; respects the kill-switch.
    Returns ``None`` if disabled, not installed, or the fetch failed.
    """
    pair = (pair or "").strip()
    if not pair:
        return None
    if not settings_store.get_market_data_enabled():
        return None
    yf = _import_yfinance()
    if yf is None:
        return None
    now = _now()
    with _LOCK:
        cached = _FX_CACHE.get(pair)
    if cached and (now - cached[0]) < CACHE_TTL_SECONDS:
        return cached[1]
    try:
        ticker = yf.Ticker(pair)
        hist = ticker.history(period="5d", interval="1d", auto_adjust=False)
        if hist is None or hist.empty:
            return None
        last = float(hist["Close"].iloc[-1])
    except Exception as exc:
        logger_service.log_exception(
            "market_data", "fetch_fx_failed", exc, pair=pair,
        )
        return None
    with _LOCK:
        _FX_CACHE[pair] = (now, last)
    return last


__all__ = ["Quote", "get_quotes", "get_fx", "CACHE_TTL_SECONDS"]
