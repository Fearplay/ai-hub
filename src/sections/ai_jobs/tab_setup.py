"""Setup tab - the user describes the role + location + everything else, then runs.

Twelve step cards stacked in a scroll area:

1. Keywords (free text).
2. Profile - any combination of free-text bio, uploaded CV / LinkedIn
   export, or public LinkedIn URL. All optional.
3. Location - dropdown with presets + free-text override on "Custom".
4. Technologies + seniority.
5. Exclusions (keywords / companies / locations / work-type chips).
6. Sources picker - grouped chip grid + custom URL textarea.
7. Job age + verification toggles.
8. Filters (work-mode radios + contract chips + max results spin).
9. Search mode (segmented buttons).
10. Salary + output language.
11. Pre-run summary + the Run button + extra actions (save as
    template / clear / load last).
12. Saved profiles list with per-profile actions.

A sticky footer hosts the section-wide status label. The Run button
lives inside Step 11 (no duplicate footer button) and stays disabled
until at least one input is provided (see :meth:`JobsState.can_run`).
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFrame,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.components.followup_dialog import open_followup_dialog
from src.qt.dialog import BaseDialog, show_dialog
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
    ScrollSafeComboBox,
    ScrollSafeSpinBox,
    SecondaryButton,
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
from src.sections.ai_jobs import pipeline, profiles_store
from src.sections.ai_jobs.refs import REFS
from src.sections.ai_jobs.state import (
    MAX_RESULTS_MAX,
    MAX_RESULTS_MIN,
    STATE,
    TAB_RESULTS,
    TAB_SKILL_GAP,
    UploadedFile,
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


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------


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


def _styled_combo(theme: Theme) -> ScrollSafeComboBox:
    combo = ScrollSafeComboBox()
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


def _styled_checkbox(theme: Theme, label: str) -> QCheckBox:
    chk = QCheckBox(label)
    chk.setCursor(Qt.CursorShape.PointingHandCursor)
    chk.setStyleSheet(
        f"""
        QCheckBox {{
            color: {theme.text};
            font-size: 12px;
            spacing: 8px;
            padding: 4px 0;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {theme.border};
            border-radius: 4px;
            background-color: {theme.surface_2};
        }}
        QCheckBox::indicator:checked {{
            background-color: {theme.primary};
            border: 1px solid {theme.primary};
        }}
        """
    )
    return chk


def _styled_spin(theme: Theme, *, value: int, lo: int, hi: int, step: int = 1) -> ScrollSafeSpinBox:
    spin = ScrollSafeSpinBox()
    spin.setRange(lo, hi)
    spin.setValue(value)
    spin.setSingleStep(step)
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


def _pill_button(theme: Theme, label: str, *, selected: bool) -> QWidget:
    """A small togglable pill used for multi-select chip grids.

    The label inside is forced to single-line: chips are by design
    compact UI elements, and letting them word-wrap caused the
    "Posledních 24 hodin" / "Poslední 14 dní" labels to wrap to a
    second line whose height the chip frame did not absorb, clipping
    the bottom half of the text. The parent ``_segmented_buttons`` /
    ``_multiselect_pills`` use a ``FlowLayout`` so the row itself
    wraps to a second line when the available width is too small -
    no chip ever has to compress its text.
    """
    btn = QFrame()
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setProperty("selected", selected)
    btn.setObjectName("JobsPill")
    fill = rgba(theme.primary, 0.18) if selected else theme.surface_2
    text = theme.primary if selected else theme.text
    border = rgba(theme.primary, 0.45) if selected else theme.border
    btn.setStyleSheet(
        f"""
        QFrame#JobsPill {{
            background-color: {fill};
            color: {text};
            border: 1px solid {border};
            border-radius: 16px;
        }}
        """
    )
    layout = hbox(spacing=0, margins=(12, 6, 12, 6))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    btn.setLayout(layout)
    chip_label = custom_label(label, color=text, size=12, weight=QFont.Weight.DemiBold)
    # Chips are single-line by design - see the docstring above for
    # why we override the helper's default wrap=True here.
    chip_label.setWordWrap(False)
    layout.addWidget(chip_label)
    btn.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
    return btn


def _segmented_buttons(
    theme: Theme,
    *,
    options: list[dict],
    selected_id: str,
    on_change: Callable[[str], None],
) -> QFrame:
    """A row of pill buttons where exactly one is selected at a time.

    Uses a :class:`FlowLayout` so chips wrap to a second row when the
    parent step card is narrower than the natural sum of all chip
    widths. With a plain ``QHBoxLayout`` the chips were getting
    horizontally compressed, which forced the inner labels to word-wrap
    and clipped lines like "Posledních 24 hodin" / "Poslední 14 dní".
    """
    from src.qt.widgets import FlowLayout

    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    flow = FlowLayout(holder, margin=0, h_spacing=8, v_spacing=8)
    holder.setLayout(flow)

    for opt in options:
        opt_id = opt["id"]
        pill = _pill_button(theme, opt["label"], selected=(opt_id == selected_id))

        def _make_handler(captured_id: str = opt_id) -> Callable[[Any], None]:
            def _on_click(_evt: Any) -> None:
                try:
                    on_change(captured_id)
                except Exception as exc:
                    logger_service.log_exception(
                        "ai_jobs.tab_setup", "segmented_handler_failed", exc,
                        option_id=captured_id,
                    )
            return _on_click

        pill.mousePressEvent = _make_handler()  # type: ignore[assignment]
        flow.addWidget(pill)

    return holder


def _multiselect_pills(
    theme: Theme,
    *,
    options: list[dict],
    selected: set[str],
    on_change: Callable[[set[str]], None],
) -> QFrame:
    """A chip-toggle grid that flips ids in / out of ``selected``."""
    from src.qt.widgets import FlowLayout

    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    flow = FlowLayout(holder, margin=0, h_spacing=8, v_spacing=8)
    holder.setLayout(flow)

    for opt in options:
        opt_id = opt["id"]
        is_selected = opt_id in selected
        pill = _pill_button(theme, opt["label"], selected=is_selected)

        def _make_handler(captured_id: str = opt_id) -> Callable[[Any], None]:
            def _on_click(_evt: Any) -> None:
                new_selected = set(selected)
                if captured_id in new_selected:
                    new_selected.remove(captured_id)
                else:
                    new_selected.add(captured_id)
                try:
                    on_change(new_selected)
                except Exception as exc:
                    logger_service.log_exception(
                        "ai_jobs.tab_setup", "multiselect_handler_failed", exc,
                        option_id=captured_id,
                    )
            return _on_click

        pill.mousePressEvent = _make_handler()  # type: ignore[assignment]
        flow.addWidget(pill)

    return holder


# ---------------------------------------------------------------------------
# Profile file chip
# ---------------------------------------------------------------------------


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


def _lang_for(txt: dict) -> str:
    nav = txt.get("nav_label", "")
    return "cs" if "Hled" in nav else "en"


# ---------------------------------------------------------------------------
# Step 1 - keywords
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Step 2 - profile
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Step 3 - location
# ---------------------------------------------------------------------------


def _step_location(theme: Theme, txt: dict, on_state_change: Callable[[], None]) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    label = BodyLabel(txt["location_preset_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold)
    body_layout.addWidget(label)

    combo = _styled_combo(theme)
    lang = _lang_for(txt)
    localised = jobs_data.location_presets(lang)
    initial_index = 0
    for idx, preset in enumerate(localised):
        combo.addItem(preset["label"], userData=preset["id"])
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


# ---------------------------------------------------------------------------
# Step 4 - technologies + seniority
# ---------------------------------------------------------------------------


def _step_skills(theme: Theme, txt: dict, on_state_change: Callable[[], None]) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    body_layout.addWidget(
        BodyLabel(txt["tech_skills_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold)
    )
    tech_area = themed_text_edit(theme, placeholder=txt["tech_skills_hint"], min_height=70)
    tech_area.setPlainText(STATE.tech_skills)
    def _on_tech() -> None:
        STATE.tech_skills = tech_area.toPlainText()
        on_state_change()
    tech_area.textChanged.connect(_on_tech)
    body_layout.addWidget(tech_area)

    body_layout.addSpacing(6)
    body_layout.addWidget(
        BodyLabel(txt["additional_experience_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold)
    )
    extra_area = themed_text_edit(theme, placeholder=txt["additional_experience_hint"], min_height=60)
    extra_area.setPlainText(STATE.additional_experience)
    def _on_extra() -> None:
        STATE.additional_experience = extra_area.toPlainText()
        on_state_change()
    extra_area.textChanged.connect(_on_extra)
    body_layout.addWidget(extra_area)

    body_layout.addSpacing(6)
    body_layout.addWidget(
        BodyLabel(txt["seniority_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold)
    )

    def _on_seniority(level_id: str) -> None:
        STATE.seniority = level_id
        on_state_change()
        runtime_dispatch(_request_full_refresh)

    body_layout.addWidget(
        _segmented_buttons(
            theme,
            options=jobs_data.seniority_levels(_lang_for(txt)),
            selected_id=STATE.seniority,
            on_change=_on_seniority,
        )
    )

    body_layout.addWidget(SubtleLabel(txt["skills_helper_note"], theme=theme, size=11, italic=True))

    return _step_card(
        theme,
        label=txt["step_4_label"],
        title=txt["step_4_title"],
        desc=txt["step_4_desc"],
        body=body,
    )


# ---------------------------------------------------------------------------
# Step 5 - exclusions
# ---------------------------------------------------------------------------


def _step_exclusions(theme: Theme, txt: dict, on_state_change: Callable[[], None]) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    def _text_field(label_key: str, hint_key: str, attr: str) -> None:
        body_layout.addWidget(
            BodyLabel(txt[label_key], theme=theme, size=12, weight=QFont.Weight.DemiBold)
        )
        area = themed_text_edit(theme, placeholder=txt[hint_key], min_height=60)
        area.setPlainText(getattr(STATE, attr))
        def _on_change() -> None:
            setattr(STATE, attr, area.toPlainText())
            on_state_change()
        area.textChanged.connect(_on_change)
        body_layout.addWidget(area)
        body_layout.addSpacing(4)

    _text_field("excluded_keywords_label", "excluded_keywords_hint", "excluded_keywords")
    _text_field("excluded_companies_label", "excluded_companies_hint", "excluded_companies")
    _text_field("excluded_locations_label", "excluded_locations_hint", "excluded_locations")

    body_layout.addWidget(
        BodyLabel(txt["excluded_work_types_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold)
    )

    def _on_excl_change(new_selected: set[str]) -> None:
        STATE.excluded_work_types = new_selected
        on_state_change()
        runtime_dispatch(_request_full_refresh)

    body_layout.addWidget(
        _multiselect_pills(
            theme,
            options=jobs_data.excluded_work_type_presets(_lang_for(txt)),
            selected=set(STATE.excluded_work_types),
            on_change=_on_excl_change,
        )
    )
    body_layout.addWidget(SubtleLabel(txt["exclusions_helper_note"], theme=theme, size=11, italic=True))

    return _step_card(
        theme,
        label=txt["step_5_label"],
        title=txt["step_5_title"],
        desc=txt["step_5_desc"],
        body=body,
    )


# ---------------------------------------------------------------------------
# Step 6 - sources picker
# ---------------------------------------------------------------------------


def _step_sources(theme: Theme, txt: dict, on_state_change: Callable[[], None]) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=14, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    def _on_sources_change(new_selected: set[str]) -> None:
        STATE.selected_sources = new_selected
        on_state_change()
        runtime_dispatch(_request_full_refresh)

    for group in jobs_data.source_categories(_lang_for(txt)):
        if not group["items"]:
            continue
        body_layout.addWidget(
            BodyLabel(group["label"], theme=theme, size=12, weight=QFont.Weight.DemiBold)
        )
        body_layout.addWidget(
            _multiselect_pills(
                theme,
                options=group["items"],
                selected=set(STATE.selected_sources),
                on_change=_on_sources_change,
            )
        )

    body_layout.addSpacing(6)
    body_layout.addWidget(
        BodyLabel(txt["sources_custom_urls_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold)
    )
    urls_area = themed_text_edit(theme, placeholder=txt["sources_custom_urls_hint"], min_height=70)
    urls_area.setPlainText(STATE.custom_source_urls)
    def _on_urls() -> None:
        STATE.custom_source_urls = urls_area.toPlainText()
        on_state_change()
    urls_area.textChanged.connect(_on_urls)
    body_layout.addWidget(urls_area)
    body_layout.addWidget(SubtleLabel(txt["sources_helper_note"], theme=theme, size=11, italic=True))

    return _step_card(
        theme,
        label=txt["step_6_label"],
        title=txt["step_6_title"],
        desc=txt["step_6_desc"],
        body=body,
    )


# ---------------------------------------------------------------------------
# Step 7 - job age + verification
# ---------------------------------------------------------------------------


def _step_age(theme: Theme, txt: dict, on_state_change: Callable[[], None]) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    body_layout.addWidget(
        BodyLabel(txt["age_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold)
    )

    def _on_age(age_id: str) -> None:
        STATE.job_age = age_id
        on_state_change()
        runtime_dispatch(_request_full_refresh)

    body_layout.addWidget(
        _segmented_buttons(
            theme,
            options=jobs_data.job_age_presets(_lang_for(txt)),
            selected_id=STATE.job_age,
            on_change=_on_age,
        )
    )

    body_layout.addSpacing(6)
    verify_chk = _styled_checkbox(theme, txt["verify_links_label"])
    verify_chk.setChecked(STATE.verify_active_links)
    def _on_verify(state: int) -> None:
        STATE.verify_active_links = bool(state)
        on_state_change()
    verify_chk.stateChanged.connect(_on_verify)
    body_layout.addWidget(verify_chk)

    show_chk = _styled_checkbox(theme, txt["show_without_date_label"])
    show_chk.setChecked(STATE.show_without_date)
    def _on_show(state: int) -> None:
        STATE.show_without_date = bool(state)
        on_state_change()
    show_chk.stateChanged.connect(_on_show)
    body_layout.addWidget(show_chk)

    body_layout.addWidget(SubtleLabel(txt["age_helper_note"], theme=theme, size=11, italic=True))

    return _step_card(
        theme,
        label=txt["step_7_label"],
        title=txt["step_7_title"],
        desc=txt["step_7_desc"],
        body=body,
    )


# ---------------------------------------------------------------------------
# Step 8 - filters (work mode + contract + count)
# ---------------------------------------------------------------------------


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
        def _on_toggled(checked: bool, mode_id: str = entry["id"]) -> None:
            if checked:
                STATE.work_mode = mode_id
                on_state_change()
        radio.toggled.connect(_on_toggled)
        group.addButton(radio)
        radios_layout.addWidget(radio)
    radios_layout.addStretch(1)
    body_layout.addWidget(radios_holder)

    body_layout.addSpacing(6)
    body_layout.addWidget(
        BodyLabel(txt["contract_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold)
    )

    def _on_contract_change(new_selected: set[str]) -> None:
        STATE.contract_types = new_selected
        on_state_change()
        runtime_dispatch(_request_full_refresh)

    body_layout.addWidget(
        _multiselect_pills(
            theme,
            options=jobs_data.contract_types(_lang_for(txt)),
            selected=set(STATE.contract_types),
            on_change=_on_contract_change,
        )
    )

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
        label=txt["step_8_label"],
        title=txt["step_8_title"],
        desc=txt["step_8_desc"],
        body=body,
    )


# ---------------------------------------------------------------------------
# Step 9 - search mode
# ---------------------------------------------------------------------------


def _step_mode(theme: Theme, txt: dict, on_state_change: Callable[[], None]) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    modes = jobs_data.search_modes(_lang_for(txt))

    def _on_mode(mode_id: str) -> None:
        STATE.search_mode = mode_id
        on_state_change()
        runtime_dispatch(_request_full_refresh)

    body_layout.addWidget(
        _segmented_buttons(
            theme,
            options=modes,
            selected_id=STATE.search_mode,
            on_change=_on_mode,
        )
    )

    desc = next((m for m in modes if m["id"] == STATE.search_mode), modes[0])
    body_layout.addWidget(MutedLabel(desc.get("desc", ""), theme=theme, size=12))

    return _step_card(
        theme,
        label=txt["step_9_label"],
        title=txt["step_9_title"],
        desc=txt["step_9_desc"],
        body=body,
    )


# ---------------------------------------------------------------------------
# Step 10 - salary + output language
# ---------------------------------------------------------------------------


def _step_salary_lang(theme: Theme, txt: dict, on_state_change: Callable[[], None]) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    body_layout.addWidget(
        BodyLabel(txt["salary_min_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold)
    )

    salary_row = QFrame()
    salary_row.setStyleSheet("background: transparent;")
    salary_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    salary_row.setLayout(salary_layout)

    spin = _styled_spin(theme, value=int(STATE.salary_min or 0), lo=0, hi=2_000_000, step=5000)
    def _on_salary(value: int) -> None:
        STATE.salary_min = int(value)
        on_state_change()
    spin.valueChanged.connect(_on_salary)
    salary_layout.addWidget(spin)

    currency_combo = _styled_combo(theme)
    currencies = jobs_data.salary_currencies(_lang_for(txt))
    selected_idx = 0
    for idx, c in enumerate(currencies):
        currency_combo.addItem(c["label"], userData=c["id"])
        if c["id"] == STATE.salary_currency:
            selected_idx = idx
    currency_combo.setCurrentIndex(selected_idx)
    def _on_currency(index: int) -> None:
        STATE.salary_currency = currency_combo.itemData(index) or "any"
        on_state_change()
    currency_combo.currentIndexChanged.connect(_on_currency)
    salary_layout.addWidget(currency_combo)
    salary_layout.addStretch(1)
    body_layout.addWidget(salary_row)
    body_layout.addWidget(SubtleLabel(txt["salary_helper_note"], theme=theme, size=11, italic=True))

    body_layout.addSpacing(6)
    body_layout.addWidget(
        BodyLabel(txt["output_lang_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold)
    )

    def _on_lang(lang_id: str) -> None:
        STATE.output_language = lang_id
        on_state_change()
        runtime_dispatch(_request_full_refresh)

    body_layout.addWidget(
        _segmented_buttons(
            theme,
            options=jobs_data.output_languages(_lang_for(txt)),
            selected_id=STATE.output_language,
            on_change=_on_lang,
        )
    )

    return _step_card(
        theme,
        label=txt["step_10_label"],
        title=txt["step_10_title"],
        desc=txt["step_10_desc"],
        body=body,
    )


# ---------------------------------------------------------------------------
# Step 11 - summary + run
# ---------------------------------------------------------------------------


def _summary_value_for(*, label_key: str, value: str, txt: dict) -> str:
    if value:
        return value
    return txt["summary_value_any"]


def _format_seniority(level: str, txt: dict) -> str:
    if not level or level == "any":
        return ""
    return txt.get(f"seniority_{level}", level.title())


def _format_search_mode(mode: str, txt: dict) -> str:
    if not mode:
        return txt["mode_smart"]
    return txt.get(f"mode_{mode}", mode.title())


def _format_work_mode(mode: str, txt: dict) -> str:
    if mode in {"remote", "hybrid", "onsite"}:
        return txt.get(f"mode_{mode}", mode.title())
    return ""


def _format_age(age: str, txt: dict) -> str:
    if not age or age == "any":
        return ""
    return txt.get(f"age_{age}", age)


def _format_output_lang(value: str, txt: dict) -> str:
    return txt.get(f"output_lang_{value}", txt["output_lang_auto"])


def _format_sources(selected: set[str], txt: dict) -> str:
    if not selected:
        return txt["summary_sources_recommended"]
    return txt["summary_sources_count_template"].format(count=len(selected))


def _format_contracts(selected: set[str], txt: dict) -> str:
    if not selected:
        return ""
    labels = [txt.get(f"contract_{c}", c.upper()) for c in selected]
    return ", ".join(labels)


def _format_salary(amount: int, currency: str, txt: dict) -> str:
    if not amount or currency == "any":
        return ""
    return txt["summary_salary_value_template"].format(amount=amount, currency=currency)


def _format_location(txt: dict) -> str:
    if STATE.location_preset == "custom":
        return STATE.location_custom or txt["summary_value_unset"]
    for preset in jobs_data.location_presets(_lang_for(txt)):
        if preset["id"] == STATE.location_preset:
            return preset["label"]
    return txt["summary_value_any"]


def _summary_row(theme: Theme, label: str, value: str) -> QFrame:
    row = QFrame()
    row.setStyleSheet("background: transparent;")
    layout = hbox(spacing=12, margins=(0, 0, 0, 0))
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    row.setLayout(layout)
    name_label = SubtleLabel(label, theme=theme, size=12, weight=QFont.Weight.DemiBold)
    name_label.setMinimumWidth(160)
    layout.addWidget(name_label)
    value_label = BodyLabel(value, theme=theme, size=12)
    value_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    layout.addWidget(value_label, 1)
    return row


def _step_summary_run(
    theme: Theme,
    txt: dict,
    on_state_change: Callable[[], None],
    *,
    on_run: Callable[[], None],
    on_save_template: Callable[[], None],
    on_clear: Callable[[], None],
    on_load_last: Callable[[], None],
    run_button: PrimaryButton,
) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=12, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    summary_holder = QFrame()
    summary_holder.setObjectName("JobsSummaryHolder")
    summary_holder.setStyleSheet(
        f"""
        QFrame#JobsSummaryHolder {{
            background-color: {theme.surface_2};
            border-radius: 12px;
        }}
        """
    )
    summary_layout = vbox(spacing=6, margins=(14, 12, 14, 12))
    summary_holder.setLayout(summary_layout)

    rows: list[tuple[str, str]] = [
        (txt["summary_role_label"], STATE.keywords.strip() or txt["summary_value_unset"]),
        (txt["summary_location_label"], _format_location(txt)),
        (txt["summary_seniority_label"], _format_seniority(STATE.seniority, txt) or txt["summary_value_any"]),
        (txt["summary_work_mode_label"], _format_work_mode(STATE.work_mode, txt) or txt["summary_value_any"]),
        (txt["summary_contract_label"], _format_contracts(STATE.contract_types, txt) or txt["summary_value_any"]),
        (txt["summary_age_label"], _format_age(STATE.job_age, txt) or txt["summary_value_any"]),
        (txt["summary_sources_label"], _format_sources(STATE.selected_sources, txt)),
        (txt["summary_results_label"], str(STATE.max_results)),
        (txt["summary_mode_label"], _format_search_mode(STATE.search_mode, txt)),
        (txt["summary_salary_label"], _format_salary(STATE.salary_min, STATE.salary_currency, txt) or txt["summary_value_any"]),
        (txt["summary_output_lang_label"], _format_output_lang(STATE.output_language, txt)),
    ]
    for label, value in rows:
        summary_layout.addWidget(_summary_row(theme, label, value))

    body_layout.addWidget(summary_holder)

    # Main run button.
    run_row = QFrame()
    run_row.setStyleSheet("background: transparent;")
    run_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    run_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
    run_row.setLayout(run_layout)
    run_button.clicked.connect(on_run)
    run_layout.addWidget(run_button)
    run_layout.addStretch(1)
    body_layout.addWidget(run_row)

    # Secondary actions.
    more_row = QFrame()
    more_row.setStyleSheet("background: transparent;")
    more_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    more_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
    more_row.setLayout(more_layout)

    save_btn = SecondaryButton(txt["run_more_btn_save_template"], theme=theme, icon=Icons.SAVE_OUTLINED)
    save_btn.clicked.connect(on_save_template)
    more_layout.addWidget(save_btn)

    clear_btn = GhostButton(txt["run_more_btn_clear"], theme=theme, icon=Icons.CLOSE)
    clear_btn.clicked.connect(on_clear)
    more_layout.addWidget(clear_btn)

    load_btn = GhostButton(txt["run_more_btn_load_last"], theme=theme, icon=Icons.HISTORY)
    load_btn.clicked.connect(on_load_last)
    more_layout.addWidget(load_btn)
    more_layout.addStretch(1)
    body_layout.addWidget(more_row)

    return _step_card(
        theme,
        label=txt["step_11_label"],
        title=txt["step_11_title"],
        desc=txt["step_11_desc"],
        body=body,
    )


# ---------------------------------------------------------------------------
# Step 12 - saved profiles
# ---------------------------------------------------------------------------


def _profile_card(
    theme: Theme,
    txt: dict,
    profile: dict[str, Any],
    *,
    on_run: Callable[[dict[str, Any]], None],
    on_edit: Callable[[dict[str, Any]], None],
    on_duplicate: Callable[[dict[str, Any]], None],
    on_delete: Callable[[dict[str, Any]], None],
) -> QFrame:
    card = QFrame()
    card.setObjectName("JobsProfileCard")
    card.setStyleSheet(
        f"""
        QFrame#JobsProfileCard {{
            background-color: {theme.surface_2};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        """
    )
    layout = vbox(spacing=8, margins=(14, 12, 14, 12))
    card.setLayout(layout)

    header_row = QFrame()
    header_row.setStyleSheet("background: transparent;")
    header_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    header_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    header_row.setLayout(header_layout)

    name_holder = QFrame()
    name_holder.setStyleSheet("background: transparent;")
    name_holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    name_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    name_holder.setLayout(name_layout)
    name_layout.addWidget(TitleLabel(profile.get("name", "?"), theme=theme, size=14, weight=QFont.Weight.Bold))

    snapshot = profile.get("snapshot") or {}
    detail_lines: list[str] = []
    if snapshot.get("keywords"):
        detail_lines.append(snapshot["keywords"])
    last_run = profile.get("last_run")
    if last_run:
        detail_lines.append(txt["profile_last_run_template"].format(when=last_run.replace("T", " ")))
    else:
        detail_lines.append(txt["profile_never_run"])
    for line in detail_lines:
        name_layout.addWidget(SubtleLabel(line, theme=theme, size=11, italic=True))

    header_layout.addWidget(name_holder, 1)
    layout.addWidget(header_row)

    actions_row = QFrame()
    actions_row.setStyleSheet("background: transparent;")
    actions_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    actions_row.setLayout(actions_layout)

    run_btn = PrimaryButton(txt["profile_run_again"], theme=theme, icon=Icons.MANAGE_SEARCH)
    run_btn.clicked.connect(lambda: on_run(profile))
    actions_layout.addWidget(run_btn)

    edit_btn = GhostButton(txt["profile_edit"], theme=theme, icon=Icons.TUNE)
    edit_btn.clicked.connect(lambda: on_edit(profile))
    actions_layout.addWidget(edit_btn)

    dup_btn = GhostButton(txt["profile_duplicate"], theme=theme, icon=Icons.CONTENT_COPY)
    dup_btn.clicked.connect(lambda: on_duplicate(profile))
    actions_layout.addWidget(dup_btn)

    del_btn = GhostButton(txt["profile_delete"], theme=theme, icon=Icons.CLOSE)
    del_btn.clicked.connect(lambda: on_delete(profile))
    actions_layout.addWidget(del_btn)

    actions_layout.addStretch(1)
    layout.addWidget(actions_row)
    return card


def _step_saved_profiles(
    theme: Theme,
    txt: dict,
    *,
    on_run: Callable[[dict[str, Any]], None],
    on_edit: Callable[[dict[str, Any]], None],
    on_duplicate: Callable[[dict[str, Any]], None],
    on_delete: Callable[[dict[str, Any]], None],
) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    profiles = list(STATE.saved_profiles or [])
    if not profiles:
        body_layout.addWidget(MutedLabel(txt["profiles_empty"], theme=theme, size=12))
    else:
        for profile in profiles:
            body_layout.addWidget(_profile_card(
                theme, txt, profile,
                on_run=on_run,
                on_edit=on_edit,
                on_duplicate=on_duplicate,
                on_delete=on_delete,
            ))

    return _step_card(
        theme,
        label=txt["step_12_label"],
        title=txt["step_12_title"],
        desc=txt["step_12_desc"],
        body=body,
    )


# ---------------------------------------------------------------------------
# Profile snapshot helpers
# ---------------------------------------------------------------------------


def _build_snapshot() -> dict[str, Any]:
    """Serialise the user-side STATE fields into a profile snapshot.

    Skips the uploaded CV file (binary blob, kept in memory only) and
    every transient field (results, activity, history). Only the
    inputs the next run will need are captured.
    """
    return {
        "keywords": STATE.keywords,
        "profile_text": STATE.profile_text,
        "linkedin_url": STATE.linkedin_url,
        "location_preset": STATE.location_preset,
        "location_custom": STATE.location_custom,
        "tech_skills": STATE.tech_skills,
        "additional_experience": STATE.additional_experience,
        "seniority": STATE.seniority,
        "excluded_keywords": STATE.excluded_keywords,
        "excluded_companies": STATE.excluded_companies,
        "excluded_locations": STATE.excluded_locations,
        "excluded_work_types": sorted(STATE.excluded_work_types),
        "selected_sources": sorted(STATE.selected_sources),
        "custom_source_urls": STATE.custom_source_urls,
        "job_age": STATE.job_age,
        "verify_active_links": STATE.verify_active_links,
        "show_without_date": STATE.show_without_date,
        "work_mode": STATE.work_mode,
        "contract_types": sorted(STATE.contract_types),
        "max_results": STATE.max_results,
        "search_mode": STATE.search_mode,
        "salary_min": STATE.salary_min,
        "salary_currency": STATE.salary_currency,
        "output_language": STATE.output_language,
    }


def _apply_snapshot(snapshot: dict[str, Any]) -> None:
    """Apply a saved snapshot back onto STATE. Missing keys keep defaults."""
    if not snapshot:
        return
    STATE.keywords = snapshot.get("keywords", "")
    STATE.profile_text = snapshot.get("profile_text", "")
    STATE.linkedin_url = snapshot.get("linkedin_url", "")
    STATE.location_preset = snapshot.get("location_preset", STATE.location_preset)
    STATE.location_custom = snapshot.get("location_custom", "")
    STATE.tech_skills = snapshot.get("tech_skills", "")
    STATE.additional_experience = snapshot.get("additional_experience", "")
    STATE.seniority = snapshot.get("seniority", "any")
    STATE.excluded_keywords = snapshot.get("excluded_keywords", "")
    STATE.excluded_companies = snapshot.get("excluded_companies", "")
    STATE.excluded_locations = snapshot.get("excluded_locations", "")
    STATE.excluded_work_types = set(snapshot.get("excluded_work_types") or [])
    STATE.selected_sources = set(snapshot.get("selected_sources") or [])
    STATE.custom_source_urls = snapshot.get("custom_source_urls", "")
    STATE.job_age = snapshot.get("job_age", "any")
    STATE.verify_active_links = bool(snapshot.get("verify_active_links", True))
    STATE.show_without_date = bool(snapshot.get("show_without_date", True))
    STATE.work_mode = snapshot.get("work_mode", "any")
    STATE.contract_types = set(snapshot.get("contract_types") or [])
    try:
        STATE.max_results = int(snapshot.get("max_results") or STATE.max_results)
    except (TypeError, ValueError):
        pass
    STATE.search_mode = snapshot.get("search_mode", "smart")
    try:
        STATE.salary_min = int(snapshot.get("salary_min") or 0)
    except (TypeError, ValueError):
        STATE.salary_min = 0
    STATE.salary_currency = snapshot.get("salary_currency", "any")
    STATE.output_language = snapshot.get("output_language", "auto")


# ---------------------------------------------------------------------------
# Save-profile dialog
# ---------------------------------------------------------------------------


def _prompt_profile_name(theme: Theme, txt: dict) -> Optional[str]:
    parent = get_main_window()
    dlg = BaseDialog(
        parent=parent,
        theme=theme,
        title=txt["profile_save_dialog_title"],
        width=460,
    )

    body_layout = dlg.body_layout
    body_layout.addWidget(
        BodyLabel(txt["profile_save_dialog_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold)
    )
    name_field = themed_line_edit(theme, placeholder=txt["profile_save_dialog_hint"])
    body_layout.addWidget(name_field)

    dlg.add_action(GhostButton(txt["profile_cancel_btn"], theme=theme), role="cancel")
    save_button = PrimaryButton(txt["profile_save_btn"], theme=theme, icon=Icons.SAVE_OUTLINED)
    dlg.add_action(save_button, role="accept")

    if show_dialog(dlg) != QDialog.DialogCode.Accepted:
        return None
    return name_field.text().strip() or None


# ---------------------------------------------------------------------------
# Build the tab
# ---------------------------------------------------------------------------


def build_setup_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Optional[Callable[[], None]] = None,
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

    # Footer status label lives below the scroll so worker threads can
    # update it without finding the right widget across step cards.
    status_label = SubtleLabel("", theme=theme, size=11)

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

    # Run button - shared between Step 11 (primary CTA) and the footer.
    run_btn = PrimaryButton(txt["run_btn"], theme=theme, icon=Icons.MANAGE_SEARCH)

    state_change_holder: dict[str, Callable[[], None]] = {"fn": lambda: None}
    def _on_state_change() -> None:
        fn = state_change_holder["fn"]
        try:
            fn()
        except Exception as exc:
            logger_service.log_exception(
                "ai_jobs.tab_setup", "footer_refresh_failed", exc,
            )

    # Run + secondary action handlers ---------------------------------
    def _label_for(activity: str) -> str:
        if activity == "searching":
            return txt["run_running"]
        if activity == "followups":
            return txt["run_followups"]
        if activity == "waiting_user":
            return txt["ctx_activity_waiting_user"]
        if activity == "extracting":
            return txt["run_extracting"]
        if activity == "verifying":
            return txt["run_verifying"]
        if activity == "scoring":
            return txt["run_scoring"]
        if activity == "gap_analysis":
            return txt["run_gap"]
        return txt["run_btn"]

    def _refresh_run_button() -> None:
        running = STATE.activity in {
            "searching", "followups", "waiting_user",
            "extracting", "verifying", "scoring", "gap_analysis",
        }
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

    def _resolve_followups(questions: list[dict]) -> Optional[list[dict]]:
        """Worker-thread side of the follow-up dialog.

        Called from inside ``pipeline.run_search`` once the LLM produced
        clarifying questions. We dispatch the actual modal onto the GUI
        thread, block this worker on a ``threading.Event``, and return
        the answers (or ``None`` if the user cancelled).
        """
        done = threading.Event()
        result_holder: dict[str, Optional[list[dict]]] = {"answers": None}

        def _open_now() -> None:
            def _on_submit(answers: list[dict]) -> None:
                result_holder["answers"] = list(answers or [])
                done.set()

            def _on_cancel() -> None:
                result_holder["answers"] = None
                done.set()

            try:
                open_followup_dialog(
                    get_main_window(),
                    theme,
                    title=txt["followup_title"],
                    intro=txt["followup_intro"],
                    cancel_label=txt["followup_cancel"],
                    continue_label=txt["followup_continue_btn"],
                    answer_hint=txt["followup_answer_hint"],
                    skip_all_label=txt["followup_skip_btn"],
                    other_label=txt["followup_other_label"],
                    other_hint=txt["followup_other_hint"],
                    questions=list(questions),
                    on_submit=_on_submit,
                    on_cancel=_on_cancel,
                )
            except Exception as exc:
                logger_service.log_exception(
                    "ai_jobs.tab_setup", "followup_dialog_failed", exc,
                )
                result_holder["answers"] = None
                done.set()

        runtime_dispatch(_open_now)
        done.wait()
        return result_holder["answers"]

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

        pipeline.set_followup_resolver(_resolve_followups)

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
                if result.error == "cancelled_by_user":
                    runtime_dispatch(lambda: _set_status(txt["search_cancelled"], error=False))
                else:
                    runtime_dispatch(lambda: _set_status(txt["search_failed_template"].format(error=result.error), error=True))
                runtime_dispatch(_refresh_run_button)
                return

            count = STATE.active_results_count()
            dropped = STATE.last_dropped
            if count == 0 and not STATE.results:
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

    def _on_save_template() -> None:
        name = _prompt_profile_name(theme, txt)
        if not name:
            return
        try:
            record = profiles_store.save_profile(name=name, snapshot=_build_snapshot())
        except Exception as exc:
            logger_service.log_exception(
                "ai_jobs.tab_setup", "save_profile_failed", exc, name=name,
            )
            _set_status(txt["profile_save_failed_template"].format(error=exc), error=True)
            return
        pipeline.refresh_saved_profiles()
        _set_status(txt["profile_saved_toast_template"].format(name=record["name"]), error=False)
        runtime_dispatch(_request_full_refresh)

    def _on_clear_form() -> None:
        STATE.reset_inputs()
        _set_status(txt["profile_form_cleared"], error=False)
        runtime_dispatch(_request_full_refresh)

    def _on_load_last() -> None:
        profiles = list(STATE.saved_profiles or [])
        if not profiles:
            _set_status(txt["profile_load_last_no_search"], error=True)
            return
        last = profiles[0]
        _apply_snapshot(last.get("snapshot") or {})
        _set_status(txt["profile_loaded_toast_template"].format(name=last.get("name", "?")), error=False)
        runtime_dispatch(_request_full_refresh)

    def _on_profile_run(profile: dict[str, Any]) -> None:
        _apply_snapshot(profile.get("snapshot") or {})
        try:
            profiles_store.stamp_last_run(profile.get("id", ""))
        except Exception as exc:
            logger_service.log_exception(
                "ai_jobs.tab_setup", "stamp_last_run_failed", exc,
                profile_id=profile.get("id"),
            )
        pipeline.refresh_saved_profiles()
        _set_status(txt["profile_loaded_toast_template"].format(name=profile.get("name", "?")), error=False)
        runtime_dispatch(_request_full_refresh)
        # Auto-run after the next tick so the user sees the form filled in.
        runtime_dispatch(_on_run)

    def _on_profile_edit(profile: dict[str, Any]) -> None:
        _apply_snapshot(profile.get("snapshot") or {})
        _set_status(txt["profile_loaded_toast_template"].format(name=profile.get("name", "?")), error=False)
        runtime_dispatch(_request_full_refresh)

    def _on_profile_duplicate(profile: dict[str, Any]) -> None:
        try:
            profiles_store.duplicate_profile(
                profile.get("id", ""),
                suffix=txt["profile_duplicate_suffix"],
            )
        except Exception as exc:
            logger_service.log_exception(
                "ai_jobs.tab_setup", "duplicate_profile_failed", exc,
                profile_id=profile.get("id"),
            )
            _set_status(txt["profile_save_failed_template"].format(error=exc), error=True)
            return
        pipeline.refresh_saved_profiles()
        runtime_dispatch(_request_full_refresh)

    def _on_profile_delete(profile: dict[str, Any]) -> None:
        if not profiles_store.delete_profile(profile.get("id", "")):
            return
        pipeline.refresh_saved_profiles()
        _set_status(txt["profile_deleted_toast_template"].format(name=profile.get("name", "?")), error=False)
        runtime_dispatch(_request_full_refresh)

    # Step cards ------------------------------------------------------
    body_layout.addWidget(_step_keywords(theme, txt, _on_state_change))
    body_layout.addWidget(_step_profile(theme, txt, _on_state_change))
    body_layout.addWidget(_step_location(theme, txt, _on_state_change))
    body_layout.addWidget(_step_skills(theme, txt, _on_state_change))
    body_layout.addWidget(_step_exclusions(theme, txt, _on_state_change))
    body_layout.addWidget(_step_sources(theme, txt, _on_state_change))
    body_layout.addWidget(_step_age(theme, txt, _on_state_change))
    body_layout.addWidget(_step_filters(theme, txt, _on_state_change))
    body_layout.addWidget(_step_mode(theme, txt, _on_state_change))
    body_layout.addWidget(_step_salary_lang(theme, txt, _on_state_change))
    body_layout.addWidget(_step_summary_run(
        theme, txt, _on_state_change,
        on_run=_on_run,
        on_save_template=_on_save_template,
        on_clear=_on_clear_form,
        on_load_last=_on_load_last,
        run_button=run_btn,
    ))
    body_layout.addWidget(_step_saved_profiles(
        theme, txt,
        on_run=_on_profile_run,
        on_edit=_on_profile_edit,
        on_duplicate=_on_profile_duplicate,
        on_delete=_on_profile_delete,
    ))
    body_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(body_holder)
    layout.addWidget(scroll, 1)

    # --- scroll-position memory --------------------------------------
    # Every chip / checkbox click triggers a full section rebuild via
    # ``request_section_refresh``, which materialises a brand-new
    # ``QScrollArea`` whose viewport starts at y=0. Without saving and
    # restoring the previous y the user gets thrown back to the top of
    # the form on every interaction. We hook the scrollbar's
    # ``valueChanged`` to keep ``STATE.setup_scroll_pos`` in sync and
    # then restore the value on the next event-loop tick (after Qt has
    # had a chance to compute the new scroll range).
    _vbar = scroll.verticalScrollBar()

    def _save_scroll_pos(value: int) -> None:
        STATE.setup_scroll_pos = max(0, int(value))

    _vbar.valueChanged.connect(_save_scroll_pos)

    def _restore_scroll_pos() -> None:
        try:
            target = max(0, min(STATE.setup_scroll_pos, _vbar.maximum()))
            _vbar.setValue(target)
        except RuntimeError:
            # Widget already deleted - safe to ignore.
            pass

    if STATE.setup_scroll_pos > 0:
        QTimer.singleShot(0, _restore_scroll_pos)

    # Footer hosts the status label + the "ask clarifying questions" toggle.
    # The Run button itself lives in Step 11 (no duplicate footer button).
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
    footer_layout = vbox(spacing=6, margins=(24, 12, 24, 12))
    footer.setLayout(footer_layout)

    fu_check = QCheckBox(txt["footer_ask_followups_label"])
    fu_check.setChecked(settings_store.get_ask_followups())
    fu_check.setStyleSheet(
        f"""
        QCheckBox {{ color: {theme.text}; font-size: 11px; font-weight: 600; spacing: 8px; }}
        QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {theme.border}; border-radius: 4px; background-color: {theme.surface_2}; }}
        QCheckBox::indicator:checked {{ background-color: {theme.primary}; border: 1px solid {theme.primary}; }}
        """
    )
    fu_check.stateChanged.connect(
        lambda _state: settings_store.set_ask_followups(bool(fu_check.isChecked()))
    )
    footer_layout.addWidget(fu_check)
    footer_layout.addWidget(status_label)
    layout.addWidget(footer)

    # Clear the pipeline-level resolver when this view is destroyed so a
    # rebuilt setup tab does not race against a worker holding a stale
    # closure over deleted widgets.
    def _on_destroyed(_obj=None) -> None:
        try:
            pipeline.set_followup_resolver(None)
        except Exception as exc:
            logger_service.log_exception(
                "ai_jobs.tab_setup", "clear_followup_resolver_failed", exc,
            )

    container.destroyed.connect(_on_destroyed)

    return container
