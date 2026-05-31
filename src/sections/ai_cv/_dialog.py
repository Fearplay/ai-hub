"""Dialog helpers for AI Career (PySide6 port).

The PySide6 BaseDialog already provides open/close primitives; this
module is kept as a thin compatibility layer so existing imports keep
working. Use ``BaseDialog`` directly in new code.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QDialog

from src.qt.dialog import BaseDialog
from src.services import logger as logger_service


def open_dialog(page: Any, dialog: QDialog) -> None:  # noqa: ARG001
    """Open `dialog` modally."""
    try:
        if hasattr(dialog, "open_modal"):
            dialog.open_modal()
        else:
            dialog.exec()
    except Exception as exc:
        logger_service.log_exception(
            "ai_cv._dialog", "open_dialog_failed", exc,
        )


def close_dialog(page: Any) -> None:  # noqa: ARG001
    """No-op on PySide6 - dialogs close themselves."""
    return None
