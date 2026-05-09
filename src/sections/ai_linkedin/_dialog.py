"""Modal dialog helpers for the AI LinkedIn section (PySide6 port).

Mirrors :mod:`src.sections.ai_career._dialog` so the LinkedIn section
can keep its own copy and stay isolated per the section contract.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QDialog, QWidget

from src.services import logger as logger_service


def open_dialog(parent: Optional[QWidget], dialog: QDialog) -> None:
    """Show ``dialog`` modally as a child of ``parent`` (best-effort)."""
    try:
        if parent is not None:
            dialog.setParent(parent, dialog.windowFlags())
        dialog.exec()
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin._dialog", "dialog_exec_failed", exc,
        )


def close_dialog(dialog: Optional[QDialog]) -> None:
    """Close the given dialog if any."""
    if dialog is None:
        return
    try:
        dialog.accept()
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin._dialog", "dialog_close_failed", exc,
        )
