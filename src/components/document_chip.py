"""File chip + badge - used in the context panel and as chat attachments."""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QSizePolicy

from src.i18n import t
from src.qt.icons import Icons
from src.qt.widgets import (
    BodyLabel,
    IconLabel,
    IconOnlyButton,
    MutedLabel,
    hbox,
    vbox,
)
from src.theme import Theme


def file_type_color(theme: Theme, ext: str) -> str:
    return theme.file_pdf if ext.upper() == "PDF" else theme.file_docx


def file_type_icon(ext: str) -> str:
    return Icons.PICTURE_AS_PDF if ext.upper() == "PDF" else Icons.DESCRIPTION


def file_badge(theme: Theme, ext: str, *, size: int = 36) -> QFrame:
    box = QFrame()
    box.setFixedSize(size, size)
    box.setStyleSheet(
        f"background-color: {file_type_color(theme, ext)}; border-radius: 8px;"
    )
    layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    box.setLayout(layout)
    icon = IconLabel(file_type_icon(ext), color="#FFFFFF", size=int(size * 0.5))
    layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignCenter)
    return box


def document_chip(
    theme: Theme,
    lang: str,
    *,
    name: str,
    ext: str,
    size: str,
    on_remove: Optional[Callable[[], None]] = None,
) -> QFrame:
    chip = QFrame()
    chip.setStyleSheet(
        f"""
        QFrame {{
            background-color: {theme.surface_2};
            border-radius: 10px;
        }}
        """
    )
    chip.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

    layout = hbox(spacing=10, margins=(10, 8, 10, 8))
    chip.setLayout(layout)

    layout.addWidget(file_badge(theme, ext))

    text_holder = QFrame()
    text_holder.setStyleSheet("background: transparent;")
    text_holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    text_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    text_holder.setLayout(text_layout)
    text_layout.addWidget(BodyLabel(name, theme=theme, size=13))
    text_layout.addWidget(MutedLabel(f"{ext.upper()} \u2022 {size}", theme=theme, size=11))
    layout.addWidget(text_holder, 1)

    if on_remove is not None:
        close_btn = IconOnlyButton(
            "close",
            color=theme.text_muted,
            size=16,
            bg="transparent",
            bg_hover=theme.surface,
            tooltip=t("remove", lang),
        )
        close_btn.clicked.connect(on_remove)
        layout.addWidget(close_btn)

    return chip
