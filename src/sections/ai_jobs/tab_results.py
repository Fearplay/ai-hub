"""Results tab - one card per active position + Save HTML footer.

Empty-state copy is shown when ``STATE.results`` is empty (the user has
not run a search yet, or the search came back with zero verified
positions). Otherwise we render a vertical scroll of cards: title,
work-mode pill, company / location / posted / source meta, summary,
and two action buttons (open posting in browser, copy URL to
clipboard).

The footer hosts the ``Save as HTML`` button. Saving spawns a worker
thread (the file write is fast but the in-app history rewrite touches
``~/AI Hub/history.json``) and shows the resulting path inline once
done.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from typing import Callable, Optional

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QFrame,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.qt.icons import Icons
from src.qt.runtime import dispatch as runtime_dispatch
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    FlowLayout,
    GhostButton,
    IconLabel,
    MutedLabel,
    PrimaryButton,
    SecondaryButton,
    SubtleLabel,
    TitleLabel,
    custom_label,
    hbox,
    vbox,
)
from src.services import clipboard
from src.services import logger as logger_service
from src.sections.ai_jobs import pipeline
from src.sections.ai_jobs.refs import REFS
from src.sections.ai_jobs.state import STATE, TAB_SETUP
from src.sections.ai_jobs.strings import s
from src.theme import Theme


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception:
        return
    request_section_refresh()


def _open_url(url: str) -> None:
    if not url:
        return
    try:
        QDesktopServices.openUrl(QUrl(url))
    except Exception as exc:
        logger_service.log_exception(
            "ai_jobs.tab_results", "open_url_failed", exc, url=url,
        )


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
            "ai_jobs.tab_results", "open_in_explorer_failed", exc, path=path,
        )


def _meta_row(theme: Theme, *, icon: str, label: str, value: str) -> Optional[QFrame]:
    if not value:
        return None
    row = QFrame()
    row.setStyleSheet("background: transparent;")
    layout = hbox(spacing=6, margins=(0, 0, 0, 0))
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    row.setLayout(layout)
    layout.addWidget(IconLabel(icon, color=theme.text_muted, size=14))
    layout.addWidget(SubtleLabel(f"{label}:", theme=theme, size=11, weight=QFont.Weight.DemiBold))
    layout.addWidget(BodyLabel(value, theme=theme, size=12, selectable=True), 1)
    return row


def _work_mode_pill(theme: Theme, mode: str) -> Optional[QFrame]:
    if mode not in {"remote", "hybrid", "onsite"}:
        return None
    pill = QFrame()
    pill.setStyleSheet(
        f"background-color: {rgba(theme.primary, 0.16)}; border-radius: 9px;"
    )
    layout = hbox(spacing=4, margins=(8, 3, 8, 3))
    pill.setLayout(layout)
    layout.addWidget(custom_label(mode.upper(), color=theme.primary, size=10, weight=QFont.Weight.Bold))
    pill.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
    return pill


def _match_pill(theme: Theme, txt: dict, score: Optional[int]) -> Optional[QFrame]:
    """Small "Match XX%" pill rendered in the position card header.

    Colour bands match the HTML export (>=75 green, 50-74 amber,
    <50 red). On-screen the rest of the per-position analysis stays
    lean per user direction - the chips / recommendation paragraph
    only render in the saved HTML.
    """
    if not isinstance(score, int):
        return None

    if score >= 75:
        color = "#22C55E"  # good
    elif score >= 50:
        color = "#F59E0B"  # warn
    else:
        color = "#EF4444"  # danger

    pill = QFrame()
    pill.setStyleSheet(
        f"background-color: {rgba(color, 0.18)}; border-radius: 9px;"
    )
    layout = hbox(spacing=4, margins=(8, 3, 8, 3))
    pill.setLayout(layout)
    layout.addWidget(custom_label(
        txt["results_match_pill_template"].format(score=score),
        color=color, size=10, weight=QFont.Weight.Bold,
    ))
    pill.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
    return pill


def _inactive_pill(theme: Theme, txt: dict, *, marker: str = "") -> QFrame:
    """Red "No longer hiring" pill shown on closed listings.

    Surfaces dead postings instead of dropping them - the verifier
    matched on a known marker phrase ("No longer accepting
    applications", "U\u017e nep\u0159ij\u00edm\u00e1 \u017e\u00e1dosti", "Tahle nab\u00eddka u\u017e je
    pry\u010d", \u2026), an HTTP 404 / 410 status, or a hard scrape
    failure. The matched marker is appended to the tooltip when
    present so the user can verify detection accuracy without
    opening the HTML export.
    """
    color = "#EF4444"  # danger - matches the < 50 score band
    pill = QFrame()
    pill.setStyleSheet(
        f"background-color: {rgba(color, 0.18)}; border-radius: 9px;"
    )
    layout = hbox(spacing=4, margins=(8, 3, 8, 3))
    pill.setLayout(layout)
    layout.addWidget(custom_label(
        txt["results_inactive_pill"],
        color=color, size=10, weight=QFont.Weight.Bold,
    ))
    pill.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
    tooltip = txt["results_inactive_tooltip"]
    if marker:
        tooltip = f'{tooltip}\n\u2192 "{marker}"'
    pill.setToolTip(tooltip)
    return pill


def _relaxed_pill(theme: Theme, txt: dict) -> QFrame:
    """Amber "Less relevant" pill for results from the relaxed pass.

    The pipeline runs a final relaxed broad pass when the strict
    top-ups cannot fill the user's active target; this pill warns the
    user that the posting still active but came from a broader search
    (adjacent role or nearby city). Mirrors :func:`_inactive_pill`'s
    structure so the title row keeps a consistent visual rhythm.
    """
    color = "#F59E0B"  # warn - matches the relaxed-pill CSS in the HTML export
    pill = QFrame()
    pill.setStyleSheet(
        f"background-color: {rgba(color, 0.18)}; border-radius: 9px;"
    )
    layout = hbox(spacing=4, margins=(8, 3, 8, 3))
    pill.setLayout(layout)
    layout.addWidget(custom_label(
        txt["results_relaxed_pill"],
        color=color, size=10, weight=QFont.Weight.Bold,
    ))
    pill.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
    pill.setToolTip(txt["results_relaxed_tooltip"])
    return pill


def _skill_chip(theme: Theme, label: str, *, color: str, fill: str) -> QFrame:
    """Small pill that mirrors the saved-HTML ``.skill-chip`` look.

    Kept in this module (rather than imported from ``tab_skill_gap``)
    so the Results tab does not pull in skill-gap's empty-state
    bootstrapping when there is no profile yet.
    """
    chip = QFrame()
    chip.setStyleSheet(f"background-color: {fill}; border-radius: 12px;")
    layout = hbox(spacing=0, margins=(10, 4, 10, 4))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    chip.setLayout(layout)
    layout.addWidget(custom_label(label, color=color, size=11, weight=QFont.Weight.DemiBold))
    chip.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
    return chip


def _skill_subcard(
    theme: Theme,
    *,
    title: str,
    items: list[str],
    color: str,
) -> Optional[QFrame]:
    """Header + wrapping chip row, or ``None`` when ``items`` is empty.

    Drives the on-screen "Sedí" / "Co může být problém" sections in
    ``_position_card`` so the in-app card looks the same as the saved
    HTML export.
    """
    items = [s for s in (str(x).strip() for x in items or []) if s]
    if not items:
        return None
    card = QFrame()
    card.setObjectName("JobsResultSubCard")
    card.setStyleSheet(
        f"""
        QFrame#JobsResultSubCard {{
            background-color: {rgba(theme.text, 0.04)};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        """
    )
    layout = vbox(spacing=8, margins=(14, 12, 14, 12))
    card.setLayout(layout)
    layout.addWidget(SubtleLabel(title.upper(), theme=theme, size=10, weight=QFont.Weight.Bold))
    chips_holder = QFrame()
    chips_holder.setStyleSheet("background: transparent;")
    flow = FlowLayout(chips_holder, h_spacing=6, v_spacing=6)
    chips_holder.setLayout(flow)
    fill = rgba(color, 0.18)
    for label in items:
        flow.addWidget(_skill_chip(theme, label, color=color, fill=fill))
    layout.addWidget(chips_holder)
    return card


def _recommendation_card(theme: Theme, *, title: str, body: str) -> Optional[QFrame]:
    body = (body or "").strip()
    if not body:
        return None
    card = QFrame()
    card.setObjectName("JobsResultRecCard")
    card.setStyleSheet(
        f"""
        QFrame#JobsResultRecCard {{
            background-color: {rgba(theme.primary, 0.10)};
            border-left: 3px solid {theme.primary};
            border-radius: 10px;
        }}
        """
    )
    layout = vbox(spacing=6, margins=(14, 12, 14, 12))
    card.setLayout(layout)
    layout.addWidget(SubtleLabel(title.upper(), theme=theme, size=10, weight=QFont.Weight.Bold))
    layout.addWidget(BodyLabel(body, theme=theme, size=13, selectable=True))
    return card


def _position_card(
    theme: Theme,
    txt: dict,
    item: dict,
    *,
    on_link_copied: Callable[[str], None],
) -> QFrame:
    is_active = bool(item.get("is_active", True))
    is_relaxed = bool(item.get("is_relaxed", False))
    card = QFrame()
    card.setObjectName("JobsResultCard")
    if not is_active:
        # Muted look for closed listings so the live ones pop visually,
        # without hiding them - the user has to be able to verify the
        # marker detection by clicking through.
        border = rgba("#EF4444", 0.32)
        bg = rgba(theme.surface, 0.7)
    elif is_relaxed:
        # Subtle amber border for relaxed active postings - same colour
        # as the pill so the two visual cues reinforce each other.
        border = rgba("#F59E0B", 0.32)
        bg = theme.surface
    else:
        border = theme.border
        bg = theme.surface
    card.setStyleSheet(
        f"""
        QFrame#JobsResultCard {{
            background-color: {bg};
            border: 1px solid {border};
            border-radius: 14px;
        }}
        """
    )
    layout = vbox(spacing=10, margins=(18, 16, 18, 16))
    card.setLayout(layout)

    title_row = QFrame()
    title_row.setStyleSheet("background: transparent;")
    title_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    title_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    title_row.setLayout(title_layout)
    title_label = TitleLabel(item.get("title", ""), theme=theme, size=15, weight=QFont.Weight.Bold)
    title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    title_layout.addWidget(title_label, 1)
    if not is_active:
        marker = (item.get("inactive_reason") or "").strip()
        title_layout.addWidget(_inactive_pill(theme, txt, marker=marker))
    elif is_relaxed:
        title_layout.addWidget(_relaxed_pill(theme, txt))
    match_pill = _match_pill(theme, txt, item.get("match_score"))
    if match_pill is not None:
        title_layout.addWidget(match_pill)
    pill = _work_mode_pill(theme, item.get("work_mode", "unknown"))
    if pill is not None:
        title_layout.addWidget(pill)
    layout.addWidget(title_row)

    meta_holder = QFrame()
    meta_holder.setStyleSheet("background: transparent;")
    meta_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    meta_holder.setLayout(meta_layout)
    salary_value = (item.get("salary_text") or "").strip()
    contract_raw = (item.get("contract_type") or "unknown").strip().lower()
    contract_value = contract_raw.upper() if contract_raw and contract_raw != "unknown" else ""
    for icon_name, label_key, value in (
        (Icons.WORK_OUTLINE, txt["results_meta_company"], item.get("company", "")),
        (Icons.LOCATION_ON, txt["results_meta_location"], item.get("location", "")),
        (Icons.SCHEDULE, txt["results_meta_posted"], item.get("posted", "")),
        (Icons.PAYMENTS_OUTLINED, txt["results_meta_salary"], salary_value),
        (Icons.WORKSPACE_PREMIUM_OUTLINED, txt["results_meta_contract"], contract_value),
        (Icons.PUBLIC, txt["results_meta_source"], item.get("source", "")),
    ):
        row = _meta_row(theme, icon=icon_name, label=label_key, value=value)
        if row is not None:
            meta_layout.addWidget(row)
    layout.addWidget(meta_holder)

    summary = (item.get("summary") or "").strip()
    if summary:
        layout.addWidget(BodyLabel(summary, theme=theme, size=13, selectable=True))

    # Per-position AI fields - only computed for active postings (Pass 4
    # of the search pipeline). Mirrors the saved HTML export so the
    # in-app card carries the same context the user sees offline.
    if is_active:
        fit_card = _skill_subcard(
            theme,
            title=txt["results_card_fit_title"],
            items=item.get("matched_skills") or [],
            color="#22C55E",
        )
        if fit_card is not None:
            layout.addWidget(fit_card)
        concerns_card = _skill_subcard(
            theme,
            title=txt["results_card_concerns_title"],
            items=item.get("missing_skills") or [],
            color="#EF4444",
        )
        if concerns_card is not None:
            layout.addWidget(concerns_card)
        rec_card = _recommendation_card(
            theme,
            title=txt["results_card_recommendation_title"],
            body=str(item.get("recommendation") or ""),
        )
        if rec_card is not None:
            layout.addWidget(rec_card)

    actions = QFrame()
    actions.setStyleSheet("background: transparent;")
    actions_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    actions.setLayout(actions_layout)

    open_btn = PrimaryButton(txt["results_open_btn"], theme=theme, icon=Icons.OPEN_IN_NEW)
    open_btn.clicked.connect(lambda _checked=False, url=item.get("url", ""): _open_url(url))
    actions_layout.addWidget(open_btn)

    copy_btn = SecondaryButton(txt["results_copy_btn"], theme=theme, icon=Icons.CONTENT_COPY)
    def _copy(url: str = item.get("url", "")) -> None:
        if not url:
            return
        if clipboard.copy(url):
            on_link_copied(url)
    copy_btn.clicked.connect(lambda _checked=False: _copy())
    actions_layout.addWidget(copy_btn)
    actions_layout.addStretch(1)
    layout.addWidget(actions)

    return card


def _empty_state(theme: Theme, txt: dict) -> QWidget:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=8, margins=(40, 60, 40, 60))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    holder.setLayout(layout)
    layout.addWidget(IconLabel(Icons.MANAGE_SEARCH, color=theme.text_muted, size=42),
                     alignment=Qt.AlignmentFlag.AlignHCenter)
    layout.addWidget(TitleLabel(txt["results_empty_title"], theme=theme, size=16))
    desc = MutedLabel(txt["results_empty_desc"], theme=theme, size=12)
    desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(desc)

    open_setup_btn = GhostButton(txt["tab_setup"], theme=theme, icon=Icons.TUNE)
    def _go_setup() -> None:
        STATE.active_tab = TAB_SETUP
        REFS.dispatch(_request_full_refresh)
    open_setup_btn.clicked.connect(_go_setup)
    layout.addWidget(open_setup_btn, 0, Qt.AlignmentFlag.AlignHCenter)
    return holder


def _summary_card(theme: Theme, txt: dict) -> Optional[QFrame]:
    summary = (STATE.summary or "").strip()
    if not summary:
        return None
    card = QFrame()
    card.setObjectName("JobsSummaryCard")
    card.setStyleSheet(
        f"""
        QFrame#JobsSummaryCard {{
            background-color: {rgba(theme.primary, 0.10)};
            border: 1px solid {rgba(theme.primary, 0.24)};
            border-radius: 14px;
        }}
        """
    )
    layout = vbox(spacing=8, margins=(18, 14, 18, 14))
    card.setLayout(layout)

    head = QFrame()
    head.setStyleSheet("background: transparent;")
    hl = hbox(spacing=8, margins=(0, 0, 0, 0))
    hl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    head.setLayout(hl)
    hl.addWidget(IconLabel(Icons.AUTO_AWESOME, color=theme.primary, size=18))
    hl.addWidget(custom_label(txt["results_summary_title"], color=theme.primary, size=12, weight=QFont.Weight.Bold))
    layout.addWidget(head)

    layout.addWidget(BodyLabel(summary, theme=theme, size=13, selectable=True))

    if STATE.last_query:
        layout.addWidget(SubtleLabel(
            txt["results_query_template"].format(query=STATE.last_query),
            theme=theme, size=11, italic=True,
        ))
    if STATE.last_location_label:
        layout.addWidget(SubtleLabel(
            txt["results_location_template"].format(location=STATE.last_location_label),
            theme=theme, size=11, italic=True,
        ))
    if STATE.last_dropped:
        layout.addWidget(SubtleLabel(
            txt["results_dropped_note_template"].format(count=STATE.last_dropped),
            theme=theme, size=11, italic=True,
        ))
    if STATE.last_inactive:
        layout.addWidget(SubtleLabel(
            txt["results_inactive_count_template"].format(count=STATE.last_inactive),
            theme=theme, size=11, italic=True,
        ))
    return card


def build_results_tab(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    if not STATE.has_results():
        layout.addWidget(_empty_state(theme, txt), 1)
        return container

    # Body --------------------------------------------------------------
    body_holder = QWidget()
    body_holder.setStyleSheet(f"background-color: {theme.bg};")
    body_layout = vbox(spacing=14, margins=(24, 18, 24, 18))
    body_holder.setLayout(body_layout)

    header = QFrame()
    header.setStyleSheet("background: transparent;")
    header_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    header.setLayout(header_layout)
    header_layout.addWidget(TitleLabel(txt["results_title"], theme=theme, size=18, weight=QFont.Weight.Bold))
    header_layout.addWidget(MutedLabel(
        txt["results_subtitle_template"].format(count=STATE.active_results_count()),
        theme=theme, size=12,
    ))
    body_layout.addWidget(header)

    summary_card = _summary_card(theme, txt)
    if summary_card is not None:
        body_layout.addWidget(summary_card)

    # Status label captured by closures so the Save action can update it
    # without rebuilding the tab.
    status_label = SubtleLabel("", theme=theme, size=11)

    def _on_link_copied(url: str) -> None:
        runtime_dispatch(lambda: status_label.setText(txt["results_copied_template"].format(url=url)))

    for item in STATE.results:
        body_layout.addWidget(_position_card(theme, txt, item, on_link_copied=_on_link_copied))
    body_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(body_holder)
    layout.addWidget(scroll, 1)

    # --- scroll-position memory --------------------------------------
    # Mirrors the Setup tab: copying / opening a job link, switching
    # tabs, or any other action that triggers ``request_section_refresh``
    # rebuilds this tab and resets the QScrollArea to y=0. Saving the
    # last known position to ``STATE.results_scroll_pos`` and restoring
    # it on the next event-loop tick keeps the user in place.
    _vbar = scroll.verticalScrollBar()

    def _save_scroll_pos(value: int) -> None:
        STATE.results_scroll_pos = max(0, int(value))

    _vbar.valueChanged.connect(_save_scroll_pos)

    def _restore_scroll_pos() -> None:
        try:
            target = max(0, min(STATE.results_scroll_pos, _vbar.maximum()))
            _vbar.setValue(target)
        except RuntimeError:
            pass

    if STATE.results_scroll_pos > 0:
        QTimer.singleShot(0, _restore_scroll_pos)

    # Footer ------------------------------------------------------------
    footer = QFrame()
    footer.setObjectName("JobsResultsFooter")
    footer.setStyleSheet(
        f"""
        QFrame#JobsResultsFooter {{
            background-color: {theme.bg};
            border-top: 1px solid {theme.border};
        }}
        """
    )
    footer_layout = vbox(spacing=8, margins=(24, 12, 24, 12))
    footer.setLayout(footer_layout)

    button_row = QFrame()
    button_row.setStyleSheet("background: transparent;")
    button_row_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    button_row_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    button_row.setLayout(button_row_layout)
    button_row_layout.addWidget(status_label, 1)

    save_btn = PrimaryButton(txt["results_save_btn"], theme=theme, icon=Icons.SAVE_OUTLINED)
    button_row_layout.addWidget(save_btn)
    footer_layout.addWidget(button_row)
    layout.addWidget(footer)

    def _set_status(message: str, *, error: bool = False) -> None:
        try:
            status_label.setText(message)
            status_label.setStyleSheet(
                f"color: {'#EF4444' if error else theme.text_subtle}; background: transparent;"
            )
        except RuntimeError:
            logger_service.log_event(
                "INFO", "ai_jobs.tab_results", "status_label_stale",
            )

    def _set_button(running: bool) -> None:
        try:
            save_btn.setEnabled(not running)
            save_btn.setText(txt["results_saving"] if running else txt["results_save_btn"])
        except RuntimeError:
            pass

    def _on_save() -> None:
        _set_button(True)
        _set_status("")

        def _worker() -> None:
            try:
                result = pipeline.save_html(output_lang=lang)
            except Exception as exc:
                logger_service.log_exception(
                    "ai_jobs.tab_results", "save_html_worker_failed", exc,
                )
                runtime_dispatch(lambda: _set_status(txt["results_save_failed_template"].format(error=exc), error=True))
                runtime_dispatch(lambda: _set_button(False))
                return

            runtime_dispatch(lambda: _set_button(False))
            if not result.ok:
                runtime_dispatch(lambda: _set_status(txt["results_save_failed_template"].format(error=result.error), error=True))
                return
            runtime_dispatch(lambda: _set_status(txt["results_save_done_template"].format(path=result.folder), error=False))
            runtime_dispatch(lambda: _open_in_explorer(result.folder))
            runtime_dispatch(_request_full_refresh)

        threading.Thread(target=_worker, daemon=True).start()

    save_btn.clicked.connect(_on_save)
    return container
