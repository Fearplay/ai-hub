"""Cross-Flet-version helpers for opening / closing modal dialogs.

Flet 0.84 dropped the legacy ``page.dialog = dlg; dlg.open = True`` flow
in favour of the cleaner ``page.show_dialog(dlg)`` / ``page.pop_dialog()``
pair, but older 0.2x releases still expose ``page.open(dlg)``. The helpers
below pick whichever is available so callers don't have to repeat the
try / except dance.

These mirror the small helpers that already lived in
:mod:`src.sections.ai_career.followup_dialog`; centralising them lets the
language picker, follow-up questions, and any future modal share one
implementation.

Errors are logged via :func:`log_exception` instead of swallowed - we
still fall through to the next compatibility path so the user keeps
seeing the dialog, but the failure shows up in Settings -> Debug logs
so we know why we had to fall back.
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
        # Expected on older Flet versions that lack ``show_dialog``.
        pass
    try:
        page.open(dialog)  # type: ignore[attr-defined]
        return
    except AttributeError:
        # Even older Flet that lacks ``page.open``; fall through.
        pass
    except Exception as exc:
        logger_service.log_exception(
            "ai_career._dialog", "open_dialog_page_open_failed", exc,
        )
    # Last-resort path for very old Flet versions: assign + flag + flush.
    try:
        page.dialog = dialog  # type: ignore[attr-defined]
        dialog.open = True
        page.update()
    except Exception as exc:
        logger_service.log_exception(
            "ai_career._dialog", "open_dialog_legacy_failed", exc,
        )


def close_dialog(page: ft.Page) -> None:
    """Close the current modal on ``page``, regardless of Flet version."""
    try:
        page.pop_dialog()
        return
    except AttributeError:
        # Expected on older Flet versions that lack ``pop_dialog``.
        pass
    try:
        page.close(None)  # type: ignore[attr-defined]
    except AttributeError:
        # Older Flet without ``page.close``; fall through.
        pass
    except Exception as exc:
        logger_service.log_exception(
            "ai_career._dialog", "close_dialog_page_close_failed", exc,
        )
    try:
        page.update()
    except Exception as exc:
        logger_service.log_exception(
            "ai_career._dialog", "close_dialog_page_update_failed", exc,
        )
