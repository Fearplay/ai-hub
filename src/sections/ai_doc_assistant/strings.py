"""EN + CS copy for the AI Doc Assistant section.

This is the "version B" alternative to the simpler ``ai_documents``
placeholder: a full AI assistant for arbitrary PDF / DOCX / TXT / HTML
files. The user uploads a document, picks an action (summarise, ask a
question, rewrite a section, extract action items) and gets a
structured output.
"""

from __future__ import annotations


STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "nav_label": "AI Doc Assistant",
        "title": "AI Doc Assistant",
        "subtitle": "Upload a document and let the AI summarise it, answer questions, or rewrite a section.",

        "tab_upload": "Upload",
        "tab_analyze": "Analyze",
        "tab_output": "Output",

        "step_1_label": "STEP 1",
        "step_1_title": "Upload a document",
        "step_1_desc": "Drop a PDF, DOCX, TXT, MD or HTML file. The AI works only with the text it can extract - scanned PDFs need OCR first.",
        "drop_title": "Drop your document here",
        "drop_hint": "or click to browse the disk",
        "no_file": "No file selected",
        "unsupported": "Unsupported file type. Use PDF, DOCX, TXT, MD or HTML.",
        "clear_btn": "Clear",
        "preview_label": "Preview (first 800 characters)",

        "step_2_label": "STEP 2",
        "step_2_title": "Pick an action",
        "step_2_desc": "What should the AI do with the document?",
        "action_summary": "Summarise",
        "action_summary_desc": "TL;DR + key bullet points + action items.",
        "action_qa": "Ask a question",
        "action_qa_desc": "Get an answer grounded in the document only.",
        "action_rewrite": "Rewrite a section",
        "action_rewrite_desc": "Improve clarity / tone of a passage you paste in.",
        "action_extract": "Extract data",
        "action_extract_desc": "Pull out names, dates, numbers, and other facts as a table.",

        "qa_question_label": "Your question",
        "qa_question_hint": "What is the deadline for the submission?",
        "rewrite_passage_label": "Passage to rewrite",
        "rewrite_passage_hint": "Paste the part you want the AI to improve...",
        "rewrite_tone_label": "Target tone",
        "rewrite_tone_options": "neutral | formal | friendly | concise | technical",

        "footer_demo_btn": "Try demo data",
        "footer_run_btn": "Run",
        "footer_run_running": "Working...",
        "run_disabled_hint": "Upload a document and pick an action to run.",
        "no_key_template": "Missing API key for {provider}. Open Settings and save your key first.",

        "output_empty": "Nothing to show yet. Run an action on the Analyze tab.",
        "output_summary_title": "Summary",
        "output_bullets_title": "Key points",
        "output_actions_title": "Action items",
        "output_answer_title": "Answer",
        "output_evidence_title": "Evidence from the document",
        "output_rewrite_title": "Rewritten passage",
        "output_extract_title": "Extracted facts",
        "output_back_btn": "Back to Analyze",
        "output_copy_btn": "Copy",
        "output_copied": "Copied!",

        "demo_pill": "DEMO",

        "how_to_title": "How to use AI Doc Assistant",
        "how_to_close": "Got it",
        "how_to_section_what": "What it does",
        "how_to_what_text": "Upload one document and ask the AI to summarise it, answer a specific question, rewrite a passage, or extract structured data. Every answer is grounded in the document text - the AI is told never to invent facts.",
        "how_to_section_inputs": "Supported files",
        "how_to_inputs_text": "PDF, DOCX, TXT, MD, HTML. Scanned PDFs need OCR first - the AI cannot read images. Files larger than ~50 pages are truncated to keep the cost predictable.",
        "how_to_section_quality": "Tips for better answers",
        "how_to_quality_text": "Pick the most specific action you can. Asking 'What is the deadline?' beats 'Summarise this'. For rewrites, paste only the passage you actually want changed - not the whole document.",
    },
    "cs": {
        "nav_label": "AI Asistent dokumentů",
        "title": "AI Asistent dokumentů",
        "subtitle": "Nahraj dokument a nech AI ať ho shrne, odpoví na otázku nebo přepíše pasáž.",

        "tab_upload": "Nahrát",
        "tab_analyze": "Analyzovat",
        "tab_output": "Výstup",

        "step_1_label": "KROK 1",
        "step_1_title": "Nahraj dokument",
        "step_1_desc": "Pusť sem PDF, DOCX, TXT, MD nebo HTML. AI pracuje jen s textem, který se z něj dá vytáhnout - skenované PDF potřebuje nejdřív OCR.",
        "drop_title": "Sem pusť dokument",
        "drop_hint": "nebo klikni a vyber ho z disku",
        "no_file": "Žádný soubor",
        "unsupported": "Nepodporovaný typ souboru. Použij PDF, DOCX, TXT, MD nebo HTML.",
        "clear_btn": "Smazat",
        "preview_label": "Náhled (prvních 800 znaků)",

        "step_2_label": "KROK 2",
        "step_2_title": "Vyber akci",
        "step_2_desc": "Co má AI s dokumentem udělat?",
        "action_summary": "Shrnout",
        "action_summary_desc": "TL;DR + klíčové body + úkoly k akci.",
        "action_qa": "Položit otázku",
        "action_qa_desc": "Odpověď striktně z obsahu dokumentu.",
        "action_rewrite": "Přepsat pasáž",
        "action_rewrite_desc": "Vylepšit srozumitelnost / tón vložené pasáže.",
        "action_extract": "Vytáhnout data",
        "action_extract_desc": "Vytáhnout jména, data, čísla a fakta do tabulky.",

        "qa_question_label": "Tvoje otázka",
        "qa_question_hint": "Jaký je termín odevzdání?",
        "rewrite_passage_label": "Pasáž k přepsání",
        "rewrite_passage_hint": "Sem vlož část textu, kterou má AI vylepšit...",
        "rewrite_tone_label": "Cílový tón",
        "rewrite_tone_options": "neutrální | formální | přátelský | stručný | technický",

        "footer_demo_btn": "Vyzkoušet ukázková data",
        "footer_run_btn": "Spustit",
        "footer_run_running": "Pracuji...",
        "run_disabled_hint": "Nahraj dokument a vyber akci.",
        "no_key_template": "Chybí API klíč pro {provider}. Otevři Nastavení a klíč ulož.",

        "output_empty": "Zatím nic. Spusť akci na záložce Analyzovat.",
        "output_summary_title": "Shrnutí",
        "output_bullets_title": "Klíčové body",
        "output_actions_title": "Úkoly k akci",
        "output_answer_title": "Odpověď",
        "output_evidence_title": "Důkazy z dokumentu",
        "output_rewrite_title": "Přepsaná pasáž",
        "output_extract_title": "Vytažená fakta",
        "output_back_btn": "Zpět na Analyzovat",
        "output_copy_btn": "Kopírovat",
        "output_copied": "Zkopírováno!",

        "demo_pill": "DEMO",

        "how_to_title": "Jak používat AI Asistent dokumentů",
        "how_to_close": "Rozumím",
        "how_to_section_what": "Co umí",
        "how_to_what_text": "Nahraj jeden dokument a nech AI ať ho shrne, odpoví na konkrétní otázku, přepíše pasáž nebo vytáhne strukturovaná data. Každá odpověď je opřená o text dokumentu - AI má zákaz cokoli vymýšlet.",
        "how_to_section_inputs": "Podporované soubory",
        "how_to_inputs_text": "PDF, DOCX, TXT, MD, HTML. Skenované PDF potřebuje nejdřív OCR - AI nečte obrázky. Soubory delší než cca 50 stran se zkracují, aby cena za jeden běh zůstala předvídatelná.",
        "how_to_section_quality": "Tipy na lepší odpovědi",
        "how_to_quality_text": "Vybírej co nejspecifičtější akci. \"Jaký je termín?\" funguje líp než \"Shrň to\". Pro přepis vlož jen tu část, kterou opravdu chceš změnit - ne celý dokument.",
    },
}


def s(lang: str) -> dict[str, str]:
    return STRINGS.get(lang) or STRINGS["en"]
