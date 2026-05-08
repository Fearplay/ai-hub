"""Documents tab - generated CV, cover letter, interview prep, exports.

Sub-tabs are document kinds. Each one renders the markdown body, a list of
"Problem N" inputs, a Refine button (which runs an LLM follow-up), and a
footer with export buttons. Generation and refinement run on a daemon
thread so the UI does not freeze; status feedback flows through inline
text and the right context panel's activity counter.

The Evidence document is hidden when no GitHub data is loaded - we don't
have anything truthful to put there.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from typing import Callable, Optional

import json

import flet as ft

from src.components.tab_bar import tab_bar
from src.services import exporter, store
from src.sections.ai_career import modern_cv_render, pipeline
from src.sections.ai_career.refs import REFS, safe
from src.sections.ai_career.state import (
    DOC_COVER_LETTER,
    DOC_EVIDENCE,
    DOC_INTERVIEW_PREP,
    DOC_KINDS,
    DOC_MATCH_REPORT,
    DOC_MODERN_CV,
    DOC_SKILL_GAP,
    DOC_TAILORED_CV,
    STATE,
    TAB_MATCH,
)
from src.sections.ai_career.strings import s
from src.theme import Theme


_DOC_TAB_LABEL_KEYS = {
    DOC_TAILORED_CV: "doc_tab_tailored_cv",
    DOC_MODERN_CV: "doc_tab_modern_cv",
    DOC_COVER_LETTER: "doc_tab_cover_letter",
    DOC_MATCH_REPORT: "doc_tab_match_report",
    DOC_INTERVIEW_PREP: "doc_tab_interview_prep",
    DOC_SKILL_GAP: "doc_tab_skill_gap",
    DOC_EVIDENCE: "doc_tab_evidence",
}

_DOC_FILE_BASENAMES = {
    DOC_TAILORED_CV: "Tailored_CV",
    DOC_MODERN_CV: "Modern_CV",
    DOC_COVER_LETTER: "Cover_Letter",
    DOC_MATCH_REPORT: "Match_Report",
    DOC_INTERVIEW_PREP: "Interview_Prep",
    DOC_SKILL_GAP: "Skill_Gap_Plan",
    DOC_EVIDENCE: "Evidence_Report",
}

# Per-kind export plan used by "Save complete analysis".
#
# The CVs ship as both HTML (open-in-browser preview) and PDF (the file
# the candidate sends to the recruiter). The Cover Letter is PDF-only by
# design - prose document; HTML markup tends to look worse than the PDF.
# The remaining narrative documents (match report, interview prep, etc.)
# get HTML + Markdown so the candidate can read them in a browser and
# also edit / quote from them in their notes.
_EXPORT_PLAN: dict[str, tuple[str, ...]] = {
    DOC_TAILORED_CV: ("html", "pdf"),
    DOC_MODERN_CV: ("html", "pdf"),
    DOC_COVER_LETTER: ("pdf",),
    DOC_MATCH_REPORT: ("html", "md"),
    DOC_INTERVIEW_PREP: ("html", "md"),
    DOC_SKILL_GAP: ("html", "md"),
    DOC_EVIDENCE: ("html", "md"),
}

# Document kinds that should render with the "modern" CSS / PDF style.
_MODERN_STYLE_DOCS: frozenset[str] = frozenset({DOC_MODERN_CV, DOC_COVER_LETTER})


def _visible_doc_kinds() -> list[str]:
    has_github = STATE.candidate is not None and STATE.candidate.get("github_present")
    return [k for k in DOC_KINDS if k != DOC_EVIDENCE or has_github]


def _flat_button(
    theme: Theme,
    label: str,
    *,
    icon: str | None = None,
    primary: bool = False,
    enabled: bool = True,
    on_click: Optional[Callable[[ft.ControlEvent], None]] = None,
) -> ft.Container:
    color = ft.Colors.WHITE if (primary and enabled) else (theme.text if enabled else theme.text_subtle)
    bg = theme.primary if (primary and enabled) else theme.surface_2
    border = None if (primary and enabled) else ft.border.all(1, theme.border)
    children: list[ft.Control] = []
    if icon:
        children.append(ft.Icon(icon, color=color, size=14))
    children.append(ft.Text(label, color=color, size=12, weight=ft.FontWeight.W_600))
    return ft.Container(
        content=ft.Row(controls=children, spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        bgcolor=bg,
        border=border,
        border_radius=10,
        ink=enabled,
        on_click=(on_click if enabled else None),
        opacity=1.0 if enabled else 0.55,
    )


def _ensure_run_folder(role: str) -> str:
    if STATE.last_run_folder and os.path.isdir(STATE.last_run_folder):
        return STATE.last_run_folder
    folder = store.new_run_dir(role or "ai-career-run")
    STATE.last_run_folder = str(folder)
    return STATE.last_run_folder


def _open_in_explorer(path: str) -> None:
    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


def _document_body(theme: Theme, txt: dict, kind: str) -> ft.Control:
    if kind == DOC_EVIDENCE and not (STATE.candidate and STATE.candidate.get("github_present")):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.LOCK_OUTLINE, color=theme.text_muted, size=36),
                    ft.Text(txt["doc_no_evidence_title"], color=theme.text, size=15, weight=ft.FontWeight.W_700),
                    ft.Text(txt["doc_no_evidence_desc"], color=theme.text_muted, size=12, text_align=ft.TextAlign.CENTER),
                ],
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=40,
            alignment=ft.Alignment.CENTER,
        )

    if kind == DOC_MODERN_CV:
        # Modern CV is the structured JSON payload + the dedicated
        # two-column renderer. Falls back to the empty placeholder when
        # the user hasn't generated it yet.
        if STATE.modern_cv_data:
            return modern_cv_render.render_view(theme, STATE.modern_cv_data)
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.HOURGLASS_EMPTY_ROUNDED, color=theme.text_muted, size=36),
                    ft.Text(txt["doc_empty_title"], color=theme.text, size=15, weight=ft.FontWeight.W_700),
                    ft.Text(txt["doc_empty_desc"], color=theme.text_muted, size=12, text_align=ft.TextAlign.CENTER),
                ],
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=30,
            alignment=ft.Alignment.CENTER,
        )

    body_text = STATE.documents.get(kind) or ""
    if not body_text:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.HOURGLASS_EMPTY_ROUNDED, color=theme.text_muted, size=36),
                    ft.Text(txt["doc_empty_title"], color=theme.text, size=15, weight=ft.FontWeight.W_700),
                    ft.Text(txt["doc_empty_desc"], color=theme.text_muted, size=12, text_align=ft.TextAlign.CENTER),
                ],
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=30,
            alignment=ft.Alignment.CENTER,
        )
    return ft.Container(
        content=ft.Markdown(
            body_text,
            extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
            selectable=True,
        ),
        padding=18,
        bgcolor=theme.surface,
        border=ft.border.all(1, theme.border),
        border_radius=12,
    )


def _problem_inputs(
    theme: Theme,
    txt: dict,
    kind: str,
    *,
    on_dirty: Callable[[], None],
) -> tuple[ft.Container, Callable[[], list[str]]]:
    problems = STATE.refine_problems.setdefault(kind, [""])
    if not problems:
        problems.append("")

    fields_holder = ft.Column(spacing=8, tight=True)
    field_refs: list[ft.TextField] = []

    def _build_field(idx: int, value: str) -> ft.Row:
        field = ft.TextField(
            value=value,
            hint_text=txt["problem_hint"].format(n=idx + 1),
            text_style=ft.TextStyle(color=theme.text, size=12),
            hint_style=ft.TextStyle(color=theme.text_subtle, size=12),
            bgcolor=theme.surface_2,
            border=ft.InputBorder.NONE,
            filled=True,
            cursor_color=theme.primary,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border_radius=10,
            expand=True,
            on_change=lambda e, i=idx: _update_value(i, e.control.value or ""),
        )
        field_refs.append(field)
        return ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text(txt["problem_label_template"].format(n=idx + 1), color=theme.text, size=11, weight=ft.FontWeight.W_700),
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    bgcolor=theme.surface_2,
                    border_radius=8,
                    border=ft.border.all(1, theme.border),
                ),
                field,
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _rebuild() -> None:
        fields_holder.controls = [
            _build_field(i, v) for i, v in enumerate(problems)
        ]
        try:
            fields_holder.update()
        except Exception:
            pass

    def _update_value(idx: int, value: str) -> None:
        if 0 <= idx < len(problems):
            problems[idx] = value

    def _add_problem(_e: ft.ControlEvent) -> None:
        problems.append("")
        _rebuild()
        on_dirty()

    add_btn = ft.Container(
        content=ft.Text(
            txt["add_problem_btn"],
            color=theme.primary,
            size=12,
            weight=ft.FontWeight.W_600,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        ink=True,
        on_click=_add_problem,
    )

    _rebuild()

    body = ft.Container(
        content=ft.Column(
            controls=[
                fields_holder,
                add_btn,
            ],
            spacing=8,
            tight=True,
        ),
    )

    def _values() -> list[str]:
        return [p for p in problems if p.strip()]

    return body, _values


def _build_active_doc_panel(
    theme: Theme,
    lang: str,
    txt: dict,
    kind: str,
    *,
    on_request_rerender: Callable[[], None],
    show_status: Callable[[str, bool], None],
) -> ft.Control:
    body_holder = ft.Container(content=_document_body(theme, txt, kind), expand=True)

    def _refresh_body() -> None:
        body_holder.content = _document_body(theme, txt, kind)
        try:
            body_holder.update()
        except Exception:
            pass

    if kind == DOC_MODERN_CV:
        # Modern CV is keyed off ``STATE.modern_cv_data`` (structured
        # JSON), not ``STATE.documents`` which holds markdown bodies.
        has_text = bool(STATE.modern_cv_data)
    else:
        has_text = bool(STATE.documents.get(kind))
    is_evidence_locked = (
        kind == DOC_EVIDENCE
        and not (STATE.candidate and STATE.candidate.get("github_present"))
    )

    refine_problems_block, get_problem_values = _problem_inputs(theme, txt, kind, on_dirty=lambda: None)

    refine_running: dict[str, bool] = {"value": False}
    refine_button_holder = ft.Container()
    generate_button_holder = ft.Container()

    def _render_buttons() -> None:
        running = refine_running["value"]
        refine_button_holder.content = _flat_button(
            theme,
            txt["refine_running"] if running else txt["refine_btn"],
            icon=ft.Icons.AUTO_FIX_HIGH,
            primary=True,
            enabled=has_text and not running and not is_evidence_locked,
            on_click=lambda e: _start_refine(),
        )
        try:
            refine_button_holder.update()
        except Exception:
            pass
        generate_label = txt["doc_running"] if running else (
            txt["doc_regenerate_btn"] if has_text else txt["doc_generate_btn"]
        )
        generate_button_holder.content = _flat_button(
            theme,
            generate_label,
            icon=ft.Icons.AUTO_AWESOME,
            primary=not has_text,
            enabled=not running and not is_evidence_locked,
            on_click=lambda e: _start_generate(),
        )
        try:
            generate_button_holder.update()
        except Exception:
            pass

    def _start_generate() -> None:
        refine_running["value"] = True
        show_status(txt["doc_running"], False)
        _render_buttons()

        def _worker() -> None:
            try:
                result = pipeline.generate_document(kind, output_lang=lang)
                if result.ok:
                    show_status("", False)
                    nonlocal has_text
                    if kind == DOC_MODERN_CV:
                        has_text = bool(STATE.modern_cv_data)
                    else:
                        has_text = bool(STATE.documents.get(kind))
                    _refresh_body()
                else:
                    show_status(result.error, True)
            finally:
                refine_running["value"] = False
                _render_buttons()

        threading.Thread(target=_worker, daemon=True).start()

    def _start_refine() -> None:
        problems = get_problem_values()
        if not problems:
            show_status(txt["problem_hint"].format(n=1), True)
            return
        refine_running["value"] = True
        show_status(txt["refine_running"], False)
        _render_buttons()

        def _worker() -> None:
            try:
                result = pipeline.refine_document(kind, output_lang=lang, problems=problems)
                if result.ok:
                    show_status("", False)
                    _refresh_body()
                else:
                    show_status(result.error, True)
            finally:
                refine_running["value"] = False
                _render_buttons()

        threading.Thread(target=_worker, daemon=True).start()

    _render_buttons()

    return ft.Column(
        controls=[
            ft.Container(content=body_holder, expand=True),
            ft.Container(
                content=ft.Column(
                    controls=[
                        refine_problems_block,
                        ft.Row(
                            controls=[
                                generate_button_holder,
                                ft.Container(expand=True),
                                refine_button_holder,
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=10,
                    tight=True,
                ),
                padding=ft.padding.symmetric(horizontal=18, vertical=12),
                bgcolor=theme.surface,
                border=ft.border.only(top=ft.BorderSide(1, theme.border)),
                border_radius=12,
                margin=ft.margin.only(top=12),
            ),
        ],
        spacing=0,
        expand=True,
        tight=True,
    )


def build_documents_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Callable[[], None],
    on_navigate_tab: Callable[[int], None],
) -> ft.Control:
    txt = s(lang)

    visible_kinds = _visible_doc_kinds()
    if not visible_kinds:
        visible_kinds = list(DOC_KINDS)
    if STATE.active_document not in visible_kinds:
        STATE.active_document = visible_kinds[0]

    tab_labels = [txt[_DOC_TAB_LABEL_KEYS[k]] for k in visible_kinds]

    body_holder = ft.Container(expand=True)
    status_text = ft.Text("", color=theme.text_muted, size=11)

    def _show_status(message: str, is_error: bool) -> None:
        status_text.value = message
        status_text.color = "#EF4444" if (is_error and message) else theme.text_muted
        try:
            status_text.update()
        except Exception:
            pass

    def _refresh_body() -> None:
        # In-place swap of the doc panel - cheaper than a full section
        # rebuild when the user is just flipping between sub-tabs and
        # everything else (header, stage tab bar, footer) is unchanged.
        body_holder.content = _build_active_doc_panel(
            theme,
            lang,
            txt,
            STATE.active_document,
            on_request_rerender=on_request_rerender,
            show_status=_show_status,
        )
        try:
            body_holder.update()
        except Exception:
            pass

    tab_bar_holder = ft.Container()

    def _refresh_tab_bar() -> None:
        # Rebuilding the whole tab_bar widget is the cheapest way to move
        # the active-state highlight to the clicked tab; the underlying
        # ``_tab`` controls bake the bold + underline into their initial
        # render and don't reactively update when ``active_index`` changes.
        tab_bar_holder.content = tab_bar(
            theme,
            tabs=tab_labels,
            active_index=visible_kinds.index(STATE.active_document),
            on_change=_on_doc_tab,
        )
        try:
            tab_bar_holder.update()
        except Exception:
            pass

    def _on_doc_tab(idx: int) -> None:
        STATE.active_document = visible_kinds[idx]
        _refresh_tab_bar()
        _refresh_body()

    _refresh_tab_bar()
    _refresh_body()

    def _export(kind_action: str) -> None:
        kind = STATE.active_document
        # Modern CV is structured JSON, the others are markdown bodies.
        if kind == DOC_MODERN_CV:
            has_payload = bool(STATE.modern_cv_data)
            text = ""
        else:
            text = STATE.documents.get(kind, "")
            has_payload = bool(text)

        if not has_payload and kind_action != "all":
            _show_status(txt["doc_empty_title"], True)
            return
        role = ""
        if STATE.job_spec:
            role = str(STATE.job_spec.get("title") or "")
        folder = _ensure_run_folder(role)

        _show_status(txt["export_running"], False)

        def _worker() -> None:
            try:
                from pathlib import Path

                folder_path = Path(folder)
                if kind_action == "all":
                    save = pipeline.save_full_analysis()
                    if save.ok:
                        _show_status(
                            txt["export_ok_template"].format(path=save.folder),
                            False,
                        )
                    else:
                        _show_status(txt["doc_empty_title"], True)
                    return
                basename = _DOC_FILE_BASENAMES.get(kind, kind)
                title = basename.replace("_", " ")
                style = "modern" if kind in _MODERN_STYLE_DOCS else "ats"

                # Modern CV ships from the dedicated two-column renderer
                # so the HTML / PDF look exactly like the in-app preview.
                if kind == DOC_MODERN_CV:
                    target_html = folder_path / f"{basename}.html"
                    target_pdf = folder_path / f"{basename}.pdf"
                    if kind_action == "html":
                        target_html.parent.mkdir(parents=True, exist_ok=True)
                        target_html.write_text(
                            modern_cv_render.render_html(STATE.modern_cv_data),
                            encoding="utf-8",
                        )
                        path = target_html
                    elif kind_action == "pdf":
                        path = modern_cv_render.render_pdf(STATE.modern_cv_data, target_pdf)
                    elif kind_action == "md":
                        # Escape hatch: dump the structured payload as
                        # JSON so the user can grab the raw fields.
                        target_md = folder_path / f"{basename}.json"
                        target_md.parent.mkdir(parents=True, exist_ok=True)
                        target_md.write_text(
                            json.dumps(STATE.modern_cv_data or {}, indent=2, ensure_ascii=False),
                            encoding="utf-8",
                        )
                        path = target_md
                    elif kind_action == "docx":
                        _show_status(
                            txt["export_failed_template"].format(
                                error="DOCX is not supported for the Modern CV - export HTML or PDF instead."
                            ),
                            True,
                        )
                        return
                    else:
                        return
                    _show_status(txt["export_ok_template"].format(path=str(path)), False)
                    return

                if kind_action == "md":
                    path = exporter.export_markdown(text, folder_path / f"{basename}.md")
                elif kind_action == "html":
                    path = exporter.export_html(
                        text, folder_path / f"{basename}.html", title=title, style=style
                    )
                elif kind_action == "docx":
                    path = exporter.export_docx(text, folder_path / f"{basename}.docx", title=title)
                elif kind_action == "pdf":
                    path = exporter.export_pdf(
                        text, folder_path / f"{basename}.pdf", title=title, style=style
                    )
                else:
                    return
                _show_status(txt["export_ok_template"].format(path=str(path)), False)
            except Exception as exc:
                _show_status(txt["export_failed_template"].format(error=str(exc)), True)

        threading.Thread(target=_worker, daemon=True).start()

    footer = ft.Container(
        content=ft.Column(
            controls=[
                status_text,
                ft.Row(
                    controls=[
                        _flat_button(
                            theme,
                            txt["doc_back_btn"],
                            icon=ft.Icons.ARROW_BACK,
                            on_click=lambda e: on_navigate_tab(TAB_MATCH),
                        ),
                        ft.Container(expand=True),
                        _flat_button(theme, txt["export_md_btn"], icon=ft.Icons.NOTES, on_click=lambda e: _export("md")),
                        _flat_button(theme, txt["export_html_btn"], icon=ft.Icons.HTML, on_click=lambda e: _export("html")),
                        _flat_button(theme, txt["export_docx_btn"], icon=ft.Icons.DESCRIPTION, on_click=lambda e: _export("docx")),
                        _flat_button(theme, txt["export_pdf_btn"], icon=ft.Icons.PICTURE_AS_PDF, on_click=lambda e: _export("pdf")),
                        _flat_button(theme, txt["export_all_btn"], icon=ft.Icons.SAVE_OUTLINED, primary=True, on_click=lambda e: _export("all")),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=8,
            tight=True,
        ),
        padding=ft.padding.symmetric(horizontal=24, vertical=12),
        border=ft.border.only(top=ft.BorderSide(1, theme.border)),
        bgcolor=theme.bg,
    )

    return ft.Column(
        controls=[
            tab_bar_holder,
            ft.Container(content=body_holder, expand=True, padding=ft.padding.symmetric(horizontal=18, vertical=14)),
            footer,
        ],
        spacing=0,
        expand=True,
        tight=True,
    )
