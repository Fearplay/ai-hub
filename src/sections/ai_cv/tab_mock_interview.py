"""Mock Interview tab for the AI Career section.

An interactive interview simulator that reuses the section's chat-style
bubbles. The flow per the plan:

    interviewer asks a tailored question
        -> candidate answers
            -> coach gives STAR feedback + a model answer
                -> interviewer asks the next question
                    ... until ~6 questions or the candidate stops.

All AI work goes through :func:`pipeline.interview_turn` (structured
output via ``ai_provider.run``); demo mode returns canned turns. The
transcript lives on ``STATE.interview_messages`` so it survives the
theme / language / tab rebuilds.
"""

from __future__ import annotations

import threading
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.qt.icons import Icons
from src.qt.runtime import dispatch as runtime_dispatch
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    GhostButton,
    IconLabel,
    MutedLabel,
    PrimaryButton,
    SubtleLabel,
    TitleLabel,
    custom_label,
    hbox,
    themed_text_edit,
    vbox,
    wrap_label_slot,
)
from src.services import logger as logger_service
from src.sections.ai_cv import pipeline
from src.sections.ai_cv.refs import REFS
from src.sections.ai_cv.state import STATE
from src.sections.ai_cv.strings import s
from src.theme import Theme


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception as exc:
        logger_service.log_exception(
            "ai_cv.tab_mock_interview", "request_full_refresh_import", exc,
        )
        return
    request_section_refresh()


def _has_context() -> bool:
    return bool(
        STATE.candidate
        or (STATE.resume and STATE.resume.text)
        or (STATE.linkedin and STATE.linkedin.text)
    )


def _question_bubble(theme: Theme, txt: dict, *, text: str, focus: str, number: int) -> QWidget:
    avatar = QFrame()
    avatar.setFixedSize(36, 36)
    avatar.setStyleSheet(f"background-color: {theme.primary}; border-radius: 10px;")
    al = hbox(spacing=0, margins=(0, 0, 0, 0))
    al.setAlignment(Qt.AlignmentFlag.AlignCenter)
    avatar.setLayout(al)
    al.addWidget(IconLabel(Icons.QUESTION_ANSWER_OUTLINED, color="#FFFFFF", size=18),
                 alignment=Qt.AlignmentFlag.AlignCenter)

    body = QFrame()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    label_bits = [txt["interview_question_label"].format(n=number)]
    if focus:
        label_bits.append(focus)
    body_layout.addWidget(SubtleLabel(
        "  \u00b7  ".join(label_bits), theme=theme, size=11, weight=QFont.Weight.DemiBold,
    ))

    bubble = QFrame()
    bubble.setStyleSheet(f"background-color: {theme.assistant_bubble}; border-radius: 14px;")
    bl = vbox(spacing=0, margins=(14, 12, 14, 12))
    bubble.setLayout(bl)
    q_label = BodyLabel(text, theme=theme, size=14, selectable=True)
    wrap_label_slot(q_label)
    bl.addWidget(q_label)
    body_layout.addWidget(bubble)

    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    wl = QHBoxLayout(wrapper)
    wl.setContentsMargins(0, 0, 0, 0)
    wl.setSpacing(12)
    wl.setAlignment(Qt.AlignmentFlag.AlignTop)
    wl.addWidget(avatar)
    wl.addWidget(body, 1)
    return wrapper


def _answer_bubble(theme: Theme, *, text: str) -> QWidget:
    bubble = QFrame()
    bubble.setStyleSheet(f"background-color: {theme.user_bubble}; border-radius: 14px;")
    bl = vbox(spacing=0, margins=(14, 10, 14, 10))
    bubble.setLayout(bl)
    a_label = custom_label(text, color=theme.user_bubble_text, size=14, selectable=True)
    a_label.setWordWrap(True)
    bl.addWidget(a_label)
    bubble.setMaximumWidth(560)
    bubble.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)

    avatar = QFrame()
    avatar.setFixedSize(28, 28)
    avatar.setStyleSheet(f"background-color: {theme.primary_soft}; border-radius: 14px;")
    al = hbox(spacing=0, margins=(0, 0, 0, 0))
    al.setAlignment(Qt.AlignmentFlag.AlignCenter)
    avatar.setLayout(al)
    al.addWidget(IconLabel(Icons.PERSON, color="#FFFFFF", size=16),
                 alignment=Qt.AlignmentFlag.AlignCenter)

    row = QFrame()
    row.setStyleSheet("background: transparent;")
    rl = hbox(spacing=10, margins=(0, 0, 0, 0))
    rl.setAlignment(Qt.AlignmentFlag.AlignBottom)
    row.setLayout(rl)
    rl.addWidget(bubble)
    rl.addWidget(avatar)

    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    wl = QHBoxLayout(wrapper)
    wl.setContentsMargins(0, 0, 0, 0)
    wl.setSpacing(0)
    wl.addStretch(1)
    wl.addWidget(row)
    return wrapper


def _bullet_block(theme: Theme, *, title: str, items: list[str], color: str) -> QWidget:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    layout.addWidget(SubtleLabel(title.upper(), theme=theme, size=10, weight=QFont.Weight.Bold))
    for item in items:
        row = QFrame()
        row.setStyleSheet("background: transparent;")
        rl = hbox(spacing=8, margins=(0, 0, 0, 0))
        rl.setAlignment(Qt.AlignmentFlag.AlignTop)
        row.setLayout(rl)
        rl.addWidget(IconLabel(Icons.CIRCLE, color=color, size=8), 0, Qt.AlignmentFlag.AlignTop)
        item_label = BodyLabel(item, theme=theme, size=13)
        wrap_label_slot(item_label)
        rl.addWidget(item_label, 1)
        layout.addWidget(row)
    return holder


def _feedback_card(theme: Theme, txt: dict, msg: dict) -> QWidget:
    accent = "#22C55E"
    card = QFrame()
    card.setObjectName("InterviewFeedbackCard")
    card.setStyleSheet(
        f"""
        QFrame#InterviewFeedbackCard {{
            background-color: {rgba(accent, 0.08)};
            border: 1px solid {rgba(accent, 0.28)};
            border-left: 3px solid {accent};
            border-radius: 14px;
        }}
        """
    )
    layout = vbox(spacing=10, margins=(16, 14, 16, 14))
    card.setLayout(layout)

    head = QFrame()
    head.setStyleSheet("background: transparent;")
    hl = hbox(spacing=8, margins=(0, 0, 0, 0))
    hl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    head.setLayout(hl)
    hl.addWidget(IconLabel(Icons.AUTO_AWESOME, color=accent, size=16))
    hl.addWidget(custom_label(txt["interview_feedback_label"], color=accent, size=12, weight=QFont.Weight.Bold))
    layout.addWidget(head)

    feedback = (msg.get("text") or "").strip()
    if feedback:
        fb_label = BodyLabel(feedback, theme=theme, size=13, selectable=True)
        wrap_label_slot(fb_label)
        layout.addWidget(fb_label)

    strengths = [x for x in (msg.get("strengths") or []) if x]
    if strengths:
        layout.addWidget(_bullet_block(theme, title=txt["interview_strengths_label"], items=strengths, color="#22C55E"))

    gaps = [x for x in (msg.get("gaps") or []) if x]
    if gaps:
        layout.addWidget(_bullet_block(theme, title=txt["interview_gaps_label"], items=gaps, color="#F59E0B"))

    improved = (msg.get("improved") or "").strip()
    if improved:
        # Sample answer as a plain labelled block - no nested bordered
        # frame. The boxed border inside the green feedback card looked
        # like a stray box around the text, so we drop it and rely on the
        # uppercase heading for separation.
        box = QFrame()
        box.setStyleSheet("background: transparent;")
        box_layout = vbox(spacing=4, margins=(0, 6, 0, 0))
        box.setLayout(box_layout)
        box_layout.addWidget(SubtleLabel(
            txt["interview_improved_label"].upper(), theme=theme, size=10, weight=QFont.Weight.Bold,
        ))
        imp_label = BodyLabel(improved, theme=theme, size=13, selectable=True)
        wrap_label_slot(imp_label)
        box_layout.addWidget(imp_label)
        layout.addWidget(box)

    return card


def _done_card(theme: Theme, txt: dict) -> QWidget:
    card = QFrame()
    card.setObjectName("InterviewDoneCard")
    card.setStyleSheet(
        f"""
        QFrame#InterviewDoneCard {{
            background-color: {rgba(theme.primary, 0.10)};
            border: 1px solid {rgba(theme.primary, 0.24)};
            border-radius: 14px;
        }}
        """
    )
    layout = vbox(spacing=6, margins=(18, 16, 18, 16))
    card.setLayout(layout)
    head = QFrame()
    head.setStyleSheet("background: transparent;")
    hl = hbox(spacing=8, margins=(0, 0, 0, 0))
    hl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    head.setLayout(hl)
    hl.addWidget(IconLabel(Icons.CHECK_CIRCLE, color=theme.primary, size=18))
    hl.addWidget(custom_label(txt["interview_done_title"], color=theme.primary, size=14, weight=QFont.Weight.Bold))
    layout.addWidget(head)
    desc = BodyLabel(txt["interview_done_desc"], theme=theme, size=13)
    wrap_label_slot(desc)
    layout.addWidget(desc)
    return card


def _run_turn(lang: str, *, candidate_answer: str, is_opening: bool, on_request_rerender: Callable[[], None]) -> None:
    """Kick off one interview turn on a worker thread."""
    STATE.interview_running = True
    STATE.interview_last_error = ""
    on_request_rerender()

    def _worker() -> None:
        try:
            turn, error = pipeline.interview_turn(
                output_lang=lang,
                candidate_answer=candidate_answer,
                is_opening=is_opening,
            )
        except Exception as exc:
            logger_service.log_exception(
                "ai_cv.tab_mock_interview", "interview_worker_failed", exc,
            )
            turn, error = {}, str(exc) or "unexpected error"

        STATE.interview_running = False
        if error:
            STATE.interview_last_error = error
        elif turn:
            if any(turn.get(k) for k in ("feedback", "improved_answer", "strengths", "gaps")):
                pipeline.append_interview_message(
                    "feedback",
                    text=turn.get("feedback", ""),
                    strengths=turn.get("strengths", []),
                    gaps=turn.get("gaps", []),
                    improved=turn.get("improved_answer", ""),
                )
            if turn.get("done"):
                STATE.interview_done = True
            elif turn.get("next_question"):
                pipeline.append_interview_message(
                    "question",
                    text=turn.get("next_question", ""),
                    focus=turn.get("question_focus", ""),
                )
        REFS.request_context_refresh()
        REFS.dispatch(_request_full_refresh)

    threading.Thread(target=_worker, daemon=True).start()


def _empty_state(theme: Theme, lang: str, txt: dict, on_request_rerender: Callable[[], None]) -> QWidget:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    # NB: do NOT set an AlignCenter flag on the layout itself - that makes
    # Qt size the wrap-prone description from its single-line sizeHint, so
    # the wrapped text clips (only one line's height is allocated). Instead
    # the labels span the full width (their text is centered) and the block
    # is centred vertically with stretches, which collapse so the scroll
    # area can scroll when the window is too short to fit everything.
    layout = vbox(spacing=12, margins=(40, 28, 40, 28))
    holder.setLayout(layout)

    layout.addStretch(1)
    layout.addWidget(
        IconLabel(Icons.QUESTION_ANSWER_OUTLINED, color=theme.primary, size=44),
        alignment=Qt.AlignmentFlag.AlignHCenter,
    )
    title_label = TitleLabel(txt["interview_empty_title"], theme=theme, size=17)
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title_label)
    desc = MutedLabel(txt["interview_empty_desc"], theme=theme, size=13)
    desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(desc)

    if not _has_context():
        hint = SubtleLabel(txt["interview_no_context_hint"], theme=theme, size=12, italic=True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

    start_btn = PrimaryButton(txt["interview_start_btn"], theme=theme, icon=Icons.PLAY_ARROW_ROUNDED)
    start_btn.clicked.connect(
        lambda: _run_turn(lang, candidate_answer="", is_opening=True, on_request_rerender=on_request_rerender)
    )
    layout.addWidget(start_btn, 0, Qt.AlignmentFlag.AlignHCenter)
    layout.addStretch(1)
    return holder


def _input_bar(theme: Theme, lang: str, txt: dict, on_request_rerender: Callable[[], None]) -> QFrame:
    holder = QFrame()
    holder.setObjectName("InterviewInputBar")
    holder.setStyleSheet(
        f"""
        QFrame#InterviewInputBar {{
            background-color: {theme.bg};
            border-top: 1px solid {theme.border};
        }}
        """
    )
    layout = vbox(spacing=8, margins=(24, 12, 24, 14))
    holder.setLayout(layout)

    field = themed_text_edit(theme, placeholder=txt["interview_placeholder"], min_height=72)
    layout.addWidget(field)

    row = QFrame()
    row.setStyleSheet("background: transparent;")
    rl = hbox(spacing=10, margins=(0, 0, 0, 0))
    rl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    row.setLayout(rl)

    if STATE.interview_running:
        rl.addWidget(SubtleLabel(txt["interview_running"], theme=theme, size=11, italic=True))
    elif STATE.interview_last_error:
        rl.addWidget(SubtleLabel(
            f"{txt['interview_error_prefix']}: {STATE.interview_last_error}",
            theme=theme, size=11,
        ))
    rl.addStretch(1)

    send_btn = PrimaryButton(txt["interview_send_tooltip"], theme=theme, icon=Icons.SEND)
    send_btn.setEnabled(not STATE.interview_running)

    def _submit() -> None:
        if STATE.interview_running or STATE.interview_done:
            return
        answer = field.toPlainText().strip()
        if not answer:
            return
        pipeline.append_interview_message("answer", text=answer)
        _run_turn(lang, candidate_answer=answer, is_opening=False, on_request_rerender=on_request_rerender)

    send_btn.clicked.connect(_submit)
    rl.addWidget(send_btn)
    layout.addWidget(row)
    return holder


def build_mock_interview_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Callable[[], None],
) -> QWidget:
    txt = s(lang)

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    # Header row: title + restart.
    header = QFrame()
    header.setStyleSheet("background: transparent;")
    header_layout = hbox(spacing=8, margins=(24, 14, 24, 6))
    header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    header.setLayout(header_layout)
    title_holder = QFrame()
    title_holder.setStyleSheet("background: transparent;")
    th = vbox(spacing=2, margins=(0, 0, 0, 0))
    title_holder.setLayout(th)
    th.addWidget(TitleLabel(txt["interview_title"], theme=theme, size=18, weight=QFont.Weight.Bold))
    th.addWidget(MutedLabel(txt["interview_subtitle"], theme=theme, size=12))
    header_layout.addWidget(title_holder, 1)

    if STATE.interview_messages:
        def _restart() -> None:
            # Wipe the transcript and immediately kick off a fresh opening
            # question for the SAME target role/candidate (reset_interview
            # leaves those untouched). Previously this dropped the user
            # back on the "Start interview" screen and made them click
            # again; now "Start over" restarts the conversation in place.
            STATE.reset_interview()
            _run_turn(
                lang,
                candidate_answer="",
                is_opening=True,
                on_request_rerender=on_request_rerender,
            )

        restart_btn = GhostButton(txt["interview_restart_btn"], theme=theme, icon=Icons.RESTART_ALT)
        restart_btn.clicked.connect(_restart)
        header_layout.addWidget(restart_btn, 0, Qt.AlignmentFlag.AlignTop)
    layout.addWidget(header)

    if not STATE.interview_messages and not STATE.interview_running:
        # Wrap the intro in a scroll area so the multi-line description +
        # button never clip at the 1220x760 minimum window size. With
        # ``setWidgetResizable(True)`` the content stays vertically
        # centered when there is room and scrolls only when there isn't.
        empty_scroll = QScrollArea()
        empty_scroll.setWidgetResizable(True)
        empty_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        empty_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        empty_scroll.setFrameShape(QFrame.Shape.NoFrame)
        empty_scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
        empty_scroll.setWidget(_empty_state(theme, lang, txt, on_request_rerender))
        layout.addWidget(empty_scroll, 1)
        return container

    # Transcript.
    msgs_holder = QWidget()
    msgs_holder.setStyleSheet(f"background-color: {theme.bg};")
    msgs_layout = vbox(spacing=16, margins=(24, 12, 24, 16))
    msgs_holder.setLayout(msgs_layout)

    question_number = 0
    for msg in STATE.interview_messages:
        kind = msg.get("kind")
        if kind == "question":
            question_number += 1
            msgs_layout.addWidget(_question_bubble(
                theme, txt,
                text=msg.get("text", ""),
                focus=msg.get("focus", ""),
                number=question_number,
            ))
        elif kind == "answer":
            msgs_layout.addWidget(_answer_bubble(theme, text=msg.get("text", "")))
        elif kind == "feedback":
            msgs_layout.addWidget(_feedback_card(theme, txt, msg))

    if STATE.interview_done:
        msgs_layout.addWidget(_done_card(theme, txt))
    msgs_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(msgs_holder)
    layout.addWidget(scroll, 1)

    if not STATE.interview_done:
        layout.addWidget(_input_bar(theme, lang, txt, on_request_rerender))

    def _scroll_to_bottom() -> None:
        bar = scroll.verticalScrollBar()
        if bar is not None:
            bar.setValue(bar.maximum())

    runtime_dispatch(_scroll_to_bottom)
    return container
