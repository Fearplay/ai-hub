"""Click-to-browse upload zone for AI LinkedIn (resume + LinkedIn export).

This is a thin wrapper around :func:`src.components.file_drop_zone.file_drop_zone`
introduced as part of the LinkedIn builder + UX polish PR. The shared
component handles best-effort OS drag-and-drop with a graceful click-to-
browse fallback so the same widget powers both AI Career and AI LinkedIn.
"""

from __future__ import annotations

from typing import Callable, Sequence

import flet as ft

from src.components.file_drop_zone import file_drop_zone
from src.services.file_parser import ParsedFile
from src.theme import Theme


def upload_zone(
    theme: Theme,
    *,
    title: str,
    hint: str,
    extensions: Sequence[str],
    unsupported_message: str,
    on_file_resolved: Callable[[ParsedFile], None],
    height: int = 132,
    paste_path_label: str | None = None,
    paste_path_tooltip: str | None = None,
    cta_label: str | None = None,
) -> ft.Control:
    """Section-local alias around :func:`file_drop_zone`.

    Existing call sites in :mod:`src.sections.ai_linkedin.tab_setup`
    refer to ``upload_zone`` so we keep the symbol around. When the
    caller does not pass a localised ``paste_path_label`` /
    ``cta_label`` the shared component falls back to its English
    defaults so the buttons are still visible.
    """
    return file_drop_zone(
        theme,
        log_area="ai_linkedin.upload",
        title=title,
        hint=hint,
        extensions=extensions,
        unsupported_message=unsupported_message,
        on_file_resolved=on_file_resolved,
        height=height,
        paste_path_label=paste_path_label or "Paste path",
        paste_path_tooltip=paste_path_tooltip,
        cta_label=cta_label or "Click to browse",
    )
