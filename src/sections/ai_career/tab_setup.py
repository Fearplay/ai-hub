"""Setup tab - the user picks the role, uploads the resume, runs analysis (PySide6 port)."""

from __future__ import annotations

import threading
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
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
    GhostButton,
    IconLabel,
    IconOnlyButton,
    MutedLabel,
    PrimaryButton,
    SubtleLabel,
    TitleLabel,
    custom_label,
    hbox,
    themed_line_edit,
    themed_text_edit,
    vbox,
)
from src.services import logger as logger_service
from src.services import secrets, settings_store
from src.services.file_parser import ParsedFile, human_size
from src.sections.ai_career import pipeline
from src.sections.ai_career.followup_dialog import open_followup_dialog
from src.sections.ai_career.refs import REFS
from src.sections.ai_career.state import (
    STATE,
    TAB_MATCH,
    UploadedFile,
)
from src.sections.ai_career.strings import s
from src.sections.ai_career.upload import upload_zone
from src.theme import Theme


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception:
        return
    request_section_refresh()


_RESUME_EXTENSIONS = ("pdf", "docx", "txt", "md", "html", "htm")
_LINKEDIN_EXTENSIONS = ("pdf", "txt", "html", "htm")


def _step_card(theme: Theme, *, label: str, title: str, desc: str, body: QWidget) -> QFrame:
    card = QFrame()
    card.setStyleSheet(
        f"""
        QFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 14px;
        }}
        """
    )
    layout = vbox(spacing=4, margins=(18, 18, 18, 18))
    card.setLayout(layout)

    label_widget = custom_label(label, color=theme.primary, size=11, weight=QFont.Weight.Bold)
    f = QFont(label_widget.font())
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.4)
    label_widget.setFont(f)
    layout.addWidget(label_widget)
    layout.addWidget(TitleLabel(title, theme=theme, size=15, weight=QFont.Weight.Bold))
    layout.addWidget(MutedLabel(desc, theme=theme, size=12))
    layout.addSpacing(8)
    layout.addWidget(body)
    return card


def _to_parsed(uploaded: UploadedFile) -> ParsedFile:
    return ParsedFile(
        path=uploaded.path,
        name=uploaded.name,
        ext=uploaded.ext,
        size_bytes=uploaded.size_bytes,
        text=uploaded.text,
        error=None,
    )


def _file_chip(theme: Theme, *, parsed: ParsedFile, on_clear: Callable[[], None], clear_tooltip: str) -> QFrame:
    chip = QFrame()
    chip.setStyleSheet(
        f"""
        QFrame {{
            background-color: {theme.surface_2};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        """
    )
    layout = hbox(spacing=10, margins=(12, 10, 12, 10))
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    chip.setLayout(layout)

    badge = QFrame()
    badge.setFixedSize(32, 32)
    badge.setStyleSheet(f"background-color: {rgba(theme.primary, 0.14)}; border-radius: 8px;")
    bl = hbox(spacing=0, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setLayout(bl)
    bl.addWidget(IconLabel(Icons.DESCRIPTION_OUTLINED, color=theme.primary, size=18),
                 alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(badge)

    info = QFrame()
    info.setStyleSheet("background: transparent;")
    info.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    info_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    info.setLayout(info_layout)
    info_layout.addWidget(BodyLabel(parsed.name, theme=theme, size=13, weight=QFont.Weight.DemiBold))
    info_layout.addWidget(MutedLabel(f"{parsed.ext.upper()} \u00b7 {human_size(parsed.size_bytes)}", theme=theme, size=11))
    layout.addWidget(info, 1)

    close = IconOnlyButton(Icons.CLOSE, color=theme.text_muted, size=16, bg_hover=theme.surface, tooltip=clear_tooltip)
    close.clicked.connect(on_clear)
    layout.addWidget(close)
    return chip


def _step_1(theme: Theme, txt: dict, on_state_change: Callable[[], None]) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    url_row = QFrame()
    url_row.setStyleSheet("background: transparent;")
    url_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    url_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    url_row.setLayout(url_layout)

    url_field = themed_line_edit(theme, placeholder=txt["job_url_hint"])
    url_field.setText(STATE.job_url)
    def _set_url(value: str) -> None:
        STATE.job_url = value
        on_state_change()
    url_field.textChanged.connect(_set_url)
    url_layout.addWidget(url_field, 1)

    fetch_btn = PrimaryButton(txt["job_url_btn"], theme=theme, icon=Icons.DOWNLOAD_OUTLINED)
    url_layout.addWidget(fetch_btn)
    body_layout.addWidget(url_row)

    text_area = themed_text_edit(theme, placeholder=txt["job_text_hint"], min_height=140)
    text_area.setPlainText(STATE.job_text)
    def _set_text() -> None:
        STATE.job_text = text_area.toPlainText()
        STATE.job_text_source = "paste" if STATE.job_text else ""
        on_state_change()
    text_area.textChanged.connect(_set_text)
    body_layout.addWidget(text_area)

    def _start_fetch() -> None:
        url = url_field.text().strip()
        if not url:
            return
        STATE.activity = "scraping"
        STATE.last_error = ""
        REFS.request_context_refresh()
        REFS.dispatch(_request_full_refresh)

        def _worker() -> None:
            text, error = pipeline.fetch_job_text(url)
            if text:
                STATE.job_text = text
                STATE.job_url = url
                STATE.job_text_source = "scrape"
                STATE.activity = "ready"
                STATE.last_error = ""
            else:
                STATE.activity = "error"
                STATE.last_error = error or txt["job_url_failed"]
            REFS.request_context_refresh()
            REFS.dispatch(_request_full_refresh)

        threading.Thread(target=_worker, daemon=True).start()

    fetch_btn.clicked.connect(_start_fetch)
    return _step_card(theme, label=txt["step_1_label"], title=txt["step_1_title"], desc=txt["step_1_desc"], body=body)


def _step_2(theme: Theme, txt: dict, on_state_change: Callable[[], None]) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    body_layout.addWidget(BodyLabel(txt["resume_label"], theme=theme, size=13, weight=QFont.Weight.DemiBold))

    resume_holder = QWidget()
    resume_holder.setStyleSheet("background: transparent;")
    resume_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    resume_holder.setLayout(resume_layout)

    def _refresh_resume_chip() -> None:
        while resume_layout.count():
            it = resume_layout.takeAt(0)
            if it is None:
                continue
            w = it.widget()
            if w is not None:
                w.deleteLater()
        if STATE.resume:
            resume_layout.addWidget(_file_chip(theme, parsed=_to_parsed(STATE.resume), on_clear=_clear_resume, clear_tooltip=txt["resume_clear_btn"]))
        else:
            resume_layout.addWidget(MutedLabel(txt["resume_no_file"], theme=theme, size=12))

    def _clear_resume() -> None:
        STATE.resume = None
        _refresh_resume_chip()
        on_state_change()

    def _on_resume(parsed: ParsedFile) -> None:
        STATE.resume = UploadedFile(
            path=parsed.path,
            name=parsed.name,
            ext=parsed.ext,
            size_bytes=parsed.size_bytes,
            text=parsed.text,
        )
        _refresh_resume_chip()
        on_state_change()

    body_layout.addWidget(upload_zone(
        theme,
        title=txt["resume_drop_title"],
        hint=txt["resume_drop_hint"],
        extensions=_RESUME_EXTENSIONS,
        unsupported_message=txt["resume_unsupported"],
        on_file_resolved=_on_resume,
        paste_path_label=txt["upload_paste_path_btn"],
        paste_path_tooltip=txt["upload_paste_path_tooltip"],
        cta_label=txt["upload_cta_label"],
    ))
    body_layout.addWidget(resume_holder)
    _refresh_resume_chip()

    body_layout.addSpacing(8)
    body_layout.addWidget(BodyLabel(txt["linkedin_label"], theme=theme, size=13, weight=QFont.Weight.DemiBold))

    linkedin_holder = QWidget()
    linkedin_holder.setStyleSheet("background: transparent;")
    linkedin_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    linkedin_holder.setLayout(linkedin_layout)

    def _refresh_linkedin_chip() -> None:
        while linkedin_layout.count():
            it = linkedin_layout.takeAt(0)
            if it is None:
                continue
            w = it.widget()
            if w is not None:
                w.deleteLater()
        if STATE.linkedin:
            linkedin_layout.addWidget(_file_chip(theme, parsed=_to_parsed(STATE.linkedin), on_clear=_clear_linkedin, clear_tooltip=txt["resume_clear_btn"]))
        else:
            linkedin_layout.addWidget(MutedLabel(txt["linkedin_no_file"], theme=theme, size=12))

    def _clear_linkedin() -> None:
        STATE.linkedin = None
        _refresh_linkedin_chip()
        on_state_change()

    def _on_linkedin(parsed: ParsedFile) -> None:
        STATE.linkedin = UploadedFile(
            path=parsed.path,
            name=parsed.name,
            ext=parsed.ext,
            size_bytes=parsed.size_bytes,
            text=parsed.text,
        )
        _refresh_linkedin_chip()
        on_state_change()

    body_layout.addWidget(upload_zone(
        theme,
        title=txt["linkedin_drop_title"],
        hint=txt["linkedin_drop_hint"],
        extensions=_LINKEDIN_EXTENSIONS,
        unsupported_message=txt["resume_unsupported"],
        on_file_resolved=_on_linkedin,
        height=104,
        paste_path_label=txt["upload_paste_path_btn"],
        paste_path_tooltip=txt["upload_paste_path_tooltip"],
        cta_label=txt["upload_cta_label"],
    ))
    body_layout.addWidget(linkedin_holder)
    _refresh_linkedin_chip()

    return _step_card(theme, label=txt["step_2_label"], title=txt["step_2_title"], desc=txt["step_2_desc"], body=body)


def _step_3(theme: Theme, txt: dict, on_state_change: Callable[[], None]) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    url_field = themed_line_edit(theme, placeholder=txt["github_url_hint"])
    url_field.setText(STATE.github_url)
    url_field.setEnabled(not STATE.github_skip)
    def _set_url(value: str) -> None:
        STATE.github_url = value
        on_state_change()
    url_field.textChanged.connect(_set_url)
    body_layout.addWidget(url_field)

    skip_box = QCheckBox(txt["github_skip_label"])
    skip_box.setChecked(STATE.github_skip)
    skip_box.setStyleSheet(
        f"""
        QCheckBox {{ color: {theme.text}; font-size: 12px; spacing: 8px; }}
        QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {theme.border}; border-radius: 4px; background-color: {theme.surface_2}; }}
        QCheckBox::indicator:checked {{ background-color: {theme.primary}; border: 1px solid {theme.primary}; }}
        """
    )
    def _set_skip(state) -> None:
        STATE.github_skip = bool(skip_box.isChecked())
        if STATE.github_skip:
            STATE.github_profile = None
        url_field.setEnabled(not STATE.github_skip)
        on_state_change()
    skip_box.stateChanged.connect(_set_skip)
    body_layout.addWidget(skip_box)

    has_token = secrets.has_secret(secrets.GITHUB_TOKEN)
    note_text = txt["github_token_note_authenticated" if has_token else "github_token_note_anonymous"]
    body_layout.addWidget(SubtleLabel(note_text, theme=theme, size=11, italic=True))
    return _step_card(theme, label=txt["step_3_label"], title=txt["step_3_title"], desc=txt["step_3_desc"], body=body)


def build_setup_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Callable[[], None],
) -> QWidget:
    txt = s(lang)

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    body_holder = QWidget()
    body_holder.setStyleSheet(f"background-color: {theme.bg};")
    body_layout = vbox(spacing=14, margins=(24, 18, 24, 18))
    body_holder.setLayout(body_layout)

    state_change_holder = {"fn": lambda: None}
    def _on_state_change() -> None:
        fn = state_change_holder["fn"]
        try:
            fn()
        except Exception as exc:
            logger_service.log_exception(
                "ai_career.tab_setup", "footer_refresh_failed", exc,
            )

    body_layout.addWidget(_step_1(theme, txt, _on_state_change))
    body_layout.addWidget(_step_2(theme, txt, _on_state_change))
    body_layout.addWidget(_step_3(theme, txt, _on_state_change))
    body_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(body_holder)
    layout.addWidget(scroll, 1)

    footer = QFrame()
    footer.setStyleSheet(f"background-color: {theme.bg}; border-top: 1px solid {theme.border};")
    footer_layout = vbox(spacing=8, margins=(24, 12, 24, 12))
    footer.setLayout(footer_layout)

    button_row = QFrame()
    button_row.setStyleSheet("background: transparent;")
    button_row_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    button_row_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    button_row.setLayout(button_row_layout)

    demo_btn = GhostButton(txt["footer_demo_btn"], theme=theme, icon=Icons.AUTO_AWESOME)
    button_row_layout.addWidget(demo_btn)
    button_row_layout.addStretch(1)
    run_btn = PrimaryButton(txt["footer_run_btn"], theme=theme, icon=Icons.PLAY_ARROW_ROUNDED)
    button_row_layout.addWidget(run_btn)
    footer_layout.addWidget(button_row)

    status_label = SubtleLabel("", theme=theme, size=11)
    footer_layout.addWidget(status_label)

    followups_row = QFrame()
    followups_row.setStyleSheet("background: transparent;")
    followups_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    followups_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    followups_row.setLayout(followups_layout)
    fu_check = QCheckBox(txt["footer_followup_label"])
    fu_check.setChecked(settings_store.get_ask_followups())
    fu_check.setStyleSheet(
        f"""
        QCheckBox {{ color: {theme.text}; font-size: 11px; font-weight: 600; spacing: 8px; }}
        QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {theme.border}; border-radius: 4px; background-color: {theme.surface_2}; }}
        QCheckBox::indicator:checked {{ background-color: {theme.primary}; border: 1px solid {theme.primary}; }}
        """
    )
    fu_check.stateChanged.connect(lambda s: settings_store.set_ask_followups(bool(fu_check.isChecked())))
    followups_layout.addWidget(fu_check)
    followups_layout.addWidget(MutedLabel(txt["footer_followup_desc"], theme=theme, size=10))
    followups_layout.addStretch(1)
    footer_layout.addWidget(followups_row)
    layout.addWidget(footer)

    def _set_status(message: str, *, error: bool = False) -> None:
        status_label.setText(message)
        status_label.setStyleSheet(
            f"color: {'#EF4444' if error else theme.text_subtle}; background: transparent;"
        )

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

    def _refresh_run_button() -> None:
        stage = STATE.run_stage
        running = bool(stage)
        enabled = STATE.can_run() and not running
        run_btn.setText(_label_for(stage))
        run_btn.setEnabled(enabled)

    state_change_holder["fn"] = _refresh_run_button
    _refresh_run_button()

    def _go_to_match() -> None:
        STATE.active_tab = TAB_MATCH
        REFS.dispatch(_request_full_refresh)

    def _phase2_match() -> None:
        STATE.run_stage = "match"
        runtime_dispatch(_refresh_run_button)
        result = pipeline.analyze_match(output_lang=lang)
        if not result.ok:
            runtime_dispatch(lambda: _set_status(result.error, error=True))
            STATE.run_stage = ""
            runtime_dispatch(_refresh_run_button)
            return
        STATE.activity = "ready"
        STATE.run_stage = ""
        REFS.request_context_refresh()
        runtime_dispatch(_refresh_run_button)
        _go_to_match()

    def _open_followup_dialog_now() -> None:
        def _on_submit(answers: list[dict]) -> None:
            STATE.followup_qa = answers
            STATE.activity = "analyzing"
            REFS.request_context_refresh()
            REFS.dispatch(_request_full_refresh)
            threading.Thread(target=_phase2_match, daemon=True).start()

        def _on_cancel() -> None:
            STATE.followup_qa = []
            STATE.activity = "ready"
            STATE.run_stage = ""
            REFS.request_context_refresh()
            runtime_dispatch(_refresh_run_button)
            REFS.dispatch(_request_full_refresh)

        open_followup_dialog(
            get_main_window(),
            theme,
            title=txt["followup_title"],
            intro=txt["followup_intro"],
            cancel_label=txt["followup_cancel"],
            continue_label=txt["followup_continue"],
            answer_hint=txt["followup_answer_hint"],
            skip_all_label=txt["followup_skip_all"],
            other_label=txt["followup_other_label"],
            other_hint=txt["followup_other_hint"],
            questions=STATE.followup_questions,
            on_submit=_on_submit,
            on_cancel=_on_cancel,
        )

    def _on_demo() -> None:
        STATE.demo_mode = True
        pipeline.load_demo(output_lang=lang)
        STATE.active_tab = TAB_MATCH
        REFS.dispatch(_request_full_refresh)
    demo_btn.clicked.connect(_on_demo)

    def _on_run() -> None:
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
                _set_status(txt["error_no_key_template"].format(provider=provider), error=True)
                return

        STATE.followup_questions = []
        STATE.followup_qa = []
        _set_status("")
        STATE.run_stage = "demo" if STATE.demo_mode else "running"
        _refresh_run_button()

        def _phase1() -> None:
            try:
                if (
                    not STATE.demo_mode
                    and STATE.github_url
                    and not STATE.github_skip
                    and STATE.github_profile is None
                ):
                    STATE.github_profile = pipeline.fetch_github_profile(STATE.github_url)

                if STATE.demo_mode:
                    pipeline.load_demo(output_lang=lang)
                    STATE.run_stage = ""
                    runtime_dispatch(_refresh_run_button)
                    _go_to_match()
                    return

                res = pipeline.extract_candidate(output_lang=lang)
                if not res.ok:
                    runtime_dispatch(lambda: _set_status(res.error, error=True))
                    STATE.run_stage = ""
                    runtime_dispatch(_refresh_run_button)
                    return

                res = pipeline.extract_job_spec(output_lang=lang)
                if not res.ok:
                    runtime_dispatch(lambda: _set_status(res.error, error=True))
                    STATE.run_stage = ""
                    runtime_dispatch(_refresh_run_button)
                    return

                if settings_store.get_ask_followups():
                    STATE.run_stage = "followups"
                    runtime_dispatch(_refresh_run_button)
                    STATE.activity = "followups"
                    REFS.request_context_refresh()
                    res = pipeline.generate_followup_questions(output_lang=lang)
                    if not res.ok:
                        runtime_dispatch(lambda: _set_status(res.error, error=True))
                        STATE.run_stage = ""
                        runtime_dispatch(_refresh_run_button)
                        return
                    if STATE.followup_questions:
                        STATE.activity = "waiting_user"
                        REFS.request_context_refresh()
                        REFS.dispatch(_open_followup_dialog_now)
                        return

                _phase2_match()
            except Exception as exc:
                logger_service.log_exception("ai_career.tab_setup", "phase1_failed", exc)
                runtime_dispatch(lambda: _set_status(str(exc), error=True))
                STATE.run_stage = ""
                runtime_dispatch(_refresh_run_button)

        threading.Thread(target=_phase1, daemon=True).start()

    run_btn.clicked.connect(_on_run)
    return container
