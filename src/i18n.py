"""Global UI strings (sidebar, shared components, secondary nav).

Per-section copy lives in ``src/sections/<key>/strings.py`` so editing one
section's translations never touches another file.

Usage::

    from src.i18n import t

    label = t("app_name", lang)  # "AI Hub"
"""

from __future__ import annotations


DEFAULT_LANG = "en"
LANGUAGES = ("en", "cs")


GLOBAL_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "app_name": "AI Hub",
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
        "settings": "Settings",
        "how_to_use": "How to use this assistant?",
        "my_profile": "My Profile",
        "profile_plan_pro": "Pro version",
        "profile_plan_free": "Free version",
        "profile_set_name": "Set your name",
        "profile_menu_tooltip": "Profile options",
        "profile_name_dialog_label": "Display name",
        "profile_name_dialog_hint": "e.g. Jane Doe",
        "profile_save_btn": "Save",
        "profile_cancel_btn": "Cancel",
        "mock_in_preparation": "This module is being prepared. The form below is a preview - no AI is wired up yet.",
        "mock_examples_title": "Examples",
        "mock_btn_generate": "Generate preview",
        "mock_btn_save_draft": "Save as draft",
        "mock_field_topic": "Topic",
        "mock_field_topic_hint": "What is the post about?",
        "mock_field_audience": "Target audience",
        "mock_field_audience_hint": "Who is it for?",
        "mock_field_tone": "Tone of voice",
        "mock_field_tone_hint": "Friendly, formal, witty...",
        "mock_field_length": "Length",
        "mock_field_length_hint": "Short / medium / long",
        "mock_field_your_text": "Your text",
        "mock_field_your_text_hint": "Paste a few notes to start from.",
    },
    "cs": {
        "app_name": "AI Hub",
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
        "settings": "Nastavení",
        "how_to_use": "Jak používat tohoto asistenta?",
        "my_profile": "Můj profil",
        "profile_plan_pro": "Pro verze",
        "profile_plan_free": "Free verze",
        "profile_set_name": "Nastav si jméno",
        "profile_menu_tooltip": "Možnosti profilu",
        "profile_name_dialog_label": "Zobrazované jméno",
        "profile_name_dialog_hint": "např. Jan Novák",
        "profile_save_btn": "Uložit",
        "profile_cancel_btn": "Zrušit",
        "mock_in_preparation": "Tento modul se právě připravuje. Formulář níže je jen náhled - AI zatím není napojené.",
        "mock_examples_title": "Příklady",
        "mock_btn_generate": "Vygenerovat náhled",
        "mock_btn_save_draft": "Uložit jako koncept",
        "mock_field_topic": "Téma",
        "mock_field_topic_hint": "O čem příspěvek je?",
        "mock_field_audience": "Cílová skupina",
        "mock_field_audience_hint": "Pro koho to je?",
        "mock_field_tone": "Tón komunikace",
        "mock_field_tone_hint": "Přátelský, formální, vtipný...",
        "mock_field_length": "Délka",
        "mock_field_length_hint": "Krátká / střední / dlouhá",
        "mock_field_your_text": "Váš text",
        "mock_field_your_text_hint": "Vlož pár poznámek, ze kterých vyjdeme.",
    },
}


def t(key: str, lang: str) -> str:
    table = GLOBAL_STRINGS.get(lang) or GLOBAL_STRINGS[DEFAULT_LANG]
    if key in table:
        return table[key]
    return GLOBAL_STRINGS[DEFAULT_LANG].get(key, key)


def normalize_lang(lang: str) -> str:
    return lang if lang in LANGUAGES else DEFAULT_LANG
