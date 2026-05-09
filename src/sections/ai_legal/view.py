"""Center column for the AI Legal section.

Layout:

* :func:`src.components.header.header` overlaid with the
  ``warning_pill`` aligned to the top-right.
* Interactive :func:`src.components.tab_bar.tab_bar` with four tabs;
  clicking swaps the body widget in-place without a global rebuild.
* A ``content_holder`` whose child changes as the active tab changes
  (state lives in :data:`STATE.active_tab`).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QStackedLayout,
    QWidget,
)

from src.components.header import header
from src.components.tab_bar import tab_bar
from src.qt.widgets import vbox
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


def _build_tab_body(
    theme: Theme,
    lang: str,
    on_request_rerender,
) -> QWidget:
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
        return QWidget()


def build_view(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    header_widget = header(theme, lang, icon=SECTION_ICON, title=txt["title"], subtitle=txt["subtitle"])
    pill_widget = warning_pill(theme, lang)

    header_with_pill = QFrame()
    header_with_pill.setStyleSheet("background: transparent;")
    overlay_layout = QHBoxLayout(header_with_pill)
    overlay_layout.setContentsMargins(0, 0, 0, 0)
    overlay_layout.setSpacing(0)
    overlay_layout.addWidget(header_widget, 1)
    pill_holder = QFrame()
    pill_holder.setStyleSheet("background: transparent;")
    pill_layout = vbox(spacing=0, margins=(0, 22, 24, 0))
    pill_holder.setLayout(pill_layout)
    pill_layout.addWidget(pill_widget, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
    pill_layout.addStretch(1)
    overlay_layout.addWidget(pill_holder, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
    layout.addWidget(header_with_pill)

    tab_bar_holder = QWidget()
    tab_bar_holder.setStyleSheet(f"background-color: {theme.bg};")
    tab_bar_layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    tab_bar_holder.setLayout(tab_bar_layout)
    layout.addWidget(tab_bar_holder)

    body_holder = QWidget()
    body_holder.setStyleSheet(f"background-color: {theme.bg};")
    body_stack = QStackedLayout(body_holder)
    body_stack.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(body_holder, 1)

    def _clear(layout_obj) -> None:
        while layout_obj.count():
            item = layout_obj.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _rerender_tab_body() -> None:
        while body_stack.count():
            w = body_stack.widget(0)
            body_stack.removeWidget(w)
            w.deleteLater()
        try:
            body_stack.addWidget(_build_tab_body(theme, lang, _rerender_tab_body))
        except Exception as exc:
            logger_service.log_exception("ai_legal.view", "rerender_tab_body_failed", exc)

    def _rerender_main() -> None:
        _clear(tab_bar_layout)
        try:
            tab_bar_layout.addWidget(
                tab_bar(
                    theme,
                    tabs=tabs(lang),
                    active_index=STATE.active_tab,
                    on_change=_on_tab_change,
                )
            )
        except Exception as exc:
            logger_service.log_exception("ai_legal.view", "rerender_main_tab_bar_failed", exc)
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

    tab_bar_layout.addWidget(
        tab_bar(
            theme,
            tabs=tabs(lang),
            active_index=STATE.active_tab,
            on_change=_on_tab_change,
        )
    )
    body_stack.addWidget(_build_tab_body(theme, lang, _rerender_tab_body))

    return container
