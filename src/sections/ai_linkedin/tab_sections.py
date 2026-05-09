"""Sections tab - pick what to build, then run the LinkedIn pipeline.

The user lands here after Setup. Three blocks live in this tab:

1. **Section picker** - presets + a fine-grained checkbox grid.
2. **Post kinds** - secondary picker: which post variants to emit.
3. **Footer bar** - "Ask clarifying questions first" + "Run profile build".

Running the build kicks off :func:`pipeline.run_full_profile_build` on a
worker thread; ``REFS.dispatch`` makes sure the activity feed and the
Output tab repaint as soon as each section comes back from the LLM.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

import flet as ft

from src.services import logger as logger_service
from src.services import secrets, settings_store
from src.sections.ai_linkedin import pipeline
from src.sections.ai_linkedin.data import (
    post_kind_options,
    section_picker_options,
)
from src.sections.ai_linkedin.followup_dialog import open_followup_dialog
from src.sections.ai_linkedin.refs import REFS, safe
from src.sections.ai_linkedin.state import (
    DEFAULT_SECTIONS,
    POST_LEARNING_UPDATE,
    POST_PROJECT_LAUNCH,
    SEC_ABOUT,
    SEC_HEADLINE,
    SEC_POSTS,
    SECTION_IDS,
    STATE,
    TAB_OUTPUT,
)
from src.sections.ai_linkedin.strings import s
from src.theme import Theme


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.tab_sections", "request_full_refresh_import", exc,
        )
        return
    request_section_refresh()


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


def _preset_chip(
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


def _section_card(
    theme: Theme,
    *,
    label: str,
    hint: str,
    selected: bool,
    on_toggle: Callable[[bool], None],
) -> ft.Container:
    def _on_click(_e: ft.ControlEvent) -> None:
        on_toggle(not selected)

    badge = ft.Container(
        content=ft.Icon(
            ft.Icons.CHECK if selected else ft.Icons.ADD,
            color=ft.Colors.WHITE if selected else theme.text_muted,
            size=14,
        ),
        width=24,
        height=24,
        bgcolor=theme.primary if selected else theme.surface_2,
        border_radius=12,
        alignment=ft.Alignment.CENTER,
    )
    return ft.Container(
        content=ft.Row(
            controls=[
                badge,
                ft.Column(
                    controls=[
                        ft.Text(
                            label,
                            color=theme.text,
                            size=13,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Text(
                            hint,
                            color=theme.text_muted,
                            size=11,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                    tight=True,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        bgcolor=theme.surface,
        border_radius=12,
        border=ft.border.all(
            1,
            theme.primary if selected else theme.border,
        ),
        ink=True,
        on_click=_on_click,
    )


def _build_section_grid(
    theme: Theme, lang: str, on_state_change: Callable[[], None]
) -> ft.Container:
    options = section_picker_options(lang)
    holder = ft.Container()

    def _toggle(key: str, value: bool) -> None:
        if value:
            STATE.selected_sections.add(key)
        else:
            STATE.selected_sections.discard(key)
        _render()
        on_state_change()

    def _render() -> None:
        cards = [
            _section_card(
                theme,
                label=opt["label"],
                hint=opt["hint"],
                selected=opt["key"] in STATE.selected_sections,
                on_toggle=lambda val, k=opt["key"]: _toggle(k, val),
            )
            for opt in options
        ]
        holder.content = ft.Column(
            controls=cards,
            spacing=8,
            tight=True,
        )
        logger_service.try_update(holder)

    _render()
    return holder


def _preset_for_state() -> str:
    selected = set(STATE.selected_sections)
    if selected == {SEC_HEADLINE}:
        return "just_headline"
    if selected == {SEC_ABOUT}:
        return "just_about"
    if selected == {SEC_POSTS}:
        return "just_posts"
    if selected >= set(SECTION_IDS):
        return "everything"
    if selected == set(DEFAULT_SECTIONS):
        return "everything"
    return "custom"


def _post_kind_chips(
    theme: Theme, lang: str, on_state_change: Callable[[], None]
) -> ft.Container:
    holder = ft.Container()
    options = post_kind_options(lang)

    def _toggle(key: str) -> None:
        if key in STATE.selected_post_kinds:
            STATE.selected_post_kinds.discard(key)
        else:
            STATE.selected_post_kinds.add(key)
        _render()
        on_state_change()

    def _render() -> None:
        chips = [
            _preset_chip(
                theme,
                label=opt["label"],
                active=opt["key"] in STATE.selected_post_kinds,
                on_click=lambda _e, k=opt["key"]: _toggle(k),
            )
            for opt in options
        ]
        holder.content = ft.Row(
            controls=chips,
            spacing=8,
            run_spacing=8,
            wrap=True,
        )
        logger_service.try_update(holder)

    _render()
    return holder


def _apply_preset(name: str) -> None:
    if name == "just_headline":
        STATE.selected_sections = {SEC_HEADLINE}
    elif name == "just_about":
        STATE.selected_sections = {SEC_ABOUT}
    elif name == "just_posts":
        STATE.selected_sections = {SEC_POSTS}
        if not STATE.selected_post_kinds:
            STATE.selected_post_kinds = {POST_LEARNING_UPDATE, POST_PROJECT_LAUNCH}
    elif name == "everything":
        STATE.selected_sections = set(SECTION_IDS)


def build_sections_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Callable[[], None],
    on_navigate_tab: Callable[[int], None],
) -> ft.Column:
    txt = s(lang)

    presets_holder = ft.Container()

    def _on_state_change() -> None:
        safe(REFS.rerender_context)
        _render_presets()

    def _render_presets() -> None:
        active = _preset_for_state()
        chips = [
            _preset_chip(
                theme,
                label=txt["sections_preset_just_headline"],
                active=active == "just_headline",
                on_click=lambda _e: (_apply_preset("just_headline"), _on_state_change(), _refresh_grid()),
            ),
            _preset_chip(
                theme,
                label=txt["sections_preset_just_about"],
                active=active == "just_about",
                on_click=lambda _e: (_apply_preset("just_about"), _on_state_change(), _refresh_grid()),
            ),
            _preset_chip(
                theme,
                label=txt["sections_preset_just_posts"],
                active=active == "just_posts",
                on_click=lambda _e: (_apply_preset("just_posts"), _on_state_change(), _refresh_grid()),
            ),
            _preset_chip(
                theme,
                label=txt["sections_preset_everything"],
                active=active == "everything",
                on_click=lambda _e: (_apply_preset("everything"), _on_state_change(), _refresh_grid()),
            ),
            _preset_chip(
                theme,
                label=txt["sections_preset_custom"],
                active=active == "custom",
                on_click=lambda _e: None,
            ),
        ]
        presets_holder.content = ft.Row(
            controls=chips,
            spacing=8,
            run_spacing=8,
            wrap=True,
        )
        logger_service.try_update(presets_holder)

    grid_holder_ref: dict[str, Optional[ft.Container]] = {"holder": None}

    def _refresh_grid() -> None:
        h = grid_holder_ref["holder"]
        if h is None:
            return
        h.content = _build_section_grid(theme, lang, _on_state_change)
        logger_service.try_update(h)

    grid = _build_section_grid(theme, lang, _on_state_change)
    grid_holder = ft.Container(content=grid)
    grid_holder_ref["holder"] = grid_holder
    _render_presets()

    post_kinds_holder = _post_kind_chips(theme, lang, _on_state_change)

    run_holder = ft.Container()

    def _phase_run(*, ask_followups: bool, page: ft.Page | None) -> None:
        STATE.run_stage = "running"
        STATE.last_error = ""
        safe(REFS.rerender_context)

        def _worker() -> None:
            output_lang = (STATE.output_lang or lang or "en")
            try:
                if ask_followups and not STATE.demo_mode:
                    res = pipeline.extract_profile(output_lang=output_lang)
                    if not res.ok:
                        STATE.run_stage = ""
                        REFS.dispatch(_request_full_refresh)
                        return
                    res = pipeline.generate_followup_questions(output_lang=output_lang)
                    if not res.ok:
                        STATE.run_stage = ""
                        REFS.dispatch(_request_full_refresh)
                        return
                    if STATE.followup_questions and page is not None:
                        STATE.run_stage = "followups"
                        REFS.dispatch(
                            lambda: _open_followups(page=page, output_lang=output_lang)
                        )
                        return

                res = pipeline.run_full_profile_build(output_lang=output_lang)
                if not res.ok:
                    STATE.run_stage = ""
                    REFS.dispatch(_request_full_refresh)
                    return
            except Exception as exc:
                logger_service.log_exception(
                    "ai_linkedin.tab_sections", "run_worker_failed", exc,
                )
            STATE.run_stage = ""
            REFS.dispatch(_request_full_refresh)
            REFS.dispatch(lambda: on_navigate_tab(TAB_OUTPUT))

        threading.Thread(target=_worker, daemon=True).start()

    def _open_followups(*, page: ft.Page, output_lang: str) -> None:
        REFS.page = page

        def _on_submit(answers: list[dict]) -> None:
            STATE.followup_qa = answers
            STATE.activity = "analyzing"
            REFS.request_context_refresh()
            REFS.dispatch(_request_full_refresh)

            def _resume_worker() -> None:
                try:
                    res = pipeline.run_full_profile_build(output_lang=output_lang)
                    if not res.ok:
                        STATE.run_stage = ""
                        REFS.dispatch(_request_full_refresh)
                        return
                except Exception as exc:
                    logger_service.log_exception(
                        "ai_linkedin.tab_sections", "resume_worker_failed", exc,
                    )
                STATE.run_stage = ""
                REFS.dispatch(_request_full_refresh)
                REFS.dispatch(lambda: on_navigate_tab(TAB_OUTPUT))

            threading.Thread(target=_resume_worker, daemon=True).start()

        def _on_cancel() -> None:
            STATE.run_stage = ""
            STATE.activity = "ready"
            REFS.request_context_refresh()
            REFS.dispatch(_request_full_refresh)

        open_followup_dialog(
            page,
            theme,
            title=txt["followup_dialog_title"],
            intro=txt["followup_dialog_subtitle"],
            cancel_label=txt["followup_dialog_cancel"],
            continue_label=txt["followup_dialog_submit"],
            answer_hint=txt["followup_dialog_answer_hint"],
            skip_all_label=txt["followup_dialog_skip_all"],
            other_label=txt["followup_dialog_other_label"],
            other_hint=txt["followup_dialog_other_hint"],
            questions=STATE.followup_questions,
            on_submit=_on_submit,
            on_cancel=_on_cancel,
        )

    def _on_run(e: ft.ControlEvent) -> None:
        page = e.page
        if page is not None:
            REFS.page = page
        if not STATE.demo_mode and not STATE.target_roles:
            logger_service.log_event(
                "WARNING", "ai_linkedin.tab_sections", "run_no_target_roles",
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
                    "WARNING", "ai_linkedin.tab_sections",
                    "run_no_api_key", provider=provider,
                )
                return
        ask = STATE.ask_followups
        _phase_run(ask_followups=ask, page=page)
        _render_run()

    def _on_followup_first(e: ft.ControlEvent) -> None:
        page = e.page
        if page is not None:
            REFS.page = page
        STATE.ask_followups = True
        _phase_run(ask_followups=True, page=page)
        _render_run()

    def _render_run() -> None:
        running = bool(STATE.run_stage)
        run_label = txt["sections_run_running"] if running else txt["sections_run_button"]
        run_holder.content = ft.Row(
            controls=[
                _flat_button(
                    theme,
                    txt["sections_followup_button"],
                    icon=ft.Icons.QUIZ_OUTLINED,
                    enabled=not running,
                    on_click=_on_followup_first,
                ),
                ft.Container(expand=True),
                _flat_button(
                    theme,
                    run_label,
                    icon=ft.Icons.PLAY_ARROW_ROUNDED,
                    primary=True,
                    enabled=not running,
                    on_click=_on_run,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        logger_service.try_update(run_holder)

    _render_run()

    section_card_target = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    txt["sections_title"],
                    color=theme.text,
                    size=15,
                    weight=ft.FontWeight.W_700,
                ),
                ft.Text(
                    txt["sections_desc"],
                    color=theme.text_muted,
                    size=12,
                ),
                ft.Container(height=8),
                presets_holder,
                ft.Container(height=10),
                grid_holder,
            ],
            spacing=4,
            tight=True,
        ),
        padding=18,
        bgcolor=theme.surface,
        border_radius=14,
        border=ft.border.all(1, theme.border),
    )

    posts_card = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    txt["sections_post_kinds_title"],
                    color=theme.text,
                    size=15,
                    weight=ft.FontWeight.W_700,
                ),
                ft.Text(
                    txt["sections_post_kinds_desc"],
                    color=theme.text_muted,
                    size=12,
                ),
                ft.Container(height=8),
                post_kinds_holder,
            ],
            spacing=4,
            tight=True,
        ),
        padding=18,
        bgcolor=theme.surface,
        border_radius=14,
        border=ft.border.all(1, theme.border),
    )

    body = ft.ListView(
        controls=[section_card_target, posts_card],
        spacing=14,
        padding=ft.padding.symmetric(horizontal=24, vertical=18),
        expand=True,
    )

    footer = ft.Container(
        content=run_holder,
        padding=ft.padding.symmetric(horizontal=24, vertical=12),
        border=ft.border.only(top=ft.BorderSide(1, theme.border)),
        bgcolor=theme.bg,
    )

    return ft.Column(
        controls=[body, footer],
        spacing=0,
        expand=True,
        tight=True,
    )
