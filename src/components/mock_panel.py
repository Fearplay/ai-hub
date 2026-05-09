"""Light mock panels for tabs that aren't wired to AI yet.

Two flavors:

* :func:`mock_form_panel`     - hero card + form fields + primary button.
  Used for "writer" / "generator" style tabs (Form mode, Social posts,
  Ads, Email campaigns, Budget, Summarise topic, ...).
* :func:`mock_card_grid_panel`- hero card + a wrap-grid of mock cards.
  Used for gallery-ish tabs (Templates, Quizzes, Calculators, Sources).

The chrome (hero card + scrollable body) is shared so every section feels
the same when you click between tabs.
"""

from __future__ import annotations

from typing import Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.i18n import t
from src.qt.icons import Icons
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    ClickFrame,
    GhostButton,
    IconLabel,
    MutedLabel,
    PrimaryButton,
    SubtleLabel,
    TitleLabel,
    hbox,
    themed_line_edit,
    themed_text_edit,
    vbox,
)
from src.theme import Theme


def _hero_card(theme: Theme, *, icon: str, title: str, description: str) -> QFrame:
    card = QFrame()
    card.setStyleSheet(
        f"""
        QFrame {{
            background-color: {rgba(theme.primary_tint, 0.35)};
            border: 1px solid {rgba(theme.primary, 0.35)};
            border-radius: 12px;
        }}
        """
    )
    layout = hbox(spacing=14, margins=(16, 16, 16, 16))
    card.setLayout(layout)

    icon_box = QFrame()
    icon_box.setFixedSize(44, 44)
    icon_box.setStyleSheet(f"background-color: {theme.primary}; border-radius: 12px;")
    icon_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setLayout(icon_layout)
    icon_layout.addWidget(IconLabel(icon, color="#FFFFFF", size=20),
                          alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(icon_box)

    text_holder = QFrame()
    text_holder.setStyleSheet("background: transparent;")
    text_holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    text_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    text_holder.setLayout(text_layout)
    text_layout.addWidget(TitleLabel(title, theme=theme, size=15))
    text_layout.addWidget(MutedLabel(description, theme=theme, size=12))
    layout.addWidget(text_holder, 1)

    return card


def _in_preparation_pill(theme: Theme, lang: str) -> QFrame:
    pill = QFrame()
    pill.setStyleSheet(
        f"""
        QFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 10px;
        }}
        """
    )
    layout = hbox(spacing=8, margins=(12, 10, 12, 10))
    pill.setLayout(layout)
    layout.addWidget(IconLabel(Icons.HOURGLASS_EMPTY_ROUNDED, color=theme.primary, size=14))
    label = MutedLabel(t("mock_in_preparation", lang), theme=theme, size=12)
    layout.addWidget(label, 1)
    return pill


def _text_field_block(theme: Theme, *, label: str, hint: str, multiline: bool = False) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=6, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    layout.addWidget(SubtleLabel(label, theme=theme, size=11))
    if multiline:
        edit = themed_text_edit(theme, placeholder=hint, min_height=84)
    else:
        edit = themed_line_edit(theme, placeholder=hint)
    layout.addWidget(edit)
    return holder


def _examples_card(theme: Theme, lang: str, examples: Sequence[str]) -> QFrame:
    card = QFrame()
    card.setStyleSheet(
        f"""
        QFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        """
    )
    card.setFixedWidth(240)
    layout = vbox(spacing=10, margins=(14, 14, 14, 14))
    card.setLayout(layout)

    layout.addWidget(SubtleLabel(t("mock_examples_title", lang), theme=theme, size=11))
    for line in examples:
        row = hbox(spacing=8, margins=(0, 0, 0, 0))
        row.addWidget(IconLabel(Icons.AUTO_AWESOME, color=theme.primary, size=14))
        body = BodyLabel(line, theme=theme, size=12, selectable=True)
        body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row.addWidget(body, 1)
        row_holder = QFrame()
        row_holder.setStyleSheet("background: transparent;")
        row_holder.setLayout(row)
        layout.addWidget(row_holder)
    return card


def _scrollable(content: QWidget, theme: Theme) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(content)
    return scroll


def mock_form_panel(
    theme: Theme,
    lang: str,
    *,
    icon: str,
    title: str,
    description: str,
    fields: Sequence[dict],
    button_label: Optional[str] = None,
    secondary_label: Optional[str] = None,
    examples: Optional[Sequence[str]] = None,
) -> QWidget:
    primary_label = button_label or t("mock_btn_generate", lang)
    save_label = secondary_label or t("mock_btn_save_draft", lang)

    page = QFrame()
    page.setStyleSheet(f"background-color: {theme.bg};")
    page_layout = vbox(spacing=14, margins=(24, 20, 24, 20))
    page.setLayout(page_layout)

    page_layout.addWidget(_hero_card(theme, icon=icon, title=title, description=description))
    page_layout.addWidget(_in_preparation_pill(theme, lang))

    body_row = hbox(spacing=18, margins=(0, 0, 0, 0))
    body_row.setAlignment(Qt.AlignmentFlag.AlignTop)

    form_holder = QFrame()
    form_holder.setStyleSheet("background: transparent;")
    form_holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    form_layout = vbox(spacing=14, margins=(0, 0, 0, 0))
    form_holder.setLayout(form_layout)

    for f in fields:
        form_layout.addWidget(
            _text_field_block(
                theme,
                label=f["label"],
                hint=f.get("hint", ""),
                multiline=bool(f.get("multiline", False)),
            )
        )

    actions = QFrame()
    actions.setStyleSheet("background: transparent;")
    actions_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    actions.setLayout(actions_layout)
    actions_layout.addWidget(PrimaryButton(primary_label, theme=theme, icon=Icons.AUTO_AWESOME))
    actions_layout.addWidget(GhostButton(save_label, theme=theme, icon=Icons.BOOKMARK_BORDER))
    actions_layout.addStretch(1)
    form_layout.addWidget(actions)

    body_row.addWidget(form_holder, 1)

    if examples:
        body_row.addWidget(_examples_card(theme, lang, examples))

    body_holder = QFrame()
    body_holder.setStyleSheet("background: transparent;")
    body_holder.setLayout(body_row)
    page_layout.addWidget(body_holder)
    page_layout.addStretch(1)

    return _scrollable(page, theme)


def _grid_card(theme: Theme, card: dict) -> QFrame:
    cell = ClickFrame()
    cell.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        ClickFrame:hover {{
            background-color: {theme.surface_2};
        }}
        """
    )
    cell.setFixedSize(220, 160)
    layout = vbox(spacing=10, margins=(14, 14, 14, 14))
    cell.setLayout(layout)

    badge = QFrame()
    badge.setFixedSize(36, 36)
    badge.setStyleSheet(
        f"background-color: {card.get('color') or theme.primary}; border-radius: 10px;"
    )
    bl = hbox(spacing=0, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setLayout(bl)
    bl.addWidget(IconLabel(card["icon"], color="#FFFFFF", size=18),
                 alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(badge)

    layout.addWidget(BodyLabel(card["title"], theme=theme, size=12))
    layout.addWidget(MutedLabel(card["description"], theme=theme, size=11))

    action_row = hbox(spacing=2, margins=(0, 0, 0, 0))
    action_label = card.get("action_label", "")
    if action_label:
        a = BodyLabel(action_label, theme=theme, size=11)
        a.setStyleSheet(f"color: {theme.primary}; background: transparent;")
        action_row.addWidget(a)
    action_row.addWidget(IconLabel(Icons.CHEVRON_RIGHT, color=theme.primary, size=14))
    action_row_holder = QFrame()
    action_row_holder.setStyleSheet("background: transparent;")
    action_row_holder.setLayout(action_row)
    layout.addWidget(action_row_holder)

    return cell


def mock_card_grid_panel(
    theme: Theme,
    lang: str,
    *,
    icon: str,
    title: str,
    description: str,
    cards: Sequence[dict],
) -> QWidget:
    page = QFrame()
    page.setStyleSheet(f"background-color: {theme.bg};")
    page_layout = vbox(spacing=14, margins=(24, 20, 24, 20))
    page.setLayout(page_layout)

    page_layout.addWidget(_hero_card(theme, icon=icon, title=title, description=description))
    page_layout.addWidget(_in_preparation_pill(theme, lang))

    grid_holder = QFrame()
    grid_holder.setStyleSheet("background: transparent;")
    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(14)
    grid.setVerticalSpacing(14)
    grid_holder.setLayout(grid)

    cols = 3
    for i, c in enumerate(cards):
        grid.addWidget(_grid_card(theme, c), i // cols, i % cols)
    page_layout.addWidget(grid_holder)
    page_layout.addStretch(1)

    return _scrollable(page, theme)
