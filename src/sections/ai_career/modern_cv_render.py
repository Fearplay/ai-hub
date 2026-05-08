"""Two-column "modern CV" renderer driven by ``MODERN_CV_SCHEMA`` JSON.

Three render targets share one payload:

* :func:`render_view` — a Flet control tree that the Documents tab paints
  in the in-app preview. Mirrors the reference HTML the user sent
  (teal sidebar with contact / online / skills / languages on the
  left; main column with profile, leadership banner, experience cards,
  projects, education, certifications on the right).
* :func:`render_html` — the same layout exported as a self-contained
  HTML file. Reuses the exact CSS structure from the reference.
* :func:`render_pdf` — the same layout flowed onto A4 via a
  ``reportlab`` two-column table. Sidebar gets a teal background fill,
  main column flows Paragraphs / list items.

Markdown bold (``**...**``) inside any text field is honored across all
three render targets. No other markdown is supported - the payload's
fields are short and structured by design.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

import flet as ft

from src.theme import Theme


# Reference palette — mirrors the user's sample HTML so the in-app
# preview, the HTML export, and the PDF export all agree.
_TEAL_900 = "#0E7490"
_TEAL_700 = "#0F766E"
_TEAL_500 = "#14B8A6"
_TEAL_50 = "#F0FDFA"
_TEAL_TINT = "#99F6E4"
_INK_900 = "#0F172A"
_INK_700 = "#334155"
_INK_500 = "#64748B"
_INK_200 = "#E2E8F0"
_SIDEBAR_LIGHT = "#7DD3FC"
_SIDEBAR_BODY = "#E0F7FA"
_PAPER = "#FFFFFF"


# --- shared helpers ---------------------------------------------------------


_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _split_bold(text: str) -> list[tuple[str, bool]]:
    """Split ``text`` into ``(chunk, is_bold)`` runs.

    The Modern CV payload uses ``**...**`` exclusively for emphasis; we
    don't try to handle italics / inline code / links. Anything outside
    a ``**...**`` pair is rendered as plain text.
    """
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


def _spans_to_flet(
    text: str,
    *,
    color: str,
    size: float,
    bold_color: str | None = None,
    bold_weight: ft.FontWeight = ft.FontWeight.W_700,
    weight: ft.FontWeight = ft.FontWeight.W_400,
) -> list[ft.TextSpan]:
    """Render markdown-bold text as a list of TextSpans for ``ft.Text``."""
    spans: list[ft.TextSpan] = []
    for chunk, bold in _split_bold(text):
        if not chunk:
            continue
        if bold:
            spans.append(
                ft.TextSpan(
                    chunk,
                    ft.TextStyle(
                        color=bold_color or color,
                        size=size,
                        weight=bold_weight,
                    ),
                )
            )
        else:
            spans.append(
                ft.TextSpan(
                    chunk,
                    ft.TextStyle(color=color, size=size, weight=weight),
                )
            )
    return spans


def _rich_text(
    text: str,
    *,
    color: str,
    size: float,
    bold_color: str | None = None,
    bold_weight: ft.FontWeight = ft.FontWeight.W_700,
    weight: ft.FontWeight = ft.FontWeight.W_400,
    selectable: bool = True,
) -> ft.Text:
    spans = _spans_to_flet(
        text,
        color=color,
        size=size,
        bold_color=bold_color,
        bold_weight=bold_weight,
        weight=weight,
    )
    if not spans:
        return ft.Text("", color=color, size=size, selectable=selectable)
    # ``ft.Text(spans=...)`` requires the ``value`` arg to be empty so
    # only the spans render; if both are set Flet duplicates the text.
    return ft.Text(
        "",
        spans=spans,
        color=color,
        size=size,
        selectable=selectable,
    )


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _safe_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    return []


# --- in-app Flet view -------------------------------------------------------


def _sidebar_section_title(text: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            text.upper(),
            color=_SIDEBAR_LIGHT,
            size=10,
            weight=ft.FontWeight.W_700,
            style=ft.TextStyle(letter_spacing=1.6),
        ),
        padding=ft.padding.only(bottom=4),
        border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.35, _SIDEBAR_LIGHT))),
        margin=ft.margin.only(bottom=8),
    )


def _sidebar_contact_row(icon: str, text: str) -> ft.Row:
    return ft.Row(
        controls=[
            ft.Container(
                content=ft.Text(icon, color=_SIDEBAR_LIGHT, size=11, weight=ft.FontWeight.W_700),
                width=14,
            ),
            ft.Text(
                text,
                color=ft.Colors.WHITE,
                size=11,
                expand=True,
                selectable=True,
            ),
        ],
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def _sidebar_block(title: str, body_controls: Iterable[ft.Control]) -> ft.Container:
    children: list[ft.Control] = [_sidebar_section_title(title)]
    children.extend(body_controls)
    return ft.Container(
        content=ft.Column(controls=children, spacing=6, tight=True),
        margin=ft.margin.only(top=14),
    )


def _skill_chip_dark(label: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(label, color=ft.Colors.WHITE, size=11, weight=ft.FontWeight.W_500),
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        bgcolor=ft.Colors.with_opacity(0.14, ft.Colors.WHITE),
        border=ft.border.all(1, ft.Colors.with_opacity(0.22, ft.Colors.WHITE)),
        border_radius=6,
    )


def _highlight_pill(label: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(label, color=_TEAL_900, size=10.5, weight=ft.FontWeight.W_600),
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        bgcolor=_TEAL_50,
        border=ft.border.all(1, _TEAL_TINT),
        border_radius=6,
    )


def _section_heading(text: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            text.upper(),
            color=_TEAL_900,
            size=12,
            weight=ft.FontWeight.W_800,
            style=ft.TextStyle(letter_spacing=1.6),
        ),
        padding=ft.padding.only(bottom=4),
        border=ft.border.only(bottom=ft.BorderSide(2, _TEAL_500)),
        margin=ft.margin.only(top=18, bottom=10),
    )


def _bullet_row(text: str) -> ft.Row:
    return ft.Row(
        controls=[
            ft.Container(
                content=ft.Text("▸", color=_TEAL_500, size=11, weight=ft.FontWeight.W_700),
                width=14,
                padding=ft.padding.only(top=1),
            ),
            _rich_text(
                text,
                color=_INK_700,
                size=11,
                bold_color=_INK_900,
                bold_weight=ft.FontWeight.W_600,
            ),
        ],
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.START,
        expand=False,
    )


def _job_card(entry: dict) -> ft.Container:
    role = _safe_str(entry.get("role"))
    period = _safe_str(entry.get("period"))
    company = _safe_str(entry.get("company"))
    context = _safe_str(entry.get("context"))
    pills = [_safe_str(p) for p in _safe_list(entry.get("highlight_pills")) if _safe_str(p)]
    bullets = [_safe_str(b) for b in _safe_list(entry.get("bullets")) if _safe_str(b)]

    children: list[ft.Control] = [
        ft.Row(
            controls=[
                ft.Text(role, color=_INK_900, size=12.5, weight=ft.FontWeight.W_700, expand=True),
                ft.Text(period, color=_INK_500, size=11, weight=ft.FontWeight.W_500),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
    ]

    company_line: list[ft.TextSpan] = []
    if company:
        company_line.append(
            ft.TextSpan(
                company,
                ft.TextStyle(color=_TEAL_700, size=11, weight=ft.FontWeight.W_600),
            )
        )
    if context:
        sep = " " if not context.startswith(("(", "·", "—")) else " "
        company_line.append(
            ft.TextSpan(
                f"{sep}{context}",
                ft.TextStyle(color=_INK_500, size=11, weight=ft.FontWeight.W_400, italic=True),
            )
        )
    if company_line:
        children.append(ft.Text("", spans=company_line, selectable=True))

    if pills:
        children.append(
            ft.Row(
                controls=[_highlight_pill(p) for p in pills],
                spacing=6,
                run_spacing=6,
                wrap=True,
            )
        )

    if bullets:
        children.append(
            ft.Column(
                controls=[_bullet_row(b) for b in bullets],
                spacing=4,
                tight=True,
            )
        )

    return ft.Container(
        content=ft.Column(controls=children, spacing=4, tight=True),
        margin=ft.margin.only(bottom=14),
    )


def _project_card(entry: dict) -> ft.Container:
    name = _safe_str(entry.get("name"))
    desc = _safe_str(entry.get("description"))
    url = _safe_str(entry.get("url"))

    children: list[ft.Control] = []
    if name:
        children.append(ft.Text(name, color=_INK_900, size=12, weight=ft.FontWeight.W_700))
    if desc:
        children.append(
            _rich_text(
                desc,
                color=_INK_700,
                size=11,
                bold_color=_INK_900,
                bold_weight=ft.FontWeight.W_600,
            )
        )
    if url:
        children.append(
            ft.Text(
                url,
                color=_TEAL_700,
                size=10.5,
                weight=ft.FontWeight.W_500,
                selectable=True,
            )
        )

    return ft.Container(
        content=ft.Column(controls=children, spacing=3, tight=True),
        padding=ft.padding.only(left=8),
        border=ft.border.only(left=ft.BorderSide(3, _TEAL_500)),
        margin=ft.margin.only(bottom=10),
    )


def _edu_row(entry: dict) -> ft.Container:
    title = _safe_str(entry.get("title"))
    sub = _safe_str(entry.get("sub"))
    period = _safe_str(entry.get("period"))
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(title, color=_INK_900, size=11.5, weight=ft.FontWeight.W_600, expand=True),
                        ft.Text(period, color=_INK_500, size=10.5, weight=ft.FontWeight.W_500),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                ft.Text(sub, color=_INK_500, size=11, italic=True, selectable=True),
            ],
            spacing=2,
            tight=True,
        ),
        margin=ft.margin.only(bottom=8),
    )


def _cert_item(entry: dict) -> ft.Row:
    year = _safe_str(entry.get("year"))
    text = _safe_str(entry.get("text"))
    children: list[ft.Control] = []
    if year:
        children.append(
            ft.Text(year, color=_TEAL_700, size=11, weight=ft.FontWeight.W_700)
        )
    children.append(
        _rich_text(
            text,
            color=_INK_700,
            size=11,
            bold_color=_INK_900,
            bold_weight=ft.FontWeight.W_600,
        )
    )
    return ft.Row(
        controls=children,
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def _leadership_banner(items: list[str]) -> ft.Container:
    rows: list[ft.Control] = []
    for item in items:
        rows.append(
            ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Text("●", color=_TEAL_500, size=10, weight=ft.FontWeight.W_700),
                        width=12,
                        padding=ft.padding.only(top=1),
                    ),
                    _rich_text(
                        item,
                        color=_INK_700,
                        size=11,
                        bold_color=_TEAL_900,
                        bold_weight=ft.FontWeight.W_700,
                    ),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    "LEADERSHIP HIGHLIGHTS",
                    color=_TEAL_900,
                    size=10.5,
                    weight=ft.FontWeight.W_700,
                    style=ft.TextStyle(letter_spacing=1.4),
                ),
                ft.Container(height=4),
                ft.Column(controls=rows, spacing=4, tight=True),
            ],
            spacing=2,
            tight=True,
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        bgcolor=_TEAL_50,
        border=ft.border.only(left=ft.BorderSide(4, _TEAL_500)),
        border_radius=6,
        margin=ft.margin.only(top=10, bottom=14),
    )


def render_view(theme: Theme, data: dict | None) -> ft.Control:
    """Render the Modern CV payload as a two-column Flet preview.

    The card sits inside the existing Documents body container, so we
    paint the full A4 paper background ourselves (white) and surround it
    with a subtle drop shadow that matches the reference HTML's
    ``box-shadow`` look. Theme colors are intentionally NOT used inside
    the card - the modern CV is meant to look exactly like the export
    regardless of dark/light mode.
    """
    if not isinstance(data, dict):
        return ft.Container()

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

    # ---------- sidebar (left column) -----------------------------------
    sidebar_children: list[ft.Control] = [
        ft.Text(full_name, color=ft.Colors.WHITE, size=22, weight=ft.FontWeight.W_800),
    ]
    if role_headline:
        sidebar_children.append(
            ft.Text(role_headline, color=_TEAL_50, size=11.5, weight=ft.FontWeight.W_500)
        )
    if role_subtitle:
        sidebar_children.append(
            ft.Text(role_subtitle, color=_SIDEBAR_LIGHT, size=10.5, weight=ft.FontWeight.W_400)
        )

    contact_rows: list[ft.Control] = []
    location = _safe_str(contact.get("location") if isinstance(contact, dict) else "")
    email = _safe_str(contact.get("email") if isinstance(contact, dict) else "")
    phone = _safe_str(contact.get("phone") if isinstance(contact, dict) else "")
    if location:
        contact_rows.append(_sidebar_contact_row("@", location))
    if email:
        contact_rows.append(_sidebar_contact_row("✉", email))
    if phone:
        contact_rows.append(_sidebar_contact_row("☎", phone))
    if contact_rows:
        sidebar_children.append(_sidebar_block("Contact", contact_rows))

    if online_links:
        link_rows: list[ft.Control] = []
        for link in online_links:
            if not isinstance(link, dict):
                continue
            label = _safe_str(link.get("label")) or _safe_str(link.get("url"))
            icon = _safe_str(link.get("icon")) or "•"
            if not label:
                continue
            link_rows.append(_sidebar_contact_row(icon, label))
        if link_rows:
            sidebar_children.append(_sidebar_block("Online", link_rows))

    if skill_groups:
        skill_blocks: list[ft.Control] = []
        for group in skill_groups:
            if not isinstance(group, dict):
                continue
            label = _safe_str(group.get("label"))
            tags = [_safe_str(t) for t in _safe_list(group.get("tags")) if _safe_str(t)]
            if not (label and tags):
                continue
            skill_blocks.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                label.upper(),
                                color=_SIDEBAR_LIGHT,
                                size=9.5,
                                weight=ft.FontWeight.W_600,
                                style=ft.TextStyle(letter_spacing=0.6),
                            ),
                            ft.Row(
                                controls=[_skill_chip_dark(t) for t in tags],
                                spacing=4,
                                run_spacing=4,
                                wrap=True,
                            ),
                        ],
                        spacing=4,
                        tight=True,
                    ),
                    margin=ft.margin.only(bottom=8),
                )
            )
        if skill_blocks:
            sidebar_children.append(_sidebar_block("Tech Stack", skill_blocks))

    if languages:
        lang_rows: list[ft.Control] = []
        for lang_entry in languages:
            if not isinstance(lang_entry, dict):
                continue
            name = _safe_str(lang_entry.get("name"))
            level = _safe_str(lang_entry.get("level"))
            if not name:
                continue
            lang_rows.append(
                ft.Row(
                    controls=[
                        ft.Text(name, color=ft.Colors.WHITE, size=11, weight=ft.FontWeight.W_500, expand=True),
                        ft.Text(level, color=_SIDEBAR_LIGHT, size=10.5, weight=ft.FontWeight.W_600),
                    ],
                    spacing=8,
                )
            )
        if lang_rows:
            sidebar_children.append(_sidebar_block("Languages", lang_rows))

    sidebar = ft.Container(
        content=ft.Column(controls=sidebar_children, spacing=4, tight=True),
        bgcolor=_TEAL_900,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_CENTER,
            end=ft.Alignment.BOTTOM_CENTER,
            colors=[_TEAL_900, _TEAL_700],
        ),
        padding=ft.padding.symmetric(horizontal=20, vertical=22),
        width=270,
    )

    # ---------- main column ---------------------------------------------
    main_children: list[ft.Control] = []
    main_children.append(_section_heading("Profile"))
    if profile_summary:
        main_children.append(
            _rich_text(
                profile_summary,
                color=_INK_700,
                size=11.5,
                bold_color=_INK_900,
                bold_weight=ft.FontWeight.W_600,
            )
        )
    if leadership_highlights:
        main_children.append(_leadership_banner(leadership_highlights))

    if experience:
        main_children.append(_section_heading("Work Experience"))
        for entry in experience:
            if isinstance(entry, dict):
                main_children.append(_job_card(entry))

    if projects:
        main_children.append(_section_heading("Projects"))
        for entry in projects:
            if isinstance(entry, dict):
                main_children.append(_project_card(entry))

    if education:
        main_children.append(_section_heading("Education"))
        for entry in education:
            if isinstance(entry, dict):
                main_children.append(_edu_row(entry))

    if certifications:
        main_children.append(_section_heading("Certifications & Courses"))
        for entry in certifications:
            if isinstance(entry, dict):
                main_children.append(_cert_item(entry))

    main_column = ft.Container(
        content=ft.Column(controls=main_children, spacing=4, tight=True),
        bgcolor=_PAPER,
        padding=ft.padding.symmetric(horizontal=24, vertical=22),
        expand=True,
    )

    paper = ft.Container(
        content=ft.Row(
            controls=[sidebar, main_column],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        bgcolor=_PAPER,
        border_radius=6,
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=18,
            color=ft.Colors.with_opacity(0.18, _INK_900),
            offset=ft.Offset(0, 6),
        ),
    )

    # The Documents tab's body sits in a scrolling Container - keep the
    # paper card centred horizontally with a comfortable max width so it
    # doesn't stretch on ultra-wide windows.
    return ft.Container(
        content=paper,
        alignment=ft.Alignment.TOP_CENTER,
        padding=ft.padding.symmetric(horizontal=4, vertical=4),
    )


# --- HTML export ------------------------------------------------------------


_HTML_CSS = """\
:root{
  --teal-900:#0E7490;
  --teal-700:#0F766E;
  --teal-500:#14B8A6;
  --teal-50:#F0FDFA;
  --ink-900:#0F172A;
  --ink-700:#334155;
  --ink-500:#64748B;
  --ink-200:#E2E8F0;
  --bg:#FFFFFF;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{font-family:'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif;color:var(--ink-900);background:#F8FAFC;line-height:1.45;font-size:10.5pt}
.page{max-width:210mm;min-height:297mm;margin:0 auto;background:var(--bg);box-shadow:0 8px 30px rgba(15,23,42,0.08);display:grid;grid-template-columns:73mm 1fr}
.sidebar{background:linear-gradient(180deg,var(--teal-900) 0%,var(--teal-700) 100%);color:#fff;padding:14mm 9mm 12mm 9mm}
.sidebar h1{font-size:20pt;line-height:1.1;font-weight:800;letter-spacing:-0.02em;margin-bottom:3mm}
.sidebar .role{font-size:10.5pt;color:var(--teal-50);font-weight:500;margin-bottom:8mm;letter-spacing:0.02em}
.sidebar .role-sub{font-size:9pt;color:#7DD3FC;font-weight:400;display:block;margin-top:1mm}
.sb-section{margin-top:7mm}
.sb-section h3{font-size:9pt;text-transform:uppercase;letter-spacing:0.18em;font-weight:700;color:#7DD3FC;border-bottom:1px solid rgba(125,211,252,0.35);padding-bottom:1.5mm;margin-bottom:3mm}
.sb-section p,.sb-section li{font-size:9.5pt;color:#E0F7FA;margin-bottom:1.5mm;word-wrap:break-word}
.sb-section a{color:#fff;text-decoration:none;border-bottom:1px dotted rgba(255,255,255,0.4)}
.sb-section ul{list-style:none}
.sb-section .contact-line{display:flex;align-items:flex-start;gap:2mm;font-size:9pt;margin-bottom:1.8mm}
.sb-section .contact-line .ic{flex:0 0 4mm;color:#7DD3FC;font-weight:700;font-size:9pt}
.skill-group{margin-bottom:3.5mm}
.skill-group .group-label{font-size:8.5pt;color:#7DD3FC;font-weight:600;margin-bottom:1mm;text-transform:uppercase;letter-spacing:0.06em}
.skill-tags{display:flex;flex-wrap:wrap;gap:1.5mm}
.skill-tag{background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.2);padding:0.8mm 2mm;border-radius:2mm;font-size:8.5pt;color:#fff}
.lang-row{display:flex;justify-content:space-between;align-items:center;font-size:9.5pt;margin-bottom:1.5mm}
.lang-row .lvl{font-size:8.5pt;color:#7DD3FC;font-weight:600}
.main{padding:14mm 12mm 12mm 12mm}
.main h2{font-size:11pt;text-transform:uppercase;letter-spacing:0.16em;color:var(--teal-900);font-weight:800;border-bottom:2px solid var(--teal-500);padding-bottom:1.2mm;margin:0 0 4mm 0}
.main h2:not(:first-child){margin-top:7mm}
.summary{font-size:10pt;color:var(--ink-700);line-height:1.55}
.summary strong{color:var(--ink-900);font-weight:600}
.job{margin-bottom:5mm}
.job-header{display:flex;justify-content:space-between;align-items:baseline;gap:3mm;margin-bottom:0.5mm}
.job-title{font-size:10.5pt;font-weight:700;color:var(--ink-900)}
.job-period{font-size:9pt;color:var(--ink-500);font-variant-numeric:tabular-nums;white-space:nowrap;font-weight:500}
.job-company{font-size:9.5pt;color:var(--teal-700);font-weight:600;margin-bottom:1.5mm}
.job-company .ctx{color:var(--ink-500);font-weight:400;font-style:italic}
.job ul{list-style:none;padding-left:0}
.job ul li{position:relative;padding-left:4mm;margin-bottom:1.4mm;font-size:9.5pt;color:var(--ink-700);line-height:1.45}
.job ul li::before{content:'\\25B8';position:absolute;left:0;top:0;color:var(--teal-500);font-weight:700;font-size:9pt}
.job ul li strong{color:var(--ink-900);font-weight:600}
.highlight-row{display:flex;flex-wrap:wrap;gap:2mm;margin:1.5mm 0 2mm 0}
.highlight-pill{background:var(--teal-50);border:1px solid #99F6E4;color:var(--teal-900);font-size:8.5pt;padding:0.6mm 2mm;border-radius:2mm;font-weight:600}
.project-card{border-left:3px solid var(--teal-500);padding-left:3mm;margin-bottom:3mm}
.project-card .pname{font-size:10pt;font-weight:700;color:var(--ink-900);margin-bottom:0.5mm}
.project-card .pdesc{font-size:9.5pt;color:var(--ink-700);line-height:1.45}
.project-card .pdesc strong{color:var(--ink-900);font-weight:600}
.project-card a{color:var(--teal-700);text-decoration:none;font-weight:500;font-size:9pt}
.edu-row{margin-bottom:3mm}
.edu-row .top{display:flex;justify-content:space-between;font-size:10pt;font-weight:600;color:var(--ink-900)}
.edu-row .sub{font-size:9.5pt;color:var(--ink-500);font-style:italic}
.cert-list{display:grid;grid-template-columns:1fr 1fr;gap:1.5mm 4mm}
.cert-item{font-size:9.5pt;color:var(--ink-700)}
.cert-item .y{color:var(--teal-700);font-weight:600;font-variant-numeric:tabular-nums}
.cert-item strong{color:var(--ink-900);font-weight:600}
.leadership-banner{background:linear-gradient(90deg,var(--teal-50) 0%,#FFFFFF 100%);border-left:4px solid var(--teal-500);padding:3mm 4mm;margin-bottom:5mm;border-radius:0 2mm 2mm 0}
.leadership-banner .lb-title{font-size:9pt;color:var(--teal-900);font-weight:700;text-transform:uppercase;letter-spacing:0.12em;margin-bottom:1.5mm}
.leadership-banner .lb-list{display:flex;flex-direction:column;gap:1mm;font-size:9pt;color:var(--ink-700)}
.leadership-banner .lb-list strong{color:var(--teal-900);font-weight:700}
@page{size:A4;margin:0}
@media print{body{background:#fff}.page{box-shadow:none;margin:0}}
"""


def _escape_html(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _bold_to_html(text: str) -> str:
    """Escape HTML then convert ``**...**`` to ``<strong>...</strong>``."""
    escaped = _escape_html(text)
    return _BOLD_RE.sub(lambda m: f"<strong>{m.group(1)}</strong>", escaped)


def render_html(data: dict | None) -> str:
    """Render a self-contained HTML document mirroring the reference layout."""
    if not isinstance(data, dict):
        data = {}

    full_name = _safe_str(data.get("full_name"))
    role_headline = _safe_str(data.get("role_headline"))
    role_subtitle = _safe_str(data.get("role_subtitle"))
    contact = data.get("contact") or {}
    online_links = _safe_list(data.get("online_links"))
    skill_groups = _safe_list(data.get("skill_groups"))
    languages = _safe_list(data.get("languages"))
    profile_summary = _safe_str(data.get("profile_summary"))
    leadership_highlights = [_safe_str(x) for x in _safe_list(data.get("leadership_highlights")) if _safe_str(x)]
    experience = _safe_list(data.get("experience"))
    projects = _safe_list(data.get("projects"))
    education = _safe_list(data.get("education"))
    certifications = _safe_list(data.get("certifications"))

    sidebar_parts: list[str] = []
    sidebar_parts.append(f"<h1>{_escape_html(full_name)}</h1>")
    if role_headline or role_subtitle:
        role_html = _escape_html(role_headline)
        if role_subtitle:
            role_html += f"<span class='role-sub'>{_escape_html(role_subtitle)}</span>"
        sidebar_parts.append(f"<div class='role'>{role_html}</div>")

    location = _safe_str(contact.get("location") if isinstance(contact, dict) else "")
    email = _safe_str(contact.get("email") if isinstance(contact, dict) else "")
    phone = _safe_str(contact.get("phone") if isinstance(contact, dict) else "")
    contact_html: list[str] = []
    if location:
        contact_html.append(
            f"<div class='contact-line'><span class='ic'>@</span><span>{_escape_html(location)}</span></div>"
        )
    if email:
        contact_html.append(
            f"<div class='contact-line'><span class='ic'>&#9993;</span><span>{_escape_html(email)}</span></div>"
        )
    if phone:
        contact_html.append(
            f"<div class='contact-line'><span class='ic'>&#9742;</span><span>{_escape_html(phone)}</span></div>"
        )
    if contact_html:
        sidebar_parts.append("<div class='sb-section'><h3>Contact</h3>" + "".join(contact_html) + "</div>")

    online_html: list[str] = []
    for link in online_links:
        if not isinstance(link, dict):
            continue
        label = _safe_str(link.get("label")) or _safe_str(link.get("url"))
        url = _safe_str(link.get("url"))
        icon = _safe_str(link.get("icon")) or "&#8226;"
        if not label:
            continue
        if url:
            online_html.append(
                f"<div class='contact-line'><span class='ic'>{_escape_html(icon)}</span>"
                f"<a href='{_escape_html(url)}'>{_escape_html(label)}</a></div>"
            )
        else:
            online_html.append(
                f"<div class='contact-line'><span class='ic'>{_escape_html(icon)}</span>"
                f"<span>{_escape_html(label)}</span></div>"
            )
    if online_html:
        sidebar_parts.append("<div class='sb-section'><h3>Online</h3>" + "".join(online_html) + "</div>")

    skills_html: list[str] = []
    for group in skill_groups:
        if not isinstance(group, dict):
            continue
        label = _safe_str(group.get("label"))
        tags = [_safe_str(t) for t in _safe_list(group.get("tags")) if _safe_str(t)]
        if not (label and tags):
            continue
        tag_html = "".join(f"<span class='skill-tag'>{_escape_html(t)}</span>" for t in tags)
        skills_html.append(
            "<div class='skill-group'>"
            f"<div class='group-label'>{_escape_html(label)}</div>"
            f"<div class='skill-tags'>{tag_html}</div>"
            "</div>"
        )
    if skills_html:
        sidebar_parts.append(
            "<div class='sb-section'><h3>Tech Stack</h3>" + "".join(skills_html) + "</div>"
        )

    languages_html: list[str] = []
    for entry in languages:
        if not isinstance(entry, dict):
            continue
        name = _safe_str(entry.get("name"))
        level = _safe_str(entry.get("level"))
        if not name:
            continue
        languages_html.append(
            f"<div class='lang-row'><span>{_escape_html(name)}</span>"
            f"<span class='lvl'>{_escape_html(level)}</span></div>"
        )
    if languages_html:
        sidebar_parts.append(
            "<div class='sb-section'><h3>Languages</h3>" + "".join(languages_html) + "</div>"
        )

    main_parts: list[str] = []
    main_parts.append("<h2>Profile</h2>")
    if profile_summary:
        main_parts.append(f"<p class='summary'>{_bold_to_html(profile_summary)}</p>")

    if leadership_highlights:
        items_html = "".join(
            f"<div>&bull; {_bold_to_html(item)}</div>" for item in leadership_highlights
        )
        main_parts.append(
            "<div class='leadership-banner'>"
            "<div class='lb-title'>Leadership Highlights</div>"
            f"<div class='lb-list'>{items_html}</div>"
            "</div>"
        )

    if experience:
        main_parts.append("<h2>Work Experience</h2>")
        for entry in experience:
            if not isinstance(entry, dict):
                continue
            role = _escape_html(_safe_str(entry.get("role")))
            period = _escape_html(_safe_str(entry.get("period")))
            company = _escape_html(_safe_str(entry.get("company")))
            context = _escape_html(_safe_str(entry.get("context")))
            pills = [_safe_str(p) for p in _safe_list(entry.get("highlight_pills")) if _safe_str(p)]
            bullets = [_safe_str(b) for b in _safe_list(entry.get("bullets")) if _safe_str(b)]
            pill_html = "".join(
                f"<span class='highlight-pill'>{_escape_html(p)}</span>" for p in pills
            )
            bullet_html = "".join(f"<li>{_bold_to_html(b)}</li>" for b in bullets)
            main_parts.append(
                "<div class='job'>"
                f"<div class='job-header'><div class='job-title'>{role}</div>"
                f"<div class='job-period'>{period}</div></div>"
                f"<div class='job-company'>{company}"
                + (f" <span class='ctx'>{context}</span>" if context else "")
                + "</div>"
                + (f"<div class='highlight-row'>{pill_html}</div>" if pill_html else "")
                + (f"<ul>{bullet_html}</ul>" if bullet_html else "")
                + "</div>"
            )

    if projects:
        main_parts.append("<h2>Personal Projects</h2>")
        for entry in projects:
            if not isinstance(entry, dict):
                continue
            name = _escape_html(_safe_str(entry.get("name")))
            url = _escape_html(_safe_str(entry.get("url")))
            description = _bold_to_html(_safe_str(entry.get("description")))
            link_html = f' <a href="{url}">{url}</a>' if url else ""
            main_parts.append(
                "<div class='project-card'>"
                f"<div class='pname'>{name}</div>"
                f"<div class='pdesc'>{description}{link_html}</div>"
                "</div>"
            )

    if education:
        main_parts.append("<h2>Education</h2>")
        for entry in education:
            if not isinstance(entry, dict):
                continue
            title = _escape_html(_safe_str(entry.get("title")))
            sub = _escape_html(_safe_str(entry.get("sub")))
            period = _escape_html(_safe_str(entry.get("period")))
            main_parts.append(
                "<div class='edu-row'>"
                f"<div class='top'><span>{title}</span><span class='job-period'>{period}</span></div>"
                f"<div class='sub'>{sub}</div>"
                "</div>"
            )

    if certifications:
        main_parts.append("<h2>Certifications &amp; Courses</h2>")
        cert_items: list[str] = []
        for entry in certifications:
            if not isinstance(entry, dict):
                continue
            year = _escape_html(_safe_str(entry.get("year")))
            text = _bold_to_html(_safe_str(entry.get("text")))
            cert_items.append(
                f"<div class='cert-item'><span class='y'>{year}</span> {text}</div>"
            )
        if cert_items:
            main_parts.append("<div class='cert-list'>" + "".join(cert_items) + "</div>")

    title_for_doc = _safe_str(full_name) or "Modern CV"
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n<head>\n"
        "<meta charset=\"UTF-8\" />\n"
        f"<title>{_escape_html(title_for_doc)} - Modern CV</title>\n"
        f"<style>{_HTML_CSS}</style>\n"
        "</head>\n<body>\n"
        "<div class='page'>\n"
        f"<aside class='sidebar'>{''.join(sidebar_parts)}</aside>\n"
        f"<main class='main'>{''.join(main_parts)}</main>\n"
        "</div>\n"
        "</body>\n</html>\n"
    )


# --- PDF export -------------------------------------------------------------


def _bold_to_rl(text: str) -> str:
    """Convert ``**...**`` to reportlab ``<b>...</b>`` while escaping HTML."""
    escaped = _escape_html(text)
    return _BOLD_RE.sub(lambda m: f"<b>{m.group(1)}</b>", escaped)


def render_pdf(data: dict | None, target: Path) -> Path:
    """Two-column reportlab PDF render of the Modern CV payload."""
    try:
        from reportlab.lib.colors import HexColor, white  # type: ignore[import-not-found]
        from reportlab.lib.pagesizes import A4  # type: ignore[import-not-found]
        from reportlab.lib.styles import ParagraphStyle  # type: ignore[import-not-found]
        from reportlab.lib.units import mm  # type: ignore[import-not-found]
        from reportlab.platypus import (  # type: ignore[import-not-found]
            BaseDocTemplate,
            Frame,
            KeepInFrame,
            PageTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise RuntimeError(
            "reportlab not installed - run pip install -r requirements.txt"
        ) from exc

    if not isinstance(data, dict):
        data = {}

    teal_900 = HexColor(_TEAL_900)
    teal_700 = HexColor(_TEAL_700)
    teal_500 = HexColor(_TEAL_500)
    teal_50 = HexColor(_TEAL_50)
    sidebar_light = HexColor(_SIDEBAR_LIGHT)
    sidebar_body = HexColor(_SIDEBAR_BODY)
    ink_900 = HexColor(_INK_900)
    ink_700 = HexColor(_INK_700)
    ink_500 = HexColor(_INK_500)

    sidebar_width = 65 * mm

    # --- styles ---------------------------------------------------------
    sb_name = ParagraphStyle(
        "sb_name",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=20,
        textColor=white,
        spaceAfter=2,
    )
    sb_role = ParagraphStyle(
        "sb_role",
        fontName="Helvetica",
        fontSize=10,
        leading=12,
        textColor=teal_50,
        spaceAfter=10,
    )
    sb_h3 = ParagraphStyle(
        "sb_h3",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=sidebar_light,
        spaceBefore=8,
        spaceAfter=4,
    )
    sb_p = ParagraphStyle(
        "sb_p",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=white,
        spaceAfter=2,
    )
    sb_p_body = ParagraphStyle(
        "sb_p_body",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=sidebar_body,
        spaceAfter=2,
    )
    sb_skill_label = ParagraphStyle(
        "sb_skill_label",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=sidebar_light,
        spaceBefore=4,
        spaceAfter=2,
    )
    sb_skill_tags = ParagraphStyle(
        "sb_skill_tags",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=white,
        spaceAfter=4,
    )

    main_h2 = ParagraphStyle(
        "main_h2",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=teal_900,
        spaceBefore=10,
        spaceAfter=6,
    )
    summary = ParagraphStyle(
        "summary",
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=ink_700,
        spaceAfter=8,
    )
    leadership_title = ParagraphStyle(
        "leadership_title",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=teal_900,
        spaceAfter=4,
    )
    leadership_item = ParagraphStyle(
        "leadership_item",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=ink_700,
        spaceAfter=2,
    )
    job_role = ParagraphStyle(
        "job_role",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=ink_900,
        spaceAfter=1,
    )
    job_period = ParagraphStyle(
        "job_period",
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=ink_500,
        alignment=2,
    )
    job_company = ParagraphStyle(
        "job_company",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=teal_700,
        spaceAfter=2,
    )
    job_pill = ParagraphStyle(
        "job_pill",
        fontName="Helvetica",
        fontSize=8.5,
        leading=10,
        textColor=teal_900,
        spaceAfter=2,
    )
    job_bullet = ParagraphStyle(
        "job_bullet",
        fontName="Helvetica",
        fontSize=9.5,
        leading=12.5,
        textColor=ink_700,
        leftIndent=10,
        bulletIndent=0,
        spaceAfter=2,
    )
    project_name = ParagraphStyle(
        "project_name",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=ink_900,
        spaceAfter=1,
    )
    project_desc = ParagraphStyle(
        "project_desc",
        fontName="Helvetica",
        fontSize=9.5,
        leading=12.5,
        textColor=ink_700,
        spaceAfter=4,
        leftIndent=6,
    )
    edu_title = ParagraphStyle(
        "edu_title",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=ink_900,
        spaceAfter=1,
    )
    edu_sub = ParagraphStyle(
        "edu_sub",
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=11,
        textColor=ink_500,
        spaceAfter=4,
    )
    cert_line = ParagraphStyle(
        "cert_line",
        fontName="Helvetica",
        fontSize=9.5,
        leading=12,
        textColor=ink_700,
        spaceAfter=2,
    )

    # --- build flowables for each column --------------------------------
    sidebar_flow: list = []
    sidebar_flow.append(Paragraph(_escape_html(_safe_str(data.get("full_name"))), sb_name))
    role_html = _escape_html(_safe_str(data.get("role_headline")))
    role_sub = _safe_str(data.get("role_subtitle"))
    if role_sub:
        role_html += f"<br/><font color='{_SIDEBAR_LIGHT}' size='8'>{_escape_html(role_sub)}</font>"
    if role_html:
        sidebar_flow.append(Paragraph(role_html, sb_role))

    contact = data.get("contact") or {}
    location = _safe_str(contact.get("location") if isinstance(contact, dict) else "")
    email = _safe_str(contact.get("email") if isinstance(contact, dict) else "")
    phone = _safe_str(contact.get("phone") if isinstance(contact, dict) else "")
    if location or email or phone:
        sidebar_flow.append(Paragraph("CONTACT", sb_h3))
        if location:
            sidebar_flow.append(Paragraph(_escape_html(location), sb_p))
        if email:
            sidebar_flow.append(Paragraph(_escape_html(email), sb_p))
        if phone:
            sidebar_flow.append(Paragraph(_escape_html(phone), sb_p))

    online_links = _safe_list(data.get("online_links"))
    if online_links:
        sidebar_flow.append(Paragraph("ONLINE", sb_h3))
        for link in online_links:
            if not isinstance(link, dict):
                continue
            label = _safe_str(link.get("label")) or _safe_str(link.get("url"))
            url = _safe_str(link.get("url"))
            if not label:
                continue
            if url:
                sidebar_flow.append(
                    Paragraph(f"<link href='{_escape_html(url)}'>{_escape_html(label)}</link>", sb_p)
                )
            else:
                sidebar_flow.append(Paragraph(_escape_html(label), sb_p))

    skill_groups = _safe_list(data.get("skill_groups"))
    if skill_groups:
        sidebar_flow.append(Paragraph("TECH STACK", sb_h3))
        for group in skill_groups:
            if not isinstance(group, dict):
                continue
            label = _safe_str(group.get("label"))
            tags = [_safe_str(t) for t in _safe_list(group.get("tags")) if _safe_str(t)]
            if not (label and tags):
                continue
            sidebar_flow.append(Paragraph(_escape_html(label.upper()), sb_skill_label))
            sidebar_flow.append(
                Paragraph(_escape_html(" · ".join(tags)), sb_skill_tags)
            )

    languages = _safe_list(data.get("languages"))
    if languages:
        sidebar_flow.append(Paragraph("LANGUAGES", sb_h3))
        for entry in languages:
            if not isinstance(entry, dict):
                continue
            name = _safe_str(entry.get("name"))
            level = _safe_str(entry.get("level"))
            if not name:
                continue
            sidebar_flow.append(
                Paragraph(
                    f"{_escape_html(name)} <font color='{_SIDEBAR_LIGHT}'>· {_escape_html(level)}</font>",
                    sb_p,
                )
            )

    main_flow: list = []
    main_flow.append(Paragraph("PROFILE", main_h2))
    profile_summary = _safe_str(data.get("profile_summary"))
    if profile_summary:
        main_flow.append(Paragraph(_bold_to_rl(profile_summary), summary))

    leadership = [_safe_str(x) for x in _safe_list(data.get("leadership_highlights")) if _safe_str(x)]
    if leadership:
        leadership_block: list = [Paragraph("LEADERSHIP HIGHLIGHTS", leadership_title)]
        for item in leadership:
            leadership_block.append(
                Paragraph(f"&#9679; {_bold_to_rl(item)}", leadership_item)
            )
        # Wrap in a Table to get the teal-tinted background + accent bar.
        banner = Table(
            [[leadership_block]],
            colWidths=[125 * mm],
        )
        banner.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), teal_50),
                    ("LINEBEFORE", (0, 0), (-1, -1), 2.4, teal_500),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        main_flow.append(banner)
        main_flow.append(Spacer(1, 8))

    experience = _safe_list(data.get("experience"))
    if experience:
        main_flow.append(Paragraph("WORK EXPERIENCE", main_h2))
        for entry in experience:
            if not isinstance(entry, dict):
                continue
            role = _safe_str(entry.get("role"))
            period = _safe_str(entry.get("period"))
            company = _safe_str(entry.get("company"))
            context = _safe_str(entry.get("context"))
            pills = [_safe_str(p) for p in _safe_list(entry.get("highlight_pills")) if _safe_str(p)]
            bullets = [_safe_str(b) for b in _safe_list(entry.get("bullets")) if _safe_str(b)]

            header_table = Table(
                [
                    [
                        Paragraph(_escape_html(role), job_role),
                        Paragraph(_escape_html(period), job_period),
                    ]
                ],
                colWidths=[None, 35 * mm],
            )
            header_table.setStyle(
                TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)])
            )
            main_flow.append(header_table)
            if company or context:
                ctx_html = (
                    f" <font color='{_INK_500}'><i>{_escape_html(context)}</i></font>"
                    if context
                    else ""
                )
                main_flow.append(Paragraph(f"{_escape_html(company)}{ctx_html}", job_company))
            if pills:
                main_flow.append(
                    Paragraph(
                        " &nbsp; ".join(f"<b>{_escape_html(p)}</b>" for p in pills),
                        job_pill,
                    )
                )
            for bullet in bullets:
                main_flow.append(
                    Paragraph(f"&#9656; {_bold_to_rl(bullet)}", job_bullet)
                )
            main_flow.append(Spacer(1, 6))

    projects = _safe_list(data.get("projects"))
    if projects:
        main_flow.append(Paragraph("PERSONAL PROJECTS", main_h2))
        for entry in projects:
            if not isinstance(entry, dict):
                continue
            name = _safe_str(entry.get("name"))
            description = _safe_str(entry.get("description"))
            url = _safe_str(entry.get("url"))
            if name:
                main_flow.append(Paragraph(_escape_html(name), project_name))
            if description:
                desc_html = _bold_to_rl(description)
                if url:
                    desc_html += (
                        f" <link href='{_escape_html(url)}'>"
                        f"<font color='{_TEAL_700}'>{_escape_html(url)}</font></link>"
                    )
                main_flow.append(Paragraph(desc_html, project_desc))

    education = _safe_list(data.get("education"))
    if education:
        main_flow.append(Paragraph("EDUCATION", main_h2))
        for entry in education:
            if not isinstance(entry, dict):
                continue
            title = _safe_str(entry.get("title"))
            sub = _safe_str(entry.get("sub"))
            period = _safe_str(entry.get("period"))
            top_table = Table(
                [
                    [
                        Paragraph(_escape_html(title), edu_title),
                        Paragraph(_escape_html(period), job_period),
                    ]
                ],
                colWidths=[None, 35 * mm],
            )
            top_table.setStyle(
                TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)])
            )
            main_flow.append(top_table)
            if sub:
                main_flow.append(Paragraph(_escape_html(sub), edu_sub))

    certifications = _safe_list(data.get("certifications"))
    if certifications:
        main_flow.append(Paragraph("CERTIFICATIONS &amp; COURSES", main_h2))
        for entry in certifications:
            if not isinstance(entry, dict):
                continue
            year = _safe_str(entry.get("year"))
            text = _safe_str(entry.get("text"))
            line = (
                f"<font color='{_TEAL_700}'><b>{_escape_html(year)}</b></font> "
                + _bold_to_rl(text)
            )
            main_flow.append(Paragraph(line, cert_line))

    # --- compose two-column page ---------------------------------------
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(target),
        pagesize=A4,
        leftMargin=0,
        rightMargin=0,
        topMargin=0,
        bottomMargin=0,
        title=_safe_str(data.get("full_name")) or "Modern CV",
    )

    page_width, page_height = A4

    sidebar_frame = Frame(
        x1=0,
        y1=0,
        width=sidebar_width,
        height=page_height,
        leftPadding=12 * mm,
        rightPadding=8 * mm,
        topPadding=14 * mm,
        bottomPadding=12 * mm,
        showBoundary=0,
        id="sidebar",
    )
    main_frame = Frame(
        x1=sidebar_width,
        y1=0,
        width=page_width - sidebar_width,
        height=page_height,
        leftPadding=10 * mm,
        rightPadding=12 * mm,
        topPadding=14 * mm,
        bottomPadding=12 * mm,
        showBoundary=0,
        id="main",
    )

    def _draw_background(canvas, _doc) -> None:
        canvas.saveState()
        # Sidebar gradient (approximated with a filled rect in teal_900;
        # reportlab linearGradient is heavier than what we need here).
        canvas.setFillColor(teal_900)
        canvas.rect(0, 0, sidebar_width, page_height, fill=1, stroke=0)
        # Subtle bottom-half tint to hint at the linear gradient.
        canvas.setFillColor(teal_700)
        canvas.rect(0, 0, sidebar_width, page_height * 0.35, fill=1, stroke=0)
        canvas.restoreState()

    template = PageTemplate(
        id="two_col",
        frames=[sidebar_frame, main_frame],
        onPage=_draw_background,
    )
    doc.addPageTemplates([template])

    # KeepInFrame protects each column from overflow; if the user crams
    # the CV with content the height shrinks to fit instead of throwing.
    flowables = [
        KeepInFrame(sidebar_width, page_height, sidebar_flow, mode="shrink"),
        KeepInFrame(page_width - sidebar_width, page_height, main_flow, mode="shrink"),
    ]
    doc.build(flowables)
    return target
