"""Click-to-browse upload zone for the AI Jobs profile uploader.

Thin wrapper around :func:`src.components.file_drop_zone.file_drop_zone`
mirroring :mod:`src.sections.ai_cv.upload` so the section reuses the
shared OS drag-and-drop / paste-path / browse implementation. Only the
``log_area`` differs - failures show up under ``ai_jobs.upload`` in
Settings -> Debug logs so we can tell where they came from.
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
    return file_drop_zone(
        theme,
        log_area="ai_jobs.upload",
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
