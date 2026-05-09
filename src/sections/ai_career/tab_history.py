"""History tab - list previous AI Career analyses.

History entries live on disk under ``~/AI Hub/history.json`` (newest
first). Entries link to the run folder so the user can re-open the
generated documents at any time.

The "Open in app" button restores a snapshot of that run into the
current STATE - we read ``summary.json`` next to the entry and rebuild
the candidate / job spec / match / documents fields from disk.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

import flet as ft

from src.services import logger as logger_service
from src.services import store
from src.sections.ai_career.refs import safe
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


def _row(theme: Theme, txt: dict, summary: store.RunSummary, *, on_open_app: Callable[[str], None]) -> ft.Container:
    score = int(summary.overall_score or 0)
    score_color = "#22C55E" if score >= 80 else ("#F97316" if score < 60 else theme.primary)

    score_pill = ft.Container(
        content=ft.Text(f"{txt['history_score_label']}: {score}", color=score_color, size=12, weight=ft.FontWeight.W_700),
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        bgcolor=ft.Colors.with_opacity(0.14, score_color),
        border_radius=8,
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text(summary.role or "—", color=theme.text, size=14, weight=ft.FontWeight.W_700),
                        ft.Text(
                            f"{summary.company or '—'} · {summary.timestamp}",
                            color=theme.text_muted,
                            size=12,
                        ),
                        ft.Text(
                            summary.folder,
                            color=theme.text_subtle,
                            size=11,
                            italic=True,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                    tight=True,
                ),
                score_pill,
                ft.IconButton(
                    icon=ft.Icons.FOLDER_OPEN,
                    icon_color=theme.text_muted,
                    icon_size=18,
                    tooltip=txt["history_open_folder_btn"],
                    on_click=lambda e, folder=summary.folder: _open_in_explorer(folder),
                ),
                ft.IconButton(
                    icon=ft.Icons.OPEN_IN_NEW,
                    icon_color=theme.primary,
                    icon_size=18,
                    tooltip=txt["history_open_app_btn"],
                    on_click=lambda e, folder=summary.folder: on_open_app(folder),
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        bgcolor=theme.surface,
        border_radius=12,
        border=ft.border.all(1, theme.border),
    )


def _empty_state(theme: Theme, txt: dict) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.HISTORY_TOGGLE_OFF, color=theme.primary, size=42),
                    width=84,
                    height=84,
                    bgcolor=theme.primary_tint,
                    border_radius=22,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text(txt["history_empty_title"], color=theme.text, size=18, weight=ft.FontWeight.W_700),
                ft.Text(txt["history_empty_desc"], color=theme.text_muted, size=13, text_align=ft.TextAlign.CENTER),
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
        padding=40,
    )


def build_history_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Callable[[], None],
    on_navigate_tab: Callable[[int], None],
) -> ft.Control:
    txt = s(lang)

    list_holder = ft.Container(expand=True)
    info_text = ft.Text(
        txt["history_loaded_from_template"].format(path=str(store.history_path())),
        color=theme.text_subtle,
        size=11,
    )

    def _refresh() -> None:
        runs = store.list_runs()
        if not runs:
            list_holder.content = _empty_state(theme, txt)
        else:
            list_holder.content = ft.ListView(
                controls=[
                    _row(theme, txt, r, on_open_app=lambda folder: _open_app(folder))
                    for r in runs
                ],
                spacing=10,
                padding=ft.padding.symmetric(horizontal=18, vertical=12),
                expand=True,
            )
        logger_service.try_update(list_holder)

    def _open_app(folder: str) -> None:
        _restore_run(folder, on_done=on_request_rerender)
        on_navigate_tab(TAB_MATCH)

    _refresh()

    footer = ft.Container(
        content=ft.Row(
            controls=[
                info_text,
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.REFRESH, color=theme.text, size=14),
                            ft.Text(txt["history_refresh_btn"], color=theme.text, size=12, weight=ft.FontWeight.W_600),
                        ],
                        spacing=6,
                        tight=True,
                    ),
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    bgcolor=theme.surface_2,
                    border=ft.border.all(1, theme.border),
                    border_radius=10,
                    ink=True,
                    on_click=lambda e: _refresh(),
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=24, vertical=12),
        border=ft.border.only(top=ft.BorderSide(1, theme.border)),
        bgcolor=theme.bg,
    )

    return ft.Column(
        controls=[
            ft.Container(content=list_holder, expand=True),
            footer,
        ],
        spacing=0,
        expand=True,
        tight=True,
    )
