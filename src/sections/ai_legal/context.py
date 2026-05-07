"""Right-hand context panel for the AI Legal section.

Three cards stacked from top to bottom:

1. **Attached documents** - upload button at the top, currently uploaded
   PDF chip below it (or a placeholder + the drop zone if nothing's
   uploaded yet). Either way the drop zone stays available so users can
   replace the file by dropping a new one.
2. **Document analysis** - the four stats from the screenshot
   (Summary / Risks / Important clauses / Recommendations) followed by
   a primary button that jumps the user to the Analýza tab.
3. **Quick actions** - same chevron-list pattern other sections use.
"""

from __future__ import annotations

from typing import Callable

import flet as ft

from src.components.context_panel import (
    context_panel_shell,
    quick_actions_column,
)
from src.components.document_chip import document_chip
from src.components.section_card import section_card
from src.sections.ai_legal.data import context_quick_actions, context_stats
from src.sections.ai_legal.drop_zone import drop_zone
from src.sections.ai_legal.refs import REFS
from src.sections.ai_legal.state import STATE
from src.sections.ai_legal.strings import s
from src.theme import Theme


_STATUS_COLOR = {
    "ok": "#22C55E",
    "warn": "#F59E0B",
    "info": "#3B82F6",
}


def _upload_button(theme: Theme, lang: str) -> ft.Container:
    txt = s(lang)
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.FILE_UPLOAD_OUTLINED, color=theme.primary, size=16),
                ft.Text(
                    txt["ctx_upload_btn"],
                    color=theme.primary,
                    size=13,
                    weight=ft.FontWeight.W_600,
                ),
            ],
            spacing=8,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        bgcolor=ft.Colors.with_opacity(0.10, theme.primary),
        border=ft.border.all(1, ft.Colors.with_opacity(0.20, theme.primary)),
        border_radius=10,
        ink=True,
        on_click=lambda e: None,
        alignment=ft.Alignment.CENTER,
    )


def _analysis_stat_row(
    theme: Theme,
    *,
    icon: str,
    title: str,
    desc: str,
    status: str,
) -> ft.Container:
    accent = _STATUS_COLOR.get(status, theme.text_muted)
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(icon, color=accent, size=16),
                    width=28,
                    height=28,
                    bgcolor=ft.Colors.with_opacity(0.15, accent),
                    border_radius=8,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    controls=[
                        ft.Text(
                            title,
                            color=theme.text,
                            size=13,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Text(
                            desc,
                            color=theme.text_muted,
                            size=11,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                    tight=True,
                ),
                ft.Icon(
                    {
                        "ok": ft.Icons.CHECK_CIRCLE,
                        "warn": ft.Icons.WARNING_AMBER_ROUNDED,
                        "info": ft.Icons.INFO,
                    }.get(status, ft.Icons.CIRCLE),
                    color=accent,
                    size=18,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=4, vertical=6),
    )


def _show_detail_button(
    theme: Theme,
    lang: str,
    *,
    on_click: Callable[[ft.ControlEvent], None],
) -> ft.Container:
    txt = s(lang)
    return ft.Container(
        content=ft.Text(
            txt["ctx_show_detail_btn"],
            color=ft.Colors.WHITE,
            size=13,
            weight=ft.FontWeight.W_600,
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        bgcolor=theme.primary,
        border_radius=10,
        ink=True,
        on_click=on_click,
        alignment=ft.Alignment.CENTER,
    )


def _build_panel(theme: Theme, lang: str) -> ft.Container:
    """Compose the three context-panel cards from the latest STATE."""
    txt = s(lang)

    def _on_open_analysis() -> None:
        STATE.active_tab = 1
        if REFS.rerender_main is not None:
            REFS.rerender_main()

    def _on_file_resolved(file_dict: dict) -> None:
        STATE.uploaded_file = file_dict
        if REFS.rerender_context is not None:
            REFS.rerender_context()
        if REFS.rerender_tab_body is not None:
            REFS.rerender_tab_body()

    docs_children: list[ft.Control] = [_upload_button(theme, lang)]
    if STATE.uploaded_file:
        f = STATE.uploaded_file
        docs_children.append(
            document_chip(
                theme,
                lang,
                name=f["name"],
                ext=f["type"],
                size=f["size"],
            )
        )
    else:
        docs_children.append(
            ft.Text(txt["ctx_no_doc"], color=theme.text_muted, size=12)
        )

    docs_children.append(
        drop_zone(
            theme,
            lang,
            on_file_resolved=_on_file_resolved,
            height=104,
        )
    )

    documents_card = section_card(
        theme,
        ft.Icons.DESCRIPTION_OUTLINED,
        txt["ctx_attached_title"],
        ft.Column(controls=docs_children, spacing=10, tight=True),
    )

    stat_rows: list[ft.Control] = [
        _analysis_stat_row(
            theme,
            icon=stat["icon"],
            title=stat["title"],
            desc=stat["desc"],
            status=stat["status"],
        )
        for stat in context_stats(lang)
    ]
    stat_rows.append(
        _show_detail_button(
            theme,
            lang,
            on_click=lambda e: _on_open_analysis(),
        )
    )

    analysis_card = section_card(
        theme,
        ft.Icons.INSIGHTS_OUTLINED,
        txt["ctx_analysis_title"],
        ft.Column(controls=stat_rows, spacing=8, tight=True),
    )

    quick_actions_card = section_card(
        theme,
        ft.Icons.BOLT_OUTLINED,
        txt["ctx_quick_actions"],
        quick_actions_column(theme, context_quick_actions(lang)),
    )

    return context_panel_shell(
        theme,
        documents_card,
        analysis_card,
        quick_actions_card,
    )


def build_context(theme: Theme, lang: str) -> ft.Control:
    """Section entry-point. Wraps :func:`_build_panel` so it can swap in
    place when state changes (file upload, etc.) without going through
    a global ``AIHubApp.build`` rebuild."""
    holder = ft.Container(content=_build_panel(theme, lang))

    def _rerender_context() -> None:
        holder.content = _build_panel(theme, lang)
        try:
            holder.update()
        except AssertionError:
            pass

    REFS.rerender_context = _rerender_context
    return holder
