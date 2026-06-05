"""AI Doc Assistant - center column view (PySide6 port).

Header (with the help dialog button) + 3 tabs:

* **Upload** - drop a PDF / DOCX / TXT / MD / HTML and see a preview.
* **Analyze** - pick an action (summary / Q&A / rewrite / extract) +
  the per-action inputs, then click Run. The pipeline call lives on a
  background thread so the UI stays responsive.
* **Output** - render the structured result of the last action.

State that must survive theme / language / tab toggles lives in
:mod:`src.sections.ai_doc_assistant.state`.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from src.components.header import HeaderMenuItem, header
from src.components.tab_bar import tab_bar
from src.qt.icons import Icons
from src.qt.runtime import dispatch
from src.qt.theme import rgba
from src.qt.widgets import (
    AccentLabel,
    BodyLabel,
    ClickFrame,
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
from src.services import secrets, settings_store
from src.services.file_parser import ParsedFile, human_size
from src.sections.ai_cv.upload import upload_zone
from src.sections.ai_doc_assistant import pipeline
from src.sections.ai_doc_assistant.how_to import open_doc_assistant_how_to
from src.sections.ai_doc_assistant.state import (
    ACTION_EXTRACT,
    ACTION_QA,
    ACTION_REWRITE,
    ACTION_SUMMARY,
    ACTIONS,
    STATE,
    TAB_ANALYZE,
    TAB_OUTPUT,
    TAB_UPLOAD,
    UploadedDoc,
)
from src.sections.ai_doc_assistant.strings import s
from src.theme import Theme


_DOC_EXTENSIONS = ("pdf", "docx", "txt", "md", "html", "htm")
_PREVIEW_CHARS = 800


def _step_card(theme: Theme, *, label: str, title: str, desc: str, body: QWidget) -> QFrame:
    card = QFrame()
    card.setObjectName("DocAssistantStepCard")
    card.setStyleSheet(
        f"""
        QFrame#DocAssistantStepCard {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 14px;
        }}
        """
    )
    layout = vbox(spacing=4, margins=(18, 18, 18, 18))
    card.setLayout(layout)

    step_label = QLabel(label)
    step_label_font = QFont()
    step_label_font.setPixelSize(11)
    step_label_font.setWeight(QFont.Weight.Bold)
    step_label_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.4)
    step_label.setFont(step_label_font)
    step_label.setStyleSheet(f"color: {theme.primary}; background: transparent;")
    layout.addWidget(step_label)
    layout.addWidget(TitleLabel(title, theme=theme, size=15, weight=QFont.Weight.Bold))
    layout.addWidget(MutedLabel(desc, theme=theme, size=12))
    layout.addSpacing(8)
    layout.addWidget(body)
    return card


def _file_chip(theme: Theme, txt: dict, doc: UploadedDoc, on_clear: Callable[[], None]) -> QFrame:
    chip = QFrame()
    chip.setObjectName("DocAssistantFileChip")
    chip.setStyleSheet(
        f"""
        QFrame#DocAssistantFileChip {{
            background-color: {theme.surface_2};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        """
    )
    layout = hbox(spacing=10, margins=(12, 10, 12, 10))
    chip.setLayout(layout)

    badge = QFrame()
    badge.setFixedSize(32, 32)
    badge.setStyleSheet(
        f"background-color: {rgba(theme.primary, 0.14)}; border-radius: 8px;"
    )
    bl = hbox(spacing=0, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setLayout(bl)
    bl.addWidget(IconLabel(Icons.DESCRIPTION_OUTLINED, color=theme.primary, size=18),
                 alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(badge)

    info = QFrame()
    info.setStyleSheet("background: transparent;")
    info_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    info.setLayout(info_layout)
    info_layout.addWidget(BodyLabel(doc.name, theme=theme, size=13, weight=QFont.Weight.DemiBold))
    info_layout.addWidget(MutedLabel(f"{doc.ext.upper()} \u00b7 {human_size(doc.size_bytes)}", theme=theme, size=11))
    layout.addWidget(info, 1)

    close_btn = IconOnlyButton(
        Icons.CLOSE,
        color=theme.text_muted,
        size=16,
        bg_hover=theme.surface,
        tooltip=txt["clear_btn"],
    )
    close_btn.clicked.connect(lambda: on_clear())
    layout.addWidget(close_btn)

    return chip


def _preview_block(theme: Theme, txt: dict, doc: UploadedDoc) -> QWidget:
    preview = (doc.text or "")[:_PREVIEW_CHARS]
    if len(doc.text or "") > _PREVIEW_CHARS:
        preview += "\n\n..."

    holder = QWidget()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=8, margins=(0, 8, 0, 0))
    holder.setLayout(layout)

    label = QLabel(txt["preview_label"])
    label_font = QFont()
    label_font.setPixelSize(11)
    label_font.setWeight(QFont.Weight.DemiBold)
    label_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.6)
    label.setFont(label_font)
    label.setStyleSheet(f"color: {theme.text_subtle}; background: transparent;")
    layout.addWidget(label)

    body = QFrame()
    body.setStyleSheet(
        f"background-color: {theme.surface_2}; border: 1px solid {theme.border}; border-radius: 10px;"
    )
    body_layout = vbox(spacing=0, margins=(12, 10, 12, 10))
    body.setLayout(body_layout)
    text = MutedLabel(preview or "(empty)", theme=theme, size=12)
    text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    body_layout.addWidget(text)
    layout.addWidget(body)
    return holder


def _build_upload_tab(
    theme: Theme,
    txt: dict,
    on_state_change: Callable[[], None],
) -> QWidget:
    holder = QWidget()
    holder.setStyleSheet("background: transparent;")
    holder_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    holder.setLayout(holder_layout)

    def _clear_layout() -> None:
        while holder_layout.count():
            item = holder_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _render() -> None:
        _clear_layout()
        if STATE.document:
            holder_layout.addWidget(_file_chip(theme, txt, STATE.document, _clear_doc))
            holder_layout.addWidget(_preview_block(theme, txt, STATE.document))
        else:
            empty = QFrame()
            empty.setStyleSheet("background: transparent;")
            empty_layout = vbox(spacing=0, margins=(4, 8, 4, 8))
            empty.setLayout(empty_layout)
            empty_layout.addWidget(MutedLabel(txt["no_file"], theme=theme, size=12))
            holder_layout.addWidget(empty)

    def _clear_doc() -> None:
        STATE.document = None
        STATE.reset_result()
        _render()
        on_state_change()

    def _on_doc(parsed: ParsedFile) -> None:
        STATE.document = UploadedDoc(
            path=parsed.path,
            name=parsed.name,
            ext=parsed.ext,
            size_bytes=parsed.size_bytes,
            text=parsed.text,
        )
        STATE.reset_result()
        _render()
        on_state_change()

    _render()

    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    body_layout.addWidget(
        upload_zone(
            theme,
            title=txt["drop_title"],
            hint=txt["drop_hint"],
            extensions=_DOC_EXTENSIONS,
            unsupported_message=txt["unsupported"],
            on_file_resolved=_on_doc,
            paste_path_label=txt["upload_paste_path_btn"],
            paste_path_tooltip=txt["upload_paste_path_tooltip"],
            cta_label=txt["upload_cta_label"],
        )
    )
    body_layout.addWidget(holder)

    return _step_card(
        theme,
        label=txt["step_1_label"],
        title=txt["step_1_title"],
        desc=txt["step_1_desc"],
        body=body,
    )


def _action_radio(
    theme: Theme,
    *,
    title: str,
    desc: str,
    selected: bool,
    on_click: Callable[[], None],
) -> ClickFrame:
    border_color = theme.primary if selected else theme.border
    chip = ClickFrame()
    chip.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {theme.surface_2};
            border: 1px solid {border_color};
            border-radius: 12px;
        }}
        ClickFrame:hover {{
            border: 1px solid {theme.primary};
        }}
        """
    )
    layout = hbox(spacing=12, margins=(12, 12, 12, 12))
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    chip.setLayout(layout)

    indicator = QFrame()
    indicator.setFixedSize(18, 18)
    if selected:
        indicator.setStyleSheet(
            f"background-color: {theme.primary}; border: 2px solid {theme.primary}; border-radius: 9px;"
        )
        ind_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
        ind_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        indicator.setLayout(ind_layout)
        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet("background-color: #FFFFFF; border-radius: 4px;")
        ind_layout.addWidget(dot, alignment=Qt.AlignmentFlag.AlignCenter)
    else:
        indicator.setStyleSheet(
            f"background-color: transparent; border: 2px solid {theme.border}; border-radius: 9px;"
        )
    layout.addWidget(indicator)

    info = QFrame()
    info.setStyleSheet("background: transparent;")
    info_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    info.setLayout(info_layout)
    info_layout.addWidget(BodyLabel(title, theme=theme, size=13, weight=QFont.Weight.DemiBold))
    info_layout.addWidget(MutedLabel(desc, theme=theme, size=11))
    layout.addWidget(info, 1)

    chip.clicked.connect(on_click)
    return chip


def _build_analyze_tab(
    theme: Theme,
    txt: dict,
    on_state_change: Callable[[], None],
) -> QWidget:
    actions_holder = QWidget()
    actions_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    actions_holder.setLayout(actions_layout)

    inputs_holder = QWidget()
    inputs_layout = vbox(spacing=6, margins=(0, 0, 0, 0))
    inputs_holder.setLayout(inputs_layout)

    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _render_actions() -> None:
        _clear_layout(actions_layout)
        labels = {
            ACTION_SUMMARY: (txt["action_summary"], txt["action_summary_desc"]),
            ACTION_QA: (txt["action_qa"], txt["action_qa_desc"]),
            ACTION_REWRITE: (txt["action_rewrite"], txt["action_rewrite_desc"]),
            ACTION_EXTRACT: (txt["action_extract"], txt["action_extract_desc"]),
        }
        for key in ACTIONS:
            title, desc = labels[key]
            actions_layout.addWidget(
                _action_radio(
                    theme,
                    title=title,
                    desc=desc,
                    selected=STATE.action == key,
                    on_click=lambda k=key: _set_action(k),
                )
            )

    def _render_inputs() -> None:
        _clear_layout(inputs_layout)
        if STATE.action == ACTION_QA:
            label = BodyLabel(txt["qa_question_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold)
            edit = themed_line_edit(theme, placeholder=txt["qa_question_hint"])
            edit.setText(STATE.qa_question)
            edit.textChanged.connect(_set_question)
            inputs_layout.addWidget(label)
            inputs_layout.addWidget(edit)
        elif STATE.action == ACTION_REWRITE:
            inputs_layout.addWidget(BodyLabel(txt["rewrite_passage_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold))
            passage_edit = themed_text_edit(theme, placeholder=txt["rewrite_passage_hint"], min_height=110)
            passage_edit.setPlainText(STATE.rewrite_passage)
            passage_edit.textChanged.connect(lambda: _set_passage(passage_edit.toPlainText()))
            inputs_layout.addWidget(passage_edit)
            inputs_layout.addSpacing(6)
            inputs_layout.addWidget(BodyLabel(txt["rewrite_tone_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold))
            tone_edit = themed_line_edit(theme, placeholder=txt["rewrite_tone_options"])
            tone_edit.setText(STATE.rewrite_tone)
            tone_edit.textChanged.connect(_set_tone)
            inputs_layout.addWidget(tone_edit)

    def _set_action(key: str) -> None:
        STATE.action = key
        _render_actions()
        _render_inputs()
        on_state_change()

    def _set_question(value: str) -> None:
        STATE.qa_question = value
        on_state_change()

    def _set_passage(value: str) -> None:
        STATE.rewrite_passage = value
        on_state_change()

    def _set_tone(value: str) -> None:
        STATE.rewrite_tone = value
        on_state_change()

    _render_actions()
    _render_inputs()

    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)
    body_layout.addWidget(actions_holder)
    body_layout.addSpacing(4)
    body_layout.addWidget(inputs_holder)

    return _step_card(
        theme,
        label=txt["step_2_label"],
        title=txt["step_2_title"],
        desc=txt["step_2_desc"],
        body=body,
    )


def _result_section(theme: Theme, *, title: str, body: QWidget) -> QFrame:
    frame = QFrame()
    frame.setStyleSheet(
        f"background-color: {theme.surface}; border: 1px solid {theme.border}; border-radius: 12px;"
    )
    layout = vbox(spacing=2, margins=(14, 14, 14, 14))
    frame.setLayout(layout)

    label = QLabel(title)
    label_font = QFont()
    label_font.setPixelSize(11)
    label_font.setWeight(QFont.Weight.Bold)
    label_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
    label.setFont(label_font)
    label.setStyleSheet(f"color: {theme.primary}; background: transparent;")
    layout.addWidget(label)
    layout.addSpacing(4)
    layout.addWidget(body)
    return frame


def _bullet_list(theme: Theme, items: list[str]) -> QWidget:
    if not items:
        return MutedLabel("-", theme=theme, size=12)

    holder = QWidget()
    holder.setStyleSheet("background: transparent;")
    holder_layout = vbox(spacing=6, margins=(0, 0, 0, 0))
    holder.setLayout(holder_layout)
    for item in items:
        row = QFrame()
        row.setStyleSheet("background: transparent;")
        row_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
        row_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        row.setLayout(row_layout)
        dot = QFrame()
        dot.setFixedSize(6, 6)
        dot.setStyleSheet(f"background-color: {theme.primary}; border-radius: 3px;")
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


def _build_output_tab(
    theme: Theme,
    txt: dict,
    on_navigate_tab: Callable[[int], None],
) -> QWidget:
    if STATE.last_error:
        holder = QWidget()
        holder.setStyleSheet("background: transparent;")
        layout = vbox(spacing=8, margins=(24, 24, 24, 24))
        holder.setLayout(layout)
        layout.addWidget(IconLabel(Icons.ERROR_OUTLINE, color="#EF4444", size=24))
        err_label = custom_label(STATE.last_error, color="#EF4444", size=13, weight=QFont.Weight.DemiBold, selectable=True)
        layout.addWidget(err_label)
        layout.addSpacing(6)
        back = GhostButton(txt["output_back_btn"], theme=theme, icon=Icons.ARROW_BACK)
        back.clicked.connect(lambda: on_navigate_tab(TAB_ANALYZE))
        layout.addWidget(back)
        layout.addStretch(1)
        return holder

    if not STATE.last_result:
        holder = QWidget()
        holder.setStyleSheet("background: transparent;")
        layout = vbox(spacing=8, margins=(24, 24, 24, 24))
        holder.setLayout(layout)
        layout.addWidget(MutedLabel(txt["output_empty"], theme=theme, size=13))
        layout.addSpacing(6)
        back = GhostButton(txt["output_back_btn"], theme=theme, icon=Icons.ARROW_BACK)
        back.clicked.connect(lambda: on_navigate_tab(TAB_ANALYZE))
        layout.addWidget(back)
        layout.addStretch(1)
        return holder

    data = STATE.last_result
    action = STATE.last_action

    inner = QWidget()
    inner.setStyleSheet(f"background-color: {theme.bg};")
    inner_layout = vbox(spacing=10, margins=(24, 18, 24, 18))
    inner.setLayout(inner_layout)

    if action == ACTION_SUMMARY:
        inner_layout.addWidget(_result_section(theme, title=txt["output_summary_title"],
                                               body=BodyLabel(data.get("tldr") or "-", theme=theme, size=13, selectable=True)))
        inner_layout.addWidget(_result_section(theme, title=txt["output_bullets_title"],
                                               body=_bullet_list(theme, list(data.get("key_points") or []))))
        inner_layout.addWidget(_result_section(theme, title=txt["output_actions_title"],
                                               body=_bullet_list(theme, list(data.get("action_items") or []))))
    elif action == ACTION_QA:
        confidence = (data.get("confidence") or "").upper()

        ans_body = QWidget()
        ans_body.setStyleSheet("background: transparent;")
        ab_layout = vbox(spacing=6, margins=(0, 0, 0, 0))
        ans_body.setLayout(ab_layout)
        ab_layout.addWidget(Pill(text=confidence or "-", bg=theme.primary, fg="#FFFFFF"))
        ab_layout.addWidget(BodyLabel(data.get("answer") or "-", theme=theme, size=13, selectable=True))
        inner_layout.addWidget(_result_section(theme, title=txt["output_answer_title"], body=ans_body))
        inner_layout.addWidget(_result_section(theme, title=txt["output_evidence_title"],
                                               body=_bullet_list(theme, list(data.get("evidence") or []))))
    elif action == ACTION_REWRITE:
        inner_layout.addWidget(_result_section(theme, title=txt["output_rewrite_title"],
                                               body=BodyLabel(data.get("rewritten") or "-", theme=theme, size=13, selectable=True)))
        inner_layout.addWidget(_result_section(theme, title=txt["output_actions_title"],
                                               body=_bullet_list(theme, list(data.get("changes") or []))))
    elif action == ACTION_EXTRACT:
        facts = list(data.get("facts") or [])
        if not facts:
            inner_layout.addWidget(_result_section(theme, title=txt["output_extract_title"],
                                                   body=MutedLabel("-", theme=theme, size=12)))
        else:
            facts_holder = QWidget()
            facts_holder.setStyleSheet("background: transparent;")
            fh_layout = vbox(spacing=6, margins=(0, 0, 0, 0))
            facts_holder.setLayout(fh_layout)
            for fact in facts:
                label = (fact.get("label") or "").strip() or "-"
                value = (fact.get("value") or "").strip() or "-"
                evidence = (fact.get("evidence") or "").strip()
                row = QFrame()
                row.setStyleSheet(
                    f"background-color: {theme.surface_2}; border: 1px solid {theme.border}; border-radius: 10px;"
                )
                row_layout = vbox(spacing=2, margins=(10, 10, 10, 10))
                row.setLayout(row_layout)
                row_layout.addWidget(SubtleLabel(label, theme=theme, size=10))
                row_layout.addWidget(BodyLabel(value, theme=theme, size=13, weight=QFont.Weight.DemiBold, selectable=True))
                if evidence:
                    row_layout.addWidget(SubtleLabel(evidence, theme=theme, size=11, italic=True))
                fh_layout.addWidget(row)
            inner_layout.addWidget(_result_section(theme, title=txt["output_extract_title"], body=facts_holder))

    inner_layout.addSpacing(4)
    back = GhostButton(txt["output_back_btn"], theme=theme, icon=Icons.ARROW_BACK)
    back.clicked.connect(lambda: on_navigate_tab(TAB_ANALYZE))
    back_holder = QFrame()
    back_holder.setStyleSheet("background: transparent;")
    back_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    back_holder.setLayout(back_layout)
    back_layout.addWidget(back)
    back_layout.addStretch(1)
    inner_layout.addWidget(back_holder)
    inner_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(inner)
    return scroll


def _build_footer(
    theme: Theme,
    lang: str,
    txt: dict,
    on_state_change: Callable[[], None],
    on_navigate_tab: Callable[[int], None],
) -> tuple[QWidget, Callable[[], None]]:
    container = QFrame()
    # Scope ``border-top`` to the footer container so it does not paint
    # a thin line across every QFrame child (the QFrame-based Ghost /
    # Primary buttons inside). Without scoping the cascade applies the
    # border to each button too - see image 4 in
    # feat/dashboard-and-ui-fixes for the symptom.
    container.setObjectName("DocAssistantFooter")
    container.setStyleSheet(
        f"""
        QFrame#DocAssistantFooter {{
            background-color: {theme.bg};
            border-top: 1px solid {theme.border};
        }}
        """
    )
    layout = hbox(spacing=10, margins=(24, 12, 24, 12))
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    container.setLayout(layout)

    # The "Try demo data" GhostButton used to live here; demo is now
    # exposed via the header ``...`` menu so every section shares the
    # same affordance (see ``.cursor/rules/ai-section.mdc``).
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
        while run_layout.count():
            item = run_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        running = bool(state_box["stage"])
        enabled = STATE.can_run() and not running
        label = txt["footer_run_running"] if running else txt["footer_run_btn"]
        button = PrimaryButton(label, theme=theme, icon=Icons.PLAY_ARROW_ROUNDED)
        button.setEnabled(enabled)
        button.clicked.connect(_on_run)
        run_layout.addWidget(button)

    def _refresh() -> None:
        _render_run_button()

    def _on_run() -> None:
        if not STATE.can_run():
            _set_status(txt["run_disabled_hint"], error=True)
            return
        if not STATE.demo_mode:
            provider = settings_store.get_provider()
            key_name = (
                secrets.ANTHROPIC_API_KEY
                if provider == settings_store.PROVIDER_ANTHROPIC
                else secrets.OPENAI_API_KEY
            )
            if not secrets.has_secret(key_name):
                _set_status(txt["no_key_template"].format(provider=provider), error=True)
                return

        _set_status("")
        state_box["stage"] = "running"
        _render_run_button()

        def _worker() -> None:
            try:
                result = pipeline.run_action(output_lang=lang)
            except Exception as exc:
                logger_service.log_exception(
                    "ai_doc_assistant.view", "run_action_worker_failed", exc,
                    action=STATE.action,
                )
                STATE.last_error = str(exc)
                state_box["stage"] = ""
                dispatch(lambda: (_set_status(str(exc), error=True), _render_run_button()))
                return
            state_box["stage"] = ""
            if not result.ok:
                dispatch(lambda: (_set_status(result.error or "Run failed.", error=True), _render_run_button()))
                return
            dispatch(lambda: (_render_run_button(), on_navigate_tab(TAB_OUTPUT)))

        threading.Thread(target=_worker, daemon=True).start()

    _render_run_button()
    return container, _refresh


def build_view(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    demo_pill: Optional[QWidget] = None
    if STATE.demo_mode:
        demo_pill = Pill(text=txt["demo_pill"], bg="#F59E0B", fg="#FFFFFF")

    def _menu_load_demo() -> None:
        logger_service.log_event(
            "INFO", "ai_doc_assistant.view", "menu_load_demo"
        )
        STATE.demo_mode = True
        try:
            pipeline.load_demo()
        except Exception as exc:
            logger_service.log_exception(
                "ai_doc_assistant.view", "menu_load_demo_failed", exc,
            )
            return
        STATE.active_tab = TAB_OUTPUT
        try:
            from src.app import request_section_refresh

            request_section_refresh()
        except Exception as exc:
            logger_service.log_exception(
                "ai_doc_assistant.view", "menu_load_demo_refresh_failed", exc,
            )

    def _menu_clear_demo() -> None:
        logger_service.log_event(
            "INFO", "ai_doc_assistant.view", "menu_clear_demo"
        )
        STATE.demo_mode = False
        STATE.last_result = None
        STATE.last_error = ""
        STATE.active_tab = TAB_UPLOAD
        try:
            from src.app import request_section_refresh

            request_section_refresh()
        except Exception as exc:
            logger_service.log_exception(
                "ai_doc_assistant.view", "menu_clear_demo_refresh_failed", exc,
            )

    menu_items = [
        HeaderMenuItem(
            icon=Icons.AUTO_AWESOME,
            label=(
                txt["menu_demo_clear"] if STATE.demo_mode else txt["menu_demo_load"]
            ),
            on_click=_menu_clear_demo if STATE.demo_mode else _menu_load_demo,
        ),
    ]

    header_widget = header(
        theme,
        lang,
        icon=Icons.AUTO_STORIES_OUTLINED,
        title=txt["title"],
        subtitle=txt["subtitle"],
        on_help_click=lambda: open_doc_assistant_how_to(container, theme, lang),
        trailing=demo_pill,
        menu_items=menu_items,
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
    footer_layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    footer_holder.setLayout(footer_layout)
    layout.addWidget(footer_holder)

    state_box: dict[str, Optional[Callable[[], None]]] = {"refresh_footer": None}

    def _clear_widget(widget: QWidget) -> None:
        layout_obj = widget.layout()
        if layout_obj is None:
            return
        while layout_obj.count():
            item = layout_obj.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _refresh_tabs() -> None:
        _clear_widget(tab_holder)
        try:
            tab_widget = tab_bar(
                theme,
                tabs=[txt["tab_upload"], txt["tab_analyze"], txt["tab_output"]],
                active_index=STATE.active_tab,
                on_change=_on_tab_change,
            )
            tab_layout.addWidget(tab_widget)
        except Exception as exc:
            logger_service.log_exception("ai_doc_assistant.view", "refresh_tabs_build_failed", exc)

    def _refresh_body() -> None:
        while body_stack.count():
            w = body_stack.widget(0)
            body_stack.removeWidget(w)
            w.deleteLater()
        try:
            if STATE.active_tab == TAB_UPLOAD:
                widget = _build_upload_tab(theme, txt, _on_state_change)
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
                scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
                scroll.setWidget(wrapper)
                body_stack.addWidget(scroll)
            elif STATE.active_tab == TAB_ANALYZE:
                widget = _build_analyze_tab(theme, txt, _on_state_change)
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
                scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
                scroll.setWidget(wrapper)
                body_stack.addWidget(scroll)
            else:
                body_stack.addWidget(_build_output_tab(theme, txt, _on_navigate_tab))
        except Exception as exc:
            logger_service.log_exception(
                "ai_doc_assistant.view", "refresh_tab_body_build_failed", exc,
                active_tab=STATE.active_tab,
            )

    def _refresh_footer() -> None:
        _clear_widget(footer_holder)
        try:
            widget, refresh_fn = _build_footer(
                theme, lang, txt, _on_state_change, _on_navigate_tab
            )
            footer_layout.addWidget(widget)
            state_box["refresh_footer"] = refresh_fn
        except Exception as exc:
            logger_service.log_exception("ai_doc_assistant.view", "refresh_footer_build_failed", exc)
            state_box["refresh_footer"] = None

    def _on_state_change() -> None:
        fn = state_box.get("refresh_footer")
        if fn is not None:
            fn()

    def _on_tab_change(index: int) -> None:
        if index == STATE.active_tab:
            return
        logger_service.log_event(
            "INFO", "ai_doc_assistant.view", "tab_change",
            prev_tab=STATE.active_tab, new_tab=index,
        )
        STATE.active_tab = index
        _refresh_tabs()
        _refresh_body()

    def _on_navigate_tab(index: int) -> None:
        STATE.active_tab = index
        _refresh_tabs()
        _refresh_body()

    _refresh_tabs()
    _refresh_body()
    _refresh_footer()

    return container
