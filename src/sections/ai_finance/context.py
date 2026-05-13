"""AI Finance - right-hand context panel.

Four cards:

1. Quick actions - 5 link-style rows with chevrons.
2. Markets overview - 5 ticker rows with QPainter sparklines.
3. Recent analyses - 4 history-like rows.
4. Daily tip - icon + paragraph.
"""

from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QWidget

from src.components.context_panel import (
    context_panel_shell,
    history_row,
    quick_action_row,
)
from src.components.section_card import section_card
from src.qt.icons import Icons
from src.qt.widgets import (
    BodyLabel,
    ClickFrame,
    IconLabel,
    MutedLabel,
    hbox,
    vbox,
)
from src.sections.ai_finance.data import (
    TREND_DOWN,
    TREND_UP,
    daily_tip,
    market_tickers,
    quick_actions,
    recent_analyses,
)
from src.sections.ai_finance.strings import s
from src.theme import Theme


SPARK_WIDTH = 64
SPARK_HEIGHT = 26


class _Sparkline(QWidget):
    """Tiny line chart painted via ``QPainter``.

    Antialiased + rounded caps so the line still reads at 26 px tall.
    """

    def __init__(self, values: Sequence[float], *, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._values = list(values)
        self._color = QColor(color)
        self.setFixedSize(SPARK_WIDTH, SPARK_HEIGHT)

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._values:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        lo = min(self._values)
        hi = max(self._values)
        span = (hi - lo) or 1.0

        margin_y = 3
        plot_h = SPARK_HEIGHT - 2 * margin_y
        step_x = SPARK_WIDTH / max(1, len(self._values) - 1)

        points = QPolygonF()
        for i, v in enumerate(self._values):
            x = i * step_x
            y = margin_y + (1 - (v - lo) / span) * plot_h
            points.append(QPointF(x, y))

        pen = QPen(self._color, 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPolyline(points)


def _quick_actions_card(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    rows = QFrame()
    rows.setStyleSheet("background: transparent;")
    rows_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    rows.setLayout(rows_layout)
    for a in quick_actions(lang):
        rows_layout.addWidget(quick_action_row(theme, a["icon"], a["label"]))
    return section_card(theme, icon=Icons.BOLT_OUTLINED, title=txt["quick_title"], body=rows)


def _ticker_row(theme: Theme, ticker: dict) -> ClickFrame:
    trend_color = TREND_UP if ticker["trend"] == "up" else TREND_DOWN

    row = ClickFrame()
    row.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: transparent;
            border-radius: 8px;
        }}
        ClickFrame:hover {{
            background-color: {theme.surface_2};
        }}
        """
    )
    layout = hbox(spacing=10, margins=(4, 6, 4, 6))
    row.setLayout(layout)

    icon_box = QFrame()
    icon_box.setFixedSize(28, 28)
    icon_box.setStyleSheet(
        f"background-color: {ticker['icon_color']}; border-radius: 8px;"
    )
    ib = hbox(spacing=0, margins=(0, 0, 0, 0))
    ib.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setLayout(ib)
    ib.addWidget(IconLabel(ticker["icon"], color="#FFFFFF", size=14),
                 alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(icon_box)

    name_value = QFrame()
    name_value.setStyleSheet("background: transparent;")
    name_value.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    nv_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    name_value.setLayout(nv_layout)
    nv_layout.addWidget(BodyLabel(ticker["symbol"], theme=theme, size=12))
    nv_layout.addWidget(MutedLabel(ticker["value"], theme=theme, size=11))
    layout.addWidget(name_value, 1)

    layout.addWidget(_Sparkline(ticker["spark"], color=trend_color))

    change_label = QLabel(ticker["change"])
    change_font = QFont()
    change_font.setPixelSize(11)
    change_font.setWeight(QFont.Weight.Bold)
    change_label.setFont(change_font)
    change_label.setStyleSheet(f"color: {trend_color}; background: transparent;")
    layout.addWidget(change_label)
    return row


def _markets_card(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    rows = QFrame()
    rows.setStyleSheet("background: transparent;")
    rows_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    rows.setLayout(rows_layout)
    for ticker in market_tickers(lang):
        rows_layout.addWidget(_ticker_row(theme, ticker))
    return section_card(theme, icon=Icons.SHOW_CHART, title=txt["markets_title"], body=rows)


def _analyses_card(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    rows = QFrame()
    rows.setStyleSheet("background: transparent;")
    rows_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    rows.setLayout(rows_layout)
    for item in recent_analyses(lang):
        rows_layout.addWidget(history_row(theme, item["title"], item["time"]))
    return section_card(theme, icon=Icons.HISTORY, title=txt["analyses_title"], body=rows)


def _tip_card(theme: Theme, lang: str) -> QWidget:
    tip = daily_tip(lang)
    body = BodyLabel(tip["text"], theme=theme, size=12, selectable=True)
    return section_card(theme, icon=Icons.LIGHTBULB_OUTLINE, title=tip["title"], body=body)


def build_context(theme: Theme, lang: str) -> QWidget:
    return context_panel_shell(
        theme,
        _quick_actions_card(theme, lang),
        _markets_card(theme, lang),
        _analyses_card(theme, lang),
        _tip_card(theme, lang),
    )
