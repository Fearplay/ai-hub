"""Right-hand context panel for AI Career.

Three cards stack here:

* **Session cost** - calls / tokens / dollar estimate from
  :data:`src.services.cost_tracker.COST`. Hidden in Demo mode (always $0).
* **Activity** - one-line status reflecting the pipeline stage (idle,
  scraping, parsing, analyzing, generating, exporting, error).
* **Quick actions** - shortcuts to start a fresh run, open History, or
  reopen the how-to dialog.

The view subscribes a re-render callback on :data:`COST` so each LLM call
updates the panel without an explicit page repaint.
"""

from __future__ import annotations

import flet as ft

from src.components.context_panel import context_panel_shell
from src.components.section_card import section_card
from src.services import settings_store
from src.services.cost_tracker import COST
from src.sections.ai_career.refs import REFS
from src.sections.ai_career.state import (
    STATE,
    TAB_HISTORY,
    TAB_SETUP,
)
from src.sections.ai_career.strings import s
from src.theme import Theme


_ACTIVITY_KEYS = {
    "ready": "ctx_activity_ready",
    "scraping": "ctx_activity_scraping",
    "parsing": "ctx_activity_parsing",
    "analyzing": "ctx_activity_analyzing",
    "followups": "ctx_activity_followups",
    "waiting_user": "ctx_activity_waiting_user",
    "generating": "ctx_activity_generating",
    "exporting": "ctx_activity_exporting",
    "error": "ctx_activity_error",
}


def _cost_card(theme: Theme, lang: str, txt: dict) -> ft.Control:
    if STATE.demo_mode:
        body = ft.Text(txt["ctx_cost_demo"], color=theme.text_muted, size=12)
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
                    txt["ctx_cost_calls_template"].format(calls=COST.calls, tokens=COST.tokens_total),
                    color=theme.text,
                    size=13,
                ),
                ft.Text(
                    txt["ctx_cost_session_template"].format(cost=COST.cost_usd),
                    color=theme.text,
                    size=13,
                    weight=ft.FontWeight.W_700,
                ),
                ft.Text(
                    txt["ctx_provider_template"].format(provider=provider_label.title(), model=model_label),
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


def _activity_card(theme: Theme, lang: str, txt: dict) -> ft.Control:
    key = _ACTIVITY_KEYS.get(STATE.activity, "ctx_activity_ready")
    label = txt.get(key) or txt["ctx_activity_ready"]
    color = "#22C55E" if STATE.activity == "ready" else (
        "#EF4444" if STATE.activity == "error" else
        "#F59E0B" if STATE.activity == "waiting_user" else
        theme.primary
    )
    body = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Container(
                        width=10,
                        height=10,
                        bgcolor=color,
                        border_radius=5,
                    ),
                    ft.Text(label, color=theme.text, size=13, weight=ft.FontWeight.W_600, expand=True),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ],
        spacing=4,
        tight=True,
    )
    if STATE.last_error and STATE.activity == "error":
        body.controls.append(ft.Text(STATE.last_error, color="#EF4444", size=11))

    return section_card(
        theme,
        ft.Icons.RADIO_BUTTON_CHECKED,
        txt["ctx_activity_title"],
        body,
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

    def _new_run(_e: ft.ControlEvent) -> None:
        STATE.reset_run()
        STATE.demo_mode = False
        STATE.documents.clear()
        STATE.refine_problems.clear()
        STATE.active_tab = TAB_SETUP
        if REFS.rerender_main:
            REFS.rerender_main()

    def _open_history(_e: ft.ControlEvent) -> None:
        STATE.active_tab = TAB_HISTORY
        if REFS.rerender_main:
            REFS.rerender_main()

    def _open_how_to(e: ft.ControlEvent) -> None:
        from src.sections.ai_career.how_to import open_career_how_to

        if e.page is not None:
            open_career_how_to(e.page, theme, lang)

    body = ft.Column(
        controls=[
            _row(ft.Icons.RESTART_ALT, txt["ctx_qa_new_run"], _new_run),
            _row(ft.Icons.HISTORY, txt["ctx_qa_show_history"], _open_history),
            _row(ft.Icons.MENU_BOOK_OUTLINED, txt["ctx_qa_open_how_to"], _open_how_to),
        ],
        spacing=2,
        tight=True,
    )
    return section_card(
        theme,
        ft.Icons.BOLT_OUTLINED,
        txt["ctx_quick_actions_title"],
        body,
    )


# Tracks the previously-subscribed cost listener so we can release it when
# the section is rebuilt (theme / lang change, return to AI Career, …).
_PREV_UNSUBSCRIBE: dict[str, object] = {"fn": None}


def build_context(theme: Theme, lang: str) -> ft.Container:
    txt = s(lang)

    panel_holder = ft.Container()

    def _render() -> None:
        panel_holder.content = context_panel_shell(
            theme,
            _cost_card(theme, lang, txt),
            _activity_card(theme, lang, txt),
            _quick_actions_card(theme, lang, txt),
        )
        try:
            panel_holder.update()
        except Exception:
            pass

    def _on_cost_change() -> None:
        _render()

    prev = _PREV_UNSUBSCRIBE.get("fn")
    if callable(prev):
        try:
            prev()
        except Exception:
            pass
    _PREV_UNSUBSCRIBE["fn"] = COST.subscribe(_on_cost_change)
    REFS.rerender_context = _render

    _render()
    return panel_holder
