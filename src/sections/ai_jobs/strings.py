"""EN + CS copy for the AI Jobs section.

Keep keys grouped roughly by where they appear in the UI:

* sidebar / header
* tab labels
* setup form (steps, hints, button labels, validation messages)
* location presets + work modes
* activity / status badges
* results tab (cards, save dialog, empty states)
* history tab
* how-to dialog
* shared menu / quick-action labels (mirrors the convention used by
  the ai_career and ai_finance sections)
"""

from __future__ import annotations


STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # sidebar / header ------------------------------------------------
        "nav_label": "AI Job Search",
        "title": "AI Job Search",
        "subtitle": "Describe the role (or upload your CV), pick a location, and let AI scour the web for active openings.",

        # tab labels ------------------------------------------------------
        "tab_setup": "Setup",
        "tab_results": "Results",
        "tab_history": "History",

        # setup hero ------------------------------------------------------
        "setup_hero_title": "Find positions worth applying to",
        "setup_hero_desc": "Tell AI what you are looking for. The more context you give (CV, short bio, target keywords), the closer the matches. Active postings only - dead links are dropped before you see them.",

        # step 1 - keywords ----------------------------------------------
        "step_1_label": "STEP 1",
        "step_1_title": "What role are you after?",
        "step_1_desc": "Type the job title or keywords. AI auto-expands them with synonyms (e.g. 'QA Engineer' also matches 'Tester' and 'Quality Engineer').",
        "keywords_hint": "QA software engineer, Python backend developer, data analyst...",
        "keywords_synonyms_note": "Synonyms and adjacent roles are added automatically.",

        # step 2 - profile -----------------------------------------------
        "step_2_label": "STEP 2",
        "step_2_title": "Your profile (optional)",
        "step_2_desc": "Drop your CV, paste a short bio about yourself, or share a LinkedIn URL. Any combination works - AI uses whatever you give to refine the matches.",
        "profile_text_label": "About you (free text)",
        "profile_text_hint": "I am a QA engineer with 4 years of experience in API testing, automation in Playwright, and CI in GitLab. I am looking for a senior role...",
        "profile_file_label": "Upload your CV / LinkedIn export (PDF / DOCX / TXT / HTML)",
        "profile_file_drop_title": "Drop your CV here",
        "profile_file_drop_hint": "or click to browse the disk",
        "profile_file_no_file": "No file selected",
        "profile_file_unsupported": "Unsupported file type. Use PDF, DOCX, TXT or HTML.",
        "profile_file_clear": "Clear",
        "linkedin_label": "Public LinkedIn profile URL (optional)",
        "linkedin_hint": "https://www.linkedin.com/in/your-handle",

        # step 3 - location ----------------------------------------------
        "step_3_label": "STEP 3",
        "step_3_title": "Where should AI look?",
        "step_3_desc": "Pick a region or city. Postings outside the chosen location are ignored.",
        "location_preset_label": "Location",
        "location_custom_label": "Custom location",
        "location_custom_hint": "e.g. Prague + 30 km, or Berlin / Munich",

        # step 4 - filters -----------------------------------------------
        "step_4_label": "STEP 4",
        "step_4_title": "Filters",
        "step_4_desc": "Optional - leave on 'Any' if it doesn't matter.",
        "work_mode_label": "Work setup",
        "max_results_label": "Number of results to fetch",
        "max_results_hint": "Each result triggers a quick URL verification, so larger numbers take longer.",

        # location presets -----------------------------------------------
        "loc_any": "Anywhere",
        "loc_remote_world": "Remote (worldwide)",
        "loc_eu": "European Union",
        "loc_usa": "United States",
        "loc_uk": "United Kingdom",
        "loc_cz": "Czech Republic",
        "loc_sk": "Slovakia",
        "loc_de": "Germany",
        "loc_at": "Austria",
        "loc_pl": "Poland",
        "loc_praha": "Prague",
        "loc_brno": "Brno",
        "loc_ostrava": "Ostrava",
        "loc_custom": "Custom (free text)...",

        # work modes -----------------------------------------------------
        "mode_any": "Any",
        "mode_remote": "Remote",
        "mode_hybrid": "Hybrid",
        "mode_onsite": "On-site",

        # footer ---------------------------------------------------------
        "run_btn": "Search positions",
        "run_running": "Searching the web...",
        "run_extracting": "Structuring results...",
        "run_verifying": "Verifying links...",
        "run_disabled_hint": "Add a job title (or your CV / bio) to start searching.",
        "error_no_key_template": "Your {provider} API key is not saved yet. Open Settings to add it.",
        "search_failed_template": "Search failed: {error}",
        "search_done_template": "Found {count} active positions ({dropped} link(s) skipped because they were dead or redirected).",
        "search_done_no_drops_template": "Found {count} active positions.",
        "search_zero_results": "AI returned no positions for this query. Try broader keywords or a different location.",

        # results tab ----------------------------------------------------
        "results_title": "Found positions",
        "results_subtitle_template": "{count} active openings - sorted by relevance.",
        "results_empty_title": "No search yet",
        "results_empty_desc": "Open Setup, fill in at least the role (or your CV) and click Search positions.",
        "results_meta_company": "Company",
        "results_meta_location": "Location",
        "results_meta_posted": "Posted",
        "results_meta_source": "Source",
        "results_open_btn": "Open posting",
        "results_copy_btn": "Copy link",
        "results_copied_template": "Link copied: {url}",
        "results_save_btn": "Save as HTML",
        "results_saving": "Saving...",
        "results_save_done_template": "Saved to {path}",
        "results_save_failed_template": "Save failed: {error}",
        "results_summary_title": "AI summary",
        "results_query_template": "Query: {query}",
        "results_location_template": "Location: {location}",
        "results_dropped_note_template": "{count} link(s) were dropped during verification.",

        # history tab ----------------------------------------------------
        "history_title": "Past searches",
        "history_subtitle": "Each saved search is kept on disk so you can re-open the HTML or delete the folder.",
        "history_empty_title": "No saved searches yet",
        "history_empty_desc": "Run a search and click Save as HTML to keep it for later.",
        "history_open_folder_btn": "Open folder",
        "history_delete_btn": "Delete",
        "history_refresh_btn": "Refresh",
        "history_query_template": "{query}",
        "history_location_template": "{location}",
        "history_count_template": "{count} positions",

        # right-hand context panel ---------------------------------------
        "ctx_cost_title": "Session cost",
        "ctx_cost_calls_template": "{calls} calls \u00b7 {tokens} tokens",
        "ctx_cost_session_template": "~${cost:.2f} this session",
        "ctx_provider_template": "{provider} \u00b7 {model}",
        "ctx_activity_title": "Activity",
        "ctx_activity_ready": "Ready",
        "ctx_activity_searching": "Searching the web...",
        "ctx_activity_extracting": "Structuring results...",
        "ctx_activity_verifying": "Verifying links...",
        "ctx_activity_saving": "Saving HTML...",
        "ctx_activity_error": "Error",
        "ctx_quick_actions_title": "Quick actions",
        "ctx_qa_new_search": "New search",
        "ctx_qa_open_results": "Open results",
        "ctx_qa_show_history": "Open history",
        "ctx_qa_open_folder": "Open output folder",
        "ctx_qa_open_how_to": "How to use this assistant",
        "ctx_last_run_title": "Last search",
        "ctx_last_run_empty": "No search has been run yet.",

        # header overflow menu -------------------------------------------
        "menu_new_search": "New search",
        "menu_save_html": "Save results as HTML",
        "menu_open_folder": "Open output folder",
        "menu_show_history": "Show history",
        "menu_how_to": "How to use this assistant",
        "menu_save_no_run": "Run a search first - there is nothing to save yet.",
        "menu_open_folder_no_run": "No saved searches yet - save one first.",

        # how-to dialog --------------------------------------------------
        "how_to_title": "How to use this assistant",
        "how_to_section_what": "What this section does",
        "how_to_what_text": "AI Job Search asks the model's hosted web search to find currently open positions matching your role keywords (or your CV / bio) and location. It then verifies every URL with the built-in scraper, drops any dead or expired links, and shows the survivors as cards you can open or save as a single HTML file.",
        "how_to_section_inputs": "Inputs you should prepare",
        "how_to_inputs_text": "At minimum: a job title (e.g. 'QA software engineer'). Optionally a CV (PDF / DOCX / TXT / HTML), a short bio about yourself, or your public LinkedIn URL - anything you provide makes the matches more relevant. Pick a location preset or type a custom region.",
        "how_to_section_quality": "Quality tips",
        "how_to_quality_text": "Bigger 'number of results' values cost more tokens and take longer (each link is HTTP-verified in parallel). Use the cheapest model that gives good output and pre-filter with a specific location - 'European Union' is fine but 'Prague + 30 km' returns tighter matches. Save your OpenAI / Anthropic key in Settings before searching.",
        "how_to_close": "Got it",
    },
    "cs": {
        # sidebar / header ------------------------------------------------
        "nav_label": "AI Hled\u00e1n\u00ed pr\u00e1ce",
        "title": "AI Hled\u00e1n\u00ed pr\u00e1ce",
        "subtitle": "Pop\u011b\u0161 pozici (nebo nahraj \u017eivotopis), zvol lokalitu a AI prohled\u00e1 web po aktivn\u00edch nab\u00eddk\u00e1ch.",

        # tab labels ------------------------------------------------------
        "tab_setup": "Nastaven\u00ed",
        "tab_results": "V\u00fdsledky",
        "tab_history": "Historie",

        # setup hero ------------------------------------------------------
        "setup_hero_title": "Najdi pozice, na kter\u00e9 stoj\u00ed za to reagovat",
        "setup_hero_desc": "\u0158ekni AI, co hled\u00e1\u0161. \u010c\u00edm v\u00edc kontextu d\u00e1\u0161 (\u017eivotopis, kr\u00e1tk\u00e9 bio, c\u00edlov\u00e9 kl\u00ed\u010dov\u00e9 slova), t\u00edm p\u0159esn\u011bj\u0161\u00ed shody. Ukazujeme jen aktivn\u00ed inzer\u00e1ty - mrtv\u00e9 odkazy zahod\u00edme d\u0159\u00edv, ne\u017e je uvid\u00ed\u0161.",

        # step 1 - keywords ----------------------------------------------
        "step_1_label": "KROK 1",
        "step_1_title": "Jakou roli hled\u00e1\u0161?",
        "step_1_desc": "Napi\u0161 n\u00e1zev pozice nebo kl\u00ed\u010dov\u00e1 slova. AI sama p\u0159id\u00e1 synonyma (nap\u0159. 'QA Engineer' pokryje i 'Tester' nebo 'Quality Engineer').",
        "keywords_hint": "QA software engineer, Python backend developer, data anal\u00fdza...",
        "keywords_synonyms_note": "Synonyma a p\u0159\u00edbuzn\u00e9 role se p\u0159id\u00e1vaj\u00ed automaticky.",

        # step 2 - profile -----------------------------------------------
        "step_2_label": "KROK 2",
        "step_2_title": "Tv\u016fj profil (voliteln\u00e9)",
        "step_2_desc": "P\u0159etr\u00e1hni \u017eivotopis, vlo\u017e kr\u00e1tk\u00fd popis sebe nebo URL na LinkedIn profil. M\u016f\u017ee\u0161 d\u00e1t libovolnou kombinaci - AI vyu\u017eije v\u0161e, co m\u00e1.",
        "profile_text_label": "O sob\u011b (voln\u00fd text)",
        "profile_text_hint": "Jsem QA engineer se 4 lety zku\u0161enost\u00ed v testov\u00e1n\u00ed API, automatizaci v Playwrightu a CI v GitLabu. Hled\u00e1m senior roli...",
        "profile_file_label": "Nahraj \u017eivotopis / LinkedIn export (PDF / DOCX / TXT / HTML)",
        "profile_file_drop_title": "P\u0159et\u00e1hni svoje CV sem",
        "profile_file_drop_hint": "nebo klikni a vyber z disku",
        "profile_file_no_file": "Nen\u00ed vybr\u00e1n \u017e\u00e1dn\u00fd soubor",
        "profile_file_unsupported": "Nepodporovan\u00fd typ souboru. Pou\u017eij PDF, DOCX, TXT nebo HTML.",
        "profile_file_clear": "Vy\u010distit",
        "linkedin_label": "Ve\u0159ejn\u00fd LinkedIn profil URL (voliteln\u00e9)",
        "linkedin_hint": "https://www.linkedin.com/in/tvoje-jmeno",

        # step 3 - location ----------------------------------------------
        "step_3_label": "KROK 3",
        "step_3_title": "Kde m\u00e1 AI hledat?",
        "step_3_desc": "Vyber region nebo m\u011bsto. Inzer\u00e1ty mimo zvolenou lokalitu se ignoruj\u00ed.",
        "location_preset_label": "Lokalita",
        "location_custom_label": "Vlastn\u00ed lokalita",
        "location_custom_hint": "nap\u0159. Praha + 30 km, nebo Berl\u00edn / Mnichov",

        # step 4 - filters -----------------------------------------------
        "step_4_label": "KROK 4",
        "step_4_title": "Filtry",
        "step_4_desc": "Voliteln\u00e9 - pokud na tom nez\u00e1le\u017e\u00ed, nech 'Cokoli'.",
        "work_mode_label": "Forma pr\u00e1ce",
        "max_results_label": "Po\u010det v\u00fdsledk\u016f, kter\u00e9 chce\u0161 st\u00e1hnout",
        "max_results_hint": "Ka\u017ed\u00fd v\u00fdsledek spou\u0161t\u00ed rychl\u00e9 ov\u011b\u0159en\u00ed URL, vy\u0161\u0161\u00ed \u010d\u00edsla zaberou v\u00edc \u010dasu.",

        # location presets -----------------------------------------------
        "loc_any": "Kdekoli",
        "loc_remote_world": "Remote (cel\u00fd sv\u011bt)",
        "loc_eu": "Evropsk\u00e1 unie",
        "loc_usa": "Spojen\u00e9 st\u00e1ty",
        "loc_uk": "Spojen\u00e9 kr\u00e1lovstv\u00ed",
        "loc_cz": "\u010cesk\u00e1 republika",
        "loc_sk": "Slovensko",
        "loc_de": "N\u011bmecko",
        "loc_at": "Rakousko",
        "loc_pl": "Polsko",
        "loc_praha": "Praha",
        "loc_brno": "Brno",
        "loc_ostrava": "Ostrava",
        "loc_custom": "Vlastn\u00ed (voln\u00fd text)...",

        # work modes -----------------------------------------------------
        "mode_any": "Cokoli",
        "mode_remote": "Remote",
        "mode_hybrid": "Hybridn\u00ed",
        "mode_onsite": "Na pracovi\u0161ti",

        # footer ---------------------------------------------------------
        "run_btn": "Hledat pozice",
        "run_running": "Prohled\u00e1v\u00e1m web...",
        "run_extracting": "Strukturalizuju v\u00fdsledky...",
        "run_verifying": "Ov\u011b\u0159uji odkazy...",
        "run_disabled_hint": "Doplnit n\u00e1zev pozice (nebo \u017eivotopis / bio), ab\u016fch mohl/a hledat.",
        "error_no_key_template": "API kl\u00ed\u010d pro {provider} je\u0161t\u011b nen\u00ed ulo\u017een. Otev\u0159i Nastaven\u00ed a p\u0159idej ho.",
        "search_failed_template": "Hled\u00e1n\u00ed selhalo: {error}",
        "search_done_template": "Na\u0161el jsem {count} aktivn\u00edch pozic ({dropped} odkaz(\u016f) jsem zahodil, proto\u017ee byly mrtv\u00e9 nebo p\u0159esm\u011brovan\u00e9).",
        "search_done_no_drops_template": "Na\u0161el jsem {count} aktivn\u00edch pozic.",
        "search_zero_results": "AI nena\u0161la \u017e\u00e1dnou pozici pro tento dotaz. Zkus \u0161ir\u0161\u00ed kl\u00ed\u010dov\u00e1 slova nebo jinou lokalitu.",

        # results tab ----------------------------------------------------
        "results_title": "Nalezen\u00e9 pozice",
        "results_subtitle_template": "{count} aktivn\u00edch nab\u00eddek - se\u0159azeno podle relevance.",
        "results_empty_title": "Zat\u00edm \u017e\u00e1dn\u00e9 hled\u00e1n\u00ed",
        "results_empty_desc": "Otev\u0159i Nastaven\u00ed, doplnit aspo\u0148 roli (nebo \u017eivotopis) a klikni na Hledat pozice.",
        "results_meta_company": "Firma",
        "results_meta_location": "Lokalita",
        "results_meta_posted": "Vlo\u017eeno",
        "results_meta_source": "Zdroj",
        "results_open_btn": "Otev\u0159\u00edt inzer\u00e1t",
        "results_copy_btn": "Kop\u00edrovat odkaz",
        "results_copied_template": "Odkaz zkop\u00edrov\u00e1n: {url}",
        "results_save_btn": "Ulo\u017eit jako HTML",
        "results_saving": "Ukl\u00e1d\u00e1m...",
        "results_save_done_template": "Ulo\u017eeno do {path}",
        "results_save_failed_template": "Ulo\u017een\u00ed selhalo: {error}",
        "results_summary_title": "Shrnut\u00ed od AI",
        "results_query_template": "Dotaz: {query}",
        "results_location_template": "Lokalita: {location}",
        "results_dropped_note_template": "{count} odkaz(\u016f) bylo b\u011bhem ov\u011b\u0159ov\u00e1n\u00ed zahozeno.",

        # history tab ----------------------------------------------------
        "history_title": "P\u0159edchoz\u00ed hled\u00e1n\u00ed",
        "history_subtitle": "Ka\u017ed\u00e9 ulo\u017een\u00e9 hled\u00e1n\u00ed z\u016fst\u00e1v\u00e1 na disku, ab\u016fchom mohl/a otev\u0159\u00edt HTML nebo slo\u017eku smazat.",
        "history_empty_title": "Zat\u00edm \u017e\u00e1dn\u00e9 ulo\u017een\u00e9 hled\u00e1n\u00ed",
        "history_empty_desc": "Spus\u0165 hled\u00e1n\u00ed a klikni na Ulo\u017eit jako HTML, ab\u016fchom ho m\u011bli na pozd\u011bji.",
        "history_open_folder_btn": "Otev\u0159\u00edt slo\u017eku",
        "history_delete_btn": "Smazat",
        "history_refresh_btn": "Obnovit",
        "history_query_template": "{query}",
        "history_location_template": "{location}",
        "history_count_template": "{count} pozic",

        # right-hand context panel ---------------------------------------
        "ctx_cost_title": "N\u00e1klady relace",
        "ctx_cost_calls_template": "{calls} vol\u00e1n\u00ed \u00b7 {tokens} token\u016f",
        "ctx_cost_session_template": "~${cost:.2f} v t\u00e9to relaci",
        "ctx_provider_template": "{provider} \u00b7 {model}",
        "ctx_activity_title": "Aktivita",
        "ctx_activity_ready": "P\u0159ipraveno",
        "ctx_activity_searching": "Prohled\u00e1v\u00e1m web...",
        "ctx_activity_extracting": "Strukturalizuju v\u00fdsledky...",
        "ctx_activity_verifying": "Ov\u011b\u0159uji odkazy...",
        "ctx_activity_saving": "Ukl\u00e1d\u00e1m HTML...",
        "ctx_activity_error": "Chyba",
        "ctx_quick_actions_title": "Rychl\u00e9 akce",
        "ctx_qa_new_search": "Nov\u00e9 hled\u00e1n\u00ed",
        "ctx_qa_open_results": "Otev\u0159\u00edt v\u00fdsledky",
        "ctx_qa_show_history": "Otev\u0159\u00edt historii",
        "ctx_qa_open_folder": "Otev\u0159\u00edt v\u00fdstupn\u00ed slo\u017eku",
        "ctx_qa_open_how_to": "Jak pou\u017e\u00edvat tohoto asistenta",
        "ctx_last_run_title": "Posledn\u00ed hled\u00e1n\u00ed",
        "ctx_last_run_empty": "Hled\u00e1n\u00ed je\u0161t\u011b neprob\u011bhlo.",

        # header overflow menu -------------------------------------------
        "menu_new_search": "Nov\u00e9 hled\u00e1n\u00ed",
        "menu_save_html": "Ulo\u017eit v\u00fdsledky jako HTML",
        "menu_open_folder": "Otev\u0159\u00edt v\u00fdstupn\u00ed slo\u017eku",
        "menu_show_history": "Otev\u0159\u00edt historii",
        "menu_how_to": "Jak pou\u017e\u00edvat tohoto asistenta",
        "menu_save_no_run": "Spus\u0165 nejprve hled\u00e1n\u00ed - zat\u00edm nen\u00ed co ukl\u00e1dat.",
        "menu_open_folder_no_run": "Zat\u00edm \u017e\u00e1dn\u00e9 ulo\u017een\u00e9 hled\u00e1n\u00ed - nejprve n\u011bjak\u00e9 ulo\u017e.",

        # how-to dialog --------------------------------------------------
        "how_to_title": "Jak pou\u017e\u00edvat tohoto asistenta",
        "how_to_section_what": "Co tahle sekce d\u011bl\u00e1",
        "how_to_what_text": "AI Hled\u00e1n\u00ed pr\u00e1ce vyu\u017e\u00edv\u00e1 vestav\u011bn\u00fd web search providera, aby na\u0161la aktu\u00e1ln\u011b otev\u0159en\u00e9 pozice odpov\u00eddaj\u00edc\u00ed tv\u00fdm kl\u00ed\u010dov\u00fdm slov\u016fm (nebo \u017eivotopisu / bio) a lokalit\u011b. Pak ka\u017edou URL ov\u011b\u0159\u00ed vestav\u011bn\u00fdm scraperem, mrtv\u00e9 nebo expirovan\u00e9 odkazy zahod\u00ed a zb\u00fdvaj\u00edc\u00ed zobraz\u00ed jako karti\u010dky, kter\u00e9 m\u016f\u017ee\u0161 otev\u0159\u00edt nebo ulo\u017eit do jednoho HTML souboru.",
        "how_to_section_inputs": "Co si p\u0159ichystat",
        "how_to_inputs_text": "Minim\u00e1ln\u011b: n\u00e1zev pozice (nap\u0159. 'QA software engineer'). Voliteln\u011b: \u017eivotopis (PDF / DOCX / TXT / HTML), kr\u00e1tk\u00e9 bio o sob\u011b nebo ve\u0159ejn\u00fd LinkedIn URL - cokoli p\u0159id\u00e1\u0161, zp\u0159esn\u00ed shody. Vyber preset lokality nebo napi\u0161 vlastn\u00ed.",
        "how_to_section_quality": "Tipy na kvalitu",
        "how_to_quality_text": "V\u011bt\u0161\u00ed 'po\u010det v\u00fdsledk\u016f' stoj\u00ed v\u00edc token\u016f a trv\u00e1 d\u00e9l (ka\u017ed\u00fd odkaz se ov\u011b\u0159uje paraleln\u011b p\u0159es HTTP). Pou\u017e\u00edvej nejlevn\u011bj\u0161\u00ed model, kter\u00fd d\u00e1v\u00e1 dobr\u00e9 v\u00fdsledky, a c\u00edluj specifickou lokalitu - 'Evropsk\u00e1 unie' je OK, ale 'Praha + 30 km' vrac\u00ed t\u011bsn\u011bj\u0161\u00ed shody. Ne\u017e za\u010dne\u0161 hledat, ulo\u017e si OpenAI / Anthropic kl\u00ed\u010d v Nastaven\u00ed.",
        "how_to_close": "Rozum\u00edm",
    },
}


def s(lang: str) -> dict[str, str]:
    return STRINGS.get(lang) or STRINGS["en"]
