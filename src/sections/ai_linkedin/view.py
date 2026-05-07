"""AI LinkedIn - main center view.

Mirrors the rich chat layout used by AI Marketing: the user pastes a
few notes about their week and the assistant returns a structured post
draft (Hook / Body / Bullets / CTA / Hashtags). Six other tabs use the
shared mock helpers so the section feels alive even before any AI is
wired up.
"""

from __future__ import annotations

import flet as ft

from src.components.chat_input import chat_input
from src.components.chat_message import chat_message
from src.components.header import header
from src.components.mock_panel import mock_card_grid_panel, mock_form_panel
from src.components.tabbed_panel import tabbed_panel
from src.i18n import t
from src.sections.ai_linkedin.data import SECTION_ICON, assistant_actions, tabs
from src.sections.ai_linkedin.strings import s
from src.theme import Theme


def _hashtag_block(theme: Theme, label: str, text: str) -> ft.Column:
    heading = ft.Row(
        controls=[
            ft.Icon(ft.Icons.TAG, color=theme.primary, size=16),
            ft.Text(label, color=theme.primary, size=13, weight=ft.FontWeight.W_700),
        ],
        spacing=6,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    return ft.Column(
        controls=[
            heading,
            ft.Text(text, color=theme.primary, size=13, selectable=True),
        ],
        spacing=8,
        tight=True,
    )


def _chat_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)

    user_msg = chat_message(
        theme,
        lang,
        avatar_icon=SECTION_ICON,
        role="user",
        time="10:42",
        text=txt["msg1_user"],
    )

    assistant_sections = [
        {
            "icon": ft.Icons.PUSH_PIN_OUTLINED,
            "title": txt["msg2_hook_title"],
            "text": txt["msg2_hook_text"],
        },
        {
            "icon": ft.Icons.EDIT_OUTLINED,
            "title": txt["msg2_body_title"],
            "text": txt["msg2_body_text"],
        },
        {
            "icon": ft.Icons.CHECKLIST_OUTLINED,
            "title": txt["msg2_bullets_title"],
            "bullets": [txt["msg2_bullet1"], txt["msg2_bullet2"], txt["msg2_bullet3"]],
        },
        {
            "icon": ft.Icons.QUESTION_ANSWER_OUTLINED,
            "title": txt["msg2_cta_title"],
            "text": txt["msg2_cta_text"],
        },
    ]

    assistant_msg = chat_message(
        theme,
        lang,
        avatar_icon=SECTION_ICON,
        role="assistant",
        time="10:42",
        text=txt["msg2_intro"],
        sections=assistant_sections,
        extra=_hashtag_block(theme, txt["msg2_hashtags_title"], txt["msg2_hashtags_text"]),
        actions=assistant_actions(lang),
    )

    return ft.ListView(
        controls=[user_msg, assistant_msg],
        spacing=22,
        padding=ft.padding.symmetric(horizontal=24, vertical=20),
        expand=True,
        auto_scroll=False,
    )


def _post_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=ft.Icons.EDIT_OUTLINED,
        title=txt["post_title"],
        description=txt["post_desc"],
        fields=[
            {"label": txt["post_field_idea"], "hint": txt["post_field_idea_hint"], "multiline": True},
            {"label": txt["post_field_goal"], "hint": txt["post_field_goal_hint"]},
            {"label": txt["post_field_format"], "hint": txt["post_field_format_hint"]},
            {"label": t("mock_field_audience", lang), "hint": t("mock_field_audience_hint", lang)},
            {"label": t("mock_field_tone", lang), "hint": t("mock_field_tone_hint", lang)},
        ],
        examples=[txt["post_example_1"], txt["post_example_2"], txt["post_example_3"]],
    )


def _carousel_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=ft.Icons.VIEW_CAROUSEL_OUTLINED,
        title=txt["carousel_title"],
        description=txt["carousel_desc"],
        fields=[
            {"label": t("mock_field_topic", lang), "hint": txt["carousel_field_topic_hint"]},
            {"label": txt["carousel_field_takeaway"], "hint": txt["carousel_field_takeaway_hint"]},
            {"label": txt["carousel_field_slides"], "hint": txt["carousel_field_slides_hint"]},
            {"label": t("mock_field_tone", lang), "hint": t("mock_field_tone_hint", lang)},
        ],
        examples=[txt["carousel_example_1"], txt["carousel_example_2"], txt["carousel_example_3"]],
    )


def _article_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=ft.Icons.ARTICLE_OUTLINED,
        title=txt["article_title"],
        description=txt["article_desc"],
        fields=[
            {"label": t("mock_field_topic", lang), "hint": t("mock_field_topic_hint", lang)},
            {"label": txt["article_field_thesis"], "hint": txt["article_field_thesis_hint"]},
            {"label": txt["article_field_outline"], "hint": txt["article_field_outline_hint"], "multiline": True},
            {"label": t("mock_field_audience", lang), "hint": txt["article_field_audience_hint"]},
            {"label": t("mock_field_tone", lang), "hint": t("mock_field_tone_hint", lang)},
        ],
        examples=[txt["article_example_1"], txt["article_example_2"], txt["article_example_3"]],
    )


def _headlines_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=ft.Icons.LIGHTBULB_OUTLINE,
        title=txt["headlines_title"],
        description=txt["headlines_desc"],
        fields=[
            {"label": t("mock_field_topic", lang), "hint": txt["headlines_field_topic_hint"]},
            {"label": txt["headlines_field_angles"], "hint": txt["headlines_field_angles_hint"]},
            {"label": t("mock_field_tone", lang), "hint": t("mock_field_tone_hint", lang)},
        ],
        examples=[txt["headlines_example_1"], txt["headlines_example_2"], txt["headlines_example_3"]],
    )


def _comments_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=ft.Icons.CHAT_BUBBLE_OUTLINE,
        title=txt["comments_title"],
        description=txt["comments_desc"],
        fields=[
            {"label": txt["comments_field_post"], "hint": txt["comments_field_post_hint"], "multiline": True},
            {"label": txt["comments_field_angle"], "hint": txt["comments_field_angle_hint"]},
            {"label": t("mock_field_tone", lang), "hint": t("mock_field_tone_hint", lang)},
        ],
        examples=[txt["comments_example_1"], txt["comments_example_2"], txt["comments_example_3"]],
    )


def _templates_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    cards = [
        {
            "icon": ft.Icons.NEW_RELEASES_OUTLINED,
            "title": txt["tpl_announcement_title"],
            "description": txt["tpl_announcement_desc"],
            "action_label": txt["tpl_use"],
            "color": "#0A66C2",
        },
        {
            "icon": ft.Icons.SCHOOL_OUTLINED,
            "title": txt["tpl_lesson_title"],
            "description": txt["tpl_lesson_desc"],
            "action_label": txt["tpl_use"],
            "color": "#7C5CFC",
        },
        {
            "icon": ft.Icons.WORK_OUTLINE,
            "title": txt["tpl_hiring_title"],
            "description": txt["tpl_hiring_desc"],
            "action_label": txt["tpl_use"],
            "color": "#22C55E",
        },
        {
            "icon": ft.Icons.EMOJI_EVENTS_OUTLINED,
            "title": txt["tpl_milestone_title"],
            "description": txt["tpl_milestone_desc"],
            "action_label": txt["tpl_use"],
            "color": "#F59E0B",
        },
        {
            "icon": ft.Icons.QUESTION_ANSWER_OUTLINED,
            "title": txt["tpl_thread_title"],
            "description": txt["tpl_thread_desc"],
            "action_label": txt["tpl_use"],
            "color": "#0EA5E9",
        },
        {
            "icon": ft.Icons.FAVORITE_BORDER,
            "title": txt["tpl_personal_title"],
            "description": txt["tpl_personal_desc"],
            "action_label": txt["tpl_use"],
            "color": "#EF4444",
        },
    ]
    return mock_card_grid_panel(
        theme,
        lang,
        icon=ft.Icons.GRID_VIEW_OUTLINED,
        title=txt["tpl_title"],
        description=txt["tpl_desc"],
        cards=cards,
    )


def build_view(theme: Theme, lang: str) -> ft.Column:
    txt = s(lang)

    panels = [
        _chat_panel(theme, lang),
        _post_panel(theme, lang),
        _carousel_panel(theme, lang),
        _article_panel(theme, lang),
        _headlines_panel(theme, lang),
        _comments_panel(theme, lang),
        _templates_panel(theme, lang),
    ]

    return ft.Column(
        controls=[
            header(
                theme,
                lang,
                icon=SECTION_ICON,
                title=txt["title"],
                subtitle=txt["subtitle"],
            ),
            tabbed_panel(theme, tabs=tabs(lang), panels=panels),
            chat_input(theme, lang),
        ],
        spacing=0,
        expand=True,
        tight=True,
    )
