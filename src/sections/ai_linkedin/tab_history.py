"""History tab - list previous AI LinkedIn profile builds.

Reads ``~/AI Hub/history.json`` through :mod:`src.services.store` and
renders one row per saved run, scoped to the LinkedIn section
(``note == "ai_linkedin"``). The "Open folder" button opens the run's
output directory in the OS file browser.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Callable

import flet as ft

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


def _row(theme: Theme, txt: dict, summary: store.RunSummary) -> ft.Container:
    score = int(summary.overall_score or 0)
    score_color = "#22C55E" if score >= 80 else ("#F97316" if score < 60 else theme.primary)

    score_pill = ft.Container(
        content=ft.Text(
            f"{txt['history_score']}: {score}",
            color=score_color,
            size=12,
            weight=ft.FontWeight.W_700,
        ),
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        bgcolor=ft.Colors.with_opacity(0.14, score_color),
        border_radius=8,
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text(
                            summary.role or txt["recent_default_title"],
                            color=theme.text, size=14, weight=ft.FontWeight.W_700,
                        ),
                        ft.Text(
                            f"{summary.timestamp}",
                            color=theme.text_muted, size=12,
                        ),
                        ft.Text(
                            summary.folder,
                            color=theme.text_subtle, size=11, italic=True,
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
                    tooltip=txt["history_open"],
                    on_click=lambda e, folder=summary.folder: _open_in_explorer(folder),
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
                    content=ft.Icon(
                        ft.Icons.HISTORY_TOGGLE_OFF, color=theme.primary, size=42,
                    ),
                    width=84,
                    height=84,
                    bgcolor=ft.Colors.with_opacity(0.14, theme.primary),
                    border_radius=22,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text(
                    txt["history_empty_title"],
                    color=theme.text, size=18, weight=ft.FontWeight.W_700,
                ),
                ft.Text(
                    txt["history_empty_desc"],
                    color=theme.text_muted, size=13, text_align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
        padding=40,
    )


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
) -> ft.Column:
    txt = s(lang)

    list_holder = ft.Container(expand=True)

    def _refresh() -> None:
        runs = _list_runs()
        if not runs:
            list_holder.content = _empty_state(theme, txt)
        else:
            list_holder.content = ft.ListView(
                controls=[_row(theme, txt, r) for r in runs],
                spacing=10,
                padding=ft.padding.symmetric(horizontal=18, vertical=12),
                expand=True,
            )
        if not logger_service.try_update(list_holder):
            logger_service.log_event(
                "DEBUG", "ai_linkedin.tab_history", "list_holder_update_skipped",
            )

    _refresh()

    refresh_btn = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.REFRESH, color=theme.text, size=14),
                ft.Text(
                    txt["history_open"],
                    color=theme.text, size=12, weight=ft.FontWeight.W_600,
                ),
            ],
            spacing=6,
            tight=True,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        bgcolor=theme.surface_2,
        border=ft.border.all(1, theme.border),
        border_radius=10,
        ink=True,
        on_click=lambda e: (_refresh(), safe(on_request_rerender)),
    )

    footer = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(expand=True),
                refresh_btn,
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
