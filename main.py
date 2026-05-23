"""Entry point.

Starts a ``QApplication``, shows the :class:`src.app.AIHubApp` main
window, and runs the Qt event loop. The actual UI lives in ``src/`` -
this file is intentionally small so the PyInstaller wrapper has very
little to bundle for the launcher itself.

Before any other import, we inject the OS-native trust store into
Python's ``ssl`` module via :mod:`truststore`. That way every HTTPS
client we spin up later (``openai``, ``anthropic``, ``httpx`` for the
job scraper / GitHub client) trusts the same root CAs as the rest of
the OS - corporate proxies, antivirus MITM scanners, and custom roots
all stop tripping ``CERTIFICATE_VERIFY_FAILED``. Per the upstream
warning, ``inject_into_ssl()`` is only safe inside applications and
scripts (never libraries) - this entry point is exactly that.

Icons are rendered through :mod:`qtawesome` (see ``src/qt/icons.py``);
QtAwesome lazy-loads its font files on first use, so we don't need to
prime anything at startup.
"""

from __future__ import annotations

import truststore

truststore.inject_into_ssl()

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.app import AIHubApp


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("AI Hub")
    app.setOrganizationName("AI Hub")

    window = AIHubApp()
    window.build()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
