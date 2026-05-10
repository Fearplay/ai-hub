"""History tab - list previous AI Career analyses (PySide6 port)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
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
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    ElidedLabel,
    GhostButton,
    IconLabel,
    IconOnlyButton,
    MutedLabel,
    Pill,
    SubtleLabel,
    TitleLabel,
    custom_label,
    hbox,
    vbox,
)
from src.services import logger as logger_service
from src.services import store
from src.sections.ai_career.state import STATE, TAB_MATCH
from src.sections.ai_career.strings import s
from src.theme import Theme


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
            "ai_career.tab_history", "open_in_explorer_failed", exc, path=path,
        )


def _restore_run(folder: str, on_done: Callable[[], None]) -> None:
    summary = store.read_run_summary(folder)
    if not summary:
        return
    STATE.candidate = summary.get("candidate")
    STATE.job_spec = summary.get("job_spec")
    STATE.match = summary.get("match")

    docs: dict[str, str] = {}
    folder_path = Path(folder)
    file_map = {
        "tailored_cv": "Tailored_CV.md",
        "modern_cv": "Modern_CV.md",
        "cover_letter": "Cover_Letter.md",
        "match_report": "Match_Report.md",
        "interview_prep": "Interview_Prep.md",
        "skill_gap": "Skill_Gap_Plan.md",
        "evidence": "Evidence_Report.md",
    }
    for kind, filename in file_map.items():
        candidate_path = folder_path / filename
        if candidate_path.exists():
            try:
                docs[kind] = candidate_path.read_text(encoding="utf-8")
            except OSError:
                continue
    STATE.documents = docs
    STATE.last_run_folder = folder
    STATE.active_tab = TAB_MATCH
    on_done()


def _row(
    theme: Theme,
    txt: dict,
    summary: store.RunSummary,
    *,
    on_open_app: Callable[[str], None],
) -> QFrame:
    score = int(summary.overall_score or 0)
    score_color = "#22C55E" if score >= 80 else ("#F97316" if score < 60 else theme.primary)

    row = QFrame()
    row.setObjectName("CareerHistoryRow")
    row.setStyleSheet(
        f"""
        QFrame#CareerHistoryRow {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        """
    )
    layout = hbox(spacing=10, margins=(14, 10, 14, 10))
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    row.setLayout(layout)

    info = QFrame()
    info.setStyleSheet("background: transparent;")
    info.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    il = vbox(spacing=2, margins=(0, 0, 0, 0))
    info.setLayout(il)
    il.addWidget(BodyLabel(summary.role or "—", theme=theme, size=14, weight=QFont.Weight.Bold))
    il.addWidget(MutedLabel(f"{summary.company or '—'} · {summary.timestamp}", theme=theme, size=12))
    folder_label = ElidedLabel(
        summary.folder,
        color=theme.text_subtle,
        size=11,
        italic=True,
    )
    il.addWidget(folder_label)
    layout.addWidget(info, 1)

    pill = Pill(text=f"{txt['history_score_label']}: {score}", bg=rgba(score_color, 0.14), fg=score_color)
    layout.addWidget(pill)

    open_folder = IconOnlyButton(Icons.FOLDER_OPEN, color=theme.text_muted, size=18, bg_hover=theme.surface_2, tooltip=txt["history_open_folder_btn"])
    open_folder.clicked.connect(lambda folder=summary.folder: _open_in_explorer(folder))
    layout.addWidget(open_folder)

    open_app = IconOnlyButton(Icons.OPEN_IN_NEW, color=theme.primary, size=18, bg_hover=theme.surface_2, tooltip=txt["history_open_app_btn"])
    open_app.clicked.connect(lambda folder=summary.folder: on_open_app(folder))
    layout.addWidget(open_app)
    return row


def _empty_state(theme: Theme, txt: dict) -> QWidget:
    holder = QWidget()
    holder.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=12, margins=(40, 40, 40, 40))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    holder.setLayout(layout)

    badge = QFrame()
    badge.setFixedSize(84, 84)
    badge.setStyleSheet(
        f"background-color: {theme.primary_tint}; border-radius: 22px;"
    )
    bl = hbox(spacing=0, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setLayout(bl)
    bl.addWidget(IconLabel(Icons.HISTORY_TOGGLE_OFF, color=theme.primary, size=42),
                 alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignHCenter)
    layout.addWidget(TitleLabel(txt["history_empty_title"], theme=theme, size=18, weight=QFont.Weight.Bold), alignment=Qt.AlignmentFlag.AlignHCenter)
    desc = MutedLabel(txt["history_empty_desc"], theme=theme, size=13)
    desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(desc, alignment=Qt.AlignmentFlag.AlignHCenter)
    return holder


def build_history_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Callable[[], None],
    on_navigate_tab: Callable[[int], None],
) -> QWidget:
    txt = s(lang)

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    list_holder = QWidget()
    list_holder.setStyleSheet(f"background-color: {theme.bg};")
    list_layout = vbox(spacing=10, margins=(18, 12, 18, 12))
    list_holder.setLayout(list_layout)

    def _open_app(folder: str) -> None:
        _restore_run(folder, on_done=on_request_rerender)
        on_navigate_tab(TAB_MATCH)

    def _populate() -> None:
        while list_layout.count():
            item = list_layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()
        runs = store.list_runs()
        if not runs:
            list_layout.addWidget(_empty_state(theme, txt))
            return
        for r in runs:
            list_layout.addWidget(_row(theme, txt, r, on_open_app=_open_app))
        list_layout.addStretch(1)

    _populate()

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(list_holder)
    layout.addWidget(scroll, 1)

    footer = QFrame()
    footer.setObjectName("CareerHistoryFooter")
    footer.setStyleSheet(
        f"""
        QFrame#CareerHistoryFooter {{
            background-color: {theme.bg};
            border-top: 1px solid {theme.border};
        }}
        """
    )
    footer_layout = hbox(spacing=10, margins=(24, 12, 24, 12))
    footer_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    footer.setLayout(footer_layout)
    info = SubtleLabel(
        txt["history_loaded_from_template"].format(path=str(store.history_path())),
        theme=theme, size=11,
    )
    footer_layout.addWidget(info)
    footer_layout.addStretch(1)
    refresh = GhostButton(txt["history_refresh_btn"], theme=theme, icon=Icons.REFRESH)
    refresh.clicked.connect(_populate)
    footer_layout.addWidget(refresh)
    layout.addWidget(footer)

    return container
