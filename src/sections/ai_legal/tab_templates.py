"""Templates tab for the AI Legal section.

Two-column rich editor:

* Left  - selectors: 6 templates in a 3x2 grid, 12 colour swatches in
  3 rows of 4, 4 font choices, plus a special "Default - same format as
  input" card explaining the fallback option.
* Right - a live ``A4 preview`` that re-renders whenever any selector
  changes.

All choices live in :class:`LegalState` so they survive switching to
another tab / theme / language.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.qt.effects import apply_drop_shadow
from src.qt.icons import Icons
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    ClickFrame,
    GhostButton,
    IconLabel,
    MutedLabel,
    PrimaryButton,
    custom_label,
    hbox,
    vbox,
)
from src.sections.ai_legal.data import COLORS, fonts, templates
from src.sections.ai_legal.state import STATE
from src.sections.ai_legal.strings import s
from src.theme import Theme


def _section_title(theme: Theme, label: str) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    title = MutedLabel(label, theme=theme, size=11)
    f = QFont(title.font())
    f.setWeight(QFont.Weight.Bold)
    title.setFont(f)
    layout.addWidget(title)
    return holder


def _template_thumb(theme: Theme, *, accent: str) -> QFrame:
    box = QFrame()
    box.setFixedSize(78, 82)
    box.setStyleSheet(
        f"background-color: {theme.surface_2}; border: none; border-radius: 8px;"
    )
    layout = vbox(spacing=4, margins=(10, 10, 10, 10))
    layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
    box.setLayout(layout)

    def _bar(w: int, h: int, color: str) -> QFrame:
        bar = QFrame()
        bar.setFixedSize(w, h)
        bar.setStyleSheet(f"background-color: {color}; border: none; border-radius: 1px;")
        return bar

    layout.addWidget(_bar(44, 4, accent))
    layout.addWidget(_bar(58, 2, rgba(theme.text_muted, 0.55)))
    layout.addWidget(_bar(50, 2, rgba(theme.text_muted, 0.45)))
    layout.addWidget(_bar(46, 2, rgba(theme.text_muted, 0.35)))
    layout.addWidget(_bar(58, 2, rgba(theme.text_muted, 0.45)))
    return box


def _template_card(
    theme: Theme,
    *,
    template: dict,
    active: bool,
    accent: str,
    on_click: Callable[[], None],
) -> ClickFrame:
    border_color = theme.primary if active else theme.border
    border_width = 2 if active else 1
    card = ClickFrame()
    card.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {theme.surface};
            border: {border_width}px solid {border_color};
            border-radius: 12px;
        }}
        ClickFrame:hover {{
            border: 2px solid {theme.primary};
        }}
        """
    )
    layout = vbox(spacing=8, margins=(12, 12, 12, 12))
    card.setLayout(layout)
    layout.addWidget(_template_thumb(theme, accent=accent))

    head = QFrame()
    head.setStyleSheet("background: transparent; border: none;")
    head_layout = hbox(spacing=4, margins=(0, 0, 0, 0))
    head_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    head.setLayout(head_layout)
    title = BodyLabel(template["label"], theme=theme, size=13, weight=QFont.Weight.Bold)
    title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    head_layout.addWidget(title, 1)
    if active:
        head_layout.addWidget(IconLabel(Icons.CHECK_CIRCLE, color=theme.primary, size=16))
    layout.addWidget(head)

    desc = MutedLabel(template["desc"], theme=theme, size=11)
    layout.addWidget(desc)
    card.clicked.connect(on_click)
    return card


def _color_swatch(
    theme: Theme,
    *,
    color: str,
    active: bool,
    on_click: Callable[[], None],
) -> ClickFrame:
    border_color = theme.primary if active else theme.border
    swatch = ClickFrame()
    swatch.setFixedSize(38, 38)
    swatch.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {rgba(color, 0.20) if active else 'transparent'};
            border: 2px solid {border_color};
            border-radius: 18px;
        }}
        """
    )
    layout = hbox(spacing=0, margins=(2, 2, 2, 2))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    swatch.setLayout(layout)

    inner = QFrame()
    inner.setFixedSize(28, 28)
    inner.setStyleSheet(f"background-color: {color}; border: none; border-radius: 14px;")
    if active:
        inner_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
        inner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.setLayout(inner_layout)
        inner_layout.addWidget(IconLabel(Icons.CHECK, color="#FFFFFF", size=14),
                               alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(inner, alignment=Qt.AlignmentFlag.AlignCenter)
    swatch.clicked.connect(on_click)
    return swatch


def _font_row(
    theme: Theme,
    *,
    font: dict,
    active: bool,
    on_click: Callable[[], None],
) -> ClickFrame:
    border_color = theme.primary if active else theme.border
    border_width = 2 if active else 1
    row = ClickFrame()
    row.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {theme.surface};
            border: {border_width}px solid {border_color};
            border-radius: 10px;
        }}
        ClickFrame:hover {{
            border: 2px solid {theme.primary};
        }}
        """
    )
    layout = hbox(spacing=10, margins=(12, 10, 12, 10))
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    row.setLayout(layout)
    label = BodyLabel(font["label"], theme=theme, size=13, weight=QFont.Weight.DemiBold)
    label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    layout.addWidget(label, 1)
    layout.addWidget(MutedLabel(s("en")["font_sample"], theme=theme, size=14))
    layout.addWidget(IconLabel(
        Icons.CHECK_CIRCLE if active else Icons.RADIO_BUTTON_UNCHECKED,
        color=theme.primary if active else theme.text_subtle,
        size=18,
    ))
    row.clicked.connect(on_click)
    return row


def _default_card(
    theme: Theme,
    lang: str,
    *,
    active: bool,
    on_click: Callable[[], None],
) -> ClickFrame:
    txt = s(lang)
    accent = "#3B82F6"
    border_color = accent if active else theme.border
    border_width = 2 if active else 1
    card = ClickFrame()
    card.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {rgba(accent, 0.06)};
            border: {border_width}px solid {border_color};
            border-radius: 12px;
        }}
        ClickFrame:hover {{
            border: 2px solid {accent};
        }}
        """
    )
    layout = hbox(spacing=12, margins=(14, 14, 14, 14))
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    card.setLayout(layout)

    badge = QFrame()
    badge.setFixedSize(44, 44)
    badge.setStyleSheet(
        f"background-color: {rgba(accent, 0.15)}; border: none; border-radius: 10px;"
    )
    bl = hbox(spacing=0, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setLayout(bl)
    bl.addWidget(IconLabel(Icons.RESTART_ALT, color=accent, size=22), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(badge)

    info = QFrame()
    info.setStyleSheet("background: transparent; border: none;")
    info.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    info_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    info.setLayout(info_layout)
    info_layout.addWidget(BodyLabel(txt["templates_section_default_title"], theme=theme, size=14, weight=QFont.Weight.Bold))
    info_layout.addWidget(MutedLabel(txt["templates_section_default_desc"], theme=theme, size=12))
    layout.addWidget(info, 1)

    layout.addWidget(IconLabel(
        Icons.CHECK_CIRCLE if active else Icons.RADIO_BUTTON_UNCHECKED,
        color=accent if active else theme.text_subtle,
        size=18,
    ))
    card.clicked.connect(on_click)
    return card


def _selected_template(lang: str) -> dict:
    items = templates(lang)
    for tpl in items:
        if tpl["key"] == STATE.selected_template:
            return tpl
    return items[0]


def _selected_font(lang: str) -> dict:
    items = fonts(lang)
    for f in items:
        if f["key"] == STATE.selected_font:
            return f
    return items[0]


def _a4_preview(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    accent = STATE.selected_color
    is_default = STATE.selected_template == "default"
    template = _selected_template(lang) if not is_default else None
    font = _selected_font(lang)

    body_color = "#1E293B"
    muted_color = "#64748B"
    paper_color = "#FDFDFD"

    if is_default:
        accent = "#3B82F6"
        heading_size = 22
    else:
        heading_size = template["heading_size"] if template else 22

    paragraphs = [
        txt["preview_doc_paragraph_1"],
        txt["preview_doc_paragraph_2"],
        txt["preview_doc_paragraph_3"],
    ]

    paper = QFrame()
    paper.setFixedSize(320, 440)
    paper.setStyleSheet(
        f"""
        QFrame {{
            background-color: {paper_color};
            border: 1px solid #CBD5F5;
            border-radius: 10px;
        }}
        """
    )
    apply_drop_shadow(paper, blur=24, offset=(0, 8), color="#000000", alpha=0.20)
    layout = vbox(spacing=10, margins=(24, 22, 24, 22))
    paper.setLayout(layout)

    accent_bar = QFrame()
    accent_bar.setFixedSize(92, 6)
    accent_bar.setStyleSheet(f"background-color: {accent}; border: none; border-radius: 3px;")
    layout.addWidget(accent_bar)

    heading = custom_label(txt["preview_doc_heading"], color=body_color, size=heading_size, weight=QFont.Weight.Bold)
    layout.addWidget(heading)
    sub = custom_label(txt["preview_doc_subheading"], color=accent, size=13, weight=QFont.Weight.DemiBold)
    layout.addWidget(sub)

    layout.addSpacing(4)
    for p in paragraphs:
        layout.addWidget(custom_label(p, color=body_color, size=12, selectable=True))

    layout.addStretch(1)

    foot = QFrame()
    foot.setStyleSheet("background: transparent; border: none;")
    foot_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    foot_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    foot.setLayout(foot_layout)
    foot_layout.addWidget(custom_label(txt["preview_doc_footer"], color=muted_color, size=10))
    foot_layout.addStretch(1)

    badge = QFrame()
    badge.setStyleSheet(
        f"background-color: {rgba(accent, 0.12)}; border: none; border-radius: 4px;"
    )
    badge_layout = hbox(spacing=0, margins=(8, 2, 8, 2))
    badge.setLayout(badge_layout)
    badge_layout.addWidget(custom_label(
        STATE.selected_template.upper() if not is_default else "DEFAULT",
        color=accent,
        size=10,
        weight=QFont.Weight.Bold,
    ))
    foot_layout.addWidget(badge)
    layout.addWidget(foot)
    return paper


def build_templates_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Optional[Callable[[], None]] = None,
) -> QWidget:
    txt = s(lang)

    def _trigger_rerender() -> None:
        if on_request_rerender is not None:
            on_request_rerender()

    def _set_template(key: str) -> None:
        if STATE.selected_template == key:
            return
        STATE.selected_template = key
        _trigger_rerender()

    def _set_color(color: str) -> None:
        if STATE.selected_color == color:
            return
        STATE.selected_color = color
        _trigger_rerender()

    def _set_font(key: str) -> None:
        if STATE.selected_font == key:
            return
        STATE.selected_font = key
        _trigger_rerender()

    template_grid_holder = QFrame()
    template_grid_holder.setStyleSheet("background: transparent;")
    template_grid = QGridLayout(template_grid_holder)
    template_grid.setContentsMargins(0, 0, 0, 0)
    template_grid.setHorizontalSpacing(12)
    template_grid.setVerticalSpacing(12)
    cols = 3
    for i, tpl in enumerate(templates(lang)):
        template_grid.addWidget(
            _template_card(
                theme,
                template=tpl,
                active=STATE.selected_template == tpl["key"],
                accent=STATE.selected_color,
                on_click=lambda k=tpl["key"]: _set_template(k),
            ),
            i // cols,
            i % cols,
        )

    swatches_holder = QFrame()
    swatches_holder.setStyleSheet("background: transparent;")
    swatches_grid = QGridLayout(swatches_holder)
    swatches_grid.setContentsMargins(0, 0, 0, 0)
    swatches_grid.setHorizontalSpacing(10)
    swatches_grid.setVerticalSpacing(10)
    swatch_cols = 6
    for i, c in enumerate(COLORS):
        swatches_grid.addWidget(
            _color_swatch(
                theme,
                color=c,
                active=STATE.selected_color == c,
                on_click=lambda color=c: _set_color(color),
            ),
            i // swatch_cols,
            i % swatch_cols,
        )

    fonts_holder = QFrame()
    fonts_holder.setStyleSheet("background: transparent;")
    fonts_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    fonts_holder.setLayout(fonts_layout)
    for f in fonts(lang):
        fonts_layout.addWidget(_font_row(theme, font=f, active=STATE.selected_font == f["key"], on_click=lambda k=f["key"]: _set_font(k)))

    default_card = _default_card(theme, lang, active=STATE.selected_template == "default", on_click=lambda: _set_template("default"))

    left_holder = QWidget()
    left_holder.setStyleSheet("background: transparent;")
    left_layout = vbox(spacing=10, margins=(0, 0, 16, 0))
    left_holder.setLayout(left_layout)
    left_layout.addWidget(_section_title(theme, txt["templates_section_styles"]))
    left_layout.addWidget(template_grid_holder)
    left_layout.addSpacing(4)
    left_layout.addWidget(_section_title(theme, txt["templates_section_color"]))
    left_layout.addWidget(swatches_holder)
    left_layout.addSpacing(4)
    left_layout.addWidget(_section_title(theme, txt["templates_section_font"]))
    left_layout.addWidget(fonts_holder)
    left_layout.addSpacing(4)
    left_layout.addWidget(default_card)
    left_layout.addStretch(1)

    right_holder = QWidget()
    right_holder.setStyleSheet("background: transparent;")
    right_layout = vbox(spacing=14, margins=(0, 0, 0, 0))
    right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    right_holder.setLayout(right_layout)

    right_title = MutedLabel(txt["preview_title"], theme=theme, size=11)
    f = QFont(right_title.font())
    f.setWeight(QFont.Weight.Bold)
    right_title.setFont(f)
    right_layout.addWidget(right_title)

    preview_row = QFrame()
    preview_row.setStyleSheet("background: transparent;")
    pr = hbox(spacing=0, margins=(0, 0, 0, 0))
    pr.setAlignment(Qt.AlignmentFlag.AlignCenter)
    preview_row.setLayout(pr)
    pr.addWidget(_a4_preview(theme, lang))
    right_layout.addWidget(preview_row)

    btn_row = QFrame()
    btn_row.setStyleSheet("background: transparent;")
    br = hbox(spacing=10, margins=(0, 0, 0, 0))
    br.setAlignment(Qt.AlignmentFlag.AlignCenter)
    btn_row.setLayout(br)
    br.addWidget(PrimaryButton(txt["btn_apply_template"], theme=theme))
    br.addWidget(GhostButton(txt["btn_download_sample"], theme=theme))
    right_layout.addWidget(btn_row)

    inner = QWidget()
    inner.setStyleSheet(f"background-color: {theme.bg};")
    inner_layout = QHBoxLayout(inner)
    inner_layout.setContentsMargins(24, 18, 24, 18)
    inner_layout.setSpacing(18)
    inner_layout.addWidget(left_holder, 7)
    inner_layout.addWidget(right_holder, 5)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(inner)
    return scroll
