"""QPainter chart widgets for AI Finance.

Tabs render structured pipeline outputs through a handful of small
QPainter widgets that turn list-of-dicts JSON into something the user
can scan visually:

* :class:`AllocationStackedBar` - stacked horizontal bar, one segment
  per asset class. Used by Investments to show the per-scenario asset
  mix without a heavy chart library.
* :class:`ProjectionSparkline` - smooth sparkline showing a 12-month
  compounding projection of an investment scenario. The pipeline
  doesn't ship the per-month series so we synthesise it from
  ``amount`` + ``expected_annual_return_pct`` (compound monthly).
* :class:`SeverityHeatmap` - grid of coloured pills per insurance
  coverage gap, organised by severity columns. Highlights "high" risks
  visually so the user can see which gaps deserve attention first.
* :class:`DeadlineTimeline` - horizontal timeline that distributes
  taxe deadlines across the next 12 calendar months.

All widgets use :func:`src.qt.theme.rgba` for hover-friendly tints and
honour the section ``Theme`` so the painted graphics blend with the
panel surface in both light and dark mode. They do NOT depend on
matplotlib / pyqtgraph - we want a single-file PyInstaller bundle.
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QFrame, QSizePolicy, QWidget

from src.qt.theme import rgba
from src.qt.widgets import BodyLabel, MutedLabel, SubtleLabel, custom_label, hbox, vbox
from src.theme import Theme


CHART_DEFAULT_HEIGHT = 36
SPARK_HEIGHT = 60
TIMELINE_HEIGHT = 80


# -- Allocation stacked bar -------------------------------------------


class AllocationStackedBar(QWidget):
    """Single horizontal bar split into asset-class segments.

    Each segment is the percentage allocated to one asset class. The
    widget paints labels above the bar (asset name + percentage) when
    space allows; very narrow segments only show the swatch. The
    rounded corners + 1px outline keep the bar legible against the
    surface colour in both themes.
    """

    def __init__(
        self,
        *,
        segments: list[tuple[str, float, str]],
        theme: Theme,
        height: int = CHART_DEFAULT_HEIGHT,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._segments = list(segments)
        self._theme = theme
        self.setFixedHeight(height)
        self.setMinimumWidth(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        radius = min(rect.height() / 2.0, 10.0)

        track = QColor(self._theme.surface_2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(rect, radius, radius)

        total = sum(max(0.0, p) for _name, p, _color in self._segments) or 1.0
        x = float(rect.x())
        for i, (_name, percent, color) in enumerate(self._segments):
            width = rect.width() * (max(0.0, percent) / total)
            if width <= 0.5:
                continue
            seg_rect = QRectF(x, rect.y(), width, rect.height())
            seg_color = QColor(color)
            gradient = QLinearGradient(seg_rect.topLeft(), seg_rect.bottomLeft())
            gradient.setColorAt(0.0, seg_color.lighter(108))
            gradient.setColorAt(1.0, seg_color)
            painter.setBrush(QBrush(gradient))
            if i == 0:
                # leftmost segment has a flat right edge if more
                # segments follow - draw a clipped rounded rect by
                # overpainting a smaller rect on the right
                painter.drawRoundedRect(seg_rect, radius, radius)
                if len(self._segments) > 1:
                    flat = QRectF(seg_rect.right() - radius, seg_rect.y(), radius, seg_rect.height())
                    painter.drawRect(flat)
            elif i == len(self._segments) - 1:
                painter.drawRoundedRect(seg_rect, radius, radius)
                flat = QRectF(seg_rect.x(), seg_rect.y(), radius, seg_rect.height())
                painter.drawRect(flat)
            else:
                painter.drawRect(seg_rect)
            x += width


def allocation_legend(
    theme: Theme,
    segments: list[tuple[str, float, str]],
) -> QFrame:
    """Render a small swatch+label legend for an allocation bar."""
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    for name, percent, color in segments:
        row = QFrame()
        row.setStyleSheet("background: transparent;")
        row_layout = hbox(spacing=6, margins=(0, 0, 0, 0))
        row_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        row.setLayout(row_layout)
        swatch = QFrame()
        swatch.setFixedSize(10, 10)
        swatch.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
        row_layout.addWidget(swatch)
        row_layout.addWidget(BodyLabel(name, theme=theme, size=11), 1)
        row_layout.addWidget(custom_label(f"{percent:.0f}%", color=theme.text_muted, size=11))
        layout.addWidget(row)
    return holder


# -- Projection sparkline ---------------------------------------------


class ProjectionSparkline(QWidget):
    """Compounding-return sparkline for an investment projection.

    Synthesises a per-month series from the scenario's annual return.
    We use monthly compounding so the curve is gently exponential
    rather than linear - matches the way users intuit "growth over
    time" without needing the pipeline to emit a 12-element series.
    """

    def __init__(
        self,
        *,
        amount: float,
        annual_return_pct: float,
        horizon_years: float,
        color: str,
        theme: Theme,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._amount = max(0.0, float(amount))
        self._color = QColor(color)
        self._theme = theme
        months = max(2, int(round(horizon_years * 12)))
        if months > 360:
            months = 360
        rate = float(annual_return_pct) / 100.0 / 12.0
        series: list[float] = []
        value = self._amount
        for _ in range(months):
            value *= (1.0 + rate)
            series.append(value)
        self._series = series or [self._amount]
        self.setFixedHeight(SPARK_HEIGHT)
        self.setMinimumWidth(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        # Frame fill
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self._theme.surface_2))
        painter.drawRoundedRect(rect, 8, 8)

        if len(self._series) < 2:
            return
        lo = min(self._series)
        hi = max(self._series)
        spread = max(1e-6, hi - lo)
        margin_x = 8.0
        margin_y = 10.0
        usable_w = max(1.0, rect.width() - 2 * margin_x)
        usable_h = max(1.0, rect.height() - 2 * margin_y)

        points: list[QPointF] = []
        for i, value in enumerate(self._series):
            x = margin_x + (i / (len(self._series) - 1)) * usable_w
            y = margin_y + usable_h - ((value - lo) / spread) * usable_h
            points.append(QPointF(x, y))

        # Soft gradient fill under the line
        from PySide6.QtGui import QPolygonF

        polygon = QPolygonF(points + [
            QPointF(points[-1].x(), rect.bottom() - 1),
            QPointF(points[0].x(), rect.bottom() - 1),
        ])
        gradient = QLinearGradient(0, rect.top(), 0, rect.bottom())
        soft = QColor(self._color)
        soft.setAlphaF(0.32)
        gradient.setColorAt(0.0, soft)
        soft2 = QColor(self._color)
        soft2.setAlphaF(0.0)
        gradient.setColorAt(1.0, soft2)
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(polygon)

        pen = QPen(self._color, 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i + 1])

        # End-of-series marker dot
        painter.setBrush(self._color)
        painter.setPen(Qt.PenStyle.NoPen)
        last = points[-1]
        painter.drawEllipse(last, 3.0, 3.0)


# -- Severity heatmap (insurance) -------------------------------------


_SEVERITY_BANDS = ("high", "medium", "low")


def severity_heatmap(
    theme: Theme,
    gaps: list[dict],
    *,
    high_label: str = "High",
    medium_label: str = "Medium",
    low_label: str = "Low",
) -> QFrame:
    """Three columns of severity-coloured pills (high / medium / low).

    Each gap becomes a pill in its severity column with the topic +
    risk text. Empty columns get an em-dash placeholder so all three
    columns stay aligned regardless of how many gaps the AI returned.
    """
    colors = {
        "high": "#EF4444",
        "medium": "#F59E0B",
        "low": "#22C55E",
    }
    labels = {"high": high_label, "medium": medium_label, "low": low_label}
    grouped: dict[str, list[dict]] = {sev: [] for sev in _SEVERITY_BANDS}
    for gap in gaps or []:
        sev = (gap.get("severity") or "low").lower()
        if sev not in grouped:
            sev = "low"
        grouped[sev].append(gap)

    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    holder.setLayout(layout)

    for sev in _SEVERITY_BANDS:
        col = QFrame()
        col.setStyleSheet("background: transparent;")
        col_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
        col.setLayout(col_layout)
        col_layout.addWidget(
            custom_label(labels[sev], color=colors[sev], size=11)
        )
        items = grouped[sev]
        if not items:
            placeholder = QFrame()
            placeholder.setStyleSheet(
                f"background-color: {theme.surface_2}; border-radius: 8px;"
            )
            ph_layout = vbox(spacing=0, margins=(8, 8, 8, 8))
            placeholder.setLayout(ph_layout)
            ph_layout.addWidget(MutedLabel("-", theme=theme, size=12))
            col_layout.addWidget(placeholder)
        else:
            for gap in items:
                pill = QFrame()
                pill.setStyleSheet(
                    f"background-color: {rgba(colors[sev], 0.16)};"
                    f" border: 1px solid {rgba(colors[sev], 0.32)};"
                    f" border-radius: 10px;"
                )
                pill_layout = vbox(spacing=2, margins=(10, 8, 10, 8))
                pill.setLayout(pill_layout)
                pill_layout.addWidget(
                    BodyLabel(
                        str(gap.get("topic", "") or ""),
                        theme=theme,
                        size=12,
                        weight=QFont.Weight.DemiBold,
                    )
                )
                pill_layout.addWidget(
                    SubtleLabel(
                        str(gap.get("risk", "") or ""),
                        theme=theme,
                        size=11,
                    )
                )
                col_layout.addWidget(pill)
        col_layout.addStretch(1)
        layout.addWidget(col, 1)
    return holder


# -- Deadline timeline (taxes) ----------------------------------------


class DeadlineTimeline(QWidget):
    """Horizontal timeline for tax deadlines across the next 12 months.

    The pipeline returns a free-form ``date_or_window`` string per
    deadline (e.g. "mid-March", "early April", "by 31 May 2026"). We
    parse the first month name we recognise to position the marker;
    deadlines without a recognisable month sit at the left edge. The
    label hovers above each marker, the date string below.
    """

    _MONTHS = (
        ("january", "leden", "led"),
        ("february", "unor", "uno"),
        ("march", "brezen", "bre"),
        ("april", "duben", "dub"),
        ("may", "kveten", "kve"),
        ("june", "cerven", "cer"),
        ("july", "cervenec", "cvc"),
        ("august", "srpen", "srp"),
        ("september", "zari", "zar"),
        ("october", "rijen", "rij"),
        ("november", "listopad", "lis"),
        ("december", "prosinec", "pro"),
    )

    def __init__(
        self,
        *,
        deadlines: list[dict],
        theme: Theme,
        accent: str = "#3B82F6",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._deadlines = list(deadlines or [])
        self._theme = theme
        self._accent = QColor(accent)
        self.setFixedHeight(TIMELINE_HEIGHT)
        self.setMinimumWidth(280)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _month_index(self, text: str) -> int:
        haystack = (text or "").lower()
        # Strip Czech diacritics so 'unor', 'brezen' etc. match.
        haystack = (
            haystack.replace("á", "a").replace("é", "e").replace("ě", "e")
            .replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ů", "u")
            .replace("š", "s").replace("č", "c").replace("ř", "r")
            .replace("ž", "z").replace("ý", "y")
        )
        for i, names in enumerate(self._MONTHS):
            for n in names:
                if n in haystack:
                    return i
        return -1

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        margin_x = 16.0
        baseline = rect.top() + rect.height() * 0.55
        track_left = rect.left() + margin_x
        track_right = rect.right() - margin_x
        usable_w = max(1.0, track_right - track_left)

        # Track line
        pen = QPen(QColor(self._theme.surface_2), 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(track_left, baseline), QPointF(track_right, baseline))

        # Month tick marks (4 tick marks at quarter boundaries)
        tick_pen = QPen(QColor(self._theme.border), 1.0)
        painter.setPen(tick_pen)
        for q in range(5):
            x = track_left + (q / 4.0) * usable_w
            painter.drawLine(QPointF(x, baseline - 4), QPointF(x, baseline + 4))

        # Markers
        font = self.font()
        font.setPointSize(9)
        metrics = QFontMetrics(font)
        for d in self._deadlines:
            label = str(d.get("label", "") or "")
            window = str(d.get("date_or_window", "") or "")
            month_idx = self._month_index(window)
            if month_idx < 0:
                month_idx = self._month_index(label)
            if month_idx < 0:
                month_idx = 0
            x = track_left + (month_idx / 11.0) * usable_w if month_idx > 0 else track_left
            x = min(track_right, max(track_left, x))

            # Marker dot
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._accent)
            painter.drawEllipse(QPointF(x, baseline), 5.0, 5.0)
            painter.setBrush(QColor(self._theme.surface))
            painter.drawEllipse(QPointF(x, baseline), 2.0, 2.0)

            # Label above
            painter.setFont(font)
            painter.setPen(QColor(self._theme.text))
            label_w = metrics.horizontalAdvance(label)
            label_x = max(track_left, min(track_right - label_w, x - label_w / 2.0))
            painter.drawText(QPointF(label_x, baseline - 12), label)

            # Window below in muted colour
            painter.setPen(QColor(self._theme.text_muted))
            window_w = metrics.horizontalAdvance(window)
            window_x = max(track_left, min(track_right - window_w, x - window_w / 2.0))
            painter.drawText(QPointF(window_x, baseline + 22), window)


__all__ = [
    "AllocationStackedBar",
    "DeadlineTimeline",
    "ProjectionSparkline",
    "allocation_legend",
    "severity_heatmap",
    "CHART_DEFAULT_HEIGHT",
    "SPARK_HEIGHT",
    "TIMELINE_HEIGHT",
]
