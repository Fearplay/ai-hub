"""AI Bug Report - centre column view.

Header (with the help dialog button) + 3 tabs:

* **Input** - description + optional environment hints + a single drop
  zone that accepts both screenshots (PNG / JPG / WEBP / GIF / BMP /
  HEIC) and supporting documents (TXT / LOG / JSON / PDF / DOCX / MD /
  HTML). Each attached item appears as a chip with a remove button.
* **Preview** - renders the structured bug-report fields as titled
  cards; the user can edit the title / severity / priority inline
  before saving.
* **Export** - the Save-as-Word action + an Open-output-folder button.

State that must survive theme / language / tab toggles lives in
:mod:`src.sections.ai_bug_report.state`. The pipeline call runs on a
background thread so the UI stays responsive while the LLM is in
flight.
"""

from __future__ import annotations

import os
import threading
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QScrollArea,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from src.components.file_drop_zone import file_drop_zone
from src.components.header import header
from src.components.tab_bar import tab_bar
from src.qt.icons import Icons
from src.qt.runtime import dispatch
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    GhostButton,
    IconLabel,
    IconOnlyButton,
    MutedLabel,
    Pill,
    PrimaryButton,
    SubtleLabel,
    TitleLabel,
    custom_label,
    hbox,
    themed_line_edit,
    themed_text_edit,
    vbox,
)
from src.services import logger as logger_service
from src.services import secrets, settings_store, store
from src.services.file_parser import (
    SUPPORTED_EXTENSIONS,
    human_size,
    parse_file,
)
from src.sections.ai_bug_report import pipeline
from src.sections.ai_bug_report.how_to import open_bug_report_how_to
from src.sections.ai_bug_report.refs import REFS
from src.sections.ai_bug_report.state import (
    PRIORITY_VALUES,
    SEVERITY_VALUES,
    REPRODUCIBILITY_VALUES,
    TAB_EXPORT,
    TAB_INPUT,
    TAB_PREVIEW,
    DocAttachment,
    ImageAttachment,
    STATE,
)
from src.sections.ai_bug_report.strings import s
from src.theme import Theme


_IMAGE_EXTENSIONS = ("png", "jpg", "jpeg", "webp", "gif", "bmp", "heic")
_IMAGE_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
    "bmp": "image/bmp",
    "heic": "image/heic",
}
_DOC_EXTENSIONS = tuple(SUPPORTED_EXTENSIONS) + ("log", "json")
_ATTACHMENT_EXTENSIONS = _IMAGE_EXTENSIONS + _DOC_EXTENSIONS


# ---------------------------------------------------------------------------
# Drop-zone routing helpers (image vs text-document).
# ---------------------------------------------------------------------------


def _ext_of(path: str) -> str:
    return os.path.splitext(path)[1].lower().lstrip(".")


def _ingest_image(path: str) -> Optional[ImageAttachment]:
    """Read a screenshot from disk into an :class:`ImageAttachment`.

    Returns ``None`` when the file is missing / unreadable. The bytes
    are captured eagerly so the user can move / delete the source file
    after attaching without breaking the AI call.
    """
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        logger_service.log_exception(
            "ai_bug_report.view", "ingest_image_read_failed", exc, path=path,
        )
        return None
    ext = _ext_of(path)
    name = os.path.basename(path)
    return ImageAttachment(
        path=path,
        name=name or f"screenshot.{ext or 'png'}",
        ext=ext or "png",
        size_bytes=len(data),
        bytes_data=data,
        mime=_IMAGE_MIME.get(ext, "image/png"),
    )


def _ingest_log_or_text(path: str) -> Optional[DocAttachment]:
    """Read a .log / .json / .txt file via simple text read.

    The shared :func:`src.services.file_parser.parse_file` already
    handles PDF / DOCX / HTML / MD / TXT; this helper covers the two
    extra extensions the bug-report UI advertises (.log / .json) by
    falling back to a UTF-8 read so the AI can see log lines verbatim.
    """
    try:
        text = open(path, "r", encoding="utf-8", errors="ignore").read()
    except OSError as exc:
        logger_service.log_exception(
            "ai_bug_report.view", "ingest_log_read_failed", exc, path=path,
        )
        return None
    ext = _ext_of(path)
    name = os.path.basename(path)
    try:
        size = os.path.getsize(path)
    except OSError:
        size = len(text.encode("utf-8", errors="ignore"))
    return DocAttachment(
        path=path,
        name=name or f"document.{ext or 'txt'}",
        ext=ext or "txt",
        size_bytes=size,
        text=text.strip(),
    )


def _ingest_document(path: str) -> Optional[DocAttachment]:
    parsed = parse_file(path)
    if parsed.error:
        logger_service.log_event(
            "WARNING",
            "ai_bug_report.view",
            "ingest_document_parse_failed",
            path=path,
            error=parsed.error,
        )
        return None
    if not parsed.text:
        return None
    return DocAttachment(
        path=parsed.path,
        name=parsed.name,
        ext=parsed.ext,
        size_bytes=parsed.size_bytes,
        text=parsed.text,
    )


# ---------------------------------------------------------------------------
# Layout helpers.
# ---------------------------------------------------------------------------


def _clear_layout(layout) -> None:
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.deleteLater()


def _clear_widget(widget: QWidget) -> None:
    _clear_layout(widget.layout())


def _step_card(
    theme: Theme,
    *,
    label: str,
    title: str,
    desc: str,
    body: QWidget,
) -> QFrame:
    card = QFrame()
    card.setObjectName("BugReportStepCard")
    card.setStyleSheet(
        f"""
        QFrame#BugReportStepCard {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 14px;
        }}
        """
    )
    layout = vbox(spacing=4, margins=(18, 18, 18, 18))
    card.setLayout(layout)

    step_label = custom_label(label, color=theme.primary, size=11, weight=700)
    layout.addWidget(step_label)
    layout.addWidget(TitleLabel(title, theme=theme, size=15, weight=QFont.Weight.Bold))
    layout.addWidget(MutedLabel(desc, theme=theme, size=12))
    layout.addSpacing(8)
    layout.addWidget(body)
    return card


def _attachment_chip(
    theme: Theme,
    txt: dict,
    *,
    icon_name: str,
    badge: str,
    name: str,
    sub: str,
    on_remove: Callable[[], None],
) -> QFrame:
    chip = QFrame()
    chip.setObjectName("BugReportChip")
    chip.setStyleSheet(
        f"""
        QFrame#BugReportChip {{
            background-color: {theme.surface_2};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        """
    )
    layout = hbox(spacing=10, margins=(12, 10, 12, 10))
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    chip.setLayout(layout)

    icon_box = QFrame()
    icon_box.setFixedSize(34, 34)
    icon_box.setStyleSheet(
        f"background-color: {rgba(theme.primary, 0.14)}; border-radius: 8px;"
    )
    icon_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setLayout(icon_layout)
    icon_layout.addWidget(
        IconLabel(icon_name, color=theme.primary, size=18),
        alignment=Qt.AlignmentFlag.AlignCenter,
    )
    layout.addWidget(icon_box)

    info = QFrame()
    info.setStyleSheet("background: transparent;")
    info.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    info_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    info.setLayout(info_layout)
    name_row = QFrame()
    name_row.setStyleSheet("background: transparent;")
    name_row_layout = hbox(spacing=6, margins=(0, 0, 0, 0))
    name_row_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    name_row.setLayout(name_row_layout)
    name_row_layout.addWidget(
        Pill(text=badge, bg=theme.primary, fg="#FFFFFF")
    )
    name_row_layout.addWidget(
        BodyLabel(name, theme=theme, size=13, weight=QFont.Weight.DemiBold), 1
    )
    info_layout.addWidget(name_row)
    info_layout.addWidget(MutedLabel(sub, theme=theme, size=11))
    layout.addWidget(info, 1)

    close_btn = IconOnlyButton(
        Icons.CLOSE,
        color=theme.text_muted,
        size=16,
        bg_hover=theme.surface,
        tooltip=txt["remove_btn"],
    )
    close_btn.clicked.connect(on_remove)
    layout.addWidget(close_btn)
    return chip


# ---------------------------------------------------------------------------
# Input tab.
# ---------------------------------------------------------------------------


def _build_input_tab(
    theme: Theme,
    txt: dict,
    *,
    on_state_change: Callable[[], None],
) -> QWidget:
    holder = QWidget()
    holder.setStyleSheet("background: transparent;")
    holder_layout = vbox(spacing=14, margins=(0, 0, 0, 0))
    holder.setLayout(holder_layout)

    desc_holder = QWidget()
    desc_holder.setStyleSheet("background: transparent;")
    desc_layout = vbox(spacing=6, margins=(0, 0, 0, 0))
    desc_holder.setLayout(desc_layout)
    desc_layout.addWidget(
        BodyLabel(
            txt["description_label"],
            theme=theme,
            size=12,
            weight=QFont.Weight.DemiBold,
        )
    )
    desc_edit = themed_text_edit(theme, placeholder=txt["description_hint"], min_height=140)
    desc_edit.setPlainText(STATE.description)
    desc_edit.textChanged.connect(
        lambda: (
            setattr(STATE, "description", desc_edit.toPlainText()),
            on_state_change(),
        )
    )
    desc_layout.addWidget(desc_edit)

    desc_layout.addSpacing(6)
    desc_layout.addWidget(
        BodyLabel(
            txt["env_label"],
            theme=theme,
            size=12,
            weight=QFont.Weight.DemiBold,
        )
    )
    env_edit = themed_line_edit(theme, placeholder=txt["env_hint"])
    env_edit.setText(STATE.environment_hint)
    env_edit.textChanged.connect(
        lambda value: (
            setattr(STATE, "environment_hint", value),
            on_state_change(),
        )
    )
    desc_layout.addWidget(env_edit)

    desc_card = _step_card(
        theme,
        label=txt["step_input_label"],
        title=txt["step_input_title"],
        desc=txt["step_input_desc"],
        body=desc_holder,
    )

    attachments_holder = QWidget()
    attachments_holder.setStyleSheet("background: transparent;")
    attachments_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    attachments_holder.setLayout(attachments_layout)

    chips_holder = QWidget()
    chips_holder.setStyleSheet("background: transparent;")
    chips_layout = vbox(spacing=6, margins=(0, 0, 0, 0))
    chips_holder.setLayout(chips_layout)

    def _render_chips() -> None:
        _clear_widget(chips_holder)
        if not STATE.images and not STATE.documents:
            chips_layout.addWidget(
                MutedLabel(txt["no_attachments"], theme=theme, size=12)
            )
            return
        for idx, img in enumerate(list(STATE.images)):
            chips_layout.addWidget(
                _attachment_chip(
                    theme,
                    txt,
                    icon_name=Icons.IMAGE_OUTLINED,
                    badge=txt["attachment_image_badge"],
                    name=img.name,
                    sub=f"{img.ext.upper()} \u00b7 {human_size(img.size_bytes)}",
                    on_remove=lambda i=idx: _remove_image(i),
                )
            )
        for idx, doc in enumerate(list(STATE.documents)):
            chips_layout.addWidget(
                _attachment_chip(
                    theme,
                    txt,
                    icon_name=Icons.DESCRIPTION_OUTLINED,
                    badge=txt["attachment_doc_badge"],
                    name=doc.name,
                    sub=f"{doc.ext.upper()} \u00b7 {human_size(doc.size_bytes)}",
                    on_remove=lambda i=idx: _remove_doc(i),
                )
            )

    def _remove_image(index: int) -> None:
        if 0 <= index < len(STATE.images):
            STATE.images.pop(index)
            STATE.reset_result()
            _render_chips()
            on_state_change()

    def _remove_doc(index: int) -> None:
        if 0 <= index < len(STATE.documents):
            STATE.documents.pop(index)
            STATE.reset_result()
            _render_chips()
            on_state_change()

    def _on_drop(parsed) -> None:
        """Route the drop zone callback to either image or doc storage.

        The shared :func:`file_drop_zone` already validated the
        extension is in :data:`_ATTACHMENT_EXTENSIONS`. We re-derive
        whether it is an image from the parsed file's extension; for
        images we re-read the raw bytes from disk because the shared
        parser only returns the text body, and for log / json /
        markdown / text we use a UTF-8 read fallback when the shared
        parser returned an empty text (which happens for .log / .json
        because they are not in the official SUPPORTED_EXTENSIONS).
        """
        try:
            ext = (parsed.ext or "").lower()
            path = parsed.path
            if ext in _IMAGE_EXTENSIONS:
                attachment = _ingest_image(path)
                if attachment is not None:
                    STATE.images.append(attachment)
            elif ext in ("log", "json"):
                doc = _ingest_log_or_text(path)
                if doc is not None:
                    STATE.documents.append(doc)
            else:
                # parsed already has text from file_drop_zone's parse_file
                if parsed.text:
                    STATE.documents.append(
                        DocAttachment(
                            path=parsed.path,
                            name=parsed.name,
                            ext=parsed.ext,
                            size_bytes=parsed.size_bytes,
                            text=parsed.text,
                        )
                    )
                else:
                    doc = _ingest_document(path)
                    if doc is not None:
                        STATE.documents.append(doc)
            STATE.reset_result()
            _render_chips()
            on_state_change()
        except Exception as exc:
            logger_service.log_exception(
                "ai_bug_report.view", "on_drop_failed", exc,
                path=getattr(parsed, "path", ""),
            )

    drop = file_drop_zone(
        theme,
        log_area="ai_bug_report.upload",
        title=txt["drop_title"],
        hint=txt["drop_hint"],
        extensions=_ATTACHMENT_EXTENSIONS,
        unsupported_message=txt["unsupported"],
        on_file_resolved=_on_drop,
        height=140,
        paste_path_label=txt["upload_paste_path_btn"],
        paste_path_tooltip=txt["upload_paste_path_tooltip"],
        cta_label=txt["upload_cta_label"],
    )
    attachments_layout.addWidget(drop)
    attachments_layout.addWidget(
        BodyLabel(
            txt["attachments_label"],
            theme=theme,
            size=12,
            weight=QFont.Weight.DemiBold,
        )
    )
    attachments_layout.addWidget(chips_holder)
    _render_chips()

    attachments_card = _step_card(
        theme,
        label="STEP 2" if txt["step_input_label"] == "STEP 1" else "KROK 2",
        title=txt["attachments_label"],
        desc=txt["drop_hint"],
        body=attachments_holder,
    )

    holder_layout.addWidget(desc_card)
    holder_layout.addWidget(attachments_card)
    return holder


# ---------------------------------------------------------------------------
# Preview tab.
# ---------------------------------------------------------------------------


def _preview_section(
    theme: Theme,
    *,
    title: str,
    body: QWidget,
) -> QFrame:
    frame = QFrame()
    frame.setStyleSheet(
        f"background-color: {theme.surface}; border: 1px solid {theme.border}; border-radius: 12px;"
    )
    layout = vbox(spacing=4, margins=(14, 14, 14, 14))
    frame.setLayout(layout)

    layout.addWidget(custom_label(title, color=theme.primary, size=11, weight=700))
    layout.addSpacing(2)
    layout.addWidget(body)
    return frame


def _bullet_list(theme: Theme, items: list[str], numbered: bool = False) -> QWidget:
    if not items:
        return MutedLabel("-", theme=theme, size=12)
    holder = QWidget()
    holder.setStyleSheet("background: transparent;")
    holder_layout = vbox(spacing=6, margins=(0, 0, 0, 0))
    holder.setLayout(holder_layout)
    for idx, item in enumerate(items, start=1):
        row = QFrame()
        row.setStyleSheet("background: transparent;")
        row_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
        row_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        row.setLayout(row_layout)
        if numbered:
            row_layout.addWidget(
                custom_label(
                    f"{idx}.",
                    color=theme.primary,
                    size=12,
                    weight=700,
                )
            )
        else:
            dot = QFrame()
            dot.setFixedSize(6, 6)
            dot.setStyleSheet(
                f"background-color: {theme.primary}; border-radius: 3px;"
            )
            dot_holder = QFrame()
            dot_holder.setStyleSheet("background: transparent;")
            dh_layout = vbox(spacing=0, margins=(0, 6, 0, 0))
            dot_holder.setLayout(dh_layout)
            dh_layout.addWidget(dot)
            row_layout.addWidget(dot_holder)
        text = BodyLabel(item, theme=theme, size=12, selectable=True)
        text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row_layout.addWidget(text, 1)
        holder_layout.addWidget(row)
    return holder


def _env_block(theme: Theme, txt: dict, env: dict) -> QWidget:
    rows: list[tuple[str, str]] = []
    for key, label_key in (
        ("browser", "env_browser"),
        ("os", "env_os"),
        ("device", "env_device"),
        ("app_version", "env_app_version"),
        ("url", "env_url"),
    ):
        value = (env.get(key) or "").strip()
        if value:
            rows.append((txt[label_key], value))
    if not rows:
        return MutedLabel("-", theme=theme, size=12)
    holder = QWidget()
    holder.setStyleSheet("background: transparent;")
    holder_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    holder.setLayout(holder_layout)
    for name, value in rows:
        row = QFrame()
        row.setStyleSheet("background: transparent;")
        row_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
        row_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        row.setLayout(row_layout)
        row_layout.addWidget(
            custom_label(name, color=theme.text_muted, size=12, weight=600)
        )
        body = BodyLabel(value, theme=theme, size=12, selectable=True)
        body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row_layout.addWidget(body, 1)
        holder_layout.addWidget(row)
    return holder


def _build_preview_tab(
    theme: Theme,
    txt: dict,
    *,
    on_state_change: Callable[[], None],
    on_navigate_tab: Callable[[int], None],
    on_regenerate: Callable[[], None],
) -> QWidget:
    if not STATE.last_report:
        holder = QWidget()
        holder.setStyleSheet("background: transparent;")
        layout = vbox(spacing=10, margins=(24, 24, 24, 24))
        holder.setLayout(layout)
        if STATE.last_error:
            layout.addWidget(IconLabel(Icons.ERROR_OUTLINE, color="#EF4444", size=24))
            layout.addWidget(
                custom_label(
                    STATE.last_error,
                    color="#EF4444",
                    size=13,
                    weight=QFont.Weight.DemiBold,
                    selectable=True,
                )
            )
        else:
            layout.addWidget(MutedLabel(txt["preview_empty"], theme=theme, size=13))
        back = GhostButton(txt["preview_back_btn"], theme=theme, icon=Icons.ARROW_BACK)
        back.clicked.connect(lambda: on_navigate_tab(TAB_INPUT))
        layout.addWidget(back)
        layout.addStretch(1)
        return holder

    report = STATE.last_report

    inner = QWidget()
    inner.setStyleSheet(f"background-color: {theme.bg};")
    inner_layout = vbox(spacing=12, margins=(24, 18, 24, 18))
    inner.setLayout(inner_layout)

    title_holder = QFrame()
    title_holder.setStyleSheet("background: transparent;")
    title_layout = vbox(spacing=6, margins=(0, 0, 0, 0))
    title_holder.setLayout(title_layout)
    title_layout.addWidget(
        custom_label(
            txt["preview_title_label"], color=theme.primary, size=11, weight=700
        )
    )
    title_edit = themed_line_edit(theme, placeholder=txt["preview_title_label"])
    title_edit.setText(report.get("title", ""))
    title_edit.textChanged.connect(
        lambda value: (report.__setitem__("title", value), on_state_change())
    )
    title_layout.addWidget(title_edit)
    inner_layout.addWidget(title_holder)

    meta_row = QFrame()
    meta_row.setStyleSheet("background: transparent;")
    meta_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    meta_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    meta_row.setLayout(meta_layout)

    def _add_combo(
        label_text: str, values: tuple, current: str, key: str
    ) -> None:
        cell = QFrame()
        cell.setStyleSheet("background: transparent;")
        cell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        cell_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
        cell.setLayout(cell_layout)
        cell_layout.addWidget(
            custom_label(label_text, color=theme.primary, size=11, weight=700)
        )
        combo = QComboBox()
        for value in values:
            combo.addItem(value)
        if current in values:
            combo.setCurrentText(current)
        combo.setStyleSheet(
            f"""
            QComboBox {{
                background-color: {theme.surface_2};
                color: {theme.text};
                border: 1px solid {theme.border};
                border-radius: 8px;
                padding: 8px 10px;
            }}
            """
        )
        combo.currentTextChanged.connect(
            lambda value, k=key: (report.__setitem__(k, value), on_state_change())
        )
        cell_layout.addWidget(combo)
        meta_layout.addWidget(cell, 1)

    _add_combo(
        txt["preview_severity_label"],
        SEVERITY_VALUES,
        report.get("severity", ""),
        "severity",
    )
    _add_combo(
        txt["preview_priority_label"],
        PRIORITY_VALUES,
        report.get("priority", ""),
        "priority",
    )
    _add_combo(
        txt["preview_repro_label"],
        REPRODUCIBILITY_VALUES,
        report.get("reproducibility", ""),
        "reproducibility",
    )
    inner_layout.addWidget(meta_row)

    if report.get("summary"):
        inner_layout.addWidget(
            _preview_section(
                theme,
                title=txt["preview_summary_label"],
                body=BodyLabel(
                    report["summary"], theme=theme, size=13, selectable=True
                ),
            )
        )

    inner_layout.addWidget(
        _preview_section(
            theme,
            title=txt["preview_environment_label"],
            body=_env_block(theme, txt, report.get("environment") or {}),
        )
    )

    if report.get("preconditions"):
        inner_layout.addWidget(
            _preview_section(
                theme,
                title=txt["preview_preconditions_label"],
                body=_bullet_list(theme, list(report["preconditions"])),
            )
        )

    inner_layout.addWidget(
        _preview_section(
            theme,
            title=txt["preview_str_label"],
            body=_bullet_list(
                theme,
                list(report.get("steps_to_reproduce") or []),
                numbered=True,
            ),
        )
    )

    inner_layout.addWidget(
        _preview_section(
            theme,
            title=txt["preview_expected_label"],
            body=BodyLabel(
                report.get("expected_result") or "-",
                theme=theme,
                size=13,
                selectable=True,
            ),
        )
    )

    inner_layout.addWidget(
        _preview_section(
            theme,
            title=txt["preview_actual_label"],
            body=BodyLabel(
                report.get("actual_result") or "-",
                theme=theme,
                size=13,
                selectable=True,
            ),
        )
    )

    if report.get("attachments_summary"):
        inner_layout.addWidget(
            _preview_section(
                theme,
                title=txt["preview_attachments_label"],
                body=_bullet_list(theme, list(report["attachments_summary"])),
            )
        )

    if report.get("additional_notes"):
        inner_layout.addWidget(
            _preview_section(
                theme,
                title=txt["preview_notes_label"],
                body=BodyLabel(
                    report["additional_notes"],
                    theme=theme,
                    size=13,
                    selectable=True,
                ),
            )
        )

    actions_row = QFrame()
    actions_row.setStyleSheet("background: transparent;")
    actions_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    actions_row.setLayout(actions_layout)
    back = GhostButton(txt["preview_back_btn"], theme=theme, icon=Icons.ARROW_BACK)
    back.clicked.connect(lambda: on_navigate_tab(TAB_INPUT))
    actions_layout.addWidget(back)
    regen = GhostButton(txt["preview_regen_btn"], theme=theme, icon=Icons.REFRESH)
    regen.clicked.connect(lambda: on_regenerate())
    actions_layout.addWidget(regen)
    actions_layout.addStretch(1)
    inner_layout.addWidget(actions_row)
    inner_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(
        f"QScrollArea {{ background-color: {theme.bg}; border: none; }}"
    )
    scroll.setWidget(inner)
    return scroll


# ---------------------------------------------------------------------------
# Export tab.
# ---------------------------------------------------------------------------


def _build_export_tab(
    theme: Theme,
    txt: dict,
    lang: str,
    *,
    on_state_change: Callable[[], None],
    on_navigate_tab: Callable[[int], None],
) -> QWidget:
    holder = QWidget()
    holder.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=12, margins=(24, 18, 24, 18))
    holder.setLayout(layout)

    status_label = MutedLabel("", theme=theme, size=12, selectable=True)

    def _set_status(msg: str, *, error: bool = False) -> None:
        status_label.setText(msg)
        status_label.setStyleSheet(
            f"color: {'#EF4444' if error else theme.text_muted}; background: transparent;"
        )

    card_body = QWidget()
    card_body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    card_body.setLayout(body_layout)
    body_layout.addWidget(MutedLabel(txt["export_desc"], theme=theme, size=12))

    save_btn = PrimaryButton(
        txt["export_save_btn"], theme=theme, icon=Icons.SAVE_OUTLINED
    )
    folder_btn = GhostButton(
        txt["export_open_folder_btn"], theme=theme, icon=Icons.FOLDER_OPEN
    )

    actions = QFrame()
    actions.setStyleSheet("background: transparent;")
    actions_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    actions.setLayout(actions_layout)
    actions_layout.addWidget(save_btn)
    actions_layout.addWidget(folder_btn)
    actions_layout.addStretch(1)
    body_layout.addWidget(actions)
    body_layout.addWidget(status_label)

    if not STATE.last_report:
        _set_status(txt["export_run_first"], error=False)
        save_btn.setEnabled(False)
    elif STATE.last_save_path:
        _set_status(txt["export_saved_template"].format(path=STATE.last_save_path))

    def _on_save() -> None:
        if not STATE.last_report:
            _set_status(txt["export_run_first"], error=True)
            return
        try:
            result = pipeline.save_bug_report_docx(labels=s(lang))
        except Exception as exc:
            logger_service.log_exception(
                "ai_bug_report.view", "save_bug_report_failed", exc,
            )
            _set_status(
                txt["export_save_failed"].format(error=str(exc)), error=True
            )
            return
        if not result.ok:
            _set_status(
                txt["export_save_failed"].format(error=result.error or "?"),
                error=True,
            )
            return
        _set_status(
            txt["export_saved_template"].format(path=result.path)
        )
        on_state_change()

    def _on_open_folder() -> None:
        section_root = str(store.section_runs_dir("ai_bug_report"))
        target = (
            STATE.last_run_folder
            or (section_root if os.path.isdir(section_root) else str(store.runs_dir()))
        )
        try:
            os.makedirs(target, exist_ok=True)
        except OSError as exc:
            logger_service.log_exception(
                "ai_bug_report.view", "open_folder_mkdir_failed", exc, target=target,
            )
            return
        try:
            if os.name == "nt":
                os.startfile(target)  # noqa: S606 - intentional, opens Explorer
            else:
                import subprocess

                opener = "open" if os.uname().sysname == "Darwin" else "xdg-open"
                subprocess.Popen([opener, target])  # noqa: S603 - trusted path
        except Exception as exc:
            logger_service.log_exception(
                "ai_bug_report.view", "open_folder_failed", exc, target=target,
            )

    save_btn.clicked.connect(_on_save)
    folder_btn.clicked.connect(_on_open_folder)

    export_card = _step_card(
        theme,
        label=txt["tab_export"].upper(),
        title=txt["export_title"],
        desc="",
        body=card_body,
    )
    layout.addWidget(export_card)

    back = GhostButton(txt["preview_back_btn"], theme=theme, icon=Icons.ARROW_BACK)
    back.clicked.connect(lambda: on_navigate_tab(TAB_INPUT))
    back_holder = QFrame()
    back_holder.setStyleSheet("background: transparent;")
    back_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    back_holder.setLayout(back_layout)
    back_layout.addWidget(back)
    back_layout.addStretch(1)
    layout.addWidget(back_holder)
    layout.addStretch(1)

    return holder


# ---------------------------------------------------------------------------
# Footer (Generate + Demo buttons).
# ---------------------------------------------------------------------------


def _build_footer(
    theme: Theme,
    lang: str,
    txt: dict,
    *,
    on_state_change: Callable[[], None],
    on_navigate_tab: Callable[[int], None],
) -> tuple[QWidget, Callable[[], None]]:
    container = QFrame()
    container.setStyleSheet(
        f"background-color: {theme.bg}; border-top: 1px solid {theme.border};"
    )
    layout = hbox(spacing=10, margins=(24, 12, 24, 12))
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    container.setLayout(layout)

    demo_btn = GhostButton(txt["footer_demo_btn"], theme=theme, icon=Icons.AUTO_AWESOME)
    layout.addWidget(demo_btn)
    layout.addStretch(1)

    status_label = MutedLabel("", theme=theme, size=11)
    layout.addWidget(status_label)

    run_holder = QWidget()
    run_holder.setStyleSheet("background: transparent;")
    run_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    run_holder.setLayout(run_layout)
    layout.addWidget(run_holder)

    state_box: dict[str, str] = {"stage": ""}

    def _set_status(msg: str, *, error: bool = False) -> None:
        status_label.setText(msg)
        status_label.setStyleSheet(
            f"color: {'#EF4444' if error else theme.text_muted}; background: transparent;"
        )

    def _render_run_button() -> None:
        _clear_layout(run_layout)
        running = bool(state_box["stage"])
        enabled = STATE.can_generate() and not running
        label = (
            txt["footer_generate_running"]
            if running
            else txt["footer_generate_btn"]
        )
        button = PrimaryButton(
            label, theme=theme, icon=Icons.PLAY_ARROW_ROUNDED
        )
        button.setEnabled(enabled)
        button.clicked.connect(_on_generate)
        run_layout.addWidget(button)

    def _refresh() -> None:
        _render_run_button()

    def _on_demo() -> None:
        STATE.demo_mode = True
        pipeline.load_demo()
        on_state_change()
        on_navigate_tab(TAB_PREVIEW)

    def _on_generate() -> None:
        if not STATE.can_generate():
            _set_status(txt["generate_disabled_hint"], error=True)
            return
        if not STATE.demo_mode:
            provider = settings_store.get_provider()
            key_name = (
                secrets.ANTHROPIC_API_KEY
                if provider == settings_store.PROVIDER_ANTHROPIC
                else secrets.OPENAI_API_KEY
            )
            if not secrets.has_secret(key_name):
                _set_status(
                    txt["no_key_template"].format(provider=provider), error=True
                )
                return

        _set_status("")
        state_box["stage"] = "running"
        _render_run_button()

        def _worker() -> None:
            try:
                result = pipeline.generate_bug_report(output_lang=lang)
            except Exception as exc:
                logger_service.log_exception(
                    "ai_bug_report.view", "generate_worker_failed", exc,
                )
                STATE.last_error = str(exc)
                state_box["stage"] = ""
                dispatch(
                    lambda: (
                        _set_status(str(exc), error=True),
                        _render_run_button(),
                    )
                )
                return
            state_box["stage"] = ""
            if not result.ok:
                dispatch(
                    lambda: (
                        _set_status(
                            result.error or "Run failed.", error=True
                        ),
                        _render_run_button(),
                    )
                )
                return
            dispatch(
                lambda: (
                    _render_run_button(),
                    on_navigate_tab(TAB_PREVIEW),
                )
            )

        threading.Thread(target=_worker, daemon=True).start()

    demo_btn.clicked.connect(_on_demo)
    _render_run_button()
    return container, _refresh


# ---------------------------------------------------------------------------
# Top-level view.
# ---------------------------------------------------------------------------


def build_view(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    demo_pill: Optional[QWidget] = None
    if STATE.demo_mode:
        demo_pill = Pill(text=txt["demo_pill"], bg="#F59E0B", fg="#FFFFFF")

    header_widget = header(
        theme,
        lang,
        icon=Icons.WARNING_AMBER_OUTLINED,
        title=txt["title"],
        subtitle=txt["subtitle"],
        on_help_click=lambda: open_bug_report_how_to(container, theme, lang),
        trailing=demo_pill,
    )
    layout.addWidget(header_widget)

    tab_holder = QWidget()
    tab_holder.setStyleSheet(f"background-color: {theme.bg};")
    tab_layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    tab_holder.setLayout(tab_layout)
    layout.addWidget(tab_holder)

    body_holder = QWidget()
    body_holder.setStyleSheet(f"background-color: {theme.bg};")
    body_stack = QStackedLayout(body_holder)
    body_stack.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(body_holder, 1)

    footer_holder = QWidget()
    footer_layout: QVBoxLayout = vbox(spacing=0, margins=(0, 0, 0, 0))
    footer_holder.setLayout(footer_layout)
    layout.addWidget(footer_holder)

    state_box: dict[str, Optional[Callable[[], None]]] = {"refresh_footer": None}

    def _on_state_change() -> None:
        fn = state_box.get("refresh_footer")
        if fn is not None:
            fn()
        REFS.request_context_refresh()

    def _on_navigate_tab(index: int) -> None:
        if index == STATE.active_tab:
            return
        logger_service.log_event(
            "INFO",
            "ai_bug_report.view",
            "tab_change",
            prev_tab=STATE.active_tab,
            new_tab=index,
        )
        STATE.active_tab = index
        try:
            _refresh_tabs()
            _refresh_body()
        except Exception as exc:
            logger_service.log_exception(
                "ai_bug_report.view", "tab_change_failed", exc,
            )

    def _on_regenerate() -> None:
        STATE.reset_result()
        _on_navigate_tab(TAB_INPUT)

    def _refresh_tabs() -> None:
        _clear_widget(tab_holder)
        try:
            tab_widget = tab_bar(
                theme,
                tabs=[txt["tab_input"], txt["tab_preview"], txt["tab_export"]],
                active_index=STATE.active_tab,
                on_change=_on_navigate_tab,
            )
            tab_layout.addWidget(tab_widget)
        except Exception as exc:
            logger_service.log_exception(
                "ai_bug_report.view", "refresh_tabs_build_failed", exc,
            )

    def _refresh_body() -> None:
        while body_stack.count():
            w = body_stack.widget(0)
            body_stack.removeWidget(w)
            w.deleteLater()
        try:
            if STATE.active_tab == TAB_INPUT:
                widget = _build_input_tab(theme, txt, on_state_change=_on_state_change)
                wrapper = QWidget()
                wrapper.setStyleSheet(f"background-color: {theme.bg};")
                w_layout = vbox(spacing=14, margins=(24, 18, 24, 18))
                wrapper.setLayout(w_layout)
                w_layout.addWidget(widget)
                w_layout.addStretch(1)
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                scroll.setFrameShape(QFrame.Shape.NoFrame)
                scroll.setStyleSheet(
                    f"QScrollArea {{ background-color: {theme.bg}; border: none; }}"
                )
                scroll.setWidget(wrapper)
                body_stack.addWidget(scroll)
            elif STATE.active_tab == TAB_PREVIEW:
                body_stack.addWidget(
                    _build_preview_tab(
                        theme,
                        txt,
                        on_state_change=_on_state_change,
                        on_navigate_tab=_on_navigate_tab,
                        on_regenerate=_on_regenerate,
                    )
                )
            else:
                body_stack.addWidget(
                    _build_export_tab(
                        theme,
                        txt,
                        lang,
                        on_state_change=_on_state_change,
                        on_navigate_tab=_on_navigate_tab,
                    )
                )
        except Exception as exc:
            logger_service.log_exception(
                "ai_bug_report.view", "refresh_tab_body_build_failed", exc,
                active_tab=STATE.active_tab,
            )

    def _refresh_footer() -> None:
        _clear_widget(footer_holder)
        try:
            widget, refresh_fn = _build_footer(
                theme,
                lang,
                txt,
                on_state_change=_on_state_change,
                on_navigate_tab=_on_navigate_tab,
            )
            footer_layout.addWidget(widget)
            state_box["refresh_footer"] = refresh_fn
        except Exception as exc:
            logger_service.log_exception(
                "ai_bug_report.view", "refresh_footer_build_failed", exc,
            )
            state_box["refresh_footer"] = None

    REFS.rerender_main = lambda: (_refresh_tabs(), _refresh_body(), _refresh_footer())

    _refresh_tabs()
    _refresh_body()
    _refresh_footer()
    return container
