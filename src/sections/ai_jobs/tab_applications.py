"""Applications tab - a lightweight tracker for the roles the user pursues.

One card per saved application: editable status (dropdown), deadline, next
step and notes, plus links to the posting / any linked documents. Data
lives in :mod:`src.services.applications_store` (``~/AI Hub/applications.json``);
entries are created from the Results tab's "Save to applications" action.

This is an MVP list (not a kanban). Status changes / deletes trigger a full
section refresh so the status pill recolours; free-text edits persist
silently (debounced for notes) so the user does not lose focus mid-typing.
"""

from __future__ import annotations

import os
import subprocess
import sys

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import QFrame, QScrollArea, QSizePolicy, QWidget

from src.qt.icons import Icons
from src.qt.runtime import dispatch as runtime_dispatch
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    GhostButton,
    IconLabel,
    IconOnlyButton,
    MutedLabel,
    Pill,
    ScrollSafeComboBox,
    SubtleLabel,
    TitleLabel,
    custom_label,
    hbox,
    themed_line_edit,
    themed_text_edit,
    vbox,
    wrap_label_slot,
)
from src.services import applications_store
from src.services import logger as logger_service
from src.sections.ai_jobs.strings import s
from src.theme import Theme


# Module-level so the scroll offset survives the full-section rebuild that
# fires on a status change / delete.
_SCROLL: dict[str, int] = {"y": 0}


_STATUS_COLORS = {
    applications_store.STATUS_FOUND: "#94A3B8",
    applications_store.STATUS_CV_READY: "#6366F1",
    applications_store.STATUS_SENT: "#3B82F6",
    applications_store.STATUS_INTERVIEW: "#F59E0B",
    applications_store.STATUS_OFFER: "#22C55E",
    applications_store.STATUS_REJECTED: "#EF4444",
    applications_store.STATUS_ACCEPTED: "#22C55E",
    applications_store.STATUS_ARCHIVED: "#94A3B8",
}


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception:
        return
    request_section_refresh()


def _status_label(status: str, txt: dict) -> str:
    return txt.get(f"apps_status_{status}", status.title())


def _open_url(url: str) -> None:
    if not url:
        return
    try:
        QDesktopServices.openUrl(QUrl(url))
    except Exception as exc:
        logger_service.log_exception("ai_jobs.tab_applications", "open_url_failed", exc, url=url)


def _open_path(path_str: str) -> None:
    if not path_str or not os.path.exists(path_str):
        logger_service.log_event(
            "WARNING", "ai_jobs.tab_applications", "open_path_missing", path=str(path_str),
        )
        return
    try:
        if os.name == "nt":
            os.startfile(path_str)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path_str])
        else:
            subprocess.Popen(["xdg-open", path_str])
    except Exception as exc:
        logger_service.log_exception("ai_jobs.tab_applications", "open_path_failed", exc, path=path_str)


def _styled_combo(theme: Theme) -> ScrollSafeComboBox:
    combo = ScrollSafeComboBox()
    combo.setStyleSheet(
        f"""
        QComboBox {{
            background-color: {theme.surface_2};
            color: {theme.text};
            border: 1px solid transparent;
            border-radius: 10px;
            padding: 6px 10px;
            min-height: 20px;
        }}
        QComboBox:hover {{ border: 1px solid {rgba(theme.primary, 0.30)}; }}
        QComboBox::drop-down {{ border: none; width: 22px; }}
        QComboBox QAbstractItemView {{
            background-color: {theme.surface};
            color: {theme.text};
            border: 1px solid {theme.border};
            selection-background-color: {rgba(theme.primary, 0.20)};
            selection-color: {theme.text};
            outline: 0;
        }}
        """
    )
    return combo


def _labeled_field(theme: Theme, label: str, field: QWidget) -> QWidget:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    layout.addWidget(SubtleLabel(label.upper(), theme=theme, size=10, weight=QFont.Weight.Bold))
    layout.addWidget(field)
    return holder


def _application_card(theme: Theme, txt: dict, app: dict) -> QFrame:
    app_id = app.get("id", "")
    status = app.get("status", applications_store.STATUS_FOUND)
    accent = _STATUS_COLORS.get(status, theme.text_muted)

    card = QFrame()
    card.setObjectName("JobsAppCard")
    card.setStyleSheet(
        f"""
        QFrame#JobsAppCard {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-left: 3px solid {accent};
            border-radius: 14px;
        }}
        """
    )
    layout = vbox(spacing=12, margins=(18, 16, 18, 16))
    card.setLayout(layout)

    # Title row: title/company + status pill + delete.
    head = QFrame()
    head.setStyleSheet("background: transparent;")
    head_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    head_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    head.setLayout(head_layout)

    title_holder = QFrame()
    title_holder.setStyleSheet("background: transparent;")
    title_holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    th_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    title_holder.setLayout(th_layout)
    title_label = TitleLabel(app.get("title", ""), theme=theme, size=15, weight=QFont.Weight.Bold)
    wrap_label_slot(title_label)
    th_layout.addWidget(title_label)
    sub_bits = [b for b in (app.get("company", ""), app.get("source", "")) if b]
    if sub_bits:
        sub_label = MutedLabel("  \u00b7  ".join(sub_bits), theme=theme, size=12)
        wrap_label_slot(sub_label)
        th_layout.addWidget(sub_label)
    created = (app.get("created_at") or "").strip()
    if created:
        th_layout.addWidget(
            SubtleLabel(txt["apps_added_on_template"].format(when=created), theme=theme, size=11, italic=True)
        )
    head_layout.addWidget(title_holder, 1)

    head_layout.addWidget(
        Pill(text=_status_label(status, txt), bg=rgba(accent, 0.16), fg=accent),
        0, Qt.AlignmentFlag.AlignTop,
    )
    del_btn = IconOnlyButton(
        Icons.DELETE_OUTLINE, color="#EF4444", size=18,
        bg_hover=rgba("#EF4444", 0.14), tooltip=txt["apps_delete_btn"],
    )

    def _on_delete() -> None:
        applications_store.delete_application(app_id)
        runtime_dispatch(_request_full_refresh)

    del_btn.clicked.connect(_on_delete)
    head_layout.addWidget(del_btn, 0, Qt.AlignmentFlag.AlignTop)
    layout.addWidget(head)

    # Status dropdown + deadline row.
    row1 = QFrame()
    row1.setStyleSheet("background: transparent;")
    row1_layout = hbox(spacing=12, margins=(0, 0, 0, 0))
    row1_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    row1.setLayout(row1_layout)

    status_combo = _styled_combo(theme)
    for st in applications_store.STATUSES:
        status_combo.addItem(_status_label(st, txt), userData=st)
    try:
        status_combo.setCurrentIndex(list(applications_store.STATUSES).index(status))
    except ValueError:
        status_combo.setCurrentIndex(0)

    def _on_status(index: int) -> None:
        new_status = status_combo.itemData(index) or applications_store.STATUS_FOUND
        if new_status == app.get("status"):
            return
        applications_store.update_application(app_id, status=new_status)
        runtime_dispatch(_request_full_refresh)

    status_combo.currentIndexChanged.connect(_on_status)
    row1_layout.addWidget(_labeled_field(theme, txt["apps_status_label"], status_combo), 1)

    deadline_field = themed_line_edit(theme, placeholder=txt["apps_deadline_hint"])
    deadline_field.setText(app.get("deadline", ""))
    deadline_field.editingFinished.connect(
        lambda: applications_store.update_application(app_id, deadline=deadline_field.text().strip())
    )
    row1_layout.addWidget(_labeled_field(theme, txt["apps_deadline_label"], deadline_field), 1)
    layout.addWidget(row1)

    # Next step.
    next_field = themed_line_edit(theme, placeholder=txt["apps_next_step_hint"])
    next_field.setText(app.get("next_step", ""))
    next_field.editingFinished.connect(
        lambda: applications_store.update_application(app_id, next_step=next_field.text().strip())
    )
    layout.addWidget(_labeled_field(theme, txt["apps_next_step_label"], next_field))

    # Notes (debounced save so we keep focus while typing).
    notes_field = themed_text_edit(theme, placeholder=txt["apps_notes_hint"], min_height=70)
    notes_field.setPlainText(app.get("notes", ""))
    notes_timer = QTimer(notes_field)
    notes_timer.setSingleShot(True)
    notes_timer.setInterval(500)
    notes_timer.timeout.connect(
        lambda: applications_store.update_application(app_id, notes=notes_field.toPlainText().strip())
    )
    notes_field.textChanged.connect(notes_timer.start)
    layout.addWidget(_labeled_field(theme, txt["apps_notes_label"], notes_field))

    # Linked documents.
    documents = app.get("documents") or []
    if documents:
        layout.addWidget(SubtleLabel(txt["apps_documents_label"].upper(), theme=theme, size=10, weight=QFont.Weight.Bold))
        for doc in documents:
            doc_path = str(doc.get("path") or "")
            doc_row = QFrame()
            doc_row.setStyleSheet("background: transparent;")
            dl = hbox(spacing=8, margins=(0, 0, 0, 0))
            dl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            doc_row.setLayout(dl)
            dl.addWidget(IconLabel(Icons.DESCRIPTION_OUTLINED, color=theme.text_muted, size=16))
            doc_label = BodyLabel(str(doc.get("label") or doc_path), theme=theme, size=12)
            wrap_label_slot(doc_label)
            dl.addWidget(doc_label, 1)
            open_doc = GhostButton(txt["apps_open_doc_btn"], theme=theme, icon=Icons.OPEN_IN_NEW)
            open_doc.clicked.connect(lambda _c=False, p=doc_path: _open_path(p))
            dl.addWidget(open_doc)
            layout.addWidget(doc_row)

    # Footer actions.
    url = (app.get("url") or "").strip()
    if url:
        actions = QFrame()
        actions.setStyleSheet("background: transparent;")
        actions_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
        actions.setLayout(actions_layout)
        open_btn = GhostButton(txt["apps_open_btn"], theme=theme, icon=Icons.OPEN_IN_NEW)
        open_btn.clicked.connect(lambda _c=False, u=url: _open_url(u))
        actions_layout.addWidget(open_btn)
        actions_layout.addStretch(1)
        layout.addWidget(actions)

    return card


def _empty_state(theme: Theme, txt: dict) -> QWidget:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    # NB: centre the block with stretches rather than a layout-level
    # ``AlignCenter`` + per-item ``AlignHCenter``. An item alignment flag
    # makes QBoxLayout fall back to the label's single-line ``sizeHint``
    # instead of its ``heightForWidth``, which clipped the wrapped second
    # line of ``apps_empty_desc`` (see the "Uložit do žádostí" overflow).
    layout = vbox(spacing=8, margins=(40, 48, 40, 48))
    holder.setLayout(layout)
    layout.addStretch(1)

    icon_row = hbox(spacing=0, margins=(0, 0, 0, 0))
    icon_row.addStretch(1)
    icon_row.addWidget(IconLabel(Icons.WORK_OUTLINE, color=theme.text_muted, size=42))
    icon_row.addStretch(1)
    layout.addLayout(icon_row)

    title_label = TitleLabel(txt["apps_empty_title"], theme=theme, size=16)
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title_label)

    desc = MutedLabel(txt["apps_empty_desc"], theme=theme, size=12)
    desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
    desc.setMaximumWidth(460)
    desc_row = hbox(spacing=0, margins=(0, 0, 0, 0))
    desc_row.addStretch(1)
    desc_row.addWidget(desc)
    desc_row.addStretch(1)
    layout.addLayout(desc_row)

    layout.addStretch(1)
    return holder


def build_applications_tab(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    try:
        apps = applications_store.list_applications()
    except Exception as exc:
        logger_service.log_exception("ai_jobs.tab_applications", "list_failed", exc)
        apps = []

    if not apps:
        layout.addWidget(_empty_state(theme, txt), 1)
        return container

    body_holder = QWidget()
    body_holder.setStyleSheet(f"background-color: {theme.bg};")
    body_layout = vbox(spacing=14, margins=(24, 18, 24, 24))
    body_holder.setLayout(body_layout)

    header = QFrame()
    header.setStyleSheet("background: transparent;")
    header_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    header.setLayout(header_layout)
    header_layout.addWidget(TitleLabel(txt["apps_title"], theme=theme, size=18, weight=QFont.Weight.Bold))
    header_layout.addWidget(
        MutedLabel(txt["apps_count_template"].format(count=len(apps)), theme=theme, size=12)
    )
    body_layout.addWidget(header)

    try:
        for app in apps:
            body_layout.addWidget(_application_card(theme, txt, app))
    except Exception as exc:
        logger_service.log_exception("ai_jobs.tab_applications", "build_cards_failed", exc)
        raise
    body_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(body_holder)
    layout.addWidget(scroll, 1)

    _vbar = scroll.verticalScrollBar()
    _vbar.valueChanged.connect(lambda v: _SCROLL.__setitem__("y", max(0, int(v))))
    if _SCROLL["y"] > 0:
        def _restore() -> None:
            try:
                _vbar.setValue(max(0, min(_SCROLL["y"], _vbar.maximum())))
            except RuntimeError:
                pass
        QTimer.singleShot(0, _restore)

    return container
