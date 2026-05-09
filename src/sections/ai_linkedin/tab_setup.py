"""Setup tab - targeting + uploads + output language for AI LinkedIn (PySide6 port)."""

from __future__ import annotations

import threading
from typing import Callable

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
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    ClickFrame,
    GhostButton,
    IconLabel,
    IconOnlyButton,
    MutedLabel,
    PrimaryButton,
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
from src.sections.ai_linkedin import pipeline
from src.sections.ai_linkedin.data import audience_options, tone_options
from src.sections.ai_linkedin.refs import REFS, safe
from src.sections.ai_linkedin.state import (
    STATE,
    TAB_SECTIONS,
    UploadedFile,
)
from src.sections.ai_linkedin.strings import s
from src.sections.ai_linkedin.upload import upload_zone
from src.theme import Theme


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

    label_text = custom_label(label, color=theme.primary, size=11, weight=QFont.Weight.Bold)
    f = QFont(label_text.font())
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.4)
    label_text.setFont(f)
    layout.addWidget(label_text)
    layout.addWidget(TitleLabel(title, theme=theme, size=15, weight=QFont.Weight.Bold))
    layout.addWidget(MutedLabel(desc, theme=theme, size=12))
    layout.addSpacing(8)
    layout.addWidget(body)
    return card


def _file_chip(
    theme: Theme,
    *,
    parsed: ParsedFile,
    on_clear: Callable[[], None],
    clear_tooltip: str,
) -> QFrame:
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
    badge.setStyleSheet(
        f"background-color: {rgba(theme.primary, 0.14)}; border-radius: 8px;"
    )
    bl = hbox(spacing=0, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setLayout(bl)
    bl.addWidget(IconLabel(Icons.DESCRIPTION_OUTLINED, color=theme.primary, size=18),
                 alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(badge)

    info = QFrame()
    info.setStyleSheet("background: transparent; border: none;")
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


def _option_chip(
    theme: Theme,
    *,
    label: str,
    active: bool,
    on_click: Callable[[], None],
) -> ClickFrame:
    chip = ClickFrame()
    chip.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {theme.primary if active else theme.surface_2};
            border: 1px solid {theme.primary if active else theme.border};
            border-radius: 999px;
        }}
        ClickFrame:hover {{
            border: 1px solid {theme.primary};
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


def _to_parsed(uploaded: UploadedFile) -> ParsedFile:
    return ParsedFile(
        path=uploaded.path,
        name=uploaded.name,
        ext=uploaded.ext,
        size_bytes=uploaded.size_bytes,
        text=uploaded.text,
        error=None,
    )


def _step_targeting(
    theme: Theme,
    lang: str,
    txt: dict,
    on_state_change: Callable[[], None],
    rebuild: Callable[[], None],
) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=6, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    body_layout.addWidget(BodyLabel(txt["setup_target_roles_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold))
    roles_field = themed_text_edit(theme, placeholder=txt["setup_target_roles_hint"], min_height=70)
    roles_field.setPlainText("\n".join(STATE.target_roles))

    def _on_roles_changed() -> None:
        text = roles_field.toPlainText()
        STATE.target_roles = [line.strip() for line in text.splitlines() if line.strip()]
        on_state_change()

    roles_field.textChanged.connect(_on_roles_changed)
    body_layout.addWidget(roles_field)

    body_layout.addSpacing(4)
    body_layout.addWidget(BodyLabel(txt["setup_audience_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold))
    audience_holder = QFrame()
    audience_holder.setStyleSheet("background: transparent;")
    audience_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    audience_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
    audience_holder.setLayout(audience_layout)

    def _make_audience_chip(opt: dict) -> ClickFrame:
        return _option_chip(
            theme,
            label=opt["label"],
            active=STATE.audience == opt["key"],
            on_click=lambda k=opt["key"]: _set_audience(k),
        )

    def _set_audience(key: str) -> None:
        STATE.audience = key
        rebuild()

    for opt in audience_options(lang):
        audience_layout.addWidget(_make_audience_chip(opt))
    audience_layout.addStretch(1)
    body_layout.addWidget(audience_holder)

    body_layout.addSpacing(4)
    body_layout.addWidget(BodyLabel(txt["setup_tone_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold))
    tone_holder = QFrame()
    tone_holder.setStyleSheet("background: transparent;")
    tone_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    tone_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
    tone_holder.setLayout(tone_layout)

    def _set_tone(key: str) -> None:
        STATE.tone = key
        rebuild()

    for opt in tone_options(lang):
        tone_layout.addWidget(_option_chip(
            theme, label=opt["label"], active=STATE.tone == opt["key"],
            on_click=lambda k=opt["key"]: _set_tone(k),
        ))
    tone_layout.addStretch(1)
    body_layout.addWidget(tone_holder)
    body_layout.addSpacing(8)

    services_row = QFrame()
    services_row.setStyleSheet("background: transparent;")
    services_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    services_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    services_row.setLayout(services_layout)

    services_check = QCheckBox()
    services_check.setChecked("services" in STATE.selected_sections)
    services_check.setStyleSheet(f"QCheckBox {{ color: {theme.text}; }}")

    def _on_services(state: int) -> None:
        if state == Qt.CheckState.Checked.value:
            STATE.selected_sections.add("services")
        else:
            STATE.selected_sections.discard("services")
        on_state_change()

    services_check.stateChanged.connect(_on_services)
    services_layout.addWidget(services_check)

    info = QFrame()
    info.setStyleSheet("background: transparent;")
    info.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    info_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    info.setLayout(info_layout)
    info_layout.addWidget(BodyLabel(txt["setup_offer_services_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold))
    info_layout.addWidget(MutedLabel(txt["setup_offer_services_hint"], theme=theme, size=11))
    services_layout.addWidget(info, 1)

    body_layout.addWidget(services_row)
    return _step_card(theme, label="01", title=txt["setup_step1_title"], desc=txt["setup_step1_desc"], body=body)


def _step_inputs(
    theme: Theme,
    lang: str,
    txt: dict,
    on_state_change: Callable[[], None],
    rebuild: Callable[[], None],
) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=6, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    def _clear_resume() -> None:
        STATE.resume = None
        rebuild()

    def _clear_linkedin() -> None:
        STATE.linkedin_export = None
        rebuild()

    def _on_resume(parsed: ParsedFile) -> None:
        STATE.resume = UploadedFile(path=parsed.path, name=parsed.name, ext=parsed.ext, size_bytes=parsed.size_bytes, text=parsed.text)
        rebuild()

    def _on_linkedin(parsed: ParsedFile) -> None:
        STATE.linkedin_export = UploadedFile(path=parsed.path, name=parsed.name, ext=parsed.ext, size_bytes=parsed.size_bytes, text=parsed.text)
        rebuild()

    body_layout.addWidget(BodyLabel(txt["setup_resume_title"], theme=theme, size=12, weight=QFont.Weight.DemiBold))
    body_layout.addWidget(upload_zone(
        theme,
        title=txt["setup_resume_title"],
        hint=txt["setup_resume_hint"],
        extensions=_RESUME_EXTENSIONS,
        unsupported_message=txt["setup_resume_hint"],
        on_file_resolved=_on_resume,
        paste_path_label=txt["upload_paste_path_btn"],
        paste_path_tooltip=txt["upload_paste_path_tooltip"],
        cta_label=txt["upload_cta_label"],
    ))
    if STATE.resume:
        body_layout.addWidget(_file_chip(theme, parsed=_to_parsed(STATE.resume), on_clear=_clear_resume, clear_tooltip=txt["menu_new_build"]))
    else:
        body_layout.addWidget(MutedLabel("\u2014", theme=theme, size=12))
    body_layout.addSpacing(8)

    body_layout.addWidget(BodyLabel(txt["setup_linkedin_title"], theme=theme, size=12, weight=QFont.Weight.DemiBold))
    body_layout.addWidget(upload_zone(
        theme,
        title=txt["setup_linkedin_title"],
        hint=txt["setup_linkedin_hint"],
        extensions=_LINKEDIN_EXTENSIONS,
        unsupported_message=txt["setup_linkedin_hint"],
        on_file_resolved=_on_linkedin,
        height=104,
        paste_path_label=txt["upload_paste_path_btn"],
        paste_path_tooltip=txt["upload_paste_path_tooltip"],
        cta_label=txt["upload_cta_label"],
    ))
    if STATE.linkedin_export:
        body_layout.addWidget(_file_chip(theme, parsed=_to_parsed(STATE.linkedin_export), on_clear=_clear_linkedin, clear_tooltip=txt["menu_new_build"]))
    else:
        body_layout.addWidget(MutedLabel("\u2014", theme=theme, size=12))
    body_layout.addSpacing(8)

    body_layout.addWidget(BodyLabel(txt["setup_github_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold))
    github_field = themed_line_edit(theme, placeholder=txt["setup_github_hint"])
    github_field.setText(STATE.github_url)
    github_field.setEnabled(not STATE.github_skip)
    github_field.textChanged.connect(lambda v: _set_github(v))

    def _set_github(value: str) -> None:
        STATE.github_url = value
        on_state_change()

    body_layout.addWidget(github_field)
    skip_check = QCheckBox(txt["setup_github_skip"])
    skip_check.setChecked(STATE.github_skip)
    skip_check.setStyleSheet(f"QCheckBox {{ color: {theme.text}; }}")
    skip_check.stateChanged.connect(lambda st: _set_skip(st == Qt.CheckState.Checked.value))

    def _set_skip(value: bool) -> None:
        STATE.github_skip = value
        if value:
            STATE.github_profile = None
        rebuild()

    body_layout.addWidget(skip_check)
    body_layout.addSpacing(8)

    body_layout.addWidget(BodyLabel(txt["setup_notes_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold))
    notes_field = themed_text_edit(theme, placeholder=txt["setup_notes_hint"], min_height=120)
    notes_field.setPlainText(STATE.notes)

    def _on_notes_changed() -> None:
        STATE.notes = notes_field.toPlainText()
        on_state_change()

    notes_field.textChanged.connect(_on_notes_changed)
    body_layout.addWidget(notes_field)

    return _step_card(theme, label="02", title=txt["setup_step2_title"], desc=txt["setup_step2_desc"], body=body)


def _step_output(
    theme: Theme,
    lang: str,
    txt: dict,
    on_state_change: Callable[[], None],
    rebuild: Callable[[], None],
) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=6, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    body_layout.addWidget(BodyLabel(txt["setup_lang_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold))

    active = (STATE.output_lang or lang or "en").lower()

    def _set_lang(value: str) -> None:
        STATE.output_lang = value
        rebuild()

    lang_holder = QFrame()
    lang_holder.setStyleSheet("background: transparent;")
    lang_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    lang_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
    lang_holder.setLayout(lang_layout)
    lang_layout.addWidget(_option_chip(theme, label=txt["setup_lang_en"], active=active == "en", on_click=lambda: _set_lang("en")))
    lang_layout.addWidget(_option_chip(theme, label=txt["setup_lang_cs"], active=active == "cs", on_click=lambda: _set_lang("cs")))
    lang_layout.addStretch(1)
    body_layout.addWidget(lang_holder)
    body_layout.addSpacing(8)

    followups_row = QFrame()
    followups_row.setStyleSheet("background: transparent;")
    fr_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    fr_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    followups_row.setLayout(fr_layout)

    followups_check = QCheckBox()
    followups_check.setChecked(STATE.ask_followups or settings_store.get_ask_followups())
    followups_check.setStyleSheet(f"QCheckBox {{ color: {theme.text}; }}")

    def _set_followups(state: int) -> None:
        value = state == Qt.CheckState.Checked.value
        STATE.ask_followups = value
        try:
            settings_store.set_ask_followups(value)
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.tab_setup", "set_ask_followups_failed", exc,
            )
        on_state_change()

    followups_check.stateChanged.connect(_set_followups)
    fr_layout.addWidget(followups_check)

    info = QFrame()
    info.setStyleSheet("background: transparent;")
    info.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    info_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    info.setLayout(info_layout)
    info_layout.addWidget(BodyLabel(txt["setup_followups_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold))
    info_layout.addWidget(MutedLabel(txt["setup_followups_hint"], theme=theme, size=11))
    fr_layout.addWidget(info, 1)
    body_layout.addWidget(followups_row)

    return _step_card(theme, label="03", title=txt["setup_step3_title"], desc=txt["setup_step3_desc"], body=body)


def _footer_bar(
    theme: Theme,
    lang: str,
    txt: dict,
    on_navigate_tab: Callable[[int], None],
) -> QFrame:
    bar = QFrame()
    bar.setStyleSheet(f"background-color: {theme.bg}; border-top: 1px solid {theme.border};")
    layout = hbox(spacing=10, margins=(24, 12, 24, 12))
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    bar.setLayout(layout)

    def _on_demo() -> None:
        STATE.demo_mode = True

        def _worker() -> None:
            try:
                pipeline.load_demo(output_lang=(STATE.output_lang or lang))
            except Exception as exc:
                logger_service.log_exception(
                    "ai_linkedin.tab_setup", "demo_worker_failed", exc,
                )
                return
            runtime_dispatch(lambda: on_navigate_tab(TAB_SECTIONS))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_continue() -> None:
        if not STATE.demo_mode and not STATE.target_roles:
            logger_service.log_event(
                "WARNING", "ai_linkedin.tab_setup", "continue_no_roles",
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
                    "WARNING", "ai_linkedin.tab_setup", "continue_no_api_key", provider=provider,
                )
        on_navigate_tab(TAB_SECTIONS)

    demo_btn = GhostButton(txt["setup_demo_button"], theme=theme, icon=Icons.AUTO_AWESOME)
    demo_btn.clicked.connect(_on_demo)
    layout.addWidget(demo_btn)
    layout.addStretch(1)

    continue_btn = PrimaryButton(txt["setup_continue_button"], theme=theme, icon=Icons.ARROW_FORWARD)
    continue_btn.clicked.connect(_on_continue)
    layout.addWidget(continue_btn)
    return bar


def build_setup_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Callable[[], None],
    on_navigate_tab: Callable[[int], None],
) -> QWidget:
    txt = s(lang)

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    def _on_state_change() -> None:
        safe(REFS.rerender_context)

    inner = QWidget()
    inner.setStyleSheet(f"background-color: {theme.bg};")
    inner_layout = vbox(spacing=14, margins=(24, 18, 24, 18))
    inner.setLayout(inner_layout)
    inner_layout.addWidget(_step_targeting(theme, lang, txt, _on_state_change, on_request_rerender))
    inner_layout.addWidget(_step_inputs(theme, lang, txt, _on_state_change, on_request_rerender))
    inner_layout.addWidget(_step_output(theme, lang, txt, _on_state_change, on_request_rerender))
    inner_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(inner)
    layout.addWidget(scroll, 1)

    layout.addWidget(_footer_bar(theme, lang, txt, on_navigate_tab))
    return container
