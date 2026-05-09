"""AI Study - right-hand context panel.

Four cards:

1. Today's overview - 3 stat tiles (Topics, Studied, Progress).
2. My subjects - rows with a gradient progress bar per subject.
3. Quick tools - 3-column grid of small action tiles.
4. Upcoming tasks - checkbox + title + due-date pill rows.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QSizePolicy,
    QWidget,
)

from src.components.context_panel import context_panel_shell
from src.components.section_card import section_card
from src.qt.icons import Icons
from src.qt.theme import rgba
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
from src.sections.ai_study.data import (
    quick_tools,
    subjects,
    today_overview,
    upcoming_tasks,
)
from src.sections.ai_study.strings import s
from src.theme import Theme


def _stat_tile(theme: Theme, *, icon: str, value: str, label: str) -> QFrame:
    tile = QFrame()
    tile.setStyleSheet(
        f"background-color: {theme.surface_2}; border-radius: 10px;"
    )
    tile.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    layout = vbox(spacing=4, margins=(10, 12, 10, 12))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    tile.setLayout(layout)

    icon_label = IconLabel(icon, color=theme.primary, size=18)
    icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignHCenter)

    value_label = TitleLabel(value, theme=theme, size=18, weight=QFont.Weight.Bold)
    value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(value_label, alignment=Qt.AlignmentFlag.AlignHCenter)

    text_label = MutedLabel(label, theme=theme, size=11)
    text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(text_label, alignment=Qt.AlignmentFlag.AlignHCenter)
    return tile


def _today_overview_card(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    for item in today_overview(lang):
        layout.addWidget(_stat_tile(theme, icon=item["icon"], value=item["value"], label=item["label"]))
    return section_card(theme, icon=Icons.CALENDAR_TODAY, title=txt["today_title"], body=holder)


class _GradientProgress(QWidget):
    """Custom progress bar with a gradient fill painted via QPainter."""

    def __init__(
        self,
        *,
        percent: int,
        color_start: str,
        color_end: str,
        track_color: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._percent = max(0, min(100, percent))
        self._color_start = QColor(color_start)
        self._color_end = QColor(color_end)
        self._track_color = QColor(track_color)
        self.setFixedHeight(6)
        self.setMinimumWidth(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._track_color)
        painter.drawRoundedRect(rect, 3, 3)

        if self._percent <= 0:
            return
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QLinearGradient

        fill_w = int(rect.width() * (self._percent / 100.0))
        if fill_w <= 0:
            return
        gradient = QLinearGradient(QPointF(0, 0), QPointF(fill_w, 0))
        gradient.setColorAt(0.0, self._color_start)
        gradient.setColorAt(1.0, self._color_end)
        painter.setBrush(gradient)
        fill_rect = rect.adjusted(0, 0, fill_w - rect.width(), 0)
        painter.drawRoundedRect(fill_rect, 3, 3)


def _subject_row(theme: Theme, subject: dict) -> QFrame:
    row = QFrame()
    row.setStyleSheet("background: transparent;")
    layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    row.setLayout(layout)

    layout.addWidget(IconLabel(subject["icon"], color=subject["color_start"], size=16))

    name_label = BodyLabel(subject["name"], theme=theme, size=13)
    name_label.setFixedWidth(92)
    layout.addWidget(name_label)

    bar = _GradientProgress(
        percent=subject["percent"],
        color_start=subject["color_start"],
        color_end=subject["color_end"],
        track_color=theme.surface_2,
    )
    layout.addWidget(bar, 1)

    pct_label = BodyLabel(f"{subject['percent']}%", theme=theme, size=12, weight=QFont.Weight.DemiBold)
    pct_label.setFixedWidth(36)
    pct_label.setAlignment(Qt.AlignmentFlag.AlignRight)
    layout.addWidget(pct_label)

    return row


def _add_pill(theme: Theme, label: str) -> ClickFrame:
    pill = ClickFrame()
    pill.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {rgba(theme.primary, 0.10)};
            border: 1px solid {rgba(theme.primary, 0.20)};
            border-radius: 10px;
        }}
        ClickFrame:hover {{
            background-color: {rgba(theme.primary, 0.16)};
        }}
        """
    )
    layout = hbox(spacing=6, margins=(10, 8, 10, 8))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    pill.setLayout(layout)
    layout.addWidget(IconLabel(Icons.ADD, color=theme.primary, size=14))
    layout.addWidget(AccentLabel(label, theme=theme, size=12))
    return pill


def _subjects_card(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=12, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    for subj in subjects(lang):
        layout.addWidget(_subject_row(theme, subj))
    layout.addWidget(_add_pill(theme, txt["add_subject"]))
    return section_card(theme, icon=Icons.BOOKMARK_OUTLINE, title=txt["subjects_title"], body=holder)


def _tool_tile(theme: Theme, *, icon: str, label: str) -> ClickFrame:
    tile = ClickFrame()
    tile.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {theme.surface_2};
            border-radius: 10px;
        }}
        ClickFrame:hover {{
            background-color: {theme.surface};
        }}
        """
    )
    tile.setFixedHeight(72)
    layout = vbox(spacing=6, margins=(6, 10, 6, 10))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    tile.setLayout(layout)
    icon_label = IconLabel(icon, color=theme.primary, size=18)
    icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignHCenter)
    text_label = QLabel(label)
    text_font = QFont()
    text_font.setPixelSize(11)
    text_label.setFont(text_font)
    text_label.setStyleSheet(f"color: {theme.text}; background: transparent;")
    text_label.setWordWrap(True)
    text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(text_label)
    return tile


def _tools_card(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    items = quick_tools(lang)

    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    grid = QGridLayout(holder)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(8)

    cols = 3
    for i, item in enumerate(items):
        grid.addWidget(_tool_tile(theme, icon=item["icon"], label=item["label"]), i // cols, i % cols)

    return section_card(theme, icon=Icons.AUTO_AWESOME, title=txt["tools_title"], body=holder)


def _task_row(theme: Theme, task: dict) -> QFrame:
    row = QFrame()
    row.setStyleSheet("background: transparent;")
    layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    row.setLayout(layout)

    checkbox = QFrame()
    checkbox.setFixedSize(18, 18)
    checkbox.setStyleSheet(
        f"background-color: transparent; border: 1.5px solid {theme.text_muted}; border-radius: 9px;"
    )
    layout.addWidget(checkbox)

    title = BodyLabel(task["title"], theme=theme, size=13)
    title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    layout.addWidget(title, 1)

    layout.addWidget(MutedLabel(task["due"], theme=theme, size=11))
    return row


def _tasks_card(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=12, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    for task in upcoming_tasks(lang):
        layout.addWidget(_task_row(theme, task))
    layout.addWidget(_add_pill(theme, txt["add_task"]))
    return section_card(theme, icon=Icons.EVENT_NOTE, title=txt["tasks_title"], body=holder)


def build_context(theme: Theme, lang: str) -> QWidget:
    return context_panel_shell(
        theme,
        _today_overview_card(theme, lang),
        _subjects_card(theme, lang),
        _tools_card(theme, lang),
        _tasks_card(theme, lang),
    )
