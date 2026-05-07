"""Section contract.

A section = one item in the left sidebar (e.g. AI Marketing). Each lives in
its own folder under ``src/sections/<key>/`` and exports a ``SECTION``
constant of this type. The registry in :mod:`src.sections` auto-discovers
all subfolders, so adding a new section never touches a shared file.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import flet as ft

from src.theme import Theme


ViewBuilder = Callable[[Theme, str], ft.Control]


@dataclass(frozen=True)
class Section:
    key: str
    icon: str
    labels: dict[str, str]
    build_view: ViewBuilder
    build_context: Optional[ViewBuilder] = None
    order: int = 100
    badge: Optional[str] = None
    accent: Optional[str] = None  # hex like "#22C55E"; None = default theme primary

    def label(self, lang: str) -> str:
        return self.labels.get(lang) or self.labels.get("en") or self.key
