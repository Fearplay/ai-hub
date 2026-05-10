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

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFont, QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.qt.icons import glyph, icon_font
from src.qt.theme import rgba
from src.theme import Theme


# --- typography -------------------------------------------------------------


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
    label = QLabel(text)
    font = QFont()
    font.setPixelSize(size)
    font.setWeight(_coerce_weight(weight))
    font.setItalic(italic)
    label.setFont(font)
    label.setStyleSheet(f"color: {color}; background: transparent;")
    label.setWordWrap(True)
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
) -> QLabel:
    return _make_label(
        text, color=theme.text_muted, size=size, weight=weight, italic=italic
    )


def SubtleLabel(
    text: str,
    *,
    theme: Theme,
    size: int = 11,
    weight: int | QFont.Weight = QFont.Weight.Normal,
    italic: bool = False,
) -> QLabel:
    return _make_label(
        text, color=theme.text_subtle, size=size, weight=weight, italic=italic
    )


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
    """Single Material Icons glyph rendered with the bundled font.

    Acts like ``ft.Icon(name, color=..., size=...)``: pass the icon
    name (from :class:`src.qt.icons.Icons`), a colour, and a pixel
    size. The colour is applied via QSS so the icon repaints without
    the parent having to call ``update()``.
    """

    def __init__(
        self,
        name: str,
        *,
        color: str,
        size: int = 18,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(glyph(name), parent)
        self._color = color
        self._size = size
        self.setFont(icon_font(size))
        self.setStyleSheet(f"color: {color}; background: transparent;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(size + 4, size + 4)

    def set_color(self, color: str) -> None:
        if color == self._color:
            return
        self._color = color
        self.setStyleSheet(f"color: {color}; background: transparent;")

    def set_icon(self, name: str) -> None:
        self.setText(glyph(name))

    def set_size(self, size: int) -> None:
        if size == self._size:
            return
        self._size = size
        self.setFont(icon_font(size))
        self.setFixedSize(size + 4, size + 4)


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
        icon="check_circle" if ok else "radio_button_unchecked",
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
            }}
            QPushButton:hover {{
                background-color: {bg_hover};
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
    the default Qt button chrome.
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
        self.setText(glyph(name))
        self.setFont(icon_font(size))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        self.setFixedSize(size + 14, size + 14)
        self.setToolTip(tooltip)
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
            {hover_rule}
            """
        )


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
    "ClickFrame",
    "DangerButton",
    "GhostButton",
    "HSeparator",
    "IconLabel",
    "IconOnlyButton",
    "MutedLabel",
    "Pill",
    "PrimaryButton",
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
]
