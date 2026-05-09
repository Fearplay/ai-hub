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
"""

from __future__ import annotations

import flet as ft


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
    except Exception:
        pass
    # Last-resort path for very old Flet versions: assign + flag + flush.
    try:
        page.dialog = dialog  # type: ignore[attr-defined]
        dialog.open = True
        page.update()
    except Exception:
        pass


def close_dialog(page: ft.Page) -> None:
    """Close the current modal on ``page``, regardless of Flet version."""
    try:
        page.pop_dialog()
        return
    except AttributeError:
        pass
    try:
        page.close(None)  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        page.update()
    except Exception:
        pass
