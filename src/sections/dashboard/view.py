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
from functools import lru_cache

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.components.header import header
from src.qt.icons import Icons
from src.qt.theme import rgba
from src.qt.widgets import (
    ClampLabel,
    ClickFrame,
    IconLabel,
    MutedLabel,
    Pill,
    PrimaryButton,
    TitleLabel,
    hbox,
    vbox,
    wrap_label_slot,
)
from src.sections._base import Section
from src.sections.dashboard.strings import s
from src.services import logger as logger_service
from src.theme import Theme


@lru_cache(maxsize=64)
def _section_subtitle_for_key(section_key: str, lang: str) -> str:
    """Pull the short subtitle from the target section's strings module.

    Each section package ships a ``strings.py`` with at least a
    ``subtitle`` key (the same string the section header renders).
    Importing it lazily keeps the dashboard module decoupled - we never
    have to update a registry when a new section appears, the
    auto-discovered ``Section`` instance is enough.
    """
    try:
        module = importlib.import_module(f"src.sections.{section_key}.strings")
    except Exception as exc:
        logger_service.log_exception(
            "dashboard.view", "section_subtitle_import_failed", exc,
            section=section_key,
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


def _section_subtitle(section: Section, lang: str) -> str:
    return _section_subtitle_for_key(section.key, lang)


def _modules_pill_text(count: int, lang: str, txt: dict) -> str:
    """Short count chip copy, e.g. ``5 modulů`` / ``5 modules``.

    Czech has three plural forms (1 / 2-4 / 5+); English has two. We
    pick the right key per language and fall back to ``modules_pill_other``
    so a missing key never raises.
    """
    if lang == "cs":
        if count == 1:
            key = "modules_pill_one"
        elif 2 <= count <= 4:
            key = "modules_pill_few"
        else:
            key = "modules_pill_other"
    else:
        key = "modules_pill_one" if count == 1 else "modules_pill_other"
    template = txt.get(key) or txt.get("modules_pill_other") or "{n}"
    return template.format(n=count)


def _count_pill(theme: Theme, *, count: int, lang: str, txt: dict) -> QWidget:
    return Pill(
        text=_modules_pill_text(count, lang, txt),
        bg=rgba(theme.primary, 0.14),
        fg=theme.primary,
        icon=Icons.AUTO_AWESOME,
        icon_size=14,
        radius=12,
        padding=(6, 12, 6, 12),
    )


def _module_card(
    theme: Theme,
    section: Section,
    *,
    lang: str,
    open_label: str,
    on_open,
) -> ClickFrame:
    # Each tile carries its section's own accent (Career = violet, Jobs =
    # indigo, LinkedIn = blue, Finance = green, Bug Report = orange). The
    # whole card is clickable - clicking anywhere navigates into the
    # section, not just the button.
    accent = section.accent or theme.primary
    accent_theme = theme.with_accent(accent)

    card = ClickFrame()
    card.setObjectName("DashboardModuleCard")
    card.setStyleSheet(
        f"""
        ClickFrame#DashboardModuleCard {{
            background-color: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 {rgba(accent, 0.16)},
                stop:0.5 {theme.surface},
                stop:1 {theme.surface}
            );
            border: 1px solid {theme.border};
            border-radius: 14px;
        }}
        ClickFrame#DashboardModuleCard:hover {{
            border: 1px solid {accent};
        }}
        """
    )
    card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    card.setMinimumHeight(84)
    card.clicked.connect(lambda: on_open(section))

    # Full-width "list" row: icon | title + blurb | Open button. A single
    # column of full-width rows always fills the centre column, so there is
    # never an empty trailing grid cell or an empty band on the right -
    # regardless of how wide the window gets.
    layout = hbox(spacing=16, margins=(16, 14, 18, 14))
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    card.setLayout(layout)

    icon_box = QFrame()
    icon_box.setFixedSize(48, 48)
    icon_box.setStyleSheet(
        f"background-color: {rgba(accent, 0.16)}; border-radius: 13px;"
    )
    icon_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setLayout(icon_layout)
    icon_layout.addWidget(
        IconLabel(section.icon, color=accent, size=24),
        alignment=Qt.AlignmentFlag.AlignCenter,
    )
    layout.addWidget(icon_box)

    # Single-line title + blurb, each clamped to one line. ClampLabel wraps
    # internally, so its minimum width is just the widest word - that lets
    # the text column shrink and elide on narrow windows instead of forcing
    # the whole row wider than the centre column (which pushed the Open
    # button and the count pill off the right edge). The row never wraps,
    # so AlignVCenter is safe and the card height stays uniform.
    text_col = QFrame()
    text_col.setStyleSheet("background: transparent;")
    wrap_label_slot(text_col)
    text_layout = vbox(spacing=3, margins=(0, 0, 0, 0))
    text_col.setLayout(text_layout)
    text_layout.addWidget(
        ClampLabel(
            section.label(lang),
            color=theme.text,
            size=15,
            weight=QFont.Weight.Bold,
            lines=1,
        )
    )
    subtitle = _section_subtitle(section, lang)
    if subtitle:
        text_layout.addWidget(
            ClampLabel(subtitle, color=theme.text_muted, size=12, lines=1)
        )
    layout.addWidget(text_col, 1)

    # ``accent_theme`` so the "Open" button matches the tile accent.
    open_btn = PrimaryButton(open_label, theme=accent_theme, icon=Icons.ARROW_FORWARD)
    open_btn.clicked.connect(lambda: on_open(section))
    layout.addWidget(open_btn, 0, Qt.AlignmentFlag.AlignVCenter)

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

    # Section heading with a compact count chip pinned to the right.
    # This replaces the standalone "5 modules" stat card that used to
    # float above the grid and waste a whole row of vertical space.
    title_row = QFrame()
    title_row.setStyleSheet("background: transparent;")
    title_row_layout = hbox(spacing=12, margins=(0, 4, 0, 0))
    title_row_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    title_row.setLayout(title_row_layout)

    title_col = QFrame()
    title_col.setStyleSheet("background: transparent;")
    wrap_label_slot(title_col)
    title_col_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    title_col.setLayout(title_col_layout)
    title_col_layout.addWidget(
        TitleLabel(
            txt["modules_grid_title"], theme=theme, size=15, weight=QFont.Weight.Bold,
        )
    )
    title_col_layout.addWidget(
        MutedLabel(txt["modules_grid_desc"], theme=theme, size=12)
    )
    title_row_layout.addWidget(title_col, 1)
    title_row_layout.addWidget(
        _count_pill(theme, count=count, lang=lang, txt=txt),
        0,
        Qt.AlignmentFlag.AlignTop,
    )
    body_layout.addWidget(title_row)

    if not sections:
        body_layout.addWidget(
            _empty_state(theme, title=txt["empty_title"], desc=txt["empty_desc"])
        )
    else:
        list_holder = QFrame()
        list_holder.setStyleSheet("background: transparent;")
        list_layout = vbox(spacing=12, margins=(0, 0, 0, 0))
        list_holder.setLayout(list_layout)

        try:
            # One full-width row per module. A single column fills the centre
            # column at any width, so there is no empty trailing cell / empty
            # band on the right that the old 2-column grid left behind.
            for section in sections:
                list_layout.addWidget(
                    _module_card(
                        theme,
                        section,
                        lang=lang,
                        open_label=txt["open_btn"],
                        on_open=_on_open_section,
                    )
                )
        except Exception as exc:
            logger_service.log_exception(
                "dashboard.view", "build_list_failed", exc,
            )
            raise

        body_layout.addWidget(list_holder)

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
