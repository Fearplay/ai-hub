"""Persistent run history + run-output folders.

A "run" is one AI Career analysis: candidate JSON, job spec JSON, match
analysis, and zero or more generated documents (CV, cover letter, …).

Disk layout::

    <repo-root>/outputs/
        qa-engineer-20260508-204231/
            summary.json
            Tailored_CV.pdf
            ...

    ~/AI Hub/
        history.json                    # newest-first list of run summaries

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


_LOCK = threading.Lock()


def root_dir() -> Path:
    return Path.home() / "AI Hub"


def _project_root_dir() -> Path:
    # store.py -> services -> src -> repo root
    return Path(__file__).resolve().parents[2]


def runs_dir() -> Path:
    return _project_root_dir() / "outputs"


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


def new_run_dir(role: str) -> Path:
    ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    role_slug = _slug(role, max_length=60)
    if role_slug:
        folder = runs_dir() / f"{role_slug}-{stamp}"
    else:
        folder = runs_dir() / f"run-{stamp}"
    counter = 1
    while folder.exists():
        counter += 1
        if role_slug:
            folder = runs_dir() / f"{role_slug}-{stamp}-{counter}"
        else:
            folder = runs_dir() / f"run-{stamp}-{counter}"
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
