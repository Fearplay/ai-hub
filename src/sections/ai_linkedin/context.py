"""Right-hand context panel for AI LinkedIn.

Five cards stack here, in order:

* **Brand profile** - one-glance summary of who the LinkedIn assistant
  is writing for (name, role, industry, audience, tone).
* **Activity** - one-line status reflecting the pipeline stage (ready,
  scraping, parsing, extracting, analyzing, generating, scoring, saving,
  error). Mirrors the Activity card from AI Career so users get a
  consistent feedback channel across sections.
* **Attachments** (Chat mode only) - the parsed documents the user has
  pasted into the chat input.
* **Quick actions** - shortcuts to start a fresh build, open History,
  or reopen the how-to dialog.
* **Recent profile builds** - last few runs the user saved on disk.
* **Run cost** - calls / tokens / dollar estimate from the cost
  tracker. Hidden in Demo mode.

The view subscribes a re-render callback on :data:`COST` so each LLM
call updates the panel without an explicit page repaint, and exposes a
``REFS.rerender_context`` hook so worker threads in ``pipeline.py`` can
ask for a refresh after every activity-state change.
"""

from __future__ import annotations

import flet as ft

from src.components.context_panel import context_panel_shell
from src.components.section_card import section_card
from src.services import logger as logger_service
from src.services import settings_store, store
from src.services.cost_tracker import COST
from src.sections.ai_linkedin.data import (
    brand_profile_fields,
    quick_actions,
    recent_runs,
)
from src.sections.ai_linkedin.refs import REFS
from src.sections.ai_linkedin.state import (
    MODE_CHAT,
    MODE_BUILDER,
    STATE,
    TAB_HISTORY,
    TAB_SETUP,
)
from src.sections.ai_linkedin.strings import s
from src.theme import Theme


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.context", "request_full_refresh_import", exc,
        )
        return
    request_section_refresh()


_ACTIVITY_KEYS = {
    "ready": "ctx_activity_ready",
    "scraping": "ctx_activity_scraping",
    "parsing": "ctx_activity_parsing",
    "extracting": "ctx_activity_extracting",
    "analyzing": "ctx_activity_analyzing",
    "generating": "ctx_activity_generating",
    "scoring": "ctx_activity_scoring",
    "saving": "ctx_activity_saving",
    "error": "ctx_activity_error",
}


def _brief_field(theme: Theme, *, label: str, value: str, chip: bool = False) -> ft.Column:
    if chip:
        value_control: ft.Control = ft.Container(
            content=ft.Text(
                value,
                color=theme.text,
                size=12,
                weight=ft.FontWeight.W_500,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
            bgcolor=ft.Colors.with_opacity(0.18, theme.primary),
            border_radius=12,
            alignment=ft.Alignment.CENTER_LEFT,
        )
    else:
        value_control = ft.Text(
            value,
            color=theme.text,
            size=13,
            weight=ft.FontWeight.W_500,
        )

    label_text = ft.Text(
        label,
        color=theme.text_muted,
        size=11,
        weight=ft.FontWeight.W_500,
    )

    if chip:
        body: ft.Control = ft.Row(controls=[value_control], alignment=ft.MainAxisAlignment.START)
    else:
        body = value_control

    return ft.Column(controls=[label_text, body], spacing=4, tight=True)


def _brief_content(theme: Theme, lang: str) -> ft.Column:
    return ft.Column(
        controls=[
            _brief_field(
                theme,
                label=field["label"],
                value=field["value"],
                chip=field.get("chip", False),
            )
            for field in brand_profile_fields(lang)
        ],
        spacing=12,
        tight=True,
    )


def _brand_card(theme: Theme, lang: str, txt: dict) -> ft.Control:
    return section_card(
        theme,
        ft.Icons.PERSON_OUTLINE,
        txt["ctx_brand_title"],
        _brief_content(theme, lang),
    )


def _activity_card(theme: Theme, txt: dict) -> ft.Control:
    key = _ACTIVITY_KEYS.get(STATE.activity, "ctx_activity_ready")
    label = txt.get(key) or txt["ctx_activity_ready"]
    color = "#22C55E" if STATE.activity == "ready" else (
        "#EF4444" if STATE.activity == "error" else theme.primary
    )
    body_controls: list[ft.Control] = [
        ft.Row(
            controls=[
                ft.Container(
                    width=10,
                    height=10,
                    bgcolor=color,
                    border_radius=5,
                ),
                ft.Text(
                    label,
                    color=theme.text,
                    size=13,
                    weight=ft.FontWeight.W_600,
                    expand=True,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    ]
    if STATE.last_error and STATE.activity == "error":
        body_controls.append(
            ft.Text(STATE.last_error, color="#EF4444", size=11)
        )
    return section_card(
        theme,
        ft.Icons.RADIO_BUTTON_CHECKED,
        txt["ctx_activity_title"],
        ft.Column(controls=body_controls, spacing=6, tight=True),
    )


def _attachments_card(theme: Theme, txt: dict) -> ft.Control:
    if not STATE.chat_attachments:
        body: ft.Control = ft.Text(
            "—",
            color=theme.text_muted,
            size=12,
        )
    else:
        rows: list[ft.Control] = []
        for name in list(STATE.chat_attachments.keys()):
            rows.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, color=theme.primary, size=16),
                            ft.Text(
                                name,
                                color=theme.text,
                                size=12,
                                expand=True,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.CLOSE,
                                icon_color=theme.text_muted,
                                icon_size=14,
                                on_click=lambda e, n=name: _remove_attachment(n),
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    bgcolor=theme.surface_2,
                    border_radius=8,
                )
            )
        body = ft.Column(controls=rows, spacing=6, tight=True)
    return section_card(
        theme,
        ft.Icons.ATTACH_FILE,
        txt["ctx_attachments_title"],
        body,
    )


def _remove_attachment(name: str) -> None:
    STATE.chat_attachments.pop(name, None)
    if REFS.rerender_context:
        try:
            REFS.rerender_context()
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.context", "remove_attachment_rerender_failed", exc,
            )


def _quick_actions_card(theme: Theme, lang: str, txt: dict) -> ft.Control:
    def _row(icon: str, label: str, on_click) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, color=theme.text_muted, size=16),
                    ft.Text(label, color=theme.text, size=13, expand=True),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color=theme.text_muted, size=16),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=8, vertical=10),
            border_radius=8,
            ink=True,
            on_click=on_click,
        )

    def _new_build(_e: ft.ControlEvent) -> None:
        STATE.reset_all()
        STATE.mode = MODE_BUILDER
        STATE.active_tab = TAB_SETUP
        _request_full_refresh()

    def _improve_headline(_e: ft.ControlEvent) -> None:
        from src.sections.ai_linkedin.state import SEC_HEADLINE
        STATE.mode = MODE_BUILDER
        STATE.active_tab = TAB_SETUP
        STATE.selected_sections = {SEC_HEADLINE}
        _request_full_refresh()

    def _write_post(_e: ft.ControlEvent) -> None:
        from src.sections.ai_linkedin.state import SEC_POSTS
        STATE.mode = MODE_BUILDER
        STATE.active_tab = TAB_SETUP
        STATE.selected_sections = {SEC_POSTS}
        _request_full_refresh()

    def _open_history(_e: ft.ControlEvent) -> None:
        STATE.mode = MODE_BUILDER
        STATE.active_tab = TAB_HISTORY
        _request_full_refresh()

    def _open_how_to(e: ft.ControlEvent) -> None:
        from src.sections.ai_linkedin.how_to import open_linkedin_how_to

        if e.page is not None:
            REFS.page = e.page
            open_linkedin_how_to(e.page, theme, lang)

    handlers = {
        "build_full": _new_build,
        "improve_headline": _improve_headline,
        "write_post": _write_post,
        "show_history": _open_history,
        "how_to": _open_how_to,
    }

    rows: list[ft.Control] = []
    for action in quick_actions(lang):
        handler = handlers.get(action["key"])
        if handler is None:
            continue
        rows.append(_row(action["icon"], action["label"], handler))

    body = ft.Column(controls=rows, spacing=2, tight=True)
    return section_card(
        theme,
        ft.Icons.BOLT_OUTLINED,
        txt["ctx_quick_actions_title"],
        body,
    )


def _recent_card(theme: Theme, lang: str, txt: dict) -> ft.Control:
    runs = recent_runs(lang)
    rows: list[ft.Control] = []
    for entry in runs:
        rows.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            entry["title"],
                            color=theme.text,
                            size=12,
                            weight=ft.FontWeight.W_600,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(
                            entry.get("time") or "—",
                            color=theme.text_muted,
                            size=11,
                        ),
                    ],
                    spacing=2,
                    tight=True,
                ),
                padding=ft.padding.symmetric(horizontal=4, vertical=6),
                border_radius=6,
                ink=True,
                on_click=lambda e: None,
            )
        )
    body = ft.Column(controls=rows, spacing=4, tight=True)
    return section_card(
        theme,
        ft.Icons.HISTORY,
        txt["ctx_recent_title"],
        body,
    )


def _cost_card(theme: Theme, txt: dict) -> ft.Control:
    if STATE.demo_mode:
        body: ft.Control = ft.Text(
            "—",
            color=theme.text_muted,
            size=12,
        )
    else:
        provider_label = (
            settings_store.PROVIDER_OPENAI
            if settings_store.get_provider() == settings_store.PROVIDER_OPENAI
            else settings_store.PROVIDER_ANTHROPIC
        )
        model_label = settings_store.get_model()
        body = ft.Column(
            controls=[
                ft.Text(
                    f"{COST.calls} calls · {COST.tokens_total} tokens",
                    color=theme.text,
                    size=13,
                ),
                ft.Text(
                    f"~ ${COST.cost_usd:.4f}",
                    color=theme.text,
                    size=13,
                    weight=ft.FontWeight.W_700,
                ),
                ft.Text(
                    f"{provider_label.title()} · {model_label}",
                    color=theme.text_subtle,
                    size=11,
                    italic=True,
                ),
            ],
            spacing=2,
            tight=True,
        )
    return section_card(
        theme,
        ft.Icons.PAYMENTS_OUTLINED,
        txt["ctx_cost_title"],
        body,
    )


_PREV_UNSUBSCRIBE: dict[str, object] = {"fn": None}


def build_context(theme: Theme, lang: str) -> ft.Container:
    txt = s(lang)

    panel_holder = ft.Container()

    def _render() -> None:
        cards: list[ft.Control] = [
            _brand_card(theme, lang, txt),
            _activity_card(theme, txt),
        ]
        if STATE.mode == MODE_CHAT:
            cards.append(_attachments_card(theme, txt))
        cards.append(_quick_actions_card(theme, lang, txt))
        cards.append(_recent_card(theme, lang, txt))
        cards.append(_cost_card(theme, txt))
        panel_holder.content = context_panel_shell(theme, *cards)
        if not logger_service.try_update(panel_holder):
            logger_service.log_event(
                "DEBUG", "ai_linkedin.context", "panel_holder_update_skipped",
            )
        # Reading ``panel_holder.page`` directly would raise
        # ``RuntimeError: Control must be added to the page first`` on
        # the very first render (called synchronously from
        # ``build_context`` before the panel is mounted). The app keeps
        # a live ``ft.Page`` reference we can grab without walking the
        # parent chain, so use that instead and store it on REFS for
        # later worker threads.
        try:
            from src.app import get_active_page
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.context", "page_import_failed", exc,
            )
            return
        page = get_active_page()
        if page is None:
            return
        REFS.page = page
        try:
            page.update()
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.context", "page_update_failed", exc,
            )

    def _on_cost_change() -> None:
        _render()

    prev = _PREV_UNSUBSCRIBE.get("fn")
    if callable(prev):
        try:
            prev()
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.context", "cost_unsubscribe_failed", exc,
            )
    _PREV_UNSUBSCRIBE["fn"] = COST.subscribe(_on_cost_change)
    REFS.rerender_context = _render

    # Eagerly load existing runs so the recent card paints something
    # useful even before the user opens the History tab.
    try:
        store.list_runs()
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.context", "list_runs_warmup_failed", exc,
        )

    _render()
    return panel_holder
