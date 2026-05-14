"""Setup tab - the user describes the role + location and runs the search.

Four step cards stacked in a scroll area:

1. Keywords (free text).
2. Profile - any combination of free-text bio, uploaded CV / LinkedIn
   export, or public LinkedIn URL. All optional.
3. Location - dropdown with presets + free-text override on "Custom".
4. Filters - work-mode radio group + max-results spinner.

A sticky footer hosts the ``Search positions`` button + status label.
The button stays disabled until at least one input is provided (see
:meth:`JobsState.can_run`).
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QWidget,
)

from src.qt.icons import Icons
from src.qt.runtime import dispatch as runtime_dispatch
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
from src.sections.ai_jobs import data as jobs_data
from src.sections.ai_jobs import pipeline
from src.sections.ai_jobs.refs import REFS
from src.sections.ai_jobs.state import (
    MAX_RESULTS_MAX,
    MAX_RESULTS_MIN,
    STATE,
    TAB_RESULTS,
    UploadedFile,
    WORK_MODE_ANY,
)
from src.sections.ai_jobs.strings import s
from src.sections.ai_jobs.upload import upload_zone
from src.theme import Theme


_PROFILE_EXTENSIONS = ("pdf", "docx", "txt", "md", "html", "htm")


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception:
        return
    request_section_refresh()


def _step_card(theme: Theme, *, label: str, title: str, desc: str, body: QWidget) -> QFrame:
    card = QFrame()
    card.setObjectName("JobsStepCard")
    card.setStyleSheet(
        f"""
        QFrame#JobsStepCard {{
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


def _file_chip(
    theme: Theme,
    *,
    parsed: ParsedFile,
    on_clear: Callable[[], None],
    clear_tooltip: str,
) -> QFrame:
    chip = QFrame()
    chip.setObjectName("JobsFileChip")
    chip.setStyleSheet(
        f"""
        QFrame#JobsFileChip {{
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
    bl.addWidget(
        IconLabel(Icons.DESCRIPTION_OUTLINED, color=theme.primary, size=18),
        alignment=Qt.AlignmentFlag.AlignCenter,
    )
    layout.addWidget(badge)

    info = QFrame()
    info.setStyleSheet("background: transparent;")
    info.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    info_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    info.setLayout(info_layout)
    info_layout.addWidget(BodyLabel(parsed.name, theme=theme, size=13, weight=QFont.Weight.DemiBold))
    info_layout.addWidget(
        MutedLabel(f"{parsed.ext.upper()} \u00b7 {human_size(parsed.size_bytes)}", theme=theme, size=11)
    )
    layout.addWidget(info, 1)

    close = IconOnlyButton(
        Icons.CLOSE,
        color=theme.text_muted,
        size=16,
        bg_hover=theme.surface,
        tooltip=clear_tooltip,
    )
    close.clicked.connect(on_clear)
    layout.addWidget(close)
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


def _step_keywords(theme: Theme, txt: dict, on_state_change: Callable[[], None]) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    field = themed_line_edit(theme, placeholder=txt["keywords_hint"])
    field.setText(STATE.keywords)
    def _on_text(value: str) -> None:
        STATE.keywords = value
        on_state_change()
    field.textChanged.connect(_on_text)
    body_layout.addWidget(field)
    body_layout.addWidget(SubtleLabel(txt["keywords_synonyms_note"], theme=theme, size=11, italic=True))

    return _step_card(
        theme,
        label=txt["step_1_label"],
        title=txt["step_1_title"],
        desc=txt["step_1_desc"],
        body=body,
    )


def _step_profile(theme: Theme, txt: dict, on_state_change: Callable[[], None]) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    body_layout.addWidget(
        BodyLabel(txt["profile_text_label"], theme=theme, size=13, weight=QFont.Weight.DemiBold)
    )
    text_area = themed_text_edit(theme, placeholder=txt["profile_text_hint"], min_height=110)
    text_area.setPlainText(STATE.profile_text)
    def _on_text() -> None:
        STATE.profile_text = text_area.toPlainText()
        on_state_change()
    text_area.textChanged.connect(_on_text)
    body_layout.addWidget(text_area)

    body_layout.addSpacing(6)
    body_layout.addWidget(
        BodyLabel(txt["profile_file_label"], theme=theme, size=13, weight=QFont.Weight.DemiBold)
    )

    file_holder = QWidget()
    file_holder.setStyleSheet("background: transparent;")
    file_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    file_holder.setLayout(file_layout)

    def _refresh_chip() -> None:
        while file_layout.count():
            it = file_layout.takeAt(0)
            if it is None:
                continue
            w = it.widget()
            if w is not None:
                w.deleteLater()
        if STATE.profile_file:
            file_layout.addWidget(
                _file_chip(
                    theme,
                    parsed=_to_parsed(STATE.profile_file),
                    on_clear=_clear_file,
                    clear_tooltip=txt["profile_file_clear"],
                )
            )
        else:
            file_layout.addWidget(MutedLabel(txt["profile_file_no_file"], theme=theme, size=12))

    def _clear_file() -> None:
        STATE.profile_file = None
        _refresh_chip()
        on_state_change()

    def _on_file(parsed: ParsedFile) -> None:
        STATE.profile_file = UploadedFile(
            path=parsed.path,
            name=parsed.name,
            ext=parsed.ext,
            size_bytes=parsed.size_bytes,
            text=parsed.text,
        )
        _refresh_chip()
        on_state_change()

    body_layout.addWidget(
        upload_zone(
            theme,
            title=txt["profile_file_drop_title"],
            hint=txt["profile_file_drop_hint"],
            extensions=_PROFILE_EXTENSIONS,
            unsupported_message=txt["profile_file_unsupported"],
            on_file_resolved=_on_file,
        )
    )
    body_layout.addWidget(file_holder)
    _refresh_chip()

    body_layout.addSpacing(6)
    body_layout.addWidget(
        BodyLabel(txt["linkedin_label"], theme=theme, size=13, weight=QFont.Weight.DemiBold)
    )
    linkedin_field = themed_line_edit(theme, placeholder=txt["linkedin_hint"])
    linkedin_field.setText(STATE.linkedin_url)
    def _on_linkedin(value: str) -> None:
        STATE.linkedin_url = value
        on_state_change()
    linkedin_field.textChanged.connect(_on_linkedin)
    body_layout.addWidget(linkedin_field)

    return _step_card(
        theme,
        label=txt["step_2_label"],
        title=txt["step_2_title"],
        desc=txt["step_2_desc"],
        body=body,
    )


def _styled_combo(theme: Theme) -> QComboBox:
    combo = QComboBox()
    combo.setStyleSheet(
        f"""
        QComboBox {{
            background-color: {theme.surface_2};
            color: {theme.text};
            border: 1px solid transparent;
            border-radius: 10px;
            padding: 8px 12px;
            min-height: 22px;
        }}
        QComboBox:hover {{
            border: 1px solid {rgba(theme.primary, 0.30)};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 22px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {theme.surface};
            color: {theme.text};
            border: 1px solid {theme.border};
            selection-background-color: {rgba(theme.primary, 0.20)};
            selection-color: {theme.text};
            outline: 0;
        }}
        """
    )
    return combo


def _styled_radio(theme: Theme, label: str) -> QRadioButton:
    btn = QRadioButton(label)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        f"""
        QRadioButton {{
            color: {theme.text};
            font-size: 12px;
            spacing: 8px;
            padding: 4px 0;
        }}
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {theme.border};
            border-radius: 8px;
            background-color: {theme.surface_2};
        }}
        QRadioButton::indicator:checked {{
            background-color: {theme.primary};
            border: 4px solid {theme.surface_2};
            outline: 1px solid {theme.primary};
        }}
        """
    )
    return btn


def _styled_spin(theme: Theme, *, value: int, lo: int, hi: int) -> QSpinBox:
    spin = QSpinBox()
    spin.setRange(lo, hi)
    spin.setValue(value)
    spin.setSingleStep(1)
    spin.setFixedHeight(36)
    spin.setMinimumWidth(120)
    spin.setStyleSheet(
        f"""
        QSpinBox {{
            background-color: {theme.surface_2};
            color: {theme.text};
            border: 1px solid transparent;
            border-radius: 10px;
            padding: 6px 8px;
            font-size: 13px;
        }}
        QSpinBox:focus {{
            border: 1px solid {rgba(theme.primary, 0.45)};
        }}
        QSpinBox::up-button, QSpinBox::down-button {{
            background: transparent;
            border: none;
            width: 18px;
        }}
        """
    )
    return spin


def _step_location(theme: Theme, txt: dict, on_state_change: Callable[[], None]) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    label = BodyLabel(txt["location_preset_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold)
    body_layout.addWidget(label)

    combo = _styled_combo(theme)
    presets = jobs_data.location_presets("en")  # query strings stay english
    localised_labels = {p["id"]: p["label"] for p in jobs_data.location_presets(_lang_for(txt))}
    initial_index = 0
    for idx, preset in enumerate(presets):
        combo.addItem(localised_labels.get(preset["id"], preset["label"]), userData=preset["id"])
        if preset["id"] == STATE.location_preset:
            initial_index = idx
    combo.setCurrentIndex(initial_index)
    body_layout.addWidget(combo)

    custom_holder = QWidget()
    custom_holder.setStyleSheet("background: transparent;")
    custom_layout = vbox(spacing=4, margins=(0, 4, 0, 0))
    custom_holder.setLayout(custom_layout)
    custom_layout.addWidget(
        BodyLabel(txt["location_custom_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold)
    )
    custom_field = themed_line_edit(theme, placeholder=txt["location_custom_hint"])
    custom_field.setText(STATE.location_custom)
    def _on_custom(value: str) -> None:
        STATE.location_custom = value
        on_state_change()
    custom_field.textChanged.connect(_on_custom)
    custom_layout.addWidget(custom_field)
    custom_holder.setVisible(STATE.location_preset == "custom")
    body_layout.addWidget(custom_holder)

    def _on_preset_change(index: int) -> None:
        new_id = combo.itemData(index) or "any"
        STATE.location_preset = new_id
        custom_holder.setVisible(new_id == "custom")
        on_state_change()

    combo.currentIndexChanged.connect(_on_preset_change)

    return _step_card(
        theme,
        label=txt["step_3_label"],
        title=txt["step_3_title"],
        desc=txt["step_3_desc"],
        body=body,
    )


def _step_filters(theme: Theme, txt: dict, on_state_change: Callable[[], None]) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    body_layout.addWidget(
        BodyLabel(txt["work_mode_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold)
    )

    radios_holder = QFrame()
    radios_holder.setStyleSheet("background: transparent;")
    radios_layout = hbox(spacing=18, margins=(0, 0, 0, 0))
    radios_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
    radios_holder.setLayout(radios_layout)

    group = QButtonGroup(body)
    group.setExclusive(True)
    for entry in jobs_data.work_modes(_lang_for(txt)):
        radio = _styled_radio(theme, entry["label"])
        radio.setChecked(entry["id"] == STATE.work_mode)
        # bind directly to STATE.work_mode by id captured in closure
        def _on_toggled(checked: bool, mode_id: str = entry["id"]) -> None:
            if checked:
                STATE.work_mode = mode_id
                on_state_change()
        radio.toggled.connect(_on_toggled)
        group.addButton(radio)
        radios_layout.addWidget(radio)
    radios_layout.addStretch(1)
    body_layout.addWidget(radios_holder)

    body_layout.addSpacing(8)
    body_layout.addWidget(
        BodyLabel(txt["max_results_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold)
    )
    body_layout.addWidget(SubtleLabel(txt["max_results_hint"], theme=theme, size=11, italic=True))
    spin = _styled_spin(theme, value=STATE.max_results, lo=MAX_RESULTS_MIN, hi=MAX_RESULTS_MAX)
    def _on_count(value: int) -> None:
        STATE.max_results = int(value)
        on_state_change()
    spin.valueChanged.connect(_on_count)
    body_layout.addWidget(spin)

    return _step_card(
        theme,
        label=txt["step_4_label"],
        title=txt["step_4_title"],
        desc=txt["step_4_desc"],
        body=body,
    )


def _lang_for(txt: dict) -> str:
    """Reverse-lookup the language code from a strings dict.

    The string dict is the only thing we receive in step builders; we
    use it to keep the location presets / work modes localised without
    threading ``lang`` through every call.
    """
    nav = txt.get("nav_label", "")
    return "cs" if "Hled" in nav else "en"


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

    hero = QFrame()
    hero.setStyleSheet("background: transparent;")
    hero_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    hero.setLayout(hero_layout)
    hero_layout.addWidget(TitleLabel(txt["setup_hero_title"], theme=theme, size=18, weight=QFont.Weight.Bold))
    hero_layout.addWidget(MutedLabel(txt["setup_hero_desc"], theme=theme, size=12))
    body_layout.addWidget(hero)

    state_change_holder = {"fn": lambda: None}
    def _on_state_change() -> None:
        fn = state_change_holder["fn"]
        try:
            fn()
        except Exception as exc:
            logger_service.log_exception(
                "ai_jobs.tab_setup", "footer_refresh_failed", exc,
            )

    body_layout.addWidget(_step_keywords(theme, txt, _on_state_change))
    body_layout.addWidget(_step_profile(theme, txt, _on_state_change))
    body_layout.addWidget(_step_location(theme, txt, _on_state_change))
    body_layout.addWidget(_step_filters(theme, txt, _on_state_change))
    body_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(body_holder)
    layout.addWidget(scroll, 1)

    footer = QFrame()
    footer.setObjectName("JobsSetupFooter")
    footer.setStyleSheet(
        f"""
        QFrame#JobsSetupFooter {{
            background-color: {theme.bg};
            border-top: 1px solid {theme.border};
        }}
        """
    )
    footer_layout = vbox(spacing=8, margins=(24, 12, 24, 12))
    footer.setLayout(footer_layout)

    button_row = QFrame()
    button_row.setStyleSheet("background: transparent;")
    button_row_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    button_row_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    button_row.setLayout(button_row_layout)
    button_row_layout.addStretch(1)
    run_btn = PrimaryButton(txt["run_btn"], theme=theme, icon=Icons.MANAGE_SEARCH)
    button_row_layout.addWidget(run_btn)
    footer_layout.addWidget(button_row)

    status_label = SubtleLabel("", theme=theme, size=11)
    footer_layout.addWidget(status_label)
    layout.addWidget(footer)

    def _set_status(message: str, *, error: bool = False) -> None:
        try:
            status_label.setText(message)
            status_label.setStyleSheet(
                f"color: {'#EF4444' if error else theme.text_subtle}; background: transparent;"
            )
        except RuntimeError:
            logger_service.log_event(
                "INFO", "ai_jobs.tab_setup", "status_label_stale",
            )

    def _label_for(activity: str) -> str:
        if activity == "searching":
            return txt["run_running"]
        if activity == "extracting":
            return txt["run_extracting"]
        if activity == "verifying":
            return txt["run_verifying"]
        return txt["run_btn"]

    def _refresh_run_button() -> None:
        running = STATE.activity in {"searching", "extracting", "verifying"}
        enabled = STATE.can_run() and not running
        try:
            run_btn.setText(_label_for(STATE.activity))
            run_btn.setEnabled(enabled)
        except RuntimeError:
            logger_service.log_event(
                "INFO", "ai_jobs.tab_setup", "run_btn_stale",
                activity=STATE.activity,
            )

    state_change_holder["fn"] = _refresh_run_button
    _refresh_run_button()

    def _go_to_results() -> None:
        STATE.active_tab = TAB_RESULTS
        REFS.dispatch(_request_full_refresh)

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

        _set_status("")
        STATE.activity = "searching"
        REFS.request_context_refresh()
        _refresh_run_button()

        def _worker() -> None:
            try:
                result = pipeline.run_search(output_lang=lang)
            except Exception as exc:
                logger_service.log_exception(
                    "ai_jobs.tab_setup", "run_search_worker_failed", exc,
                )
                STATE.activity = "error"
                STATE.last_error = str(exc)
                REFS.request_context_refresh()
                runtime_dispatch(lambda: _set_status(txt["search_failed_template"].format(error=exc), error=True))
                runtime_dispatch(_refresh_run_button)
                return

            if not result.ok:
                runtime_dispatch(lambda: _set_status(txt["search_failed_template"].format(error=result.error), error=True))
                runtime_dispatch(_refresh_run_button)
                return

            count = len(STATE.results)
            dropped = STATE.last_dropped
            if count == 0:
                runtime_dispatch(lambda: _set_status(txt["search_zero_results"], error=False))
                runtime_dispatch(_refresh_run_button)
                runtime_dispatch(_request_full_refresh)
                return

            if dropped > 0:
                msg = txt["search_done_template"].format(count=count, dropped=dropped)
            else:
                msg = txt["search_done_no_drops_template"].format(count=count)
            runtime_dispatch(lambda: _set_status(msg, error=False))
            runtime_dispatch(_refresh_run_button)
            runtime_dispatch(_go_to_results)

        threading.Thread(target=_worker, daemon=True).start()

    run_btn.clicked.connect(_on_run)
    return container
