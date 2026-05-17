"""Skill gap tab - aggregated requirements vs. user's profile.

Renders the Pass 5 output (:data:`STATE.skill_gap`) into a single
scrollable panel: header, top required skills (sorted by demand),
strong sides (skills the user has + the market wants), missing
skills, and a list of AI advice paragraphs.

When ``STATE.skill_gap`` is empty (no search yet, or the user did
not provide any profile material) we show an empty state directing
them to Setup. The tab never spawns AI calls itself - the heavy
lifting happens during the search pipeline, this is pure
presentation.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QScrollArea, QSizePolicy, QWidget

from src.qt.icons import Icons
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    FlowLayout,
    GhostButton,
    IconLabel,
    MutedLabel,
    SubtleLabel,
    TitleLabel,
    custom_label,
    hbox,
    vbox,
)
from src.sections.ai_jobs.refs import REFS
from src.sections.ai_jobs.state import STATE, TAB_SETUP
from src.sections.ai_jobs.strings import s
from src.theme import Theme


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception:
        return
    request_section_refresh()


def _chip(theme: Theme, label: str, *, color: str, fill: str) -> QFrame:
    chip = QFrame()
    chip.setStyleSheet(f"background-color: {fill}; border-radius: 12px;")
    layout = hbox(spacing=0, margins=(10, 4, 10, 4))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    chip.setLayout(layout)
    layout.addWidget(custom_label(label, color=color, size=12, weight=QFont.Weight.DemiBold))
    chip.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
    return chip


def _chip_flow(theme: Theme, *, items: list[str], color: str, fill: str) -> Optional[QWidget]:
    items = [item for item in items if (item or "").strip()]
    if not items:
        return None
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    flow = FlowLayout(holder, margin=0, h_spacing=8, v_spacing=8)
    holder.setLayout(flow)
    for item in items:
        flow.addWidget(_chip(theme, item, color=color, fill=fill))
    return holder


def _section_card(theme: Theme, *, title: str, body: QWidget) -> QFrame:
    card = QFrame()
    card.setObjectName("JobsSkillGapCard")
    card.setStyleSheet(
        f"""
        QFrame#JobsSkillGapCard {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 14px;
        }}
        """
    )
    layout = vbox(spacing=10, margins=(20, 16, 20, 16))
    card.setLayout(layout)
    layout.addWidget(TitleLabel(title, theme=theme, size=14, weight=QFont.Weight.Bold))
    layout.addWidget(body)
    return card


def _top_required_body(theme: Theme, txt: dict, items: list[dict], total: int) -> QWidget:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    holder.setLayout(layout)

    for entry in items:
        skill = (entry.get("skill") or "").strip()
        count = int(entry.get("count") or 0)
        if not skill or count <= 0:
            continue
        row = QFrame()
        row.setStyleSheet("background: transparent;")
        row_layout = hbox(spacing=12, margins=(0, 0, 0, 0))
        row_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        row.setLayout(row_layout)

        skill_label = BodyLabel(skill, theme=theme, size=13, weight=QFont.Weight.DemiBold)
        skill_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row_layout.addWidget(skill_label, 1)

        count_text = txt["skill_gap_top_count_template"].format(count=count, total=total)
        row_layout.addWidget(SubtleLabel(count_text, theme=theme, size=12))
        layout.addWidget(row)

    if layout.count() == 0:
        layout.addWidget(MutedLabel(txt["skill_gap_no_strong"], theme=theme, size=12))

    return holder


def _empty_state(theme: Theme, txt: dict) -> QWidget:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=12, margins=(48, 68, 48, 68))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    holder.setLayout(layout)

    badge = QFrame()
    badge.setFixedSize(72, 72)
    badge.setStyleSheet(
        f"background-color: {rgba(theme.primary, 0.14)}; border-radius: 18px;"
    )
    bl = hbox(spacing=0, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setLayout(bl)
    bl.addWidget(
        IconLabel(Icons.TRACK_CHANGES, color=theme.primary, size=34),
        alignment=Qt.AlignmentFlag.AlignCenter,
    )
    layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignHCenter)

    layout.addWidget(
        TitleLabel(txt["skill_gap_empty_title"], theme=theme, size=17, weight=QFont.Weight.Bold),
        alignment=Qt.AlignmentFlag.AlignHCenter,
    )
    desc = MutedLabel(txt["skill_gap_empty_desc"], theme=theme, size=12)
    desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
    desc.setMaximumWidth(460)
    layout.addWidget(desc, alignment=Qt.AlignmentFlag.AlignHCenter)

    open_btn = GhostButton(txt["tab_setup"], theme=theme, icon=Icons.TUNE)
    def _go_setup() -> None:
        STATE.active_tab = TAB_SETUP
        REFS.dispatch(_request_full_refresh)
    open_btn.clicked.connect(_go_setup)
    layout.addWidget(open_btn, 0, Qt.AlignmentFlag.AlignHCenter)
    return holder


def _no_profile_state(theme: Theme, txt: dict) -> QWidget:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=12, margins=(48, 68, 48, 68))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    holder.setLayout(layout)

    badge = QFrame()
    badge.setFixedSize(72, 72)
    badge.setStyleSheet(
        f"background-color: {rgba(theme.primary, 0.14)}; border-radius: 18px;"
    )
    bl = hbox(spacing=0, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setLayout(bl)
    bl.addWidget(
        IconLabel(Icons.PERSON_OUTLINE, color=theme.primary, size=34),
        alignment=Qt.AlignmentFlag.AlignCenter,
    )
    layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignHCenter)

    layout.addWidget(
        TitleLabel(txt["skill_gap_empty_title"], theme=theme, size=17, weight=QFont.Weight.Bold),
        alignment=Qt.AlignmentFlag.AlignHCenter,
    )
    desc = MutedLabel(txt["skill_gap_skipped_no_profile"], theme=theme, size=12)
    desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
    desc.setMaximumWidth(460)
    layout.addWidget(desc, alignment=Qt.AlignmentFlag.AlignHCenter)

    open_btn = GhostButton(txt["tab_setup"], theme=theme, icon=Icons.TUNE)
    def _go_setup() -> None:
        STATE.active_tab = TAB_SETUP
        REFS.dispatch(_request_full_refresh)
    open_btn.clicked.connect(_go_setup)
    layout.addWidget(open_btn, 0, Qt.AlignmentFlag.AlignHCenter)
    return holder


def build_skill_gap_tab(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    gap = STATE.skill_gap or {}

    # Empty state - no results yet OR results without a profile.
    if not STATE.has_results():
        layout.addWidget(_empty_state(theme, txt), 1)
        return container

    if not gap:
        if not STATE.has_profile():
            layout.addWidget(_no_profile_state(theme, txt), 1)
            return container
        layout.addWidget(_empty_state(theme, txt), 1)
        return container

    body_holder = QWidget()
    body_holder.setStyleSheet(f"background-color: {theme.bg};")
    body_layout = vbox(spacing=14, margins=(24, 18, 24, 18))
    body_holder.setLayout(body_layout)

    header = QFrame()
    header.setStyleSheet("background: transparent;")
    header_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    header.setLayout(header_layout)
    header_layout.addWidget(TitleLabel(txt["skill_gap_title"], theme=theme, size=18, weight=QFont.Weight.Bold))
    header_layout.addWidget(MutedLabel(txt["skill_gap_subtitle"], theme=theme, size=12))
    body_layout.addWidget(header)

    # Top required ----------------------------------------------------
    top_required = gap.get("top_required") or []
    if top_required:
        body_layout.addWidget(_section_card(
            theme,
            title=txt["skill_gap_top_title"],
            body=_top_required_body(theme, txt, top_required, total=len(STATE.results)),
        ))

    # Strong sides ----------------------------------------------------
    strong = gap.get("user_strong") or []
    strong_body_holder = QFrame()
    strong_body_holder.setStyleSheet("background: transparent;")
    strong_body_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    strong_body_holder.setLayout(strong_body_layout)
    strong_flow = _chip_flow(
        theme,
        items=strong,
        color="#22C55E",
        fill=rgba("#22C55E", 0.18),
    )
    if strong_flow is not None:
        strong_body_layout.addWidget(strong_flow)
    else:
        strong_body_layout.addWidget(MutedLabel(txt["skill_gap_no_strong"], theme=theme, size=12))
    body_layout.addWidget(_section_card(
        theme, title=txt["skill_gap_strong_title"], body=strong_body_holder,
    ))

    # Missing ---------------------------------------------------------
    missing = gap.get("user_missing") or []
    missing_body_holder = QFrame()
    missing_body_holder.setStyleSheet("background: transparent;")
    missing_body_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    missing_body_holder.setLayout(missing_body_layout)
    missing_flow = _chip_flow(
        theme,
        items=missing,
        color="#EF4444",
        fill=rgba("#EF4444", 0.18),
    )
    if missing_flow is not None:
        missing_body_layout.addWidget(missing_flow)
    else:
        missing_body_layout.addWidget(MutedLabel(txt["skill_gap_no_missing"], theme=theme, size=12))
    body_layout.addWidget(_section_card(
        theme, title=txt["skill_gap_missing_title"], body=missing_body_holder,
    ))

    # Advice ----------------------------------------------------------
    advice = gap.get("advice") or []
    advice_body_holder = QFrame()
    advice_body_holder.setStyleSheet("background: transparent;")
    advice_body_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    advice_body_holder.setLayout(advice_body_layout)
    if advice:
        for paragraph in advice:
            bullet_row = QFrame()
            bullet_row.setStyleSheet("background: transparent;")
            row_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
            row_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            bullet_row.setLayout(row_layout)
            row_layout.addWidget(IconLabel(Icons.LIGHTBULB_OUTLINE, color=theme.primary, size=16))
            body_label = BodyLabel(paragraph, theme=theme, size=13, selectable=True)
            body_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            row_layout.addWidget(body_label, 1)
            advice_body_layout.addWidget(bullet_row)
    else:
        advice_body_layout.addWidget(MutedLabel(txt["skill_gap_no_advice"], theme=theme, size=12))
    body_layout.addWidget(_section_card(
        theme, title=txt["skill_gap_advice_title"], body=advice_body_holder,
    ))

    body_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(body_holder)
    layout.addWidget(scroll, 1)
    return container
