"""EN + CS copy for the AI Bug Report section.

The section turns a free-form description, optional environment notes,
attached screenshots, and supporting docs / logs into a well-structured
Word bug report (title, severity, STR, expected vs actual, ...). Every
visible string lives here so the contributor never has to chase Czech
translations through ``src/i18n.py``.
"""

from __future__ import annotations


STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "nav_label": "AI Bug Report",
        "title": "AI Bug Report",
        "subtitle": (
            "Drop a description, screenshots, or logs - the AI fills in the title, "
            "steps to reproduce, expected vs actual, severity, and saves a polished "
            "Word document."
        ),

        "tab_input": "Input",
        "tab_preview": "Preview",
        "tab_export": "Export",

        "step_input_label": "STEP 1",
        "step_input_title": "Describe the bug",
        "step_input_desc": (
            "Type what happened, what you expected, what you actually saw - any "
            "detail helps. Drop screenshots or logs below. If something is missing "
            "the AI infers a reasonable guess and marks it as inferred."
        ),
        "description_label": "What happened?",
        "description_hint": (
            "Example: 'Clicking Save on the profile page does nothing. I expected "
            "the toast to confirm and the page to reload, but the button just "
            "stays in the loading state.'"
        ),
        "env_label": "Environment hints (optional)",
        "env_hint": (
            "Browser / OS / device / app version / URL - whatever you have. "
            "Leave blank to let the AI infer from the screenshots."
        ),
        "attachments_label": "Attachments",
        "drop_title": "Drop screenshots, logs, or PDFs here",
        "drop_hint": "PNG / JPG / WEBP for screenshots, TXT / LOG / JSON / PDF / DOCX / MD / HTML for context",
        "unsupported": "Unsupported file type. Use PNG / JPG / WEBP / GIF / BMP / TXT / LOG / JSON / PDF / DOCX / MD / HTML.",
        "upload_paste_path_btn": "Paste path",
        "upload_paste_path_tooltip": "Tip on Windows: Shift+Right-click a file in Explorer -> Copy as path, then click here.",
        "upload_cta_label": "Click to browse",
        "no_attachments": "No attachments yet.",
        "remove_btn": "Remove",
        "attachment_image_badge": "IMAGE",
        "attachment_doc_badge": "DOC",

        "footer_demo_btn": "Try demo data",
        "footer_generate_btn": "Generate bug report",
        "footer_generate_running": "Generating...",
        "generate_disabled_hint": "Add a description or at least one attachment first.",
        "input_requirement_hint": "Minimum input: add a description or at least one attachment.",
        "no_key_template": "Missing API key for {provider}. Open Settings and save your key first.",

        "preview_empty": "Nothing to show yet. Run Generate on the Input tab.",
        "preview_back_btn": "Back to Input",
        "preview_regen_btn": "Regenerate",
        "preview_title_label": "Title",
        "preview_summary_label": "Summary",
        "preview_severity_label": "Severity",
        "preview_priority_label": "Priority",
        "preview_repro_label": "Reproducibility",
        "preview_environment_label": "Environment",
        "preview_preconditions_label": "Preconditions",
        "preview_str_label": "Steps to reproduce",
        "preview_expected_label": "Expected result",
        "preview_actual_label": "Actual result",
        "preview_attachments_label": "Attachments summary",
        "preview_notes_label": "Additional notes",

        "env_browser": "Browser",
        "env_os": "Operating system",
        "env_device": "Device",
        "env_app_version": "App version",
        "env_url": "URL",

        "export_title": "Save the bug report",
        "export_desc": (
            "The Word document mirrors the preview - title, environment table, numbered "
            "steps, expected vs actual, embedded screenshots, attachments summary. A "
            "Markdown mirror and a summary.json land in the same folder."
        ),
        "export_save_btn": "Save as Word document",
        "export_open_folder_btn": "Open output folder",
        "export_saved_template": "Saved to {path}",
        "export_save_failed": "Could not save the report: {error}",
        "export_run_first": "Generate the bug report first.",

        "demo_pill": "DEMO",

        "how_to_title": "How to use AI Bug Report",
        "how_to_close": "Got it",
        "how_to_section_what": "What it does",
        "how_to_what_text": (
            "Drop anything that describes the bug - a one-line note, a long rant, a "
            "screenshot of the broken screen, a log file. The AI reads the lot and "
            "produces a structured bug report (title, severity, steps, expected vs "
            "actual). When a field is missing the AI marks its best guess as inferred "
            "instead of leaving the report blank."
        ),
        "how_to_section_inputs": "Inputs",
        "how_to_inputs_text": (
            "Text in the description, optional environment hints (browser / OS / URL), "
            "and any number of screenshots (PNG / JPG / WEBP / GIF / BMP / HEIC) or "
            "supporting docs (TXT / LOG / JSON / PDF / DOCX / MD / HTML). Screenshots "
            "are sent to the model via its vision API; text-only docs are parsed locally."
        ),
        "how_to_section_quality": "Tips for a great report",
        "how_to_quality_text": (
            "Add at least one screenshot when possible - the AI gets dramatically more "
            "accurate about expected vs actual when it can see the broken state. Mention "
            "the browser / OS once in the description and the environment table fills "
            "itself. After generating, edit the title / severity / priority inline before "
            "saving the Word file."
        ),

        "ctx_section_label": "AI Bug Report",
        "ctx_activity_title": "Activity",
        "ctx_activity_ready": "Ready",
        "ctx_activity_generating": "Generating bug report...",
        "ctx_activity_saving": "Saving Word document...",
        "ctx_activity_error": "Error",
        "ctx_attachments_title": "Attachments",
        "ctx_attachments_template": "{images} screenshots, {docs} documents",
        "ctx_attachments_empty": "Nothing attached yet.",
        "ctx_cost_title": "Session cost",
        "ctx_cost_calls_template": "{calls} calls / {tokens} tokens",
        "ctx_cost_session_template": "${cost:.4f} this session",
        "ctx_provider_template": "{provider} - {model}",
        "ctx_last_save_title": "Last save",
        "ctx_last_save_empty": "Nothing saved yet.",
    },
    "cs": {
        "nav_label": "AI Bug Report",
        "title": "AI Bug Report",
        "subtitle": (
            "Hod sem popis, screenshoty nebo logy - AI sama doplní název, kroky k "
            "reprodukci, očekávaný vs skutečný výsledek a uloží to do hezkýho Wordu."
        ),

        "tab_input": "Vstup",
        "tab_preview": "Náhled",
        "tab_export": "Export",

        "step_input_label": "KROK 1",
        "step_input_title": "Popiš chybu",
        "step_input_desc": (
            "Napiš co se stalo, co jsi čekal a co se reálně stalo - cokoli pomůže. "
            "Dole připoj screenshoty nebo logy. Když něco chybí, AI doplní rozumný "
            "odhad a označí ho jako odhadnutý."
        ),
        "description_label": "Co se stalo?",
        "description_hint": (
            "Příklad: 'Kliknutí na Uložit na profilu nedělá nic. Čekal jsem potvrzení "
            "a reload stránky, ale tlačítko jen zůstane v loading stavu.'"
        ),
        "env_label": "Prostředí (volitelné)",
        "env_hint": (
            "Prohlížeč / OS / zařízení / verze aplikace / URL - cokoli máš. Můžeš "
            "nechat prázdné a nechat AI ať si to vyčte ze screenshotů."
        ),
        "attachments_label": "Přílohy",
        "drop_title": "Sem pusť screenshoty, logy nebo PDF",
        "drop_hint": "PNG / JPG / WEBP pro screenshoty, TXT / LOG / JSON / PDF / DOCX / MD / HTML pro kontext",
        "unsupported": "Nepodporovaný typ souboru. Použij PNG / JPG / WEBP / GIF / BMP / TXT / LOG / JSON / PDF / DOCX / MD / HTML.",
        "upload_paste_path_btn": "Vložit cestu",
        "upload_paste_path_tooltip": "Tip pro Windows: ve Průzkumníku Shift+pravý klik na soubor -> Kopírovat jako cestu, pak klikni sem.",
        "upload_cta_label": "Klikni a vyber soubor",
        "no_attachments": "Žádné přílohy.",
        "remove_btn": "Odebrat",
        "attachment_image_badge": "OBR",
        "attachment_doc_badge": "DOK",

        "footer_demo_btn": "Vyzkoušet ukázková data",
        "footer_generate_btn": "Vygenerovat bug report",
        "footer_generate_running": "Generuji...",
        "generate_disabled_hint": "Přidej popis nebo aspoň jednu přílohu.",
        "input_requirement_hint": "Minimum vstup: vyplň popis nebo přidej aspoň jednu přílohu.",
        "no_key_template": "Chybí API klíč pro {provider}. Otevři Nastavení a klíč ulož.",

        "preview_empty": "Zatím nic. Spusť Generování na záložce Vstup.",
        "preview_back_btn": "Zpět na Vstup",
        "preview_regen_btn": "Znovu vygenerovat",
        "preview_title_label": "Název",
        "preview_summary_label": "Shrnutí",
        "preview_severity_label": "Závažnost",
        "preview_priority_label": "Priorita",
        "preview_repro_label": "Reprodukovatelnost",
        "preview_environment_label": "Prostředí",
        "preview_preconditions_label": "Předpoklady",
        "preview_str_label": "Kroky k reprodukci",
        "preview_expected_label": "Očekávaný výsledek",
        "preview_actual_label": "Skutečný výsledek",
        "preview_attachments_label": "Souhrn příloh",
        "preview_notes_label": "Další poznámky",

        "env_browser": "Prohlížeč",
        "env_os": "Operační systém",
        "env_device": "Zařízení",
        "env_app_version": "Verze aplikace",
        "env_url": "URL",

        "export_title": "Ulož bug report",
        "export_desc": (
            "Wordový dokument se shoduje s náhledem - název, tabulka prostředí, číslované "
            "kroky, očekávaný vs skutečný výsledek, vložené screenshoty, souhrn příloh. "
            "Vedle něj se uloží i markdown verze a summary.json."
        ),
        "export_save_btn": "Uložit jako Word",
        "export_open_folder_btn": "Otevřít složku s výstupy",
        "export_saved_template": "Uloženo do {path}",
        "export_save_failed": "Uložení selhalo: {error}",
        "export_run_first": "Nejdřív vygeneruj bug report.",

        "demo_pill": "DEMO",

        "how_to_title": "Jak používat AI Bug Report",
        "how_to_close": "Rozumím",
        "how_to_section_what": "Co umí",
        "how_to_what_text": (
            "Hoď sem cokoli co popisuje chybu - krátkou poznámku, dlouhý popis, "
            "screenshot rozbitý obrazovky, log soubor. AI to celé přečte a vyrobí "
            "strukturovaný bug report (název, závažnost, kroky, očekávaný vs skutečný "
            "výsledek). Když nějaké pole chybí, AI doplní nejlepší odhad a označí ho "
            "jako odhadnutý - radši dá rozumný odhad než prázdný report."
        ),
        "how_to_section_inputs": "Vstupy",
        "how_to_inputs_text": (
            "Text v popisu, volitelné poznámky o prostředí (prohlížeč / OS / URL) a "
            "libovolný počet screenshotů (PNG / JPG / WEBP / GIF / BMP / HEIC) nebo "
            "podpůrných souborů (TXT / LOG / JSON / PDF / DOCX / MD / HTML). Screenshoty "
            "jdou do modelu přes vision API; textové soubory se parsují lokálně."
        ),
        "how_to_section_quality": "Tipy na kvalitní report",
        "how_to_quality_text": (
            "Pokud to jde, přidej aspoň jeden screenshot - AI je výrazně přesnější u "
            "očekávaný vs skutečný, když vidí rozbitý stav. Stačí jednou zmínit "
            "prohlížeč / OS v popisu a tabulka prostředí se doplní sama. Po vygenerování "
            "můžeš název / závažnost / prioritu opravit přímo v náhledu před uložením."
        ),

        "ctx_section_label": "AI Bug Report",
        "ctx_activity_title": "Aktivita",
        "ctx_activity_ready": "Připraveno",
        "ctx_activity_generating": "Generuji bug report...",
        "ctx_activity_saving": "Ukládám Word...",
        "ctx_activity_error": "Chyba",
        "ctx_attachments_title": "Přílohy",
        "ctx_attachments_template": "{images} screenshotů, {docs} dokumentů",
        "ctx_attachments_empty": "Zatím nic nepřipojeno.",
        "ctx_cost_title": "Cena této session",
        "ctx_cost_calls_template": "{calls} volání / {tokens} tokenů",
        "ctx_cost_session_template": "${cost:.4f} tato session",
        "ctx_provider_template": "{provider} - {model}",
        "ctx_last_save_title": "Poslední uložení",
        "ctx_last_save_empty": "Zatím nic neuloženo.",
    },
}


def s(lang: str) -> dict[str, str]:
    return STRINGS.get(lang) or STRINGS["en"]
