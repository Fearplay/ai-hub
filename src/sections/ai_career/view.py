"""AI Career - center column orchestrator.

Header (with the ``?`` button hooked to the section's how-to dialog) +
**top-level mode tab bar** (Chat vs. Form mode) + the body.

* In **Form mode** the body is the historical four-stage tab bar
  (Setup / Match / Documents / History). Stage state lives in
  :data:`STATE.active_tab` so it survives theme / language toggles.
* In **Chat mode** the body is a free-form HR-assistant conversation.
  Transcript state lives in :data:`STATE.chat_messages`, also outside
  ``build_view`` so it survives rebuilds.

Switching between modes is reversible and never throws away the other
mode's state - the user can toggle back and forth without losing their
analysis or their chat.

Re-rendering is delegated to :func:`src.app.request_section_refresh` -
that re-runs ``build_view`` end-to-end and re-mounts the tree under
``AIHubApp._main_container``. Mutating ``content_holder.content`` in
place was unreliable for the deep ``build_documents_tab`` subtree in
Flet 0.84 (the previous body lingered after the user clicked Setup);
re-using the proven section-switch path avoids that entirely.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading

import flet as ft

from src.components.header import HeaderMenuItem, header
from src.components.tab_bar import tab_bar
from src.sections.ai_career import pipeline
from src.sections.ai_career.data import SECTION_ICON
from src.sections.ai_career.how_to import open_career_how_to
from src.sections.ai_career.refs import REFS, safe
from src.sections.ai_career.state import (
    MODE_CHAT,
    MODE_FORM,
    STATE,
    TAB_DOCUMENTS,
    TAB_HISTORY,
    TAB_MATCH,
    TAB_SETUP,
)
from src.sections.ai_career.strings import s
from src.sections.ai_career.tab_chat import build_chat_tab
from src.sections.ai_career.tab_documents import build_documents_tab
from src.sections.ai_career.tab_history import build_history_tab
from src.sections.ai_career.tab_match import build_match_tab
from src.sections.ai_career.tab_setup import build_setup_tab
from src.theme import Theme


def _refresh() -> None:
    """Trigger a full section rebuild via the app shell.

    Imported lazily so this module can be imported during section
    auto-discovery without forcing :mod:`src.app` to load first.
    """
    from src.app import request_section_refresh

    request_section_refresh()


def _open_in_explorer(path: str) -> None:
    if not path or not os.path.isdir(path):
        return
    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


def _show_snack(page: ft.Page | None, message: str) -> None:
    if page is None or not message:
        return
    try:
        page.snack_bar = ft.SnackBar(content=ft.Text(message))
        page.snack_bar.open = True
        page.update()
    except Exception:
        pass


def _mode_tabs(lang: str) -> list[str]:
    txt = s(lang)
    return [txt["mode_chat"], txt["mode_form"]]


def _stage_tabs(lang: str) -> list[str]:
    txt = s(lang)
    return [txt["tab_setup"], txt["tab_match"], txt["tab_documents"], txt["tab_history"]]


def _build_form_tab_body(theme: Theme, lang: str) -> ft.Control:
    if STATE.active_tab == TAB_MATCH:
        return build_match_tab(
            theme,
            lang,
            on_request_rerender=_refresh,
            on_navigate_tab=_navigate_tab,
        )
    if STATE.active_tab == TAB_DOCUMENTS:
        return build_documents_tab(
            theme,
            lang,
            on_request_rerender=_refresh,
            on_navigate_tab=_navigate_tab,
        )
    if STATE.active_tab == TAB_HISTORY:
        return build_history_tab(
            theme,
            lang,
            on_request_rerender=_refresh,
            on_navigate_tab=_navigate_tab,
        )
    return build_setup_tab(
        theme,
        lang,
        on_request_rerender=_refresh,
    )


def _navigate_tab(index: int) -> None:
    """Programmatic navigation hook handed to child tabs.

    Tabs use this to jump the user from e.g. Match -> Documents after
    "Generate documents" finishes. We force Form mode here because the
    Chat body never wants to receive a stage tab index.
    """
    STATE.mode = MODE_FORM
    STATE.active_tab = index
    _refresh()


def build_view(theme: Theme, lang: str) -> ft.Column:
    txt = s(lang)

    # Cache the live page on REFS the moment we have one. The capture
    # below runs only when build_view is hooked into the page tree, but
    # because :func:`_refresh` re-runs ``build_view`` on every state
    # change, REFS.page is refreshed on every rebuild too.
    def _capture_page(control: ft.Control) -> None:
        try:
            page = getattr(control, "page", None)
        except Exception:
            page = None
        if page is not None:
            REFS.page = page

    def _on_stage_tab_change(index: int) -> None:
        if STATE.mode != MODE_FORM:
            return
        if index == STATE.active_tab:
            return
        STATE.active_tab = index
        _refresh()

    def _on_mode_change(index: int) -> None:
        new_mode = MODE_CHAT if index == 0 else MODE_FORM
        if new_mode == STATE.mode:
            return
        STATE.mode = new_mode
        _refresh()

    mode_tab_bar = tab_bar(
        theme,
        tabs=_mode_tabs(lang),
        active_index=0 if STATE.mode == MODE_CHAT else 1,
        on_change=_on_mode_change,
    )
    if STATE.mode == MODE_CHAT:
        stage_tab_bar_control: ft.Control = ft.Container(height=0)
    else:
        stage_tab_bar_control = tab_bar(
            theme,
            tabs=_stage_tabs(lang),
            active_index=STATE.active_tab,
            on_change=_on_stage_tab_change,
        )

    if STATE.mode == MODE_CHAT:
        body_control: ft.Control = build_chat_tab(
            theme,
            lang,
            on_request_rerender=_refresh,
            on_navigate_tab=_navigate_tab,
            on_switch_to_form=_refresh,
        )
    else:
        body_control = _build_form_tab_body(theme, lang)

    content_holder = ft.Container(content=body_control, expand=True)
    _capture_page(content_holder)

    def _on_help(e: ft.ControlEvent) -> None:
        if e.page is None:
            return
        REFS.page = e.page
        open_career_how_to(e.page, theme, lang)

    def _menu_new_run(_e: ft.ControlEvent) -> None:
        STATE.reset_run()
        STATE.demo_mode = False
        STATE.documents.clear()
        STATE.refine_problems.clear()
        STATE.followup_questions = []
        STATE.followup_qa = []
        STATE.mode = MODE_FORM
        STATE.active_tab = TAB_SETUP
        _refresh()

    def _menu_open_history(_e: ft.ControlEvent) -> None:
        STATE.mode = MODE_FORM
        STATE.active_tab = TAB_HISTORY
        _refresh()

    def _menu_open_folder(e: ft.ControlEvent) -> None:
        page = e.page
        if page is not None:
            REFS.page = page
        folder = STATE.last_run_folder
        if not folder or not os.path.isdir(folder):
            _show_snack(page, txt["menu_open_folder_no_run"])
            return
        _open_in_explorer(folder)

    def _menu_save_full(e: ft.ControlEvent) -> None:
        page = e.page
        if page is not None:
            REFS.page = page
        if not STATE.documents:
            _show_snack(page, txt["menu_save_no_run"])
            return
        STATE.activity = "exporting"
        STATE.last_error = ""
        safe(REFS.rerender_context)
        REFS.dispatch(_refresh)

        def _worker() -> None:
            result = pipeline.save_full_analysis()
            STATE.activity = "ready"
            safe(REFS.rerender_context)
            if result.ok and page is not None:
                try:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(
                            txt["menu_save_done_template"].format(path=result.folder)
                        ),
                    )
                    page.snack_bar.open = True
                except Exception:
                    pass
            REFS.dispatch(_refresh)

        threading.Thread(target=_worker, daemon=True).start()

    def _menu_how_to(e: ft.ControlEvent) -> None:
        if e.page is None:
            return
        REFS.page = e.page
        open_career_how_to(e.page, theme, lang)

    menu_items: list[HeaderMenuItem] = [
        HeaderMenuItem(
            icon=ft.Icons.RESTART_ALT,
            label=txt["menu_new_run"],
            on_click=_menu_new_run,
        ),
        HeaderMenuItem(
            icon=ft.Icons.SAVE_OUTLINED,
            label=txt["menu_save_full"],
            on_click=_menu_save_full,
        ),
        HeaderMenuItem(
            icon=ft.Icons.FOLDER_OPEN,
            label=txt["menu_open_folder"],
            on_click=_menu_open_folder,
        ),
        HeaderMenuItem(
            icon=ft.Icons.HISTORY,
            label=txt["menu_show_history"],
            on_click=_menu_open_history,
        ),
        HeaderMenuItem(
            icon=ft.Icons.MENU_BOOK_OUTLINED,
            label=txt["menu_how_to"],
            on_click=_menu_how_to,
        ),
    ]

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
        menu_items=menu_items,
    )

    return ft.Column(
        controls=[
            header_control,
            mode_tab_bar,
            stage_tab_bar_control,
            content_holder,
        ],
        spacing=0,
        expand=True,
        tight=True,
    )
