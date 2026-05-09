"""Match tab - score, categories, matches, gaps, ATS keywords.

Renders the analysis output in a layout inspired by the user's old
ApplyPilot screenshot: a big overall score on the left, category score
bars on the right, three result columns (matches / gaps / ATS keywords)
underneath, and an evidence preview list at the bottom.

If the user has not run an analysis yet, a friendly empty state nudges
them back to Setup.

The "Generate documents" footer button kicks off
:func:`pipeline.generate_all_documents` on a daemon thread, then auto-
redirects to the Documents tab once every kind is populated. This is
why the user does not have to click Generate per document.
"""

from __future__ import annotations

import threading
from typing import Callable

import flet as ft

from src.services import logger as logger_service
from src.sections.ai_career import pipeline
from src.sections.ai_career._dialog import close_dialog, open_dialog
from src.sections.ai_career.refs import REFS, safe
from src.sections.ai_career.state import STATE, TAB_DOCUMENTS, TAB_SETUP
from src.sections.ai_career.strings import s
from src.theme import Theme


def _request_full_refresh() -> None:
    """Trigger a full section rebuild from anywhere in this module."""
    try:
        from src.app import request_section_refresh
    except Exception as exc:
        logger_service.log_exception(
            "ai_career.tab_match", "request_full_refresh_import", exc,
        )
        return
    request_section_refresh()


_OK_COLOR = "#22C55E"
_RISK_COLOR = "#F97316"
_INFO_COLOR = "#3B82F6"


def _score_circle(theme: Theme, score: int, label: str) -> ft.Container:
    score = max(0, min(100, int(score)))
    color = _OK_COLOR if score >= 80 else (_RISK_COLOR if score < 60 else theme.primary)
    return ft.Container(
        content=ft.Stack(
            controls=[
                ft.ProgressRing(
                    value=score / 100.0,
                    width=152,
                    height=152,
                    stroke_width=10,
                    color=color,
                    bgcolor=ft.Colors.with_opacity(0.18, color),
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                label,
                                color=theme.text_muted,
                                size=10,
                                weight=ft.FontWeight.W_700,
                                style=ft.TextStyle(letter_spacing=1.4),
                            ),
                            ft.Text(
                                str(score),
                                color=theme.text,
                                size=44,
                                weight=ft.FontWeight.W_700,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=2,
                        tight=True,
                    ),
                    width=152,
                    height=152,
                    alignment=ft.Alignment.CENTER,
                ),
            ],
        ),
        bgcolor=theme.surface,
        border=ft.border.all(1, theme.border),
        border_radius=14,
        padding=14,
        width=180,
        height=180,
        alignment=ft.Alignment.CENTER,
    )


def _category_bar(theme: Theme, *, name: str, score: int, evidence: list[str]) -> ft.Container:
    score = max(0, min(100, int(score)))
    color = _OK_COLOR if score >= 75 else (_RISK_COLOR if score < 55 else theme.primary)
    tooltip = "\n".join(f"• {e}" for e in evidence) if evidence else None

    # Use flex weights so the fill width tracks the score regardless of the
    # parent's actual pixel width. The previous version multiplied the
    # score by a hard-coded 1.0 px max which rendered every bar as a
    # sub-pixel sliver.
    filled_flex = max(1, score)
    empty_flex = max(1, 100 - score)
    bar = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    expand=filled_flex,
                    height=6,
                    bgcolor=color,
                    border_radius=3,
                ),
                ft.Container(expand=empty_flex, height=6),
            ],
            spacing=0,
        ),
        height=6,
        bgcolor=ft.Colors.with_opacity(0.18, color),
        border_radius=3,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(name, color=theme.text, size=12, weight=ft.FontWeight.W_600, expand=True),
                        ft.Text(f"{score} / 100", color=theme.text_muted, size=11, weight=ft.FontWeight.W_500),
                    ],
                    spacing=8,
                ),
                bar,
            ],
            spacing=6,
            tight=True,
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        bgcolor=theme.surface,
        border=ft.border.all(1, theme.border),
        border_radius=12,
        tooltip=tooltip,
    )


def _bullet_column(
    theme: Theme,
    *,
    title: str,
    items: list[str],
    accent: str,
    bullet_marker: str = "•",
) -> ft.Container:
    body: list[ft.Control] = [
        ft.Text(
            title,
            color=theme.text_muted,
            size=10,
            weight=ft.FontWeight.W_700,
            style=ft.TextStyle(letter_spacing=1.4),
        )
    ]
    if not items:
        body.append(ft.Text("—", color=theme.text_subtle, size=12))
    else:
        for item in items:
            body.append(
                ft.Row(
                    controls=[
                        ft.Text(bullet_marker, color=accent, size=14, weight=ft.FontWeight.W_700),
                        ft.Text(item, color=theme.text, size=12, expand=True, selectable=True),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
            )
    return ft.Container(
        content=ft.Column(controls=body, spacing=8, tight=True),
        padding=14,
        bgcolor=theme.surface,
        border_radius=12,
        border=ft.border.all(1, theme.border),
        expand=True,
    )


def _ats_column(theme: Theme, *, title: str, present: list[str], missing: list[str], present_label: str, missing_label: str) -> ft.Container:
    def _chip(text: str, *, ok: bool) -> ft.Container:
        color = _OK_COLOR if ok else _RISK_COLOR
        return ft.Container(
            content=ft.Text(text, color=color, size=11, weight=ft.FontWeight.W_500),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            bgcolor=ft.Colors.with_opacity(0.14, color),
            border_radius=8,
        )

    present_chips = ft.Row(
        controls=[_chip(k, ok=True) for k in present] or [ft.Text("—", color=theme.text_subtle, size=12)],
        wrap=True,
        spacing=6,
        run_spacing=6,
    )
    missing_chips = ft.Row(
        controls=[_chip(k, ok=False) for k in missing] or [ft.Text("—", color=theme.text_subtle, size=12)],
        wrap=True,
        spacing=6,
        run_spacing=6,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    title,
                    color=theme.text_muted,
                    size=10,
                    weight=ft.FontWeight.W_700,
                    style=ft.TextStyle(letter_spacing=1.4),
                ),
                ft.Text(present_label, color=theme.text_muted, size=11, weight=ft.FontWeight.W_500),
                present_chips,
                ft.Container(height=4),
                ft.Text(missing_label, color=theme.text_muted, size=11, weight=ft.FontWeight.W_500),
                missing_chips,
            ],
            spacing=6,
            tight=True,
        ),
        padding=14,
        bgcolor=theme.surface,
        border_radius=12,
        border=ft.border.all(1, theme.border),
        expand=True,
    )


def _empty_state(theme: Theme, txt: dict, on_back: Callable[[], None]) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.QUERY_STATS, color=theme.primary, size=42),
                    width=84,
                    height=84,
                    bgcolor=theme.primary_tint,
                    border_radius=22,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text(txt["match_no_results_title"], color=theme.text, size=18, weight=ft.FontWeight.W_700),
                ft.Text(
                    txt["match_no_results_desc"],
                    color=theme.text_muted,
                    size=13,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(
                    content=ft.Text(txt["tab_setup"], color=ft.Colors.WHITE, size=13, weight=ft.FontWeight.W_600),
                    padding=ft.padding.symmetric(horizontal=18, vertical=10),
                    bgcolor=theme.primary,
                    border_radius=10,
                    ink=True,
                    on_click=lambda e: on_back(),
                    alignment=ft.Alignment.CENTER,
                ),
            ],
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
        padding=40,
    )


def build_match_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Callable[[], None],
    on_navigate_tab: Callable[[int], None],
) -> ft.Control:
    txt = s(lang)
    match = STATE.match

    def _resolved_output_lang() -> str:
        selected = (STATE.document_output_lang or "").strip().lower()
        if selected in ("en", "cs"):
            return selected
        return "en" if lang == "en" else "cs"

    def _open_documents_with_language(
        page: ft.Page | None,
        *,
        on_confirm: Callable[[str], None],
    ) -> None:
        # If we have no page handle (edge-case callback path), keep the
        # default language and continue immediately.
        if page is None:
            fallback_lang = _resolved_output_lang()
            STATE.document_output_lang = fallback_lang
            on_confirm(fallback_lang)
            return

        radio = ft.RadioGroup(
            value=_resolved_output_lang(),
            content=ft.Column(
                controls=[
                    ft.Radio(value="cs", label=txt["docs_lang_option_cs"]),
                    ft.Radio(value="en", label=txt["docs_lang_option_en"]),
                ],
                spacing=6,
                tight=True,
            ),
        )

        def _on_cancel(_e: ft.ControlEvent) -> None:
            close_dialog(page)

        def _confirm_and_open(_e: ft.ControlEvent) -> None:
            chosen = (radio.value or "").strip().lower()
            if chosen not in ("en", "cs"):
                chosen = _resolved_output_lang()
            STATE.document_output_lang = chosen
            close_dialog(page)
            on_confirm(chosen)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(txt["docs_lang_dialog_title"]),
            content=ft.Column(
                controls=[
                    ft.Text(txt["docs_lang_dialog_desc"], size=12),
                    radio,
                ],
                spacing=10,
                tight=True,
            ),
            actions=[
                ft.TextButton(txt["docs_lang_dialog_cancel"], on_click=_on_cancel),
                ft.ElevatedButton(txt["docs_lang_dialog_confirm"], on_click=_confirm_and_open),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        # ``open_dialog`` papers over the Flet 0.84 vs. older API split so
        # the dialog actually appears - the previous ``page.dialog = ...;
        # dialog.open = True`` flow silently no-ops on current Flet.
        open_dialog(page, dialog)

    if not match:
        return _empty_state(theme, txt, on_back=lambda: on_navigate_tab(TAB_SETUP))

    status_text = ft.Text("", color=theme.text_muted, size=11)
    button_holder = ft.Container()

    def _show_status(message: str, *, error: bool = False) -> None:
        status_text.value = message
        status_text.color = "#EF4444" if error else theme.text_muted
        logger_service.try_update(status_text)

    def _is_running() -> bool:
        # Source-of-truth lives on STATE so the disabled state survives the
        # full section rebuild that happens immediately after click. A
        # closure-local flag was being reset to False by the rebuild and
        # the button became clickable again mid-generation.
        return STATE.activity == "generating"

    def _render_button() -> None:
        running = _is_running()
        label = (
            txt["match_generating_documents"] if running else txt["match_open_documents_btn"]
        )
        button_holder.content = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.WHITE, size=14),
                    ft.Text(
                        label,
                        color=ft.Colors.WHITE,
                        size=13,
                        weight=ft.FontWeight.W_600,
                    ),
                ],
                spacing=8,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=18, vertical=10),
            bgcolor=theme.primary,
            border_radius=10,
            ink=not running,
            opacity=0.6 if running else 1.0,
            on_click=(None if running else _start_generate_all),
        )
        if not logger_service.try_update(button_holder):
            logger_service.log_event(
                "ERROR",
                "ai_career.tab_match",
                "render_button_update_failed",
            )

    def _start_generate_all(_e: ft.ControlEvent | None = None) -> None:
        if _is_running():
            return
        page = getattr(_e, "page", None) if _e is not None else None

        def _start_with_lang(doc_lang: str) -> None:
            STATE.activity = "generating"
            STATE.last_error = ""
            REFS.request_context_refresh()
            _show_status(txt["match_generating_documents"])
            _render_button()
            REFS.dispatch(_request_full_refresh)

            def _worker() -> None:
                try:
                    result = pipeline.generate_all_documents(output_lang=doc_lang)
                    if not result.ok:
                        _show_status(result.error, error=True)
                        return
                    STATE.active_tab = TAB_DOCUMENTS
                finally:
                    STATE.activity = "ready"
                    REFS.request_context_refresh()
                    REFS.dispatch(_request_full_refresh)

            threading.Thread(target=_worker, daemon=True).start()

        _open_documents_with_language(page, on_confirm=_start_with_lang)

    overall = int(match.get("overall_score") or 0)
    verdict = match.get("verdict") or ""
    categories = match.get("categories") or []
    matches = match.get("matches") or []
    gaps = match.get("gaps") or []
    ats_present = match.get("ats_keywords_present") or []
    ats_missing = match.get("ats_keywords_missing") or []
    evidence = match.get("evidence_preview") or []

    score_block = _score_circle(theme, overall, txt["match_overall_label"])

    category_controls = [
        _category_bar(
            theme,
            name=str(c.get("name") or ""),
            score=int(c.get("score") or 0),
            evidence=[str(x) for x in (c.get("evidence") or [])],
        )
        for c in categories
    ]
    if not category_controls:
        category_controls = [
            ft.Container(
                content=ft.Text(txt["match_per_category_hint"], color=theme.text_muted, size=12),
                padding=14,
                bgcolor=theme.surface,
                border=ft.border.all(1, theme.border),
                border_radius=12,
            )
        ]

    top_row = ft.Row(
        controls=[
            score_block,
            ft.Column(
                controls=category_controls,
                spacing=8,
                expand=True,
                tight=True,
            ),
        ],
        spacing=18,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    verdict_text = ft.Text(
        f"{txt['match_verdict_label']}: {verdict}" if verdict else "",
        color=theme.text_muted,
        size=12,
        italic=True,
    )

    columns_row = ft.ResponsiveRow(
        controls=[
            ft.Container(
                content=_bullet_column(theme, title=txt["match_matches_title"], items=[str(m) for m in matches], accent=_OK_COLOR, bullet_marker="✓"),
                col={"xs": 12, "md": 4},
            ),
            ft.Container(
                content=_bullet_column(theme, title=txt["match_gaps_title"], items=[str(g) for g in gaps], accent=_RISK_COLOR, bullet_marker="!"),
                col={"xs": 12, "md": 4},
            ),
            ft.Container(
                content=_ats_column(
                    theme,
                    title=txt["match_ats_title"],
                    present=[str(x) for x in ats_present],
                    missing=[str(x) for x in ats_missing],
                    present_label=txt["match_ats_present_label"],
                    missing_label=txt["match_ats_missing_label"],
                ),
                col={"xs": 12, "md": 4},
            ),
        ],
        spacing=12,
        run_spacing=12,
    )

    evidence_card = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    txt["match_evidence_title"],
                    color=theme.text_muted,
                    size=10,
                    weight=ft.FontWeight.W_700,
                    style=ft.TextStyle(letter_spacing=1.4),
                ),
                ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Container(
                                    width=6,
                                    height=6,
                                    bgcolor=theme.primary,
                                    border_radius=3,
                                    margin=ft.margin.only(top=8, right=10),
                                ),
                                ft.Text(str(e), color=theme.text, size=12, expand=True, selectable=True),
                            ],
                            spacing=0,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                        )
                        for e in evidence
                    ]
                    or [ft.Text("—", color=theme.text_subtle, size=12)],
                    spacing=4,
                    tight=True,
                ),
            ],
            spacing=8,
            tight=True,
        ),
        padding=14,
        bgcolor=theme.surface,
        border_radius=12,
        border=ft.border.all(1, theme.border),
    )

    body = ft.Column(
        controls=[
            top_row,
            verdict_text,
            ft.Container(height=4),
            columns_row,
            evidence_card,
        ],
        spacing=14,
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True,
        tight=True,
    )

    _render_button()

    footer = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[status_text],
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=[ft.Container(expand=True), button_holder],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=6,
            tight=True,
        ),
        padding=ft.padding.symmetric(horizontal=24, vertical=12),
        border=ft.border.only(top=ft.BorderSide(1, theme.border)),
        bgcolor=theme.bg,
    )

    return ft.Column(
        controls=[
            ft.Container(
                content=body,
                expand=True,
                padding=ft.padding.symmetric(horizontal=24, vertical=18),
            ),
            footer,
        ],
        spacing=0,
        expand=True,
        tight=True,
    )
