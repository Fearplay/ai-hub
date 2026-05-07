"""Mock chat / context data for the AI LinkedIn section."""

from __future__ import annotations

import flet as ft

from src.sections.ai_linkedin.strings import s


SECTION_ICON = ft.Icons.HUB_OUTLINED


def tabs(lang: str) -> list[str]:
    txt = s(lang)
    return [
        txt["tab_chat"],
        txt["tab_post"],
        txt["tab_carousel"],
        txt["tab_article"],
        txt["tab_headlines"],
        txt["tab_comments"],
        txt["tab_templates"],
    ]


def assistant_actions(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"icon": ft.Icons.CONTENT_COPY, "label": txt["action_copy"]},
        {"icon": ft.Icons.UNFOLD_LESS, "label": txt["action_shorten"]},
        {"icon": ft.Icons.TAG, "label": txt["action_hashtags"]},
        {"icon": ft.Icons.MOOD_OUTLINED, "label": txt["action_tone"]},
        {"icon": ft.Icons.SCHEDULE_OUTLINED, "label": txt["action_schedule"]},
    ]


def brand_profile_fields(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"label": txt["brief_name_label"], "value": txt["brief_name"]},
        {"label": txt["brief_role_label"], "value": txt["brief_role"]},
        {"label": txt["brief_industry_label"], "value": txt["brief_industry"]},
        {"label": txt["brief_audience_label"], "value": txt["brief_audience"]},
        {"label": txt["brief_tone_label"], "value": txt["brief_tone"], "chip": True},
    ]


def quick_actions(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"icon": ft.Icons.EDIT_OUTLINED, "label": txt["qa_post"]},
        {"icon": ft.Icons.AUTO_FIX_HIGH, "label": txt["qa_polish"]},
        {"icon": ft.Icons.LIGHTBULB_OUTLINE, "label": txt["qa_headlines"]},
        {"icon": ft.Icons.CHAT_BUBBLE_OUTLINE, "label": txt["qa_comment"]},
        {"icon": ft.Icons.PERSON_ADD_ALT_OUTLINED, "label": txt["qa_connection"]},
    ]


def history(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"title": txt["history_1"], "time": txt["history_1_time"], "pinned": True},
        {"title": txt["history_2"], "time": txt["history_2_time"]},
        {"title": txt["history_3"], "time": txt["history_3_time"]},
        {"title": txt["history_4"], "time": txt["history_4_time"]},
    ]
