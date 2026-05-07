"""AI Doc Assistant - center column view.

Header (with the help dialog button) + 3 tabs:

* **Upload** - drop a PDF / DOCX / TXT / MD / HTML and see a preview.
* **Analyze** - pick an action (summary / Q&A / rewrite / extract) +
  the per-action inputs, then click Run. The pipeline call lives on a
  background thread so the UI stays responsive.
* **Output** - render the structured result of the last action.

State that must survive theme / language / tab toggles lives in
:mod:`src.sections.ai_doc_assistant.state`.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

import flet as ft

from src.components.header import header
from src.components.tab_bar import tab_bar
from src.services import secrets, settings_store
from src.services.file_parser import ParsedFile, human_size
from src.sections.ai_career.upload import upload_zone
from src.sections.ai_doc_assistant import pipeline
from src.sections.ai_doc_assistant.how_to import open_doc_assistant_how_to
from src.sections.ai_doc_assistant.state import (
    ACTION_EXTRACT,
    ACTION_QA,
    ACTION_REWRITE,
    ACTION_SUMMARY,
    ACTIONS,
    STATE,
    TAB_ANALYZE,
    TAB_OUTPUT,
    TAB_UPLOAD,
    UploadedDoc,
)
from src.sections.ai_doc_assistant.strings import s
from src.theme import Theme


_DOC_EXTENSIONS = ("pdf", "docx", "txt", "md", "html", "htm")
_PREVIEW_CHARS = 800


# ---------------------------------------------------------------------------
# Small visual helpers (kept local so we don't fight ai_career patterns)
# ---------------------------------------------------------------------------


def _step_card(
    theme: Theme, *, label: str, title: str, desc: str, body: ft.Control
) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    label,
                    color=theme.primary,
                    size=11,
                    weight=ft.FontWeight.W_700,
                    style=ft.TextStyle(letter_spacing=1.4),
                ),
                ft.Text(title, color=theme.text, size=15, weight=ft.FontWeight.W_700),
                ft.Text(desc, color=theme.text_muted, size=12),
                ft.Container(height=8),
                body,
            ],
            spacing=4,
            tight=True,
        ),
        padding=18,
        bgcolor=theme.surface,
        border_radius=14,
        border=ft.border.all(1, theme.border),
    )


def _flat_button(
    theme: Theme,
    label: str,
    *,
    icon: Optional[str] = None,
    primary: bool = False,
    enabled: bool = True,
    on_click: Optional[Callable[[ft.ControlEvent], None]] = None,
) -> ft.Container:
    color = (
        ft.Colors.WHITE
        if (primary and enabled)
        else (theme.text if enabled else theme.text_subtle)
    )
    bg = theme.primary if (primary and enabled) else theme.surface_2
    border = None if (primary and enabled) else ft.border.all(1, theme.border)
    children: list[ft.Control] = []
    if icon:
        children.append(ft.Icon(icon, color=color, size=14))
    children.append(
        ft.Text(label, color=color, size=12, weight=ft.FontWeight.W_600)
    )
    return ft.Container(
        content=ft.Row(
            controls=children,
            spacing=6,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        bgcolor=bg,
        border=border,
        border_radius=10,
        ink=enabled,
        on_click=(on_click if enabled else None),
        opacity=1.0 if enabled else 0.55,
    )


def _file_chip(
    theme: Theme, txt: dict, doc: UploadedDoc, on_clear: Callable[[], None]
) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.DESCRIPTION_OUTLINED, color=theme.primary, size=18
                    ),
                    width=32,
                    height=32,
                    bgcolor=ft.Colors.with_opacity(0.14, theme.primary),
                    border_radius=8,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    controls=[
                        ft.Text(
                            doc.name,
                            color=theme.text,
                            size=13,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Text(
                            f"{doc.ext.upper()} - {human_size(doc.size_bytes)}",
                            color=theme.text_muted,
                            size=11,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                    tight=True,
                ),
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_color=theme.text_muted,
                    icon_size=16,
                    tooltip=txt["clear_btn"],
                    on_click=lambda e: on_clear(),
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        bgcolor=theme.surface_2,
        border_radius=12,
        border=ft.border.all(1, theme.border),
    )


def _preview_block(theme: Theme, txt: dict, doc: UploadedDoc) -> ft.Control:
    preview = (doc.text or "")[:_PREVIEW_CHARS]
    if len(doc.text or "") > _PREVIEW_CHARS:
        preview += "\n\n..."
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    txt["preview_label"],
                    color=theme.text_subtle,
                    size=11,
                    weight=ft.FontWeight.W_600,
                    style=ft.TextStyle(letter_spacing=0.6),
                ),
                ft.Container(
                    content=ft.Text(
                        preview or "(empty)",
                        color=theme.text_muted,
                        size=12,
                        selectable=True,
                    ),
                    bgcolor=theme.surface_2,
                    border=ft.border.all(1, theme.border),
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                ),
            ],
            spacing=8,
            tight=True,
        ),
        padding=ft.padding.only(top=8),
    )


# ---------------------------------------------------------------------------
# Tab content
# ---------------------------------------------------------------------------


def _build_upload_tab(
    theme: Theme,
    txt: dict,
    on_state_change: Callable[[], None],
) -> ft.Control:
    holder = ft.Container()

    def _render() -> None:
        if STATE.document:
            children: list[ft.Control] = [
                _file_chip(
                    theme, txt, STATE.document, on_clear=_clear_doc
                ),
                _preview_block(theme, txt, STATE.document),
            ]
        else:
            children = [
                ft.Container(
                    content=ft.Text(
                        txt["no_file"], color=theme.text_muted, size=12
                    ),
                    padding=ft.padding.symmetric(horizontal=4, vertical=8),
                )
            ]
        holder.content = ft.Column(controls=children, spacing=8, tight=True)
        try:
            holder.update()
        except Exception:
            pass

    def _clear_doc() -> None:
        STATE.document = None
        STATE.reset_result()
        _render()
        on_state_change()

    def _on_doc(parsed: ParsedFile) -> None:
        STATE.document = UploadedDoc(
            path=parsed.path,
            name=parsed.name,
            ext=parsed.ext,
            size_bytes=parsed.size_bytes,
            text=parsed.text,
        )
        STATE.reset_result()
        _render()
        on_state_change()

    _render()

    body = ft.Column(
        controls=[
            upload_zone(
                theme,
                title=txt["drop_title"],
                hint=txt["drop_hint"],
                extensions=_DOC_EXTENSIONS,
                unsupported_message=txt["unsupported"],
                on_file_resolved=_on_doc,
            ),
            holder,
        ],
        spacing=8,
        tight=True,
    )

    return _step_card(
        theme,
        label=txt["step_1_label"],
        title=txt["step_1_title"],
        desc=txt["step_1_desc"],
        body=body,
    )


def _action_radio(
    theme: Theme,
    *,
    title: str,
    desc: str,
    selected: bool,
    on_click: Callable[[ft.ControlEvent], None],
) -> ft.Container:
    indicator = ft.Container(
        width=18,
        height=18,
        border_radius=9,
        border=ft.border.all(2, theme.primary if selected else theme.border),
        bgcolor=theme.primary if selected else "transparent",
        alignment=ft.Alignment.CENTER,
        content=(
            ft.Container(
                width=8, height=8, border_radius=4, bgcolor=ft.Colors.WHITE
            )
            if selected
            else None
        ),
    )
    return ft.Container(
        content=ft.Row(
            controls=[
                indicator,
                ft.Column(
                    controls=[
                        ft.Text(
                            title,
                            color=theme.text,
                            size=13,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Text(desc, color=theme.text_muted, size=11),
                    ],
                    spacing=2,
                    tight=True,
                    expand=True,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        padding=12,
        bgcolor=theme.surface_2,
        border=ft.border.all(
            1, theme.primary if selected else theme.border
        ),
        border_radius=12,
        ink=True,
        on_click=on_click,
    )


def _build_analyze_tab(
    theme: Theme,
    txt: dict,
    on_state_change: Callable[[], None],
) -> ft.Control:
    actions_holder = ft.Container()
    inputs_holder = ft.Container()

    def _render_actions() -> None:
        action_cards: list[ft.Control] = []
        labels = {
            ACTION_SUMMARY: (txt["action_summary"], txt["action_summary_desc"]),
            ACTION_QA: (txt["action_qa"], txt["action_qa_desc"]),
            ACTION_REWRITE: (txt["action_rewrite"], txt["action_rewrite_desc"]),
            ACTION_EXTRACT: (txt["action_extract"], txt["action_extract_desc"]),
        }
        for key in ACTIONS:
            title, desc = labels[key]
            action_cards.append(
                _action_radio(
                    theme,
                    title=title,
                    desc=desc,
                    selected=STATE.action == key,
                    on_click=lambda e, k=key: _set_action(k),
                )
            )
        actions_holder.content = ft.Column(
            controls=action_cards, spacing=8, tight=True
        )
        try:
            actions_holder.update()
        except Exception:
            pass

    def _render_inputs() -> None:
        if STATE.action == ACTION_QA:
            inputs_holder.content = ft.Column(
                controls=[
                    ft.Text(
                        txt["qa_question_label"],
                        color=theme.text,
                        size=12,
                        weight=ft.FontWeight.W_600,
                    ),
                    ft.TextField(
                        value=STATE.qa_question,
                        hint_text=txt["qa_question_hint"],
                        text_style=ft.TextStyle(color=theme.text, size=13),
                        hint_style=ft.TextStyle(color=theme.text_subtle, size=12),
                        bgcolor=theme.surface_2,
                        border=ft.InputBorder.NONE,
                        filled=True,
                        cursor_color=theme.primary,
                        content_padding=ft.padding.symmetric(
                            horizontal=12, vertical=10
                        ),
                        border_radius=10,
                        on_change=lambda e: _set_question(e.control.value or ""),
                    ),
                ],
                spacing=6,
                tight=True,
            )
        elif STATE.action == ACTION_REWRITE:
            inputs_holder.content = ft.Column(
                controls=[
                    ft.Text(
                        txt["rewrite_passage_label"],
                        color=theme.text,
                        size=12,
                        weight=ft.FontWeight.W_600,
                    ),
                    ft.TextField(
                        value=STATE.rewrite_passage,
                        hint_text=txt["rewrite_passage_hint"],
                        multiline=True,
                        min_lines=4,
                        max_lines=10,
                        text_style=ft.TextStyle(color=theme.text, size=12),
                        hint_style=ft.TextStyle(color=theme.text_subtle, size=12),
                        bgcolor=theme.surface_2,
                        border=ft.InputBorder.NONE,
                        filled=True,
                        cursor_color=theme.primary,
                        content_padding=ft.padding.symmetric(
                            horizontal=12, vertical=10
                        ),
                        border_radius=10,
                        on_change=lambda e: _set_passage(e.control.value or ""),
                    ),
                    ft.Container(height=6),
                    ft.Text(
                        txt["rewrite_tone_label"],
                        color=theme.text,
                        size=12,
                        weight=ft.FontWeight.W_600,
                    ),
                    ft.TextField(
                        value=STATE.rewrite_tone,
                        hint_text=txt["rewrite_tone_options"],
                        text_style=ft.TextStyle(color=theme.text, size=13),
                        hint_style=ft.TextStyle(color=theme.text_subtle, size=12),
                        bgcolor=theme.surface_2,
                        border=ft.InputBorder.NONE,
                        filled=True,
                        cursor_color=theme.primary,
                        content_padding=ft.padding.symmetric(
                            horizontal=12, vertical=10
                        ),
                        border_radius=10,
                        on_change=lambda e: _set_tone(e.control.value or ""),
                    ),
                ],
                spacing=6,
                tight=True,
            )
        else:
            inputs_holder.content = ft.Container()
        try:
            inputs_holder.update()
        except Exception:
            pass

    def _set_action(key: str) -> None:
        STATE.action = key
        _render_actions()
        _render_inputs()
        on_state_change()

    def _set_question(value: str) -> None:
        STATE.qa_question = value
        on_state_change()

    def _set_passage(value: str) -> None:
        STATE.rewrite_passage = value
        on_state_change()

    def _set_tone(value: str) -> None:
        STATE.rewrite_tone = value
        on_state_change()

    _render_actions()
    _render_inputs()

    body = ft.Column(
        controls=[
            actions_holder,
            ft.Container(height=4),
            inputs_holder,
        ],
        spacing=8,
        tight=True,
    )

    return _step_card(
        theme,
        label=txt["step_2_label"],
        title=txt["step_2_title"],
        desc=txt["step_2_desc"],
        body=body,
    )


def _result_section(
    theme: Theme, *, title: str, body: ft.Control
) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    title,
                    color=theme.primary,
                    size=11,
                    weight=ft.FontWeight.W_700,
                    style=ft.TextStyle(letter_spacing=1.2),
                ),
                ft.Container(height=4),
                body,
            ],
            spacing=2,
            tight=True,
        ),
        padding=14,
        bgcolor=theme.surface,
        border_radius=12,
        border=ft.border.all(1, theme.border),
    )


def _bullet_list(
    theme: Theme, items: list[str]
) -> ft.Control:
    if not items:
        return ft.Text("-", color=theme.text_muted, size=12)
    rows = [
        ft.Row(
            controls=[
                ft.Container(
                    width=6,
                    height=6,
                    border_radius=3,
                    bgcolor=theme.primary,
                    margin=ft.margin.only(top=6),
                ),
                ft.Text(
                    item,
                    color=theme.text,
                    size=12,
                    selectable=True,
                    expand=True,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
        for item in items
    ]
    return ft.Column(controls=rows, spacing=6, tight=True)


def _build_output_tab(
    theme: Theme,
    txt: dict,
    on_navigate_tab: Callable[[int], None],
) -> ft.Control:
    if STATE.last_error:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(
                        ft.Icons.ERROR_OUTLINE, color="#EF4444", size=24
                    ),
                    ft.Text(
                        STATE.last_error,
                        color="#EF4444",
                        size=13,
                        weight=ft.FontWeight.W_500,
                        selectable=True,
                    ),
                    ft.Container(height=6),
                    _flat_button(
                        theme,
                        txt["output_back_btn"],
                        icon=ft.Icons.ARROW_BACK,
                        on_click=lambda e: on_navigate_tab(TAB_ANALYZE),
                    ),
                ],
                spacing=8,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=24,
        )

    if not STATE.last_result:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        txt["output_empty"],
                        color=theme.text_muted,
                        size=13,
                    ),
                    ft.Container(height=6),
                    _flat_button(
                        theme,
                        txt["output_back_btn"],
                        icon=ft.Icons.ARROW_BACK,
                        on_click=lambda e: on_navigate_tab(TAB_ANALYZE),
                    ),
                ],
                spacing=8,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=24,
        )

    data = STATE.last_result
    action = STATE.last_action
    blocks: list[ft.Control] = []

    if action == ACTION_SUMMARY:
        blocks.append(
            _result_section(
                theme,
                title=txt["output_summary_title"],
                body=ft.Text(
                    data.get("tldr") or "-",
                    color=theme.text,
                    size=13,
                    selectable=True,
                ),
            )
        )
        blocks.append(
            _result_section(
                theme,
                title=txt["output_bullets_title"],
                body=_bullet_list(theme, list(data.get("key_points") or [])),
            )
        )
        blocks.append(
            _result_section(
                theme,
                title=txt["output_actions_title"],
                body=_bullet_list(theme, list(data.get("action_items") or [])),
            )
        )
    elif action == ACTION_QA:
        confidence = (data.get("confidence") or "").upper()
        confidence_pill = ft.Container(
            content=ft.Text(
                confidence or "-",
                color=ft.Colors.WHITE,
                size=10,
                weight=ft.FontWeight.W_700,
            ),
            padding=ft.padding.symmetric(horizontal=8, vertical=2),
            bgcolor=theme.primary,
            border_radius=8,
        )
        blocks.append(
            _result_section(
                theme,
                title=txt["output_answer_title"],
                body=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[confidence_pill],
                            spacing=0,
                            tight=True,
                        ),
                        ft.Text(
                            data.get("answer") or "-",
                            color=theme.text,
                            size=13,
                            selectable=True,
                        ),
                    ],
                    spacing=6,
                    tight=True,
                ),
            )
        )
        blocks.append(
            _result_section(
                theme,
                title=txt["output_evidence_title"],
                body=_bullet_list(theme, list(data.get("evidence") or [])),
            )
        )
    elif action == ACTION_REWRITE:
        blocks.append(
            _result_section(
                theme,
                title=txt["output_rewrite_title"],
                body=ft.Text(
                    data.get("rewritten") or "-",
                    color=theme.text,
                    size=13,
                    selectable=True,
                ),
            )
        )
        blocks.append(
            _result_section(
                theme,
                title=txt["output_actions_title"],
                body=_bullet_list(theme, list(data.get("changes") or [])),
            )
        )
    elif action == ACTION_EXTRACT:
        facts = list(data.get("facts") or [])
        if not facts:
            blocks.append(
                _result_section(
                    theme,
                    title=txt["output_extract_title"],
                    body=ft.Text("-", color=theme.text_muted, size=12),
                )
            )
        else:
            rows: list[ft.Control] = []
            for fact in facts:
                label = (fact.get("label") or "").strip() or "-"
                value = (fact.get("value") or "").strip() or "-"
                evidence = (fact.get("evidence") or "").strip()
                rows.append(
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(
                                    label,
                                    color=theme.text_subtle,
                                    size=10,
                                    weight=ft.FontWeight.W_700,
                                    style=ft.TextStyle(letter_spacing=0.6),
                                ),
                                ft.Text(
                                    value,
                                    color=theme.text,
                                    size=13,
                                    weight=ft.FontWeight.W_600,
                                    selectable=True,
                                ),
                                ft.Text(
                                    evidence,
                                    color=theme.text_muted,
                                    size=11,
                                    italic=True,
                                    selectable=True,
                                )
                                if evidence
                                else ft.Container(),
                            ],
                            spacing=2,
                            tight=True,
                        ),
                        padding=10,
                        bgcolor=theme.surface_2,
                        border=ft.border.all(1, theme.border),
                        border_radius=10,
                    )
                )
            blocks.append(
                _result_section(
                    theme,
                    title=txt["output_extract_title"],
                    body=ft.Column(controls=rows, spacing=6, tight=True),
                )
            )

    blocks.append(ft.Container(height=4))
    blocks.append(
        _flat_button(
            theme,
            txt["output_back_btn"],
            icon=ft.Icons.ARROW_BACK,
            on_click=lambda e: on_navigate_tab(TAB_ANALYZE),
        )
    )

    return ft.ListView(
        controls=blocks,
        spacing=10,
        padding=ft.padding.symmetric(horizontal=24, vertical=18),
        expand=True,
    )


# ---------------------------------------------------------------------------
# Run footer + tab body wiring
# ---------------------------------------------------------------------------


def _build_footer(
    theme: Theme,
    lang: str,
    txt: dict,
    on_state_change: Callable[[], None],
    on_navigate_tab: Callable[[int], None],
) -> ft.Control:
    run_status = ft.Text("", color=theme.text_muted, size=11)
    run_button_holder = ft.Container()
    run_state: dict[str, str] = {"stage": ""}

    def _set_status(msg: str, *, error: bool = False) -> None:
        run_status.value = msg
        run_status.color = "#EF4444" if error else theme.text_muted
        try:
            run_status.update()
        except Exception:
            pass

    def _render_run_button() -> None:
        running = bool(run_state["stage"])
        enabled = STATE.can_run() and not running
        label = txt["footer_run_running"] if running else txt["footer_run_btn"]
        run_button_holder.content = _flat_button(
            theme,
            label,
            icon=ft.Icons.PLAY_ARROW_ROUNDED,
            primary=True,
            enabled=enabled,
            on_click=lambda e: _on_run(),
        )
        try:
            run_button_holder.update()
        except Exception:
            pass

    def _on_demo() -> None:
        STATE.demo_mode = True
        pipeline.load_demo()
        on_state_change()
        on_navigate_tab(TAB_OUTPUT)

    def _on_run() -> None:
        if not STATE.can_run():
            _set_status(txt["run_disabled_hint"], error=True)
            return
        if not STATE.demo_mode:
            provider = settings_store.get_provider()
            key_name = (
                secrets.ANTHROPIC_API_KEY
                if provider == settings_store.PROVIDER_ANTHROPIC
                else secrets.OPENAI_API_KEY
            )
            if not secrets.has_secret(key_name):
                _set_status(
                    txt["no_key_template"].format(provider=provider), error=True
                )
                return

        _set_status("")
        run_state["stage"] = "running"
        _render_run_button()

        def _worker() -> None:
            try:
                result = pipeline.run_action(output_lang=lang)
            except Exception as exc:
                STATE.last_error = str(exc)
                run_state["stage"] = ""
                _set_status(str(exc), error=True)
                _render_run_button()
                return
            run_state["stage"] = ""
            if not result.ok:
                _set_status(result.error or "Run failed.", error=True)
                _render_run_button()
                return
            _render_run_button()
            on_navigate_tab(TAB_OUTPUT)

        threading.Thread(target=_worker, daemon=True).start()

    demo_btn = _flat_button(
        theme,
        txt["footer_demo_btn"],
        icon=ft.Icons.AUTO_AWESOME,
        on_click=lambda e: _on_demo(),
    )

    _render_run_button()

    return ft.Container(
        content=ft.Row(
            controls=[
                demo_btn,
                ft.Container(expand=True),
                run_status,
                run_button_holder,
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=24, vertical=12),
        border=ft.border.only(top=ft.BorderSide(1, theme.border)),
        bgcolor=theme.bg,
    )


def _build_tab_body(
    theme: Theme,
    txt: dict,
    on_state_change: Callable[[], None],
    on_navigate_tab: Callable[[int], None],
) -> ft.Control:
    if STATE.active_tab == TAB_ANALYZE:
        body = _build_analyze_tab(theme, txt, on_state_change)
    elif STATE.active_tab == TAB_OUTPUT:
        return _build_output_tab(theme, txt, on_navigate_tab)
    else:
        body = _build_upload_tab(theme, txt, on_state_change)

    return ft.ListView(
        controls=[body],
        spacing=14,
        padding=ft.padding.symmetric(horizontal=24, vertical=18),
        expand=True,
    )


# ---------------------------------------------------------------------------
# Public build_view
# ---------------------------------------------------------------------------


def build_view(theme: Theme, lang: str) -> ft.Column:
    txt = s(lang)

    content_holder = ft.Container(expand=True)
    tab_bar_holder = ft.Container()
    footer_holder = ft.Container()

    def _refresh_tab_body() -> None:
        content_holder.content = _build_tab_body(
            theme, txt, _on_state_change, _on_navigate_tab
        )
        try:
            content_holder.update()
        except Exception:
            pass

    def _refresh_tabs() -> None:
        tab_bar_holder.content = tab_bar(
            theme,
            tabs=[txt["tab_upload"], txt["tab_analyze"], txt["tab_output"]],
            active_index=STATE.active_tab,
            on_change=_on_tab_change,
        )
        try:
            tab_bar_holder.update()
        except Exception:
            pass

    def _refresh_footer() -> None:
        footer_holder.content = _build_footer(
            theme, lang, txt, _on_state_change, _on_navigate_tab
        )
        try:
            footer_holder.update()
        except Exception:
            pass

    def _on_state_change() -> None:
        _refresh_footer()

    def _on_tab_change(index: int) -> None:
        if index == STATE.active_tab:
            return
        STATE.active_tab = index
        _refresh_tabs()
        _refresh_tab_body()

    def _on_navigate_tab(index: int) -> None:
        STATE.active_tab = index
        _refresh_tabs()
        _refresh_tab_body()

    tab_bar_holder.content = tab_bar(
        theme,
        tabs=[txt["tab_upload"], txt["tab_analyze"], txt["tab_output"]],
        active_index=STATE.active_tab,
        on_change=_on_tab_change,
    )
    content_holder.content = _build_tab_body(
        theme, txt, _on_state_change, _on_navigate_tab
    )
    footer_holder.content = _build_footer(
        theme, lang, txt, _on_state_change, _on_navigate_tab
    )

    def _on_help(e: ft.ControlEvent) -> None:
        if e.page is None:
            return
        open_doc_assistant_how_to(e.page, theme, lang)

    demo_pill: ft.Control | None = None
    if STATE.demo_mode:
        demo_pill = ft.Container(
            content=ft.Text(
                txt["demo_pill"],
                color=ft.Colors.WHITE,
                size=11,
                weight=ft.FontWeight.W_700,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
            bgcolor="#F59E0B",
            border_radius=10,
        )

    header_control = header(
        theme,
        lang,
        icon=ft.Icons.AUTO_STORIES_OUTLINED,
        title=txt["title"],
        subtitle=txt["subtitle"],
        on_help_click=_on_help,
        trailing=demo_pill,
    )

    return ft.Column(
        controls=[
            header_control,
            tab_bar_holder,
            content_holder,
            footer_holder,
        ],
        spacing=0,
        expand=True,
        tight=True,
    )
