"""History tab - lists every saved AI Jobs search.

Pulls rows from disk via :func:`pipeline.list_saved_runs` (which reads
the global ``~/AI Hub/history.json`` and filters by the ``ai-jobs``
note we stamp in :func:`pipeline.save_html`). Each row shows query +
location + position count + timestamp and exposes:

* **Open folder** - shells out to the OS file manager so the user can
  re-open the saved ``results.html`` in their browser.
* **Delete** - removes the run folder from disk + drops the row from
  the global history index.

Empty state copy when no run has been saved yet.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.qt.icons import Icons
from src.qt.runtime import dispatch as runtime_dispatch
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    DangerButton,
    GhostButton,
    IconLabel,
    MutedLabel,
    SubtleLabel,
    TitleLabel,
    custom_label,
    hbox,
    vbox,
)
from src.services import logger as logger_service
from src.sections.ai_jobs import pipeline
from src.sections.ai_jobs.refs import REFS
from src.sections.ai_jobs.state import STATE
from src.sections.ai_jobs.strings import s
from src.theme import Theme


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception:
        return
    request_section_refresh()


def _open_in_explorer(path: str) -> None:
    if not path or not os.path.isdir(path):
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
            "ai_jobs.tab_history", "open_in_explorer_failed", exc, path=path,
        )


def _format_timestamp(value: str) -> str:
    """Return ``YYYY-MM-DD HH:MM`` from an ISO string."""
    if not value:
        return ""
    text = str(value).replace("T", " ")
    if len(text) >= 16:
        return text[:16]
    return text


def _empty_state(theme: Theme, txt: dict) -> QWidget:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=8, margins=(40, 60, 40, 60))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    holder.setLayout(layout)
    layout.addWidget(IconLabel(Icons.HISTORY, color=theme.text_muted, size=42),
                     alignment=Qt.AlignmentFlag.AlignHCenter)
    layout.addWidget(TitleLabel(txt["history_empty_title"], theme=theme, size=16))
    desc = MutedLabel(txt["history_empty_desc"], theme=theme, size=12)
    desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(desc)
    return holder


def _row(
    theme: Theme,
    txt: dict,
    entry: dict,
    *,
    on_open: Callable[[str], None],
    on_delete: Callable[[str], None],
) -> QFrame:
    folder = entry.get("folder") or ""
    query = (entry.get("query") or "").strip() or "-"
    location = (entry.get("location") or "").strip() or "-"
    count = int(entry.get("count") or 0)
    timestamp = _format_timestamp(entry.get("timestamp") or "")

    row = QFrame()
    row.setObjectName("JobsHistoryRow")
    row.setStyleSheet(
        f"""
        QFrame#JobsHistoryRow {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        """
    )
    layout = hbox(spacing=12, margins=(16, 12, 16, 12))
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    row.setLayout(layout)

    badge = QFrame()
    badge.setFixedSize(40, 40)
    badge.setStyleSheet(f"background-color: {rgba(theme.primary, 0.16)}; border-radius: 10px;")
    bl = hbox(spacing=0, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setLayout(bl)
    bl.addWidget(IconLabel(Icons.MANAGE_SEARCH, color=theme.primary, size=20),
                 alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(badge)

    info = QFrame()
    info.setStyleSheet("background: transparent;")
    info.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    il = vbox(spacing=4, margins=(0, 0, 0, 0))
    info.setLayout(il)

    title_row = QFrame()
    title_row.setStyleSheet("background: transparent;")
    title_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    title_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    title_row.setLayout(title_layout)
    title_layout.addWidget(BodyLabel(query, theme=theme, size=13, weight=QFont.Weight.DemiBold), 1)
    if timestamp:
        title_layout.addWidget(SubtleLabel(timestamp, theme=theme, size=11))
    il.addWidget(title_row)

    meta_row = QFrame()
    meta_row.setStyleSheet("background: transparent;")
    meta_layout = hbox(spacing=12, margins=(0, 0, 0, 0))
    meta_row.setLayout(meta_layout)
    meta_layout.addWidget(MutedLabel(location, theme=theme, size=11))
    meta_layout.addWidget(custom_label(
        txt["history_count_template"].format(count=count),
        color=theme.primary, size=11, weight=QFont.Weight.DemiBold,
    ))
    meta_layout.addStretch(1)
    il.addWidget(meta_row)

    layout.addWidget(info, 1)

    actions = QFrame()
    actions.setStyleSheet("background: transparent;")
    actions_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    actions.setLayout(actions_layout)
    open_btn = GhostButton(txt["history_open_folder_btn"], theme=theme, icon=Icons.FOLDER_OPEN)
    open_btn.clicked.connect(lambda _checked=False: on_open(folder))
    actions_layout.addWidget(open_btn)
    delete_btn = DangerButton(txt["history_delete_btn"], theme=theme, icon=Icons.DELETE_OUTLINE)
    delete_btn.clicked.connect(lambda _checked=False: on_delete(folder))
    actions_layout.addWidget(delete_btn)
    layout.addWidget(actions)

    return row


def build_history_tab(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    body_holder = QWidget()
    body_holder.setStyleSheet(f"background-color: {theme.bg};")
    body_layout = vbox(spacing=14, margins=(24, 18, 24, 18))
    body_holder.setLayout(body_layout)

    header = QFrame()
    header.setStyleSheet("background: transparent;")
    header_layout = hbox(spacing=12, margins=(0, 0, 0, 0))
    header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    header.setLayout(header_layout)
    title_holder = QFrame()
    title_holder.setStyleSheet("background: transparent;")
    title_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    title_holder.setLayout(title_layout)
    title_layout.addWidget(TitleLabel(txt["history_title"], theme=theme, size=18, weight=QFont.Weight.Bold))
    title_layout.addWidget(MutedLabel(txt["history_subtitle"], theme=theme, size=12))
    header_layout.addWidget(title_holder, 1)
    refresh_btn = GhostButton(txt["history_refresh_btn"], theme=theme, icon=Icons.REFRESH)
    header_layout.addWidget(refresh_btn)
    body_layout.addWidget(header)

    try:
        entries = pipeline.list_saved_runs()
    except Exception as exc:
        logger_service.log_exception(
            "ai_jobs.tab_history", "list_saved_runs_failed", exc,
        )
        entries = []
    STATE.runs_history = entries

    if not entries:
        body_layout.addWidget(_empty_state(theme, txt), 1)
    else:
        def _open(folder: str) -> None:
            _open_in_explorer(folder)

        def _delete(folder: str) -> None:
            ok = pipeline.delete_run(folder)
            if not ok:
                logger_service.log_event(
                    "WARNING", "ai_jobs.tab_history", "delete_partial",
                    folder=folder,
                )
            runtime_dispatch(_request_full_refresh)

        for entry in entries:
            body_layout.addWidget(_row(theme, txt, entry, on_open=_open, on_delete=_delete))
        body_layout.addStretch(1)

    refresh_btn.clicked.connect(lambda _checked=False: _request_full_refresh())

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(body_holder)
    layout.addWidget(scroll, 1)
    return container
