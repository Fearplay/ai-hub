"""EN + CS copy for the Settings section."""

from __future__ import annotations


STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "nav_label": "Settings",
        "title": "Settings",
        "subtitle": "Pick your AI provider, store API keys safely on your computer, tune defaults.",

        "provider_card_title": "AI provider & model",
        "provider_card_desc": "Each AI section uses these defaults. Sections may override the model from their own UI.",
        "provider_label": "Provider",
        "provider_openai": "OpenAI",
        "provider_anthropic": "Anthropic",
        "model_label": "Model",
        "model_hint": "Pick from the list or type your own model id.",
        "model_save": "Save model",
        "model_saved": "Saved",
        "model_invalid": "Model id can't be empty.",

        "keys_card_title": "API keys",
        "keys_card_desc_template": "Keys are stored in {keystore} on this computer. We never send them anywhere except to the provider you call.",
        "key_openai_label": "OpenAI API key",
        "key_openai_hint": "Starts with sk-...",
        "key_anthropic_label": "Anthropic API key",
        "key_anthropic_hint": "Starts with sk-ant-...",
        "key_github_label": "GitHub personal access token",
        "key_github_hint": "Read-only token. Optional - lets AI Career fetch your public repos with a higher rate limit.",
        "key_save_btn": "Save",
        "key_delete_btn": "Delete",
        "key_status_set": "Saved securely",
        "key_status_unset": "Not set",
        "key_save_empty": "Paste a key first.",
        "key_save_ok": "Saved.",
        "key_save_failed": "Could not save - the OS keystore is unavailable.",
        "key_delete_ok": "Deleted.",
        "key_delete_failed": "Nothing to delete.",
        "key_show_btn": "Show",
        "key_hide_btn": "Hide",

        "general_card_title": "General",
        "general_demo_default_label": "Start AI Career runs in Demo mode",
        "general_demo_default_desc": "When on, the analysis uses local mock data instead of calling the AI - useful for screenshots and offline work.",
        "general_followups_label": "Ask clarifying questions before each run",
        "general_followups_desc": "When on, the AI inspects your resume against the job description and asks short, role-specific questions about anything that isn't clearly answered (e.g. 'Have you worked with Python?'). The number of questions matches the number of unclear items - the AI never asks more than it needs and asks nothing when your resume already covers the role. Off by default.",

        "vault_unavailable_title": "OS keystore is not reachable",
        "vault_unavailable_desc": "On Linux you may need to install gnome-keyring or kwallet. Until a backend is reachable, API keys can't be saved.",

        "ctx_quick_actions": "Quick actions",
        "ctx_qa_test_openai": "Test OpenAI key",
        "ctx_qa_test_anthropic": "Test Anthropic key",
        "ctx_qa_open_settings_file": "Open settings folder",

        "test_running": "Testing...",
        "test_ok": "Connection OK.",
        "test_no_key": "Save the key first.",
        "test_failed": "Failed: {error}",
    },
    "cs": {
        "nav_label": "Nastavení",
        "title": "Nastavení",
        "subtitle": "Vyber AI providera, ulož si API klíče bezpečně na svém počítači a uprav výchozí volby.",

        "provider_card_title": "AI provider & model",
        "provider_card_desc": "Tyto volby používají všechny AI sekce. Konkrétní sekce si může model přepsat ze svého UI.",
        "provider_label": "Provider",
        "provider_openai": "OpenAI",
        "provider_anthropic": "Anthropic",
        "model_label": "Model",
        "model_hint": "Vyber ze seznamu nebo napiš vlastní identifikátor.",
        "model_save": "Uložit model",
        "model_saved": "Uloženo",
        "model_invalid": "Identifikátor modelu nesmí být prázdný.",

        "keys_card_title": "API klíče",
        "keys_card_desc_template": "Klíče se ukládají do {keystore} na tomto počítači. Posílají se jen tomu providerovi, kterého voláte.",
        "key_openai_label": "OpenAI API klíč",
        "key_openai_hint": "Začíná na sk-...",
        "key_anthropic_label": "Anthropic API klíč",
        "key_anthropic_hint": "Začíná na sk-ant-...",
        "key_github_label": "GitHub personal access token",
        "key_github_hint": "Read-only token. Volitelné - umožní AI Career stáhnout vaše veřejné repozitáře s vyšším limitem.",
        "key_save_btn": "Uložit",
        "key_delete_btn": "Smazat",
        "key_status_set": "Uloženo bezpečně",
        "key_status_unset": "Nenastaveno",
        "key_save_empty": "Nejdřív vlož klíč.",
        "key_save_ok": "Uloženo.",
        "key_save_failed": "Nepovedlo se uložit - úložiště OS není dostupné.",
        "key_delete_ok": "Smazáno.",
        "key_delete_failed": "Není co smazat.",
        "key_show_btn": "Zobrazit",
        "key_hide_btn": "Skrýt",

        "general_card_title": "Obecné",
        "general_demo_default_label": "Spustit AI Career analýzu v Demo režimu",
        "general_demo_default_desc": "Když je zapnuté, analýza používá lokální mock data místo volání AI - hodí se na screenshoty a offline práci.",
        "general_followups_label": "Před každým spuštěním se ptát na nejasné věci",
        "general_followups_desc": "Když je zapnuté, AI před spuštěním porovná tvůj životopis s inzerátem a položí krátké otázky vázané na konkrétní roli ke všemu, co z CV není jasné (např. „Pracoval jsi s Pythonem?“). Počet otázek odpovídá počtu nejasností - AI se neptá víc, než potřebuje, a pokud životopis pozici plně pokrývá, nezeptá se vůbec. Defaultně vypnuto.",

        "vault_unavailable_title": "Úložiště OS není dostupné",
        "vault_unavailable_desc": "Na Linuxu může chybět gnome-keyring nebo kwallet. Dokud nebude backend dostupný, API klíče nelze uložit.",

        "ctx_quick_actions": "Rychlé akce",
        "ctx_qa_test_openai": "Otestovat OpenAI klíč",
        "ctx_qa_test_anthropic": "Otestovat Anthropic klíč",
        "ctx_qa_open_settings_file": "Otevřít složku s nastavením",

        "test_running": "Testuji...",
        "test_ok": "Spojení OK.",
        "test_no_key": "Nejdřív klíč ulož.",
        "test_failed": "Neúspěch: {error}",
    },
}


def s(lang: str) -> dict[str, str]:
    return STRINGS.get(lang) or STRINGS["en"]
