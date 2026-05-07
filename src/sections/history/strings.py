"""EN + CS copy for the History section (placeholder)."""

from __future__ import annotations


STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "nav_label": "History",
        "title": "History",
    },
    "cs": {
        "nav_label": "Historie",
        "title": "Historie",
    },
}


def s(lang: str) -> dict[str, str]:
    return STRINGS.get(lang) or STRINGS["en"]
