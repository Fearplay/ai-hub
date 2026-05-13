"""AI Marketing - main center view (matches the design screenshot).

The first tab keeps the rich chat + phone-mockup composition. The other
six tabs (Social posts, Ads, Email, Landing, Strategy, Templates) are
swapped in via :func:`tabbed_panel` and use the shared mock helpers so
clicking around feels alive without any AI being wired up.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.components.chat_input import chat_input
from src.components.chat_message import chat_message
from src.components.header import header
from src.components.mock_panel import mock_card_grid_panel, mock_form_panel
from src.components.tabbed_panel import tabbed_panel
from src.i18n import t
from src.qt.icons import Icons
from src.qt.widgets import (
    AccentLabel,
    BodyLabel,
    ClickFrame,
    IconLabel,
    MutedLabel,
    custom_label,
    hbox,
    vbox,
)
from src.sections.ai_marketing.data import (
    SECTION_ICON,
    assistant_actions,
    tabs,
)
from src.sections.ai_marketing.phone_mockup import phone_mockup
from src.sections.ai_marketing.strings import s
from src.services import logger as logger_service
from src.theme import Theme


def _section_heading(theme: Theme, icon: str, title: str) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = hbox(spacing=6, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    layout.addWidget(IconLabel(icon, color=theme.primary, size=16))
    layout.addWidget(AccentLabel(title, theme=theme, size=13, weight=QFont.Weight.Bold))
    layout.addStretch(1)
    return holder


def _check_bullet(theme: Theme, text: str) -> QFrame:
    row = QFrame()
    row.setStyleSheet("background: transparent;")
    layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    row.setLayout(layout)
    layout.addWidget(IconLabel(Icons.CHECK_BOX_OUTLINED, color="#22C55E", size=18))
    label = BodyLabel(text, theme=theme, size=14, selectable=True)
    label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    layout.addWidget(label, 1)
    return row


def _action_chip(theme: Theme, icon: str, label: str) -> ClickFrame:
    chip = ClickFrame()
    chip.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 8px;
        }}
        ClickFrame:hover {{
            background-color: {theme.surface_2};
        }}
        """
    )
    layout = hbox(spacing=6, margins=(10, 6, 10, 6))
    chip.setLayout(layout)
    layout.addWidget(IconLabel(icon, color=theme.text_muted, size=14))
    layout.addWidget(BodyLabel(label, theme=theme, size=12))
    return chip


def _assistant_message(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    avatar = QFrame()
    avatar.setFixedSize(36, 36)
    avatar.setStyleSheet(f"background-color: {theme.primary}; border-radius: 10px;")
    avatar_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    avatar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    avatar.setLayout(avatar_layout)
    avatar_layout.addWidget(IconLabel(SECTION_ICON, color="#FFFFFF", size=18),
                            alignment=Qt.AlignmentFlag.AlignCenter)

    headline_block = QFrame()
    headline_block.setStyleSheet("background: transparent;")
    head_layout = vbox(spacing=6, margins=(0, 0, 0, 0))
    headline_block.setLayout(head_layout)
    head_layout.addWidget(_section_heading(theme, Icons.PUSH_PIN_OUTLINED, txt["msg2_headline_title"]))
    head_layout.addWidget(BodyLabel(txt["msg2_headline_text"], theme=theme, size=14, selectable=True))

    post_block = QFrame()
    post_block.setStyleSheet("background: transparent;")
    post_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    post_block.setLayout(post_layout)
    post_layout.addWidget(_section_heading(theme, Icons.EDIT_OUTLINED, txt["msg2_post_title"]))
    post_layout.addWidget(BodyLabel(txt["msg2_post_intro"], theme=theme, size=14, selectable=True))

    bullets = QFrame()
    bullets.setStyleSheet("background: transparent;")
    bullets_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    bullets.setLayout(bullets_layout)
    bullets_layout.addWidget(_check_bullet(theme, txt["msg2_check1"]))
    bullets_layout.addWidget(_check_bullet(theme, txt["msg2_check2"]))
    bullets_layout.addWidget(_check_bullet(theme, txt["msg2_check3"]))
    bullets_layout.addWidget(_check_bullet(theme, txt["msg2_check4"]))
    post_layout.addWidget(bullets)

    cta = BodyLabel(txt["msg2_cta"], theme=theme, size=14, weight=QFont.Weight.DemiBold, selectable=True)
    post_layout.addWidget(cta)
    hashtags = custom_label(txt["msg2_hashtags"], color=theme.primary, size=13, selectable=True)
    post_layout.addWidget(hashtags)

    left_holder = QFrame()
    left_holder.setStyleSheet("background: transparent;")
    left_layout = vbox(spacing=14, margins=(0, 0, 0, 0))
    left_holder.setLayout(left_layout)
    left_layout.addWidget(headline_block)
    left_layout.addWidget(post_block)

    body_row_holder = QFrame()
    body_row_holder.setStyleSheet("background: transparent;")
    body_row_layout = hbox(spacing=18, margins=(0, 0, 0, 0))
    body_row_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    body_row_holder.setLayout(body_row_layout)
    body_row_layout.addWidget(left_holder, 1)
    body_row_layout.addWidget(phone_mockup(theme, lang))

    bubble = QFrame()
    bubble.setStyleSheet(
        f"background-color: {theme.assistant_bubble}; border-radius: 14px;"
    )
    bubble_layout = vbox(spacing=14, margins=(18, 18, 18, 18))
    bubble.setLayout(bubble_layout)
    bubble_layout.addWidget(BodyLabel(txt["msg2_intro"], theme=theme, size=14, selectable=True))
    bubble_layout.addWidget(body_row_holder)

    actions = QFrame()
    actions.setStyleSheet("background: transparent;")
    actions_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    actions.setLayout(actions_layout)
    for a in assistant_actions(lang):
        actions_layout.addWidget(_action_chip(theme, a["icon"], a["label"]))
    actions_layout.addStretch(1)

    body_holder = QFrame()
    body_holder.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    body_holder.setLayout(body_layout)
    body_layout.addWidget(MutedLabel("10:42", theme=theme, size=11))
    body_layout.addWidget(bubble)
    body_layout.addWidget(actions)

    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    wrap_layout = QHBoxLayout(wrapper)
    wrap_layout.setContentsMargins(0, 0, 0, 0)
    wrap_layout.setSpacing(12)
    wrap_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    wrap_layout.addWidget(avatar)
    wrap_layout.addWidget(body_holder, 1)
    return wrapper


def _chat_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    user_msg = chat_message(
        theme,
        lang,
        avatar_icon=SECTION_ICON,
        role="user",
        time="10:42",
        text=txt["msg1_user"],
    )

    holder = QWidget()
    holder.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=22, margins=(24, 20, 24, 20))
    holder.setLayout(layout)
    layout.addWidget(user_msg)
    layout.addWidget(_assistant_message(theme, lang))
    layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(holder)
    return scroll


def _social_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=Icons.PHOTO_LIBRARY_OUTLINED,
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


def _ads_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=Icons.CAMPAIGN_OUTLINED,
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


def _email_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=Icons.MAIL_OUTLINE,
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


def _landing_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=Icons.ARTICLE_OUTLINED,
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


def _strategy_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=Icons.INSIGHTS_OUTLINED,
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


def _templates_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    cards = [
        {"icon": Icons.PHOTO_CAMERA_OUTLINED, "title": txt["tpl_instagram_title"], "description": txt["tpl_instagram_desc"], "action_label": txt["tpl_use"], "color": "#E1306C"},
        {"icon": Icons.THUMB_UP_OUTLINED, "title": txt["tpl_facebook_title"], "description": txt["tpl_facebook_desc"], "action_label": txt["tpl_use"], "color": "#1877F2"},
        {"icon": Icons.WORK_OUTLINE, "title": txt["tpl_linkedin_title"], "description": txt["tpl_linkedin_desc"], "action_label": txt["tpl_use"], "color": "#0A66C2"},
        {"icon": Icons.ALTERNATE_EMAIL, "title": txt["tpl_x_title"], "description": txt["tpl_x_desc"], "action_label": txt["tpl_use"], "color": "#1F2937"},
        {"icon": Icons.MAIL_OUTLINE, "title": txt["tpl_email_title"], "description": txt["tpl_email_desc"], "action_label": txt["tpl_use"], "color": "#F59E0B"},
        {"icon": Icons.WEB_OUTLINED, "title": txt["tpl_landing_title"], "description": txt["tpl_landing_desc"], "action_label": txt["tpl_use"], "color": "#22C55E"},
    ]
    return mock_card_grid_panel(theme, lang, icon=Icons.GRID_VIEW_OUTLINED, title=txt["templates_title"], description=txt["templates_desc"], cards=cards)


def build_view(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    try:
        panels = [
            _chat_panel(theme, lang),
            _social_panel(theme, lang),
            _ads_panel(theme, lang),
            _email_panel(theme, lang),
            _landing_panel(theme, lang),
            _strategy_panel(theme, lang),
            _templates_panel(theme, lang),
        ]
    except Exception as exc:
        logger_service.log_exception("ai_marketing.view", "build_panels_failed", exc)
        raise

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    layout.addWidget(header(theme, lang, icon=SECTION_ICON, title=txt["title"], subtitle=txt["subtitle"]))
    layout.addWidget(tabbed_panel(theme, tabs=tabs(lang), panels=panels), 1)
    layout.addWidget(chat_input(theme, lang))

    return container
