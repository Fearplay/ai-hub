"""Mock data for the AI Legal section.

Everything here is static demo content. Real data flow:
1. PDF arrives via :mod:`src.sections.ai_legal.drop_zone` (or via the upload
   button in the right context panel).
2. Mock analysis stats / chat messages stay constant - we don't run a real
   model. The shape of the data, however, matches what an LLM-backed
   pipeline would later return.
"""

from __future__ import annotations

import flet as ft

from src.sections.ai_legal.strings import s


SECTION_ICON = ft.Icons.GAVEL_OUTLINED

DEFAULT_UPLOADED_FILE: dict = {
    "name": "smlouva_o_dilo.pdf",
    "type": "PDF",
    "size": "245 kB",
}


def tabs(lang: str) -> list[str]:
    txt = s(lang)
    return [
        txt["tab_chat"],
        txt["tab_analysis"],
        txt["tab_drafts"],
        txt["tab_templates"],
    ]


def chat_quick_actions(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"icon": ft.Icons.SUMMARIZE_OUTLINED, "label": txt["chat_action_summarize"]},
        {"icon": ft.Icons.WARNING_AMBER_OUTLINED, "label": txt["chat_action_risks"]},
        {"icon": ft.Icons.MENU_BOOK_OUTLINED, "label": txt["chat_action_explain"]},
        {"icon": ft.Icons.EDIT_NOTE_OUTLINED, "label": txt["chat_action_changes"]},
    ]


def analysis_findings(lang: str) -> dict[str, list[str]]:
    txt = s(lang)
    return {
        "right": [
            txt["analysis_right_1"],
            txt["analysis_right_2"],
            txt["analysis_right_3"],
            txt["analysis_right_4"],
        ],
        "risk": [
            txt["analysis_risk_1"],
            txt["analysis_risk_2"],
            txt["analysis_risk_3"],
        ],
        "recommendations": [
            txt["analysis_recommendation_1"],
            txt["analysis_recommendation_2"],
        ],
    }


def analysis_markdown(lang: str) -> str:
    """Markdown body shown in the Analýza tab when 'Document' view is active."""
    findings = analysis_findings(lang)
    txt = s(lang)

    def _bullets(items: list[str], emoji: str) -> str:
        return "\n".join(f"- {emoji} {item}" for item in items)

    return (
        f"### {txt['analysis_doc_title']}\n\n"
        f"{txt['analysis_md_intro']}\n\n"
        f"## {txt['analysis_correct_title']}\n\n"
        f"{_bullets(findings['right'], '✅')}\n\n"
        f"## {txt['analysis_wrong_title']}\n\n"
        f"{_bullets(findings['risk'], '⚠️')}\n\n"
        f"## {txt['analysis_recommendations_title']}\n\n"
        f"{_bullets(findings['recommendations'], '💡')}\n"
    )


def drafts_diff(lang: str) -> list[str]:
    txt = s(lang)
    return [
        txt["drafts_diff_1"],
        txt["drafts_diff_2"],
        txt["drafts_diff_3"],
    ]


def drafts_preview_paragraphs(lang: str) -> list[str]:
    txt = s(lang)
    return [
        txt["drafts_preview_paragraph_1"],
        txt["drafts_preview_paragraph_2"],
        txt["drafts_preview_paragraph_3"],
        txt["drafts_preview_paragraph_4"],
    ]


def drafts_quick_actions(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"icon": ft.Icons.SENTIMENT_SATISFIED_OUTLINED, "label": txt["drafts_action_consumer"]},
        {"icon": ft.Icons.UNFOLD_LESS, "label": txt["drafts_action_shorter"]},
        {"icon": ft.Icons.SHIELD_OUTLINED, "label": txt["drafts_action_gdpr"]},
        {"icon": ft.Icons.UNDO, "label": txt["drafts_action_revert"]},
    ]


def templates(lang: str) -> list[dict]:
    """List of style templates shown as a 3x2 grid in the Šablony tab."""
    txt = s(lang)
    return [
        {
            "key": "modern",
            "label": txt["template_modern_label"],
            "desc": txt["template_modern_desc"],
            "heading_size": 22,
            "heading_weight": ft.FontWeight.W_700,
        },
        {
            "key": "classic",
            "label": txt["template_classic_label"],
            "desc": txt["template_classic_desc"],
            "heading_size": 20,
            "heading_weight": ft.FontWeight.W_600,
        },
        {
            "key": "minimal",
            "label": txt["template_minimal_label"],
            "desc": txt["template_minimal_desc"],
            "heading_size": 18,
            "heading_weight": ft.FontWeight.W_500,
        },
        {
            "key": "legal",
            "label": txt["template_legal_label"],
            "desc": txt["template_legal_desc"],
            "heading_size": 20,
            "heading_weight": ft.FontWeight.W_700,
        },
        {
            "key": "corporate",
            "label": txt["template_corporate_label"],
            "desc": txt["template_corporate_desc"],
            "heading_size": 22,
            "heading_weight": ft.FontWeight.W_700,
        },
        {
            "key": "academic",
            "label": txt["template_academic_label"],
            "desc": txt["template_academic_desc"],
            "heading_size": 21,
            "heading_weight": ft.FontWeight.W_600,
        },
    ]


COLORS: list[str] = [
    "#7C5CFC",
    "#3B82F6",
    "#06B6D4",
    "#22C55E",
    "#84CC16",
    "#EAB308",
    "#F97316",
    "#EF4444",
    "#EC4899",
    "#A855F7",
    "#1F2937",
    "#0F172A",
]


def fonts(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"key": "sans", "label": txt["font_sans_label"], "family": None},
        {"key": "serif", "label": txt["font_serif_label"], "family": "Times New Roman"},
        {"key": "mono", "label": txt["font_mono_label"], "family": "Courier New"},
        {"key": "display", "label": txt["font_display_label"], "family": "Verdana"},
    ]


def context_stats(lang: str) -> list[dict]:
    """Right-panel analysis statistics. status: ok | warn | info."""
    txt = s(lang)
    return [
        {
            "icon": ft.Icons.CHECK_CIRCLE_OUTLINED,
            "title": txt["ctx_stat_summary"],
            "desc": txt["ctx_stat_summary_desc"],
            "status": "ok",
        },
        {
            "icon": ft.Icons.WARNING_AMBER_OUTLINED,
            "title": txt["ctx_stat_risks"],
            "desc": txt["ctx_stat_risks_desc"],
            "status": "warn",
        },
        {
            "icon": ft.Icons.CHECK_CIRCLE_OUTLINED,
            "title": txt["ctx_stat_clauses"],
            "desc": txt["ctx_stat_clauses_desc"],
            "status": "ok",
        },
        {
            "icon": ft.Icons.INFO_OUTLINE,
            "title": txt["ctx_stat_recommendations"],
            "desc": txt["ctx_stat_recommendations_desc"],
            "status": "info",
        },
    ]


def context_quick_actions(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"icon": ft.Icons.MENU_BOOK_OUTLINED, "label": txt["ctx_qa_explain"]},
        {"icon": ft.Icons.WARNING_AMBER_OUTLINED, "label": txt["ctx_qa_check_risks"]},
        {"icon": ft.Icons.EDIT_NOTE_OUTLINED, "label": txt["ctx_qa_suggest_changes"]},
        {"icon": ft.Icons.COMPARE_ARROWS, "label": txt["ctx_qa_compare"]},
    ]
