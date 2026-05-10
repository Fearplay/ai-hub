"""Documents tab - generated CV, cover letter, interview prep, exports (PySide6 port)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.components.tab_bar import tab_bar
from src.qt.icons import Icons
from src.qt.runtime import dispatch as runtime_dispatch
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    GhostButton,
    IconLabel,
    MutedLabel,
    PrimaryButton,
    SubtleLabel,
    TitleLabel,
    custom_label,
    hbox,
    themed_line_edit,
    vbox,
)
from src.services import exporter, store
from src.services import logger as logger_service
from src.sections.ai_career import modern_cv_render, pipeline, themes
from src.sections.ai_career.refs import REFS
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


_THEME_PALETTE_DOCS: frozenset[str] = frozenset({DOC_MODERN_CV, DOC_COVER_LETTER})
_THEME_LAYOUT_DOCS: frozenset[str] = frozenset({DOC_MODERN_CV})

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

_MODERN_STYLE_DOCS: frozenset[str] = frozenset({DOC_MODERN_CV, DOC_COVER_LETTER})


def _resolved_output_lang(ui_lang: str) -> str:
    selected = (STATE.document_output_lang or "").strip().lower()
    if selected in ("en", "cs"):
        return selected
    return "en" if ui_lang == "en" else "cs"


def _visible_doc_kinds() -> list[str]:
    has_github = STATE.candidate is not None and STATE.candidate.get("github_present")
    return [k for k in DOC_KINDS if k != DOC_EVIDENCE or has_github]


def _palette_display_name(slug: str, lang: str) -> str:
    palette = themes.PALETTES.get(slug)
    if palette is None:
        palette = themes.PALETTES[themes.DEFAULT_PALETTE]
    code = (lang or "en").strip().lower()
    if code == "cs":
        return palette.display_name_cs
    return palette.display_name_en


def _layout_display_name(slug: str, txt: dict) -> str:
    key = f"doc_layout_{slug}"
    return txt.get(key) or slug.replace("_", " ").title()


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
    except Exception as exc:
        logger_service.log_exception(
            "ai_career.tab_documents", "open_in_explorer_failed", exc, path=path,
        )


def _empty_card(theme: Theme, txt: dict, icon: str, *, title_key: str, desc_key: str) -> QWidget:
    holder = QWidget()
    holder.setStyleSheet(f"background-color: {theme.bg};")
    holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    layout = vbox(spacing=10, margins=(40, 40, 40, 40))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    holder.setLayout(layout)
    layout.addWidget(IconLabel(icon, color=theme.text_muted, size=36),
                     alignment=Qt.AlignmentFlag.AlignHCenter)
    title_label = TitleLabel(txt[title_key], theme=theme, size=15, weight=QFont.Weight.Bold)
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title_label.setMinimumWidth(360)
    layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)
    desc = MutedLabel(txt[desc_key], theme=theme, size=12)
    desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
    desc.setMinimumWidth(360)
    layout.addWidget(desc, alignment=Qt.AlignmentFlag.AlignHCenter)
    return holder


def _markdown_card(theme: Theme, body_text: str) -> QFrame:
    card = QFrame()
    card.setObjectName("DocMarkdownCard")
    card.setStyleSheet(
        f"""
        QFrame#DocMarkdownCard {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        """
    )
    layout = vbox(spacing=0, margins=(18, 18, 18, 18))
    card.setLayout(layout)
    label = BodyLabel(body_text, theme=theme, size=13, selectable=True)
    label.setTextFormat(Qt.TextFormat.MarkdownText)
    label.setWordWrap(True)
    layout.addWidget(label)
    return card


def _document_body(theme: Theme, txt: dict, kind: str) -> QWidget:
    if kind == DOC_EVIDENCE and not (STATE.candidate and STATE.candidate.get("github_present")):
        return _empty_card(theme, txt, Icons.LOCK_OUTLINE, title_key="doc_no_evidence_title", desc_key="doc_no_evidence_desc")

    if kind == DOC_MODERN_CV:
        if STATE.modern_cv_data:
            return modern_cv_render.render_view(theme, STATE.modern_cv_data)
        return _empty_card(theme, txt, Icons.HOURGLASS_EMPTY_ROUNDED, title_key="doc_empty_title", desc_key="doc_empty_desc")

    body_text = STATE.documents.get(kind) or ""
    if not body_text:
        return _empty_card(theme, txt, Icons.HOURGLASS_EMPTY_ROUNDED, title_key="doc_empty_title", desc_key="doc_empty_desc")
    return _markdown_card(theme, body_text)


def _theme_controls(
    theme: Theme,
    lang: str,
    txt: dict,
    kind: str,
    *,
    on_changed: Callable[[], None],
) -> Optional[QFrame]:
    if kind not in _THEME_PALETTE_DOCS:
        return None

    state_theme = STATE.modern_cv_theme or {}
    palette_slug = (state_theme.get("palette") or themes.DEFAULT_PALETTE).strip().lower()
    layout_slug = (state_theme.get("layout") or themes.DEFAULT_LAYOUT).strip().lower()
    if palette_slug not in themes.PALETTES:
        palette_slug = themes.DEFAULT_PALETTE
    if layout_slug not in themes.LAYOUTS:
        layout_slug = themes.DEFAULT_LAYOUT
    palette_color = themes.PALETTES[palette_slug].accent

    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = hbox(spacing=8, margins=(0, 0, 0, 10))
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    holder.setLayout(layout)

    palette_chip = QFrame()
    palette_chip.setObjectName("DocPaletteChip")
    palette_chip.setStyleSheet(
        f"""
        QFrame#DocPaletteChip {{
            background-color: {theme.surface_2};
            border: 1px solid {theme.border};
            border-radius: 10px;
        }}
        """
    )
    pl = hbox(spacing=6, margins=(10, 6, 10, 6))
    pl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    palette_chip.setLayout(pl)
    swatch = QFrame()
    swatch.setFixedSize(12, 12)
    swatch.setStyleSheet(f"background-color: {palette_color}; border-radius: 6px; border: 1px solid {rgba('#000000', 0.20)};")
    pl.addWidget(swatch)
    pl.addWidget(MutedLabel(
        txt["doc_theme_color_label"].format(name=_palette_display_name(palette_slug, lang)),
        theme=theme, size=11,
    ))
    layout.addWidget(palette_chip)

    cycle_palette = GhostButton(txt["doc_change_color_btn"], theme=theme, icon=Icons.PALETTE_OUTLINED)
    def _do_cycle_palette() -> None:
        current = (STATE.modern_cv_theme or {}).get("palette") or themes.DEFAULT_PALETTE
        next_slug = themes.pick_next_palette(current)
        STATE.modern_cv_theme = {**(STATE.modern_cv_theme or {}), "palette": next_slug}
        on_changed()
    cycle_palette.clicked.connect(_do_cycle_palette)
    layout.addWidget(cycle_palette)

    if kind in _THEME_LAYOUT_DOCS:
        layout_chip = QFrame()
        layout_chip.setObjectName("DocLayoutChip")
        layout_chip.setStyleSheet(
            f"""
            QFrame#DocLayoutChip {{
                background-color: {theme.surface_2};
                border: 1px solid {theme.border};
                border-radius: 10px;
            }}
            """
        )
        ll = hbox(spacing=6, margins=(10, 6, 10, 6))
        layout_chip.setLayout(ll)
        ll.addWidget(MutedLabel(
            txt["doc_theme_layout_label"].format(name=_layout_display_name(layout_slug, txt)),
            theme=theme, size=11,
        ))
        layout.addWidget(layout_chip)

        cycle_layout = GhostButton(txt["doc_change_layout_btn"], theme=theme, icon=Icons.VIEW_QUILT_OUTLINED)
        def _do_cycle_layout() -> None:
            current = (STATE.modern_cv_theme or {}).get("layout") or themes.DEFAULT_LAYOUT
            next_slug = themes.pick_next_layout(current)
            STATE.modern_cv_theme = {**(STATE.modern_cv_theme or {}), "layout": next_slug}
            on_changed()
        cycle_layout.clicked.connect(_do_cycle_layout)
        layout.addWidget(cycle_layout)
    layout.addStretch(1)
    return holder


def _problem_inputs(theme: Theme, txt: dict, kind: str) -> tuple[QFrame, Callable[[], List[str]]]:
    problems = STATE.refine_problems.setdefault(kind, [""])
    if not problems:
        problems.append("")

    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    holder.setLayout(layout)

    fields: list[QFrame] = []

    def _build_field(idx: int, value: str) -> QFrame:
        row = QFrame()
        row.setStyleSheet("background: transparent;")
        rl = hbox(spacing=8, margins=(0, 0, 0, 0))
        rl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        row.setLayout(rl)

        label_chip = QFrame()
        label_chip.setObjectName("DocProblemLabelChip")
        label_chip.setStyleSheet(
            f"""
            QFrame#DocProblemLabelChip {{
                background-color: {theme.surface_2};
                border: 1px solid {theme.border};
                border-radius: 8px;
            }}
            """
        )
        ll = hbox(spacing=0, margins=(10, 6, 10, 6))
        label_chip.setLayout(ll)
        ll.addWidget(BodyLabel(txt["problem_label_template"].format(n=idx + 1), theme=theme, size=11, weight=QFont.Weight.Bold))
        rl.addWidget(label_chip)

        field = themed_line_edit(theme, placeholder=txt["problem_hint"].format(n=idx + 1))
        field.setText(value)
        def _update(text_value: str, i=idx) -> None:
            if 0 <= i < len(problems):
                problems[i] = text_value
        field.textChanged.connect(_update)
        rl.addWidget(field, 1)
        return row

    def _rebuild() -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()
        fields.clear()
        for i, v in enumerate(problems):
            row = _build_field(i, v)
            fields.append(row)
            layout.addWidget(row)
        add_btn = GhostButton(txt["add_problem_btn"], theme=theme, icon=Icons.ADD)
        add_btn.clicked.connect(_on_add)
        layout.addWidget(add_btn, 0, Qt.AlignmentFlag.AlignLeft)

    def _on_add() -> None:
        problems.append("")
        _rebuild()

    _rebuild()

    def _values() -> list[str]:
        return [p for p in problems if p.strip()]

    return holder, _values


def _build_active_doc_panel(
    theme: Theme,
    lang: str,
    txt: dict,
    kind: str,
    *,
    on_request_rerender: Callable[[], None],
    show_status: Callable[[str, bool], None],
) -> QWidget:
    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    body_holder = QWidget()
    body_holder.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    body_holder.setLayout(body_layout)

    def _refresh_body() -> None:
        while body_layout.count():
            item = body_layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()
        body_layout.addWidget(_document_body(theme, txt, kind))

    theme_controls_holder = QWidget()
    theme_controls_holder.setStyleSheet("background: transparent;")
    tch_layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    theme_controls_holder.setLayout(tch_layout)

    def _refresh_theme_controls() -> None:
        while tch_layout.count():
            item = tch_layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()
        ctrl = _theme_controls(theme, lang, txt, kind, on_changed=_refresh_body_and_controls)
        if ctrl is not None:
            tch_layout.addWidget(ctrl)

    def _refresh_body_and_controls() -> None:
        _refresh_body()
        _refresh_theme_controls()

    _refresh_body()
    _refresh_theme_controls()

    layout.addWidget(theme_controls_holder)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(body_holder)
    layout.addWidget(scroll, 1)

    if kind == DOC_MODERN_CV:
        has_text = bool(STATE.modern_cv_data)
    else:
        has_text = bool(STATE.documents.get(kind))
    is_evidence_locked = (
        kind == DOC_EVIDENCE
        and not (STATE.candidate and STATE.candidate.get("github_present"))
    )

    refine_block, get_problem_values = _problem_inputs(theme, txt, kind)
    refine_running = {"value": False}

    refine_card = QFrame()
    refine_card.setObjectName("DocRefineCard")
    refine_card.setStyleSheet(
        f"""
        QFrame#DocRefineCard {{
            background-color: {theme.surface};
            border-top: 1px solid {theme.border};
        }}
        """
    )
    rc_layout = vbox(spacing=10, margins=(18, 12, 18, 12))
    refine_card.setLayout(rc_layout)
    rc_layout.addWidget(refine_block)
    btn_row = QFrame()
    btn_row.setStyleSheet("background: transparent;")
    br_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    br_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    btn_row.setLayout(br_layout)
    generate_btn = PrimaryButton(txt["doc_generate_btn"], theme=theme, icon=Icons.AUTO_AWESOME)
    refine_btn = PrimaryButton(txt["refine_btn"], theme=theme, icon=Icons.AUTO_FIX_HIGH)
    br_layout.addWidget(generate_btn)
    br_layout.addStretch(1)
    br_layout.addWidget(refine_btn)
    rc_layout.addWidget(btn_row)
    layout.addWidget(refine_card)

    def _refresh_buttons() -> None:
        running = refine_running["value"]
        nonlocal has_text
        if kind == DOC_MODERN_CV:
            has_text = bool(STATE.modern_cv_data)
        else:
            has_text = bool(STATE.documents.get(kind))
        generate_btn.setEnabled(not running and not is_evidence_locked)
        refine_btn.setEnabled(has_text and not running and not is_evidence_locked)
        generate_btn.setText(
            txt["doc_running"] if running else (
                txt["doc_regenerate_btn"] if has_text else txt["doc_generate_btn"]
            )
        )
        refine_btn.setText(txt["refine_running"] if running else txt["refine_btn"])

    _refresh_buttons()

    def _start_generate() -> None:
        refine_running["value"] = True
        show_status(txt["doc_running"], False)
        runtime_dispatch(_refresh_buttons)
        doc_lang = _resolved_output_lang(lang)
        STATE.document_output_lang = doc_lang

        def _worker() -> None:
            try:
                result = pipeline.generate_document(kind, output_lang=doc_lang)
                if result.ok:
                    runtime_dispatch(lambda: show_status("", False))
                    runtime_dispatch(_refresh_body)
                else:
                    runtime_dispatch(lambda: show_status(result.error, True))
            finally:
                refine_running["value"] = False
                runtime_dispatch(_refresh_buttons)
        threading.Thread(target=_worker, daemon=True).start()

    def _start_refine() -> None:
        problems = get_problem_values()
        if not problems:
            show_status(txt["problem_hint"].format(n=1), True)
            return
        refine_running["value"] = True
        show_status(txt["refine_running"], False)
        runtime_dispatch(_refresh_buttons)
        doc_lang = _resolved_output_lang(lang)
        STATE.document_output_lang = doc_lang

        def _worker() -> None:
            try:
                result = pipeline.refine_document(kind, output_lang=doc_lang, problems=problems)
                if result.ok:
                    runtime_dispatch(lambda: show_status("", False))
                    runtime_dispatch(_refresh_body)
                else:
                    runtime_dispatch(lambda: show_status(result.error, True))
            finally:
                refine_running["value"] = False
                runtime_dispatch(_refresh_buttons)
        threading.Thread(target=_worker, daemon=True).start()

    generate_btn.clicked.connect(_start_generate)
    refine_btn.clicked.connect(_start_refine)
    return container


def build_documents_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Callable[[], None],
    on_navigate_tab: Callable[[int], None],
) -> QWidget:
    txt = s(lang)

    visible_kinds = _visible_doc_kinds()
    if not visible_kinds:
        visible_kinds = list(DOC_KINDS)
    if STATE.active_document not in visible_kinds:
        STATE.active_document = visible_kinds[0]

    tab_labels = [txt[_DOC_TAB_LABEL_KEYS[k]] for k in visible_kinds]

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    tab_holder = QWidget()
    tab_holder.setStyleSheet("background: transparent;")
    tab_layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    tab_holder.setLayout(tab_layout)

    body_holder = QWidget()
    body_holder.setStyleSheet(f"background-color: {theme.bg};")
    body_layout = vbox(spacing=0, margins=(18, 14, 18, 14))
    body_holder.setLayout(body_layout)
    layout.addWidget(tab_holder)
    layout.addWidget(body_holder, 1)

    status_label = SubtleLabel("", theme=theme, size=11)

    def _show_status(message: str, is_error: bool) -> None:
        status_label.setText(message)
        status_label.setStyleSheet(
            f"color: {'#EF4444' if (is_error and message) else theme.text_muted}; background: transparent;"
        )

    def _refresh_body() -> None:
        while body_layout.count():
            item = body_layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()
        body_layout.addWidget(_build_active_doc_panel(
            theme, lang, txt, STATE.active_document,
            on_request_rerender=on_request_rerender,
            show_status=_show_status,
        ))

    def _refresh_tab_bar() -> None:
        while tab_layout.count():
            item = tab_layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()
        tab_layout.addWidget(tab_bar(
            theme,
            tabs=tab_labels,
            active_index=visible_kinds.index(STATE.active_document),
            on_change=_on_doc_tab,
        ))

    def _on_doc_tab(idx: int) -> None:
        new_doc = visible_kinds[idx]
        STATE.active_document = new_doc
        _refresh_tab_bar()
        _refresh_body()

    _refresh_tab_bar()
    _refresh_body()

    def _export(action: str) -> None:
        kind = STATE.active_document
        if kind == DOC_MODERN_CV:
            has_payload = bool(STATE.modern_cv_data)
            text = ""
        else:
            text = STATE.documents.get(kind, "")
            has_payload = bool(text)

        if not has_payload and action != "all":
            _show_status(txt["doc_empty_title"], True)
            return

        role = ""
        if STATE.job_spec:
            role = str(STATE.job_spec.get("title") or "")
        folder = _ensure_run_folder(role)
        _show_status(txt["export_running"], False)

        def _worker() -> None:
            try:
                folder_path = Path(folder)
                if action == "all":
                    save = pipeline.save_full_analysis()
                    if save.ok:
                        runtime_dispatch(lambda: _show_status(
                            txt["export_ok_template"].format(path=save.folder), False))
                    else:
                        runtime_dispatch(lambda: _show_status(txt["doc_empty_title"], True))
                    return

                basename = _DOC_FILE_BASENAMES.get(kind, kind)
                title = basename.replace("_", " ")
                style = "modern" if kind in _MODERN_STYLE_DOCS else "ats"

                if kind == DOC_MODERN_CV:
                    target_html = folder_path / f"{basename}.html"
                    target_pdf = folder_path / f"{basename}.pdf"
                    if action == "html":
                        target_html.parent.mkdir(parents=True, exist_ok=True)
                        target_html.write_text(modern_cv_render.render_html(STATE.modern_cv_data), encoding="utf-8")
                        path = target_html
                    elif action == "pdf":
                        path = modern_cv_render.render_pdf(STATE.modern_cv_data, target_pdf)
                    elif action == "md":
                        target_md = folder_path / f"{basename}.json"
                        target_md.parent.mkdir(parents=True, exist_ok=True)
                        target_md.write_text(json.dumps(STATE.modern_cv_data or {}, indent=2, ensure_ascii=False), encoding="utf-8")
                        path = target_md
                    elif action == "docx":
                        runtime_dispatch(lambda: _show_status(
                            txt["export_failed_template"].format(error="DOCX is not supported for the Modern CV - export HTML or PDF instead."),
                            True,
                        ))
                        return
                    else:
                        return
                    runtime_dispatch(lambda p=path: _show_status(txt["export_ok_template"].format(path=str(p)), False))
                    return

                if kind == DOC_COVER_LETTER and action in ("pdf", "html"):
                    state_theme = STATE.modern_cv_theme or {}
                    active_theme = themes.resolve_theme(state_theme.get("palette"), state_theme.get("layout"))
                    cover_lang = _resolved_output_lang(lang)
                    name = ""
                    contact: dict[str, str] = {}
                    if isinstance(STATE.modern_cv_data, dict):
                        name = str(STATE.modern_cv_data.get("full_name") or "")
                        cd = STATE.modern_cv_data.get("contact") or {}
                        if isinstance(cd, dict):
                            contact = {
                                "location": str(cd.get("location") or ""),
                                "email": str(cd.get("email") or ""),
                                "phone": str(cd.get("phone") or ""),
                            }
                    if not name and isinstance(STATE.candidate, dict):
                        name = str(STATE.candidate.get("full_name") or "")
                    cover_html = themes.render_cover_letter_html(
                        text,
                        candidate_name=name,
                        candidate_contact=contact,
                        theme=active_theme,
                        output_lang=cover_lang,
                    )
                    if action == "html":
                        target_html = folder_path / f"{basename}.html"
                        target_html.parent.mkdir(parents=True, exist_ok=True)
                        target_html.write_text(cover_html, encoding="utf-8")
                        path = target_html
                    else:
                        from src.services import html_pdf
                        target_pdf = folder_path / f"{basename}.pdf"
                        try:
                            html_pdf.render_html_to_pdf(cover_html, target_pdf)
                            path = target_pdf
                        except html_pdf.PdfRendererUnavailableError:
                            path = exporter.export_pdf(text, target_pdf, title=title, style=style)
                    runtime_dispatch(lambda p=path: _show_status(txt["export_ok_template"].format(path=str(p)), False))
                    return

                if action == "md":
                    path = exporter.export_markdown(text, folder_path / f"{basename}.md")
                elif action == "html":
                    path = exporter.export_html(text, folder_path / f"{basename}.html", title=title, style=style)
                elif action == "docx":
                    path = exporter.export_docx(text, folder_path / f"{basename}.docx", title=title)
                elif action == "pdf":
                    path = exporter.export_pdf(text, folder_path / f"{basename}.pdf", title=title, style=style)
                else:
                    return
                runtime_dispatch(lambda p=path: _show_status(txt["export_ok_template"].format(path=str(p)), False))
            except Exception as exc:
                logger_service.log_exception(
                    "ai_career.tab_documents", "export_failed", exc, kind=kind, action=action,
                )
                runtime_dispatch(lambda e=exc: _show_status(txt["export_failed_template"].format(error=str(e)), True))

        threading.Thread(target=_worker, daemon=True).start()

    footer = QFrame()
    footer.setObjectName("DocFooter")
    footer.setStyleSheet(
        f"""
        QFrame#DocFooter {{
            background-color: {theme.bg};
            border-top: 1px solid {theme.border};
        }}
        """
    )
    footer_layout = vbox(spacing=8, margins=(24, 12, 24, 12))
    footer.setLayout(footer_layout)
    footer_layout.addWidget(status_label)

    btn_row = QFrame()
    btn_row.setStyleSheet("background: transparent;")
    br_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    br_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    btn_row.setLayout(br_layout)

    back_btn = GhostButton(txt["doc_back_btn"], theme=theme, icon=Icons.ARROW_BACK)
    back_btn.clicked.connect(lambda: on_navigate_tab(TAB_MATCH))
    br_layout.addWidget(back_btn)
    br_layout.addStretch(1)

    md_btn = GhostButton(txt["export_md_btn"], theme=theme, icon=Icons.NOTES)
    md_btn.clicked.connect(lambda: _export("md"))
    br_layout.addWidget(md_btn)
    html_btn = GhostButton(txt["export_html_btn"], theme=theme, icon=Icons.HTML)
    html_btn.clicked.connect(lambda: _export("html"))
    br_layout.addWidget(html_btn)
    docx_btn = GhostButton(txt["export_docx_btn"], theme=theme, icon=Icons.DESCRIPTION)
    docx_btn.clicked.connect(lambda: _export("docx"))
    br_layout.addWidget(docx_btn)
    pdf_btn = GhostButton(txt["export_pdf_btn"], theme=theme, icon=Icons.PICTURE_AS_PDF)
    pdf_btn.clicked.connect(lambda: _export("pdf"))
    br_layout.addWidget(pdf_btn)
    all_btn = PrimaryButton(txt["export_all_btn"], theme=theme, icon=Icons.SAVE_OUTLINED)
    all_btn.clicked.connect(lambda: _export("all"))
    br_layout.addWidget(all_btn)
    footer_layout.addWidget(btn_row)
    layout.addWidget(footer)
    return container
