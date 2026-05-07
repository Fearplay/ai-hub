"""Global UI strings (sidebar, shared components, secondary nav).

Per-section copy lives in ``src/sections/<key>/strings.py`` so editing one
section's translations never touches another file.

Usage::

    from src.i18n import t

    label = t("new_chat", lang)  # "New chat" or "Nová konverzace"
"""

from __future__ import annotations

import flet as ft


DEFAULT_LANG = "en"
LANGUAGES = ("en", "cs")


GLOBAL_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "app_name": "AI Hub",
        "new_chat": "New chat",
        "new_chat_shortcut": "Ctrl + N",
        "language": "Language",
        "czech": "Czech",
        "light_mode": "Light mode",
        "dark_mode": "Dark mode",
        "send": "Send",
        "type_message": "Type a message...",
        "ai_disclaimer": "AI can make mistakes. Verify important information.",
        "attach_file": "Attach file",
        "voice_input": "Voice input",
        "improve_prompt": "Improve prompt",
        "remove": "Remove",
        "pinned": "Pinned",
        "download": "Download",
        "show_all": "Show all",
        "manage": "Manage",
        "edit": "Edit",
        "context_title": "Context",
        "attached_documents": "Attached documents",
        "add_document": "Add document",
        "quick_actions": "Quick actions",
        "conversation_history": "Conversation history",
        "recent_conversations": "Recent conversations",
        "coming_soon": "This section is being prepared.",
        "history": "History",
        "favorites": "Favorites",
        "settings": "Settings",
        "how_to_use": "How to use this assistant?",
    },
    "cs": {
        "app_name": "AI Hub",
        "new_chat": "Nová konverzace",
        "new_chat_shortcut": "Ctrl + N",
        "language": "Jazyk",
        "czech": "Čeština",
        "light_mode": "Světlý režim",
        "dark_mode": "Tmavý režim",
        "send": "Odeslat",
        "type_message": "Napište zprávu...",
        "ai_disclaimer": "AI může dělat chyby. Ověřujte důležité informace.",
        "attach_file": "Připojit soubor",
        "voice_input": "Hlasový vstup",
        "improve_prompt": "Vylepšit prompt",
        "remove": "Odebrat",
        "pinned": "Připnuto",
        "download": "Stáhnout",
        "show_all": "Zobrazit vše",
        "manage": "Spravovat",
        "edit": "Upravit",
        "context_title": "Kontext",
        "attached_documents": "Připojené dokumenty",
        "add_document": "Přidat dokument",
        "quick_actions": "Rychlé akce",
        "conversation_history": "Historie konverzace",
        "recent_conversations": "Nedávné konverzace",
        "coming_soon": "Tato sekce se právě připravuje.",
        "history": "Historie",
        "favorites": "Oblíbené",
        "settings": "Nastavení",
        "how_to_use": "Jak používat tohoto asistenta?",
    },
}


SECONDARY_NAV: list[dict] = [
    {"key": "history", "icon": ft.Icons.HISTORY, "label_key": "history"},
    {"key": "favorites", "icon": ft.Icons.STAR_OUTLINE, "label_key": "favorites", "badge": "3"},
    {"key": "settings", "icon": ft.Icons.SETTINGS_OUTLINED, "label_key": "settings"},
]


def t(key: str, lang: str) -> str:
    table = GLOBAL_STRINGS.get(lang) or GLOBAL_STRINGS[DEFAULT_LANG]
    if key in table:
        return table[key]
    return GLOBAL_STRINGS[DEFAULT_LANG].get(key, key)


def normalize_lang(lang: str) -> str:
    return lang if lang in LANGUAGES else DEFAULT_LANG
