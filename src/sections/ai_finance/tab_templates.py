"""Templates / Outputs tab for AI Finance.

Replaces the original mock four-card placeholder with a real grid of
the user's saved analyses, sourced from
``outputs/ai_finance/<run-slug>-<stamp>/`` (per
``outputs-layout.mdc``). Each card shows the run timestamp + the doc
files it produced and exposes "Open folder" so the user can grab the
PDF / Markdown they exported.

When no run has been saved yet we fall back to a hint card explaining
where exports land - never to a fictional template grid, because the
mock cards confused users into thinking the section already runs
without their input.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.qt.icons import Icons
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    GhostButton,
    IconLabel,
    MutedLabel,
    PrimaryButton,
    SubtleLabel,
    TitleLabel,
    hbox,
    vbox,
    wrap_label_slot,
)
from src.services import logger as logger_service
from src.services import store
from src.sections.ai_finance.state import STATE, TAB_BUDGET
from src.sections.ai_finance.strings import s
from src.theme import Theme


def _open_in_explorer(path: str) -> None:
    """Open ``path`` in the OS file explorer.

    Mirrors the helper used by AI Jobs / AI Career so all sections
    behave identically when the user clicks "Open folder".
    """
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as exc:
        logger_service.log_exception(
            "ai_finance.tab_templates", "open_in_explorer_failed", exc, path=path,
        )


def _list_runs() -> list[dict]:
    """Return a sorted list of existing AI Finance runs from disk.

    Each entry is a small dict with ``folder``, ``name``, ``timestamp``,
    ``files``. The list is sorted newest-first by directory mtime so
    the most recent run appears in the top-left tile.
    """
    section_dir = store.section_runs_dir("ai_finance")
    if not section_dir.exists():
        return []
    entries: list[dict] = []
    try:
        for child in section_dir.iterdir():
            if not child.is_dir():
                continue
            try:
                stat = child.stat()
            except OSError:
                continue
            files: list[str] = []
            try:
                for f in sorted(child.iterdir()):
                    if f.is_file() and f.suffix.lower() in {".pdf", ".docx", ".md", ".html"}:
                        files.append(f.name)
            except OSError:
                pass
            try:
                ts = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            except Exception:
                ts = ""
            entries.append({
                "folder": str(child),
                "name": child.name,
                "timestamp": ts,
                "mtime": stat.st_mtime,
                "files": files,
            })
    except OSError as exc:
        logger_service.log_exception(
            "ai_finance.tab_templates", "list_runs_failed", exc,
        )
        return []
    entries.sort(key=lambda r: r.get("mtime", 0.0), reverse=True)
    return entries


def _hero_card(theme: Theme, *, icon: str, title: str, description: str) -> QFrame:
    card = QFrame()
    card.setStyleSheet(
        f"""
        QFrame {{
            background-color: {rgba(theme.primary_tint, 0.35)};
            border: 1px solid {rgba(theme.primary, 0.35)};
            border-radius: 12px;
        }}
        """
    )
    layout = hbox(spacing=14, margins=(16, 16, 16, 16))
    card.setLayout(layout)

    icon_box = QFrame()
    icon_box.setFixedSize(44, 44)
    icon_box.setStyleSheet(f"background-color: {theme.primary}; border-radius: 12px;")
    icon_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setLayout(icon_layout)
    icon_layout.addWidget(
        IconLabel(icon, color="#FFFFFF", size=20),
        alignment=Qt.AlignmentFlag.AlignCenter,
    )
    layout.addWidget(icon_box)

    text_holder = QFrame()
    text_holder.setStyleSheet("background: transparent;")
    text_holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    wrap_label_slot(text_holder)
    text_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    text_holder.setLayout(text_layout)
    text_layout.addWidget(TitleLabel(title, theme=theme, size=15))
    text_layout.addWidget(MutedLabel(description, theme=theme, size=12))
    layout.addWidget(text_holder, 1)
    return card


def _run_card(theme: Theme, lang: str, run: dict) -> QFrame:
    txt = s(lang)
    card = QFrame()
    card.setStyleSheet(
        f"""
        QFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        """
    )
    card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
    layout = vbox(spacing=8, margins=(16, 14, 16, 14))
    card.setLayout(layout)

    head = QFrame()
    head.setStyleSheet("background: transparent;")
    head_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    head_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    head.setLayout(head_layout)
    icon_holder = QFrame()
    icon_holder.setFixedSize(36, 36)
    icon_holder.setStyleSheet(
        f"background-color: {rgba(theme.primary, 0.16)}; border-radius: 10px;"
    )
    ih_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    ih_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_holder.setLayout(ih_layout)
    ih_layout.addWidget(
        IconLabel(Icons.FOLDER_OPEN, color=theme.primary, size=16),
        alignment=Qt.AlignmentFlag.AlignCenter,
    )
    head_layout.addWidget(icon_holder)

    text_holder = QFrame()
    text_holder.setStyleSheet("background: transparent;")
    text_holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    wrap_label_slot(text_holder)
    text_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    text_holder.setLayout(text_layout)
    text_layout.addWidget(BodyLabel(run.get("name", ""), theme=theme, size=13))
    text_layout.addWidget(SubtleLabel(run.get("timestamp", ""), theme=theme, size=11, italic=True))
    head_layout.addWidget(text_holder, 1)
    layout.addWidget(head)

    files = run.get("files") or []
    if files:
        files_holder = QFrame()
        files_holder.setStyleSheet("background: transparent;")
        files_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
        files_holder.setLayout(files_layout)
        for name in files[:6]:
            files_layout.addWidget(MutedLabel(name, theme=theme, size=11))
        if len(files) > 6:
            files_layout.addWidget(
                MutedLabel(f"+{len(files) - 6} more", theme=theme, size=11)
            )
        layout.addWidget(files_holder)

    btn_row = QFrame()
    btn_row.setStyleSheet("background: transparent;")
    btn_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    btn_row.setLayout(btn_layout)
    btn_layout.addStretch(1)
    open_btn = GhostButton(txt["templates_open_folder"], theme=theme, icon=Icons.FOLDER_OPEN)
    folder = run.get("folder", "")
    open_btn.clicked.connect(lambda: _open_in_explorer(folder))
    btn_layout.addWidget(open_btn)
    layout.addWidget(btn_row)
    return card


def _empty_card(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    card = QFrame()
    card.setStyleSheet(
        f"""
        QFrame {{
            background-color: {theme.surface};
            border: 1px dashed {theme.border};
            border-radius: 12px;
        }}
        """
    )
    layout = vbox(spacing=10, margins=(20, 24, 20, 24))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    card.setLayout(layout)
    layout.addWidget(
        IconLabel(Icons.FOLDER_OPEN, color=theme.text_muted, size=24),
        alignment=Qt.AlignmentFlag.AlignHCenter,
    )
    title_label = TitleLabel(txt["templates_empty_title"], theme=theme, size=14)
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)
    body_label = MutedLabel(txt["templates_empty_body"], theme=theme, size=12)
    body_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(body_label, alignment=Qt.AlignmentFlag.AlignHCenter)
    btn = PrimaryButton(txt["templates_create_btn"], theme=theme, icon=Icons.PIE_CHART_OUTLINE)
    btn.clicked.connect(lambda: _start_first_run())
    layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
    return card


def _start_first_run() -> None:
    """Jump the user to the Budget tab (first paid pipeline)."""
    STATE.active_tab = TAB_BUDGET
    try:
        from src.app import request_section_refresh

        request_section_refresh()
    except Exception as exc:
        logger_service.log_exception(
            "ai_finance.tab_templates", "start_first_run_failed", exc,
        )


def build_templates_tab(theme: Theme, lang: str) -> QWidget:
    """Render the Templates tab.

    Returns either an empty-state hint or a responsive grid of run
    cards. Wrapped in a ``QScrollArea`` so long lists do not overflow
    the tab body height.
    """
    txt = s(lang)
    page = QWidget()
    page.setStyleSheet(f"background-color: {theme.bg};")
    outer = vbox(spacing=18, margins=(24, 20, 24, 24))
    page.setLayout(outer)

    outer.addWidget(
        _hero_card(
            theme,
            icon=Icons.GRID_VIEW_OUTLINED,
            title=txt["templates_title"],
            description=txt["templates_desc"],
        )
    )

    runs = _list_runs()
    if not runs:
        outer.addWidget(_empty_card(theme, lang))
        outer.addStretch(1)
    else:
        grid_holder = QFrame()
        grid_holder.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_holder)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        cols = 2
        for i, run in enumerate(runs):
            grid.addWidget(_run_card(theme, lang, run), i // cols, i % cols)
        outer.addWidget(grid_holder)
        outer.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(page)
    return scroll


__all__ = ["build_templates_tab"]
