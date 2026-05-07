"""Mock chat / context data for the AI Marketing section."""

from __future__ import annotations

import flet as ft

from src.sections.ai_marketing.strings import s


SECTION_ICON = ft.Icons.CAMPAIGN_OUTLINED


def tabs(lang: str) -> list[str]:
    txt = s(lang)
    return [
        txt["tab_chat"],
        txt["tab_social"],
        txt["tab_ads"],
        txt["tab_email"],
        txt["tab_landing"],
        txt["tab_strategy"],
        txt["tab_templates"],
    ]


def assistant_actions(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"icon": ft.Icons.CONTENT_COPY, "label": txt["action_copy"]},
        {"icon": ft.Icons.IMAGE_OUTLINED, "label": txt["action_image"]},
        {"icon": ft.Icons.UNFOLD_LESS, "label": txt["action_shorten"]},
        {"icon": ft.Icons.MOOD_OUTLINED, "label": txt["action_tone"]},
        {"icon": ft.Icons.TRANSLATE, "label": txt["action_translate"]},
    ]


def brief_fields(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"label": txt["brief_product_label"], "value": txt["brief_product"]},
        {"label": txt["brief_audience_label"], "value": txt["brief_audience"]},
        {"label": txt["brief_goal_label"], "value": txt["brief_goal"]},
        {"label": txt["brief_tone_label"], "value": txt["brief_tone"], "chip": True},
        {"label": txt["brief_lang_label"], "value": txt["brief_lang"]},
    ]


def quick_actions(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"icon": ft.Icons.PHOTO_LIBRARY_OUTLINED, "label": txt["qa_social"]},
        {"icon": ft.Icons.CAMPAIGN_OUTLINED, "label": txt["qa_ad"]},
        {"icon": ft.Icons.MAIL_OUTLINE, "label": txt["qa_email"]},
        {"icon": ft.Icons.ARTICLE_OUTLINED, "label": txt["qa_landing"]},
        {"icon": ft.Icons.INSIGHTS_OUTLINED, "label": txt["qa_strategy"]},
    ]


def history(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"title": txt["history_1"], "time": txt["history_1_time"], "pinned": True},
        {"title": txt["history_2"], "time": txt["history_2_time"]},
        {"title": txt["history_3"], "time": txt["history_3_time"]},
        {"title": txt["history_4"], "time": txt["history_4_time"]},
    ]
