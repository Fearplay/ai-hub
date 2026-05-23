"""AI LinkedIn - thin re-export of the shared follow-up dialog.

Section-specific copy (title, intro, button labels) is owned by
``strings.py``; the dialog implementation itself lives in
:mod:`src.components.followup_dialog` so AI Career, AI LinkedIn, AI Bug
Report and AI Jobs all share the same modal.
"""

from __future__ import annotations

from src.components.followup_dialog import open_followup_dialog


__all__ = ["open_followup_dialog"]
