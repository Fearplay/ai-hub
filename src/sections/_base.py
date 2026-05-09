"""Section contract.

A section = one item in the left sidebar (e.g. AI Marketing). Each lives in
its own folder under ``src/sections/<key>/`` and exports a ``SECTION``
constant of this type. The registry in :mod:`src.sections` auto-discovers
all subfolders, so adding a new section never touches a shared file.

``nav_group`` controls where the section renders in the sidebar:

* ``"primary"`` (default) — main feature list under the "+ New chat" button.
* ``"secondary"`` — auxiliary list under the divider (History, Favorites,
  Settings). Same auto-discovery rules apply.

``wide_layout`` lets a section opt out of the 336 px right context
panel so it can use the full window width (sidebar minus). Used by
sections without a ``build_context`` whose body benefits from the extra
horizontal space (Settings, Debug logs, History, …).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Optional

import flet as ft

from src.theme import Theme


ViewBuilder = Callable[[Theme, str], ft.Control]
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

    def label(self, lang: str) -> str:
        return self.labels.get(lang) or self.labels.get("en") or self.key

    def safe_build_view(self, theme: Theme, lang: str) -> ft.Control:
        """Wrap ``build_view`` so a crash never leaves the slot blank."""
        from src.services import logger as logger_service

        try:
            return self.build_view(theme, lang)
        except Exception as exc:
            logger_service.log_exception(
                f"{self.key}.view", "build_view_crashed", exc, lang=lang,
            )
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.ERROR_OUTLINE, color="#EF4444", size=28),
                        ft.Text(
                            f"[{self.key}] build_view failed: {exc}",
                            color="#EF4444",
                            size=12,
                            selectable=True,
                        ),
                    ],
                    spacing=8,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                alignment=ft.Alignment.CENTER,
                expand=True,
                padding=20,
            )

    def safe_build_context(self, theme: Theme, lang: str) -> ft.Control:
        """Wrap ``build_context`` so a crash never leaves the slot blank."""
        from src.services import logger as logger_service

        if self.build_context is None:
            return ft.Container()
        try:
            return self.build_context(theme, lang)
        except Exception as exc:
            logger_service.log_exception(
                f"{self.key}.context", "build_context_crashed", exc, lang=lang,
            )
            return ft.Container()
