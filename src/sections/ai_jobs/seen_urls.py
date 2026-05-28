"""Cross-run "seen URLs" sidecar for AI Job Search.

The pipeline already de-duplicates within a single run. This module adds
*cross-run* memory so we can tag each posting as ``new`` (never surfaced
before for this search) or ``seen`` (shown in an earlier run), and let
the user filter to "new since last run".

State lives in ``~/AI Hub/jobs_seen_urls.json`` keyed by a slug derived
from the search keywords (there is no persistent saved-profile id loaded
into ``STATE``, so the keyword slug is the most meaningful key: re-running
the same query compares against that query's previous runs).

Shape::

    {
      "version": 1,
      "profiles": {
        "qa-engineer": {"urls": ["https://...", ...], "updated_at": "..."}
      }
    }

URLs are normalised (scheme forced to https, ``www.`` stripped, trailing
slash removed, fragment dropped, query KEPT because job-board postings
frequently carry the job id in the query string) so trivial variants of
the same posting collapse to one key.
"""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from src.services import logger as logger_service
from src.services import store

_LOCK = threading.RLock()
_VERSION = 1


def _path() -> Path:
    return store.root_dir() / "jobs_seen_urls.json"


def normalize_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
    except ValueError:
        return raw.lower().rstrip("/")
    if not parsed.scheme or not parsed.netloc:
        return raw.lower().rstrip("/")
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path.rstrip("/")
    # Keep the query (job ids live there on LinkedIn / Indeed); drop the
    # fragment and force https so http/https variants collapse.
    return urlunparse(("https", netloc, path, "", parsed.query, "")).lower()


def profile_key(keywords: str) -> str:
    """Stable slug used as the per-search bucket key."""
    base = re.sub(r"[^a-z0-9]+", "-", (keywords or "").strip().lower()).strip("-")
    return base[:60] or "default"


def _read() -> dict:
    p = _path()
    if not p.exists():
        return {"version": _VERSION, "profiles": {}}
    try:
        with _LOCK:
            data = json.loads(p.read_text(encoding="utf-8")) or {}
    except (OSError, json.JSONDecodeError) as exc:
        logger_service.log_exception("ai_jobs.seen_urls", "read_failed", exc)
        return {"version": _VERSION, "profiles": {}}
    if not isinstance(data.get("profiles"), dict):
        data["profiles"] = {}
    return data


def _write(data: dict) -> None:
    p = _path()
    try:
        with _LOCK:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        logger_service.log_exception("ai_jobs.seen_urls", "write_failed", exc)


def load_seen(key: str) -> set[str]:
    """Return the set of normalised URLs already seen for ``key``."""
    entry = _read().get("profiles", {}).get(key) or {}
    return {u for u in (entry.get("urls") or []) if u}


def record_seen(key: str, urls: list[str]) -> int:
    """Union ``urls`` (normalised) into the seen-set for ``key``.

    Returns the number of URLs that were newly added (i.e. had never
    been recorded for this key before).
    """
    incoming = {normalize_url(u) for u in (urls or []) if u}
    incoming = {u for u in incoming if u}
    if not incoming:
        return 0
    with _LOCK:
        data = _read()
        profiles = data.setdefault("profiles", {})
        entry = profiles.setdefault(key, {"urls": [], "updated_at": ""})
        existing = {u for u in (entry.get("urls") or []) if u}
        added = len(incoming - existing)
        entry["urls"] = sorted(existing | incoming)
        entry["updated_at"] = datetime.now().isoformat(timespec="seconds")
        data["version"] = _VERSION
        _write(data)
    logger_service.log_event(
        "INFO", "ai_jobs.seen_urls", "record_done",
        key=key, added=added, total=len(entry["urls"]),
    )
    return added
