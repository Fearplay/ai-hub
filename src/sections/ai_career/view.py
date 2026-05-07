"""AI Career - center column orchestrator.

Header (with the ``?`` button hooked to the section's how-to dialog) +
four stage tabs (Setup / Match / Documents / History). State for which
tab is active lives in :data:`STATE.active_tab` so it survives theme
and language toggles.
"""

from __future__ import annotations

import flet as ft

from src.components.header import header
from src.components.tab_bar import tab_bar
from src.sections.ai_career.data import SECTION_ICON
from src.sections.ai_career.how_to import open_career_how_to
from src.sections.ai_career.refs import REFS, safe
from src.sections.ai_career.state import (
    STATE,
    TAB_DOCUMENTS,
    TAB_HISTORY,
    TAB_MATCH,
    TAB_SETUP,
)
from src.sections.ai_career.strings import s
from src.sections.ai_career.tab_documents import build_documents_tab
from src.sections.ai_career.tab_history import build_history_tab
from src.sections.ai_career.tab_match import build_match_tab
from src.sections.ai_career.tab_setup import build_setup_tab
from src.theme import Theme


def _stage_tabs(lang: str) -> list[str]:
    txt = s(lang)
    return [txt["tab_setup"], txt["tab_match"], txt["tab_documents"], txt["tab_history"]]


def _build_tab_body(theme: Theme, lang: str, on_request_rerender, on_navigate_tab) -> ft.Control:
    if STATE.active_tab == TAB_MATCH:
        return build_match_tab(
            theme,
            lang,
            on_request_rerender=on_request_rerender,
            on_navigate_tab=on_navigate_tab,
        )
    if STATE.active_tab == TAB_DOCUMENTS:
        return build_documents_tab(
            theme,
            lang,
            on_request_rerender=on_request_rerender,
            on_navigate_tab=on_navigate_tab,
        )
    if STATE.active_tab == TAB_HISTORY:
        return build_history_tab(
            theme,
            lang,
            on_request_rerender=on_request_rerender,
            on_navigate_tab=on_navigate_tab,
        )
    return build_setup_tab(
        theme,
        lang,
        on_request_rerender=on_request_rerender,
    )


def build_view(theme: Theme, lang: str) -> ft.Column:
    txt = s(lang)

    content_holder = ft.Container(expand=True)
    tab_bar_holder = ft.Container()

    def _rerender_tab_body() -> None:
        content_holder.content = _build_tab_body(
            theme, lang, _rerender_tab_body, _on_navigate_tab
        )
        try:
            content_holder.update()
        except Exception:
            pass

    def _rerender_main() -> None:
        tab_bar_holder.content = tab_bar(
            theme,
            tabs=_stage_tabs(lang),
            active_index=STATE.active_tab,
            on_change=_on_tab_change,
        )
        try:
            tab_bar_holder.update()
        except Exception:
            pass
        _rerender_tab_body()

    def _on_tab_change(index: int) -> None:
        if index == STATE.active_tab:
            return
        STATE.active_tab = index
        _rerender_main()

    def _on_navigate_tab(index: int) -> None:
        STATE.active_tab = index
        _rerender_main()

    REFS.rerender_main = _rerender_main
    REFS.rerender_tab_body = _rerender_tab_body

    tab_bar_holder.content = tab_bar(
        theme,
        tabs=_stage_tabs(lang),
        active_index=STATE.active_tab,
        on_change=_on_tab_change,
    )
    content_holder.content = _build_tab_body(theme, lang, _rerender_tab_body, _on_navigate_tab)

    def _on_help(e: ft.ControlEvent) -> None:
        if e.page is None:
            return
        open_career_how_to(e.page, theme, lang)

    demo_pill: ft.Control | None = None
    if STATE.demo_mode:
        demo_pill = ft.Container(
            content=ft.Text(txt["ctx_demo_pill"], color=ft.Colors.WHITE, size=11, weight=ft.FontWeight.W_700),
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
            bgcolor="#F59E0B",
            border_radius=10,
        )

    header_control = header(
        theme,
        lang,
        icon=SECTION_ICON,
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
        ],
        spacing=0,
        expand=True,
        tight=True,
    )
