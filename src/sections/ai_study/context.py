"""AI Study - right-hand context panel.

Four cards:

1. Dnešní studijní přehled - 3 stat tiles (Témata, Studováno, Pokrok).
2. Moje předměty - rows with a gradient progress bar per subject.
3. Rychlé nástroje - 3x2 grid of small action tiles.
4. Nadcházející úkoly - checkbox + title + due-date pill rows.
"""

from __future__ import annotations

import flet as ft

from src.components.context_panel import context_panel_shell
from src.components.section_card import section_card
from src.i18n import t
from src.sections.ai_study.data import (
    quick_tools,
    subjects,
    today_overview,
    upcoming_tasks,
)
from src.sections.ai_study.strings import s
from src.theme import Theme


def _stat_tile(theme: Theme, *, icon: str, value: str, label: str) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Icon(icon, color=theme.primary, size=18),
                ft.Text(
                    value,
                    color=theme.text,
                    size=18,
                    weight=ft.FontWeight.W_700,
                ),
                ft.Text(
                    label,
                    color=theme.text_muted,
                    size=11,
                    weight=ft.FontWeight.W_500,
                ),
            ],
            spacing=4,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=10, vertical=12),
        bgcolor=theme.surface_2,
        border_radius=10,
        expand=True,
        alignment=ft.Alignment.CENTER,
    )


def _today_overview_card(theme: Theme, lang: str) -> ft.Container:
    txt = s(lang)
    tiles = [
        _stat_tile(theme, icon=item["icon"], value=item["value"], label=item["label"])
        for item in today_overview(lang)
    ]
    content = ft.Row(controls=tiles, spacing=8)
    return section_card(
        theme,
        ft.Icons.CALENDAR_TODAY,
        txt["today_title"],
        content,
    )


def _gradient_progress_bar(
    *,
    percent: int,
    color_start: str,
    color_end: str,
    track_color: str,
    width: float = 170,
) -> ft.Stack:
    track = ft.Container(
        width=width,
        height=6,
        bgcolor=track_color,
        border_radius=3,
    )
    fill_width = max(0.0, min(100.0, percent)) / 100.0 * width
    fill = ft.Container(
        width=fill_width,
        height=6,
        border_radius=3,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.CENTER_LEFT,
            end=ft.Alignment.CENTER_RIGHT,
            colors=[color_start, color_end],
        ),
    )
    return ft.Stack(controls=[track, fill], width=width, height=6)


def _subject_row(theme: Theme, subject: dict) -> ft.Row:
    return ft.Row(
        controls=[
            ft.Icon(subject["icon"], color=subject["color_start"], size=16),
            ft.Text(
                subject["name"],
                color=theme.text,
                size=13,
                weight=ft.FontWeight.W_500,
                width=92,
                overflow=ft.TextOverflow.ELLIPSIS,
                max_lines=1,
            ),
            ft.Container(
                content=_gradient_progress_bar(
                    percent=subject["percent"],
                    color_start=subject["color_start"],
                    color_end=subject["color_end"],
                    track_color=theme.surface_2,
                    width=110,
                ),
                expand=True,
            ),
            ft.Text(
                f"{subject['percent']}%",
                color=theme.text,
                size=12,
                weight=ft.FontWeight.W_600,
                width=36,
                text_align=ft.TextAlign.RIGHT,
            ),
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _add_pill(theme: Theme, label: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.ADD, color=theme.primary, size=14),
                ft.Text(label, color=theme.primary, size=12, weight=ft.FontWeight.W_600),
            ],
            spacing=6,
            alignment=ft.MainAxisAlignment.CENTER,
            tight=True,
        ),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        bgcolor=ft.Colors.with_opacity(0.10, theme.primary),
        border_radius=10,
        border=ft.border.all(1, ft.Colors.with_opacity(0.20, theme.primary)),
        ink=True,
        on_click=lambda e: None,
        alignment=ft.Alignment.CENTER,
    )


def _subjects_card(theme: Theme, lang: str) -> ft.Container:
    txt = s(lang)
    rows = [_subject_row(theme, subj) for subj in subjects(lang)]
    content = ft.Column(
        controls=[
            *rows,
            _add_pill(theme, txt["add_subject"]),
        ],
        spacing=12,
        tight=True,
    )
    return section_card(
        theme,
        ft.Icons.BOOKMARK_OUTLINE,
        txt["subjects_title"],
        content,
        action_label=t("edit", lang),
    )


def _tool_tile(theme: Theme, *, icon: str, label: str) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Icon(icon, color=theme.primary, size=18),
                ft.Text(
                    label,
                    color=theme.text,
                    size=11,
                    weight=ft.FontWeight.W_500,
                    text_align=ft.TextAlign.CENTER,
                    max_lines=2,
                ),
            ],
            spacing=6,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=6, vertical=10),
        bgcolor=theme.surface_2,
        border_radius=10,
        height=72,
        expand=True,
        alignment=ft.Alignment.CENTER,
        ink=True,
        on_click=lambda e: None,
    )


def _tools_card(theme: Theme, lang: str) -> ft.Container:
    txt = s(lang)
    items = quick_tools(lang)

    rows: list[ft.Control] = []
    for i in range(0, len(items), 3):
        chunk = items[i : i + 3]
        rows.append(
            ft.Row(
                controls=[
                    _tool_tile(theme, icon=item["icon"], label=item["label"])
                    for item in chunk
                ],
                spacing=8,
            )
        )

    content = ft.Column(controls=rows, spacing=8, tight=True)
    return section_card(
        theme,
        ft.Icons.AUTO_AWESOME,
        txt["tools_title"],
        content,
    )


def _task_row(theme: Theme, task: dict) -> ft.Row:
    checkbox = ft.Container(
        width=18,
        height=18,
        border=ft.border.all(1.5, theme.text_muted),
        border_radius=9,
        bgcolor="transparent",
    )
    title = ft.Text(
        task["title"],
        color=theme.text,
        size=13,
        weight=ft.FontWeight.W_500,
        expand=True,
        overflow=ft.TextOverflow.ELLIPSIS,
        max_lines=1,
    )
    due = ft.Text(
        task["due"],
        color=theme.text_muted,
        size=11,
        weight=ft.FontWeight.W_500,
    )
    return ft.Row(
        controls=[checkbox, title, due],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _tasks_card(theme: Theme, lang: str) -> ft.Container:
    txt = s(lang)
    rows = [_task_row(theme, task) for task in upcoming_tasks(lang)]
    content = ft.Column(
        controls=[
            *rows,
            _add_pill(theme, txt["add_task"]),
        ],
        spacing=12,
        tight=True,
    )
    return section_card(
        theme,
        ft.Icons.EVENT_NOTE,
        txt["tasks_title"],
        content,
        action_label=txt["task_show_all"],
    )


def build_context(theme: Theme, lang: str) -> ft.Container:
    return context_panel_shell(
        theme,
        _today_overview_card(theme, lang),
        _subjects_card(theme, lang),
        _tools_card(theme, lang),
        _tasks_card(theme, lang),
    )
