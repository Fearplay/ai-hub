"""Shadow / gradient helpers for the few sections that need them.

The Marketing phone mockup uses a linear gradient + a soft outer
shadow. We expose those primitives here so section code stays small.

* :func:`apply_drop_shadow` - attach a ``QGraphicsDropShadowEffect``
  to a widget. The shadow blurs / colours / offsets are wired the same
  way as ``ft.BoxShadow``.
* :func:`linear_gradient_qss` - small string helper that emits a
  ``qlineargradient(...)`` background expression for QSS rules.
"""

from __future__ import annotations

from typing import Tuple

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget


def apply_drop_shadow(
    widget: QWidget,
    *,
    blur: int = 18,
    offset: Tuple[int, int] = (0, 6),
    color: str = "#000000",
    alpha: float = 0.35,
) -> QGraphicsDropShadowEffect:
    """Attach a soft drop shadow to ``widget``.

    ``alpha`` is clamped to ``[0.0, 1.0]``. The shadow is owned by the
    widget so the effect lives as long as the widget does.
    """
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setOffset(offset[0], offset[1])
    qcolor = QColor(color)
    qcolor.setAlphaF(max(0.0, min(1.0, alpha)))
    eff.setColor(qcolor)
    widget.setGraphicsEffect(eff)
    return eff


def linear_gradient_qss(
    *,
    angle: str = "topleft-bottomright",
    color_a: str,
    color_b: str,
) -> str:
    """Return a ``qlineargradient(...)`` expression for a QSS background.

    ``angle`` is a string keyword we resolve to the four numeric
    coordinates Qt's stylesheet engine expects:

    * ``"topleft-bottomright"`` (default) - the iPhone mockup look.
    * ``"top-bottom"`` - vertical gradient.
    * ``"left-right"`` - horizontal gradient.
    """
    if angle == "top-bottom":
        x1, y1, x2, y2 = 0, 0, 0, 1
    elif angle == "left-right":
        x1, y1, x2, y2 = 0, 0, 1, 0
    else:
        x1, y1, x2, y2 = 0, 0, 1, 1
    return (
        f"qlineargradient(x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}, "
        f"stop:0 {color_a}, stop:1 {color_b})"
    )


__all__ = ["apply_drop_shadow", "linear_gradient_qss"]
