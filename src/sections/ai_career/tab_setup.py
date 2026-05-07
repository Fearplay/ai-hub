"""Setup tab - the user picks the role, uploads the resume, runs analysis.

Three numbered steps + a footer with the run button:

1. **Job posting** - URL + Fetch button OR paste textarea.
2. **Resume & profile** - resume drop zone (mandatory) + LinkedIn drop
   zone (optional).
3. **GitHub profile** - URL + Skip toggle + a small note about the
   keyring-stored token.

The Run button kicks off :func:`pipeline.run_full_analysis` on a daemon
thread - the call blocks 5-30 seconds against the LLM and we don't want
the UI to freeze. Status feedback flows through the right context panel
(``activity``) and inline status text.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

import flet as ft

from src.services import secrets, settings_store
from src.services.file_parser import ParsedFile, human_size
from src.sections.ai_career import pipeline
from src.sections.ai_career.followup_dialog import open_followup_dialog
from src.sections.ai_career.refs import REFS, safe
from src.sections.ai_career.state import (
    STATE,
    TAB_MATCH,
    UploadedFile,
)
from src.sections.ai_career.strings import s
from src.sections.ai_career.upload import upload_zone
from src.theme import Theme


_RESUME_EXTENSIONS = ("pdf", "docx", "txt", "md", "html", "htm")
_LINKEDIN_EXTENSIONS = ("pdf", "txt", "html", "htm")


def _step_card(
    theme: Theme,
    *,
    label: str,
    title: str,
    desc: str,
    body: ft.Control,
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


def _file_chip(theme: Theme, txt: dict, parsed: ParsedFile, on_clear: Callable[[], None]) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, color=theme.primary, size=18),
                    width=32,
                    height=32,
                    bgcolor=ft.Colors.with_opacity(0.14, theme.primary),
                    border_radius=8,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    controls=[
                        ft.Text(parsed.name, color=theme.text, size=13, weight=ft.FontWeight.W_600),
                        ft.Text(
                            f"{parsed.ext.upper()} · {human_size(parsed.size_bytes)}",
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
                    tooltip=txt["resume_clear_btn"],
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
    bg = (
        theme.primary
        if (primary and enabled)
        else (theme.surface_2 if enabled else theme.surface_2)
    )
    border = (
        None
        if (primary and enabled)
        else ft.border.all(1, theme.border)
    )
    children: list[ft.Control] = []
    if icon:
        children.append(ft.Icon(icon, color=color, size=14))
    children.append(ft.Text(label, color=color, size=12, weight=ft.FontWeight.W_600))
    return ft.Container(
        content=ft.Row(controls=children, spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        bgcolor=bg,
        border=border,
        border_radius=10,
        ink=enabled,
        on_click=(on_click if enabled else None),
        opacity=1.0 if enabled else 0.55,
    )


def _step_1(theme: Theme, txt: dict, on_state_change: Callable[[], None]) -> ft.Control:
    url_field = ft.TextField(
        value=STATE.job_url,
        hint_text=txt["job_url_hint"],
        hint_style=ft.TextStyle(color=theme.text_subtle, size=12),
        text_style=ft.TextStyle(color=theme.text, size=13),
        bgcolor=theme.surface_2,
        border=ft.InputBorder.NONE,
        filled=True,
        cursor_color=theme.primary,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border_radius=10,
        expand=True,
        on_change=lambda e: _set_url(e.control.value or ""),
    )

    text_area = ft.TextField(
        value=STATE.job_text if STATE.job_text_source != "demo" else STATE.job_text,
        hint_text=txt["job_text_hint"],
        multiline=True,
        min_lines=6,
        max_lines=12,
        text_style=ft.TextStyle(color=theme.text, size=12),
        hint_style=ft.TextStyle(color=theme.text_subtle, size=12),
        bgcolor=theme.surface_2,
        border=ft.InputBorder.NONE,
        filled=True,
        cursor_color=theme.primary,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border_radius=10,
        on_change=lambda e: _set_text(e.control.value or ""),
    )

    fetch_status = ft.Text("", color=theme.text_muted, size=12)
    fetch_btn = _flat_button(
        theme,
        txt["job_url_btn"],
        icon=ft.Icons.DOWNLOAD_OUTLINED,
        primary=True,
        on_click=lambda e: _start_fetch(e.page),
    )

    def _set_url(value: str) -> None:
        STATE.job_url = value
        on_state_change()

    def _set_text(value: str) -> None:
        STATE.job_text = value
        STATE.job_text_source = "paste" if value else ""
        on_state_change()

    def _start_fetch(page: Optional[ft.Page]) -> None:
        url = (url_field.value or "").strip()
        if not url:
            return
        fetch_status.value = txt["job_url_running"]
        fetch_status.color = theme.text_muted
        try:
            fetch_status.update()
        except Exception:
            pass

        def _worker() -> None:
            text, error = pipeline.fetch_job_text(url)
            if text:
                STATE.job_text = text
                STATE.job_url = url
                STATE.job_text_source = "scrape"
                text_area.value = text
                fetch_status.value = ""
            else:
                fetch_status.value = error or txt["job_url_failed"]
                fetch_status.color = "#EF4444"
            try:
                text_area.update()
            except Exception:
                pass
            try:
                fetch_status.update()
            except Exception:
                pass
            on_state_change()

        threading.Thread(target=_worker, daemon=True).start()

    body = ft.Column(
        controls=[
            ft.Row(
                controls=[url_field, fetch_btn],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            fetch_status,
            text_area,
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


def _step_2(theme: Theme, txt: dict, on_state_change: Callable[[], None]) -> ft.Control:
    resume_holder = ft.Container()
    linkedin_holder = ft.Container()

    def _render_resume() -> None:
        if STATE.resume:
            resume_holder.content = _file_chip(
                theme, txt, _to_parsed(STATE.resume), on_clear=_clear_resume
            )
        else:
            resume_holder.content = ft.Container(
                content=ft.Text(txt["resume_no_file"], color=theme.text_muted, size=12),
                padding=ft.padding.symmetric(horizontal=4, vertical=8),
            )
        try:
            resume_holder.update()
        except Exception:
            pass

    def _render_linkedin() -> None:
        if STATE.linkedin:
            linkedin_holder.content = _file_chip(
                theme, txt, _to_parsed(STATE.linkedin), on_clear=_clear_linkedin
            )
        else:
            linkedin_holder.content = ft.Container(
                content=ft.Text(txt["linkedin_no_file"], color=theme.text_muted, size=12),
                padding=ft.padding.symmetric(horizontal=4, vertical=8),
            )
        try:
            linkedin_holder.update()
        except Exception:
            pass

    def _clear_resume() -> None:
        STATE.resume = None
        _render_resume()
        on_state_change()

    def _clear_linkedin() -> None:
        STATE.linkedin = None
        _render_linkedin()
        on_state_change()

    def _on_resume(parsed: ParsedFile) -> None:
        STATE.resume = UploadedFile(
            path=parsed.path,
            name=parsed.name,
            ext=parsed.ext,
            size_bytes=parsed.size_bytes,
            text=parsed.text,
        )
        _render_resume()
        on_state_change()

    def _on_linkedin(parsed: ParsedFile) -> None:
        STATE.linkedin = UploadedFile(
            path=parsed.path,
            name=parsed.name,
            ext=parsed.ext,
            size_bytes=parsed.size_bytes,
            text=parsed.text,
        )
        _render_linkedin()
        on_state_change()

    _render_resume()
    _render_linkedin()

    body = ft.Column(
        controls=[
            ft.Text(txt["resume_label"], color=theme.text, size=13, weight=ft.FontWeight.W_600),
            upload_zone(
                theme,
                title=txt["resume_drop_title"],
                hint=txt["resume_drop_hint"],
                extensions=_RESUME_EXTENSIONS,
                unsupported_message=txt["resume_unsupported"],
                on_file_resolved=_on_resume,
            ),
            resume_holder,
            ft.Container(height=8),
            ft.Text(txt["linkedin_label"], color=theme.text, size=13, weight=ft.FontWeight.W_600),
            upload_zone(
                theme,
                title=txt["linkedin_drop_title"],
                hint=txt["linkedin_drop_hint"],
                extensions=_LINKEDIN_EXTENSIONS,
                unsupported_message=txt["resume_unsupported"],
                on_file_resolved=_on_linkedin,
                height=104,
            ),
            linkedin_holder,
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


def _step_3(theme: Theme, txt: dict, on_state_change: Callable[[], None]) -> ft.Control:
    url_field = ft.TextField(
        value=STATE.github_url,
        hint_text=txt["github_url_hint"],
        hint_style=ft.TextStyle(color=theme.text_subtle, size=12),
        text_style=ft.TextStyle(color=theme.text, size=13),
        bgcolor=theme.surface_2,
        border=ft.InputBorder.NONE,
        filled=True,
        cursor_color=theme.primary,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border_radius=10,
        on_change=lambda e: _set_url(e.control.value or ""),
        disabled=STATE.github_skip,
    )
    skip_checkbox = ft.Checkbox(
        value=STATE.github_skip,
        label=txt["github_skip_label"],
        active_color=theme.primary,
        label_style=ft.TextStyle(color=theme.text, size=12),
        on_change=lambda e: _set_skip(bool(e.control.value)),
    )
    status = ft.Text("", color=theme.text_muted, size=11)

    has_token = secrets.has_secret(secrets.GITHUB_TOKEN)
    note_text = txt["github_token_note_authenticated" if has_token else "github_token_note_anonymous"]
    note = ft.Text(note_text, color=theme.text_subtle, size=11, italic=True)

    def _set_url(value: str) -> None:
        STATE.github_url = value
        on_state_change()

    def _set_skip(value: bool) -> None:
        STATE.github_skip = value
        if value:
            STATE.github_profile = None
            status.value = ""
            try:
                status.update()
            except Exception:
                pass
        url_field.disabled = value
        try:
            url_field.update()
        except Exception:
            pass
        on_state_change()

    body = ft.Column(
        controls=[
            url_field,
            skip_checkbox,
            note,
            status,
        ],
        spacing=8,
        tight=True,
    )
    return _step_card(
        theme,
        label=txt["step_3_label"],
        title=txt["step_3_title"],
        desc=txt["step_3_desc"],
        body=body,
    )


def _to_parsed(uploaded: UploadedFile) -> ParsedFile:
    return ParsedFile(
        path=uploaded.path,
        name=uploaded.name,
        ext=uploaded.ext,
        size_bytes=uploaded.size_bytes,
        text=uploaded.text,
        error=None,
    )


def _footer_bar(
    theme: Theme,
    lang: str,
    txt: dict,
    on_state_change: Callable[[], None],
) -> tuple[ft.Container, Callable[[ft.Page | None], None]]:
    demo_btn = _flat_button(
        theme,
        txt["footer_demo_btn"],
        icon=ft.Icons.AUTO_AWESOME,
        on_click=lambda e: _on_demo(),
    )

    followups_switch = ft.Switch(
        value=settings_store.get_ask_followups(),
        active_color=theme.primary,
        scale=0.85,
        on_change=lambda e: settings_store.set_ask_followups(bool(e.control.value)),
    )

    run_status = ft.Text("", color=theme.text_muted, size=11)

    run_button_holder = ft.Container()
    # ``stage`` is one of "" | "running" | "followups" | "match" | "demo".
    run_state: dict[str, str] = {"stage": ""}

    def _set_status(message: str, *, error: bool = False) -> None:
        run_status.value = message
        run_status.color = "#EF4444" if error else theme.text_muted
        try:
            run_status.update()
        except Exception:
            pass

    def _label_for(stage: str) -> str:
        if stage == "demo":
            return txt["footer_run_demo_running"]
        if stage == "followups":
            return txt["footer_run_followups_running"]
        if stage == "match":
            return txt["footer_run_match_running"]
        if stage == "running":
            return txt["footer_run_running"]
        return txt["footer_run_btn"]

    def _render_run_button() -> None:
        stage = run_state["stage"]
        running = bool(stage)
        enabled = STATE.can_run() and not running
        run_button_holder.content = _flat_button(
            theme,
            _label_for(stage),
            icon=ft.Icons.PLAY_ARROW_ROUNDED,
            primary=True,
            enabled=enabled,
            on_click=lambda e: _on_run(e.page),
        )
        try:
            run_button_holder.update()
        except Exception:
            pass

    def _set_stage(stage: str) -> None:
        run_state["stage"] = stage
        _render_run_button()

    def _on_demo() -> None:
        STATE.demo_mode = True
        pipeline.load_demo(output_lang=lang)
        STATE.active_tab = TAB_MATCH
        on_state_change()
        safe(REFS.rerender_main)

    def _go_to_match() -> None:
        STATE.active_tab = TAB_MATCH
        safe(REFS.rerender_main)

    def _phase2_match() -> None:
        """Step 3: match analysis (same thread or fresh thread, doesn't matter)."""
        _set_stage("match")
        result = pipeline.analyze_match(output_lang=lang)
        if not result.ok:
            _set_status(result.error, error=True)
            _set_stage("")
            return
        STATE.activity = "ready"
        safe(REFS.rerender_context)
        _set_stage("")
        _go_to_match()

    def _open_followup_dialog(page: Optional[ft.Page]) -> None:
        if page is None:
            # Without a page we can't show the dialog; just continue silently.
            _phase2_match()
            return

        def _on_submit(answers: list[dict]) -> None:
            STATE.followup_qa = answers
            STATE.activity = "analyzing"
            safe(REFS.rerender_context)
            threading.Thread(target=_phase2_match, daemon=True).start()

        def _on_cancel() -> None:
            STATE.followup_qa = []
            STATE.activity = "ready"
            safe(REFS.rerender_context)
            _set_stage("")

        open_followup_dialog(
            page,
            theme,
            title=txt["followup_title"],
            intro=txt["followup_intro"],
            cancel_label=txt["followup_cancel"],
            continue_label=txt["followup_continue"],
            answer_hint=txt["followup_answer_hint"],
            skip_all_label=txt["followup_skip_all"],
            questions=STATE.followup_questions,
            on_submit=_on_submit,
            on_cancel=_on_cancel,
        )

    def _on_run(page: Optional[ft.Page]) -> None:
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
                    txt["error_no_key_template"].format(provider=provider), error=True
                )
                return

        STATE.followup_questions = []
        STATE.followup_qa = []
        _set_status("")
        _set_stage("demo" if STATE.demo_mode else "running")

        def _phase1() -> None:
            try:
                if (
                    not STATE.demo_mode
                    and STATE.github_url
                    and not STATE.github_skip
                    and STATE.github_profile is None
                ):
                    STATE.github_profile = pipeline.fetch_github_profile(
                        STATE.github_url
                    )

                if STATE.demo_mode:
                    pipeline.load_demo(output_lang=lang)
                    _set_stage("")
                    _go_to_match()
                    return

                res = pipeline.extract_candidate(output_lang=lang)
                if not res.ok:
                    _set_status(res.error, error=True)
                    _set_stage("")
                    return

                res = pipeline.extract_job_spec(output_lang=lang)
                if not res.ok:
                    _set_status(res.error, error=True)
                    _set_stage("")
                    return

                if settings_store.get_ask_followups():
                    _set_stage("followups")
                    STATE.activity = "followups"
                    safe(REFS.rerender_context)
                    res = pipeline.generate_followup_questions(output_lang=lang)
                    if not res.ok:
                        _set_status(res.error, error=True)
                        _set_stage("")
                        return
                    if STATE.followup_questions:
                        STATE.activity = "waiting_user"
                        safe(REFS.rerender_context)
                        _open_followup_dialog(page)
                        return

                _phase2_match()
            except Exception as exc:
                _set_status(str(exc), error=True)
                _set_stage("")

        threading.Thread(target=_phase1, daemon=True).start()

    _render_run_button()

    # Three-row footer to stay readable on narrow window widths (the
    # center column is only ~400-500 px wide once you subtract the
    # 280 px sidebar and 336 px right context panel from a 1080 px
    # window):
    #
    #   Row 1 - Demo button on the left, Run analysis button on the right
    #   Row 2 - status / error text, can wrap freely without ever pushing
    #           the Run button off-screen (which is what happened when
    #           everything sat on one row at this width)
    #   Row 3 - "Ask follow-up questions" toggle + description
    followups_label_block = ft.Column(
        controls=[
            ft.Text(
                txt["footer_followup_label"],
                color=theme.text,
                size=11,
                weight=ft.FontWeight.W_600,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
            ft.Text(
                txt["footer_followup_desc"],
                color=theme.text_muted,
                size=10,
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
        ],
        spacing=2,
        tight=True,
        expand=True,
    )

    button_row = ft.Row(
        controls=[
            demo_btn,
            ft.Container(expand=True),
            run_button_holder,
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    status_row = ft.Row(
        controls=[run_status],
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    followups_row = ft.Row(
        controls=[followups_switch, followups_label_block],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    bar = ft.Container(
        content=ft.Column(
            controls=[button_row, status_row, followups_row],
            spacing=8,
            tight=True,
        ),
        padding=ft.padding.symmetric(horizontal=24, vertical=12),
        border=ft.border.only(top=ft.BorderSide(1, theme.border)),
        bgcolor=theme.bg,
    )
    return bar, lambda page: _render_run_button()


def build_setup_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Callable[[], None],
) -> ft.Column:
    txt = s(lang)

    refresh_footer_holder: dict = {"fn": None}

    def _on_state_change() -> None:
        # Two responsibilities here:
        #  1. Re-evaluate ``STATE.can_run()`` so the Run analysis button
        #     enables itself the moment the user fills in the resume +
        #     job text. Calling ``footer_holder.update()`` alone does
        #     NOT rebuild the run button - we need the closure handed
        #     back from ``_footer_bar`` for that.
        #  2. Force the page to flush so updates triggered from the
        #     fetch worker (background thread) actually propagate to
        #     the frontend; ``control.update()`` from a non-UI thread
        #     can otherwise be silently dropped.
        fn = refresh_footer_holder["fn"]
        if fn is not None:
            try:
                fn(None)
            except Exception:
                pass
        try:
            footer_holder.update()
        except Exception:
            pass
        try:
            page = footer_holder.page
            if page is not None:
                page.update()
        except Exception:
            pass

    body = ft.ListView(
        controls=[
            _step_1(theme, txt, _on_state_change),
            _step_2(theme, txt, _on_state_change),
            _step_3(theme, txt, _on_state_change),
        ],
        spacing=14,
        padding=ft.padding.symmetric(horizontal=24, vertical=18),
        expand=True,
    )
    footer, _refresh_footer = _footer_bar(theme, lang, txt, _on_state_change)
    refresh_footer_holder["fn"] = _refresh_footer
    footer_holder = ft.Container(content=footer)

    return ft.Column(
        controls=[body, footer_holder],
        spacing=0,
        expand=True,
        tight=True,
    )
