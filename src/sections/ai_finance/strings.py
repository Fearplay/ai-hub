"""EN + CS copy for the AI Finance section."""

from __future__ import annotations


STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "nav_label": "AI Finance",
        "title": "AI Finance",
    },
    "cs": {
        "nav_label": "AI Finance",
        "title": "AI Finance",
    },
}


def s(lang: str) -> dict[str, str]:
    return STRINGS.get(lang) or STRINGS["en"]
