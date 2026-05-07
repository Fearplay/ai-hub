"""AI Marketing - main center view (matches the design screenshot).

The first tab keeps the rich chat + phone-mockup composition. The other
six tabs (Social posts, Ads, Email, Landing, Strategy, Templates) are
swapped in via :func:`tabbed_panel` and use the shared mock helpers so
clicking around feels alive without any AI being wired up.
"""

from __future__ import annotations

import flet as ft

from src.components.chat_input import chat_input
from src.components.chat_message import chat_message
from src.components.header import header
from src.components.mock_panel import mock_card_grid_panel, mock_form_panel
from src.components.tabbed_panel import tabbed_panel
from src.i18n import t
from src.sections.ai_marketing.data import (
    SECTION_ICON,
    assistant_actions,
    tabs,
)
from src.sections.ai_marketing.phone_mockup import phone_mockup
from src.sections.ai_marketing.strings import s
from src.theme import Theme


def _section_heading(theme: Theme, icon: str, title: str) -> ft.Row:
    return ft.Row(
        controls=[
            ft.Icon(icon, color=theme.primary, size=16),
            ft.Text(
                title,
                color=theme.primary,
                size=13,
                weight=ft.FontWeight.W_700,
            ),
        ],
        spacing=6,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _check_bullet(theme: Theme, text: str) -> ft.Row:
    return ft.Row(
        controls=[
            ft.Icon(
                ft.Icons.CHECK_BOX_OUTLINED,
                color="#22C55E",
                size=18,
            ),
            ft.Text(text, color=theme.text, size=14, expand=True, selectable=True),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _action_chip(theme: Theme, icon: str, label: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=theme.text_muted, size=14),
                ft.Text(label, color=theme.text, size=12),
            ],
            spacing=6,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        bgcolor=theme.surface,
        border_radius=8,
        border=ft.border.all(1, theme.border),
        ink=True,
        on_click=lambda e: None,
    )


def _assistant_message(theme: Theme, lang: str) -> ft.Row:
    txt = s(lang)

    headline_block = ft.Column(
        controls=[
            _section_heading(theme, ft.Icons.PUSH_PIN_OUTLINED, txt["msg2_headline_title"]),
            ft.Text(
                txt["msg2_headline_text"],
                color=theme.text,
                size=14,
                selectable=True,
            ),
        ],
        spacing=6,
        tight=True,
    )

    post_block = ft.Column(
        controls=[
            _section_heading(theme, ft.Icons.EDIT_OUTLINED, txt["msg2_post_title"]),
            ft.Text(
                txt["msg2_post_intro"],
                color=theme.text,
                size=14,
                selectable=True,
            ),
            ft.Column(
                controls=[
                    _check_bullet(theme, txt["msg2_check1"]),
                    _check_bullet(theme, txt["msg2_check2"]),
                    _check_bullet(theme, txt["msg2_check3"]),
                    _check_bullet(theme, txt["msg2_check4"]),
                ],
                spacing=4,
                tight=True,
            ),
            ft.Text(
                txt["msg2_cta"],
                color=theme.text,
                size=14,
                weight=ft.FontWeight.W_600,
                selectable=True,
            ),
            ft.Text(
                txt["msg2_hashtags"],
                color=theme.primary,
                size=13,
                selectable=True,
            ),
        ],
        spacing=10,
        tight=True,
        expand=True,
    )

    left_column = ft.Column(
        controls=[headline_block, post_block],
        spacing=14,
        expand=True,
        tight=True,
    )

    body_row = ft.Row(
        controls=[
            ft.Container(content=left_column, expand=True),
            phone_mockup(theme, lang),
        ],
        spacing=18,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    bubble = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(txt["msg2_intro"], color=theme.text, size=14, selectable=True),
                body_row,
            ],
            spacing=14,
            tight=True,
        ),
        padding=18,
        bgcolor=theme.assistant_bubble,
        border_radius=14,
    )

    actions_row = ft.Row(
        controls=[
            _action_chip(theme, a["icon"], a["label"])
            for a in assistant_actions(lang)
        ],
        spacing=8,
        wrap=True,
        run_spacing=8,
    )

    avatar = ft.Container(
        content=ft.Icon(SECTION_ICON, color=ft.Colors.WHITE, size=18),
        width=36,
        height=36,
        bgcolor=theme.primary,
        border_radius=10,
        alignment=ft.Alignment.CENTER,
    )

    body = ft.Column(
        controls=[
            ft.Container(
                content=ft.Text("10:42", color=theme.text_muted, size=11),
                padding=ft.padding.only(left=4),
            ),
            bubble,
            actions_row,
        ],
        spacing=10,
        expand=True,
        tight=True,
    )

    return ft.Row(
        controls=[avatar, body],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.START,
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

    return ft.ListView(
        controls=[user_msg, _assistant_message(theme, lang)],
        spacing=22,
        padding=ft.padding.symmetric(horizontal=24, vertical=20),
        expand=True,
        auto_scroll=False,
    )


def _social_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=ft.Icons.PHOTO_LIBRARY_OUTLINED,
        title=txt["social_title"],
        description=txt["social_desc"],
        fields=[
            {"label": t("mock_field_topic", lang), "hint": txt["social_field_topic_hint"]},
            {"label": txt["social_field_channel"], "hint": txt["social_field_channel_hint"]},
            {"label": t("mock_field_audience", lang), "hint": t("mock_field_audience_hint", lang)},
            {"label": t("mock_field_tone", lang), "hint": t("mock_field_tone_hint", lang)},
            {"label": txt["social_field_body"], "hint": txt["social_field_body_hint"], "multiline": True},
        ],
        examples=[txt["social_example_1"], txt["social_example_2"], txt["social_example_3"]],
    )


def _ads_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=ft.Icons.CAMPAIGN_OUTLINED,
        title=txt["ads_title"],
        description=txt["ads_desc"],
        fields=[
            {"label": txt["ads_field_product"], "hint": txt["ads_field_product_hint"]},
            {"label": t("mock_field_audience", lang), "hint": t("mock_field_audience_hint", lang)},
            {"label": txt["ads_field_goal"], "hint": txt["ads_field_goal_hint"]},
            {"label": txt["ads_field_format"], "hint": txt["ads_field_format_hint"]},
            {"label": t("mock_field_tone", lang), "hint": t("mock_field_tone_hint", lang)},
        ],
        examples=[txt["ads_example_1"], txt["ads_example_2"], txt["ads_example_3"]],
    )


def _email_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=ft.Icons.MAIL_OUTLINE,
        title=txt["email_title"],
        description=txt["email_desc"],
        fields=[
            {"label": txt["email_field_subject"], "hint": txt["email_field_subject_hint"]},
            {"label": t("mock_field_audience", lang), "hint": txt["email_field_audience_hint"]},
            {"label": txt["email_field_intro"], "hint": txt["email_field_intro_hint"], "multiline": True},
            {"label": t("mock_field_tone", lang), "hint": t("mock_field_tone_hint", lang)},
        ],
        examples=[txt["email_example_1"], txt["email_example_2"], txt["email_example_3"]],
    )


def _landing_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=ft.Icons.ARTICLE_OUTLINED,
        title=txt["landing_title"],
        description=txt["landing_desc"],
        fields=[
            {"label": txt["landing_field_offer"], "hint": txt["landing_field_offer_hint"]},
            {"label": t("mock_field_audience", lang), "hint": txt["landing_field_audience_hint"]},
            {"label": txt["landing_field_pains"], "hint": txt["landing_field_pains_hint"], "multiline": True},
            {"label": t("mock_field_tone", lang), "hint": t("mock_field_tone_hint", lang)},
        ],
        examples=[txt["landing_example_1"], txt["landing_example_2"], txt["landing_example_3"]],
    )


def _strategy_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=ft.Icons.INSIGHTS_OUTLINED,
        title=txt["strategy_title"],
        description=txt["strategy_desc"],
        fields=[
            {"label": txt["strategy_field_brand"], "hint": txt["strategy_field_brand_hint"]},
            {"label": t("mock_field_audience", lang), "hint": t("mock_field_audience_hint", lang)},
            {"label": txt["strategy_field_goal"], "hint": txt["strategy_field_goal_hint"]},
            {"label": txt["strategy_field_budget"], "hint": txt["strategy_field_budget_hint"]},
            {"label": txt["strategy_field_duration"], "hint": txt["strategy_field_duration_hint"]},
        ],
        examples=[txt["strategy_example_1"], txt["strategy_example_2"], txt["strategy_example_3"]],
    )


def _templates_panel(theme: Theme, lang: str) -> ft.Control:
    txt = s(lang)
    cards = [
        {
            "icon": ft.Icons.PHOTO_CAMERA_OUTLINED,
            "title": txt["tpl_instagram_title"],
            "description": txt["tpl_instagram_desc"],
            "action_label": txt["tpl_use"],
            "color": "#E1306C",
        },
        {
            "icon": ft.Icons.THUMB_UP_OUTLINED,
            "title": txt["tpl_facebook_title"],
            "description": txt["tpl_facebook_desc"],
            "action_label": txt["tpl_use"],
            "color": "#1877F2",
        },
        {
            "icon": ft.Icons.WORK_OUTLINE,
            "title": txt["tpl_linkedin_title"],
            "description": txt["tpl_linkedin_desc"],
            "action_label": txt["tpl_use"],
            "color": "#0A66C2",
        },
        {
            "icon": ft.Icons.ALTERNATE_EMAIL,
            "title": txt["tpl_x_title"],
            "description": txt["tpl_x_desc"],
            "action_label": txt["tpl_use"],
            "color": "#1F2937",
        },
        {
            "icon": ft.Icons.MAIL_OUTLINE,
            "title": txt["tpl_email_title"],
            "description": txt["tpl_email_desc"],
            "action_label": txt["tpl_use"],
            "color": "#F59E0B",
        },
        {
            "icon": ft.Icons.WEB_OUTLINED,
            "title": txt["tpl_landing_title"],
            "description": txt["tpl_landing_desc"],
            "action_label": txt["tpl_use"],
            "color": "#22C55E",
        },
    ]
    return mock_card_grid_panel(
        theme,
        lang,
        icon=ft.Icons.GRID_VIEW_OUTLINED,
        title=txt["templates_title"],
        description=txt["templates_desc"],
        cards=cards,
    )


def build_view(theme: Theme, lang: str) -> ft.Column:
    txt = s(lang)

    panels = [
        _chat_panel(theme, lang),
        _social_panel(theme, lang),
        _ads_panel(theme, lang),
        _email_panel(theme, lang),
        _landing_panel(theme, lang),
        _strategy_panel(theme, lang),
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
