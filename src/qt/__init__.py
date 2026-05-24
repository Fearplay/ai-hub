"""PySide6 foundation layer for AI Hub.

Every UI module under :mod:`src.components` and :mod:`src.sections` imports
its primitives from this package instead of pulling Qt directly. The split
keeps theme tokens, icon rendering, common widget styling, the
cross-thread dispatcher, and dialog scaffolding in one place so individual
sections never have to think about QSS, threading, or icon font handling.

Public re-exports follow the patterns we used to lean on from Flet:

* ``Theme`` / ``get_theme`` come from :mod:`src.theme` unchanged.
* :func:`qss_for_theme` produces a global stylesheet from a theme.
* :func:`rgba` is the replacement for ``ft.Colors.with_opacity``.
* :class:`Icons` exposes Material Design Icons 6 constants (rendered
  by ``qtawesome``).
* :func:`icon_pixmap` / :func:`qicon` produce raw ``QPixmap`` /
  ``QIcon`` objects for widgets that cannot use :class:`IconLabel`.
"""

from __future__ import annotations

from src.qt.icons import Icons, glyph, icon_font, icon_pixmap, qicon
from src.qt.theme import qss_for_theme, rgba

__all__ = [
    "Icons",
    "glyph",
    "icon_font",
    "icon_pixmap",
    "qicon",
    "qss_for_theme",
    "rgba",
]
