"""History tab - list previous AI LinkedIn profile builds (PySide6 port)."""

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
from src.sections.ai_linkedin.refs import safe
from src.sections.ai_linkedin.strings import s
from src.theme import Theme


def _open_in_explorer(path: str) -> None:
    if not path or not os.path.isdir(path):
        logger_service.log_event(
            "WARNING", "ai_linkedin.tab_history", "open_in_explorer_no_path",
            path=str(path),
        )
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
            "ai_linkedin.tab_history", "open_in_explorer_failed", exc, path=path,
        )


def _row(theme: Theme, txt: dict, summary: store.RunSummary) -> QFrame:
    score = int(summary.overall_score or 0)
    score_color = "#22C55E" if score >= 80 else ("#F97316" if score < 60 else theme.primary)

    row = QFrame()
    row.setObjectName("LinkedInHistoryRow")
    row.setStyleSheet(
        f"""
        QFrame#LinkedInHistoryRow {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        """
    )
    layout = hbox(spacing=10, margins=(14, 10, 14, 10))
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    row.setLayout(layout)

    info = QFrame()
    info.setStyleSheet("background: transparent; border: none;")
    info.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    info_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    info.setLayout(info_layout)
    info_layout.addWidget(BodyLabel(summary.role or txt["recent_default_title"], theme=theme, size=14, weight=QFont.Weight.Bold))
    info_layout.addWidget(MutedLabel(summary.timestamp, theme=theme, size=12))
    info_layout.addWidget(ElidedLabel(summary.folder, color=theme.text_subtle, size=11, italic=True))
    layout.addWidget(info, 1)

    pill = Pill(text=f"{txt['history_score']}: {score}", bg=rgba(score_color, 0.14), fg=score_color)
    layout.addWidget(pill, 0, Qt.AlignmentFlag.AlignTop)

    open_btn = IconOnlyButton(Icons.FOLDER_OPEN, color=theme.text_muted, size=18, bg_hover=theme.surface_2, tooltip=txt["history_open"])
    # ``QToolButton.clicked`` emits ``bool checked`` - bind it to a
    # throwaway first arg so the captured ``folder`` default is not
    # overwritten by ``True``/``False`` (see ai_career.tab_history for
    # the same pattern + the upstream traceback this fixed).
    open_btn.clicked.connect(lambda _checked=False, folder=summary.folder: _open_in_explorer(folder))
    layout.addWidget(open_btn, 0, Qt.AlignmentFlag.AlignTop)
    return row


def _empty_state(theme: Theme, txt: dict) -> QWidget:
    holder = QWidget()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=12, margins=(40, 40, 40, 40))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    holder.setLayout(layout)

    badge = QFrame()
    badge.setFixedSize(84, 84)
    badge.setStyleSheet(
        f"background-color: {rgba(theme.primary, 0.14)}; border-radius: 22px;"
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


def _list_runs() -> list[store.RunSummary]:
    try:
        runs = store.list_runs()
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.tab_history", "list_runs_failed", exc,
        )
        return []
    return [r for r in runs if (getattr(r, "note", "") or "") == "ai_linkedin"]


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

    runs = _list_runs()
    if not runs:
        layout.addWidget(_empty_state(theme, txt), 1)
    else:
        list_holder = QWidget()
        list_holder.setStyleSheet(f"background-color: {theme.bg};")
        list_layout = vbox(spacing=10, margins=(18, 12, 18, 12))
        list_holder.setLayout(list_layout)
        for r in runs:
            list_layout.addWidget(_row(theme, txt, r))
        list_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
        scroll.setWidget(list_holder)
        layout.addWidget(scroll, 1)

    footer = QFrame()
    footer.setStyleSheet(f"background-color: {theme.bg}; border-top: 1px solid {theme.border};")
    footer_layout = hbox(spacing=10, margins=(24, 12, 24, 12))
    footer_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    footer.setLayout(footer_layout)
    footer_layout.addStretch(1)
    refresh = GhostButton(txt["history_open"], theme=theme, icon=Icons.REFRESH)
    refresh.clicked.connect(lambda: safe(on_request_rerender))
    footer_layout.addWidget(refresh)
    layout.addWidget(footer)
    return container
