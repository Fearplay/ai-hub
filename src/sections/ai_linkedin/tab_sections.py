"""Sections tab - pick what to build, then run the LinkedIn pipeline (PySide6)."""

from __future__ import annotations

import threading
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.qt.icons import Icons
from src.qt.runtime import dispatch as runtime_dispatch
from src.qt.runtime import get_main_window
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    ClickFrame,
    GhostButton,
    IconLabel,
    MutedLabel,
    PrimaryButton,
    TitleLabel,
    custom_label,
    hbox,
    vbox,
)
from src.services import logger as logger_service
from src.services import secrets, settings_store
from src.sections.ai_linkedin import pipeline
from src.sections.ai_linkedin.data import (
    post_kind_options,
    section_picker_options,
)
from src.sections.ai_linkedin.followup_dialog import open_followup_dialog
from src.sections.ai_linkedin.refs import REFS
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


def _preset_chip(theme: Theme, *, label: str, active: bool, on_click: Callable[[], None]) -> ClickFrame:
    chip = ClickFrame()
    chip.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {theme.primary if active else theme.surface_2};
            border: 1px solid {theme.primary if active else theme.border};
            border-radius: 999px;
        }}
        ClickFrame:hover {{
            background-color: {theme.primary_hover if active else theme.surface};
        }}
        """
    )
    layout = hbox(spacing=0, margins=(12, 7, 12, 7))
    chip.setLayout(layout)
    layout.addWidget(custom_label(
        label,
        color="#FFFFFF" if active else theme.text,
        size=12,
        weight=QFont.Weight.Bold if active else QFont.Weight.Medium,
    ))
    chip.clicked.connect(on_click)
    return chip


def _section_card(
    theme: Theme,
    *,
    label: str,
    hint: str,
    selected: bool,
    on_toggle: Callable[[bool], None],
) -> ClickFrame:
    card = ClickFrame()
    card.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.primary if selected else theme.border};
            border-radius: 12px;
        }}
        ClickFrame:hover {{
            background-color: {theme.surface_2};
        }}
        """
    )
    layout = hbox(spacing=12, margins=(12, 10, 12, 10))
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    card.setLayout(layout)

    badge = QFrame()
    badge.setFixedSize(24, 24)
    badge.setStyleSheet(
        f"background-color: {theme.primary if selected else theme.surface_2}; border-radius: 12px;"
    )
    bl = hbox(spacing=0, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setLayout(bl)
    bl.addWidget(IconLabel(
        Icons.CHECK if selected else Icons.ADD,
        color="#FFFFFF" if selected else theme.text_muted,
        size=14,
    ), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(badge)

    info = QFrame()
    info.setStyleSheet("background: transparent;")
    il = vbox(spacing=2, margins=(0, 0, 0, 0))
    info.setLayout(il)
    il.addWidget(BodyLabel(label, theme=theme, size=13, weight=QFont.Weight.DemiBold))
    il.addWidget(MutedLabel(hint, theme=theme, size=11))
    layout.addWidget(info, 1)

    card.clicked.connect(lambda: on_toggle(not selected))
    return card


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


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            continue
        w = item.widget()
        if w is not None:
            w.deleteLater()


def build_sections_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Callable[[], None],
    on_navigate_tab: Callable[[int], None],
) -> QWidget:
    txt = s(lang)

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    root_layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(root_layout)

    body_holder = QWidget()
    body_holder.setStyleSheet(f"background-color: {theme.bg};")
    body_layout = vbox(spacing=14, margins=(24, 18, 24, 18))
    body_holder.setLayout(body_layout)

    section_card_target = QFrame()
    section_card_target.setStyleSheet(
        f"""
        QFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 14px;
        }}
        """
    )
    sc_layout = vbox(spacing=4, margins=(18, 18, 18, 18))
    section_card_target.setLayout(sc_layout)
    sc_layout.addWidget(TitleLabel(txt["sections_title"], theme=theme, size=15, weight=QFont.Weight.Bold))
    sc_layout.addWidget(MutedLabel(txt["sections_desc"], theme=theme, size=12))
    spacer1 = QWidget()
    spacer1.setFixedHeight(8)
    sc_layout.addWidget(spacer1)

    presets_holder = QWidget()
    presets_holder.setStyleSheet("background: transparent;")
    presets_layout = QGridLayout(presets_holder)
    presets_layout.setContentsMargins(0, 0, 0, 0)
    presets_layout.setHorizontalSpacing(8)
    presets_layout.setVerticalSpacing(8)
    sc_layout.addWidget(presets_holder)

    spacer2 = QWidget()
    spacer2.setFixedHeight(10)
    sc_layout.addWidget(spacer2)

    grid_holder = QWidget()
    grid_holder.setStyleSheet("background: transparent;")
    grid_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    grid_holder.setLayout(grid_layout)
    sc_layout.addWidget(grid_holder)
    body_layout.addWidget(section_card_target)

    posts_card = QFrame()
    posts_card.setStyleSheet(
        f"""
        QFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 14px;
        }}
        """
    )
    posts_layout = vbox(spacing=4, margins=(18, 18, 18, 18))
    posts_card.setLayout(posts_layout)
    posts_layout.addWidget(TitleLabel(txt["sections_post_kinds_title"], theme=theme, size=15, weight=QFont.Weight.Bold))
    posts_layout.addWidget(MutedLabel(txt["sections_post_kinds_desc"], theme=theme, size=12))
    spacer3 = QWidget()
    spacer3.setFixedHeight(8)
    posts_layout.addWidget(spacer3)

    post_kinds_holder = QWidget()
    post_kinds_holder.setStyleSheet("background: transparent;")
    pk_layout = QGridLayout(post_kinds_holder)
    pk_layout.setContentsMargins(0, 0, 0, 0)
    pk_layout.setHorizontalSpacing(8)
    pk_layout.setVerticalSpacing(8)
    posts_layout.addWidget(post_kinds_holder)
    body_layout.addWidget(posts_card)
    body_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(body_holder)
    root_layout.addWidget(scroll, 1)

    footer = QFrame()
    footer.setStyleSheet(f"background-color: {theme.bg}; border-top: 1px solid {theme.border};")
    footer_layout = hbox(spacing=10, margins=(24, 12, 24, 12))
    footer_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    footer.setLayout(footer_layout)

    followup_btn = GhostButton(txt["sections_followup_button"], theme=theme, icon=Icons.QUIZ_OUTLINED)
    footer_layout.addWidget(followup_btn)
    footer_layout.addStretch(1)
    run_btn = PrimaryButton(txt["sections_run_button"], theme=theme, icon=Icons.PLAY_ARROW_ROUNDED)
    footer_layout.addWidget(run_btn)
    root_layout.addWidget(footer)

    def _render_presets() -> None:
        active = _preset_for_state()
        _clear_layout(presets_layout)
        chips = [
            (txt["sections_preset_just_headline"], "just_headline"),
            (txt["sections_preset_just_about"], "just_about"),
            (txt["sections_preset_just_posts"], "just_posts"),
            (txt["sections_preset_everything"], "everything"),
            (txt["sections_preset_custom"], "custom"),
        ]
        col = 0
        for label, key in chips:
            chip = _preset_chip(
                theme,
                label=label,
                active=active == key,
                on_click=(lambda k=key: _on_preset(k)) if key != "custom" else (lambda: None),
            )
            presets_layout.addWidget(chip, 0, col)
            col += 1

    def _on_preset(name: str) -> None:
        _apply_preset(name)
        _render_presets()
        _render_grid()
        _on_state_change()

    def _on_state_change() -> None:
        REFS.request_context_refresh()
        _render_presets()

    def _render_grid() -> None:
        _clear_layout(grid_layout)
        options = section_picker_options(lang)
        for opt in options:
            card = _section_card(
                theme,
                label=opt["label"],
                hint=opt["hint"],
                selected=opt["key"] in STATE.selected_sections,
                on_toggle=lambda val, k=opt["key"]: _toggle_section(k, val),
            )
            grid_layout.addWidget(card)

    def _toggle_section(key: str, value: bool) -> None:
        if value:
            STATE.selected_sections.add(key)
        else:
            STATE.selected_sections.discard(key)
        _render_grid()
        _render_presets()
        _on_state_change()

    def _render_post_kinds() -> None:
        _clear_layout(pk_layout)
        options = post_kind_options(lang)
        col = 0
        for opt in options:
            chip = _preset_chip(
                theme,
                label=opt["label"],
                active=opt["key"] in STATE.selected_post_kinds,
                on_click=lambda k=opt["key"]: _toggle_post_kind(k),
            )
            pk_layout.addWidget(chip, 0, col)
            col += 1

    def _toggle_post_kind(key: str) -> None:
        if key in STATE.selected_post_kinds:
            STATE.selected_post_kinds.discard(key)
        else:
            STATE.selected_post_kinds.add(key)
        _render_post_kinds()
        _on_state_change()

    _render_presets()
    _render_grid()
    _render_post_kinds()

    def _phase_run(*, ask_followups: bool) -> None:
        STATE.run_stage = "running"
        STATE.last_error = ""
        REFS.request_context_refresh()

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
                    if STATE.followup_questions:
                        STATE.run_stage = "followups"
                        REFS.dispatch(lambda: _open_followups(output_lang=output_lang))
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

    def _open_followups(*, output_lang: str) -> None:
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
            get_main_window(),
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

    def _on_run() -> None:
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
        _phase_run(ask_followups=ask)

    def _on_followup_first() -> None:
        STATE.ask_followups = True
        _phase_run(ask_followups=True)

    run_btn.clicked.connect(_on_run)
    followup_btn.clicked.connect(_on_followup_first)

    return container
