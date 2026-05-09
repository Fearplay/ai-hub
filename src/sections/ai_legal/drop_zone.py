"""Click-to-browse drop zone for the AI Legal section.

The Qt port reuses the shared :func:`src.components.file_drop_zone.file_drop_zone`
component which already handles native OS drag-and-drop, file picker
fallback and the paste-path affordance. This wrapper preserves the
section-specific dictionary shape that ``STATE.uploaded_file`` expects
(``{"name": ..., "type": ..., "size": ...}``).
"""

from __future__ import annotations

import os
from typing import Callable, Optional

from PySide6.QtWidgets import QWidget

from src.components.file_drop_zone import file_drop_zone
from src.services.file_parser import ParsedFile, human_size
from src.sections.ai_legal.strings import s
from src.theme import Theme


def _path_to_file_dict(path: str) -> Optional[dict]:
    if not path:
        return None
    name = os.path.basename(path) or path
    ext = os.path.splitext(name)[1].lower().lstrip(".")
    if ext != "pdf":
        return None
    try:
        size = human_size(os.path.getsize(path))
    except OSError:
        size = "?"
    return {"name": name, "type": "PDF", "size": size}


def _parsed_to_file_dict(parsed: ParsedFile) -> Optional[dict]:
    if parsed.ext != "pdf":
        return None
    return {
        "name": parsed.name,
        "type": "PDF",
        "size": human_size(parsed.size_bytes),
    }


def drop_zone(
    theme: Theme,
    lang: str,
    *,
    on_file_resolved: Callable[[dict], None],
    height: int = 132,
) -> QWidget:
    txt = s(lang)

    def _on_parsed(parsed: ParsedFile) -> None:
        resolved = _parsed_to_file_dict(parsed)
        if resolved is None:
            return
        on_file_resolved(resolved)

    return file_drop_zone(
        theme,
        log_area="ai_legal.drop_zone",
        title=txt["drop_zone_title"],
        hint=txt["drop_zone_hint"],
        extensions=("pdf",),
        unsupported_message=txt["drop_zone_only_pdf"],
        on_file_resolved=_on_parsed,
        height=height,
        paste_path_label=txt.get("drop_zone_paste_path", "Paste path"),
        paste_path_tooltip=txt.get("drop_zone_paste_path_tooltip"),
        cta_label=txt.get("drop_zone_cta", "Click to browse"),
    )
