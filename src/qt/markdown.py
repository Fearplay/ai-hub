"""Tiny ``**bold**`` -> Qt rich text helper.

Qt's ``QLabel`` understands a small subset of HTML when ``setTextFormat``
is :class:`Qt.RichText`. That is enough to render bold spans inside a
single paragraph, which is the only markdown affordance our
``modern_cv_render`` and chat bubbles need.

The previous Flet implementation used ``ft.TextSpan`` lists; this
module replicates that with a single ``str -> str`` transformation
that escapes everything else so user-supplied text can never inject
HTML markup.
"""

from __future__ import annotations

import re

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def escape_html(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def bold_to_html(text: str, *, color: str | None = None) -> str:
    """Convert ``**bold**`` runs to ``<b>`` spans, escaping the rest.

    ``color``, when provided, wraps the whole string in a ``<span
    style="color: ...">`` so the host label can stay neutral and let
    the markup carry the colour.
    """
    if not text:
        return ""
    pieces: list[str] = []
    pos = 0
    for m in _BOLD_RE.finditer(text):
        if m.start() > pos:
            pieces.append(escape_html(text[pos : m.start()]))
        pieces.append(f"<b>{escape_html(m.group(1))}</b>")
        pos = m.end()
    if pos < len(text):
        pieces.append(escape_html(text[pos:]))
    body = "".join(pieces)
    if color:
        return f'<span style="color:{color};">{body}</span>'
    return body


__all__ = ["bold_to_html", "escape_html"]
