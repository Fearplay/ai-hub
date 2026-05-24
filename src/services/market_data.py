"""Live market data via ``yfinance`` (with a Stooq fallback) for AI Finance.

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

When yfinance itself fails (Yahoo SSL hiccups, the February 2025
endpoint shuffle, empty histories on a fresh symbol), we transparently
fall back to **Stooq** (https://stooq.com). Stooq exposes daily OHLC
data as a plain CSV at ``stooq.com/q/d/l/?s=<symbol>&i=d``, needs no
API key, and stays alive even when Yahoo throttles us. The fallback is
opt-out implicit (any caller that uses ``get_quotes`` / ``get_fx``
benefits) but always logged through :mod:`src.services.logger` so the
debug log makes it obvious where a value came from.

The service is import-light: yfinance itself is imported lazily on
first call so a failed import (no network at build time, library not
installed) never blocks app startup. Stooq uses only the standard
library (``urllib.request``), so it works even when yfinance + curl_cffi
are unavailable. All exceptions are logged via
:mod:`src.services.logger` so the user can find out why the markets
card is empty without digging into a console.
"""

from __future__ import annotations

import csv
import io
import os
import re
import ssl
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional, Sequence

from src.services import logger as logger_service
from src.services import settings_store


CACHE_TTL_SECONDS = 60


_SESSION_LOCK = threading.Lock()
_SHARED_SESSION: Optional[Any] = None


def _ca_bundle_path() -> Optional[str]:
    """Return the best CA bundle path for libcurl (used by curl_cffi).

    Prefers ``CURL_CA_BUNDLE`` (set by ``main.py``), then ``SSL_CERT_FILE``,
    then ``certifi.where()``. ``None`` means "let curl_cffi use its
    default", which on Windows is empty and triggers SSL errors - so
    we always try to provide *something*.
    """
    for env in ("CURL_CA_BUNDLE", "SSL_CERT_FILE"):
        path = os.environ.get(env)
        if path and os.path.isfile(path):
            return path
    try:
        import certifi  # type: ignore[import-not-found]

        bundle = certifi.where()
        if bundle and os.path.isfile(bundle):
            return bundle
    except Exception:
        return None
    return None


def _build_session() -> Optional[Any]:
    """Return a curl_cffi session pre-configured with our CA bundle.

    yfinance>=0.2.40 uses curl_cffi internally and accepts a custom
    ``session=`` on every ``Ticker(...)``. Passing one wired up with
    ``verify=<certifi-bundle>`` works around the empty native CA store
    on stock Windows Python builds.
    """
    try:
        from curl_cffi import requests as curl_requests  # type: ignore[import-not-found]
    except Exception:
        return None
    try:
        bundle = _ca_bundle_path()
        if bundle:
            session = curl_requests.Session(verify=bundle, impersonate="chrome")
        else:
            session = curl_requests.Session(impersonate="chrome")
        return session
    except Exception as exc:
        logger_service.log_exception(
            "market_data", "session_build_failed", exc,
        )
        return None


def _shared_session() -> Optional[Any]:
    global _SHARED_SESSION
    with _SESSION_LOCK:
        if _SHARED_SESSION is not None:
            return _SHARED_SESSION
        _SHARED_SESSION = _build_session()
        return _SHARED_SESSION


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

# Process-wide flag - set the first time a curl_cffi SSL verify error
# escapes, which lets us log a single user-friendly WARNING instead of
# spamming a screen-tall traceback on every retry. Subsequent failures
# downgrade to DEBUG so the debug log stays readable. Cleared on every
# successful fetch so a recovered network re-arms the warning.
_SSL_FAILURE_LOGGED = False


def _is_curl_ssl_error(exc: BaseException) -> bool:
    """Return True when an exception looks like a libcurl TLS failure.

    We match on the class name + the libcurl error preamble instead of
    importing :class:`curl_cffi.requests.exceptions.CertificateVerifyError`
    eagerly, because curl_cffi is an optional dependency of the
    ``yfinance`` pipeline - importing it here would crash the process
    on older venvs that have an alternative requests backend.
    """
    name = type(exc).__name__
    if name == "CertificateVerifyError":
        return True
    text = str(exc) or ""
    return "curl: (60)" in text or "SSL certificate problem" in text


def _log_ssl_failure(area: str, *, symbol: str = "", pair: str = "") -> None:
    """Log a libcurl TLS failure once, then suppress further noise."""
    global _SSL_FAILURE_LOGGED
    with _LOCK:
        first = not _SSL_FAILURE_LOGGED
        _SSL_FAILURE_LOGGED = True
    payload = {"symbol": symbol} if symbol else {"pair": pair}
    if first:
        logger_service.log_event(
            "WARNING", "market_data", f"{area}_ssl_verify_failed",
            **payload,
            hint=(
                "libcurl could not verify the Yahoo Finance certificate. "
                "The service automatically retries via the Stooq fallback "
                "(no key required) so the Markets card should still show data. "
                "Disable 'Live market data' in Settings to silence, or fix "
                "the Windows certificate trust store to re-enable Yahoo."
            ),
        )
    else:
        logger_service.log_event(
            "DEBUG", "market_data", f"{area}_ssl_verify_failed_repeat",
            **payload,
        )


def _now() -> float:
    return time.monotonic()


def _trend_from_change(change_pct: float) -> str:
    if change_pct > 0.05:
        return "up"
    if change_pct < -0.05:
        return "down"
    return "flat"


# ---------------------------------------------------------------------------
# Stooq fallback
# ---------------------------------------------------------------------------
#
# Stooq's daily-history CSV at ``/q/d/l/?s=<symbol>&i=d`` now requires
# a (free, but per-user) API key, so we use the lighter snapshot
# endpoint instead:
#
#     https://stooq.com/q/l/?s=<symbol>&f=sd2t2ohlcv&h&e=csv
#
# It returns a single CSV row of the most recent ``Symbol,Date,Time,
# Open,High,Low,Close,Volume`` for an unauthenticated client. We
# derive ``last`` (Close), ``prev`` (Open of the same session, which
# gives us an intraday change), and a tiny 4-point sparkline from the
# OHLC columns so the Markets card still shows a trend line - it is a
# degraded but accurate "today" view instead of the 14-day history.
#
# Symbol naming differs from Yahoo's: U.S. equities take a ``.us``
# suffix (``aapl.us``), indices use lowercase tickers without the
# ``^GSPC`` style (``^spx``), and FX pairs drop the trailing ``=X``
# (``eurczk``). We translate every Yahoo symbol we know about, and
# fall back to ``<symbol>.us`` for unknown U.S. tickers as that
# covers the long tail of stocks.

_STOOQ_BASE_URL = "https://stooq.com/q/l/"
_STOOQ_TIMEOUT_SECONDS = 6.0
_STOOQ_USER_AGENT = "AIHub/1.0 (+https://github.com/) market_data fallback"

# Process-wide ``ssl.SSLContext`` reused across Stooq requests so we
# do not rebuild it on every fetch. ``certifi`` provides a CA bundle
# that works on stock Windows Python (where the OS store is empty for
# Python's own urllib).
_STOOQ_SSL_CONTEXT: Optional[ssl.SSLContext] = None
_STOOQ_CONTEXT_LOCK = threading.Lock()


def _stooq_ssl_context() -> Optional[ssl.SSLContext]:
    global _STOOQ_SSL_CONTEXT
    with _STOOQ_CONTEXT_LOCK:
        if _STOOQ_SSL_CONTEXT is not None:
            return _STOOQ_SSL_CONTEXT
        bundle = _ca_bundle_path()
        try:
            if bundle:
                _STOOQ_SSL_CONTEXT = ssl.create_default_context(cafile=bundle)
            else:
                _STOOQ_SSL_CONTEXT = ssl.create_default_context()
        except Exception as exc:
            logger_service.log_exception(
                "market_data", "stooq_ssl_context_failed", exc,
            )
            _STOOQ_SSL_CONTEXT = None
        return _STOOQ_SSL_CONTEXT


_YAHOO_TO_STOOQ: dict[str, str] = {
    # Indices.
    "^GSPC": "^spx",
    "^SPX": "^spx",
    "^IXIC": "^ndx",
    "^NDX": "^ndx",
    "^DJI": "^dji",
    "^FTSE": "^ftm",
    "^N225": "^nkx",
    "^HSI": "^hsi",
    "^STOXX50E": "^stx50",
    # Crypto (Yahoo's ``BTC-USD`` -> Stooq's ``btcusd``).
    "BTC-USD": "btcusd",
    "ETH-USD": "ethusd",
    "BTC-EUR": "btceur",
    "ETH-EUR": "etheur",
    # FX pairs (drop the ``=X`` suffix, lower-case).
    "EURUSD=X": "eurusd",
    "USDEUR=X": "usdeur",
    "EURCZK=X": "eurczk",
    "USDCZK=X": "usdczk",
    "GBPUSD=X": "gbpusd",
    "USDGBP=X": "usdgbp",
    "USDJPY=X": "usdjpy",
    "EURGBP=X": "eurgbp",
}


def _yahoo_to_stooq_symbol(symbol: str) -> Optional[str]:
    """Translate a Yahoo Finance symbol into the Stooq convention.

    Returns ``None`` when the symbol is empty. Unknown Yahoo
    symbols default to ``<symbol>.us`` (Stooq's convention for U.S.
    equities) which is correct ~80% of the time for the long tail of
    stocks - the next CSV fetch fails gracefully when wrong.
    """
    symbol = (symbol or "").strip()
    if not symbol:
        return None
    mapped = _YAHOO_TO_STOOQ.get(symbol)
    if mapped:
        return mapped
    upper = symbol.upper()
    mapped = _YAHOO_TO_STOOQ.get(upper)
    if mapped:
        return mapped
    # Already in Stooq form? Stooq uses ``.us`` / ``^spx`` / lowercase.
    if symbol.lower().endswith(".us") or symbol.startswith("^") or "=" in symbol:
        return symbol.lower().replace("=x", "")
    # Plain ticker like ``AAPL`` -> ``aapl.us``.
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9.\-]*", symbol):
        return f"{symbol.lower()}.us"
    return symbol.lower()


def _fetch_stooq_snapshot(stooq_symbol: str) -> Optional[dict[str, str]]:
    """GET the Stooq light snapshot CSV and return a column->value dict.

    Returns ``None`` on any network / parse failure. Errors are logged
    at WARNING level so the user can see why the fallback degraded.
    """
    url = (
        f"{_STOOQ_BASE_URL}?s={stooq_symbol}&f=sd2t2ohlcv&h&e=csv"
    )
    request = urllib.request.Request(
        url, headers={"User-Agent": _STOOQ_USER_AGENT},
    )
    context = _stooq_ssl_context()
    try:
        with urllib.request.urlopen(
            request, timeout=_STOOQ_TIMEOUT_SECONDS, context=context,
        ) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        logger_service.log_event(
            "WARNING", "market_data", "stooq_http_error",
            symbol=stooq_symbol, status=getattr(exc, "code", 0),
        )
        return None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger_service.log_event(
            "WARNING", "market_data", "stooq_network_error",
            symbol=stooq_symbol, error=str(exc),
        )
        return None
    except Exception as exc:
        logger_service.log_exception(
            "market_data", "stooq_fetch_failed", exc, symbol=stooq_symbol,
        )
        return None
    text = payload.decode("utf-8", errors="replace").strip()
    if not text:
        return None
    # Stooq returns plain "No data" on an unknown symbol, or the
    # "Get your apikey:" notice if the URL pattern requires a key.
    lower = text.lower()
    if lower.startswith("no data") or "apikey" in lower:
        logger_service.log_event(
            "DEBUG", "market_data", "stooq_no_unauth_data", symbol=stooq_symbol,
        )
        return None
    try:
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
    except Exception as exc:
        logger_service.log_exception(
            "market_data", "stooq_csv_parse_failed", exc, symbol=stooq_symbol,
        )
        return None
    if len(rows) < 2:
        return None
    header = [c.strip().lower() for c in rows[0]]
    values = rows[1]
    out: dict[str, str] = {}
    for idx, key in enumerate(header):
        if idx < len(values):
            out[key] = (values[idx] or "").strip()
    return out or None


def _coerce_float(text: str) -> Optional[float]:
    """Parse a Stooq numeric cell ('7506.30' or 'N/D') into a float."""
    if not text:
        return None
    cleaned = text.replace(",", "").strip()
    if not cleaned or cleaned.upper() in {"N/D", "N/A", "-"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _fetch_single_stooq(symbol: str, *, friendly_name: str = "") -> Optional[Quote]:
    """Build a :class:`Quote` from Stooq's snapshot CSV.

    Mirrors the :func:`_fetch_single` (yfinance) interface so the
    caller's cache + return-shape logic stays identical. The
    snapshot endpoint only returns one row, so the sparkline is a
    small ``[open, high, low, close]`` synthesis instead of a
    multi-day history - the Markets card still draws a trend line
    but it shows the session range rather than two weeks of data.
    Returns ``None`` when the symbol has no usable snapshot.
    """
    mapped = _yahoo_to_stooq_symbol(symbol)
    if not mapped:
        return None
    snapshot = _fetch_stooq_snapshot(mapped)
    if not snapshot:
        return None
    close = _coerce_float(snapshot.get("close", ""))
    open_ = _coerce_float(snapshot.get("open", ""))
    high = _coerce_float(snapshot.get("high", ""))
    low = _coerce_float(snapshot.get("low", ""))
    if close is None:
        return None
    last = float(close)
    prev = float(open_) if open_ is not None else last
    change_pct = (last - prev) / prev * 100.0 if prev else 0.0
    spark_candidates = [open_, low, high, close]
    spark = [float(value) for value in spark_candidates if value is not None]
    if not spark:
        spark = [last]
    logger_service.log_event(
        "INFO", "market_data", "stooq_fallback_used",
        symbol=symbol, mapped=mapped, points=len(spark),
    )
    # Clear the SSL warning so a recovered network can warn again later.
    global _SSL_FAILURE_LOGGED
    with _LOCK:
        _SSL_FAILURE_LOGGED = False
    return Quote(
        symbol=symbol,
        name=friendly_name or symbol,
        last=float(last),
        change_pct=float(change_pct),
        trend=_trend_from_change(float(change_pct)),
        spark=spark,
    )


def _fetch_fx_stooq(pair: str) -> Optional[float]:
    """Return the most recent close for a Yahoo FX pair via Stooq."""
    quote = _fetch_single_stooq(pair, friendly_name=pair)
    if quote is None:
        return None
    return float(quote.last)


def _import_yfinance():
    try:
        import yfinance  # type: ignore[import-not-found]

        return yfinance
    except ImportError:
        # Expected branch when the user is on an older venv that
        # predates the yfinance bump. The pipeline gracefully falls
        # back to mock tickers, so this is not a real ERROR - log it as
        # INFO with the cure (``pip install -r requirements.txt``) so
        # the debug log does not look like a real failure.
        logger_service.log_event(
            "INFO", "market_data", "yfinance_not_installed",
            hint="pip install -r requirements.txt",
        )
        return None
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
    global _SSL_FAILURE_LOGGED
    try:
        session = _shared_session()
        ticker = yf.Ticker(symbol, session=session) if session is not None else yf.Ticker(symbol)
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
        # Successful fetch - re-arm the SSL warning so a transient
        # outage that recovers later is allowed to log again.
        with _LOCK:
            _SSL_FAILURE_LOGGED = False
        return Quote(
            symbol=symbol,
            name=info_name or friendly_name or symbol,
            last=float(last),
            change_pct=float(change_pct),
            trend=_trend_from_change(float(change_pct)),
            spark=spark,
        )
    except Exception as exc:
        if _is_curl_ssl_error(exc):
            _log_ssl_failure("fetch_single", symbol=symbol)
            return None
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

    Fetch order per symbol:

    1. In-memory cache (60s TTL).
    2. yfinance (when available).
    3. **Stooq fallback** (CSV via ``urllib``, no API key) when
       yfinance is missing entirely or returns no data for this symbol.

    Returns an empty list when the global ``market_data_enabled``
    toggle is off, otherwise returns whatever quotes any provider
    could deliver.
    """
    if not symbols:
        return []
    if not settings_store.get_market_data_enabled():
        return []

    yf = _import_yfinance()
    hints = name_hints or {}
    now = _now()
    out: list[Quote] = []
    fallback_count = 0
    for raw_symbol in symbols:
        symbol = str(raw_symbol).strip()
        if not symbol:
            continue
        with _LOCK:
            cached = _QUOTE_CACHE.get(symbol)
        if cached and (now - cached[0]) < CACHE_TTL_SECONDS:
            out.append(cached[1])
            continue

        quote: Optional[Quote] = None
        if yf is not None:
            quote = _fetch_single(yf, symbol, friendly_name=hints.get(symbol, ""))

        if quote is None:
            quote = _fetch_single_stooq(symbol, friendly_name=hints.get(symbol, ""))
            if quote is not None:
                fallback_count += 1

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
        stooq_fallback=fallback_count,
    )
    return out


def get_fx(pair: str) -> Optional[float]:
    """Return the latest FX rate for a Yahoo currency pair.

    ``pair`` follows the Yahoo convention ``"USDCZK=X"`` /
    ``"EURUSD=X"``. Cached for 60 seconds; respects the kill-switch.
    Falls back to Stooq's CSV when yfinance is missing or fails.
    Returns ``None`` if disabled or every provider failed.
    """
    pair = (pair or "").strip()
    if not pair:
        return None
    if not settings_store.get_market_data_enabled():
        return None
    now = _now()
    with _LOCK:
        cached = _FX_CACHE.get(pair)
    if cached and (now - cached[0]) < CACHE_TTL_SECONDS:
        return cached[1]

    last: Optional[float] = None
    global _SSL_FAILURE_LOGGED
    yf = _import_yfinance()
    if yf is not None:
        try:
            session = _shared_session()
            ticker = (
                yf.Ticker(pair, session=session)
                if session is not None
                else yf.Ticker(pair)
            )
            hist = ticker.history(period="5d", interval="1d", auto_adjust=False)
            if hist is not None and not hist.empty:
                last = float(hist["Close"].iloc[-1])
                with _LOCK:
                    _SSL_FAILURE_LOGGED = False
        except Exception as exc:
            if _is_curl_ssl_error(exc):
                _log_ssl_failure("fetch_fx", pair=pair)
            else:
                logger_service.log_exception(
                    "market_data", "fetch_fx_failed", exc, pair=pair,
                )

    if last is None:
        last = _fetch_fx_stooq(pair)
        if last is not None:
            logger_service.log_event(
                "INFO", "market_data", "stooq_fallback_fx_used", pair=pair,
            )

    if last is None:
        return None

    with _LOCK:
        _FX_CACHE[pair] = (now, last)
    return last


__all__ = ["Quote", "get_quotes", "get_fx", "CACHE_TTL_SECONDS"]
