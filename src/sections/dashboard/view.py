"""Dashboard - landing page that lets the user pick an AI module.

The dashboard is the first section in ``PRIMARY_SECTIONS`` (order=10), so
it is what the user sees on every cold launch. It re-uses the already
discovered :data:`src.sections.PRIMARY_SECTIONS` list and renders one
card per visible section. Clicking a card jumps the user straight into
that section via ``app.set_section(<key>)``.

We deliberately **do not** add any AI/network calls here - the dashboard
is just navigation. That keeps the cold-start fast and means it works
even when the user has no API keys configured yet.
"""

from __future__ import annotations

import importlib
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.components.header import header
from src.qt.icons import Icons
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    IconLabel,
    MutedLabel,
    PrimaryButton,
    TitleLabel,
    custom_label,
    hbox,
    vbox,
    wrap_label_slot,
)
from src.sections._base import Section
from src.sections.dashboard.strings import s
from src.services import logger as logger_service
from src.theme import Theme


def _section_subtitle(section: Section, lang: str) -> str:
    """Pull the short subtitle from the target section's strings module.

    Each section package ships a ``strings.py`` with at least a
    ``subtitle`` key (the same string the section header renders).
    Importing it lazily keeps the dashboard module decoupled - we never
    have to update a registry when a new section appears, the
    auto-discovered ``Section`` instance is enough.
    """
    try:
        module = importlib.import_module(f"src.sections.{section.key}.strings")
    except Exception as exc:
        logger_service.log_exception(
            "dashboard.view", "section_subtitle_import_failed", exc,
            section=section.key,
        )
        return ""
    strings = getattr(module, "STRINGS", None)
    if not isinstance(strings, dict):
        return ""
    bundle = strings.get(lang) or strings.get("en") or {}
    if not isinstance(bundle, dict):
        return ""
    value = bundle.get("subtitle")
    return str(value) if value else ""


def _stat_card(theme: Theme, *, count: int, label: str) -> QWidget:
    card = QFrame()
    card.setObjectName("DashboardStatCard")
    card.setStyleSheet(
        f"""
        QFrame#DashboardStatCard {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 14px;
        }}
        """
    )
    card.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
    layout = hbox(spacing=14, margins=(18, 16, 22, 16))
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    card.setLayout(layout)

    icon_box = QFrame()
    icon_box.setFixedSize(44, 44)
    icon_box.setStyleSheet(
        f"background-color: {rgba(theme.primary, 0.14)}; border-radius: 12px;"
    )
    icon_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setLayout(icon_layout)
    icon_layout.addWidget(
        IconLabel(Icons.AUTO_AWESOME, color=theme.primary, size=22),
        alignment=Qt.AlignmentFlag.AlignCenter,
    )
    layout.addWidget(icon_box)

    text_holder = QFrame()
    text_holder.setStyleSheet("background: transparent;")
    wrap_label_slot(text_holder)
    text_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    text_holder.setLayout(text_layout)
    text_layout.addWidget(
        custom_label(str(count), color=theme.text, size=22, weight=QFont.Weight.Bold)
    )
    text_layout.addWidget(MutedLabel(label, theme=theme, size=12))
    layout.addWidget(text_holder, 1)
    return card


def _module_card(
    theme: Theme,
    section: Section,
    *,
    lang: str,
    open_label: str,
    on_open,
) -> QFrame:
    card = QFrame()
    card.setObjectName("DashboardModuleCard")
    card.setStyleSheet(
        f"""
        QFrame#DashboardModuleCard {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 16px;
        }}
        QFrame#DashboardModuleCard:hover {{
            border: 1px solid {theme.primary};
        }}
        """
    )
    card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    # Previously ``setMinimumHeight(180)`` clipped the wrapped second
    # line of the subtitle (e.g. the long AI Bug Report description
    # rendered as "...zachy" with no second line visible). We let the
    # layout size itself to the actual wrapped content so longer
    # descriptions can flow downward instead of getting cut off.

    layout = vbox(spacing=10, margins=(18, 18, 18, 18))
    card.setLayout(layout)

    head_row = QFrame()
    head_row.setStyleSheet("background: transparent;")
    head_layout = hbox(spacing=12, margins=(0, 0, 0, 0))
    head_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    head_row.setLayout(head_layout)

    icon_box = QFrame()
    icon_box.setFixedSize(44, 44)
    icon_box.setStyleSheet(
        f"background-color: {rgba(theme.primary, 0.14)}; border-radius: 12px;"
    )
    icon_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setLayout(icon_layout)
    icon_layout.addWidget(
        IconLabel(section.icon, color=theme.primary, size=22),
        alignment=Qt.AlignmentFlag.AlignCenter,
    )
    head_layout.addWidget(icon_box, 0, Qt.AlignmentFlag.AlignTop)

    title_holder = QFrame()
    title_holder.setStyleSheet("background: transparent;")
    wrap_label_slot(title_holder)
    title_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    title_holder.setLayout(title_layout)
    title_layout.addWidget(
        TitleLabel(section.label(lang), theme=theme, size=15, weight=QFont.Weight.Bold)
    )
    subtitle = _section_subtitle(section, lang)
    if subtitle:
        subtitle_label = MutedLabel(subtitle, theme=theme, size=12)
        subtitle_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        title_layout.addWidget(subtitle_label)
    head_layout.addWidget(title_holder, 1, Qt.AlignmentFlag.AlignTop)
    head_layout.setStretch(1, 1)

    layout.addWidget(head_row)
    # Fixed spacer instead of ``addStretch(1)`` so the card grows
    # downward to fit the wrapped subtitle. ``addStretch`` would pad
    # the middle and starve the second line of pixels when the title
    # area is taller than ``setMinimumHeight``.
    layout.addSpacing(12)

    btn_row = QFrame()
    btn_row.setStyleSheet("background: transparent;")
    btn_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    btn_row.setLayout(btn_layout)
    open_btn = PrimaryButton(open_label, theme=theme, icon=Icons.ARROW_FORWARD)
    open_btn.clicked.connect(lambda: on_open(section))
    btn_layout.addWidget(open_btn)
    btn_layout.addStretch(1)
    layout.addWidget(btn_row)

    return card


def _empty_state(theme: Theme, *, title: str, desc: str) -> QWidget:
    holder = QFrame()
    holder.setObjectName("DashboardEmptyState")
    holder.setStyleSheet(
        f"""
        QFrame#DashboardEmptyState {{
            background-color: {theme.surface};
            border: 1px dashed {theme.border};
            border-radius: 14px;
        }}
        """
    )
    layout = vbox(spacing=8, margins=(40, 40, 40, 40))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    holder.setLayout(layout)
    layout.addWidget(
        IconLabel(Icons.HOURGLASS_EMPTY_ROUNDED, color=theme.text_muted, size=32),
        alignment=Qt.AlignmentFlag.AlignHCenter,
    )
    title_label = TitleLabel(title, theme=theme, size=15, weight=QFont.Weight.Bold)
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)
    desc_label = MutedLabel(desc, theme=theme, size=12)
    desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    desc_label.setMaximumWidth(560)
    layout.addWidget(desc_label, alignment=Qt.AlignmentFlag.AlignHCenter)
    return holder


def _on_open_section(section: Section) -> None:
    """Bridge the dashboard card click to the running app's section swap.

    Imported lazily so the dashboard module stays free of cyclic
    dependencies on ``src.app`` (which itself imports the section
    registry to build the sidebar).
    """
    try:
        from src.app import get_active_window
    except Exception as exc:
        logger_service.log_exception(
            "dashboard.view", "open_section_import_failed", exc,
            section=section.key,
        )
        return
    window = get_active_window()
    if window is None:
        logger_service.log_event(
            "WARNING", "dashboard.view", "open_section_no_window",
            section=section.key,
        )
        return
    logger_service.log_event(
        "INFO", "dashboard.view", "open_section_clicked", section=section.key,
    )
    try:
        window.set_section(section.key)
    except Exception as exc:
        logger_service.log_exception(
            "dashboard.view", "open_section_failed", exc, section=section.key,
        )


def _other_visible_sections() -> list[Section]:
    """Return primary sections to show on the dashboard, excluding self."""
    from src.sections import PRIMARY_SECTIONS

    return [s for s in PRIMARY_SECTIONS if s.key != "dashboard"]


def build_view(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    logger_service.log_event(
        "INFO", "dashboard.view", "build_view_start", lang=lang,
    )

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    root = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(root)

    root.addWidget(
        header(
            theme,
            lang,
            icon=Icons.DASHBOARD_OUTLINED,
            title=txt["title"],
            subtitle=txt["subtitle"],
            show_help_button=False,
            show_menu_button=False,
        )
    )

    body = QWidget()
    body.setStyleSheet(f"background-color: {theme.bg};")
    body_layout = vbox(spacing=18, margins=(24, 12, 24, 24))
    body.setLayout(body_layout)

    sections = _other_visible_sections()
    count = len(sections)
    count_label = txt["module_count_one"] if count == 1 else txt["module_count_other"]

    stats_row = QFrame()
    stats_row.setStyleSheet("background: transparent;")
    stats_layout = hbox(spacing=12, margins=(0, 0, 0, 0))
    stats_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    stats_row.setLayout(stats_layout)
    stats_layout.addWidget(_stat_card(theme, count=count, label=count_label))
    stats_layout.addStretch(1)
    body_layout.addWidget(stats_row)

    grid_title_holder = QFrame()
    grid_title_holder.setStyleSheet("background: transparent;")
    gth_layout = vbox(spacing=4, margins=(0, 4, 0, 0))
    grid_title_holder.setLayout(gth_layout)
    gth_layout.addWidget(
        TitleLabel(
            txt["modules_grid_title"], theme=theme, size=15, weight=QFont.Weight.Bold,
        )
    )
    gth_layout.addWidget(MutedLabel(txt["modules_grid_desc"], theme=theme, size=12))
    body_layout.addWidget(grid_title_holder)

    if not sections:
        body_layout.addWidget(
            _empty_state(theme, title=txt["empty_title"], desc=txt["empty_desc"])
        )
    else:
        grid_holder = QFrame()
        grid_holder.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_holder)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        try:
            columns = 3
            for index, section in enumerate(sections):
                card = _module_card(
                    theme,
                    section,
                    lang=lang,
                    open_label=txt["open_btn"],
                    on_open=_on_open_section,
                )
                grid.addWidget(card, index // columns, index % columns)
            for col in range(columns):
                grid.setColumnStretch(col, 1)
        except Exception as exc:
            logger_service.log_exception(
                "dashboard.view", "build_grid_failed", exc,
            )
            raise

        body_layout.addWidget(grid_holder)

    body_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(
        f"QScrollArea {{ background-color: {theme.bg}; border: none; }}"
    )
    scroll.setWidget(body)
    root.addWidget(scroll, 1)

    logger_service.log_event(
        "INFO", "dashboard.view", "build_view_done",
        sections=count, lang=lang,
    )
    return container
