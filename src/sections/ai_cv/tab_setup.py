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

from src.components.shared_profile_banner import open_my_profile, shared_profile_banner
from src.qt.icons import Icons
from src.qt.runtime import dispatch as runtime_dispatch
from src.qt.runtime import get_main_window
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
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
from src.sections.ai_cv import pipeline, shared_profile
from src.sections.ai_cv.followup_dialog import open_followup_dialog
from src.sections.ai_cv.refs import REFS
from src.sections.ai_cv.state import (
    STATE,
    TAB_MATCH,
    UploadedFile,
)
from src.sections.ai_cv.strings import s
from src.sections.ai_cv.upload import upload_zone
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
    card.setObjectName("CareerStepCard")
    card.setStyleSheet(
        f"""
        QFrame#CareerStepCard {{
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
    chip.setObjectName("CareerFileChip")
    chip.setStyleSheet(
        f"""
        QFrame#CareerFileChip {{
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

    fetch_status = SubtleLabel("", theme=theme, size=11)
    fetch_status.setVisible(False)
    body_layout.addWidget(fetch_status)

    def _set_fetch_status(message: str, *, error: bool = False) -> None:
        try:
            fetch_status.setText(message)
            fetch_status.setVisible(bool(message))
            fetch_status.setStyleSheet(
                f"color: {'#EF4444' if error else theme.text_subtle}; background: transparent;"
            )
        except RuntimeError:
            logger_service.log_event(
                "INFO", "ai_cv.tab_setup", "fetch_status_stale",
            )

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
        # Targeted updates only - no full section rebuild. Rebuilding the
        # whole tab on fetch start + finish is what made the UI flicker.
        STATE.activity = "scraping"
        STATE.last_error = ""
        try:
            fetch_btn.setEnabled(False)
            fetch_btn.setText(txt["job_url_btn_loading"])
        except RuntimeError:
            pass
        _set_fetch_status("")
        REFS.request_context_refresh()  # sidebar Activity, no rebuild

        def _worker() -> None:
            try:
                text, error = pipeline.fetch_job_text(url)
            except Exception as exc:
                logger_service.log_exception(
                    "ai_cv.tab_setup", "fetch_worker_failed", exc,
                )
                text, error = "", str(exc)

            def _apply() -> None:
                try:
                    fetch_btn.setEnabled(True)
                    fetch_btn.setText(txt["job_url_btn"])
                    if text:
                        # Setting the text fires ``_set_text`` which marks
                        # the source as "paste"; correct it to "scrape"
                        # afterwards so the provenance stays accurate.
                        text_area.setPlainText(text)
                        STATE.job_text = text
                        STATE.job_url = url
                        STATE.job_text_source = "scrape"
                        STATE.activity = "ready"
                        STATE.last_error = ""
                        _set_fetch_status("")
                    else:
                        STATE.activity = "error"
                        STATE.last_error = error or txt["job_url_failed"]
                        _set_fetch_status(STATE.last_error, error=True)
                except RuntimeError:
                    logger_service.log_event(
                        "INFO", "ai_cv.tab_setup", "fetch_apply_stale",
                    )
                REFS.request_context_refresh()

            runtime_dispatch(_apply)

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
        height=160,
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
                "ai_cv.tab_setup", "footer_refresh_failed", exc,
            )

    # Shared career profile - pull the once-uploaded CV (+ LinkedIn /
    # GitHub) into this flow instead of re-uploading. The upload zones in
    # the steps below stay editable for a per-run override.
    if shared_profile.has_shared():
        def _use_shared() -> None:
            shared_profile.apply()
            runtime_dispatch(_request_full_refresh)

        _applied = shared_profile.is_applied()
        body_layout.addWidget(
            shared_profile_banner(
                theme,
                title=txt["shared_title_applied"] if _applied else txt["shared_title_use"],
                summary=shared_profile.build_summary(txt),
                edit_label=txt["shared_edit_btn"],
                on_edit=open_my_profile,
                use_label=txt["shared_use_btn"],
                on_use=_use_shared,
                applied=_applied,
            )
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
    footer.setObjectName("CareerSetupFooter")
    footer.setStyleSheet(
        f"""
        QFrame#CareerSetupFooter {{
            background-color: {theme.bg};
            border-top: 1px solid {theme.border};
        }}
        """
    )
    footer_layout = vbox(spacing=8, margins=(24, 12, 24, 12))
    footer.setLayout(footer_layout)

    controls_row = QFrame()
    controls_row.setStyleSheet("background: transparent;")
    controls_layout = hbox(spacing=12, margins=(0, 0, 0, 0))
    controls_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    controls_row.setLayout(controls_layout)

    followups_col = QFrame()
    followups_col.setStyleSheet("background: transparent;")
    followups_col.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    followups_col_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    followups_col.setLayout(followups_col_layout)
    # The AI now always decides whether clarifying questions are needed -
    # the manual toggle is gone. A subtle hint explains the behaviour.
    followups_col_layout.addWidget(
        SubtleLabel(txt["footer_followup_auto_hint"], theme=theme, size=11, italic=True)
    )
    controls_layout.addWidget(followups_col, 1)

    run_btn = PrimaryButton(txt["footer_run_btn"], theme=theme, icon=Icons.PLAY_ARROW_ROUNDED)
    controls_layout.addWidget(run_btn, 0, Qt.AlignmentFlag.AlignTop)
    footer_layout.addWidget(controls_row)

    status_label = SubtleLabel("", theme=theme, size=11)
    footer_layout.addWidget(status_label)
    layout.addWidget(footer)

    def _set_status(message: str, *, error: bool = False) -> None:
        # ``status_label`` is captured by closures that fire from worker
        # threads via ``runtime_dispatch``. After a section rebuild the
        # underlying QLabel is deleted but the queued callback still
        # runs, raising ``RuntimeError: Internal C++ object ... already
        # deleted``. Swallow it - the new section already rendered the
        # right state, so dropping the late update is harmless.
        try:
            status_label.setText(message)
            status_label.setStyleSheet(
                f"color: {'#EF4444' if error else theme.text_subtle}; background: transparent;"
            )
        except RuntimeError:
            logger_service.log_event(
                "INFO", "ai_cv.tab_setup", "status_label_stale",
            )

    def _refresh_run_button() -> None:
        # Same closure-after-rebuild story as ``_set_status``: the
        # queued ``runtime_dispatch(_refresh_run_button)`` can fire
        # against a deleted button after the section was re-rendered.
        # The fresh section already rebuilt the button with the right
        # enabled state, so dropping the stale update is safe.
        #
        # The button keeps its stable "Run analysis" caption even while a
        # run is in flight - the granular progress ("Scoring the
        # match...", "Looking for unclear items...", ...) now shows in the
        # left-sidebar Activity panel (see ``CareerRefs._activity_label``)
        # instead of inside the button.
        stage = STATE.run_stage
        running = bool(stage)
        enabled = STATE.can_run() and not running
        try:
            run_btn.setText(txt["footer_run_btn"])
            run_btn.setEnabled(enabled)
        except RuntimeError:
            logger_service.log_event(
                "INFO", "ai_cv.tab_setup", "run_btn_stale",
                stage=stage,
            )

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
            # No full rebuild here - it caused the flicker the user saw
            # when answering. The single unavoidable rebuild happens in
            # ``_go_to_match`` once scoring completes.
            STATE.followup_qa = answers
            STATE.activity = "analyzing"
            REFS.request_context_refresh()
            runtime_dispatch(_refresh_run_button)
            threading.Thread(target=_phase2_match, daemon=True).start()

        def _on_cancel() -> None:
            # Dialog dismissed - just reset state + button in place; the
            # setup tab is already on screen, so no rebuild is needed.
            STATE.followup_qa = []
            STATE.activity = "ready"
            STATE.run_stage = ""
            REFS.request_context_refresh()
            runtime_dispatch(_refresh_run_button)

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

    def _on_run() -> None:
        if not STATE.can_run():
            _set_status(txt["run_disabled_hint"], error=True)
            return
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
        STATE.run_stage = "running"
        _refresh_run_button()
        # Surface "Running analysis..." in the sidebar Activity panel right
        # away; subsequent pipeline steps refresh it as the stage advances.
        REFS.request_context_refresh()

        def _phase1() -> None:
            try:
                if (
                    STATE.github_url
                    and not STATE.github_skip
                    and STATE.github_profile is None
                ):
                    STATE.github_profile = pipeline.fetch_github_profile(STATE.github_url)

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

                # Always run the clarify step - the model itself decides
                # whether any questions are warranted (it returns 0-N).
                # We only pause for the dialog when it actually asked
                # something; otherwise we go straight to scoring.
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
                logger_service.log_exception("ai_cv.tab_setup", "phase1_failed", exc)
                runtime_dispatch(lambda: _set_status(str(exc), error=True))
                STATE.run_stage = ""
                runtime_dispatch(_refresh_run_button)

        threading.Thread(target=_phase1, daemon=True).start()

    run_btn.clicked.connect(_on_run)
    return container
