"""Section contract.

A section = one item in the left sidebar (e.g. AI Marketing). Each lives in
its own folder under ``src/sections/<key>/`` and exports a ``SECTION``
constant of this type. The registry in :mod:`src.sections` auto-discovers
all subfolders, so adding a new section never touches a shared file.

``nav_group`` controls where the section renders in the sidebar:

* ``"primary"`` (default) - main feature list under the "+ New chat" button.
* ``"secondary"`` - auxiliary list under the divider (History, Favorites,
  Settings). Same auto-discovery rules apply.

``wide_layout`` lets a section opt out of the 336 px right context
panel so it can use the full window width (sidebar minus). Used by
sections without a ``build_context`` whose body benefits from the extra
horizontal space (Settings, Debug logs, History, ...).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.theme import Theme


ViewBuilder = Callable[[Theme, str], QWidget]
NavGroup = Literal["primary", "secondary"]


@dataclass(frozen=True)
class Section:
    key: str
    icon: str
    labels: dict[str, str]
    build_view: ViewBuilder
    build_context: Optional[ViewBuilder] = None
    order: int = 100
    badge: Optional[str] = None
    accent: Optional[str] = None
    nav_group: NavGroup = "primary"
    wide_layout: bool = False
    # Opt out of sidebar rendering without deleting the section folder.
    # The Section keeps appearing in ``SECTIONS`` / ``SECTION_BY_KEY`` so
    # leftover deep-links (saved sidebar order, ``set_section`` calls)
    # do not blow up; ``PRIMARY_SECTIONS`` / ``SECONDARY_SECTIONS`` skip
    # it. Used for work-in-progress sections we want hidden from end
    # users until they are ready.
    hidden: bool = False

    def label(self, lang: str) -> str:
        return self.labels.get(lang) or self.labels.get("en") or self.key

    def safe_build_view(self, theme: Theme, lang: str) -> QWidget:
        """Wrap ``build_view`` so a crash never leaves the slot blank."""
        from src.services import logger as logger_service

        try:
            return self.build_view(theme, lang)
        except Exception as exc:
            logger_service.log_exception(
                f"{self.key}.view", "build_view_crashed", exc, lang=lang,
            )
            return _error_panel(theme, key=self.key, message=str(exc))

    def safe_build_context(self, theme: Theme, lang: str) -> QWidget:
        """Wrap ``build_context`` so a crash never leaves the slot blank."""
        from src.services import logger as logger_service

        if self.build_context is None:
            return QWidget()
        try:
            return self.build_context(theme, lang)
        except Exception as exc:
            logger_service.log_exception(
                f"{self.key}.context", "build_context_crashed", exc, lang=lang,
            )
            return QWidget()


def _error_panel(theme: Theme, *, key: str, message: str) -> QWidget:
    """Red error frame matching the old Flet safety-net look."""
    from src.qt.icons import Icons
    from src.qt.widgets import IconLabel, vbox

    container = QWidget()
    layout = vbox(spacing=8, margins=(20, 20, 20, 20))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    container.setLayout(layout)
    container.setStyleSheet(f"background-color: {theme.bg};")

    icon = IconLabel(Icons.ERROR_OUTLINE, color="#EF4444", size=28)
    icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignHCenter)

    text = QLabel(f"[{key}] build_view failed: {message}")
    font = QFont()
    font.setPixelSize(12)
    text.setFont(font)
    text.setStyleSheet("color: #EF4444; background: transparent;")
    text.setWordWrap(True)
    text.setAlignment(Qt.AlignmentFlag.AlignCenter)
    text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    layout.addWidget(text)

    return container
