"""Entry point.

Starts a ``QApplication``, primes the bundled icon font / dispatcher,
shows the :class:`src.app.AIHubApp` main window, and runs the Qt event
loop. The actual UI lives in ``src/`` - this file is intentionally
small so the PyInstaller wrapper has very little to bundle for the
launcher itself.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.app import AIHubApp
from src.qt.icons import icon_font  # primes the font on import


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("AI Hub")
    app.setOrganizationName("AI Hub")

    # Touch the icon font once now so the font database registers it
    # before any widget tries to render a glyph.
    icon_font(18)

    window = AIHubApp()
    window.build()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
