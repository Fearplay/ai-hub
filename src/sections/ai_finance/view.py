"""AI Finance - main center view (matches the design screenshot).

Chat tab keeps the donut + breakdown layout; the seven other tabs use
the shared mock helpers so every Finance topic feels populated even
before any AI is wired up.
"""

from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.components.chat_input import chat_input
from src.components.chat_message import chat_message
from src.components.header import header
from src.components.mock_panel import mock_card_grid_panel, mock_form_panel
from src.components.tabbed_panel import tabbed_panel
from src.i18n import t
from src.qt.icons import Icons
from src.qt.widgets import (
    AccentLabel,
    BodyLabel,
    ClickFrame,
    IconLabel,
    MutedLabel,
    TitleLabel,
    hbox,
    vbox,
)
from src.sections.ai_finance.data import (
    SECTION_ICON,
    assistant_actions,
    budget_donut,
    budget_table,
    tabs,
)
from src.sections.ai_finance.strings import s
from src.services import logger as logger_service
from src.theme import Theme


DONUT_SIZE = 180
DONUT_STROKE = 22


class _DonutChart(QWidget):
    """Pie/donut painted via ``QPainter`` so the colours match the design.

    Slices come in as ``[{"color": "#xx", "percent": int}, ...]``. The
    track behind them sits in the theme's ``surface_2`` colour so the
    chart still reads on light backgrounds.
    """

    def __init__(self, slices: Sequence[dict], *, theme: Theme, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._slices = list(slices)
        self._track_color = QColor(theme.surface_2)
        self.setFixedSize(DONUT_SIZE, DONUT_SIZE)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        inset = DONUT_STROKE / 2 + 2
        rect = QRectF(inset, inset, DONUT_SIZE - 2 * inset, DONUT_SIZE - 2 * inset)

        # track
        track_pen = QPen(self._track_color, DONUT_STROKE)
        track_pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(track_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(rect, 0, 360 * 16)

        total = sum(s["percent"] for s in self._slices) or 1
        # Qt arc start angles are 1/16th degree, with 0 = right axis
        # going counter-clockwise. We want to start at the top and go
        # clockwise like the Flet original, so begin at 90 deg.
        start = 90 * 16
        for slc in self._slices:
            sweep_deg = (slc["percent"] / total) * 360
            sweep = -int(sweep_deg * 16) + 6  # tiny gap between slices
            pen = QPen(QColor(slc["color"]), DONUT_STROKE)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            painter.setPen(pen)
            painter.drawArc(rect, start, sweep)
            start += int(-sweep_deg * 16)


def _donut_with_caption(theme: Theme, lang: str, slices: Sequence[dict]) -> QWidget:
    txt = s(lang)
    holder = QFrame()
    holder.setFixedSize(DONUT_SIZE, DONUT_SIZE)
    holder.setStyleSheet("background: transparent;")
    layout = QVBoxLayout(holder)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    chart = _DonutChart(slices, theme=theme, parent=holder)
    chart.setParent(holder)
    chart.move(0, 0)

    caption_top = QLabel(txt["donut_caption_top"], holder)
    caption_top.setAlignment(Qt.AlignmentFlag.AlignCenter)
    caption_top.setStyleSheet(f"color: {theme.text}; background: transparent; font-size: 18px; font-weight: 700;")
    caption_top.setGeometry(0, DONUT_SIZE // 2 - 22, DONUT_SIZE, 26)

    caption_bottom = QLabel(txt["donut_caption_bottom"], holder)
    caption_bottom.setAlignment(Qt.AlignmentFlag.AlignCenter)
    caption_bottom.setStyleSheet(f"color: {theme.text_muted}; background: transparent; font-size: 11px;")
    caption_bottom.setGeometry(0, DONUT_SIZE // 2 + 6, DONUT_SIZE, 16)

    return holder


def _legend_row(theme: Theme, slc: dict) -> QFrame:
    row = QFrame()
    row.setStyleSheet("background: transparent;")
    layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    row.setLayout(layout)

    dot = QFrame()
    dot.setFixedSize(10, 10)
    dot.setStyleSheet(f"background-color: {slc['color']}; border-radius: 5px;")
    layout.addWidget(dot)

    text_holder = QFrame()
    text_holder.setStyleSheet("background: transparent;")
    text_holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    text_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    text_holder.setLayout(text_layout)
    text_layout.addWidget(BodyLabel(slc["label"], theme=theme, size=13, weight=QFont.Weight.DemiBold))
    text_layout.addWidget(MutedLabel(slc["note"], theme=theme, size=11))
    layout.addWidget(text_holder, 1)

    layout.addWidget(BodyLabel(slc["value"], theme=theme, size=13, weight=QFont.Weight.DemiBold))
    return row


def _legend(theme: Theme, slices: Sequence[dict]) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=14, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    for slc in slices:
        layout.addWidget(_legend_row(theme, slc))
    return holder


def _budget_block(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    slices = budget_donut(lang)

    block = QFrame()
    block.setStyleSheet("background: transparent;")
    block_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    block.setLayout(block_layout)

    head_row = hbox(spacing=6, margins=(0, 0, 0, 0))
    head_row.addWidget(IconLabel(Icons.PIE_CHART_OUTLINE, color=theme.primary, size=16))
    head_row.addWidget(AccentLabel(txt["budget_title"], theme=theme, size=14))
    head_row.addStretch(1)
    head_holder = QFrame()
    head_holder.setStyleSheet("background: transparent;")
    head_holder.setLayout(head_row)
    block_layout.addWidget(head_holder)

    block_layout.addWidget(MutedLabel(txt["budget_subtitle"], theme=theme, size=12))

    body = hbox(spacing=18, margins=(0, 0, 0, 0))
    body.addWidget(_donut_with_caption(theme, lang, slices))
    body.addWidget(_legend(theme, slices), 1)
    body_holder = QFrame()
    body_holder.setStyleSheet("background: transparent;")
    body_holder.setLayout(body)
    block_layout.addWidget(body_holder)

    return block


def _table_header(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    header_box = QFrame()
    header_box.setStyleSheet(
        f"background: transparent; border-bottom: 1px solid {theme.border};"
    )
    grid = QGridLayout(header_box)
    grid.setContentsMargins(4, 8, 4, 8)
    grid.setHorizontalSpacing(8)
    grid.setColumnStretch(0, 4)
    grid.setColumnStretch(1, 2)
    grid.setColumnStretch(2, 3)
    grid.setColumnStretch(3, 4)
    cells = [txt["col_category"], txt["col_recommended"], txt["col_amount"], txt["col_note"]]
    for i, c in enumerate(cells):
        cell = MutedLabel(c, theme=theme, size=12)
        font = cell.font()
        font.setWeight(QFont.Weight.DemiBold)
        cell.setFont(font)
        grid.addWidget(cell, 0, i)
    return header_box


def _table_row(theme: Theme, row: dict) -> QWidget:
    row_box = QFrame()
    row_box.setStyleSheet(
        f"background: transparent; border-bottom: 1px solid {theme.border};"
    )
    grid = QGridLayout(row_box)
    grid.setContentsMargins(4, 10, 4, 10)
    grid.setHorizontalSpacing(8)
    grid.setColumnStretch(0, 4)
    grid.setColumnStretch(1, 2)
    grid.setColumnStretch(2, 3)
    grid.setColumnStretch(3, 4)

    cat_holder = QFrame()
    cat_holder.setStyleSheet("background: transparent;")
    cat_layout = hbox(spacing=6, margins=(0, 0, 0, 0))
    cat_holder.setLayout(cat_layout)
    cat_layout.addWidget(IconLabel(row["icon"], color=row["color"], size=14))
    cat_label = QLabel(row["category"])
    cat_font = QFont()
    cat_font.setPixelSize(12)
    cat_font.setWeight(QFont.Weight.DemiBold)
    cat_label.setFont(cat_font)
    cat_label.setStyleSheet(f"color: {row['color']}; background: transparent;")
    cat_layout.addWidget(cat_label, 1)
    grid.addWidget(cat_holder, 0, 0)

    grid.addWidget(BodyLabel(row["recommended"], theme=theme, size=12), 0, 1)
    grid.addWidget(BodyLabel(row["amount"], theme=theme, size=12), 0, 2)
    grid.addWidget(MutedLabel(row["note"], theme=theme, size=12), 0, 3)
    return row_box


def _breakdown_block(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    block = QFrame()
    block.setStyleSheet("background: transparent;")
    block_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    block.setLayout(block_layout)

    title = QLabel(txt["breakdown_title"])
    title_font = QFont()
    title_font.setPixelSize(13)
    title_font.setWeight(QFont.Weight.Bold)
    title.setFont(title_font)
    title.setStyleSheet(f"color: {theme.primary}; background: transparent;")
    block_layout.addWidget(title)

    table = QFrame()
    table.setStyleSheet(
        f"""
        QFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 10px;
        }}
        """
    )
    table_layout = vbox(spacing=0, margins=(10, 2, 10, 2))
    table.setLayout(table_layout)
    table_layout.addWidget(_table_header(theme, lang))
    for row in budget_table(lang):
        table_layout.addWidget(_table_row(theme, row))
    block_layout.addWidget(table)

    return block


def _action_chip(theme: Theme, icon: str, label: str) -> ClickFrame:
    chip = ClickFrame()
    chip.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 20px;
        }}
        ClickFrame:hover {{
            background-color: {theme.surface_2};
        }}
        """
    )
    layout = hbox(spacing=6, margins=(12, 8, 12, 8))
    chip.setLayout(layout)
    layout.addWidget(IconLabel(icon, color=theme.primary, size=14))
    layout.addWidget(BodyLabel(label, theme=theme, size=12))
    return chip


def _assistant_message(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    avatar = QFrame()
    avatar.setFixedSize(36, 36)
    avatar.setStyleSheet(f"background-color: {theme.primary}; border-radius: 10px;")
    avatar_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    avatar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    avatar.setLayout(avatar_layout)
    avatar_layout.addWidget(IconLabel(SECTION_ICON, color="#FFFFFF", size=18),
                            alignment=Qt.AlignmentFlag.AlignCenter)

    bubble = QFrame()
    bubble.setStyleSheet(
        f"background-color: {theme.assistant_bubble}; border-radius: 14px;"
    )
    bubble_layout = vbox(spacing=18, margins=(18, 18, 18, 18))
    bubble.setLayout(bubble_layout)
    bubble_layout.addWidget(BodyLabel(txt["msg2_intro"], theme=theme, size=14, selectable=True))
    bubble_layout.addWidget(_budget_block(theme, lang))
    bubble_layout.addWidget(_breakdown_block(theme, lang))

    actions_holder = QFrame()
    actions_holder.setStyleSheet("background: transparent;")
    actions_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    actions_holder.setLayout(actions_layout)
    for a in assistant_actions(lang):
        actions_layout.addWidget(_action_chip(theme, a["icon"], a["label"]))
    actions_layout.addStretch(1)

    body_holder = QFrame()
    body_holder.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    body_holder.setLayout(body_layout)
    body_layout.addWidget(MutedLabel("10:28", theme=theme, size=11))
    body_layout.addWidget(bubble)
    body_layout.addWidget(actions_holder)

    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    wrap_layout = QHBoxLayout(wrapper)
    wrap_layout.setContentsMargins(0, 0, 0, 0)
    wrap_layout.setSpacing(12)
    wrap_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    wrap_layout.addWidget(avatar)
    wrap_layout.addWidget(body_holder, 1)
    return wrapper


def _chat_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    user_msg = chat_message(
        theme,
        lang,
        avatar_icon=SECTION_ICON,
        role="user",
        time="10:28",
        text=txt["msg1_user"],
    )

    page = QWidget()
    page_layout = vbox(spacing=22, margins=(24, 20, 24, 20))
    page.setLayout(page_layout)
    page_layout.addWidget(user_msg)
    page_layout.addWidget(_assistant_message(theme, lang))
    page_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(page)
    return scroll


def _budget_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
        title=txt["budget_mock_title"],
        description=txt["budget_mock_desc"],
        fields=[
            {"label": txt["budget_field_income"], "hint": txt["budget_field_income_hint"]},
            {"label": txt["budget_field_savings"], "hint": txt["budget_field_savings_hint"]},
            {"label": txt["budget_field_essentials"], "hint": txt["budget_field_essentials_hint"], "multiline": True},
            {"label": txt["budget_field_lifestyle"], "hint": txt["budget_field_lifestyle_hint"]},
        ],
        examples=[txt["budget_example_1"], txt["budget_example_2"], txt["budget_example_3"]],
    )


def _invest_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=Icons.TRENDING_UP,
        title=txt["invest_title"],
        description=txt["invest_desc"],
        fields=[
            {"label": txt["invest_field_amount"], "hint": txt["invest_field_amount_hint"]},
            {"label": txt["invest_field_horizon"], "hint": txt["invest_field_horizon_hint"]},
            {"label": txt["invest_field_risk"], "hint": txt["invest_field_risk_hint"]},
            {"label": txt["invest_field_focus"], "hint": txt["invest_field_focus_hint"]},
        ],
        examples=[txt["invest_example_1"], txt["invest_example_2"], txt["invest_example_3"]],
    )


def _analysis_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=Icons.QUERY_STATS,
        title=txt["analysis_title"],
        description=txt["analysis_desc"],
        fields=[
            {"label": txt["analysis_field_period"], "hint": txt["analysis_field_period_hint"]},
            {"label": txt["analysis_field_focus"], "hint": txt["analysis_field_focus_hint"]},
            {"label": txt["analysis_field_goal"], "hint": txt["analysis_field_goal_hint"], "multiline": True},
        ],
        examples=[txt["analysis_example_1"], txt["analysis_example_2"], txt["analysis_example_3"]],
    )


def _taxes_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=Icons.RECEIPT_LONG_OUTLINED,
        title=txt["taxes_title"],
        description=txt["taxes_desc"],
        fields=[
            {"label": txt["taxes_field_country"], "hint": txt["taxes_field_country_hint"]},
            {"label": txt["taxes_field_status"], "hint": txt["taxes_field_status_hint"]},
            {"label": txt["taxes_field_year"], "hint": txt["taxes_field_year_hint"]},
            {"label": txt["taxes_field_notes"], "hint": txt["taxes_field_notes_hint"], "multiline": True},
        ],
        examples=[txt["taxes_example_1"], txt["taxes_example_2"], txt["taxes_example_3"]],
    )


def _insurance_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=Icons.SHIELD_OUTLINED,
        title=txt["insurance_title"],
        description=txt["insurance_desc"],
        fields=[
            {"label": txt["insurance_field_household"], "hint": txt["insurance_field_household_hint"]},
            {"label": txt["insurance_field_assets"], "hint": txt["insurance_field_assets_hint"]},
            {"label": txt["insurance_field_existing"], "hint": txt["insurance_field_existing_hint"]},
            {"label": txt["insurance_field_concerns"], "hint": txt["insurance_field_concerns_hint"], "multiline": True},
        ],
        examples=[txt["insurance_example_1"], txt["insurance_example_2"], txt["insurance_example_3"]],
    )


def _calculators_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    cards = [
        {"icon": Icons.TIMELINE, "title": txt["calc_compound_title"], "description": txt["calc_compound_desc"], "action_label": t("show_all", lang), "color": "#22C55E"},
        {"icon": Icons.HOME_OUTLINED, "title": txt["calc_mortgage_title"], "description": txt["calc_mortgage_desc"], "action_label": t("show_all", lang), "color": "#3B82F6"},
        {"icon": Icons.PAYMENTS_OUTLINED, "title": txt["calc_loan_title"], "description": txt["calc_loan_desc"], "action_label": t("show_all", lang), "color": "#F59E0B"},
        {"icon": Icons.ELDERLY, "title": txt["calc_retirement_title"], "description": txt["calc_retirement_desc"], "action_label": t("show_all", lang), "color": "#EF4444"},
        {"icon": Icons.CURRENCY_EXCHANGE, "title": txt["calc_currency_title"], "description": txt["calc_currency_desc"], "action_label": t("show_all", lang), "color": "#0EA5E9"},
        {"icon": Icons.SAVINGS_OUTLINED, "title": txt["calc_savings_title"], "description": txt["calc_savings_desc"], "action_label": t("show_all", lang), "color": "#A78BFA"},
    ]
    return mock_card_grid_panel(theme, lang, icon=Icons.CALCULATE_OUTLINED, title=txt["calc_title"], description=txt["calc_desc"], cards=cards)


def _templates_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    cards = [
        {"icon": Icons.PIE_CHART_OUTLINE, "title": txt["fin_tpl_budget_title"], "description": txt["fin_tpl_budget_desc"], "action_label": txt["fin_tpl_use"], "color": "#22C55E"},
        {"icon": Icons.SHOW_CHART, "title": txt["fin_tpl_invest_title"], "description": txt["fin_tpl_invest_desc"], "action_label": txt["fin_tpl_use"], "color": "#3B82F6"},
        {"icon": Icons.CREDIT_CARD, "title": txt["fin_tpl_debt_title"], "description": txt["fin_tpl_debt_desc"], "action_label": txt["fin_tpl_use"], "color": "#F59E0B"},
        {"icon": Icons.HEALTH_AND_SAFETY, "title": txt["fin_tpl_emergency_title"], "description": txt["fin_tpl_emergency_desc"], "action_label": txt["fin_tpl_use"], "color": "#EF4444"},
    ]
    return mock_card_grid_panel(theme, lang, icon=Icons.GRID_VIEW_OUTLINED, title=txt["fin_tpl_title"], description=txt["fin_tpl_desc"], cards=cards)


def build_view(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    try:
        panels = [
            _chat_panel(theme, lang),
            _budget_panel(theme, lang),
            _invest_panel(theme, lang),
            _analysis_panel(theme, lang),
            _taxes_panel(theme, lang),
            _insurance_panel(theme, lang),
            _calculators_panel(theme, lang),
            _templates_panel(theme, lang),
        ]
    except Exception as exc:
        logger_service.log_exception("ai_finance.view", "build_panels_failed", exc)
        raise

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    layout.addWidget(header(theme, lang, icon=SECTION_ICON, title=txt["title"], subtitle=txt["subtitle"]))
    layout.addWidget(tabbed_panel(theme, tabs=tabs(lang), panels=panels), 1)
    layout.addWidget(chat_input(theme, lang))

    return container
