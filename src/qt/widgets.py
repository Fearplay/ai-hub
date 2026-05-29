"""Reusable Qt widgets that mirror the Flet primitives we used to lean on.

Every section / component module imports the building blocks here
instead of dealing with raw ``QWidget`` / ``QLabel`` / ``QFrame`` and
hand-rolled QSS. The widgets keep their styling local so a theme switch
can re-emit only the global QSS without rebuilding every control.

The naming intentionally mirrors what we used to do with Flet:

* ``Card`` plays the role of ``ft.Container(bgcolor=..., border_radius=..., border=...)``
* ``IconLabel`` plays the role of ``ft.Icon(...)``
* ``BodyLabel`` / ``MutedLabel`` / ``TitleLabel`` / ``SubtleLabel`` /
  ``PillLabel`` cover the typography helpers we used to inline as
  ``ft.Text(..., color=theme.X, size=..., weight=ft.FontWeight.W_X)``
* ``PrimaryButton`` / ``GhostButton`` / ``DangerButton`` /
  ``IconButton`` cover the three button looks the screenshots use
* ``Pill`` is the small rounded coloured chip used for status badges
* ``HSeparator`` / ``VSeparator`` are 1 px dividers

Pure styling. No business logic. Sections wire callbacks via the Qt
``clicked`` signal these widgets expose.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QFont, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLayoutItem,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.qt.icons import Icons, icon_pixmap
from src.qt.theme import rgba
from src.theme import Theme


# --- typography -------------------------------------------------------------


class _WrapAwareLabel(QLabel):
    """QLabel variant whose height follows wrapped text reliably."""

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return self.wordWrap()

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        if not self.wordWrap():
            return super().heightForWidth(width)
        margins = self.contentsMargins()
        usable_width = max(1, width - margins.left() - margins.right())
        flags = (
            Qt.AlignmentFlag.AlignLeft.value
            | Qt.AlignmentFlag.AlignTop.value
            | Qt.TextFlag.TextWordWrap.value
        )
        rect = self.fontMetrics().boundingRect(
            0,
            0,
            usable_width,
            10000,
            flags,
            self.text(),
        )
        return rect.height() + margins.top() + margins.bottom() + 2

    def sizeHint(self) -> QSize:  # noqa: N802
        hint = super().sizeHint()
        if self.wordWrap() and self.width() > 0:
            hint.setHeight(max(hint.height(), self.heightForWidth(self.width())))
        return hint

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        hint = super().minimumSizeHint()
        if self.wordWrap():
            hint.setHeight(max(hint.height(), self.fontMetrics().lineSpacing() + 2))
        return hint


def _coerce_weight(weight: int | QFont.Weight) -> QFont.Weight:
    """Accept either ``QFont.Weight`` enum or a plain int (Flet-style 100..900)."""
    if isinstance(weight, QFont.Weight):
        return weight
    return QFont.Weight(int(weight))


def _make_label(
    text: str,
    *,
    color: str,
    size: int,
    weight: int | QFont.Weight = QFont.Weight.Normal,
    italic: bool = False,
    selectable: bool = False,
) -> QLabel:
    label = _WrapAwareLabel(text)
    font = QFont()
    font.setPixelSize(size)
    font.setWeight(_coerce_weight(weight))
    font.setItalic(italic)
    label.setFont(font)
    label.setStyleSheet(f"color: {color}; background: transparent;")
    label.setWordWrap(True)
    policy = QSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Preferred,
    )
    policy.setHeightForWidth(True)
    label.setSizePolicy(policy)
    label.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse
        if selectable
        else Qt.TextInteractionFlag.NoTextInteraction
    )
    return label


def BodyLabel(
    text: str,
    *,
    theme: Theme,
    size: int = 13,
    weight: int = QFont.Weight.Normal,
    selectable: bool = False,
) -> QLabel:
    return _make_label(
        text,
        color=theme.text,
        size=size,
        weight=weight,
        selectable=selectable,
    )


def TitleLabel(
    text: str,
    *,
    theme: Theme,
    size: int = 15,
    weight: int = QFont.Weight.DemiBold,
) -> QLabel:
    return _make_label(text, color=theme.text, size=size, weight=weight)


def MutedLabel(
    text: str,
    *,
    theme: Theme,
    size: int = 12,
    weight: int | QFont.Weight = QFont.Weight.Normal,
    italic: bool = False,
    selectable: bool = False,
) -> QLabel:
    return _make_label(
        text,
        color=theme.text_muted,
        size=size,
        weight=weight,
        italic=italic,
        selectable=selectable,
    )


def SubtleLabel(
    text: str,
    *,
    theme: Theme,
    size: int = 11,
    weight: int | QFont.Weight = QFont.Weight.Normal,
    italic: bool = False,
    selectable: bool = False,
) -> QLabel:
    return _make_label(
        text,
        color=theme.text_subtle,
        size=size,
        weight=weight,
        italic=italic,
        selectable=selectable,
    )


class ElidedLabel(QLabel):
    """``QLabel`` that ellides (``...``) when the available width is too small.

    The default :class:`QLabel` clips the trailing characters when the
    text overflows; we want a ``...\\path\\to\\file`` look for long
    file paths in history rows and similar narrow strips. Set
    ``mode`` to switch between elide-left / elide-middle / elide-right
    (defaults to ``ElideMiddle`` which matches the Flet original).
    """

    def __init__(
        self,
        text: str,
        *,
        color: str,
        size: int,
        weight: int | QFont.Weight = QFont.Weight.Normal,
        italic: bool = False,
        mode: Qt.TextElideMode = Qt.TextElideMode.ElideMiddle,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._full_text = text
        self._mode = mode
        font = QFont()
        font.setPixelSize(size)
        font.setWeight(_coerce_weight(weight))
        font.setItalic(italic)
        self.setFont(font)
        self.setStyleSheet(f"color: {color}; background: transparent;")
        self.setWordWrap(False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.setText(text)

    def setText(self, text: str) -> None:  # noqa: N802
        self._full_text = text or ""
        self._update_elided()

    def setEliding(self, mode: Qt.TextElideMode) -> None:  # noqa: N802
        self._mode = mode
        self._update_elided()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_elided()

    def _update_elided(self) -> None:
        from PySide6.QtGui import QFontMetrics
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self._full_text, self._mode, max(self.width() - 4, 16))
        super().setText(elided)
        self.setToolTip(self._full_text)


class ClampLabel(QLabel):
    """Word-wrapping ``QLabel`` clamped to a fixed number of lines.

    Where :class:`ElidedLabel` keeps text on a single line, this keeps
    it on at most ``lines`` rows: the text wraps normally and the final
    visible row is truncated with an ellipsis when it does not fit.
    Used for card descriptions that must stay a uniform height so a grid
    of cards lines up cleanly (e.g. the Dashboard module tiles) instead
    of a short blurb leaving a tall sibling card half-empty.

    The wrap points depend on the available width, so the clamp is
    recomputed on every resize. The height is fixed up-front to ``lines``
    rows so the surrounding layout reserves exactly that much room and
    sibling cards in the same grid row share one height. Like
    :class:`ElidedLabel` this is the one sanctioned exception to the
    "labels go through ``_make_label``" rule because it manages its own
    wrapping (qt-text rule 1).
    """

    def __init__(
        self,
        text: str,
        *,
        color: str,
        size: int,
        lines: int = 2,
        weight: int | QFont.Weight = QFont.Weight.Normal,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._full_text = text or ""
        self._lines = max(1, lines)
        font = QFont()
        font.setPixelSize(size)
        font.setWeight(_coerce_weight(weight))
        self.setFont(font)
        self.setStyleSheet(f"color: {color}; background: transparent;")
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.setIndent(0)
        self.setMargin(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # Reserve a touch more than ``lines * lineSpacing``: some fonts lay
        # wrapped lines out slightly taller than ``lineSpacing`` reports, which
        # clips the descenders of the final row right above whatever sits below
        # the label. The small pad costs nothing visually but kills the clip.
        metrics = self.fontMetrics()
        self.setFixedHeight(metrics.lineSpacing() * self._lines + metrics.descent() + 2)
        self._relayout()

    def setText(self, text: str) -> None:  # noqa: N802
        self._full_text = text or ""
        self._relayout()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self) -> None:
        metrics = self.fontMetrics()
        width = max(1, self.width())
        words = self._full_text.split()
        if not words:
            super().setText("")
            self.setToolTip("")
            return
        rows: list[str] = []
        current = ""
        index = 0
        total = len(words)
        while index < total and len(rows) < self._lines:
            word = words[index]
            trial = word if not current else f"{current} {word}"
            if metrics.horizontalAdvance(trial) <= width or not current:
                current = trial
                index += 1
                if index == total:
                    rows.append(current)
                    current = ""
            else:
                rows.append(current)
                current = ""
        truncated = index < total
        if truncated and rows:
            leftover = " ".join(words[index:])
            rows[-1] = metrics.elidedText(
                f"{rows[-1]} {leftover}", Qt.TextElideMode.ElideRight, width
            )
        elif rows and metrics.horizontalAdvance(rows[-1]) > width:
            rows[-1] = metrics.elidedText(
                rows[-1], Qt.TextElideMode.ElideRight, width
            )
        super().setText("\n".join(rows))
        self.setToolTip(self._full_text if truncated else "")


def AccentLabel(
    text: str, *, theme: Theme, size: int = 12, weight: int = QFont.Weight.DemiBold
) -> QLabel:
    return _make_label(text, color=theme.primary, size=size, weight=weight)


def custom_label(
    text: str,
    *,
    color: str,
    size: int = 13,
    weight: int = QFont.Weight.Normal,
    italic: bool = False,
    selectable: bool = False,
) -> QLabel:
    return _make_label(
        text,
        color=color,
        size=size,
        weight=weight,
        italic=italic,
        selectable=selectable,
    )


# --- icons ------------------------------------------------------------------


class IconLabel(QLabel):
    """Single MDI6 icon rendered as a ``QPixmap`` via QtAwesome.

    Acts like ``ft.Icon(name, color=..., size=...)``: pass the icon
    name (from :class:`src.qt.icons.Icons`), a colour, and a pixel
    size. The colour is baked into the pixmap by QtAwesome, so any
    state mutation (active / hover / theme switch) re-rasterises the
    icon - cheap because the underlying font glyph is cached inside
    QtAwesome's icon engine.

    The ``size + 6`` fixed box matches the pre-migration text-glyph
    label so existing row layouts (sidebar, header, chat bubbles)
    keep their spacing without retuning every container.
    """

    def __init__(
        self,
        name: str,
        *,
        color: str,
        size: int = 18,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._name = name
        self._color = color
        self._size = size
        self.setStyleSheet("background: transparent;")
        self.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)
        self.setFixedSize(size + 6, size + 6)
        self._refresh()

    def _refresh(self) -> None:
        if self._name:
            self.setPixmap(
                icon_pixmap(self._name, color=self._color, size=self._size)
            )
        else:
            self.setPixmap(QPixmap())

    def set_color(self, color: str) -> None:
        if color == self._color:
            return
        self._color = color
        self._refresh()

    def set_icon(self, name: str) -> None:
        if name == self._name:
            return
        self._name = name
        self._refresh()

    def set_size(self, size: int) -> None:
        if size == self._size:
            return
        self._size = size
        self.setFixedSize(size + 6, size + 6)
        self._refresh()


# --- containers / cards -----------------------------------------------------


def vbox(spacing: int = 0, margins: tuple[int, int, int, int] = (0, 0, 0, 0)) -> QVBoxLayout:
    layout = QVBoxLayout()
    layout.setSpacing(spacing)
    layout.setContentsMargins(*margins)
    return layout


def hbox(spacing: int = 0, margins: tuple[int, int, int, int] = (0, 0, 0, 0)) -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.setSpacing(spacing)
    layout.setContentsMargins(*margins)
    return layout


class FlowLayout(QLayout):
    """Auto-wrapping flow layout (Qt's canonical Python example).

    Used for chip rows / tag clouds / quick-action ribbons that should
    wrap to a second line on narrow widths instead of overflowing the
    parent. Mirrors the official PySide flow-layout sample so behaviour
    matches what users intuitively expect from CSS flex-wrap.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        margin: int = 0,
        h_spacing: int = 8,
        v_spacing: int = 8,
    ) -> None:
        super().__init__(parent)
        if parent is None:
            self.setContentsMargins(margin, margin, margin, margin)
        self._items: list[QLayoutItem] = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing

    def __del__(self) -> None:
        item = self.takeAt(0)
        while item is not None:
            item = self.takeAt(0)

    def addItem(self, item: QLayoutItem) -> None:  # noqa: N802
        self._items.append(item)

    def horizontalSpacing(self) -> int:  # noqa: N802
        if self._h_spacing >= 0:
            return self._h_spacing
        return self._smart_spacing(QStyle.PixelMetric.PM_LayoutHorizontalSpacing)

    def verticalSpacing(self) -> int:  # noqa: N802
        if self._v_spacing >= 0:
            return self._v_spacing
        return self._smart_spacing(QStyle.PixelMetric.PM_LayoutVerticalSpacing)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> Optional[QLayoutItem]:  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> Optional[QLayoutItem]:  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:  # noqa: N802
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: N802
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(
            margins.left() + margins.right(),
            margins.top() + margins.bottom(),
        )
        return size

    def _do_layout(self, rect: QRect, *, test_only: bool) -> int:
        margins = self.contentsMargins()
        effective = rect.adjusted(
            margins.left(),
            margins.top(),
            -margins.right(),
            -margins.bottom(),
        )
        x = effective.x()
        y = effective.y()
        line_height = 0
        for item in self._items:
            wid = item.widget()
            space_x = self.horizontalSpacing()
            space_y = self.verticalSpacing()
            if wid is not None:
                space_x = max(
                    space_x,
                    wid.style().layoutSpacing(
                        QSizePolicy.ControlType.PushButton,
                        QSizePolicy.ControlType.PushButton,
                        Qt.Orientation.Horizontal,
                    ),
                )
                space_y = max(
                    space_y,
                    wid.style().layoutSpacing(
                        QSizePolicy.ControlType.PushButton,
                        QSizePolicy.ControlType.PushButton,
                        Qt.Orientation.Vertical,
                    ),
                )
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > effective.right() and line_height > 0:
                x = effective.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        return y + line_height - rect.y() + margins.bottom()

    def _smart_spacing(self, pm: QStyle.PixelMetric) -> int:
        parent = self.parent()
        if parent is None:
            return -1
        if parent.isWidgetType():
            return parent.style().pixelMetric(pm, None, parent)
        return parent.spacing()  # type: ignore[attr-defined]


class Card(QFrame):
    """Rounded surface with optional border + bg, used everywhere.

    Replaces the ``ft.Container(bgcolor=..., border_radius=...,
    border=ft.border.all(1, theme.border), padding=...)`` pattern
    that recurred all over the Flet code. Pass theme tokens for bg /
    border so light <-> dark switches just need to call
    :meth:`apply_theme` again.
    """

    def __init__(
        self,
        *,
        bg: str,
        border_color: Optional[str] = None,
        radius: int = 12,
        padding: tuple[int, int, int, int] = (16, 16, 16, 16),
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._bg = bg
        self._border_color = border_color
        self._radius = radius
        self._content_layout = vbox(spacing=8, margins=padding)
        self.setLayout(self._content_layout)
        self._apply()
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

    def _apply(self) -> None:
        border = (
            f"border: 1px solid {self._border_color};"
            if self._border_color
            else "border: none;"
        )
        self.setStyleSheet(
            f"""
            Card {{
                background-color: {self._bg};
                {border}
                border-radius: {self._radius}px;
            }}
            """
        )

    def apply_theme(self, *, bg: str, border_color: Optional[str], radius: Optional[int] = None) -> None:
        self._bg = bg
        self._border_color = border_color
        if radius is not None:
            self._radius = radius
        self._apply()

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._content_layout


class ClickFrame(QFrame):
    """``QFrame`` that emits ``clicked`` on mouse release.

    Used for nav rows, sidebar entries, action chips, and any other
    Flet ``ft.Container(ink=True, on_click=...)`` look-alike.
    """

    clicked = Signal()
    hovered = Signal(bool)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self._enabled_click = True

    def set_clickable(self, enabled: bool) -> None:
        self._enabled_click = enabled
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
            if enabled
            else Qt.CursorShape.ArrowCursor
        )

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if (
            self._enabled_click
            and event.button() == Qt.MouseButton.LeftButton
            and self.rect().contains(event.position().toPoint())
        ):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def enterEvent(self, event) -> None:  # noqa: N802
        self.hovered.emit(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.hovered.emit(False)
        super().leaveEvent(event)


# --- pills ------------------------------------------------------------------


class Pill(QFrame):
    """Rounded coloured chip used for status pills, badges, demo flags.

    Builds a small ``QFrame`` with optional left icon + label.
    Re-styling happens by replacing the stylesheet, so a status
    transition (idle -> ok -> error) is a one-call mutation.
    """

    def __init__(
        self,
        *,
        text: str,
        bg: str,
        fg: str,
        icon: Optional[str] = None,
        icon_size: int = 14,
        radius: int = 10,
        padding: tuple[int, int, int, int] = (4, 8, 4, 8),
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Pill")
        self._row = hbox(spacing=6, margins=padding)
        self.setLayout(self._row)
        self._icon_label: Optional[IconLabel] = None
        if icon:
            self._icon_label = IconLabel(icon, color=fg, size=icon_size)
            self._row.addWidget(self._icon_label)
        font = QFont()
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.DemiBold)
        self._text_label = QLabel(text)
        self._text_label.setFont(font)
        self._text_label.setStyleSheet(f"color: {fg}; background: transparent;")
        self._row.addWidget(self._text_label)
        self.setStyleSheet(
            f"""
            QFrame#Pill {{
                background-color: {bg};
                border-radius: {radius}px;
            }}
            """
        )
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)

    def set_text(self, text: str) -> None:
        self._text_label.setText(text)

    def set_palette(self, *, bg: str, fg: str, icon: Optional[str] = None) -> None:
        self._text_label.setStyleSheet(f"color: {fg}; background: transparent;")
        self.setStyleSheet(
            f"""
            QFrame#Pill {{
                background-color: {bg};
                border-radius: 10px;
            }}
            """
        )
        if icon and self._icon_label is not None:
            self._icon_label.set_icon(icon)
            self._icon_label.set_color(fg)


def status_pill(theme: Theme, *, ok: bool, label: str) -> Pill:
    color = "#22C55E" if ok else theme.text_muted
    return Pill(
        text=label,
        bg=rgba(color, 0.12),
        fg=color,
        icon=Icons.CHECK_CIRCLE if ok else Icons.RADIO_BUTTON_UNCHECKED,
    )


# --- buttons ----------------------------------------------------------------


class _BaseTextButton(QPushButton):
    # Horizontal padding (left + right) baked into the QSS, used by sizeHint.
    _PAD_H = 28
    # Vertical padding (top + bottom) baked into the QSS, used by sizeHint.
    _PAD_V = 16

    def __init__(
        self,
        text: str,
        *,
        bg: str,
        fg: str,
        bg_hover: str,
        border_color: Optional[str] = None,
        icon: Optional[str] = None,
        icon_size: int = 14,
        radius: int = 10,
        padding: str = "8px 14px",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        self.setText("")
        layout = hbox(spacing=6, margins=(0, 0, 0, 0))
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._inner = QWidget(self)
        self._inner.setLayout(layout)
        self._inner.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._inner.setStyleSheet("background: transparent;")
        outer = hbox(spacing=0, margins=(0, 0, 0, 0))
        outer.addWidget(self._inner)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(outer)

        if icon:
            self._icon = IconLabel(icon, color=fg, size=icon_size)
            layout.addWidget(self._icon)
        else:
            self._icon = None

        if text:
            label = QLabel(text)
            font = QFont()
            font.setPixelSize(12)
            font.setWeight(QFont.Weight.DemiBold)
            label.setFont(font)
            label.setStyleSheet(f"color: {fg}; background: transparent;")
            layout.addWidget(label)
            self._label = label
        else:
            self._label = None

        border_rule = (
            f"border: 1px solid {border_color};"
            if border_color
            else "border: none;"
        )
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {bg};
                {border_rule}
                border-radius: {radius}px;
                padding: {padding};
                color: {fg};
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {bg_hover};
            }}
            QPushButton:focus {{
                outline: none;
            }}
            QPushButton:disabled {{
                background-color: {bg};
                color: {fg};
            }}
            """
        )

    def set_label(self, text: str) -> None:
        if self._label is not None:
            self._label.setText(text)
            self.updateGeometry()

    def setText(self, text: str) -> None:  # noqa: N802
        # Override so callers using the standard QPushButton API still
        # update the visible label (and trigger a relayout).
        if getattr(self, "_label", None) is not None and text:
            self._label.setText(text)
            self.updateGeometry()
            return
        super().setText(text)

    def sizeHint(self) -> QSize:  # noqa: N802
        # QPushButton's default sizeHint is computed from its native text +
        # icon, which is empty here because we render the label inside an
        # inner QWidget. Delegate to the inner widget so the button is wide
        # enough for the actual content + the QSS padding.
        inner = getattr(self, "_inner", None)
        if inner is not None:
            hint = inner.sizeHint()
            return QSize(hint.width() + self._PAD_H, hint.height() + self._PAD_V)
        return super().sizeHint()

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return self.sizeHint()


def PrimaryButton(
    text: str,
    *,
    theme: Theme,
    icon: Optional[str] = None,
    parent: Optional[QWidget] = None,
) -> QPushButton:
    return _BaseTextButton(
        text,
        bg=theme.primary,
        fg="#FFFFFF",
        bg_hover=theme.primary_hover,
        icon=icon,
        parent=parent,
    )


def GhostButton(
    text: str,
    *,
    theme: Theme,
    icon: Optional[str] = None,
    parent: Optional[QWidget] = None,
) -> QPushButton:
    return _BaseTextButton(
        text,
        bg=theme.surface,
        fg=theme.text,
        bg_hover=theme.surface_2,
        border_color=theme.border,
        icon=icon,
        parent=parent,
    )


def SecondaryButton(
    text: str,
    *,
    theme: Theme,
    icon: Optional[str] = None,
    parent: Optional[QWidget] = None,
) -> QPushButton:
    return _BaseTextButton(
        text,
        bg=theme.surface_2,
        fg=theme.text,
        bg_hover=rgba(theme.primary, 0.12),
        border_color=theme.border,
        icon=icon,
        parent=parent,
    )


def DangerButton(
    text: str,
    *,
    theme: Theme,
    icon: Optional[str] = None,
    parent: Optional[QWidget] = None,
) -> QPushButton:
    return _BaseTextButton(
        text,
        bg=rgba("#EF4444", 0.10),
        fg="#EF4444",
        bg_hover=rgba("#EF4444", 0.20),
        border_color=rgba("#EF4444", 0.40),
        icon=icon,
        parent=parent,
    )


class IconOnlyButton(QToolButton):
    """Square button rendering only an icon glyph.

    Wraps ``QToolButton`` so we can apply hover styling via QSS without
    the default Qt button chrome. The glyph is rendered through a
    centred :class:`IconLabel` child instead of ``QToolButton``'s
    native text drawing — Material Symbols glyphs sit slightly higher
    in their em-box than what ``QToolButton`` assumes, so the native
    path looked optically shifted up-left. The inner ``IconLabel``
    layout is ``AlignCenter`` so the highlight is always centred no
    matter the button size.
    """

    def __init__(
        self,
        name: str,
        *,
        color: str,
        size: int = 18,
        bg: str = "transparent",
        bg_hover: Optional[str] = None,
        radius: int = 8,
        tooltip: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Suppress the native text rendering entirely - the glyph is
        # drawn by the inner IconLabel below.
        self.setText("")
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        self.setFixedSize(size + 14, size + 14)
        self.setToolTip(tooltip)
        self.setAttribute(Qt.WidgetAttribute.WA_LayoutUsesWidgetRect, True)

        inner = IconLabel(name, color=color, size=size, parent=self)
        inner.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(inner, 0, Qt.AlignmentFlag.AlignCenter)
        self._inner_icon = inner

        hover_rule = (
            f"QToolButton:hover {{ background-color: {bg_hover}; }}"
            if bg_hover
            else ""
        )
        self.setStyleSheet(
            f"""
            QToolButton {{
                background-color: {bg};
                color: {color};
                border: none;
                border-radius: {radius}px;
            }}
            QToolButton:disabled {{
                background-color: {bg};
            }}
            {hover_rule}
            """
        )

    def set_icon_color(self, color: str) -> None:
        """Update the inner glyph colour without rebuilding the button."""
        if hasattr(self, "_inner_icon"):
            self._inner_icon.set_color(color)


# --- inputs -----------------------------------------------------------------


def themed_line_edit(
    theme: Theme,
    *,
    placeholder: str = "",
    password: bool = False,
    parent: Optional[QWidget] = None,
) -> QLineEdit:
    edit = QLineEdit(parent)
    edit.setPlaceholderText(placeholder)
    if password:
        edit.setEchoMode(QLineEdit.EchoMode.Password)
    edit.setStyleSheet(
        f"""
        QLineEdit {{
            background-color: {theme.surface_2};
            color: {theme.text};
            border: 1px solid transparent;
            border-radius: 10px;
            padding: 10px 12px;
            selection-background-color: {rgba(theme.primary, 0.30)};
        }}
        QLineEdit:focus {{
            border: 1px solid {rgba(theme.primary, 0.45)};
        }}
        QLineEdit:disabled {{
            color: {theme.text_muted};
        }}
        """
    )
    return edit


def themed_text_edit(
    theme: Theme,
    *,
    placeholder: str = "",
    min_height: int = 80,
    parent: Optional[QWidget] = None,
) -> QPlainTextEdit:
    edit = QPlainTextEdit(parent)
    edit.setPlaceholderText(placeholder)
    edit.setMinimumHeight(min_height)
    edit.setStyleSheet(
        f"""
        QPlainTextEdit {{
            background-color: {theme.surface_2};
            color: {theme.text};
            border: 1px solid transparent;
            border-radius: 10px;
            padding: 10px 12px;
            selection-background-color: {rgba(theme.primary, 0.30)};
        }}
        QPlainTextEdit:focus {{
            border: 1px solid {rgba(theme.primary, 0.45)};
        }}
        """
    )
    return edit


# --- scroll-safe pickers ----------------------------------------------------


class ScrollSafeComboBox(QComboBox):
    """``QComboBox`` that ignores mouse-wheel events.

    Qt's default ``QComboBox.wheelEvent`` cycles through the selected
    item when the user hovers the field and turns the wheel. Inside the
    AI Hub the combo box is usually parked inside a scroll area (the
    Setup tab for AI Jobs, the meta row in AI Bug Report, every select
    field in AI Finance) so any incidental wheel motion silently
    mutates a setting instead of scrolling the page - the user's
    "Lokalita" jumps from Brno to Praha while they think they are
    paging down. Ignoring the event lets the parent ``QScrollArea``
    handle the scroll exactly as the user expects.
    """

    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()


class ScrollSafeSpinBox(QSpinBox):
    """``QSpinBox`` that ignores mouse-wheel events.

    Same rationale as :class:`ScrollSafeComboBox` - "Max výsledků" /
    other numeric pickers must not silently increment when the user
    scrolls the surrounding form.
    """

    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()


# --- separators -------------------------------------------------------------


class HSeparator(QFrame):
    def __init__(self, theme: Theme, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setStyleSheet(f"color: {theme.border}; background: {theme.border};")
        self.setFixedHeight(1)


class VSeparator(QFrame):
    def __init__(self, theme: Theme, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setStyleSheet(f"color: {theme.border}; background: {theme.border};")
        self.setFixedWidth(1)


# --- helpers ----------------------------------------------------------------


def fade_effect(widget: QWidget, opacity: float = 0.5) -> QGraphicsOpacityEffect:
    eff = QGraphicsOpacityEffect()
    eff.setOpacity(opacity)
    widget.setGraphicsEffect(eff)
    return eff


def expanding(widget: QWidget) -> QWidget:
    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    return widget


def expanding_h(widget: QWidget) -> QWidget:
    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    return widget


def wrap_label_slot(widget: QWidget) -> QWidget:
    """Mark a container as the expanding text slot in an icon+text+icon row.

    Whenever a wrap-prone label lives inside a ``QFrame`` that sits in a
    horizontal row next to fixed-size siblings (badges, status icons),
    that frame must be allowed to grow horizontally **and** report a
    height that follows the wrapped content. Without this the row
    collapses to the unwrapped single-line height and the second line
    overlaps the sibling icons.

    We also flip ``heightForWidth`` on the size policy: by default
    ``QHBoxLayout`` does not honor a child's ``heightForWidth`` even
    when the child has ``setWordWrap(True)``, which clips the second
    line of long descriptions ("Povolit vyhledávání na webu v AI chatu"
    in Settings, "Předchozí hledání" subtitle in AI Jobs History, …).
    Setting the bit forces the parent layout to ask the child how tall
    it wants to be at the current width and the wrap survives.

    See `.cursor/rules/qt-text.mdc` rule 3 ("the label slot must be
    Expanding / Preferred"). Use this helper instead of inlining the
    policy so a single grep finds every label slot in the app.
    """
    policy = QSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
    )
    policy.setHeightForWidth(True)
    widget.setSizePolicy(policy)
    return widget


def expanding_v(widget: QWidget) -> QWidget:
    widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
    return widget


def stretch_spacer() -> QWidget:
    """An empty expanding widget useful as a layout spacer."""
    spacer = QWidget()
    spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    return spacer


__all__ = [
    "AccentLabel",
    "BodyLabel",
    "Card",
    "ClampLabel",
    "ClickFrame",
    "DangerButton",
    "GhostButton",
    "HSeparator",
    "IconLabel",
    "IconOnlyButton",
    "MutedLabel",
    "Pill",
    "PrimaryButton",
    "ScrollSafeComboBox",
    "ScrollSafeSpinBox",
    "SecondaryButton",
    "SubtleLabel",
    "TitleLabel",
    "VSeparator",
    "custom_label",
    "expanding",
    "expanding_h",
    "expanding_v",
    "fade_effect",
    "hbox",
    "status_pill",
    "stretch_spacer",
    "themed_line_edit",
    "themed_text_edit",
    "vbox",
    "wrap_label_slot",
]
