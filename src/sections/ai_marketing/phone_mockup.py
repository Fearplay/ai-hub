"""Instagram-post phone preview, drawn with Qt primitives.

Lives in the right side of the AI Marketing assistant message bubble.
The mockup uses a hand-painted gradient background (via
``QGraphicsEffect`` would lose pixel control on rounded corners; we draw
the gradient ourselves in ``paintEvent``) plus regular ``QFrame``
children for the cards / chart bars / store badges.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.qt.effects import apply_drop_shadow
from src.qt.icons import Icons
from src.qt.widgets import IconLabel, hbox, vbox
from src.sections.ai_marketing.strings import s
from src.theme import Theme


PHONE_BG_TOP = "#1A1140"
PHONE_BG_BOTTOM = "#2D1568"
ACCENT = "#F0489E"
CARD_BG = "#FFFFFF"
CARD_TEXT = "#0F172A"
CHART_BAR = "#F59E0B"
CHART_BAR_DIM = "#FED7AA"
STORE_BG = "#0B0B14"


class _GradientFrame(QWidget):
    """Rounded rectangle filled with a top-left to bottom-right gradient."""

    def __init__(
        self,
        *,
        radius: int,
        color_top: str,
        color_bottom: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._radius = radius
        self._top = QColor(color_top)
        self._bottom = QColor(color_bottom)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        gradient = QLinearGradient(QPointF(0, 0), QPointF(rect.width(), rect.height()))
        gradient.setColorAt(0.0, self._top)
        gradient.setColorAt(1.0, self._bottom)

        path = QPainterPath()
        path.addRoundedRect(rect, self._radius, self._radius)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.fillPath(path, gradient)


def _chart_bars() -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = hbox(spacing=6, margins=(0, 0, 0, 0))
    layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
    holder.setLayout(layout)
    heights = [22, 30, 18, 36, 26, 42, 32]
    for i, h in enumerate(heights):
        bar = QFrame()
        bar.setFixedSize(8, h)
        color = CHART_BAR if i % 2 == 0 else CHART_BAR_DIM
        bar.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
        layout.addWidget(bar)
    return holder


def _balance_card(lang: str) -> QFrame:
    txt = s(lang)
    card = QFrame()
    card.setStyleSheet(f"background-color: {CARD_BG}; border-radius: 10px;")
    apply_drop_shadow(card, blur=8, offset=(0, 2), color="#000000", alpha=0.18)
    layout = vbox(spacing=4, margins=(10, 10, 10, 10))
    card.setLayout(layout)

    head = hbox(spacing=4, margins=(0, 0, 0, 0))
    title = QLabel(txt["phone_overview"])
    title_font = QFont()
    title_font.setPixelSize(10)
    title_font.setWeight(QFont.Weight.DemiBold)
    title.setFont(title_font)
    title.setStyleSheet(f"color: {CARD_TEXT}; background: transparent;")
    head.addWidget(title)
    head.addStretch(1)
    head.addWidget(IconLabel(Icons.MORE_HORIZ, color="#94A3B8", size=12))
    head_holder = QFrame()
    head_holder.setStyleSheet("background: transparent;")
    head_holder.setLayout(head)
    layout.addWidget(head_holder)

    balance = QLabel(txt["phone_balance"])
    balance_font = QFont()
    balance_font.setPixelSize(14)
    balance_font.setWeight(QFont.Weight.Bold)
    balance.setFont(balance_font)
    balance.setStyleSheet(f"color: {CARD_TEXT}; background: transparent;")
    layout.addWidget(balance)

    layout.addSpacing(2)
    layout.addWidget(_chart_bars())
    return card


def _cta_button(lang: str) -> QFrame:
    btn = QFrame()
    btn.setStyleSheet(f"background-color: {ACCENT}; border-radius: 20px;")
    layout = hbox(spacing=0, margins=(14, 8, 14, 8))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    btn.setLayout(layout)
    label = QLabel(s(lang)["phone_cta"])
    label_font = QFont()
    label_font.setPixelSize(11)
    label_font.setWeight(QFont.Weight.Bold)
    label.setFont(label_font)
    label.setStyleSheet("color: #FFFFFF; background: transparent;")
    layout.addWidget(label)
    return btn


def _store_badge(lang: str, *, kind: str) -> QFrame:
    txt = s(lang)
    if kind == "apple":
        icon = Icons.APPLE
        caption = txt["phone_app_store_caption"]
        store_name = txt["phone_app_store"]
    else:
        icon = Icons.PLAY_ARROW_ROUNDED
        caption = txt["phone_play_store_caption"]
        store_name = txt["phone_play_store"]

    badge = QFrame()
    badge.setStyleSheet(f"background-color: {STORE_BG}; border-radius: 6px;")
    layout = hbox(spacing=4, margins=(8, 4, 8, 4))
    badge.setLayout(layout)
    layout.addWidget(IconLabel(icon, color="#FFFFFF", size=14))

    text_holder = QFrame()
    text_holder.setStyleSheet("background: transparent;")
    text_layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    text_holder.setLayout(text_layout)

    cap = QLabel(caption)
    cap_font = QFont()
    cap_font.setPixelSize(7)
    cap.setFont(cap_font)
    cap.setStyleSheet("color: #FFFFFF; background: transparent;")
    text_layout.addWidget(cap)

    name = QLabel(store_name)
    name_font = QFont()
    name_font.setPixelSize(10)
    name_font.setWeight(QFont.Weight.Bold)
    name.setFont(name_font)
    name.setStyleSheet("color: #FFFFFF; background: transparent;")
    text_layout.addWidget(name)

    layout.addWidget(text_holder)
    return badge


def _page_dots() -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = hbox(spacing=4, margins=(0, 0, 0, 0))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    holder.setLayout(layout)
    for i in range(4):
        dot = QFrame()
        if i == 0:
            dot.setFixedSize(6, 4)
            dot.setStyleSheet("background-color: #FFFFFF; border-radius: 2px;")
        else:
            dot.setFixedSize(4, 4)
            dot.setStyleSheet("background-color: rgba(255, 255, 255, 0.4); border-radius: 2px;")
        layout.addWidget(dot)
    return holder


def phone_mockup(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)

    bezel = QFrame()
    bezel.setObjectName("PhoneBezel")
    bezel.setStyleSheet(
        f"""
        QFrame#PhoneBezel {{
            background-color: #0B0B14;
            border-radius: 26px;
        }}
        """
    )
    bezel.setFixedSize(218, 328)
    apply_drop_shadow(bezel, blur=22, offset=(0, 10), color="#000000", alpha=0.32)
    bezel_layout = vbox(spacing=0, margins=(4, 4, 4, 4))
    bezel.setLayout(bezel_layout)

    inner = _GradientFrame(radius=22, color_top=PHONE_BG_TOP, color_bottom=PHONE_BG_BOTTOM)
    inner.setFixedSize(210, 320)
    inner_layout = QVBoxLayout(inner)
    inner_layout.setContentsMargins(16, 18, 16, 14)
    inner_layout.setSpacing(8)

    headline_holder = QFrame()
    headline_holder.setStyleSheet("background: transparent;")
    headline_layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    headline_holder.setLayout(headline_layout)
    head_top = QLabel(txt["phone_headline_top"])
    head_top_font = QFont()
    head_top_font.setPixelSize(22)
    head_top_font.setWeight(QFont.Weight.Black)
    head_top.setFont(head_top_font)
    head_top.setStyleSheet("color: #FFFFFF; background: transparent;")
    headline_layout.addWidget(head_top)
    head_bottom = QLabel(txt["phone_headline_bottom"])
    head_bottom.setFont(head_top_font)
    head_bottom.setStyleSheet(f"color: {ACCENT}; background: transparent;")
    headline_layout.addWidget(head_bottom)
    inner_layout.addWidget(headline_holder)

    subtitle = QLabel(txt["phone_subtitle"])
    sub_font = QFont()
    sub_font.setPixelSize(10)
    subtitle.setFont(sub_font)
    subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.85); background: transparent;")
    subtitle.setWordWrap(True)
    inner_layout.addWidget(subtitle)

    inner_layout.addSpacing(2)
    inner_layout.addWidget(_balance_card(lang))

    cta_row = QHBoxLayout()
    cta_row.setContentsMargins(0, 0, 0, 0)
    cta_row.setSpacing(0)
    cta_row.addWidget(_cta_button(lang))
    cta_row.addStretch(1)
    inner_layout.addLayout(cta_row)

    badges_row = QFrame()
    badges_row.setStyleSheet("background: transparent;")
    badges_layout = hbox(spacing=6, margins=(0, 0, 0, 0))
    badges_row.setLayout(badges_layout)
    badges_layout.addWidget(_store_badge(lang, kind="apple"))
    badges_layout.addWidget(_store_badge(lang, kind="play"))
    badges_layout.addStretch(1)
    inner_layout.addWidget(badges_row)

    inner_layout.addStretch(1)
    inner_layout.addWidget(_page_dots())

    bezel_layout.addWidget(inner)
    return bezel
