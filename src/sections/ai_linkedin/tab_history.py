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
    ClickFrame,
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
from src.sections.ai_linkedin.refs import REFS, safe
from src.sections.ai_linkedin.state import STATE, TAB_OUTPUT
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


def _restore_run(folder: str, on_done: Callable[[], None]) -> None:
    try:
        data = store.read_run_summary(folder) or {}
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.tab_history", "restore_run_read_failed", exc,
            folder=folder,
        )
        return
    if not data.get("extracted_profile"):
        logger_service.log_event(
            "WARNING", "ai_linkedin.tab_history", "restore_run_missing_profile",
            folder=folder,
        )
        return
    STATE.extracted_profile = data.get("extracted_profile")
    STATE.headlines = data.get("headlines")
    STATE.about_variants = data.get("about_variants")
    STATE.experience_rewrites = data.get("experience_rewrites")
    STATE.education_rewrites = data.get("education_rewrites")
    STATE.certifications_rewrites = data.get("certifications_rewrites")
    STATE.skills_buckets = data.get("skills_buckets")
    STATE.featured = data.get("featured")
    STATE.projects = data.get("projects")
    STATE.services = data.get("services")
    STATE.courses = data.get("courses")
    STATE.recommendation_messages = data.get("recommendation_messages")
    STATE.posts = data.get("posts")
    STATE.completeness = data.get("completeness")
    STATE.unsupported_claims = data.get("unsupported_claims")
    STATE.profile_score = data.get("profile_score")
    STATE.target_roles = list(data.get("target_roles") or STATE.target_roles)
    STATE.audience = str(data.get("audience") or STATE.audience)
    STATE.tone = str(data.get("tone") or STATE.tone)
    STATE.output_lang = str(data.get("output_lang") or STATE.output_lang)
    STATE.last_run_folder = folder
    STATE.active_tab = TAB_OUTPUT
    logger_service.log_event(
        "INFO", "ai_linkedin.tab_history", "restore_run_done",
        folder=folder,
    )
    REFS.request_context_refresh()
    on_done()


def _row(theme: Theme, txt: dict, summary: store.RunSummary, *, on_open_app: Callable[[str], None]) -> QFrame:
    score = int(summary.overall_score or 0)
    score_color = "#22C55E" if score >= 80 else ("#F97316" if score < 60 else theme.primary)

    row = ClickFrame()
    row.setObjectName("LinkedInHistoryRow")
    row.clicked.connect(lambda _checked=False, folder=summary.folder: on_open_app(folder))
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
    # overwritten by ``True``/``False`` (see ai_cv.tab_history for
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
        def _open_app(folder: str) -> None:
            _restore_run(folder, on_done=on_request_rerender)
            on_navigate_tab(TAB_OUTPUT)

        for r in runs:
            list_layout.addWidget(_row(theme, txt, r, on_open_app=_open_app))
        list_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
        scroll.setWidget(list_holder)
        layout.addWidget(scroll, 1)

    footer = QFrame()
    # See ``ai_linkedin/tab_output.py`` for the rationale.
    footer.setObjectName("LinkedInHistoryFooter")
    footer.setStyleSheet(
        f"""
        QFrame#LinkedInHistoryFooter {{
            background-color: {theme.bg};
            border-top: 1px solid {theme.border};
        }}
        """
    )
    footer_layout = hbox(spacing=10, margins=(24, 12, 24, 12))
    footer_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    footer.setLayout(footer_layout)
    footer_layout.addStretch(1)
    refresh = GhostButton(txt["history_open"], theme=theme, icon=Icons.REFRESH)
    refresh.clicked.connect(lambda: safe(on_request_rerender))
    footer_layout.addWidget(refresh)
    layout.addWidget(footer)
    return container
