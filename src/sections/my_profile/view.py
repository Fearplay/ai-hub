"""Center view for the My Profile section.

A single scrollable page: an intro/status card, the source-material inputs
(CV required; LinkedIn / GitHub / notes optional), a build button, and the
parsed profile (or an empty state). The extraction runs on a worker thread
so the UI stays responsive; results are persisted via
:mod:`src.services.career_profile_store` and re-read on the next build.
"""

from __future__ import annotations

import threading
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.components.file_drop_zone import file_drop_zone
from src.components.header import header
from src.qt.icons import Icons
from src.qt.runtime import dispatch as runtime_dispatch
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    FlowLayout,
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
    wrap_label_slot,
)
from src.services import career_profile_store
from src.services import logger as logger_service
from src.services.file_parser import ParsedFile, human_size
from src.sections.my_profile import pipeline
from src.sections.my_profile.data import SECTION_ICON
from src.sections.my_profile.state import STATE, UploadedFile
from src.sections.my_profile.strings import s
from src.theme import Theme


_RESUME_EXTENSIONS = ("pdf", "docx", "txt", "md", "html", "htm")
_LINKEDIN_EXTENSIONS = ("pdf", "txt", "html", "htm")


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception as exc:
        logger_service.log_exception("my_profile.view", "full_refresh_import_failed", exc)
        return
    try:
        request_section_refresh()
    except Exception as exc:
        logger_service.log_exception("my_profile.view", "full_refresh_failed", exc)


def _hydrate_from_store() -> None:
    """Load the persisted profile into ``STATE`` once per session."""
    if STATE.hydrated:
        return
    STATE.hydrated = True
    try:
        data = career_profile_store.load()
    except Exception as exc:
        logger_service.log_exception("my_profile.view", "hydrate_failed", exc)
        return
    if not data:
        return
    STATE.demo_mode = bool(data.get("demo", False))
    profile = data.get("profile")
    STATE.profile = profile if isinstance(profile, dict) and profile else None
    sources = data.get("sources") or {}
    for attr, key in (("resume", "resume"), ("linkedin", "linkedin")):
        src = sources.get(key)
        if isinstance(src, dict) and src.get("text"):
            setattr(
                STATE,
                attr,
                UploadedFile(
                    path=str(src.get("path") or ""),
                    name=str(src.get("name") or ""),
                    ext=str(src.get("ext") or ""),
                    size_bytes=int(src.get("size_bytes") or 0),
                    text=str(src.get("text") or ""),
                ),
            )
    STATE.github_url = str(sources.get("github_url") or "")
    STATE.notes = str(sources.get("notes") or "")


def _card(theme: Theme, *, title: str, desc: str = "", body: QWidget) -> QFrame:
    card = QFrame()
    card.setObjectName("MyProfileCard")
    card.setStyleSheet(
        f"""
        QFrame#MyProfileCard {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 14px;
        }}
        """
    )
    layout = vbox(spacing=4, margins=(18, 18, 18, 18))
    card.setLayout(layout)
    title_label = TitleLabel(title, theme=theme, size=15, weight=QFont.Weight.Bold)
    wrap_label_slot(title_label)
    layout.addWidget(title_label)
    if desc:
        desc_label = MutedLabel(desc, theme=theme, size=12)
        wrap_label_slot(desc_label)
        layout.addWidget(desc_label)
    layout.addSpacing(8)
    layout.addWidget(body)
    return card


def _file_chip(
    theme: Theme,
    *,
    name: str,
    ext: str,
    size_bytes: int,
    on_clear: Callable[[], None],
    clear_tooltip: str,
) -> QFrame:
    chip = QFrame()
    chip.setObjectName("MyProfileFileChip")
    chip.setStyleSheet(
        f"""
        QFrame#MyProfileFileChip {{
            background-color: {theme.surface_2};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        """
    )
    layout = hbox(spacing=10, margins=(12, 10, 12, 10))
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    chip.setLayout(layout)

    badge = QFrame()
    badge.setFixedSize(32, 32)
    badge.setStyleSheet(
        f"background-color: {rgba(theme.primary, 0.14)}; border-radius: 8px;"
    )
    bl = hbox(spacing=0, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setLayout(bl)
    bl.addWidget(
        IconLabel(Icons.DESCRIPTION_OUTLINED, color=theme.primary, size=18),
        alignment=Qt.AlignmentFlag.AlignCenter,
    )
    layout.addWidget(badge)

    info = QFrame()
    info.setStyleSheet("background: transparent; border: none;")
    info.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    info_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    info.setLayout(info_layout)
    info_layout.addWidget(
        BodyLabel(name, theme=theme, size=13, weight=QFont.Weight.DemiBold)
    )
    meta = f"{(ext or '').upper()} \u00b7 {human_size(size_bytes)}" if ext else human_size(size_bytes)
    info_layout.addWidget(MutedLabel(meta, theme=theme, size=11))
    layout.addWidget(info, 1)

    close = IconOnlyButton(
        Icons.CLOSE, color=theme.text_muted, size=16,
        bg_hover=theme.surface, tooltip=clear_tooltip,
    )
    close.clicked.connect(on_clear)
    layout.addWidget(close)
    return chip


# --- inputs card ------------------------------------------------------------


def _inputs_card(
    theme: Theme,
    lang: str,
    txt: dict,
    rebuild: Callable[[], None],
) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    def _on_resume(parsed: ParsedFile) -> None:
        STATE.resume = UploadedFile(
            path=parsed.path, name=parsed.name, ext=parsed.ext,
            size_bytes=parsed.size_bytes, text=parsed.text,
        )
        STATE.last_error = ""
        rebuild()

    def _on_linkedin(parsed: ParsedFile) -> None:
        STATE.linkedin = UploadedFile(
            path=parsed.path, name=parsed.name, ext=parsed.ext,
            size_bytes=parsed.size_bytes, text=parsed.text,
        )
        rebuild()

    body_layout.addWidget(
        file_drop_zone(
            theme,
            log_area="my_profile.upload",
            title=txt["resume_title"],
            hint=txt["resume_hint"],
            extensions=_RESUME_EXTENSIONS,
            unsupported_message=txt["resume_hint"],
            on_file_resolved=_on_resume,
            height=140,
        )
    )
    if STATE.resume:
        body_layout.addWidget(
            _file_chip(
                theme, name=STATE.resume.name, ext=STATE.resume.ext,
                size_bytes=STATE.resume.size_bytes,
                on_clear=lambda: (_clear_attr("resume"), rebuild()),
                clear_tooltip=txt["clear_file_tooltip"],
            )
        )
    body_layout.addSpacing(6)

    body_layout.addWidget(
        file_drop_zone(
            theme,
            log_area="my_profile.upload",
            title=txt["linkedin_title"],
            hint=txt["linkedin_hint"],
            extensions=_LINKEDIN_EXTENSIONS,
            unsupported_message=txt["linkedin_hint"],
            on_file_resolved=_on_linkedin,
            height=120,
        )
    )
    if STATE.linkedin:
        body_layout.addWidget(
            _file_chip(
                theme, name=STATE.linkedin.name, ext=STATE.linkedin.ext,
                size_bytes=STATE.linkedin.size_bytes,
                on_clear=lambda: (_clear_attr("linkedin"), rebuild()),
                clear_tooltip=txt["clear_file_tooltip"],
            )
        )
    body_layout.addSpacing(6)

    body_layout.addWidget(
        BodyLabel(txt["github_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold)
    )
    github_field = themed_line_edit(theme, placeholder=txt["github_hint"])
    github_field.setText(STATE.github_url)
    github_field.setEnabled(not STATE.github_skip)
    github_field.textChanged.connect(lambda v: setattr(STATE, "github_url", v))
    body_layout.addWidget(github_field)

    skip_check = QCheckBox(txt["github_skip"])
    skip_check.setChecked(STATE.github_skip)
    skip_check.setStyleSheet(f"QCheckBox {{ color: {theme.text}; }}")

    def _set_skip(state: int) -> None:
        STATE.github_skip = state == Qt.CheckState.Checked.value
        if STATE.github_skip:
            STATE.github_profile = None
        rebuild()

    skip_check.stateChanged.connect(_set_skip)
    body_layout.addWidget(skip_check)
    body_layout.addSpacing(6)

    body_layout.addWidget(
        BodyLabel(txt["notes_label"], theme=theme, size=12, weight=QFont.Weight.DemiBold)
    )
    notes_field = themed_text_edit(theme, placeholder=txt["notes_hint"], min_height=90)
    notes_field.setPlainText(STATE.notes)
    notes_field.textChanged.connect(
        lambda: setattr(STATE, "notes", notes_field.toPlainText())
    )
    body_layout.addWidget(notes_field)

    return _card(
        theme, title=txt["inputs_title"], desc=txt["inputs_desc"], body=body,
    )


def _clear_attr(attr: str) -> None:
    setattr(STATE, attr, None)


# --- parsed profile display -------------------------------------------------


def _result_block(theme: Theme, title: str, body: QWidget) -> QWidget:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=6, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    layout.addWidget(
        custom_label(title.upper(), color=theme.text_muted, size=11, weight=QFont.Weight.Bold)
    )
    layout.addWidget(body)
    return holder


def _bullet_list(theme: Theme, bullets: list) -> QWidget:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=3, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    for b in bullets:
        text = str(b or "").strip()
        if not text:
            continue
        row = QFrame()
        row.setStyleSheet("background: transparent;")
        rl = hbox(spacing=8, margins=(0, 0, 0, 0))
        rl.setAlignment(Qt.AlignmentFlag.AlignTop)
        row.setLayout(rl)
        rl.addWidget(
            IconLabel(Icons.CIRCLE, color=theme.primary, size=6), 0, Qt.AlignmentFlag.AlignTop,
        )
        label = BodyLabel(text, theme=theme, size=12)
        wrap_label_slot(label)
        rl.addWidget(label, 1)
        layout.addWidget(row)
    return holder


def _entry_block(theme: Theme, *, heading: str, sub: str, bullets: list) -> QWidget:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    head = BodyLabel(heading, theme=theme, size=13, weight=QFont.Weight.DemiBold)
    wrap_label_slot(head)
    layout.addWidget(head)
    if sub:
        sub_label = MutedLabel(sub, theme=theme, size=11)
        wrap_label_slot(sub_label)
        layout.addWidget(sub_label)
    if bullets:
        layout.addSpacing(2)
        layout.addWidget(_bullet_list(theme, bullets))
    return holder


def _profile_card(theme: Theme, lang: str, txt: dict, profile: dict) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=14, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    # Identity header.
    name = (profile.get("full_name") or "").strip() or txt["none"]
    name_label = TitleLabel(name, theme=theme, size=18, weight=QFont.Weight.Bold)
    wrap_label_slot(name_label)
    body_layout.addWidget(name_label)
    headline_bits = [
        b for b in ((profile.get("headline") or "").strip(), (profile.get("industry") or "").strip()) if b
    ]
    if headline_bits:
        hl = MutedLabel("  ·  ".join(headline_bits), theme=theme, size=12)
        wrap_label_slot(hl)
        body_layout.addWidget(hl)

    contact = profile.get("contact") or {}
    contact_bits = [
        str(contact.get(k) or "").strip()
        for k in ("email", "phone", "location")
        if str(contact.get(k) or "").strip()
    ]
    if contact_bits:
        body_layout.addWidget(
            _result_block(
                theme, txt["section_contact"],
                _wrapped_label(theme, "   ".join(contact_bits)),
            )
        )

    summary = (profile.get("summary") or "").strip()
    if summary:
        body_layout.addWidget(
            _result_block(theme, txt["section_summary"], _wrapped_label(theme, summary))
        )

    skills = [str(s_).strip() for s_ in (profile.get("technical_skills") or []) if str(s_).strip()]
    if skills:
        chips = QFrame()
        chips.setStyleSheet("background: transparent;")
        wrap_label_slot(chips)
        flow = FlowLayout(chips, margin=0, h_spacing=6, v_spacing=6)
        chips.setLayout(flow)
        for sk in skills:
            flow.addWidget(Pill(text=sk, bg=rgba(theme.primary, 0.14), fg=theme.primary))
        body_layout.addWidget(_result_block(theme, txt["section_skills"], chips))

    experiences = profile.get("experiences") or []
    if experiences:
        col = _stack(theme, spacing=10)
        for exp in experiences:
            role = (exp.get("role") or "").strip()
            company = (exp.get("company") or "").strip()
            etype = (exp.get("employment_type") or "").strip()
            heading = " · ".join([b for b in (role, company) if b]) or txt["none"]
            sub_bits = [b for b in ((exp.get("period") or "").strip(), (exp.get("location") or "").strip(), etype) if b]
            col.layout().addWidget(
                _entry_block(theme, heading=heading, sub="  ·  ".join(sub_bits), bullets=exp.get("bullets") or [])
            )
        body_layout.addWidget(_result_block(theme, txt["section_experience"], col))

    education = profile.get("education") or []
    if education:
        col = _stack(theme, spacing=8)
        for edu in education:
            heading = (edu.get("institution") or "").strip() or txt["none"]
            sub_bits = [b for b in ((edu.get("degree") or "").strip(), (edu.get("period") or "").strip()) if b]
            details = (edu.get("details") or "").strip()
            col.layout().addWidget(
                _entry_block(
                    theme, heading=heading, sub="  ·  ".join(sub_bits),
                    bullets=[details] if details else [],
                )
            )
        body_layout.addWidget(_result_block(theme, txt["section_education"], col))

    certs = profile.get("certifications") or []
    if certs:
        col = _stack(theme, spacing=4)
        for cert in certs:
            bits = [b for b in ((cert.get("name") or "").strip(), (cert.get("issuer") or "").strip(), (cert.get("period") or "").strip()) if b]
            if bits:
                lbl = _wrapped_label(theme, "  ·  ".join(bits))
                col.layout().addWidget(lbl)
        body_layout.addWidget(_result_block(theme, txt["section_certifications"], col))

    languages = profile.get("languages") or []
    if languages:
        chips = QFrame()
        chips.setStyleSheet("background: transparent;")
        wrap_label_slot(chips)
        flow = FlowLayout(chips, margin=0, h_spacing=6, v_spacing=6)
        chips.setLayout(flow)
        for lng in languages:
            nm = (lng.get("name") or "").strip()
            cefr = (lng.get("cefr") or "").strip()
            if not nm:
                continue
            text = f"{nm} ({cefr})" if cefr else nm
            flow.addWidget(Pill(text=text, bg=theme.surface_2, fg=theme.text))
        body_layout.addWidget(_result_block(theme, txt["section_languages"], chips))

    projects = profile.get("projects") or []
    if projects:
        col = _stack(theme, spacing=10)
        for proj in projects:
            heading = (proj.get("name") or "").strip() or txt["none"]
            sub_bits = [b for b in ((proj.get("period") or "").strip(), (proj.get("url") or "").strip()) if b]
            col.layout().addWidget(
                _entry_block(theme, heading=heading, sub="  ·  ".join(sub_bits), bullets=proj.get("bullets") or [])
            )
        body_layout.addWidget(_result_block(theme, txt["section_projects"], col))

    links = profile.get("online_links") or []
    link_bits = []
    for link in links:
        label = (link.get("label") or "").strip()
        url = (link.get("url") or "").strip()
        if url:
            link_bits.append(f"{label}: {url}" if label else url)
    if link_bits:
        col = _stack(theme, spacing=2)
        for lb in link_bits:
            col.layout().addWidget(_wrapped_label(theme, lb, color=theme.primary))
        body_layout.addWidget(_result_block(theme, txt["section_links"], col))

    return _card(theme, title=txt["result_title"], body=body)


def _wrapped_label(theme: Theme, text: str, *, color: str = "") -> QWidget:
    label = BodyLabel(text, theme=theme, size=12)
    if color:
        label.setStyleSheet(f"color: {color}; background: transparent;")
    wrap_label_slot(label)
    return label


def _stack(theme: Theme, *, spacing: int) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=spacing, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    return holder


def _empty_state(theme: Theme, txt: dict) -> QWidget:
    holder = QFrame()
    holder.setObjectName("MyProfileEmpty")
    holder.setStyleSheet(
        f"""
        QFrame#MyProfileEmpty {{
            background-color: {theme.surface};
            border: 1px dashed {theme.border};
            border-radius: 14px;
        }}
        """
    )
    layout = vbox(spacing=8, margins=(40, 44, 40, 44))
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    holder.setLayout(layout)
    layout.addWidget(
        IconLabel(SECTION_ICON, color=theme.text_muted, size=40),
        alignment=Qt.AlignmentFlag.AlignHCenter,
    )
    title_label = TitleLabel(txt["empty_title"], theme=theme, size=16, weight=QFont.Weight.Bold)
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title_label)
    desc = MutedLabel(txt["empty_desc"], theme=theme, size=12)
    desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
    desc.setMaximumWidth(520)
    layout.addWidget(desc, alignment=Qt.AlignmentFlag.AlignHCenter)
    return holder


# --- intro / status + build -------------------------------------------------


def _intro_card(
    theme: Theme,
    lang: str,
    txt: dict,
    rebuild: Callable[[], None],
) -> QWidget:
    body = QWidget()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    used = MutedLabel(txt["used_by"], theme=theme, size=11)
    wrap_label_slot(used)
    body_layout.addWidget(used)

    meta = career_profile_store.get_meta()
    if meta.get("updated_at") and not STATE.demo_mode:
        body_layout.addWidget(
            SubtleLabel(txt["saved_at"].format(when=meta["updated_at"]), theme=theme, size=11, italic=True)
        )

    row = QFrame()
    row.setStyleSheet("background: transparent;")
    rl = hbox(spacing=10, margins=(0, 0, 0, 0))
    rl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    row.setLayout(rl)

    demo_check = QCheckBox(txt["demo_label"])
    demo_check.setChecked(STATE.demo_mode)
    demo_check.setStyleSheet(f"QCheckBox {{ color: {theme.text}; }}")
    demo_check.stateChanged.connect(
        lambda st: (pipeline.set_demo(st == Qt.CheckState.Checked.value), rebuild())
    )
    rl.addWidget(demo_check)
    rl.addStretch(1)

    if STATE.profile is not None:
        clear_btn = GhostButton(txt["clear_btn"], theme=theme, icon=Icons.DELETE_OUTLINE)
        clear_btn.clicked.connect(lambda: (pipeline.clear_profile(), rebuild()))
        rl.addWidget(clear_btn)
    body_layout.addWidget(row)

    return _card(theme, title=txt["intro_title"], desc=txt["intro_desc"], body=body)


def _build_row(
    theme: Theme,
    lang: str,
    txt: dict,
    rebuild: Callable[[], None],
) -> QWidget:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    holder.setLayout(layout)

    if STATE.last_error:
        err_map = {
            "resume_missing": txt["err_resume_missing"],
            "no_json": txt["err_no_json"],
        }
        msg = err_map.get(STATE.last_error, STATE.last_error or txt["err_generic"])
        err_label = custom_label(msg, color="#EF4444", size=12, weight=QFont.Weight.DemiBold)
        wrap_label_slot(err_label)
        layout.addWidget(err_label)

    row = QFrame()
    row.setStyleSheet("background: transparent;")
    rl = hbox(spacing=10, margins=(0, 0, 0, 0))
    rl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    row.setLayout(rl)

    has_profile = STATE.profile is not None
    label = txt["building_btn"] if STATE.building else (
        txt["rebuild_btn"] if has_profile else txt["build_btn"]
    )
    build_btn = PrimaryButton(label, theme=theme, icon=Icons.AUTO_AWESOME)
    build_btn.setEnabled(not STATE.building)
    build_btn.clicked.connect(lambda: _start_build(lang, rebuild))
    rl.addWidget(build_btn)
    rl.addStretch(1)
    layout.addWidget(row)
    return holder


def _start_build(lang: str, rebuild: Callable[[], None]) -> None:
    if STATE.building:
        return
    if not STATE.demo_mode and (not STATE.resume or not STATE.resume.text):
        STATE.last_error = "resume_missing"
        rebuild()
        return
    STATE.building = True
    STATE.last_error = ""
    rebuild()

    def _worker() -> None:
        try:
            pipeline.build_profile(output_lang=lang)
        except Exception as exc:
            logger_service.log_exception("my_profile.view", "build_worker_failed", exc)
            STATE.last_error = "generic"
        finally:
            STATE.building = False
        runtime_dispatch(_request_full_refresh)

    threading.Thread(target=_worker, daemon=True, name="my-profile-build").start()


def build_view(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    _hydrate_from_store()
    logger_service.log_event("INFO", "my_profile.view", "build_view", lang=lang)

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    root = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(root)

    root.addWidget(
        header(
            theme,
            lang,
            icon=SECTION_ICON,
            title=txt["title"],
            subtitle=txt["subtitle"],
            show_help_button=False,
            show_menu_button=False,
        )
    )

    inner = QWidget()
    inner.setStyleSheet(f"background-color: {theme.bg};")
    inner_layout = vbox(spacing=14, margins=(24, 18, 24, 24))
    inner.setLayout(inner_layout)

    def _rebuild() -> None:
        _request_full_refresh()

    try:
        inner_layout.addWidget(_intro_card(theme, lang, txt, _rebuild))
        inner_layout.addWidget(_inputs_card(theme, lang, txt, _rebuild))
        inner_layout.addWidget(_build_row(theme, lang, txt, _rebuild))
        if STATE.profile is not None:
            inner_layout.addWidget(_profile_card(theme, lang, txt, STATE.profile))
        else:
            inner_layout.addWidget(_empty_state(theme, txt))
    except Exception as exc:
        logger_service.log_exception("my_profile.view", "build_panels_failed", exc)
        raise
    inner_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(inner)
    root.addWidget(scroll, 1)
    return container
