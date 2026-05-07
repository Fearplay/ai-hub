"""EN + CS copy for the Favorites section (placeholder)."""

from __future__ import annotations


STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "nav_label": "Favorites",
        "title": "Favorites",
    },
    "cs": {
        "nav_label": "Oblíbené",
        "title": "Oblíbené",
    },
}


def s(lang: str) -> dict[str, str]:
    return STRINGS.get(lang) or STRINGS["en"]
