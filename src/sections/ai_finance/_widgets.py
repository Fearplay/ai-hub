"""Reusable widgets for AI Finance tabs.

The donut chart and breakdown table were previously inlined in
``view.py``; multiple tabs (Chat, Budget) now use them so they live in
this small helper module. Small form helpers (labelled input row,
labelled multi-line, form section card) live here for the same
reason - any new tab can compose them without copy-pasting QSS.
"""

from __future__ import annotations

from typing import Callable, Optional, Sequence

from PySide6.QtCore import QEvent, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.qt.icons import Icons
from src.qt.theme import rgba
from src.qt.widgets import (
    AccentLabel,
    BodyLabel,
    IconLabel,
    MutedLabel,
    ScrollSafeComboBox,
    SubtleLabel,
    TitleLabel,
    custom_label,
    hbox,
    themed_line_edit,
    themed_text_edit,
    vbox,
)
from src.sections.ai_finance.data import (
    NEEDS_COLOR,
    SAVING_COLOR,
    WANTS_COLOR,
)
from src.theme import Theme


DONUT_SIZE = 180
DONUT_STROKE = 22


def _group_color(group: str) -> str:
    """Map the BudgetPlan ``group`` enum to a slice colour.

    Falls back to the wants colour for any unknown enum value so the
    chart never silently renders with a transparent slice.
    """
    if group == "needs":
        return NEEDS_COLOR
    if group == "saving":
        return SAVING_COLOR
    return WANTS_COLOR


class DonutChart(QWidget):
    """Donut painted via ``QPainter`` keyed by ``[{color, percent}]``."""

    def __init__(self, slices: Sequence[dict], *, theme: Theme, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._slices = list(slices)
        self._track_color = QColor(theme.surface_2)
        self.setFixedSize(DONUT_SIZE, DONUT_SIZE)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        inset = DONUT_STROKE / 2 + 2
        rect = QRectF(inset, inset, DONUT_SIZE - 2 * inset, DONUT_SIZE - 2 * inset)
        track_pen = QPen(self._track_color, DONUT_STROKE)
        track_pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(track_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(rect, 0, 360 * 16)
        total = sum(item.get("percent", 0) for item in self._slices) or 1
        start = 90 * 16
        for slc in self._slices:
            sweep_deg = (slc.get("percent", 0) / total) * 360
            sweep = -int(sweep_deg * 16) + 6
            pen = QPen(QColor(slc.get("color", "#94A3B8")), DONUT_STROKE)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            painter.setPen(pen)
            painter.drawArc(rect, start, sweep)
            start += int(-sweep_deg * 16)


def donut_with_caption(
    theme: Theme,
    *,
    slices: Sequence[dict],
    caption_top: str,
    caption_bottom: str,
) -> QWidget:
    holder = QFrame()
    holder.setFixedSize(DONUT_SIZE, DONUT_SIZE)
    holder.setStyleSheet("background: transparent;")
    layout = QVBoxLayout(holder)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    chart = DonutChart(slices, theme=theme, parent=holder)
    chart.move(0, 0)

    top = QLabel(caption_top, holder)
    top.setAlignment(Qt.AlignmentFlag.AlignCenter)
    top.setStyleSheet(
        f"color: {theme.text}; background: transparent; font-size: 18px; font-weight: 700;"
    )
    top.setGeometry(0, DONUT_SIZE // 2 - 22, DONUT_SIZE, 26)

    bottom = QLabel(caption_bottom, holder)
    bottom.setAlignment(Qt.AlignmentFlag.AlignCenter)
    bottom.setStyleSheet(
        f"color: {theme.text_muted}; background: transparent; font-size: 11px;"
    )
    bottom.setGeometry(0, DONUT_SIZE // 2 + 6, DONUT_SIZE, 16)
    return holder


def budget_slices_from_plan(budget: dict) -> list[dict]:
    """Convert a BudgetPlan ``splits`` dict to donut slices."""
    splits = (budget or {}).get("splits") or {}
    out: list[dict] = []
    for key, color in (("needs", NEEDS_COLOR), ("wants", WANTS_COLOR), ("saving", SAVING_COLOR)):
        group = splits.get(key) or {}
        out.append(
            {
                "color": color,
                "percent": float(group.get("percent") or 0.0),
                "label": group.get("label") or key.title(),
                "value": float(group.get("amount") or 0.0),
            }
        )
    return out


def legend_for_splits(theme: Theme, slices: Sequence[dict], *, currency: str) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=14, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    for slc in slices:
        row = QFrame()
        row.setStyleSheet("background: transparent;")
        row_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
        row.setLayout(row_layout)
        dot = QFrame()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background-color: {slc['color']}; border-radius: 5px;")
        row_layout.addWidget(dot)
        text_holder = QFrame()
        text_holder.setStyleSheet("background: transparent;")
        text_holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        text_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
        text_holder.setLayout(text_layout)
        text_layout.addWidget(BodyLabel(slc["label"], theme=theme, size=13, weight=QFont.Weight.DemiBold))
        text_layout.addWidget(MutedLabel(f"{slc['percent']:.0f}%", theme=theme, size=11))
        row_layout.addWidget(text_holder, 1)
        row_layout.addWidget(
            BodyLabel(
                f"{slc['value']:,.0f} {currency}".replace(",", " "),
                theme=theme,
                size=13,
                weight=QFont.Weight.DemiBold,
            )
        )
        layout.addWidget(row)
    return holder


def section_card(theme: Theme) -> tuple[QFrame, QVBoxLayout]:
    card = QFrame()
    card.setObjectName("FinanceCard")
    card.setStyleSheet(
        f"""
        QFrame#FinanceCard {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        """
    )
    layout = vbox(spacing=12, margins=(18, 16, 18, 16))
    card.setLayout(layout)
    return card, layout


def card_title(theme: Theme, *, title: str, subtitle: str = "", icon: str = "") -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    if icon:
        layout.addWidget(IconLabel(icon, color=theme.primary, size=18))
    title_col = QFrame()
    title_col.setStyleSheet("background: transparent;")
    title_col.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    title_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    title_col.setLayout(title_layout)
    title_layout.addWidget(TitleLabel(title, theme=theme, size=14))
    if subtitle:
        title_layout.addWidget(MutedLabel(subtitle, theme=theme, size=11))
    layout.addWidget(title_col, 1)
    return holder


def labelled_line_edit(
    theme: Theme,
    *,
    label: str,
    hint: str = "",
    placeholder: str = "",
    initial: str = "",
    password: bool = False,
) -> tuple[QFrame, QLineEdit]:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    layout.addWidget(BodyLabel(label, theme=theme, size=12, weight=QFont.Weight.DemiBold))
    if hint:
        layout.addWidget(MutedLabel(hint, theme=theme, size=11))
    field = themed_line_edit(theme, placeholder=placeholder, password=password)
    field.setText(initial)
    layout.addWidget(field)
    return holder, field


def labelled_text_edit(
    theme: Theme,
    *,
    label: str,
    hint: str = "",
    placeholder: str = "",
    initial: str = "",
    min_height: int = 80,
) -> tuple[QFrame, QPlainTextEdit]:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    layout.addWidget(BodyLabel(label, theme=theme, size=12, weight=QFont.Weight.DemiBold))
    if hint:
        layout.addWidget(MutedLabel(hint, theme=theme, size=11))
    field = themed_text_edit(theme, placeholder=placeholder, min_height=min_height)
    if initial:
        field.setPlainText(initial)
    layout.addWidget(field)
    return holder, field


def labelled_combo(
    theme: Theme,
    *,
    label: str,
    options: Sequence[tuple[str, str]],
    initial_value: str = "",
) -> tuple[QFrame, ScrollSafeComboBox]:
    """Combo box with paired ``(value, label)`` tuples.

    ``initial_value`` matches one of the option values; the visible
    label is what the user sees. Returns the holder + combo so the
    caller can read ``combo.currentData()``.
    """
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    layout.addWidget(BodyLabel(label, theme=theme, size=12, weight=QFont.Weight.DemiBold))
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
    for value, item_label in options:
        combo.addItem(item_label, userData=value)
    if initial_value:
        for idx in range(combo.count()):
            if combo.itemData(idx) == initial_value:
                combo.setCurrentIndex(idx)
                break
    layout.addWidget(combo)
    return holder, combo


def disclaimer_pill(theme: Theme, *, label: str) -> QFrame:
    pill = QFrame()
    pill.setObjectName("FinanceDisclaimer")
    pill.setStyleSheet(
        f"""
        QFrame#FinanceDisclaimer {{
            background-color: {rgba("#F59E0B", 0.12)};
            border: 1px solid {rgba("#F59E0B", 0.36)};
            border-radius: 10px;
        }}
        """
    )
    layout = hbox(spacing=8, margins=(10, 6, 12, 6))
    pill.setLayout(layout)
    layout.addWidget(IconLabel(Icons.WARNING_AMBER_ROUNDED, color="#B45309", size=14))
    layout.addWidget(custom_label(label, color="#B45309", size=11, weight=QFont.Weight.DemiBold))
    return pill


def list_card(
    theme: Theme,
    *,
    title: str,
    items: Sequence[str],
    icon: str = Icons.CHECK_CIRCLE_OUTLINED,
    empty_label: str = "",
) -> QFrame:
    card, layout = section_card(theme)
    layout.addWidget(card_title(theme, title=title, icon=icon))
    if not items:
        if empty_label:
            layout.addWidget(MutedLabel(empty_label, theme=theme, size=12))
        return card
    for item in items:
        row = QFrame()
        row.setStyleSheet("background: transparent;")
        row_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
        row_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        row.setLayout(row_layout)
        row_layout.addWidget(IconLabel(icon, color=theme.primary, size=14))
        text_holder = QFrame()
        text_holder.setStyleSheet("background: transparent;")
        text_holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        text_layout = vbox(spacing=0, margins=(0, 0, 0, 0))
        text_holder.setLayout(text_layout)
        text_layout.addWidget(BodyLabel(str(item), theme=theme, size=13))
        row_layout.addWidget(text_holder, 1)
        layout.addWidget(row)
    return card


def amount_bar(theme: Theme, *, label: str, value: str, percent: float, color: str) -> QFrame:
    row = QFrame()
    row.setStyleSheet("background: transparent;")
    layout = hbox(spacing=12, margins=(0, 0, 0, 0))
    row.setLayout(layout)
    name_holder = QFrame()
    name_holder.setStyleSheet("background: transparent;")
    name_holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    name_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    name_holder.setLayout(name_layout)
    name_layout.addWidget(BodyLabel(label, theme=theme, size=12, weight=QFont.Weight.DemiBold))
    bar_track = QFrame()
    bar_track.setFixedHeight(6)
    bar_track.setStyleSheet(
        f"background-color: {theme.surface_2}; border-radius: 3px;"
    )
    bar_track_layout = QHBoxLayout(bar_track)
    bar_track_layout.setContentsMargins(0, 0, 0, 0)
    bar_track_layout.setSpacing(0)
    fill = QFrame()
    fill.setStyleSheet(f"background-color: {color}; border-radius: 3px;")
    fill.setFixedHeight(6)
    width_pct = max(0.0, min(100.0, float(percent)))
    bar_track_layout.addWidget(fill)
    fill.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    bar_track_layout.addStretch(int(max(0.0, 100.0 - width_pct)))
    # Workaround: stretch ratios give the right visual ratio.
    bar_track_layout.setStretchFactor(fill, int(width_pct) or 1)
    bar_track_layout.setStretch(1, int(max(1, 100 - width_pct)))
    name_layout.addWidget(bar_track)
    layout.addWidget(name_holder, 1)
    layout.addWidget(BodyLabel(value, theme=theme, size=12, weight=QFont.Weight.DemiBold))
    return row


def breakdown_table(theme: Theme, *, rows: Sequence[dict], currency: str, headers: Sequence[str]) -> QFrame:
    """Lightweight 4-col table used by Budget + Analysis tabs."""
    table = QFrame()
    table.setObjectName("FinanceTable")
    table.setStyleSheet(
        f"""
        QFrame#FinanceTable {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 10px;
        }}
        """
    )
    table_layout = vbox(spacing=0, margins=(10, 2, 10, 2))
    table.setLayout(table_layout)

    head = QFrame()
    head.setStyleSheet(f"background: transparent; border-bottom: 1px solid {theme.border};")
    head_grid = QGridLayout(head)
    head_grid.setContentsMargins(4, 8, 4, 8)
    head_grid.setHorizontalSpacing(8)
    head_grid.setColumnStretch(0, 4)
    head_grid.setColumnStretch(1, 2)
    head_grid.setColumnStretch(2, 3)
    head_grid.setColumnStretch(3, 4)
    for i, h in enumerate(headers):
        cell = MutedLabel(h, theme=theme, size=12)
        font = cell.font()
        font.setWeight(QFont.Weight.DemiBold)
        cell.setFont(font)
        head_grid.addWidget(cell, 0, i)
    table_layout.addWidget(head)

    for row in rows:
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

        color = _group_color(row.get("group", ""))
        cat_holder = QFrame()
        cat_holder.setStyleSheet("background: transparent;")
        cat_layout = hbox(spacing=6, margins=(0, 0, 0, 0))
        cat_holder.setLayout(cat_layout)
        cat_layout.addWidget(IconLabel(Icons.CIRCLE, color=color, size=10))
        cat_label = QLabel(str(row.get("category", "")))
        cat_font = QFont()
        cat_font.setPixelSize(12)
        cat_font.setWeight(QFont.Weight.DemiBold)
        cat_label.setFont(cat_font)
        cat_label.setStyleSheet(f"color: {theme.text}; background: transparent;")
        cat_layout.addWidget(cat_label, 1)
        grid.addWidget(cat_holder, 0, 0)

        grid.addWidget(
            BodyLabel(f"{row.get('percent', 0)}%", theme=theme, size=12),
            0, 1,
        )
        grid.addWidget(
            BodyLabel(
                f"{float(row.get('amount', 0)):,.0f} {currency}".replace(",", " "),
                theme=theme,
                size=12,
            ),
            0, 2,
        )
        grid.addWidget(MutedLabel(str(row.get("note", "")), theme=theme, size=12), 0, 3)
        table_layout.addWidget(row_box)
    return table


def scrollable_body(theme: Theme, widget: QWidget) -> QWidget:
    from PySide6.QtWidgets import QScrollArea  # local import - shared widgets

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(widget)
    return scroll


_RESPONSIVE_BREAKPOINT = 880


class ResponsiveColumns(QFrame):
    """Two-column container that collapses to a single column when narrow.

    Above the breakpoint (~880 px) the children sit side-by-side. Below
    the breakpoint they stack vertically so the donut chart / breakdown
    table / "results" view stays readable on narrow windows instead of
    being squashed into a thin half-column next to the form.

    Implementation detail: a single :class:`QGridLayout` holds both
    children. Switching orientation just re-positions them - we never
    detach / rebuild the layout, which sidesteps the "QWidget already
    has a layout" trap that ``setLayout(...)`` swaps would hit.
    """

    def __init__(
        self,
        *,
        spacing: int = 18,
        margins: tuple[int, int, int, int] = (0, 0, 0, 0),
        breakpoint_px: int = _RESPONSIVE_BREAKPOINT,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._children: list[QWidget] = []
        self._breakpoint = breakpoint_px
        self._is_horizontal: Optional[bool] = None
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(*margins)
        self._grid.setHorizontalSpacing(spacing)
        self._grid.setVerticalSpacing(spacing)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop)

    def add_column(self, widget: QWidget) -> None:
        """Append a child column. Stretch is shared evenly across columns."""
        self._children.append(widget)
        # Append into the grid in horizontal layout so resizeEvent can
        # later swap to vertical without leaving the widget unparented.
        self._grid.addWidget(widget, 0, len(self._children) - 1)
        self._is_horizontal = True
        self._apply_stretch(horizontal=True)

    def resizeEvent(self, event: QEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        if not self._children:
            return
        wants_horizontal = self.width() >= self._breakpoint
        if wants_horizontal == self._is_horizontal:
            return
        for index, widget in enumerate(self._children):
            self._grid.removeWidget(widget)
            if wants_horizontal:
                self._grid.addWidget(widget, 0, index)
            else:
                self._grid.addWidget(widget, index, 0)
        self._apply_stretch(horizontal=wants_horizontal)
        self._is_horizontal = wants_horizontal

    def _apply_stretch(self, *, horizontal: bool) -> None:
        # Reset every previous stretch so the orientation swap doesn't
        # leave row 0 stretched in column-mode (etc).
        for index in range(max(len(self._children), self._grid.rowCount())):
            self._grid.setRowStretch(index, 0)
            self._grid.setColumnStretch(index, 0)
        if horizontal:
            for index in range(len(self._children)):
                self._grid.setColumnStretch(index, 1)
        else:
            for index in range(len(self._children)):
                self._grid.setRowStretch(index, 0)


def responsive_two_columns(
    form: QWidget,
    result: QWidget,
    *,
    spacing: int = 18,
    breakpoint_px: int = _RESPONSIVE_BREAKPOINT,
) -> ResponsiveColumns:
    """Convenience helper: return a :class:`ResponsiveColumns` with two children."""
    cols = ResponsiveColumns(spacing=spacing, breakpoint_px=breakpoint_px)
    cols.add_column(form)
    cols.add_column(result)
    return cols


__all__ = [
    "DONUT_SIZE",
    "DonutChart",
    "ResponsiveColumns",
    "amount_bar",
    "breakdown_table",
    "budget_slices_from_plan",
    "card_title",
    "disclaimer_pill",
    "donut_with_caption",
    "labelled_combo",
    "labelled_line_edit",
    "labelled_text_edit",
    "legend_for_splits",
    "list_card",
    "responsive_two_columns",
    "scrollable_body",
    "section_card",
]
