"""Theme helpers that translate :class:`src.theme.Theme` into Qt styling.

The :class:`~src.theme.Theme` dataclass and the design tokens it holds
(``bg``, ``primary``, ``text_muted``, ``with_accent``, …) are reused
verbatim - they are framework-agnostic. This module adds the two
helpers Qt needs to paint those tokens:

* :func:`rgba` - replacement for ``ft.Colors.with_opacity``. Returns a
  CSS-compatible ``rgba(r, g, b, a)`` string we can drop into any QSS
  rule (Qt's stylesheet engine accepts the same syntax).
* :func:`qss_for_theme` - produces the global stylesheet applied via
  ``QApplication.setStyleSheet(...)``. Covers scrollbars, focus rings,
  the disabled-control palette, ``QLineEdit`` / ``QPlainTextEdit``
  defaults, ``QToolTip`` background, and a couple of named ``Card`` /
  ``Pill`` selectors that the widgets in :mod:`src.qt.widgets` use.

Per-section accent colours still come through :meth:`Theme.with_accent`,
which returns a new ``Theme`` with the primary family swapped in.
Sections that care about an accent (Finance = green, etc.) keep doing
``base.with_accent(theme.primary)`` and pass the resulting theme to
``qss_for_theme`` for any local stylesheet they emit.
"""

from __future__ import annotations

from src.theme import Theme


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgba(hex_color: str, alpha: float) -> str:
    """Return ``rgba(r, g, b, a)`` for ``hex_color`` with ``alpha`` opacity.

    ``alpha`` is clamped to ``[0.0, 1.0]``. Useful for any QSS rule that
    needs translucent fills (hover tints, soft borders, drop-shadow
    background overlays).
    """
    a = max(0.0, min(1.0, alpha))
    r, g, b = _hex_to_rgb(hex_color)
    return f"rgba({r}, {g}, {b}, {a:.3f})"


def qss_for_theme(theme: Theme) -> str:
    """Global stylesheet for the application window.

    Keep this short. Per-widget styling lives in the widget's own
    ``setStyleSheet`` (see :mod:`src.qt.widgets`) so the global sheet
    stays small enough to reapply on every theme switch without
    flickering.
    """
    primary_soft_a18 = rgba(theme.primary, 0.18)
    primary_soft_a30 = rgba(theme.primary, 0.30)
    primary_soft_a08 = rgba(theme.primary, 0.08)
    border_soft_a40 = rgba(theme.border, 0.40)

    return f"""
    /* base */
    QWidget {{
        background-color: {theme.bg};
        color: {theme.text};
        font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
        font-size: 13px;
    }}
    QMainWindow, QDialog {{
        background-color: {theme.bg};
    }}

    /* scrollbars */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 4px 2px 4px 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {border_soft_a40};
        border-radius: 4px;
        min-height: 32px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {primary_soft_a30};
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 2px 4px 2px 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: {border_soft_a40};
        border-radius: 4px;
        min-width: 32px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {primary_soft_a30};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        background: transparent;
        border: 0;
        width: 0;
        height: 0;
    }}
    QScrollBar::add-page, QScrollBar::sub-page {{
        background: transparent;
    }}

    /* tooltips */
    QToolTip {{
        background-color: {theme.surface};
        color: {theme.text};
        border: 1px solid {theme.border};
        border-radius: 6px;
        padding: 6px 8px;
    }}

    /* line/text edits */
    QLineEdit, QPlainTextEdit, QTextEdit {{
        background-color: {theme.surface_2};
        color: {theme.text};
        border: 1px solid transparent;
        border-radius: 10px;
        padding: 8px 12px;
        selection-background-color: {primary_soft_a30};
        selection-color: {theme.text};
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
        border: 1px solid {primary_soft_a30};
    }}
    QLineEdit:disabled, QPlainTextEdit:disabled, QTextEdit:disabled {{
        background-color: {theme.surface};
        color: {theme.text_muted};
    }}

    /* generic menus */
    QMenu {{
        background-color: {theme.surface};
        border: 1px solid {theme.border};
        border-radius: 10px;
        padding: 6px;
    }}
    QMenu::item {{
        background-color: transparent;
        color: {theme.text};
        padding: 8px 14px;
        border-radius: 6px;
    }}
    QMenu::item:selected {{
        background-color: {primary_soft_a18};
        color: {theme.text};
    }}
    QMenu::item:disabled {{
        color: {theme.text_subtle};
    }}
    QMenu::separator {{
        background: {theme.border};
        height: 1px;
        margin: 4px 8px;
    }}

    /* dialog backgrounds */
    QDialog {{
        background-color: {theme.bg};
    }}

    /* focus ring on push buttons (we mostly use custom widgets, but
       Qt's Tab order should still surface here) */
    QPushButton:focus {{
        outline: none;
    }}

    /* file dialog */
    QFileDialog {{
        background-color: {theme.surface};
        color: {theme.text};
    }}

    /* hint that scroll areas should not draw their own viewport bg */
    QScrollArea, QScrollArea > QWidget > QWidget {{
        background: transparent;
    }}
    QAbstractScrollArea {{
        background: transparent;
    }}
    """
