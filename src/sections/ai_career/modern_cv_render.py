"""Two-column "modern CV" renderer driven by ``MODERN_CV_SCHEMA`` JSON (PySide6 port).

Three render targets share one payload:

* :func:`render_view` - a Qt widget tree painted in the Documents tab
  preview. Uses QWidget primitives (no QWebEngineView) so the in-app
  preview matches the printed PDF pixel-for-pixel without bundling a
  full Chromium runtime. Pulls colours from the active palette in
  :data:`STATE.modern_cv_theme` so ``Change colour`` re-renders the
  preview in place.
* :func:`render_html` - the same layout exported as a self-contained
  HTML file. Delegates to
  :func:`src.sections.ai_career.themes.render_modern_cv_html` so HTML
  + PDF + preview all agree on layout / palette.
* :func:`render_pdf` - HTML -> A4 PDF via Playwright
  (:mod:`src.services.html_pdf`); falls back to a clean ``RuntimeError``
  if Playwright + a browser are not reachable on this machine.

Markdown bold (``**...**``) inside any text field is honoured by every
render target.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, List, Optional

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QColor,
    QFont,
    QGradient,
    QLinearGradient,
    QPainter,
    QPalette,
    QPen,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.qt.theme import rgba
from src.sections.ai_career import themes
from src.sections.ai_career.state import STATE
from src.theme import Theme


_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _split_bold(text: str) -> list[tuple[str, bool]]:
    if not text:
        return []
    out: list[tuple[str, bool]] = []
    pos = 0
    for m in _BOLD_RE.finditer(text):
        if m.start() > pos:
            out.append((text[pos : m.start()], False))
        out.append((m.group(1), True))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], False))
    return out


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _safe_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    return []


def _active_theme() -> themes.ResumeTheme:
    state_theme = getattr(STATE, "modern_cv_theme", None) or {}
    palette = (state_theme.get("palette") or "").strip().lower()
    layout = (state_theme.get("layout") or "").strip().lower()
    return themes.resolve_theme(palette, layout)


# --- low-level helpers ------------------------------------------------------


def _make_label(
    text: str,
    *,
    color: str,
    size: float,
    weight: int = 400,
    italic: bool = False,
    letter_spacing: float = 0.0,
    selectable: bool = False,
) -> QLabel:
    label = QLabel(text)
    font = QFont()
    font.setPixelSize(int(round(size)))
    font.setWeight(QFont.Weight(int(weight)))
    font.setItalic(italic)
    if letter_spacing:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, letter_spacing)
    label.setFont(font)
    label.setStyleSheet(f"color: {color}; background: transparent;")
    label.setWordWrap(True)
    if selectable:
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


def _rich_label(
    text: str,
    *,
    color: str,
    size: float,
    bold_color: Optional[str] = None,
    bold_weight: int = 700,
    weight: int = 400,
    italic: bool = False,
) -> QLabel:
    """Render markdown-bold runs by emitting an HTML label."""
    if not text:
        label = QLabel("")
        label.setStyleSheet(f"color: {color}; background: transparent;")
        return label
    bold_color = bold_color or color
    parts: list[str] = []
    for chunk, is_bold in _split_bold(text):
        if not chunk:
            continue
        chunk_html = (
            chunk.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
        )
        if is_bold:
            parts.append(
                f"<span style=\"color:{bold_color}; font-weight:{bold_weight};\">{chunk_html}</span>"
            )
        else:
            parts.append(
                f"<span style=\"color:{color}; font-weight:{weight};\">{chunk_html}</span>"
            )
    label = QLabel("".join(parts))
    label.setTextFormat(Qt.TextFormat.RichText)
    font = QFont()
    font.setPixelSize(int(round(size)))
    font.setWeight(QFont.Weight(weight))
    if italic:
        font.setItalic(True)
    label.setFont(font)
    label.setStyleSheet(f"background: transparent; color: {color};")
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


def _vbox(spacing: int = 0, margins: tuple[int, int, int, int] = (0, 0, 0, 0)) -> QVBoxLayout:
    layout = QVBoxLayout()
    layout.setSpacing(spacing)
    layout.setContentsMargins(*margins)
    return layout


def _hbox(spacing: int = 0, margins: tuple[int, int, int, int] = (0, 0, 0, 0)) -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.setSpacing(spacing)
    layout.setContentsMargins(*margins)
    return layout


# --- sidebar widgets --------------------------------------------------------


class _GradientFrame(QFrame):
    """Frame painted with a vertical accent->accent_dark gradient."""

    def __init__(self, top_color: str, bottom_color: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._top = QColor(top_color)
        self._bottom = QColor(bottom_color)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def paintEvent(self, event):  # noqa: ARG002
        painter = QPainter(self)
        gradient = QLinearGradient(0.0, 0.0, 0.0, float(self.height()))
        gradient.setColorAt(0.0, self._top)
        gradient.setColorAt(1.0, self._bottom)
        painter.fillRect(self.rect(), gradient)
        painter.end()


def _sidebar_section_title(text: str, *, accent_soft: str) -> QWidget:
    holder = QFrame()
    holder.setStyleSheet(
        f"background: transparent; border-bottom: 1px solid {rgba(accent_soft, 0.35)};"
    )
    layout = _vbox(spacing=0, margins=(0, 0, 0, 4))
    holder.setLayout(layout)
    title = _make_label(
        text.upper(),
        color=accent_soft,
        size=10,
        weight=700,
        letter_spacing=1.6,
    )
    layout.addWidget(title)
    return holder


def _sidebar_contact_row(icon: str, text: str, *, accent_soft: str) -> QWidget:
    row = QFrame()
    row.setStyleSheet("background: transparent;")
    layout = _hbox(spacing=4, margins=(0, 0, 0, 0))
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    row.setLayout(layout)
    icon_label = _make_label(icon, color=accent_soft, size=11, weight=700)
    icon_label.setFixedWidth(14)
    layout.addWidget(icon_label)
    layout.addWidget(_make_label(text, color="#FFFFFF", size=11, selectable=True), 1)
    return row


def _sidebar_block(title: str, body: Iterable[QWidget], *, accent_soft: str) -> QWidget:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = _vbox(spacing=6, margins=(0, 14, 0, 0))
    holder.setLayout(layout)
    layout.addWidget(_sidebar_section_title(title, accent_soft=accent_soft))
    spacer = QWidget()
    spacer.setFixedHeight(8)
    layout.addWidget(spacer)
    for child in body:
        layout.addWidget(child)
    return holder


def _skill_chip_dark(label: str) -> QFrame:
    chip = QFrame()
    chip.setStyleSheet(
        """
        QFrame {
            background-color: rgba(255, 255, 255, 0.14);
            border: 1px solid rgba(255, 255, 255, 0.22);
            border-radius: 6px;
        }
        """
    )
    layout = _hbox(spacing=0, margins=(8, 3, 8, 3))
    chip.setLayout(layout)
    layout.addWidget(_make_label(label, color="#FFFFFF", size=11, weight=500))
    chip.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
    return chip


def _wrap_chips(items: List[str], chip_factory) -> QWidget:
    """Place chips side-by-side wrapping to next row when needed."""
    holder = QWidget()
    holder.setStyleSheet("background: transparent;")
    grid = QVBoxLayout(holder)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSpacing(4)

    row = QFrame()
    row.setStyleSheet("background: transparent;")
    rl = _hbox(spacing=4, margins=(0, 0, 0, 0))
    rl.setAlignment(Qt.AlignmentFlag.AlignLeft)
    row.setLayout(rl)
    grid.addWidget(row)
    cnt = 0
    for it in items:
        rl.addWidget(chip_factory(it))
        cnt += 1
        if cnt >= 4:
            cnt = 0
            row = QFrame()
            row.setStyleSheet("background: transparent;")
            rl = _hbox(spacing=4, margins=(0, 0, 0, 0))
            rl.setAlignment(Qt.AlignmentFlag.AlignLeft)
            row.setLayout(rl)
            grid.addWidget(row)
    rl.addStretch(1)
    return holder


def _highlight_pill(label: str, *, accent: str, accent_soft: str) -> QFrame:
    chip = QFrame()
    chip.setObjectName("ModernCvHighlightPill")
    chip.setStyleSheet(
        f"""
        QFrame#ModernCvHighlightPill {{
            background-color: {rgba(accent, 0.14)};
            border: 1px solid {accent_soft};
            border-radius: 6px;
        }}
        """
    )
    layout = _hbox(spacing=0, margins=(8, 3, 8, 3))
    chip.setLayout(layout)
    layout.addWidget(_make_label(label, color=accent, size=10, weight=600))
    chip.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
    return chip


def _section_heading(text: str, *, accent: str, rule: str) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet(
        f"background: transparent; border-bottom: 2px solid {rule};"
    )
    layout = _vbox(spacing=0, margins=(0, 18, 0, 4))
    holder.setLayout(layout)
    layout.addWidget(_make_label(
        text.upper(),
        color=accent,
        size=12,
        weight=800,
        letter_spacing=1.6,
    ))
    return holder


def _bullet_row(text: str, *, ink_700: str, ink_900: str, rule: str) -> QFrame:
    row = QFrame()
    row.setStyleSheet("background: transparent;")
    layout = _hbox(spacing=4, margins=(0, 0, 0, 0))
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    row.setLayout(layout)
    bullet = _make_label("\u25B8", color=rule, size=11, weight=700)
    bullet.setFixedWidth(14)
    layout.addWidget(bullet)
    layout.addWidget(_rich_label(
        text,
        color=ink_700,
        size=11,
        bold_color=ink_900,
        bold_weight=600,
    ), 1)
    return row


def _job_card(
    entry: dict,
    *,
    accent: str,
    accent_dark: str,
    rule: str,
    ink_900: str,
    ink_700: str,
    ink_500: str,
    accent_soft: str,
) -> QFrame:
    role = _safe_str(entry.get("role"))
    period = _safe_str(entry.get("period"))
    company = _safe_str(entry.get("company"))
    context = _safe_str(entry.get("context"))
    pills = [_safe_str(p) for p in _safe_list(entry.get("highlight_pills")) if _safe_str(p)]
    bullets = [_safe_str(b) for b in _safe_list(entry.get("bullets")) if _safe_str(b)]

    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = _vbox(spacing=4, margins=(0, 0, 0, 14))
    holder.setLayout(layout)

    row = QFrame()
    row.setStyleSheet("background: transparent;")
    rl = _hbox(spacing=8, margins=(0, 0, 0, 0))
    rl.setAlignment(Qt.AlignmentFlag.AlignTop)
    row.setLayout(rl)
    rl.addWidget(_make_label(role, color=ink_900, size=12, weight=700), 1)
    rl.addWidget(_make_label(period, color=ink_500, size=11, weight=500))
    layout.addWidget(row)

    if company or context:
        company_html = []
        if company:
            company_html.append(
                f"<span style=\"color:{accent_dark}; font-weight:600;\">{company}</span>"
            )
        if context:
            company_html.append(
                f"<span style=\"color:{ink_500}; font-style:italic;\"> {context}</span>"
            )
        cl = QLabel("".join(company_html))
        cl.setTextFormat(Qt.TextFormat.RichText)
        cl.setStyleSheet("background: transparent;")
        font = QFont()
        font.setPixelSize(11)
        cl.setFont(font)
        cl.setWordWrap(True)
        cl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(cl)

    if pills:
        layout.addWidget(_wrap_chips(pills, lambda l: _highlight_pill(l, accent=accent_dark, accent_soft=accent_soft)))

    for b in bullets:
        layout.addWidget(_bullet_row(b, ink_700=ink_700, ink_900=ink_900, rule=rule))
    return holder


def _project_card(
    entry: dict,
    *,
    accent_dark: str,
    rule: str,
    ink_700: str,
    ink_900: str,
) -> QFrame:
    name = _safe_str(entry.get("name"))
    desc = _safe_str(entry.get("description"))
    url = _safe_str(entry.get("url"))

    holder = QFrame()
    holder.setStyleSheet(
        f"background: transparent; border-left: 3px solid {rule};"
    )
    layout = _vbox(spacing=3, margins=(8, 0, 0, 10))
    holder.setLayout(layout)
    if name:
        layout.addWidget(_make_label(name, color=ink_900, size=12, weight=700))
    if desc:
        layout.addWidget(_rich_label(desc, color=ink_700, size=11, bold_color=ink_900, bold_weight=600))
    if url:
        layout.addWidget(_make_label(url, color=accent_dark, size=10, weight=500, selectable=True))
    return holder


def _edu_row(entry: dict, *, ink_900: str, ink_500: str) -> QFrame:
    title = _safe_str(entry.get("title"))
    sub = _safe_str(entry.get("sub"))
    period = _safe_str(entry.get("period"))

    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = _vbox(spacing=2, margins=(0, 0, 0, 8))
    holder.setLayout(layout)

    row = QFrame()
    row.setStyleSheet("background: transparent;")
    rl = _hbox(spacing=8, margins=(0, 0, 0, 0))
    rl.setAlignment(Qt.AlignmentFlag.AlignTop)
    row.setLayout(rl)
    rl.addWidget(_make_label(title, color=ink_900, size=11, weight=600), 1)
    rl.addWidget(_make_label(period, color=ink_500, size=10, weight=500))
    layout.addWidget(row)
    if sub:
        layout.addWidget(_make_label(sub, color=ink_500, size=11, italic=True, selectable=True))
    return holder


def _cert_item(entry: dict, *, accent_dark: str, ink_700: str, ink_900: str) -> QFrame:
    year = _safe_str(entry.get("year"))
    text = _safe_str(entry.get("text"))
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = _hbox(spacing=8, margins=(0, 0, 0, 4))
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    holder.setLayout(layout)
    if year:
        layout.addWidget(_make_label(year, color=accent_dark, size=11, weight=700))
    layout.addWidget(_rich_label(text, color=ink_700, size=11, bold_color=ink_900, bold_weight=600), 1)
    return holder


def _leadership_banner(items: List[str], *, accent: str, accent_dark: str, rule: str, ink_700: str) -> QFrame:
    banner = QFrame()
    banner.setObjectName("ModernCvLeadershipBanner")
    banner.setStyleSheet(
        f"""
        QFrame#ModernCvLeadershipBanner {{
            background-color: {rgba(accent, 0.10)};
            border-left: 4px solid {rule};
            border-radius: 6px;
        }}
        """
    )
    layout = _vbox(spacing=2, margins=(14, 10, 14, 10))
    banner.setLayout(layout)
    layout.addWidget(_make_label(
        "LEADERSHIP HIGHLIGHTS",
        color=accent_dark,
        size=10,
        weight=700,
        letter_spacing=1.4,
    ))
    spacer = QWidget()
    spacer.setFixedHeight(4)
    layout.addWidget(spacer)
    for item in items:
        row = QFrame()
        row.setStyleSheet("background: transparent;")
        rl = _hbox(spacing=4, margins=(0, 0, 0, 0))
        rl.setAlignment(Qt.AlignmentFlag.AlignTop)
        row.setLayout(rl)
        bullet = _make_label("\u25CF", color=rule, size=10, weight=700)
        bullet.setFixedWidth(12)
        rl.addWidget(bullet)
        rl.addWidget(_rich_label(
            item,
            color=ink_700,
            size=11,
            bold_color=accent_dark,
            bold_weight=700,
        ), 1)
        layout.addWidget(row)
    return banner


# --- main render entry points -----------------------------------------------


_PAPER_WIDTH = 720
_PAPER_HEIGHT = 1018


def render_view(theme: Theme, data: Optional[dict]) -> QWidget:
    """Render the Modern CV payload as a themed two-column Qt preview."""
    if not isinstance(data, dict):
        data = {}

    active = _active_theme()
    accent = active.accent
    accent_dark = active.accent_dark
    accent_soft = active.accent_soft
    rule = active.rule
    paper = "#FFFFFF"
    ink_900 = active.text_primary
    ink_700 = "#334155"
    ink_500 = active.text_muted

    full_name = _safe_str(data.get("full_name"))
    role_headline = _safe_str(data.get("role_headline"))
    role_subtitle = _safe_str(data.get("role_subtitle"))
    contact = data.get("contact") or {}
    online_links = _safe_list(data.get("online_links"))
    skill_groups = _safe_list(data.get("skill_groups"))
    languages = _safe_list(data.get("languages"))
    profile_summary = _safe_str(data.get("profile_summary"))
    leadership_highlights = [
        _safe_str(x) for x in _safe_list(data.get("leadership_highlights")) if _safe_str(x)
    ]
    experience = _safe_list(data.get("experience"))
    projects = _safe_list(data.get("projects"))
    education = _safe_list(data.get("education"))
    certifications = _safe_list(data.get("certifications"))

    sidebar = _GradientFrame(accent, accent_dark)
    sidebar.setFixedSize(240, _PAPER_HEIGHT)
    sidebar_layout = _vbox(spacing=4, margins=(20, 22, 20, 22))
    sidebar.setLayout(sidebar_layout)
    sidebar_layout.addWidget(_make_label(full_name, color="#FFFFFF", size=22, weight=800))
    if role_headline:
        sidebar_layout.addWidget(_make_label(role_headline, color=accent_soft, size=11, weight=500))
    if role_subtitle:
        sidebar_layout.addWidget(_make_label(role_subtitle, color=accent_soft, size=10, weight=400))

    contact_rows: list[QWidget] = []
    location = _safe_str(contact.get("location") if isinstance(contact, dict) else "")
    email = _safe_str(contact.get("email") if isinstance(contact, dict) else "")
    phone = _safe_str(contact.get("phone") if isinstance(contact, dict) else "")
    if location:
        contact_rows.append(_sidebar_contact_row("@", location, accent_soft=accent_soft))
    if email:
        contact_rows.append(_sidebar_contact_row("\u2709", email, accent_soft=accent_soft))
    if phone:
        contact_rows.append(_sidebar_contact_row("\u260E", phone, accent_soft=accent_soft))
    if contact_rows:
        sidebar_layout.addWidget(_sidebar_block("Contact", contact_rows, accent_soft=accent_soft))

    if online_links:
        link_rows: list[QWidget] = []
        for link in online_links:
            if not isinstance(link, dict):
                continue
            label_text = _safe_str(link.get("label")) or _safe_str(link.get("url"))
            icon = _safe_str(link.get("icon")) or "\u2022"
            if not label_text:
                continue
            link_rows.append(_sidebar_contact_row(icon, label_text, accent_soft=accent_soft))
        if link_rows:
            sidebar_layout.addWidget(_sidebar_block("Online", link_rows, accent_soft=accent_soft))

    if skill_groups:
        groups: list[QWidget] = []
        for group in skill_groups:
            if not isinstance(group, dict):
                continue
            label_text = _safe_str(group.get("label"))
            tags = [_safe_str(t) for t in _safe_list(group.get("tags")) if _safe_str(t)]
            if not (label_text and tags):
                continue
            block = QFrame()
            block.setStyleSheet("background: transparent;")
            bl = _vbox(spacing=4, margins=(0, 0, 0, 8))
            block.setLayout(bl)
            bl.addWidget(_make_label(
                label_text.upper(),
                color=accent_soft,
                size=9,
                weight=600,
                letter_spacing=0.6,
            ))
            bl.addWidget(_wrap_chips(tags, _skill_chip_dark))
            groups.append(block)
        if groups:
            sidebar_layout.addWidget(_sidebar_block("Tech Stack", groups, accent_soft=accent_soft))

    if languages:
        lang_rows: list[QWidget] = []
        for lang_entry in languages:
            if not isinstance(lang_entry, dict):
                continue
            name = _safe_str(lang_entry.get("name"))
            level = _safe_str(lang_entry.get("level"))
            if not name:
                continue
            row = QFrame()
            row.setStyleSheet("background: transparent;")
            rl = _hbox(spacing=8, margins=(0, 0, 0, 0))
            row.setLayout(rl)
            rl.addWidget(_make_label(name, color="#FFFFFF", size=11, weight=500), 1)
            rl.addWidget(_make_label(level, color=accent_soft, size=10, weight=600))
            lang_rows.append(row)
        if lang_rows:
            sidebar_layout.addWidget(_sidebar_block("Languages", lang_rows, accent_soft=accent_soft))
    sidebar_layout.addStretch(1)

    main_column = QFrame()
    main_column.setStyleSheet(f"background-color: {paper};")
    main_column.setFixedHeight(_PAPER_HEIGHT)
    main_layout = _vbox(spacing=4, margins=(24, 22, 24, 22))
    main_column.setLayout(main_layout)

    main_layout.addWidget(_section_heading("Profile", accent=accent, rule=rule))
    if profile_summary:
        main_layout.addWidget(_rich_label(
            profile_summary,
            color=ink_700,
            size=11,
            bold_color=ink_900,
            bold_weight=600,
        ))
    if leadership_highlights:
        main_layout.addWidget(_leadership_banner(
            leadership_highlights,
            accent=accent,
            accent_dark=accent_dark,
            rule=rule,
            ink_700=ink_700,
        ))

    if experience:
        main_layout.addWidget(_section_heading("Work Experience", accent=accent, rule=rule))
        for entry in experience:
            if isinstance(entry, dict):
                main_layout.addWidget(_job_card(
                    entry,
                    accent=accent,
                    accent_dark=accent_dark,
                    rule=rule,
                    ink_900=ink_900,
                    ink_700=ink_700,
                    ink_500=ink_500,
                    accent_soft=accent_soft,
                ))

    if projects:
        main_layout.addWidget(_section_heading("Projects", accent=accent, rule=rule))
        for entry in projects:
            if isinstance(entry, dict):
                main_layout.addWidget(_project_card(
                    entry,
                    accent_dark=accent_dark,
                    rule=rule,
                    ink_700=ink_700,
                    ink_900=ink_900,
                ))

    if education:
        main_layout.addWidget(_section_heading("Education", accent=accent, rule=rule))
        for entry in education:
            if isinstance(entry, dict):
                main_layout.addWidget(_edu_row(entry, ink_900=ink_900, ink_500=ink_500))

    if certifications:
        main_layout.addWidget(_section_heading("Certifications & Courses", accent=accent, rule=rule))
        for entry in certifications:
            if isinstance(entry, dict):
                main_layout.addWidget(_cert_item(entry, accent_dark=accent_dark, ink_700=ink_700, ink_900=ink_900))
    main_layout.addStretch(1)

    paper_card = QFrame()
    paper_card.setStyleSheet(f"background-color: {paper}; border-radius: 6px;")
    paper_card.setFixedSize(_PAPER_WIDTH, _PAPER_HEIGHT)
    paper_layout = _hbox(spacing=0, margins=(0, 0, 0, 0))
    paper_card.setLayout(paper_layout)
    paper_layout.addWidget(sidebar)
    paper_layout.addWidget(main_column, 1)

    shadow = QGraphicsDropShadowEffect(paper_card)
    shadow.setBlurRadius(18)
    shadow.setOffset(0, 6)
    shadow.setColor(QColor(15, 23, 42, int(0.18 * 255)))
    paper_card.setGraphicsEffect(shadow)

    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    wrapper.setFixedHeight(_PAPER_HEIGHT + 24)
    wl = _hbox(spacing=0, margins=(8, 8, 8, 8))
    wl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
    wrapper.setLayout(wl)
    wl.addWidget(paper_card)
    return wrapper


def render_html(data: Optional[dict], *, output_lang: str = "en") -> str:
    return themes.render_modern_cv_html(data or {}, _active_theme(), output_lang=output_lang)


def render_pdf(data: Optional[dict], target: Path, *, output_lang: str = "en") -> Path:
    from src.services import html_pdf

    target = Path(target)
    html = render_html(data, output_lang=output_lang)
    try:
        html_pdf.render_html_to_pdf(html, target)
    except html_pdf.PdfRendererUnavailableError as exc:
        raise RuntimeError(
            "Playwright PDF export is unavailable on this machine. "
            "Install Google Chrome / Microsoft Edge or run "
            "`playwright install chromium` to enable PDF export. "
            f"({exc})"
        ) from exc
    return target
