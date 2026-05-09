"""Setup tab - targeting + uploads + output language for AI LinkedIn.

Three numbered steps drive the inputs the LinkedIn pipeline needs:

1. **Targeting** - one or more target roles, audience preset, tone preset,
   plus a toggle for the optional Services section.
2. **Inputs** - resume drop zone (mandatory), optional LinkedIn export
   drop zone, optional GitHub username/URL, optional free-form notes.
3. **Output** - output language (EN / CS, follows UI by default) plus the
   "Ask clarifying questions before generating" toggle.

A footer bar carries the demo button + the "Continue to sections"
button, mirroring the AI Career setup ergonomics. Worker threads use
``REFS.dispatch`` to bounce updates back onto the UI loop.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

import flet as ft

from src.services import logger as logger_service
from src.services import secrets, settings_store
from src.services.file_parser import ParsedFile, human_size
from src.sections.ai_linkedin import pipeline
from src.sections.ai_linkedin.data import (
    audience_options,
    tone_options,
)
from src.sections.ai_linkedin.refs import REFS, safe
from src.sections.ai_linkedin.state import (
    STATE,
    TAB_SECTIONS,
    UploadedFile,
)
from src.sections.ai_linkedin.strings import s
from src.sections.ai_linkedin.upload import upload_zone
from src.theme import Theme


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.tab_setup", "request_full_refresh_import", exc,
        )
        return
    request_section_refresh()


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


def _file_chip(
    theme: Theme, *, parsed: ParsedFile, on_clear: Callable[[], None],
    clear_tooltip: str,
) -> ft.Container:
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
                    tooltip=clear_tooltip,
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
    bg = theme.primary if (primary and enabled) else theme.surface_2
    border = None if (primary and enabled) else ft.border.all(1, theme.border)
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


def _to_parsed(uploaded: UploadedFile) -> ParsedFile:
    return ParsedFile(
        path=uploaded.path,
        name=uploaded.name,
        ext=uploaded.ext,
        size_bytes=uploaded.size_bytes,
        text=uploaded.text,
        error=None,
    )


def _option_chip(
    theme: Theme,
    *,
    label: str,
    active: bool,
    on_click: Callable[[ft.ControlEvent], None],
) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            label,
            color=ft.Colors.WHITE if active else theme.text,
            size=12,
            weight=ft.FontWeight.W_700 if active else ft.FontWeight.W_500,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=7),
        bgcolor=theme.primary if active else theme.surface_2,
        border_radius=999,
        border=ft.border.all(1, theme.primary if active else theme.border),
        ink=True,
        on_click=on_click,
    )


def _step_targeting(
    theme: Theme, lang: str, txt: dict, on_state_change: Callable[[], None]
) -> ft.Control:
    roles_field = ft.TextField(
        value="\n".join(STATE.target_roles),
        hint_text=txt["setup_target_roles_hint"],
        multiline=True,
        min_lines=2,
        max_lines=4,
        text_style=ft.TextStyle(color=theme.text, size=13),
        hint_style=ft.TextStyle(color=theme.text_subtle, size=12),
        bgcolor=theme.surface_2,
        border=ft.InputBorder.NONE,
        filled=True,
        cursor_color=theme.primary,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border_radius=10,
        on_change=lambda e: _set_roles(e.control.value or ""),
    )

    audience_holder = ft.Container()
    tone_holder = ft.Container()

    def _set_roles(value: str) -> None:
        STATE.target_roles = [
            line.strip() for line in (value or "").splitlines() if line.strip()
        ]
        on_state_change()

    def _set_audience(key: str) -> None:
        STATE.audience = key
        _render_audience()
        on_state_change()

    def _set_tone(key: str) -> None:
        STATE.tone = key
        _render_tone()
        on_state_change()

    def _render_audience() -> None:
        chips: list[ft.Control] = [
            _option_chip(
                theme,
                label=opt["label"],
                active=STATE.audience == opt["key"],
                on_click=lambda _e, k=opt["key"]: _set_audience(k),
            )
            for opt in audience_options(lang)
        ]
        audience_holder.content = ft.Row(
            controls=chips, spacing=8, run_spacing=8, wrap=True,
        )
        if not logger_service.try_update(audience_holder):
            logger_service.log_event(
                "DEBUG", "ai_linkedin.tab_setup", "audience_holder_update_skipped",
            )

    def _render_tone() -> None:
        chips: list[ft.Control] = [
            _option_chip(
                theme,
                label=opt["label"],
                active=STATE.tone == opt["key"],
                on_click=lambda _e, k=opt["key"]: _set_tone(k),
            )
            for opt in tone_options(lang)
        ]
        tone_holder.content = ft.Row(
            controls=chips, spacing=8, run_spacing=8, wrap=True,
        )
        if not logger_service.try_update(tone_holder):
            logger_service.log_event(
                "DEBUG", "ai_linkedin.tab_setup", "tone_holder_update_skipped",
            )

    _render_audience()
    _render_tone()

    services_switch = ft.Switch(
        value=("services" in STATE.selected_sections),
        active_color=theme.primary,
        scale=0.85,
        on_change=lambda e: _set_offer_services(bool(e.control.value)),
    )

    def _set_offer_services(value: bool) -> None:
        if value:
            STATE.selected_sections.add("services")
        else:
            STATE.selected_sections.discard("services")
        on_state_change()

    services_row = ft.Row(
        controls=[
            services_switch,
            ft.Column(
                controls=[
                    ft.Text(
                        txt["setup_offer_services_label"],
                        color=theme.text,
                        size=12,
                        weight=ft.FontWeight.W_600,
                    ),
                    ft.Text(
                        txt["setup_offer_services_hint"],
                        color=theme.text_muted,
                        size=11,
                    ),
                ],
                spacing=2,
                tight=True,
                expand=True,
            ),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    body = ft.Column(
        controls=[
            ft.Text(
                txt["setup_target_roles_label"],
                color=theme.text,
                size=12,
                weight=ft.FontWeight.W_600,
            ),
            roles_field,
            ft.Container(height=4),
            ft.Text(
                txt["setup_audience_label"],
                color=theme.text,
                size=12,
                weight=ft.FontWeight.W_600,
            ),
            audience_holder,
            ft.Container(height=4),
            ft.Text(
                txt["setup_tone_label"],
                color=theme.text,
                size=12,
                weight=ft.FontWeight.W_600,
            ),
            tone_holder,
            ft.Container(height=8),
            services_row,
        ],
        spacing=6,
        tight=True,
    )

    return _step_card(
        theme,
        label="01",
        title=txt["setup_step1_title"],
        desc=txt["setup_step1_desc"],
        body=body,
    )


def _step_inputs(
    theme: Theme, lang: str, txt: dict, on_state_change: Callable[[], None]
) -> ft.Control:
    resume_holder = ft.Container()
    linkedin_holder = ft.Container()

    def _render_resume() -> None:
        if STATE.resume:
            resume_holder.content = _file_chip(
                theme,
                parsed=_to_parsed(STATE.resume),
                on_clear=_clear_resume,
                clear_tooltip=txt["menu_new_build"],
            )
        else:
            resume_holder.content = ft.Container(
                content=ft.Text(
                    "—",
                    color=theme.text_muted,
                    size=12,
                ),
                padding=ft.padding.symmetric(horizontal=4, vertical=8),
            )
        logger_service.try_update(resume_holder)

    def _render_linkedin() -> None:
        if STATE.linkedin_export:
            linkedin_holder.content = _file_chip(
                theme,
                parsed=_to_parsed(STATE.linkedin_export),
                on_clear=_clear_linkedin,
                clear_tooltip=txt["menu_new_build"],
            )
        else:
            linkedin_holder.content = ft.Container(
                content=ft.Text(
                    "—",
                    color=theme.text_muted,
                    size=12,
                ),
                padding=ft.padding.symmetric(horizontal=4, vertical=8),
            )
        logger_service.try_update(linkedin_holder)

    def _clear_resume() -> None:
        STATE.resume = None
        _render_resume()
        on_state_change()

    def _clear_linkedin() -> None:
        STATE.linkedin_export = None
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
        STATE.linkedin_export = UploadedFile(
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

    github_field = ft.TextField(
        value=STATE.github_url,
        hint_text=txt["setup_github_hint"],
        text_style=ft.TextStyle(color=theme.text, size=13),
        hint_style=ft.TextStyle(color=theme.text_subtle, size=12),
        bgcolor=theme.surface_2,
        border=ft.InputBorder.NONE,
        filled=True,
        cursor_color=theme.primary,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border_radius=10,
        on_change=lambda e: _set_github(e.control.value or ""),
        disabled=STATE.github_skip,
    )
    skip_checkbox = ft.Checkbox(
        value=STATE.github_skip,
        label=txt["setup_github_skip"],
        active_color=theme.primary,
        label_style=ft.TextStyle(color=theme.text, size=12),
        on_change=lambda e: _set_skip(bool(e.control.value)),
    )

    def _set_github(value: str) -> None:
        STATE.github_url = value
        on_state_change()

    def _set_skip(value: bool) -> None:
        STATE.github_skip = value
        if value:
            STATE.github_profile = None
        github_field.disabled = value
        if not logger_service.try_update(github_field):
            logger_service.log_event(
                "DEBUG", "ai_linkedin.tab_setup", "github_field_update_skipped",
            )
        on_state_change()

    notes_field = ft.TextField(
        value=STATE.notes,
        hint_text=txt["setup_notes_hint"],
        multiline=True,
        min_lines=3,
        max_lines=6,
        text_style=ft.TextStyle(color=theme.text, size=13),
        hint_style=ft.TextStyle(color=theme.text_subtle, size=12),
        bgcolor=theme.surface_2,
        border=ft.InputBorder.NONE,
        filled=True,
        cursor_color=theme.primary,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border_radius=10,
        on_change=lambda e: _set_notes(e.control.value or ""),
    )

    def _set_notes(value: str) -> None:
        STATE.notes = value
        on_state_change()

    body = ft.Column(
        controls=[
            ft.Text(
                txt["setup_resume_title"],
                color=theme.text,
                size=12,
                weight=ft.FontWeight.W_600,
            ),
            upload_zone(
                theme,
                title=txt["setup_resume_title"],
                hint=txt["setup_resume_hint"],
                extensions=_RESUME_EXTENSIONS,
                unsupported_message=txt["setup_resume_hint"],
                on_file_resolved=_on_resume,
                paste_path_label=txt["upload_paste_path_btn"],
                paste_path_tooltip=txt["upload_paste_path_tooltip"],
                cta_label=txt["upload_cta_label"],
            ),
            resume_holder,
            ft.Container(height=8),
            ft.Text(
                txt["setup_linkedin_title"],
                color=theme.text,
                size=12,
                weight=ft.FontWeight.W_600,
            ),
            upload_zone(
                theme,
                title=txt["setup_linkedin_title"],
                hint=txt["setup_linkedin_hint"],
                extensions=_LINKEDIN_EXTENSIONS,
                unsupported_message=txt["setup_linkedin_hint"],
                on_file_resolved=_on_linkedin,
                height=104,
                paste_path_label=txt["upload_paste_path_btn"],
                paste_path_tooltip=txt["upload_paste_path_tooltip"],
                cta_label=txt["upload_cta_label"],
            ),
            linkedin_holder,
            ft.Container(height=8),
            ft.Text(
                txt["setup_github_label"],
                color=theme.text,
                size=12,
                weight=ft.FontWeight.W_600,
            ),
            github_field,
            skip_checkbox,
            ft.Container(height=8),
            ft.Text(
                txt["setup_notes_label"],
                color=theme.text,
                size=12,
                weight=ft.FontWeight.W_600,
            ),
            notes_field,
        ],
        spacing=6,
        tight=True,
    )

    return _step_card(
        theme,
        label="02",
        title=txt["setup_step2_title"],
        desc=txt["setup_step2_desc"],
        body=body,
    )


def _step_output(
    theme: Theme, lang: str, txt: dict, on_state_change: Callable[[], None]
) -> ft.Control:
    lang_holder = ft.Container()
    followups_switch = ft.Switch(
        value=STATE.ask_followups or settings_store.get_ask_followups(),
        active_color=theme.primary,
        scale=0.85,
        on_change=lambda e: _set_followups(bool(e.control.value)),
    )

    def _set_lang(value: str) -> None:
        STATE.output_lang = value
        _render_lang()
        on_state_change()

    def _set_followups(value: bool) -> None:
        STATE.ask_followups = value
        try:
            settings_store.set_ask_followups(value)
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.tab_setup", "set_ask_followups_failed", exc,
            )
        on_state_change()

    def _render_lang() -> None:
        active = (STATE.output_lang or lang or "en").lower()
        chips: list[ft.Control] = [
            _option_chip(
                theme,
                label=txt["setup_lang_en"],
                active=active == "en",
                on_click=lambda _e: _set_lang("en"),
            ),
            _option_chip(
                theme,
                label=txt["setup_lang_cs"],
                active=active == "cs",
                on_click=lambda _e: _set_lang("cs"),
            ),
        ]
        lang_holder.content = ft.Row(controls=chips, spacing=8, tight=True)
        logger_service.try_update(lang_holder)

    _render_lang()

    followups_row = ft.Row(
        controls=[
            followups_switch,
            ft.Column(
                controls=[
                    ft.Text(
                        txt["setup_followups_label"],
                        color=theme.text,
                        size=12,
                        weight=ft.FontWeight.W_600,
                    ),
                    ft.Text(
                        txt["setup_followups_hint"],
                        color=theme.text_muted,
                        size=11,
                    ),
                ],
                spacing=2,
                tight=True,
                expand=True,
            ),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    body = ft.Column(
        controls=[
            ft.Text(
                txt["setup_lang_label"],
                color=theme.text,
                size=12,
                weight=ft.FontWeight.W_600,
            ),
            lang_holder,
            ft.Container(height=8),
            followups_row,
        ],
        spacing=6,
        tight=True,
    )
    return _step_card(
        theme,
        label="03",
        title=txt["setup_step3_title"],
        desc=txt["setup_step3_desc"],
        body=body,
    )


def _footer_bar(
    theme: Theme,
    lang: str,
    txt: dict,
    on_navigate_tab: Callable[[int], None],
) -> ft.Container:
    def _on_demo(_e: ft.ControlEvent) -> None:
        STATE.demo_mode = True

        def _worker() -> None:
            try:
                pipeline.load_demo(output_lang=(STATE.output_lang or lang))
            except Exception as exc:
                logger_service.log_exception(
                    "ai_linkedin.tab_setup", "demo_worker_failed", exc,
                )
                return
            REFS.dispatch(lambda: on_navigate_tab(TAB_SECTIONS))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_continue(_e: ft.ControlEvent) -> None:
        if not STATE.demo_mode and not STATE.target_roles:
            logger_service.log_event(
                "WARNING", "ai_linkedin.tab_setup", "continue_no_roles",
            )
            return
        if not STATE.demo_mode:
            provider = settings_store.get_provider()
            key_name = (
                secrets.ANTHROPIC_API_KEY
                if provider == settings_store.PROVIDER_ANTHROPIC
                else secrets.OPENAI_API_KEY
            )
            if not secrets.has_secret(key_name):
                logger_service.log_event(
                    "WARNING", "ai_linkedin.tab_setup",
                    "continue_no_api_key", provider=provider,
                )
        on_navigate_tab(TAB_SECTIONS)

    demo_btn = _flat_button(
        theme,
        txt["setup_demo_button"],
        icon=ft.Icons.AUTO_AWESOME,
        on_click=_on_demo,
    )
    continue_btn = _flat_button(
        theme,
        txt["setup_continue_button"],
        icon=ft.Icons.ARROW_FORWARD,
        primary=True,
        on_click=_on_continue,
    )
    return ft.Container(
        content=ft.Row(
            controls=[
                demo_btn,
                ft.Container(expand=True),
                continue_btn,
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=24, vertical=12),
        border=ft.border.only(top=ft.BorderSide(1, theme.border)),
        bgcolor=theme.bg,
    )


def build_setup_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Callable[[], None],
    on_navigate_tab: Callable[[int], None],
) -> ft.Column:
    txt = s(lang)

    def _on_state_change() -> None:
        safe(REFS.rerender_context)

    body = ft.ListView(
        controls=[
            _step_targeting(theme, lang, txt, _on_state_change),
            _step_inputs(theme, lang, txt, _on_state_change),
            _step_output(theme, lang, txt, _on_state_change),
        ],
        spacing=14,
        padding=ft.padding.symmetric(horizontal=24, vertical=18),
        expand=True,
    )
    footer = _footer_bar(theme, lang, txt, on_navigate_tab)

    return ft.Column(
        controls=[body, footer],
        spacing=0,
        expand=True,
        tight=True,
    )
