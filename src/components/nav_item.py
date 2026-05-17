"""One row in the left sidebar.

Three flavors:

* :func:`nav_item` - simple builder that just returns a ``QWidget``. Use
  this if you only need a one-shot row that you do not plan to mutate.
* :func:`nav_item_handle` - returns the row plus references to the icon
  / text labels so callers can flip the active state without rebuilding
  (used by the sidebar to keep section clicks snappy).
* :class:`ReorderableNavRow` - wraps a :func:`nav_item_handle` row in a
  drag-and-drop container with a small grip icon on the right. Used by
  the primary section list in :mod:`src.components.sidebar` so users
  can reorder sections and have the order persisted via
  :mod:`src.services.settings_store`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from PySide6.QtCore import QMimeData, QPoint, Qt
from PySide6.QtGui import QDrag, QFont, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.qt.icons import Icons
from src.qt.theme import rgba
from src.qt.widgets import ClickFrame, IconLabel, Pill, hbox
from src.theme import Theme


REORDER_MIME = "application/x-aihub-nav-key"


def _badge_widget(theme: Theme, text: str) -> QWidget:
    """Render a sidebar nav badge.

    Short labels (<= 2 chars, e.g. notification counts) become a tight
    20x20 circle so the row stays balanced. Longer text falls back to
    the regular pill so we don't squeeze, e.g., "NEW" into a circle.
    """
    text = str(text)
    if len(text) <= 2:
        chip = QFrame()
        chip.setObjectName("NavBadge")
        chip.setFixedSize(20, 20)
        chip.setStyleSheet(
            f"QFrame#NavBadge {{ background-color: {theme.badge}; border-radius: 10px; }}"
        )
        layout = QVBoxLayout(chip)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        font = QFont()
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.DemiBold)
        label = QLabel(text)
        label.setFont(font)
        label.setStyleSheet("color: #FFFFFF; background: transparent;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        return chip
    return Pill(
        text=text,
        bg=theme.badge,
        fg="#FFFFFF",
        radius=10,
        padding=(2, 8, 2, 8),
    )


@dataclass
class NavItemHandle:
    container: ClickFrame
    icon: IconLabel
    text: QLabel

    def set_active(self, theme: Theme, *, active: bool) -> None:
        self.icon.set_color(theme.primary if active else theme.text_muted)
        self.text.setStyleSheet(
            f"color: {theme.text if active else theme.text_muted}; background: transparent;"
        )
        font = self.text.font()
        font.setWeight(QFont.Weight.DemiBold if active else QFont.Weight.Normal)
        self.text.setFont(font)
        bg = theme.primary_tint if active else "transparent"
        hover_bg = rgba(theme.primary, 0.10)
        self.container.setStyleSheet(
            f"""
            ClickFrame {{
                background-color: {bg};
                border-radius: 10px;
            }}
            ClickFrame:hover {{
                background-color: {hover_bg if not active else theme.primary_tint};
            }}
            """
        )


def nav_item_handle(
    theme: Theme,
    icon: str,
    label: str,
    *,
    active: bool = False,
    badge: Optional[str] = None,
    on_click: Optional[Callable[[], None]] = None,
) -> NavItemHandle:
    container = ClickFrame()
    container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
    layout: QHBoxLayout = hbox(spacing=12, margins=(12, 10, 12, 10))
    container.setLayout(layout)

    icon_color = theme.primary if active else theme.text_muted
    icon_label = IconLabel(icon, color=icon_color, size=20)
    layout.addWidget(icon_label)

    text_color = theme.text if active else theme.text_muted
    text_label = QLabel(label)
    font = QFont()
    font.setPixelSize(13)
    font.setWeight(QFont.Weight.DemiBold if active else QFont.Weight.Normal)
    text_label.setFont(font)
    text_label.setStyleSheet(f"color: {text_color}; background: transparent;")
    text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    text_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
    layout.addWidget(text_label, 1)

    if badge:
        layout.addWidget(_badge_widget(theme, badge))

    bg = theme.primary_tint if active else "transparent"
    hover_bg = rgba(theme.primary, 0.10) if not active else theme.primary_tint
    container.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {bg};
            border-radius: 10px;
        }}
        ClickFrame:hover {{
            background-color: {hover_bg};
        }}
        """
    )

    if on_click is not None:
        container.clicked.connect(on_click)

    return NavItemHandle(container=container, icon=icon_label, text=text_label)


def nav_item(
    theme: Theme,
    icon: str,
    label: str,
    *,
    active: bool = False,
    badge: Optional[str] = None,
    on_click: Optional[Callable[[], None]] = None,
) -> ClickFrame:
    return nav_item_handle(
        theme,
        icon,
        label,
        active=active,
        badge=badge,
        on_click=on_click,
    ).container


@dataclass
class ReorderHandle:
    """Public handle for a reorderable row.

    Mirrors :class:`NavItemHandle` but the outer container is a
    :class:`ReorderableNavRow` (with drag + drop support and a grip
    affordance). The sidebar keeps a dict of these so it can flip
    active state without rebuilding the row tree.
    """

    container: "ReorderableNavRow"
    icon: IconLabel
    text: QLabel
    grip: IconLabel
    section_key: str

    def set_active(self, theme: Theme, *, active: bool) -> None:
        self.icon.set_color(theme.primary if active else theme.text_muted)
        self.text.setStyleSheet(
            f"color: {theme.text if active else theme.text_muted}; background: transparent;"
        )
        font = self.text.font()
        font.setWeight(QFont.Weight.DemiBold if active else QFont.Weight.Normal)
        self.text.setFont(font)
        self.container.set_active_style(theme, active=active)


class ReorderableNavRow(QFrame):
    """Sidebar row that can be dragged to reorder + dropped on by peers.

    The whole row remains clickable for navigation (the embedded
    :class:`ClickFrame` keeps emitting ``clicked``); the drag is only
    armed when the press lands inside the grip handle on the right.
    That way a regular tap navigates the section as before and only an
    intentional grab on the dots initiates a reorder. Drop targets are
    visualised by a 2 px primary-color hint above / below the hovered
    row.
    """

    GRIP_SIZE = 28

    def __init__(
        self,
        theme: Theme,
        *,
        section_key: str,
        on_reorder: Callable[[str, str, bool], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._section_key = section_key
        self._on_reorder = on_reorder
        self._theme_primary = theme.primary
        self._press_pos: Optional[QPoint] = None
        self._press_on_grip = False
        self._drop_hint = "none"  # "top" | "bottom" | "none"

        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setStyleSheet("ReorderableNavRow { background: transparent; }")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self._content_layout = outer

        self._click_frame: Optional[ClickFrame] = None
        self._grip: Optional[IconLabel] = None

    # ---- public API used by the sidebar ----

    def attach(
        self,
        click_frame: ClickFrame,
        grip: IconLabel,
    ) -> None:
        """Mount the nav row body + grip widget after construction.

        The body is built by :func:`nav_item_handle` so it carries the
        active/hover styling logic shared with the secondary nav. We
        wrap it here so the grip + drop hint stay attached to the same
        widget that owns the drag mime.
        """
        self._click_frame = click_frame
        self._grip = grip
        self._content_layout.addWidget(click_frame)

    def section_key(self) -> str:
        return self._section_key

    def set_active_style(self, theme: Theme, *, active: bool) -> None:
        if self._grip is None:
            return
        self._theme_primary = theme.primary
        # Grip stays subtle until hovered.
        self._grip.set_color(theme.text_muted if active else theme.text_subtle)

    # ---- drag source ----

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position().toPoint()
            self._press_on_grip = self._point_on_grip(self._press_pos)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if (
            self._press_pos is None
            or not self._press_on_grip
            or not (event.buttons() & Qt.MouseButton.LeftButton)
        ):
            super().mouseMoveEvent(event)
            return
        delta = (event.position().toPoint() - self._press_pos).manhattanLength()
        if delta < QApplication.startDragDistance():
            return
        self._start_drag()
        self._press_pos = None
        self._press_on_grip = False

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._press_pos = None
        self._press_on_grip = False
        super().mouseReleaseEvent(event)

    def _point_on_grip(self, point: QPoint) -> bool:
        if self._grip is None:
            return False
        grip_rect = self._grip.geometry()
        parent = self._grip.parentWidget()
        # Walk up to map grip's geometry into this widget's coordinates.
        offset = QPoint(0, 0)
        node: Optional[QWidget] = parent
        while node is not None and node is not self:
            offset += node.pos()
            node = node.parentWidget()
        mapped = grip_rect.translated(offset)
        # Slightly enlarge the hit area so the user does not have to
        # land on the 18 px glyph perfectly.
        mapped.adjust(-6, -4, 6, 4)
        return mapped.contains(point)

    def _start_drag(self) -> None:
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(REORDER_MIME, self._section_key.encode("utf-8"))
        drag.setMimeData(mime)

        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        self.render(pixmap)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(20, self.height() // 2))
        drag.exec(Qt.DropAction.MoveAction)

    # ---- drop target ----

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(REORDER_MIME):
            event.acceptProposedAction()
            self._update_hint(event)
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(REORDER_MIME):
            event.acceptProposedAction()
            self._update_hint(event)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self._drop_hint = "none"
        self._apply_hint_style()
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802
        if not event.mimeData().hasFormat(REORDER_MIME):
            event.ignore()
            return
        source_key = bytes(event.mimeData().data(REORDER_MIME)).decode("utf-8")
        before = self._drop_hint != "bottom"
        self._drop_hint = "none"
        self._apply_hint_style()
        if source_key and source_key != self._section_key:
            try:
                self._on_reorder(source_key, self._section_key, before)
            except Exception:
                # Sidebar's reorder callback already has its own log.
                pass
        event.acceptProposedAction()

    def _update_hint(self, event) -> None:
        y = event.position().toPoint().y()
        midpoint = self.height() / 2
        new_hint = "top" if y < midpoint else "bottom"
        if new_hint != self._drop_hint:
            self._drop_hint = new_hint
            self._apply_hint_style()

    def _apply_hint_style(self) -> None:
        if self._drop_hint == "top":
            self.setStyleSheet(
                f"""
                ReorderableNavRow {{
                    background: transparent;
                    border-top: 2px solid {self._theme_primary};
                    border-bottom: 2px solid transparent;
                }}
                """
            )
        elif self._drop_hint == "bottom":
            self.setStyleSheet(
                f"""
                ReorderableNavRow {{
                    background: transparent;
                    border-top: 2px solid transparent;
                    border-bottom: 2px solid {self._theme_primary};
                }}
                """
            )
        else:
            self.setStyleSheet(
                """
                ReorderableNavRow {
                    background: transparent;
                    border-top: 2px solid transparent;
                    border-bottom: 2px solid transparent;
                }
                """
            )


def reorderable_nav_item(
    theme: Theme,
    icon: str,
    label: str,
    *,
    section_key: str,
    on_click: Callable[[], None],
    on_reorder: Callable[[str, str, bool], None],
    active: bool = False,
    badge: Optional[str] = None,
) -> ReorderHandle:
    """Build a draggable sidebar row plus its handle.

    The body is a regular :func:`nav_item_handle` row with one extra
    child appended on the right: a :class:`IconLabel` rendering the
    ``drag_indicator`` Material glyph. The whole row is wrapped in a
    :class:`ReorderableNavRow` so peers can drop onto it.
    """
    handle = nav_item_handle(
        theme,
        icon,
        label,
        active=active,
        badge=badge,
        on_click=on_click,
    )
    grip = IconLabel(
        Icons.MORE_HORIZ,
        color=theme.text_subtle,
        size=16,
    )
    grip.setToolTip(label)
    grip.setCursor(Qt.CursorShape.OpenHandCursor)
    handle.container.layout().addWidget(grip)

    row = ReorderableNavRow(
        theme,
        section_key=section_key,
        on_reorder=on_reorder,
    )
    row.attach(handle.container, grip)

    return ReorderHandle(
        container=row,
        icon=handle.icon,
        text=handle.text,
        grip=grip,
        section_key=section_key,
    )
