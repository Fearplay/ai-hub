"""Click-to-browse drop zone for the AI Legal section.

The zone supports the full multi-format set from
:mod:`src.services.file_parser` (PDF, DOCX, HTML / HTM, TXT, MD). The
parsed text body is what feeds the legal-assistant prompts; metadata
(``name`` / ``type`` / ``size``) lives in ``STATE.uploaded_file`` so the
chat / context panels can show the document chip.

This module is a thin wrapper around the shared
:func:`src.components.file_drop_zone.file_drop_zone` component which
already handles native OS drag-and-drop, the file picker fallback, the
paste-path button and the inline error label.
"""

from __future__ import annotations

import os
from typing import Callable, Optional

from PySide6.QtWidgets import QWidget

from src.components.file_drop_zone import file_drop_zone
from src.services.file_parser import ParsedFile, human_size
from src.sections.ai_legal.strings import s
from src.theme import Theme


SUPPORTED_EXTENSIONS: tuple[str, ...] = ("pdf", "docx", "html", "htm", "txt", "md")


def _parsed_to_file_dict(parsed: ParsedFile) -> dict:
    """Render a :class:`ParsedFile` into the ``STATE.uploaded_file`` shape.

    The ``type`` label is the upper-case extension (``"PDF"``, ``"DOCX"``,
    ``"HTML"``, …) so the document chip in the right panel can show the
    real format instead of pretending everything is a PDF.
    """
    return {
        "name": parsed.name,
        "type": parsed.ext.upper() if parsed.ext else "FILE",
        "size": human_size(parsed.size_bytes),
        "path": parsed.path,
    }


def drop_zone(
    theme: Theme,
    lang: str,
    *,
    on_file_resolved: Callable[[dict, ParsedFile], None],
    height: int = 132,
) -> QWidget:
    """Build the AI Legal drop zone.

    ``on_file_resolved`` receives ``(metadata_dict, parsed_file)`` so the
    caller (``context.py``) can store both the display chip data and the
    extracted text body on ``STATE`` in one place.
    """
    txt = s(lang)

    def _on_parsed(parsed: ParsedFile) -> None:
        resolved = _parsed_to_file_dict(parsed)
        on_file_resolved(resolved, parsed)

    return file_drop_zone(
        theme,
        log_area="ai_legal.drop_zone",
        title=txt["drop_zone_title"],
        hint=txt["drop_zone_hint"],
        extensions=SUPPORTED_EXTENSIONS,
        unsupported_message=txt.get("drop_zone_unsupported", txt["drop_zone_only_pdf"]),
        on_file_resolved=_on_parsed,
        height=height,
        paste_path_label=txt.get("drop_zone_paste_path", "Paste path"),
        paste_path_tooltip=txt.get("drop_zone_paste_path_tooltip"),
        cta_label=txt.get("drop_zone_cta", "Click to browse"),
    )
