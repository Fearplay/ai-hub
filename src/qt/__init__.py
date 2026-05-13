"""PySide6 foundation layer for AI Hub.

Every UI module under :mod:`src.components` and :mod:`src.sections` imports
its primitives from this package instead of pulling Qt directly. The split
keeps theme tokens, icon font handling, common widget styling, the
cross-thread dispatcher, and dialog scaffolding in one place so individual
sections never have to think about QSS, threading, or font loading.

Public re-exports follow the patterns we used to lean on from Flet:

* ``Theme`` / ``get_theme`` come from :mod:`src.theme` unchanged.
* :func:`qss_for_theme` produces a global stylesheet from a theme.
* :func:`rgba` is the replacement for ``ft.Colors.with_opacity``.
* :class:`Icons` exposes Material Icons constants.
* :func:`icon_font` returns the loaded ``QFont`` configured for the icon
  set so widgets can render glyphs without re-loading the font file.
"""

from __future__ import annotations

from src.qt.icons import Icons, icon_font, glyph
from src.qt.theme import qss_for_theme, rgba

__all__ = [
    "Icons",
    "icon_font",
    "glyph",
    "qss_for_theme",
    "rgba",
]
