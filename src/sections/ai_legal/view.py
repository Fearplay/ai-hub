"""Center column for the AI Legal section.

Layout:

* :func:`src.components.header.header` wrapped in a Stack with the
  ``warning_pill`` overlaid in the top-right corner.
* Interactive :func:`src.components.tab_bar.tab_bar` with four tabs;
  clicking swaps the body container in-place without a global rebuild.
* A ``content_container`` whose ``content`` mutates as the active tab
  changes (state lives in :data:`STATE.active_tab`).
"""

from __future__ import annotations

import flet as ft

from src.components.header import header
from src.components.tab_bar import tab_bar
from src.sections.ai_legal.data import SECTION_ICON, tabs
from src.sections.ai_legal.refs import REFS
from src.sections.ai_legal.state import STATE
from src.sections.ai_legal.strings import s
from src.sections.ai_legal.tab_analysis import build_analysis_tab
from src.sections.ai_legal.tab_chat import build_chat_tab
from src.sections.ai_legal.tab_drafts import build_drafts_tab
from src.sections.ai_legal.tab_templates import build_templates_tab
from src.sections.ai_legal.warning_pill import warning_pill
from src.services import logger as logger_service
from src.theme import Theme


def _build_tab_body(theme: Theme, lang: str, on_request_rerender) -> ft.Control:
    try:
        if STATE.active_tab == 0:
            return build_chat_tab(theme, lang)
        if STATE.active_tab == 1:
            return build_analysis_tab(theme, lang, on_request_rerender=on_request_rerender)
        if STATE.active_tab == 2:
            return build_drafts_tab(theme, lang, on_request_rerender=on_request_rerender)
        if STATE.active_tab == 3:
            return build_templates_tab(theme, lang, on_request_rerender=on_request_rerender)
        return build_chat_tab(theme, lang)
    except Exception as exc:
        logger_service.log_exception(
            "ai_legal.view", "build_tab_body_failed", exc,
            active_tab=STATE.active_tab,
        )
        return ft.Container()


def build_view(theme: Theme, lang: str) -> ft.Column:
    txt = s(lang)

    content_holder = ft.Container(expand=True)
    tab_bar_holder = ft.Container()

    def _rerender_tab_body() -> None:
        try:
            content_holder.content = _build_tab_body(theme, lang, _rerender_tab_body)
        except Exception as exc:
            logger_service.log_exception(
                "ai_legal.view", "rerender_tab_body_failed", exc,
            )
        logger_service.try_update(content_holder)

    def _rerender_main() -> None:
        try:
            tab_bar_holder.content = tab_bar(
                theme,
                tabs=tabs(lang),
                active_index=STATE.active_tab,
                on_change=_on_tab_change,
            )
        except Exception as exc:
            logger_service.log_exception(
                "ai_legal.view", "rerender_main_tab_bar_failed", exc,
            )
        logger_service.try_update(tab_bar_holder)
        _rerender_tab_body()

    def _on_tab_change(index: int) -> None:
        if index == STATE.active_tab:
            return
        logger_service.log_event(
            "INFO", "ai_legal.view", "tab_change",
            prev_tab=STATE.active_tab, new_tab=index,
        )
        STATE.active_tab = index
        _rerender_main()

    REFS.rerender_main = _rerender_main
    REFS.rerender_tab_body = _rerender_tab_body

    tab_bar_holder.content = tab_bar(
        theme,
        tabs=tabs(lang),
        active_index=STATE.active_tab,
        on_change=_on_tab_change,
    )

    content_holder.content = _build_tab_body(theme, lang, _rerender_tab_body)

    header_control = header(
        theme,
        lang,
        icon=SECTION_ICON,
        title=txt["title"],
        subtitle=txt["subtitle"],
    )

    header_with_pill = ft.Stack(
        controls=[
            header_control,
            ft.Container(
                content=warning_pill(theme, lang),
                right=24,
                top=22,
            ),
        ],
    )

    return ft.Column(
        controls=[
            header_with_pill,
            tab_bar_holder,
            content_holder,
        ],
        spacing=0,
        expand=True,
        tight=True,
    )
