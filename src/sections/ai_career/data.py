"""Mock chat / context data for the AI Career section."""

from __future__ import annotations

import flet as ft

from src.sections.ai_career.strings import s


SECTION_ICON = ft.Icons.WORK_OUTLINE


def messages(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {
            "role": "user",
            "time": "10:24",
            "text": txt["msg1_user"],
        },
        {
            "role": "assistant",
            "time": "10:24",
            "text": txt["msg2_text"],
            "bullets": [
                txt["msg2_bullet1"],
                txt["msg2_bullet2"],
                txt["msg2_bullet3"],
                txt["msg2_bullet4"],
                txt["msg2_bullet5"],
                txt["msg2_bullet6"],
            ],
            "footer": txt["msg2_footer"],
            "actions": [
                {"icon": ft.Icons.AUTO_AWESOME, "label": txt["action_template"]},
                {"icon": ft.Icons.VISIBILITY_OUTLINED, "label": txt["action_sample"]},
                {"icon": ft.Icons.ARTICLE_OUTLINED, "label": txt["action_form"]},
            ],
        },
        {
            "role": "user",
            "time": "10:25",
            "text": txt["msg3_user"],
        },
        {
            "role": "assistant",
            "time": "10:25",
            "text": txt["msg4_text"],
            "attachment": {
                "name": txt["attachment_name"],
                "type": "DOCX",
                "size": "24 kB",
            },
        },
    ]


def context_docs(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"name": txt["doc_my_cv"], "type": "PDF", "size": "142 kB"},
        {"name": txt["doc_cover_letter"], "type": "DOCX", "size": "32 kB"},
    ]


def quick_actions(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"icon": ft.Icons.MAIL_OUTLINE, "label": txt["qa_cover_letter"]},
        {"icon": ft.Icons.HELP_OUTLINE, "label": txt["qa_interview"]},
        {"icon": ft.Icons.DESCRIPTION_OUTLINED, "label": txt["qa_job_offer"]},
        {"icon": ft.Icons.PERSON_OUTLINE, "label": txt["qa_linkedin"]},
    ]


def history(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"title": txt["history_1"], "time": txt["history_1_time"]},
        {"title": txt["history_2"], "time": txt["history_2_time"]},
        {"title": txt["history_3"], "time": txt["history_3_time"]},
        {"title": txt["history_4"], "time": txt["history_4_time"]},
    ]
