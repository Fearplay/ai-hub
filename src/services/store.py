"""Persistent run history + run-output folders.

A "run" is one AI Career analysis: candidate JSON, job spec JSON, match
analysis, and zero or more generated documents (CV, cover letter, …).

Disk layout::

    <repo-root>/outputs/
        ai_career/
            qa-engineer-gen-20260508-204231/
                summary.json
                Tailored_CV.pdf
                ...
        ai_jobs/
            qa-engineer-search-20260508-204231/
                results.html
                summary.json
        ai_finance/
            ai-finance-20260516-150100/
        ai_linkedin/
            senior-qa-engineer-20260516-152000/

    ~/AI Hub/
        history.json                    # newest-first list of run summaries

Each section calls :func:`new_run_dir` with its own ``section`` key
(matching ``src/sections/<key>/`` and the ``key=`` field of
``section.py``). See ``.cursor/rules/outputs-layout.mdc`` for the
contributor-facing convention.

Sections never construct paths by hand - they call helpers in this module
so we keep one source of truth for filesystem layout.
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.services import logger as logger_service


_LOCK = threading.Lock()


def root_dir() -> Path:
    return Path.home() / "AI Hub"


def _project_root_dir() -> Path:
    # store.py -> services -> src -> repo root
    return Path(__file__).resolve().parents[2]


def runs_dir() -> Path:
    return _project_root_dir() / "outputs"


def section_runs_dir(section: str) -> Path:
    """Return ``outputs/<section>/`` (or top-level ``outputs/`` when blank).

    ``section`` is the section key from ``src/sections/<key>/`` (and the
    ``key=`` field in ``section.py``). Sections use this to point the
    "Open outputs folder" buttons at their own subfolder, so the user
    sees only their runs without scrolling past unrelated ones.
    """
    base = runs_dir()
    section = (section or "").strip()
    if not section:
        return base
    return base / _slug_section(section)


def history_path() -> Path:
    return root_dir() / "history.json"


def ensure_dirs() -> None:
    try:
        runs_dir().mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


def _slug(text: str, max_length: int = 40) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    if not text:
        text = "run"
    return text[:max_length]


def _slug_section(section: str) -> str:
    """Sanitise a section key for use as a folder name.

    Keeps underscores (so ``ai_jobs`` -> ``ai_jobs``, mirroring
    ``src/sections/ai_jobs/``). Other punctuation collapses to dashes.
    """
    text = (section or "").strip().lower()
    text = re.sub(r"[^a-z0-9_]+", "-", text)
    text = text.strip("-_")
    return text or "run"


def new_run_dir(role: str, company: str = "", *, section: str = "") -> Path:
    """Create + return a fresh ``outputs/<section>/<slug>-<stamp>/`` folder.

    ``section`` should be the section key (e.g. ``"ai_jobs"``,
    ``"ai_career"``, ``"ai_finance"``, ``"ai_linkedin"``). When empty,
    the folder is created directly under ``outputs/`` with a WARNING
    log so contributors notice they should pass the key. Existing
    history entries that point at old top-level paths keep working
    unchanged - they store absolute paths.
    """
    ensure_dirs()
    if not (section or "").strip():
        logger_service.log_event(
            "WARNING", "store", "new_run_dir_section_missing",
            role=role, company=company,
        )
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    role_slug = _slug(role, max_length=40) if (role or "").strip() else ""
    company_slug = _slug(company, max_length=24) if (company or "").strip() else ""
    base_slug = "-".join(part for part in (role_slug, company_slug) if part) or "run"
    parent = section_runs_dir(section)
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger_service.log_exception(
            "store", "new_run_dir_parent_create_failed", exc,
            section=section, parent=str(parent),
        )
    folder = parent / f"{base_slug}-{stamp}"
    counter = 1
    while folder.exists():
        counter += 1
        folder = parent / f"{base_slug}-{stamp}-{counter}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


@dataclass
class RunSummary:
    timestamp: str
    role: str
    company: str
    overall_score: int
    folder: str
    provider: str
    model: str
    cost_usd: float
    docs: list[str] = field(default_factory=list)
    note: str = ""


def _read_history() -> list[dict[str, Any]]:
    path = history_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8")) or []
    except (OSError, json.JSONDecodeError):
        return []


def _write_history(items: list[dict[str, Any]]) -> bool:
    path = history_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        return False
    return True


def list_runs() -> list[RunSummary]:
    with _LOCK:
        raw = _read_history()
    out: list[RunSummary] = []
    for item in raw:
        try:
            out.append(RunSummary(**item))
        except TypeError:
            continue
    return out


def append_run(summary: RunSummary) -> bool:
    with _LOCK:
        items = _read_history()
        items.insert(0, asdict(summary))
        items = items[:200]
        return _write_history(items)


def write_text_file(folder: Path, filename: str, content: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / filename
    target.write_text(content, encoding="utf-8")
    return target


def write_json_file(folder: Path, filename: str, payload: Any) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / filename
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def read_run_summary(folder: str) -> Optional[dict[str, Any]]:
    path = Path(folder) / "summary.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
