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
    QGridLayout,
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
    def __init__(self, theme: Theme, score: int, label: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self._score = max(0, min(100, int(score)))
        self._label = label
        self._color = _OK_COLOR if self._score >= 80 else (_RISK_COLOR if self._score < 60 else theme.primary)
        self.setFixedSize(180, 180)
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
        rect = QRectF(20, 20, 140, 140)
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
    layout = vbox(spacing=6, margins=(14, 10, 14, 10))
    holder.setLayout(layout)

    head = QFrame()
    head.setStyleSheet("background: transparent;")
    hl = hbox(spacing=8, margins=(0, 0, 0, 0))
    hl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    head.setLayout(hl)
    hl.addWidget(BodyLabel(name, theme=theme, size=12, weight=QFont.Weight.DemiBold), 1)
    hl.addWidget(MutedLabel(f"{score} / 100", theme=theme, size=11, weight=QFont.Weight.Medium))
    layout.addWidget(head)

    bar_holder = QFrame()
    bar_holder.setFixedHeight(6)
    bar_holder.setStyleSheet(f"background-color: {rgba(color, 0.18)}; border-radius: 3px;")
    bar_inner = QFrame(bar_holder)
    bar_inner.setStyleSheet(f"background-color: {color}; border-radius: 3px;")
    bar_inner.setFixedHeight(6)
    bar_holder.resizeEvent = lambda evt, b=bar_holder, fill=bar_inner, sc=score: fill.setGeometry(0, 0, int(b.width() * sc / 100.0), 6)  # type: ignore[assignment]
    layout.addWidget(bar_holder)

    if evidence:
        holder.setToolTip("\n".join(f"• {e}" for e in evidence))
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
        layout.addWidget(SubtleLabel("—", theme=theme, size=12))
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
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        gl = QGridLayout(row)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setHorizontalSpacing(6)
        gl.setVerticalSpacing(6)
        if not items:
            gl.addWidget(SubtleLabel("—", theme=theme, size=12), 0, 0)
            return row
        col = 0
        r = 0
        for it in items:
            chip = Pill(text=it, bg=rgba(color, 0.14), fg=color)
            gl.addWidget(chip, r, col)
            col += 1
            if col >= 4:
                col = 0
                r += 1
        return row

    layout.addWidget(MutedLabel(present_label, theme=theme, size=11, weight=QFont.Weight.Medium))
    layout.addWidget(_chip_row(present, _OK_COLOR))
    layout.addSpacing(4)
    layout.addWidget(MutedLabel(missing_label, theme=theme, size=11, weight=QFont.Weight.Medium))
    layout.addWidget(_chip_row(missing, _RISK_COLOR))
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
    dialog = BaseDialog(parent=parent, theme=theme, title=txt["docs_lang_dialog_title"], width=420, height=240)
    dialog.body_layout.addWidget(BodyLabel(txt["docs_lang_dialog_desc"], theme=theme, size=12))

    group = QButtonGroup(dialog)
    cs_btn = QRadioButton(txt["docs_lang_option_cs"])
    en_btn = QRadioButton(txt["docs_lang_option_en"])
    cs_btn.setStyleSheet(f"color: {theme.text}; font-size: 13px;")
    en_btn.setStyleSheet(f"color: {theme.text}; font-size: 13px;")
    if current == "cs":
        cs_btn.setChecked(True)
    else:
        en_btn.setChecked(True)
    group.addButton(cs_btn)
    group.addButton(en_btn)
    dialog.body_layout.addWidget(cs_btn)
    dialog.body_layout.addWidget(en_btn)

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
    top_layout = hbox(spacing=18, margins=(0, 0, 0, 0))
    top_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
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
    top_layout.addWidget(cat_holder, 1)
    body_layout.addWidget(top_row)

    if verdict:
        body_layout.addWidget(SubtleLabel(f"{txt['match_verdict_label']}: {verdict}", theme=theme, size=12, italic=True))

    cols_row = QFrame()
    cols_row.setStyleSheet("background: transparent;")
    cols_layout = hbox(spacing=12, margins=(0, 0, 0, 0))
    cols_row.setLayout(cols_layout)
    cols_layout.addWidget(_bullet_column(theme, title=txt["match_matches_title"], items=[str(m) for m in matches], accent=_OK_COLOR, bullet_marker="✓"), 1)
    cols_layout.addWidget(_bullet_column(theme, title=txt["match_gaps_title"], items=[str(g) for g in gaps], accent=_RISK_COLOR, bullet_marker="!"), 1)
    cols_layout.addWidget(_ats_column(
        theme,
        title=txt["match_ats_title"],
        present=[str(x) for x in ats_present],
        missing=[str(x) for x in ats_missing],
        present_label=txt["match_ats_present_label"],
        missing_label=txt["match_ats_missing_label"],
    ), 1)
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
        ev_layout.addWidget(SubtleLabel("—", theme=theme, size=12))
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
    body_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(body_holder)
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
