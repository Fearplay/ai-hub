"""AI Study - main center view (matches the design screenshot).

The Chat tab keeps the messages list **and** the recommended-sources
strip below it (the strip only makes sense in chat context). The other
five tabs (Summarise, Explain, Tasks & plan, Quizzes, Sources) swap in
mock panels.
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
from src.qt.theme import rgba
from src.qt.widgets import (
    AccentLabel,
    BodyLabel,
    ClickFrame,
    IconLabel,
    MutedLabel,
    hbox,
    vbox,
)
from src.sections.ai_study.data import (
    SECTION_ICON,
    assistant_actions,
    recommended_sources,
    tabs,
)
from src.sections.ai_study.strings import s
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


def _bullet_row(theme: Theme, text: str) -> QFrame:
    row = QFrame()
    row.setStyleSheet("background: transparent;")
    layout = hbox(spacing=6, margins=(0, 0, 0, 0))
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    row.setLayout(layout)

    bullet = BodyLabel("\u2022", theme=theme, size=14, weight=QFont.Weight.Bold)
    bullet.setFixedWidth(14)
    bullet.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(bullet)

    body = BodyLabel(text, theme=theme, size=14, selectable=True)
    body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    layout.addWidget(body, 1)
    return row


def _particles_artwork(theme: Theme) -> QFrame:
    """Decorative two-orb illustration painted with QFrames + radii."""
    primary = theme.primary

    def _orb(size: int, opacity: float) -> QFrame:
        orb = QFrame()
        orb.setFixedSize(size, size)
        orb.setStyleSheet(
            f"background-color: {rgba(primary, opacity)}; border-radius: {size // 2}px;"
        )
        return orb

    def _halo() -> QFrame:
        halo = QFrame()
        halo.setFixedSize(58, 58)
        halo.setStyleSheet(
            f"background-color: {rgba(primary, 0.18)}; border-radius: 29px;"
        )
        layout = hbox(spacing=0, margins=(0, 0, 0, 0))
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        halo.setLayout(layout)
        layout.addWidget(_orb(26, 0.95), alignment=Qt.AlignmentFlag.AlignCenter)
        return halo

    artwork = QFrame()
    artwork.setStyleSheet("background: transparent;")
    layout = hbox(spacing=2, margins=(12, 8, 12, 8))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    artwork.setLayout(layout)

    layout.addWidget(_halo())

    connector = QFrame()
    connector.setFixedSize(44, 2)
    connector.setStyleSheet(
        f"background-color: {rgba(primary, 0.55)}; border-radius: 1px;"
    )
    layout.addWidget(connector)

    layout.addWidget(_halo())

    return artwork


def _simple_block(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)

    block = QFrame()
    block.setObjectName("StudySimpleBlock")
    block.setStyleSheet(
        f"""
        QFrame#StudySimpleBlock {{
            background-color: {rgba(theme.primary_tint, 0.35)};
            border: 1px solid {rgba(theme.primary, 0.35)};
            border-radius: 12px;
        }}
        """
    )
    layout = hbox(spacing=14, margins=(14, 14, 14, 14))
    block.setLayout(layout)

    text_holder = QFrame()
    text_holder.setStyleSheet("background: transparent;")
    text_holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    text_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    text_holder.setLayout(text_layout)
    text_layout.addWidget(_section_heading(theme, Icons.LIGHTBULB_OUTLINE, txt["section_simple_title"]))
    text_layout.addWidget(BodyLabel(txt["section_simple_text"], theme=theme, size=13, selectable=True))
    layout.addWidget(text_holder, 1)
    layout.addWidget(_particles_artwork(theme))

    return block


def _keypoints_block(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    layout.addWidget(_section_heading(theme, Icons.PUSH_PIN_OUTLINED, txt["section_keypoints_title"]))
    body_holder = QFrame()
    body_holder.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    body_holder.setLayout(body_layout)
    body_layout.addWidget(_bullet_row(theme, txt["key_bullet1"]))
    body_layout.addWidget(_bullet_row(theme, txt["key_bullet2"]))
    body_layout.addWidget(_bullet_row(theme, txt["key_bullet3"]))
    body_layout.addWidget(_bullet_row(theme, txt["key_bullet4"]))
    layout.addWidget(body_holder)
    return holder


def _example_block(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    layout.addWidget(_section_heading(theme, Icons.AUTO_STORIES_OUTLINED, txt["section_example_title"]))
    layout.addWidget(BodyLabel(txt["section_example_text"], theme=theme, size=14, selectable=True))
    return holder


def _action_chip(theme: Theme, icon: str, label: str) -> ClickFrame:
    chip = ClickFrame()
    chip.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 20px;
        }}
        ClickFrame:hover {{
            background-color: {theme.surface_2};
        }}
        """
    )
    layout = hbox(spacing=6, margins=(12, 8, 12, 8))
    chip.setLayout(layout)
    layout.addWidget(IconLabel(icon, color=theme.primary, size=14))
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

    bubble = QFrame()
    bubble.setStyleSheet(
        f"background-color: {theme.assistant_bubble}; border-radius: 14px;"
    )
    bubble_layout = vbox(spacing=14, margins=(16, 16, 16, 16))
    bubble.setLayout(bubble_layout)
    bubble_layout.addWidget(BodyLabel(txt["msg2_intro"], theme=theme, size=14, selectable=True))
    bubble_layout.addWidget(_simple_block(theme, lang))
    bubble_layout.addWidget(_keypoints_block(theme, lang))
    bubble_layout.addWidget(_example_block(theme, lang))

    actions = QFrame()
    actions.setStyleSheet("background: transparent;")
    actions_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    actions.setLayout(actions_layout)
    for a in assistant_actions(lang):
        actions_layout.addWidget(_action_chip(theme, a["icon"], a["label"]))
    actions_layout.addStretch(1)

    body = QFrame()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)
    body_layout.addWidget(MutedLabel("10:24", theme=theme, size=11))
    body_layout.addWidget(bubble)
    body_layout.addWidget(actions)

    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    wrap_layout = QHBoxLayout(wrapper)
    wrap_layout.setContentsMargins(0, 0, 0, 0)
    wrap_layout.setSpacing(12)
    wrap_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    wrap_layout.addWidget(avatar)
    wrap_layout.addWidget(body, 1)
    return wrapper


def _source_card(theme: Theme, source: dict) -> ClickFrame:
    card = ClickFrame()
    card.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 10px;
        }}
        ClickFrame:hover {{
            background-color: {theme.surface_2};
        }}
        """
    )
    card.setFixedWidth(200)
    layout = hbox(spacing=10, margins=(10, 10, 10, 10))
    card.setLayout(layout)

    badge = QFrame()
    badge.setFixedSize(32, 32)
    badge.setStyleSheet(
        f"background-color: {source['color']}; border-radius: 8px;"
    )
    bl = hbox(spacing=0, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setLayout(bl)
    bl.addWidget(IconLabel(source["icon"], color="#FFFFFF", size=16),
                 alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(badge)

    info = QFrame()
    info.setStyleSheet("background: transparent;")
    info.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    info_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    info.setLayout(info_layout)
    info_layout.addWidget(BodyLabel(source["title"], theme=theme, size=12))
    info_layout.addWidget(MutedLabel(source["domain"], theme=theme, size=10))
    layout.addWidget(info, 1)

    return card


def _show_more(theme: Theme, label: str) -> ClickFrame:
    chip = ClickFrame()
    chip.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 10px;
        }}
        ClickFrame:hover {{
            background-color: {theme.surface_2};
        }}
        """
    )
    layout = hbox(spacing=4, margins=(12, 8, 12, 8))
    chip.setLayout(layout)
    layout.addWidget(BodyLabel(label, theme=theme, size=12))
    layout.addWidget(IconLabel(Icons.CHEVRON_RIGHT, color=theme.text_muted, size=16))
    return chip


def _sources_card(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    sources = recommended_sources(lang)

    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=8, margins=(24, 4, 24, 8))
    holder.setLayout(layout)

    layout.addWidget(MutedLabel(txt["sources_title"], theme=theme, size=12))

    row_holder = QFrame()
    row_holder.setStyleSheet("background: transparent;")
    row = hbox(spacing=10, margins=(0, 0, 0, 0))
    row_holder.setLayout(row)
    for src in sources:
        row.addWidget(_source_card(theme, src))
    row.addWidget(_show_more(theme, txt["source_show_more"]))
    row.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
    scroll.setMaximumHeight(70)
    scroll.setWidget(row_holder)
    layout.addWidget(scroll)

    return holder


def _chat_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    user_msg = chat_message(
        theme,
        lang,
        avatar_icon=SECTION_ICON,
        role="user",
        time="10:24",
        text=txt["msg1_user"],
    )

    messages_holder = QWidget()
    messages_layout = vbox(spacing=22, margins=(24, 20, 24, 20))
    messages_holder.setLayout(messages_layout)
    messages_layout.addWidget(user_msg)
    messages_layout.addWidget(_assistant_message(theme, lang))
    messages_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(messages_holder)

    panel = QWidget()
    panel_layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    panel.setLayout(panel_layout)
    panel_layout.addWidget(scroll, 1)
    panel_layout.addWidget(_sources_card(theme, lang))
    return panel


def _summary_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=Icons.SHORT_TEXT,
        title=txt["summary_title"],
        description=txt["summary_desc"],
        fields=[
            {"label": t("mock_field_topic", lang), "hint": txt["summary_field_topic_hint"]},
            {"label": txt["summary_field_input"], "hint": txt["summary_field_input_hint"], "multiline": True},
            {"label": txt["summary_field_format"], "hint": txt["summary_field_format_hint"]},
            {"label": t("mock_field_length", lang), "hint": t("mock_field_length_hint", lang)},
        ],
        examples=[txt["summary_example_1"], txt["summary_example_2"], txt["summary_example_3"]],
    )


def _explain_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=Icons.LIGHTBULB_OUTLINE,
        title=txt["explain_title"],
        description=txt["explain_desc"],
        fields=[
            {"label": txt["explain_field_term"], "hint": txt["explain_field_term_hint"]},
            {"label": txt["explain_field_level"], "hint": txt["explain_field_level_hint"]},
            {"label": txt["explain_field_context"], "hint": txt["explain_field_context_hint"], "multiline": True},
        ],
        examples=[txt["explain_example_1"], txt["explain_example_2"], txt["explain_example_3"]],
    )


def _tasks_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=Icons.EVENT_NOTE,
        title=txt["tasks_panel_title"],
        description=txt["tasks_panel_desc"],
        fields=[
            {"label": txt["tasks_field_subject"], "hint": txt["tasks_field_subject_hint"]},
            {"label": txt["tasks_field_deadline"], "hint": txt["tasks_field_deadline_hint"]},
            {"label": txt["tasks_field_hours"], "hint": txt["tasks_field_hours_hint"]},
            {"label": txt["tasks_field_focus"], "hint": txt["tasks_field_focus_hint"], "multiline": True},
        ],
        examples=[txt["tasks_example_1"], txt["tasks_example_2"], txt["tasks_example_3"]],
    )


def _quizzes_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    cards = [
        {"icon": Icons.SCIENCE_OUTLINED, "title": txt["quiz_physics_title"], "description": txt["quiz_physics_desc"], "action_label": txt["quiz_use"], "color": "#7C5CFC"},
        {"icon": Icons.FUNCTIONS, "title": txt["quiz_math_title"], "description": txt["quiz_math_desc"], "action_label": txt["quiz_use"], "color": "#38BDF8"},
        {"icon": Icons.CODE, "title": txt["quiz_code_title"], "description": txt["quiz_code_desc"], "action_label": txt["quiz_use"], "color": "#22C55E"},
        {"icon": Icons.TRENDING_UP, "title": txt["quiz_econ_title"], "description": txt["quiz_econ_desc"], "action_label": txt["quiz_use"], "color": "#F59E0B"},
    ]
    return mock_card_grid_panel(theme, lang, icon=Icons.QUIZ_OUTLINED, title=txt["quizzes_panel_title"], description=txt["quizzes_panel_desc"], cards=cards)


def _sources_panel(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    return mock_form_panel(
        theme,
        lang,
        icon=Icons.MENU_BOOK_OUTLINED,
        title=txt["sources_panel_title"],
        description=txt["sources_panel_desc"],
        fields=[
            {"label": txt["sources_field_topic"], "hint": txt["sources_field_topic_hint"]},
            {"label": txt["sources_field_type"], "hint": txt["sources_field_type_hint"]},
            {"label": txt["sources_field_lang"], "hint": txt["sources_field_lang_hint"]},
        ],
        examples=[txt["sources_example_1"], txt["sources_example_2"], txt["sources_example_3"]],
    )


def build_view(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    try:
        panels = [
            _chat_panel(theme, lang),
            _summary_panel(theme, lang),
            _explain_panel(theme, lang),
            _tasks_panel(theme, lang),
            _quizzes_panel(theme, lang),
            _sources_panel(theme, lang),
        ]
    except Exception as exc:
        logger_service.log_exception("ai_study.view", "build_panels_failed", exc)
        raise

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    layout.addWidget(header(theme, lang, icon=SECTION_ICON, title=txt["title"], subtitle=txt["subtitle"]))
    layout.addWidget(tabbed_panel(theme, tabs=tabs(lang), panels=panels), 1)
    layout.addWidget(chat_input(theme, lang))

    return container
