"""Click-to-browse upload zone for AI Career uploads (resume, LinkedIn export).

Thin wrapper around :func:`src.components.file_drop_zone.file_drop_zone`
so AI Career and AI LinkedIn share a single tested implementation. The
shared component already handles best-effort OS drag-and-drop wiring,
graceful click-to-browse fallback, and a "paste path" affordance for
power users.
"""

from __future__ import annotations

from typing import Callable, Sequence

from PySide6.QtWidgets import QWidget

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
    height: int = 160,
    paste_path_label: str | None = None,
    paste_path_tooltip: str | None = None,
    cta_label: str | None = None,
) -> QWidget:
    """Section-local alias preserved for backwards compatibility.

    Adds optional kwargs so callers can pass localised paste-path /
    call-to-action labels without touching the shared
    :func:`src.components.file_drop_zone.file_drop_zone` API.
    """
    return file_drop_zone(
        theme,
        log_area="ai_career.upload",
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
