"""Right-hand context panel for the Dashboard.

Unlike the per-AI sections, the dashboard panel is read-only and aggregates
data that already exists app-wide:

* **Activity** - the most recent saved runs across every section
  (``store.list_runs()``), each row jumping back into its section.
* **Session cost** - the live in-memory :data:`COST` singleton (calls,
  input/output tokens, total dollar estimate).
* **Quick actions** - continue the last run, open the outputs folder,
  jump to Settings.

No AI / network calls happen here, mirroring the navigation-only nature
of the dashboard itself.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QSizePolicy, QWidget

from src.components.context_panel import context_panel_shell, quick_action_row
from src.components.section_card import section_card
from src.qt.icons import Icons
from src.qt.theme import rgba
from src.qt.widgets import (
    ElidedLabel,
    IconLabel,
    MutedLabel,
    custom_label,
    hbox,
    vbox,
    wrap_label_slot,
)
from src.sections._base import Section
from src.sections.dashboard.strings import s
from src.services import logger as logger_service
from src.services import store
from src.services.cost_tracker import COST
from src.theme import Theme


def _open_path(path: str) -> None:
    if not path:
        return
    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as exc:
        logger_service.log_exception(
            "dashboard.context", "open_path_failed", exc, path=path,
        )


def _open_section_key(key: str) -> None:
    try:
        from src.app import get_active_window
    except Exception as exc:
        logger_service.log_exception(
            "dashboard.context", "open_section_import_failed", exc, key=key,
        )
        return
    window = get_active_window()
    if window is None:
        return
    try:
        window.set_section(key)
    except Exception as exc:
        logger_service.log_exception(
            "dashboard.context", "open_section_failed", exc, key=key,
        )


def _open_outputs_folder() -> None:
    try:
        store.ensure_dirs()
        path = str(store.runs_dir())
    except Exception as exc:
        logger_service.log_exception("dashboard.context", "outputs_dir_failed", exc)
        return
    _open_path(path)


def _section_for_run(summary: store.RunSummary) -> Optional[Section]:
    """Resolve which section produced a saved run.

    Prefers the stamped ``note`` (normalising ``ai-jobs`` -> ``ai_jobs``)
    and falls back to parsing ``outputs/<key>/`` out of the folder path
    for older history rows.
    """
    from src.sections import SECTION_BY_KEY

    note = (getattr(summary, "note", "") or "").strip().lower().replace("-", "_")
    section = SECTION_BY_KEY.get(note)
    if section is not None:
        return section
    folder = (getattr(summary, "folder", "") or "").replace("\\", "/").lower()
    for key, sec in SECTION_BY_KEY.items():
        if f"/outputs/{key}/" in folder:
            return sec
    return None


def _relative_time(timestamp: str, txt: dict) -> str:
    raw = (timestamp or "").strip()
    if not raw:
        return ""
    parsed: Optional[datetime] = None
    try:
        parsed = datetime.fromisoformat(raw.replace("T", " ").split(".")[0])
    except ValueError:
        try:
            parsed = datetime.strptime(raw.replace("T", " ")[:16], "%Y-%m-%d %H:%M")
        except ValueError:
            return raw[:16]
    secs = max(0, int((datetime.now() - parsed).total_seconds()))
    if secs < 60:
        return txt["time_just_now"]
    mins = secs // 60
    if mins < 60:
        return txt["time_min_ago"].format(n=mins)
    hours = mins // 60
    if hours < 24:
        return txt["time_hours_ago"].format(n=hours)
    return txt["time_days_ago"].format(n=hours // 24)


def _activity_row(theme: Theme, lang: str, summary: store.RunSummary, txt: dict) -> QFrame:
    section = _section_for_run(summary)
    accent = section.accent if (section and section.accent) else theme.primary
    icon_name = section.icon if section else Icons.HISTORY
    sec_label = section.label(lang) if section else ""
    title = (
        (summary.role or "").strip()
        or (summary.company or "").strip()
        or sec_label
        or "—"
    )
    time_text = _relative_time(summary.timestamp, txt)

    from src.qt.widgets import ClickFrame

    row = ClickFrame()
    row.setStyleSheet(
        f"""
        ClickFrame {{ background-color: transparent; border-radius: 10px; }}
        ClickFrame:hover {{ background-color: {theme.surface_2}; }}
        """
    )
    if section is not None:
        row.clicked.connect(lambda key=section.key: _open_section_key(key))
    layout = hbox(spacing=10, margins=(6, 8, 6, 8))
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    row.setLayout(layout)

    icon_box = QFrame()
    icon_box.setFixedSize(34, 34)
    icon_box.setStyleSheet(
        f"background-color: {rgba(accent, 0.16)}; border-radius: 9px;"
    )
    ib = hbox(spacing=0, margins=(0, 0, 0, 0))
    ib.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setLayout(ib)
    ib.addWidget(
        IconLabel(icon_name, color=accent, size=18),
        alignment=Qt.AlignmentFlag.AlignCenter,
    )
    layout.addWidget(icon_box)

    text_holder = QFrame()
    text_holder.setStyleSheet("background: transparent;")
    text_holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    tl = vbox(spacing=1, margins=(0, 0, 0, 0))
    text_holder.setLayout(tl)
    tl.addWidget(
        ElidedLabel(
            title,
            color=theme.text,
            size=12,
            weight=QFont.Weight.DemiBold,
            mode=Qt.TextElideMode.ElideRight,
        )
    )
    if sec_label:
        tl.addWidget(
            ElidedLabel(
                sec_label,
                color=theme.text_muted,
                size=11,
                mode=Qt.TextElideMode.ElideRight,
            )
        )
    layout.addWidget(text_holder, 1)

    if time_text:
        layout.addWidget(MutedLabel(time_text, theme=theme, size=11))
    return row


def _activity_card(theme: Theme, lang: str, txt: dict) -> QWidget:
    body = QFrame()
    body.setStyleSheet("background: transparent;")
    bl = vbox(spacing=2, margins=(0, 0, 0, 0))
    body.setLayout(bl)
    try:
        runs = store.list_runs()[:6]
    except Exception as exc:
        logger_service.log_exception("dashboard.context", "list_runs_failed", exc)
        runs = []
    if not runs:
        empty = MutedLabel(txt["activity_empty"], theme=theme, size=12)
        wrap_label_slot(empty)
        bl.addWidget(empty)
    else:
        for run in runs:
            bl.addWidget(_activity_row(theme, lang, run, txt))
    return section_card(
        theme,
        icon=Icons.TIMELINE,
        title=txt["activity_title"],
        description=txt["activity_subtitle"],
        body=body,
    )


def _metric_row(theme: Theme, label: str, value: str, *, accent: bool = False) -> QFrame:
    row = QFrame()
    row.setStyleSheet("background: transparent;")
    rl = hbox(spacing=10, margins=(0, 0, 0, 0))
    rl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    row.setLayout(rl)
    lab = MutedLabel(label, theme=theme, size=12)
    wrap_label_slot(lab)
    rl.addWidget(lab, 1)
    rl.addWidget(
        custom_label(
            value,
            color=theme.primary if accent else theme.text,
            size=13,
            weight=QFont.Weight.Bold,
        )
    )
    return row


def _cost_card(theme: Theme, txt: dict) -> QWidget:
    body = QFrame()
    body.setStyleSheet("background: transparent;")
    bl = vbox(spacing=8, margins=(0, 0, 0, 0))
    body.setLayout(bl)

    def _fmt(n: int) -> str:
        return f"{int(n):,}".replace(",", " ")

    bl.addWidget(_metric_row(theme, txt["cost_calls"], str(COST.calls)))
    bl.addWidget(_metric_row(theme, txt["cost_tokens_in"], _fmt(COST.tokens_in)))
    bl.addWidget(_metric_row(theme, txt["cost_tokens_out"], _fmt(COST.tokens_out)))
    bl.addWidget(
        _metric_row(theme, txt["cost_total"], f"${COST.cost_usd:.2f}", accent=True)
    )
    return section_card(
        theme,
        icon=Icons.PAYMENTS_OUTLINED,
        title=txt["cost_title"],
        body=body,
    )


def _quick_actions_card(theme: Theme, lang: str, txt: dict) -> QWidget:
    body = QFrame()
    body.setStyleSheet("background: transparent;")
    bl = vbox(spacing=2, margins=(0, 0, 0, 0))
    body.setLayout(bl)

    last_section: Optional[Section] = None
    try:
        runs = store.list_runs()
        if runs:
            last_section = _section_for_run(runs[0])
    except Exception as exc:
        logger_service.log_exception("dashboard.context", "quick_last_run_failed", exc)

    if last_section is not None:
        last_row = quick_action_row(theme, Icons.HISTORY, txt["qa_last_run"])
        last_row.clicked.connect(
            lambda key=last_section.key: _open_section_key(key)
        )
        bl.addWidget(last_row)

    out_row = quick_action_row(theme, Icons.FOLDER_OPEN, txt["qa_outputs"])
    out_row.clicked.connect(lambda: _open_outputs_folder())
    bl.addWidget(out_row)

    settings_row = quick_action_row(theme, Icons.SETTINGS_OUTLINED, txt["qa_settings"])
    settings_row.clicked.connect(lambda: _open_section_key("settings"))
    bl.addWidget(settings_row)

    return section_card(
        theme,
        icon=Icons.BOLT_OUTLINED,
        title=txt["quick_actions_title"],
        body=body,
    )


def build_context(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    try:
        cards = [
            _activity_card(theme, lang, txt),
            _cost_card(theme, txt),
            _quick_actions_card(theme, lang, txt),
        ]
    except Exception as exc:
        logger_service.log_exception("dashboard.context", "build_context_failed", exc)
        raise
    return context_panel_shell(theme, *cards)
