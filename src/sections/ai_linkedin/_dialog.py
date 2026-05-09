"""Cross-Flet-version helpers for opening / closing modal dialogs.

Mirrors :mod:`src.sections.ai_career._dialog` so the LinkedIn section
can keep its own copy and stay isolated per the section contract.
"""

from __future__ import annotations

import flet as ft

from src.services import logger as logger_service


def open_dialog(page: ft.Page, dialog: ft.AlertDialog) -> None:
    """Open ``dialog`` on ``page`` using whichever Flet API is available."""
    try:
        page.show_dialog(dialog)
        return
    except AttributeError:
        pass
    try:
        page.open(dialog)  # type: ignore[attr-defined]
        return
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin._dialog", "page_open_failed", exc,
        )
    try:
        page.dialog = dialog  # type: ignore[attr-defined]
        dialog.open = True
        page.update()
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin._dialog", "page_dialog_assign_failed", exc,
        )


def close_dialog(page: ft.Page) -> None:
    """Close the current modal on ``page``, regardless of Flet version."""
    try:
        page.pop_dialog()
        return
    except AttributeError:
        pass
    try:
        page.close(None)  # type: ignore[attr-defined]
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin._dialog", "page_close_failed", exc,
        )
    try:
        page.update()
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin._dialog", "page_update_failed", exc,
        )
