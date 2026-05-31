"""Match tab - score, categories, matches, gaps, ATS keywords (PySide6 port)."""

from __future__ import annotations

import math
import threading
from typing import Callable, List, Optional

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QWidget,
)

from src.qt.dialog import BaseDialog
from src.qt.icons import Icons
from src.qt.runtime import dispatch as runtime_dispatch
from src.qt.runtime import get_main_window
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    GhostButton,
    IconLabel,
    MutedLabel,
    Pill,
    PrimaryButton,
    SubtleLabel,
    TitleLabel,
    custom_label,
    hbox,
    vbox,
)
from src.services import logger as logger_service
from src.sections.ai_career import pipeline
from src.sections.ai_career.refs import REFS
from src.sections.ai_career.state import STATE, TAB_DOCUMENTS, TAB_SETUP
from src.sections.ai_career.strings import s
from src.theme import Theme


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception as exc:
        logger_service.log_exception(
            "ai_career.tab_match", "request_full_refresh_import", exc,
        )
        return
    request_section_refresh()


_OK_COLOR = "#22C55E"
_RISK_COLOR = "#F97316"
_INFO_COLOR = "#3B82F6"


class _ScoreRing(QFrame):
    """Round score badge with a 140x140 progress ring centred in a card.

    The card itself uses a fixed width but expands vertically so the
    score ring stays visually balanced next to the multi-row category
    bars. Without this, the categories block on the right would grow to
    ~270 px tall while the score ring card stayed locked at 180 px,
    leaving an awkward dark band underneath the badge.
    """

    _RING_SIZE = 140
    _CARD_WIDTH = 180
    _CARD_MIN_HEIGHT = 180

    def __init__(self, theme: Theme, score: int, label: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self._score = max(0, min(100, int(score)))
        self._label = label
        self._color = _OK_COLOR if self._score >= 80 else (_RISK_COLOR if self._score < 60 else theme.primary)
        self.setFixedWidth(self._CARD_WIDTH)
        self.setMinimumHeight(self._CARD_MIN_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.MinimumExpanding)
        self.setStyleSheet(
            f"""
            _ScoreRing {{
                background-color: {theme.surface};
                border: 1px solid {theme.border};
                border-radius: 14px;
            }}
            """
        )

    def paintEvent(self, event):  # noqa: ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Centre the ring inside the (potentially taller) card so the
        # ring keeps looking balanced when the row height grows with the
        # categories block on the right.
        ring = float(self._RING_SIZE)
        cx = (self.width() - ring) / 2.0
        cy = (self.height() - ring) / 2.0
        rect = QRectF(cx, cy, ring, ring)
        bg_color = QColor(self._color)
        bg_color.setAlpha(int(255 * 0.18))
        pen_bg = QPen(bg_color)
        pen_bg.setWidth(10)
        pen_bg.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen_bg)
        painter.drawArc(rect, 0, 360 * 16)

        pen_fg = QPen(QColor(self._color))
        pen_fg.setWidth(10)
        pen_fg.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_fg)
        span = int(360 * 16 * self._score / 100.0)
        painter.drawArc(rect, 90 * 16, -span)

        painter.setPen(QColor(self._theme.text_muted))
        font_label = QFont()
        font_label.setPixelSize(10)
        font_label.setWeight(QFont.Weight.Bold)
        font_label.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.4)
        painter.setFont(font_label)
        painter.drawText(rect.adjusted(0, 30, 0, 0), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self._label)

        painter.setPen(QColor(self._theme.text))
        font_score = QFont()
        font_score.setPixelSize(44)
        font_score.setWeight(QFont.Weight.Bold)
        painter.setFont(font_score)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(self._score))
        painter.end()


class _ScoreProgressTrack(QFrame):
    """Thin horizontal score bar that always paints an initial fill."""

    def __init__(self, *, score: int, color: str, bg_color: str, height: int = 10) -> None:
        super().__init__()
        self._score = max(0, min(100, int(score)))
        self._height = max(4, int(height))
        self.setFixedHeight(self._height)
        self.setStyleSheet(
            f"background-color: {bg_color}; border-radius: {self._height // 2}px;"
        )
        self._fill = QFrame(self)
        self._fill.setStyleSheet(
            f"background-color: {color}; border-radius: {self._height // 2}px;"
        )
        self._fill.setFixedHeight(self._height)
        self._sync_fill()

    def _sync_fill(self) -> None:
        total = max(0, self.width())
        if total <= 0 or self._score <= 0:
            self._fill.setGeometry(0, 0, 0, self._height)
            return
        fill = int(total * self._score / 100.0)
        fill = max(6, min(total, fill))
        self._fill.setGeometry(0, 0, fill, self._height)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._sync_fill()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._sync_fill()


def _category_bar(theme: Theme, *, name: str, score: int, evidence: List[str]) -> QFrame:
    score = max(0, min(100, int(score)))
    color = _OK_COLOR if score >= 75 else (_RISK_COLOR if score < 55 else theme.primary)
    holder = QFrame()
    holder.setObjectName("MatchCategoryBar")
    holder.setStyleSheet(
        f"""
        QFrame#MatchCategoryBar {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        """
    )
    layout = vbox(spacing=8, margins=(14, 12, 14, 12))
    holder.setLayout(layout)

    head = QFrame()
    head.setStyleSheet("background: transparent;")
    hl = hbox(spacing=8, margins=(0, 0, 0, 0))
    hl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    head.setLayout(hl)
    hl.addWidget(BodyLabel(name, theme=theme, size=12, weight=QFont.Weight.DemiBold), 1)
    score_label = MutedLabel(f"{score} / 100", theme=theme, size=11, weight=QFont.Weight.Medium)
    # Right-align the score label and reserve a fixed minimum width so
    # long category names (Czech translations) can't squeeze it off the
    # row. ``setWordWrap(False)`` keeps "100 / 100" on one line.
    score_label.setWordWrap(False)
    score_label.setMinimumWidth(60)
    score_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    hl.addWidget(score_label)
    layout.addWidget(head)

    layout.addWidget(
        _ScoreProgressTrack(
            score=score,
            color=color,
            bg_color=rgba(color, 0.20),
            height=10,
        )
    )

    if evidence:
        holder.setToolTip("\n".join(f"- {e}" for e in evidence))
    return holder


def _bullet_column(
    theme: Theme,
    *,
    title: str,
    items: List[str],
    accent: str,
    bullet_marker: str = "•",
) -> QFrame:
    holder = QFrame()
    holder.setObjectName("MatchBulletColumn")
    holder.setStyleSheet(
        f"""
        QFrame#MatchBulletColumn {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        """
    )
    layout = vbox(spacing=8, margins=(14, 14, 14, 14))
    holder.setLayout(layout)

    title_label = MutedLabel(title, theme=theme, size=10, weight=QFont.Weight.Bold)
    f = QFont(title_label.font())
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.4)
    title_label.setFont(f)
    layout.addWidget(title_label)

    if not items:
        layout.addWidget(SubtleLabel("-", theme=theme, size=12))
    else:
        for item in items:
            row = QFrame()
            row.setStyleSheet("background: transparent;")
            rl = hbox(spacing=8, margins=(0, 0, 0, 0))
            rl.setAlignment(Qt.AlignmentFlag.AlignTop)
            row.setLayout(rl)
            rl.addWidget(custom_label(bullet_marker, color=accent, size=14, weight=QFont.Weight.Bold))
            rl.addWidget(BodyLabel(item, theme=theme, size=12, selectable=True), 1)
            layout.addWidget(row)
    # Trailing stretch so the bullets stay anchored at the top of the
    # card when the cols row equalises every column to the tallest one.
    layout.addStretch(1)
    return holder


def _ats_column(
    theme: Theme,
    *,
    title: str,
    present: List[str],
    missing: List[str],
    present_label: str,
    missing_label: str,
) -> QFrame:
    holder = QFrame()
    holder.setObjectName("MatchAtsColumn")
    holder.setStyleSheet(
        f"""
        QFrame#MatchAtsColumn {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        """
    )
    layout = vbox(spacing=6, margins=(14, 14, 14, 14))
    holder.setLayout(layout)
    title_label = MutedLabel(title, theme=theme, size=10, weight=QFont.Weight.Bold)
    f = QFont(title_label.font())
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.4)
    title_label.setFont(f)
    layout.addWidget(title_label)

    def _chip_row(items: List[str], color: str) -> QWidget:
        # Flow layout: chips wrap to the next row when the current one
        # runs out of horizontal space. The previous implementation
        # forced a 4-column QGridLayout which clipped chips past the
        # right edge once the column got narrower than ~140 px (the
        # ATS column on a 1080 px window). Each row is a separate
        # ``QFrame`` holding a left-aligned ``hbox`` so the leftover
        # space sits on the right via a trailing stretch.
        holder = QWidget()
        holder.setStyleSheet("background: transparent;")
        holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        outer = vbox(spacing=6, margins=(0, 0, 0, 0))
        holder.setLayout(outer)
        if not items:
            outer.addWidget(SubtleLabel("-", theme=theme, size=12))
            return holder

        max_per_row = 3
        for start in range(0, len(items), max_per_row):
            row = QFrame()
            row.setStyleSheet("background: transparent;")
            rl = hbox(spacing=6, margins=(0, 0, 0, 0))
            rl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            row.setLayout(rl)
            for it in items[start : start + max_per_row]:
                rl.addWidget(Pill(text=it, bg=rgba(color, 0.14), fg=color))
            rl.addStretch(1)
            outer.addWidget(row)
        return holder

    layout.addWidget(MutedLabel(present_label, theme=theme, size=11, weight=QFont.Weight.Medium))
    layout.addWidget(_chip_row(present, _OK_COLOR))
    layout.addSpacing(4)
    layout.addWidget(MutedLabel(missing_label, theme=theme, size=11, weight=QFont.Weight.Medium))
    layout.addWidget(_chip_row(missing, _RISK_COLOR))
    # Match the bullet column - keep chips anchored at the top so an
    # ATS column shorter than the matches/gaps cards does not float
    # vertically when every column equalises to the tallest one.
    layout.addStretch(1)
    return holder


def _empty_state(theme: Theme, txt: dict, on_back: Callable[[], None]) -> QWidget:
    holder = QWidget()
    holder.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=14, margins=(40, 40, 40, 40))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    holder.setLayout(layout)

    badge = QFrame()
    badge.setFixedSize(84, 84)
    badge.setStyleSheet(f"background-color: {theme.primary_tint}; border-radius: 22px;")
    bl = hbox(spacing=0, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setLayout(bl)
    bl.addWidget(IconLabel(Icons.QUERY_STATS, color=theme.primary, size=42),
                 alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignHCenter)
    layout.addWidget(TitleLabel(txt["match_no_results_title"], theme=theme, size=18, weight=QFont.Weight.Bold), alignment=Qt.AlignmentFlag.AlignHCenter)
    desc = MutedLabel(txt["match_no_results_desc"], theme=theme, size=13)
    desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(desc, alignment=Qt.AlignmentFlag.AlignHCenter)

    btn = PrimaryButton(txt["tab_setup"], theme=theme)
    btn.clicked.connect(on_back)
    layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
    return holder


def _open_doc_lang_dialog(parent: QWidget, theme: Theme, txt: dict, *, current: str, on_confirm: Callable[[str], None]) -> None:
    # No explicit ``height=`` so the dialog hugs its content. The previous
    # ``height=260`` set ``setMinimumHeight``, and combined with the body
    # widget's stretch=1 inside :class:`BaseDialog` that produced a
    # 50-80 px empty band between the EN card and the Cancel / Continue
    # buttons.
    dialog = BaseDialog(parent=parent, theme=theme, title=txt["docs_lang_dialog_title"], width=420)
    desc_card = QFrame()
    desc_card.setStyleSheet(
        f"""
        QFrame {{
            background-color: {theme.surface_2};
            border: 1px solid {theme.border};
            border-radius: 10px;
        }}
        """
    )
    dcl = vbox(spacing=0, margins=(12, 10, 12, 10))
    desc_card.setLayout(dcl)
    desc = BodyLabel(txt["docs_lang_dialog_desc"], theme=theme, size=12)
    desc.setWordWrap(True)
    dcl.addWidget(desc)
    dialog.body_layout.addWidget(desc_card)

    # Each language is rendered as a themed clickable card that wraps a
    # real QRadioButton. Clicking anywhere on the card toggles the
    # underlying radio, and the radio's stylesheet still paints the
    # standard dot - so we get a polished look without losing the
    # native keyboard navigation / accessibility of QRadioButton.
    group = QButtonGroup(dialog)
    cs_btn = QRadioButton(txt["docs_lang_option_cs"])
    en_btn = QRadioButton(txt["docs_lang_option_en"])
    radio_qss = (
        f"QRadioButton {{ color: {theme.text}; font-size: 14px; spacing: 10px; background: transparent; }}"
        f"QRadioButton::indicator {{ width: 16px; height: 16px; border: 1px solid {theme.border}; border-radius: 8px; background-color: {theme.surface_2}; }}"
        f"QRadioButton::indicator:checked {{ background-color: {theme.primary}; border: 1px solid {theme.primary}; }}"
    )
    cs_btn.setStyleSheet(radio_qss)
    en_btn.setStyleSheet(radio_qss)
    if current == "cs":
        cs_btn.setChecked(True)
    else:
        en_btn.setChecked(True)
    group.addButton(cs_btn)
    group.addButton(en_btn)

    def _refresh_cards() -> None:
        for card, radio in ((cs_card, cs_btn), (en_card, en_btn)):
            active = radio.isChecked()
            card.setStyleSheet(
                f"""
                QFrame#DocLangCard {{
                    background-color: {theme.surface_2 if not active else rgba(theme.primary, 0.12)};
                    border: 1px solid {theme.primary if active else theme.border};
                    border-radius: 10px;
                }}
                QFrame#DocLangCard:hover {{
                    border: 1px solid {theme.primary};
                }}
                """
            )

    def _make_card(radio: QRadioButton) -> QFrame:
        card = QFrame()
        card.setObjectName("DocLangCard")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        cl = hbox(spacing=0, margins=(14, 10, 14, 10))
        card.setLayout(cl)
        cl.addWidget(radio)
        cl.addStretch(1)

        # Forward click events on the card to the radio button so users
        # can tap anywhere inside the card to select that language.
        def _mouse_release(event, r=radio):
            if event.button() == Qt.MouseButton.LeftButton:
                r.setChecked(True)

        card.mouseReleaseEvent = _mouse_release  # type: ignore[assignment]
        return card

    cs_card = _make_card(cs_btn)
    en_card = _make_card(en_btn)
    cs_btn.toggled.connect(lambda _checked: _refresh_cards())
    en_btn.toggled.connect(lambda _checked: _refresh_cards())
    _refresh_cards()
    dialog.body_layout.addWidget(cs_card)
    dialog.body_layout.addWidget(en_card)

    cancel_btn = QPushButton(txt["docs_lang_dialog_cancel"])
    cancel_btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {theme.text}; border: none; padding: 8px 12px; }}")
    confirm_btn = QPushButton(txt["docs_lang_dialog_confirm"])
    confirm_btn.setStyleSheet(
        f"""
        QPushButton {{
            background-color: {theme.primary};
            color: #FFFFFF;
            border: none;
            border-radius: 8px;
            padding: 10px 18px;
            font-weight: 600;
        }}
        QPushButton:hover {{ background-color: {theme.primary_hover}; }}
        """
    )

    def _do_confirm() -> None:
        chosen = "cs" if cs_btn.isChecked() else "en"
        STATE.document_output_lang = chosen
        dialog.accept()
        on_confirm(chosen)

    def _do_cancel() -> None:
        dialog.reject()

    dialog.add_action(cancel_btn, on_click=_do_cancel)
    dialog.add_action(confirm_btn, on_click=_do_confirm)
    dialog.exec()


def build_match_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Callable[[], None],
    on_navigate_tab: Callable[[int], None],
) -> QWidget:
    txt = s(lang)
    match = STATE.match

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    if not match:
        layout.addWidget(_empty_state(theme, txt, on_back=lambda: on_navigate_tab(TAB_SETUP)), 1)
        return container

    body_holder = QWidget()
    body_holder.setStyleSheet(f"background-color: {theme.bg};")
    # ``Preferred`` horizontally + ``Minimum`` vertically lets the
    # widget grow with the scroll viewport horizontally (so the
    # category rows can claim the full width) but stops Qt from
    # padding the widget vertically beyond the content's natural
    # height. The earlier ``addStretch(1)`` + default policy combo
    # made the QScrollArea inflate the holder to the viewport size,
    # which the user saw as a giant empty band below the evidence
    # card / columns.
    body_holder.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
    body_layout = vbox(spacing=14, margins=(24, 18, 24, 18))
    body_holder.setLayout(body_layout)

    overall = int(match.get("overall_score") or 0)
    verdict = match.get("verdict") or ""
    categories = match.get("categories") or []
    matches = match.get("matches") or []
    gaps = match.get("gaps") or []
    ats_present = match.get("ats_keywords_present") or []
    ats_missing = match.get("ats_keywords_missing") or []
    evidence = match.get("evidence_preview") or []

    top_row = QFrame()
    top_row.setStyleSheet("background: transparent;")
    # Drop the explicit ``AlignTop`` so the hbox stretches its children
    # to a uniform row height. Combined with the ``MinimumExpanding``
    # vertical policy on :class:`_ScoreRing`, the score badge now grows
    # to match the categories block and we no longer get the awkward
    # 80-90 px dark band under the score card the user reported.
    top_layout = hbox(spacing=18, margins=(0, 0, 0, 0))
    top_row.setLayout(top_layout)

    top_layout.addWidget(_ScoreRing(theme, overall, txt["match_overall_label"]))

    cat_holder = QFrame()
    cat_holder.setStyleSheet("background: transparent;")
    cat_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    cat_holder.setLayout(cat_layout)
    if not categories:
        empty_cat = QFrame()
        empty_cat.setObjectName("MatchEmptyCategories")
        empty_cat.setStyleSheet(
            f"""
            QFrame#MatchEmptyCategories {{
                background-color: {theme.surface};
                border: 1px solid {theme.border};
                border-radius: 12px;
            }}
            """
        )
        ec_layout = vbox(spacing=0, margins=(14, 14, 14, 14))
        empty_cat.setLayout(ec_layout)
        ec_layout.addWidget(MutedLabel(txt["match_per_category_hint"], theme=theme, size=12))
        cat_layout.addWidget(empty_cat)
    else:
        for c in categories:
            cat_layout.addWidget(_category_bar(
                theme,
                name=str(c.get("name") or ""),
                score=int(c.get("score") or 0),
                evidence=[str(x) for x in (c.get("evidence") or [])],
            ))
    # Trailing stretch keeps the category cards anchored to the top of
    # the row so they don't get vertically padded apart when the row
    # height stretches.
    cat_layout.addStretch(1)
    top_layout.addWidget(cat_holder, 1)
    body_layout.addWidget(top_row)

    if verdict:
        body_layout.addWidget(SubtleLabel(f"{txt['match_verdict_label']}: {verdict}", theme=theme, size=12, italic=True))

    cols_row = QFrame()
    cols_row.setStyleSheet("background: transparent;")
    # No vertical alignment override: the hbox stretches every column
    # to the row's natural height so the three card backgrounds end at
    # the same y-coordinate, instead of leaving a long dark band under
    # the shorter cards.
    cols_layout = hbox(spacing=12, margins=(0, 0, 0, 0))
    cols_row.setLayout(cols_layout)

    matches_col = _bullet_column(
        theme,
        title=txt["match_matches_title"],
        items=[str(m) for m in matches],
        accent=_OK_COLOR,
        bullet_marker="✓",
    )
    gaps_col = _bullet_column(
        theme,
        title=txt["match_gaps_title"],
        items=[str(g) for g in gaps],
        accent=_RISK_COLOR,
        bullet_marker="!",
    )
    ats_col = _ats_column(
        theme,
        title=txt["match_ats_title"],
        present=[str(x) for x in ats_present],
        missing=[str(x) for x in ats_missing],
        present_label=txt["match_ats_present_label"],
        missing_label=txt["match_ats_missing_label"],
    )
    # The bullet columns wrap their text so they shrink gracefully, but
    # the ATS keyword column is full of fixed-size :class:`Pill` chips
    # that refuse to shrink below their text width. With every column
    # at ``Expanding`` and stretch=1 the layout was giving ATS the bulk
    # of the available width (because its minimum was much larger than
    # the wrappable bullet columns) and the Czech "matches" / "gaps"
    # columns ended up squeezed into 2-3-word lines. We now cap ATS at
    # roughly a third of the row and let the bullet columns share the
    # remainder evenly.
    matches_col.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    gaps_col.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    ats_col.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
    ats_col.setMaximumWidth(380)
    cols_layout.addWidget(matches_col, 1)
    cols_layout.addWidget(gaps_col, 1)
    cols_layout.addWidget(ats_col, 0)
    body_layout.addWidget(cols_row)

    evidence_card = QFrame()
    evidence_card.setObjectName("MatchEvidenceCard")
    evidence_card.setStyleSheet(
        f"""
        QFrame#MatchEvidenceCard {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        """
    )
    ev_layout = vbox(spacing=8, margins=(14, 14, 14, 14))
    evidence_card.setLayout(ev_layout)
    ev_title = MutedLabel(txt["match_evidence_title"], theme=theme, size=10, weight=QFont.Weight.Bold)
    f = QFont(ev_title.font())
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.4)
    ev_title.setFont(f)
    ev_layout.addWidget(ev_title)
    if not evidence:
        ev_layout.addWidget(SubtleLabel("-", theme=theme, size=12))
    else:
        for e in evidence:
            row = QFrame()
            row.setStyleSheet("background: transparent;")
            rl = hbox(spacing=10, margins=(0, 0, 0, 0))
            rl.setAlignment(Qt.AlignmentFlag.AlignTop)
            row.setLayout(rl)
            dot = QFrame()
            dot.setFixedSize(6, 6)
            dot.setStyleSheet(f"background-color: {theme.primary}; border-radius: 3px;")
            row_top = QFrame()
            row_top.setStyleSheet("background: transparent;")
            rtl = vbox(spacing=0, margins=(0, 8, 0, 0))
            row_top.setLayout(rtl)
            rtl.addWidget(dot)
            rl.addWidget(row_top)
            rl.addWidget(BodyLabel(str(e), theme=theme, size=12, selectable=True), 1)
            ev_layout.addWidget(row)
    body_layout.addWidget(evidence_card)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(body_holder)
    scroll.setAlignment(Qt.AlignmentFlag.AlignTop)
    layout.addWidget(scroll, 1)

    footer = QFrame()
    footer.setObjectName("MatchFooter")
    footer.setStyleSheet(
        f"""
        QFrame#MatchFooter {{
            background-color: {theme.bg};
            border-top: 1px solid {theme.border};
        }}
        """
    )
    footer_layout = vbox(spacing=6, margins=(24, 12, 24, 12))
    footer.setLayout(footer_layout)
    status_label = SubtleLabel("", theme=theme, size=11)
    footer_layout.addWidget(status_label)
    progress_bar = QProgressBar()
    progress_bar.setRange(0, 0)
    progress_bar.setTextVisible(False)
    progress_bar.setVisible(False)
    progress_bar.setFixedHeight(6)
    progress_bar.setStyleSheet(
        f"""
        QProgressBar {{
            border: 1px solid {theme.border};
            background-color: {theme.surface};
            border-radius: 3px;
        }}
        QProgressBar::chunk {{
            background-color: {theme.primary};
            border-radius: 3px;
        }}
        """
    )
    footer_layout.addWidget(progress_bar)
    btn_row = QFrame()
    btn_row.setStyleSheet("background: transparent;")
    br_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    br_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    btn_row.setLayout(br_layout)
    br_layout.addStretch(1)
    open_docs_btn = PrimaryButton(txt["match_open_documents_btn"], theme=theme, icon=Icons.AUTO_AWESOME)
    br_layout.addWidget(open_docs_btn)
    footer_layout.addWidget(btn_row)
    layout.addWidget(footer)

    def _resolved_lang() -> str:
        sel = (STATE.document_output_lang or "").strip().lower()
        if sel in ("en", "cs"):
            return sel
        return "en" if lang == "en" else "cs"

    def _set_status(msg: str, *, error: bool = False) -> None:
        status_label.setText(msg)
        status_label.setStyleSheet(
            f"color: {'#EF4444' if error else theme.text_muted}; background: transparent;"
        )

    def _is_running() -> bool:
        return STATE.activity == "generating"

    def _refresh_button() -> None:
        running = _is_running()
        open_docs_btn.setEnabled(not running)
        open_docs_btn.setText(txt["match_generating_documents"] if running else txt["match_open_documents_btn"])
        progress_bar.setVisible(running)

    def _start_with_lang(doc_lang: str) -> None:
        STATE.activity = "generating"
        STATE.last_error = ""
        REFS.request_context_refresh()
        _set_status(txt["match_generating_documents"])
        _refresh_button()
        REFS.dispatch(_request_full_refresh)

        def _worker() -> None:
            try:
                result = pipeline.generate_all_documents(output_lang=doc_lang)
                if not result.ok:
                    runtime_dispatch(lambda: _set_status(result.error, error=True))
                    return
                STATE.active_tab = TAB_DOCUMENTS
            finally:
                STATE.activity = "ready"
                REFS.request_context_refresh()
                REFS.dispatch(_request_full_refresh)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_open_docs() -> None:
        if _is_running():
            return
        _open_doc_lang_dialog(get_main_window(), theme, txt, current=_resolved_lang(), on_confirm=_start_with_lang)

    open_docs_btn.clicked.connect(_on_open_docs)
    _refresh_button()
    return container
