"""History tab - lists every saved AI Bug Report run.

Pulls rows from disk via :func:`pipeline.list_saved_runs` (which reads
``~/AI Hub/history.json`` and filters by the ``ai_bug_report`` note we
stamp in :func:`pipeline.save_bug_report_docx`). Each row shows the
report title + severity / priority chips + screenshot count + timestamp
and exposes:

* **Open Word** - launches the saved ``.docx`` in the user's default
  Word handler when the file still exists on disk.
* **Open folder** - shells out to the OS file manager so the user can
  grab the .docx / .md / summary.json directly.
* **Delete** - removes the run folder from disk + drops the row from
  the global history index.

Empty state copy when no run has been saved yet so the tab never
renders as an empty rectangle.
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
    ClickFrame,
    FlowLayout,
    GhostButton,
    IconLabel,
    IconOnlyButton,
    MutedLabel,
    Pill,
    TitleLabel,
    hbox,
    vbox,
    wrap_label_slot,
)
from src.services import logger as logger_service
from src.sections.ai_bug_report import pipeline
from src.sections.ai_bug_report.refs import REFS
from src.sections.ai_bug_report.state import STATE, TAB_PREVIEW
from src.sections.ai_bug_report.strings import (
    priority_label,
    reproducibility_label,
    s,
    severity_label,
)
from src.theme import Theme


_SEVERITY_COLORS: dict[str, str] = {
    "Critical": "#B91C1C",
    "High": "#DC2626",
    "Medium": "#D97706",
    "Low": "#059669",
}


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception as exc:
        logger_service.log_exception(
            "ai_bug_report.tab_history", "request_full_refresh_import_failed", exc,
        )
        return
    try:
        request_section_refresh()
    except Exception as exc:
        logger_service.log_exception(
            "ai_bug_report.tab_history", "request_full_refresh_failed", exc,
        )


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
            "ai_bug_report.tab_history", "open_in_explorer_failed", exc, path=path,
        )


def _open_word_file(path: str) -> None:
    if not path or not os.path.isfile(path):
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
            "ai_bug_report.tab_history", "open_word_failed", exc, path=path,
        )


def _format_timestamp(value: str) -> str:
    """Return ``YYYY-MM-DD HH:MM`` from a stored timestamp string."""
    if not value:
        return ""
    text = str(value).replace("T", " ")
    if len(text) >= 16:
        return text[:16]
    return text


def _attachment_summary(txt: dict, image_count: int, doc_count: int) -> str:
    """Render an attachment-count chip label like '3 screenshots, 1 document'."""
    if image_count <= 0 and doc_count <= 0:
        return txt["history_count_zero"]
    parts: list[str] = []
    if image_count == 1:
        parts.append(txt["history_count_one"])
    elif image_count > 1:
        parts.append(txt["history_count_template"].format(count=image_count))
    if doc_count > 0:
        # Reuse template / one based on doc_count to stay localised.
        if doc_count == 1:
            parts.append(txt["history_doc_count_one"])
        else:
            parts.append(txt["history_doc_count_template"].format(count=doc_count))
    return ", ".join(parts) if parts else txt["history_count_zero"]


def _empty_state(theme: Theme, txt: dict) -> QWidget:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=8, margins=(40, 60, 40, 60))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    holder.setLayout(layout)
    layout.addWidget(
        IconLabel(Icons.HISTORY, color=theme.text_muted, size=42),
        alignment=Qt.AlignmentFlag.AlignHCenter,
    )
    title_label = TitleLabel(txt["history_empty_title"], theme=theme, size=16)
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title_label)
    desc = MutedLabel(txt["history_empty_desc"], theme=theme, size=12)
    desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
    desc.setMaximumWidth(520)
    layout.addWidget(desc, alignment=Qt.AlignmentFlag.AlignHCenter)
    return holder


def _row(
    theme: Theme,
    txt: dict,
    lang: str,
    entry: dict,
    *,
    on_open_folder: Callable[[str], None],
    on_open_app: Callable[[str], None],
    on_open_word: Callable[[str], None],
    on_delete: Callable[[str], None],
) -> QFrame:
    folder = entry.get("folder") or ""
    title = (entry.get("title") or "").strip() or txt.get("preview_empty", "Bug report")
    timestamp = _format_timestamp(entry.get("timestamp") or "")
    severity = (entry.get("severity") or "").strip()
    priority = (entry.get("priority") or "").strip()
    reproducibility = (entry.get("reproducibility") or "").strip()
    image_count = int(entry.get("image_count") or 0)
    doc_count = int(entry.get("doc_count") or 0)
    docs: list[str] = list(entry.get("docs") or [])
    word_path = ""
    if docs and folder:
        candidate = os.path.join(folder, docs[0])
        if os.path.isfile(candidate):
            word_path = candidate

    row = ClickFrame()
    row.setObjectName("BugReportHistoryRow")
    row.clicked.connect(lambda _checked=False, f=folder: on_open_app(f))
    row.setStyleSheet(
        f"""
        QFrame#BugReportHistoryRow {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        QFrame#BugReportHistoryRow:hover {{
            border: 1px solid {rgba(theme.primary, 0.45)};
        }}
        """
    )
    layout = hbox(spacing=14, margins=(16, 14, 14, 14))
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    row.setLayout(layout)

    # Left: accent "bug" badge.
    badge = QFrame()
    badge.setFixedSize(40, 40)
    badge.setStyleSheet(
        f"background-color: {rgba(theme.primary, 0.16)}; border-radius: 10px;"
    )
    bl = hbox(spacing=0, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setLayout(bl)
    bl.addWidget(
        IconLabel(Icons.BUG_REPORT_OUTLINED, color=theme.primary, size=20),
        alignment=Qt.AlignmentFlag.AlignCenter,
    )
    layout.addWidget(badge)

    # Middle: title on its own line, severity chips, then a single muted
    # meta line (timestamp + attachment summary). Keeping each concern on
    # its own row stops the long Czech titles from fighting the timestamp
    # for width and lets the card breathe.
    info = QFrame()
    info.setStyleSheet("background: transparent;")
    wrap_label_slot(info)
    il = vbox(spacing=6, margins=(0, 0, 0, 0))
    info.setLayout(il)

    il.addWidget(
        BodyLabel(title, theme=theme, size=14, weight=QFont.Weight.DemiBold)
    )

    if severity or priority or reproducibility:
        chips_row = QFrame()
        chips_row.setStyleSheet("background: transparent;")
        wrap_label_slot(chips_row)
        chips_layout = FlowLayout(chips_row, margin=0, h_spacing=6, v_spacing=6)
        chips_row.setLayout(chips_layout)
        if severity:
            chips_layout.addWidget(
                Pill(
                    text=severity_label(lang, severity).upper(),
                    bg=_SEVERITY_COLORS.get(severity, theme.primary),
                    fg="#FFFFFF",
                )
            )
        if priority:
            chips_layout.addWidget(
                Pill(
                    text=priority_label(lang, priority),
                    bg=theme.surface_2,
                    fg=theme.text,
                )
            )
        if reproducibility:
            chips_layout.addWidget(
                Pill(
                    text=reproducibility_label(lang, reproducibility),
                    bg=theme.surface_2,
                    fg=theme.text_muted,
                )
            )
        il.addWidget(chips_row)

    meta_bits = [
        bit
        for bit in (timestamp, _attachment_summary(txt, image_count, doc_count))
        if bit
    ]
    if meta_bits:
        meta_label = MutedLabel("  ·  ".join(meta_bits), theme=theme, size=11)
        wrap_label_slot(meta_label)
        il.addWidget(meta_label)

    layout.addWidget(info, 1)

    # Right: compact icon-only actions (tooltips carry the labels) instead
    # of three stacked full-text buttons that crowded the card before.
    actions = QFrame()
    actions.setStyleSheet("background: transparent;")
    actions.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
    actions_layout = hbox(spacing=4, margins=(0, 0, 0, 0))
    actions_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    actions.setLayout(actions_layout)
    if word_path:
        word_btn = IconOnlyButton(
            Icons.DESCRIPTION_OUTLINED,
            color=theme.text_muted,
            size=18,
            bg_hover=theme.surface_2,
            tooltip=txt["history_open_word_btn"],
        )
        word_btn.clicked.connect(lambda _checked=False, p=word_path: on_open_word(p))
        actions_layout.addWidget(word_btn)
    open_btn = IconOnlyButton(
        Icons.FOLDER_OPEN,
        color=theme.text_muted,
        size=18,
        bg_hover=theme.surface_2,
        tooltip=txt["history_open_folder_btn"],
    )
    open_btn.clicked.connect(lambda _checked=False: on_open_folder(folder))
    actions_layout.addWidget(open_btn)
    delete_btn = IconOnlyButton(
        Icons.DELETE_OUTLINE,
        color="#EF4444",
        size=18,
        bg_hover=rgba("#EF4444", 0.12),
        tooltip=txt["history_delete_btn"],
    )
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
    header_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    header.setLayout(header_layout)
    title_holder = QFrame()
    title_holder.setStyleSheet("background: transparent;")
    wrap_label_slot(title_holder)
    title_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    title_holder.setLayout(title_layout)
    title_layout.addWidget(
        TitleLabel(
            txt["history_title"], theme=theme, size=18, weight=QFont.Weight.Bold,
        )
    )
    subtitle_label = MutedLabel(txt["history_subtitle"], theme=theme, size=12)
    subtitle_label.setMinimumHeight(subtitle_label.fontMetrics().lineSpacing() * 2 + 4)
    wrap_label_slot(subtitle_label)
    title_layout.addWidget(subtitle_label)
    header_layout.addWidget(title_holder, 1)
    refresh_btn = GhostButton(
        txt["history_refresh_btn"], theme=theme, icon=Icons.REFRESH,
    )
    refresh_btn.clicked.connect(lambda _checked=False: _request_full_refresh())
    header_layout.addWidget(refresh_btn)
    body_layout.addWidget(header)

    try:
        entries = pipeline.list_saved_runs()
    except Exception as exc:
        logger_service.log_exception(
            "ai_bug_report.tab_history", "list_saved_runs_failed", exc,
        )
        entries = []
    STATE.runs_history = entries
    REFS.request_context_refresh()

    if not entries:
        body_layout.addWidget(_empty_state(theme, txt), 1)
    else:
        def _open_folder(folder: str) -> None:
            _open_in_explorer(folder)

        def _open_word(path: str) -> None:
            _open_word_file(path)

        def _open_app(folder: str) -> None:
            try:
                ok = pipeline.restore_run(folder)
            except Exception as exc:
                logger_service.log_exception(
                    "ai_bug_report.tab_history", "restore_run_failed", exc,
                    folder=folder,
                )
                ok = False
            if ok:
                STATE.active_tab = TAB_PREVIEW
                REFS.request_context_refresh()
                runtime_dispatch(_request_full_refresh)

        def _delete(folder: str) -> None:
            try:
                ok = pipeline.delete_run(folder)
            except Exception as exc:
                logger_service.log_exception(
                    "ai_bug_report.tab_history", "delete_run_failed", exc,
                    folder=folder,
                )
                ok = False
            if not ok:
                logger_service.log_event(
                    "WARNING", "ai_bug_report.tab_history", "delete_partial",
                    folder=folder,
                )
            runtime_dispatch(_request_full_refresh)

        for entry in entries:
            body_layout.addWidget(
                _row(
                    theme, txt, lang, entry,
                    on_open_folder=_open_folder,
                    on_open_app=_open_app,
                    on_open_word=_open_word,
                    on_delete=_delete,
                )
            )
        body_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(
        f"QScrollArea {{ background-color: {theme.bg}; border: none; }}"
    )
    scroll.setWidget(body_holder)
    layout.addWidget(scroll, 1)
    return container
