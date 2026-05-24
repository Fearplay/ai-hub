"""Output tab - render every generated LinkedIn section as a card (PySide6 port)."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.qt.icons import Icons
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
from src.sections.ai_linkedin import pipeline
from src.sections.ai_linkedin.refs import REFS
from src.sections.ai_linkedin.state import STATE, TAB_SETUP
from src.sections.ai_linkedin.strings import s
from src.theme import Theme


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.tab_output", "request_full_refresh_import", exc,
        )
        return
    request_section_refresh()


def _open_in_explorer(path: str) -> None:
    if not path or not os.path.isdir(path):
        return
    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.tab_output", "open_in_explorer_failed", exc, path=path,
        )


def _empty_state(theme: Theme, txt: dict, on_navigate_tab: Callable[[int], None]) -> QWidget:
    holder = QWidget()
    holder.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=10, margins=(40, 40, 40, 40))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    holder.setLayout(layout)

    badge = QFrame()
    badge.setFixedSize(84, 84)
    badge.setStyleSheet(f"background-color: {rgba(theme.primary, 0.16)}; border-radius: 22px;")
    bl = hbox(spacing=0, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setLayout(bl)
    bl.addWidget(IconLabel(Icons.WORKSPACE_PREMIUM_OUTLINED, color=theme.primary, size=42),
                 alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignHCenter)
    layout.addWidget(TitleLabel(txt["output_empty_title"], theme=theme, size=18, weight=QFont.Weight.Bold), alignment=Qt.AlignmentFlag.AlignHCenter)
    desc = MutedLabel(txt["output_empty_desc"], theme=theme, size=13)
    desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(desc, alignment=Qt.AlignmentFlag.AlignHCenter)

    spacer = QWidget()
    spacer.setFixedHeight(12)
    layout.addWidget(spacer)

    btn = GhostButton(txt["builder_tab_setup"], theme=theme, icon=Icons.ARROW_BACK)
    btn.clicked.connect(lambda: on_navigate_tab(TAB_SETUP))
    layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
    return holder


def _section_card(
    theme: Theme,
    *,
    icon: str,
    title: str,
    body: QWidget,
    actions: list[QWidget] | None = None,
) -> QFrame:
    card = QFrame()
    card.setObjectName("LinkedInOutputCard")
    card.setStyleSheet(
        f"""
        QFrame#LinkedInOutputCard {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 14px;
        }}
        """
    )
    layout = vbox(spacing=10, margins=(18, 18, 18, 18))
    card.setLayout(layout)

    header = QFrame()
    header.setStyleSheet("background: transparent;")
    h_layout = hbox(spacing=12, margins=(0, 0, 0, 0))
    h_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    header.setLayout(h_layout)

    badge = QFrame()
    badge.setFixedSize(36, 36)
    badge.setStyleSheet(f"background-color: {rgba(theme.primary, 0.14)}; border-radius: 10px;")
    bl = hbox(spacing=0, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setLayout(bl)
    bl.addWidget(IconLabel(icon, color=theme.primary, size=18),
                 alignment=Qt.AlignmentFlag.AlignCenter)
    h_layout.addWidget(badge)
    h_layout.addWidget(TitleLabel(title, theme=theme, size=15, weight=QFont.Weight.Bold), 1)
    if actions:
        for w in actions:
            h_layout.addWidget(w)
    layout.addWidget(header)
    layout.addWidget(body)
    return card


def _copy_button(theme: Theme, label: str, get_text: Callable[[], str]) -> GhostButton:
    btn = GhostButton(label, theme=theme, icon=Icons.CONTENT_COPY)

    def _on_click() -> None:
        cb = QGuiApplication.clipboard()
        if cb is not None:
            cb.setText(get_text() or "")
            QMessageBox.information(get_main_window(), label, label)
    btn.clicked.connect(_on_click)
    return btn


def _evidence_chip(theme: Theme, label: str) -> Pill:
    return Pill(text=label, bg=rgba(theme.primary, 0.14), fg=theme.primary)


def _markdown_text_block(theme: Theme, text: str) -> BodyLabel:
    label = BodyLabel(text, theme=theme, size=13, selectable=True)
    label.setTextFormat(Qt.TextFormat.MarkdownText)
    label.setWordWrap(True)
    return label


def _evidence_label(anchor: str, txt: dict) -> str:
    mapping = {
        "resume": txt["evidence_resume"],
        "linkedin_export": txt["evidence_linkedin_export"],
        "github": txt["evidence_github"],
        "user_confirmed": txt["evidence_user_confirmed"],
        "missing_evidence": txt["evidence_missing_evidence"],
    }
    return mapping.get(anchor, anchor.replace("_", " ").title())


def _score_banner(theme: Theme, txt: dict) -> QFrame:
    score = int((STATE.profile_score or {}).get("score") or 0)
    score_color = "#22C55E" if score >= 80 else ("#F97316" if score < 60 else theme.primary)
    breakdown = (STATE.profile_score or {}).get("breakdown") or []

    body = QFrame()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    row = QFrame()
    row.setStyleSheet("background: transparent;")
    rl = hbox(spacing=14, margins=(0, 0, 0, 0))
    rl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    row.setLayout(rl)

    score_chip = QFrame()
    score_chip.setStyleSheet(f"background-color: {score_color}; border-radius: 12px;")
    sl = hbox(spacing=0, margins=(18, 8, 18, 8))
    score_chip.setLayout(sl)
    sl.addWidget(custom_label(f"{score}", color="#FFFFFF", size=28, weight=QFont.Weight.Bold))
    rl.addWidget(score_chip)

    side = QFrame()
    side.setStyleSheet("background: transparent;")
    sd = vbox(spacing=2, margins=(0, 0, 0, 0))
    side.setLayout(sd)
    sd.addWidget(MutedLabel("/ 100", theme=theme, size=14, weight=QFont.Weight.Medium))
    sd.addWidget(MutedLabel(txt["output_score_card_desc"], theme=theme, size=11))
    rl.addWidget(side, 1)
    body_layout.addWidget(row)

    body_layout.addWidget(BodyLabel(txt["output_score_breakdown_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold))
    for entry in breakdown:
        label = entry.get("label") or entry.get("key") or ""
        contribution = entry.get("contribution", 0)
        weight = entry.get("weight", 0)
        item = QFrame()
        item.setStyleSheet("background: transparent;")
        il = hbox(spacing=0, margins=(0, 0, 0, 0))
        il.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        item.setLayout(il)
        il.addWidget(BodyLabel(label, theme=theme, size=12), 1)
        il.addWidget(MutedLabel(f"{contribution}/{weight}", theme=theme, size=11, weight=QFont.Weight.DemiBold))
        body_layout.addWidget(item)

    return _section_card(
        theme,
        icon=Icons.SCOREBOARD_OUTLINED,
        title=txt["output_score_card_title"],
        body=body,
    )


def _checklist_card(theme: Theme, txt: dict) -> QFrame:
    items = (STATE.completeness or {}).get("items") or []
    body = QFrame()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=6, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)
    if not items:
        body_layout.addWidget(MutedLabel(txt["output_no_evidence_skip"], theme=theme, size=12))
        return _section_card(theme, icon=Icons.CHECKLIST, title=txt["output_checklist_title"], body=body)

    grouped: dict[str, list[dict]] = {"high": [], "medium": [], "low": [], "skip": []}
    for item in items:
        prio = item.get("priority") or "low"
        grouped.setdefault(prio, []).append(item)

    priority_labels = {
        "high": txt["priority_high"],
        "medium": txt["priority_medium"],
        "low": txt["priority_low"],
        "skip": txt["priority_skip"],
    }
    priority_colors = {
        "high": "#EF4444",
        "medium": "#F59E0B",
        "low": "#0EA5E9",
        "skip": theme.text_muted,
    }
    for prio in ("high", "medium", "low", "skip"):
        bucket = grouped.get(prio) or []
        if not bucket:
            continue
        body_layout.addWidget(custom_label(
            priority_labels[prio],
            color=priority_colors[prio],
            size=11,
            weight=QFont.Weight.Bold,
        ))
        for entry in bucket:
            mark_icon = Icons.CHECK_CIRCLE if entry.get("ok") else Icons.RADIO_BUTTON_UNCHECKED
            mark_color = "#22C55E" if entry.get("ok") else theme.text_muted
            row = QFrame()
            row.setStyleSheet("background: transparent;")
            rl = hbox(spacing=10, margins=(0, 0, 0, 0))
            rl.setAlignment(Qt.AlignmentFlag.AlignTop)
            row.setLayout(rl)
            rl.addWidget(IconLabel(mark_icon, color=mark_color, size=16))
            inner = QFrame()
            inner.setStyleSheet("background: transparent;")
            inn_l = vbox(spacing=2, margins=(0, 0, 0, 0))
            inner.setLayout(inn_l)
            inn_l.addWidget(BodyLabel(entry.get("label") or "", theme=theme, size=12, weight=QFont.Weight.DemiBold))
            inn_l.addWidget(MutedLabel(entry.get("reason") or "", theme=theme, size=11))
            rl.addWidget(inner, 1)
            body_layout.addWidget(row)
    return _section_card(theme, icon=Icons.CHECKLIST, title=txt["output_checklist_title"], body=body)


def _generic_text_card(theme: Theme, txt: dict, *, icon: str, title: str, body_text: str) -> QFrame:
    body = QFrame()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)
    if not body_text.strip():
        body_layout.addWidget(MutedLabel(txt["output_no_evidence_skip"], theme=theme, size=12))
    else:
        body_layout.addWidget(_markdown_text_block(theme, body_text))
    return _section_card(
        theme, icon=icon, title=title, body=body,
        actions=[_copy_button(theme, txt["output_copy"], lambda b=body_text: b)] if body_text.strip() else None,
    )


def _build_results_cards(theme: Theme, lang: str, txt: dict) -> list[QFrame]:
    cards: list[QFrame] = [_score_banner(theme, txt), _checklist_card(theme, txt)]
    md_outputs: dict[str, str] = {}
    try:
        md_outputs = pipeline._render_section_markdown(lang)  # type: ignore[attr-defined]
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.tab_output", "render_section_markdown_failed", exc,
        )
    name_icon_title = [
        ("01_headline_variants.md", Icons.TITLE, txt["output_headlines_title"]),
        ("02_about_section.md", Icons.SUBJECT, txt["output_about_title"]),
        ("03_experience_rewrite.md", Icons.WORK_OUTLINE, txt["output_experience_title"]),
        ("04_skills_recommendation.md", Icons.LIGHTBULB_OUTLINE, txt["output_skills_title"]),
        ("05_featured_section.md", Icons.STAR_OUTLINE, txt["output_featured_title"]),
        ("06_projects.md", Icons.FOLDER_OPEN, txt["output_projects_title"]),
        ("07_certifications.md", Icons.WORKSPACE_PREMIUM_OUTLINED, txt["output_certifications_title"]),
        ("08_education.md", Icons.SCHOOL_OUTLINED, txt["output_education_title"]),
        ("09_services.md", Icons.HANDYMAN_OUTLINED, txt["output_services_title"]),
        ("10_recruiter_messages.md", Icons.MAIL_OUTLINE, txt["output_recommendations_title"]),
        ("11_linkedin_posts.md", Icons.POST_ADD, txt["output_posts_title"]),
        ("13_unsupported_claims.md", Icons.WARNING_AMBER_OUTLINED, txt["output_unsupported_title"]),
    ]
    for fname, icon, title in name_icon_title:
        body = md_outputs.get(fname) or ""
        if body.strip():
            cards.append(_generic_text_card(theme, txt, icon=icon, title=title, body_text=body))
    return cards


def build_output_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Callable[[], None],
    on_navigate_tab: Callable[[int], None],
) -> QWidget:
    txt = s(lang)

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    if not STATE.has_results():
        layout.addWidget(_empty_state(theme, txt, on_navigate_tab), 1)
        return container

    body_holder = QWidget()
    body_holder.setStyleSheet(f"background-color: {theme.bg};")
    body_layout = vbox(spacing=14, margins=(24, 18, 24, 18))
    body_holder.setLayout(body_layout)

    for card in _build_results_cards(theme, lang, txt):
        body_layout.addWidget(card)
    body_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(body_holder)
    layout.addWidget(scroll, 1)

    footer = QFrame()
    # Scope ``border-top`` to ``QFrame#LinkedInOutputFooter`` so the
    # cascade does not paint a thin line across every QFrame child of
    # the footer (including the QFrame-based Ghost / Primary buttons),
    # which is what produced the "struck-through" look reported in
    # image 4 of feat/dashboard-and-ui-fixes.
    footer.setObjectName("LinkedInOutputFooter")
    footer.setStyleSheet(
        f"""
        QFrame#LinkedInOutputFooter {{
            background-color: {theme.bg};
            border-top: 1px solid {theme.border};
        }}
        """
    )
    footer_layout = hbox(spacing=10, margins=(24, 12, 24, 12))
    footer_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    footer.setLayout(footer_layout)

    open_btn = GhostButton(txt["output_open_folder_button"], theme=theme, icon=Icons.FOLDER_OPEN)
    if not STATE.last_run_folder:
        open_btn.setEnabled(False)
    open_btn.clicked.connect(lambda: _open_in_explorer(STATE.last_run_folder or ""))
    footer_layout.addWidget(open_btn)
    footer_layout.addStretch(1)

    save_btn = PrimaryButton(txt["output_save_button"], theme=theme, icon=Icons.SAVE_OUTLINED)

    def _on_save() -> None:
        STATE.activity = "saving"
        REFS.request_context_refresh()

        def _worker() -> None:
            try:
                pipeline.save_full_profile()
            except Exception as exc:
                logger_service.log_exception(
                    "ai_linkedin.tab_output", "save_worker_failed", exc,
                )
            REFS.dispatch(_request_full_refresh)
        threading.Thread(target=_worker, daemon=True).start()

    save_btn.clicked.connect(_on_save)
    footer_layout.addWidget(save_btn)
    layout.addWidget(footer)
    return container
