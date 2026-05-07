"""EN + CS copy for this section. Add or rename keys as you build the view."""

from __future__ import annotations


STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "nav_label": "My Section",
        "title": "My Section",
    },
    "cs": {
        "nav_label": "Moje sekce",
        "title": "Moje sekce",
    },
}


def s(lang: str) -> dict[str, str]:
    return STRINGS.get(lang) or STRINGS["en"]
