"""Windows-only helper that paints the OS title bar in our theme.

PySide6 hands the OS-native chrome (X / minimise / maximise + caption
strip) to whatever Windows is configured to use, which means a fresh
boot in dark mode gives us a sidebar painted in our dark palette but
the title bar is still bright white. The user wants the title bar to
feel like the rest of the app (matching the old Flet build that they
liked), so we ask DWM (Desktop Window Manager) to tint it for us via
``DwmSetWindowAttribute``.

Two attributes are relevant:

* ``DWMWA_USE_IMMERSIVE_DARK_MODE`` (20) - BOOL switch that makes the
  caption text white and the strip dark. Works on Windows 10 1809+,
  Windows 11. Older builds expose the same flag at attribute id 19, so
  we try the modern id first and fall back.
* ``DWMWA_CAPTION_COLOR`` (35) - COLORREF that overrides the caption
  fill exactly. Windows 11 22000+. We use it to tint the strip with
  ``theme.sidebar_bg`` so the title bar visually melts into the
  sidebar column.

On macOS / Linux this module is a no-op; both already adapt the title
bar to the system colour scheme. The helper logs a single WARNING when
the call fails on Windows but never raises - a missing title-bar tint
is a polish problem, not a crash.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from typing import Optional

from PySide6.QtWidgets import QWidget

from src.services import logger as logger_service
from src.theme import Theme

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_LEGACY = 19
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36

_DWM_NOT_AVAILABLE: bool = False


def _hex_to_colorref(hex_color: str) -> int:
    """Convert ``#RRGGBB`` to the DWM 0x00BBGGRR COLORREF."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return 0
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return (b << 16) | (g << 8) | r


def _set_attr_bool(hwnd: int, attribute: int, value: bool) -> bool:
    flag = wintypes.BOOL(1 if value else 0)
    hr = ctypes.windll.dwmapi.DwmSetWindowAttribute(
        wintypes.HWND(hwnd),
        wintypes.DWORD(attribute),
        ctypes.byref(flag),
        ctypes.sizeof(flag),
    )
    return hr == 0


def _set_attr_color(hwnd: int, attribute: int, hex_color: str) -> bool:
    color = wintypes.DWORD(_hex_to_colorref(hex_color))
    hr = ctypes.windll.dwmapi.DwmSetWindowAttribute(
        wintypes.HWND(hwnd),
        wintypes.DWORD(attribute),
        ctypes.byref(color),
        ctypes.sizeof(color),
    )
    return hr == 0


def apply_title_bar_theme(window: QWidget, theme: Theme, mode: str) -> None:
    """Recolour ``window``'s title bar to match the active theme.

    ``mode`` is the high-level palette mode (``"dark"`` / ``"light"``).
    Anything other than ``dark`` falls back to the system default light
    chrome - we only force dark when the user is in dark mode so light
    mode keeps system-native min/max/close glyphs.
    """
    global _DWM_NOT_AVAILABLE

    if sys.platform != "win32":
        return
    if _DWM_NOT_AVAILABLE:
        return

    hwnd = int(window.winId())
    if not hwnd:
        return

    try:
        is_dark = mode == "dark"
        ok_modern = _set_attr_bool(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, is_dark)
        if not ok_modern:
            _set_attr_bool(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE_LEGACY, is_dark)

        if is_dark:
            _set_attr_color(hwnd, DWMWA_CAPTION_COLOR, theme.sidebar_bg)
            _set_attr_color(hwnd, DWMWA_TEXT_COLOR, theme.text)
        else:
            _set_attr_color(hwnd, DWMWA_CAPTION_COLOR, "#FFFFFF")
            _set_attr_color(hwnd, DWMWA_TEXT_COLOR, theme.text)
    except OSError as exc:
        _DWM_NOT_AVAILABLE = True
        logger_service.log_exception(
            "qt.window_chrome", "apply_title_bar_theme_failed", exc, mode=mode,
        )


__all__ = ["apply_title_bar_theme"]
