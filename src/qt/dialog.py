"""Modal dialog scaffolding shared by sections.

Replaces the page-based ``_open_dialog`` / ``_close_dialog`` pair we
had in :mod:`src.components.how_to_dialog` and the per-section
``_dialog`` helpers. PySide6 ships ``QDialog`` which already does what
we need (modal blocking, ESC-to-close, parented to the main window);
this module just adds a couple of small helpers for the visual style
the screenshots use (rounded corners, themed bg, optional drop shadow).

Usage:

.. code-block:: python

    dlg = BaseDialog(parent=get_main_window(), theme=theme, title="...")
    dlg.body_layout.addWidget(...)
    dlg.add_action(GhostButton("Cancel", theme=theme), role="cancel")
    dlg.add_action(PrimaryButton("Submit", theme=theme), role="accept")
    dlg.exec()
"""

from __future__ import annotations

from typing import Callable, Literal, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.qt.widgets import IconOnlyButton, hbox, vbox
from src.theme import Theme


ActionRole = Literal["accept", "reject", "cancel", "neutral"]


class BaseDialog(QDialog):
    """Themed ``QDialog`` with title bar + close button + body + footer.

    The dialog uses the frameless window flag so we can paint the
    rounded card ourselves; this matches the AlertDialog look of the
    Flet original.
    """

    def __init__(
        self,
        *,
        parent: Optional[QWidget],
        theme: Theme,
        title: str,
        width: int = 560,
        height: Optional[int] = None,
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self.setObjectName("AIHubDialog")
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # Stop Qt from inheriting the parent's stylesheet (which would
        # apply scroll-area / generic ``QWidget`` rules to our card).
        self.setStyleSheet("")

        self.setMinimumWidth(width)
        if height is not None:
            self.setMinimumHeight(height)

        outer = vbox(spacing=0, margins=(24, 24, 24, 24))
        self.setLayout(outer)

        card = QFrame(self)
        card.setObjectName("DialogCard")
        card.setStyleSheet(
            f"""
            QFrame#DialogCard {{
                background-color: {theme.surface};
                border: 1px solid {theme.border};
                border-radius: 16px;
            }}
            """
        )
        outer.addWidget(card)

        card_layout = vbox(spacing=14, margins=(22, 18, 22, 18))
        card.setLayout(card_layout)

        # title row -------------------------------------------------------
        title_row = hbox(spacing=12, margins=(0, 0, 0, 0))
        title_label = QLabel(title)
        font = QFont()
        font.setPixelSize(17)
        font.setWeight(QFont.Weight.DemiBold)
        title_label.setFont(font)
        title_label.setStyleSheet(f"color: {theme.text}; background: transparent;")
        title_row.addWidget(title_label)
        title_row.addStretch(1)
        close_btn = IconOnlyButton(
            "close",
            color=theme.text_muted,
            size=16,
            bg="transparent",
            bg_hover=theme.surface_2,
        )
        close_btn.clicked.connect(self.reject)
        title_row.addWidget(close_btn)
        card_layout.addLayout(title_row)

        # body ------------------------------------------------------------
        self._body_widget = QWidget()
        self._body_layout = vbox(spacing=12, margins=(0, 0, 0, 0))
        self._body_widget.setLayout(self._body_layout)
        self._body_widget.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        card_layout.addWidget(self._body_widget, 1)

        # footer ----------------------------------------------------------
        self._footer_layout = hbox(spacing=8, margins=(0, 4, 0, 0))
        self._footer_layout.addStretch(1)
        card_layout.addLayout(self._footer_layout)

    @property
    def body_layout(self) -> QVBoxLayout:
        return self._body_layout

    def add_action(
        self,
        button: QPushButton,
        *,
        role: ActionRole = "neutral",
        on_click: Optional[Callable[[], None]] = None,
    ) -> QPushButton:
        if role == "accept":
            button.clicked.connect(self.accept)
        elif role in ("reject", "cancel"):
            button.clicked.connect(self.reject)
        if on_click is not None:
            button.clicked.connect(on_click)
        self._footer_layout.addWidget(button)
        return button


def show_dialog(dialog: BaseDialog) -> int:
    """Run a dialog modally; thin wrapper over ``QDialog.exec()``.

    Returns ``QDialog.Accepted`` (1) when the user accepts, ``Rejected``
    (0) otherwise.
    """
    return dialog.exec()


__all__ = ["BaseDialog", "show_dialog"]
