"""Static metadata for the Settings UI (key rows, model dropdowns)."""

from __future__ import annotations

import flet as ft

from src.services import secrets


SECTION_ICON = ft.Icons.SETTINGS_OUTLINED


def key_rows(txt: dict) -> list[dict]:
    """Definition of the API key rows shown in the Keys card."""
    return [
        {
            "name": secrets.OPENAI_API_KEY,
            "icon": ft.Icons.AUTO_AWESOME,
            "label_key": "key_openai_label",
            "hint_key": "key_openai_hint",
            "label": txt["key_openai_label"],
            "hint": txt["key_openai_hint"],
            "color": "#10A37F",
        },
        {
            "name": secrets.ANTHROPIC_API_KEY,
            "icon": ft.Icons.PSYCHOLOGY_OUTLINED,
            "label_key": "key_anthropic_label",
            "hint_key": "key_anthropic_hint",
            "label": txt["key_anthropic_label"],
            "hint": txt["key_anthropic_hint"],
            "color": "#D97706",
        },
        {
            "name": secrets.GITHUB_TOKEN,
            "icon": ft.Icons.CODE,
            "label_key": "key_github_label",
            "hint_key": "key_github_hint",
            "label": txt["key_github_label"],
            "hint": txt["key_github_hint"],
            "color": "#3B82F6",
        },
    ]
