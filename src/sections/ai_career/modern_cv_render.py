"""Two-column "modern CV" renderer driven by ``MODERN_CV_SCHEMA`` JSON.

Three render targets share one payload:

* :func:`render_view` - a Flet control tree painted in the Documents
  tab preview. Pulls colours from the active palette in
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
render target. No other markdown is supported - the payload's fields
are short and structured by design.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

import flet as ft

from src.sections.ai_career import themes
from src.sections.ai_career.state import STATE
from src.theme import Theme


# --- shared helpers ---------------------------------------------------------


_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _split_bold(text: str) -> list[tuple[str, bool]]:
    """Split ``text`` into ``(chunk, is_bold)`` runs."""
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


def _active_theme() -> themes.ResumeTheme:
    """Resolve the user's active palette + layout into a :class:`ResumeTheme`."""
    state_theme = getattr(STATE, "modern_cv_theme", None) or {}
    palette = (state_theme.get("palette") or "").strip().lower()
    layout = (state_theme.get("layout") or "").strip().lower()
    return themes.resolve_theme(palette, layout)


# --- in-app Flet view -------------------------------------------------------


def _sidebar_section_title(text: str, *, accent_soft: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            text.upper(),
            color=accent_soft,
            size=10,
            weight=ft.FontWeight.W_700,
            style=ft.TextStyle(letter_spacing=1.6),
        ),
        padding=ft.padding.only(bottom=4),
        border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.35, accent_soft))),
        margin=ft.margin.only(bottom=8),
    )


def _sidebar_contact_row(icon: str, text: str, *, accent_soft: str) -> ft.Row:
    return ft.Row(
        controls=[
            ft.Container(
                content=ft.Text(icon, color=accent_soft, size=11, weight=ft.FontWeight.W_700),
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


def _sidebar_block(title: str, body_controls: Iterable[ft.Control], *, accent_soft: str) -> ft.Container:
    children: list[ft.Control] = [_sidebar_section_title(title, accent_soft=accent_soft)]
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


def _highlight_pill(label: str, *, accent: str, accent_soft: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(label, color=accent, size=10.5, weight=ft.FontWeight.W_600),
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        bgcolor=ft.Colors.with_opacity(0.14, accent),
        border=ft.border.all(1, accent_soft),
        border_radius=6,
    )


def _section_heading(text: str, *, accent: str, rule: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            text.upper(),
            color=accent,
            size=12,
            weight=ft.FontWeight.W_800,
            style=ft.TextStyle(letter_spacing=1.6),
        ),
        padding=ft.padding.only(bottom=4),
        border=ft.border.only(bottom=ft.BorderSide(2, rule)),
        margin=ft.margin.only(top=18, bottom=10),
    )


def _bullet_row(text: str, *, ink_700: str, ink_900: str, rule: str) -> ft.Row:
    return ft.Row(
        controls=[
            ft.Container(
                content=ft.Text("\u25B8", color=rule, size=11, weight=ft.FontWeight.W_700),
                width=14,
                padding=ft.padding.only(top=1),
            ),
            _rich_text(
                text,
                color=ink_700,
                size=11,
                bold_color=ink_900,
                bold_weight=ft.FontWeight.W_600,
            ),
        ],
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.START,
        expand=False,
    )


def _job_card(entry: dict, *, accent: str, accent_dark: str, rule: str, ink_900: str, ink_700: str, ink_500: str, accent_soft: str) -> ft.Container:
    role = _safe_str(entry.get("role"))
    period = _safe_str(entry.get("period"))
    company = _safe_str(entry.get("company"))
    context = _safe_str(entry.get("context"))
    pills = [_safe_str(p) for p in _safe_list(entry.get("highlight_pills")) if _safe_str(p)]
    bullets = [_safe_str(b) for b in _safe_list(entry.get("bullets")) if _safe_str(b)]

    children: list[ft.Control] = [
        ft.Row(
            controls=[
                ft.Text(role, color=ink_900, size=12.5, weight=ft.FontWeight.W_700, expand=True),
                ft.Text(period, color=ink_500, size=11, weight=ft.FontWeight.W_500),
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
                ft.TextStyle(color=accent_dark, size=11, weight=ft.FontWeight.W_600),
            )
        )
    if context:
        sep = " "
        company_line.append(
            ft.TextSpan(
                f"{sep}{context}",
                ft.TextStyle(color=ink_500, size=11, weight=ft.FontWeight.W_400, italic=True),
            )
        )
    if company_line:
        children.append(ft.Text("", spans=company_line, selectable=True))

    if pills:
        children.append(
            ft.Row(
                controls=[_highlight_pill(p, accent=accent_dark, accent_soft=accent_soft) for p in pills],
                spacing=6,
                run_spacing=6,
                wrap=True,
            )
        )

    if bullets:
        children.append(
            ft.Column(
                controls=[
                    _bullet_row(b, ink_700=ink_700, ink_900=ink_900, rule=rule)
                    for b in bullets
                ],
                spacing=4,
                tight=True,
            )
        )

    return ft.Container(
        content=ft.Column(controls=children, spacing=4, tight=True),
        margin=ft.margin.only(bottom=14),
    )


def _project_card(entry: dict, *, accent: str, accent_dark: str, rule: str, ink_700: str, ink_900: str) -> ft.Container:
    name = _safe_str(entry.get("name"))
    desc = _safe_str(entry.get("description"))
    url = _safe_str(entry.get("url"))

    children: list[ft.Control] = []
    if name:
        children.append(ft.Text(name, color=ink_900, size=12, weight=ft.FontWeight.W_700))
    if desc:
        children.append(
            _rich_text(
                desc,
                color=ink_700,
                size=11,
                bold_color=ink_900,
                bold_weight=ft.FontWeight.W_600,
            )
        )
    if url:
        children.append(
            ft.Text(
                url,
                color=accent_dark,
                size=10.5,
                weight=ft.FontWeight.W_500,
                selectable=True,
            )
        )

    return ft.Container(
        content=ft.Column(controls=children, spacing=3, tight=True),
        padding=ft.padding.only(left=8),
        border=ft.border.only(left=ft.BorderSide(3, rule)),
        margin=ft.margin.only(bottom=10),
    )


def _edu_row(entry: dict, *, ink_900: str, ink_500: str) -> ft.Container:
    title = _safe_str(entry.get("title"))
    sub = _safe_str(entry.get("sub"))
    period = _safe_str(entry.get("period"))
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(title, color=ink_900, size=11.5, weight=ft.FontWeight.W_600, expand=True),
                        ft.Text(period, color=ink_500, size=10.5, weight=ft.FontWeight.W_500),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                ft.Text(sub, color=ink_500, size=11, italic=True, selectable=True),
            ],
            spacing=2,
            tight=True,
        ),
        margin=ft.margin.only(bottom=8),
    )


def _cert_item(entry: dict, *, accent_dark: str, ink_700: str, ink_900: str) -> ft.Row:
    year = _safe_str(entry.get("year"))
    text = _safe_str(entry.get("text"))
    children: list[ft.Control] = []
    if year:
        children.append(
            ft.Text(year, color=accent_dark, size=11, weight=ft.FontWeight.W_700)
        )
    children.append(
        _rich_text(
            text,
            color=ink_700,
            size=11,
            bold_color=ink_900,
            bold_weight=ft.FontWeight.W_600,
        )
    )
    return ft.Row(
        controls=children,
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def _leadership_banner(items: list[str], *, accent: str, accent_dark: str, rule: str, ink_700: str) -> ft.Container:
    rows: list[ft.Control] = []
    for item in items:
        rows.append(
            ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Text("\u25CF", color=rule, size=10, weight=ft.FontWeight.W_700),
                        width=12,
                        padding=ft.padding.only(top=1),
                    ),
                    _rich_text(
                        item,
                        color=ink_700,
                        size=11,
                        bold_color=accent_dark,
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
                    color=accent_dark,
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
        bgcolor=ft.Colors.with_opacity(0.10, accent),
        border=ft.border.only(left=ft.BorderSide(4, rule)),
        border_radius=6,
        margin=ft.margin.only(top=10, bottom=14),
    )


# Preview paper dimensions. Approximates an A4 sheet at ~3.4 px / mm so
# the in-app preview reads like the printed PDF without overflowing the
# Documents tab body. The fixed height is what FIXES THE 0-HEIGHT BUG -
# a ListView gives its children their natural height, so without an
# explicit height the paper container collapses to 0 and the user sees
# a black slab.
_PAPER_WIDTH = 720
_PAPER_HEIGHT = 1018  # ~_PAPER_WIDTH * 1.414 (A4 ratio)


def render_view(theme: Theme, data: dict | None) -> ft.Control:
    """Render the Modern CV payload as a themed two-column Flet preview.

    The preview reads colours from :data:`STATE.modern_cv_theme` so the
    Documents tab's ``Change colour`` cycle button can re-render the
    paper in the next palette without rebuilding the surrounding
    section.
    """
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

    # ---------- sidebar (left column) -----------------------------------
    sidebar_children: list[ft.Control] = [
        ft.Text(full_name, color=ft.Colors.WHITE, size=22, weight=ft.FontWeight.W_800),
    ]
    if role_headline:
        sidebar_children.append(
            ft.Text(role_headline, color=accent_soft, size=11.5, weight=ft.FontWeight.W_500)
        )
    if role_subtitle:
        sidebar_children.append(
            ft.Text(role_subtitle, color=accent_soft, size=10.5, weight=ft.FontWeight.W_400)
        )

    contact_rows: list[ft.Control] = []
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
        sidebar_children.append(_sidebar_block("Contact", contact_rows, accent_soft=accent_soft))

    if online_links:
        link_rows: list[ft.Control] = []
        for link in online_links:
            if not isinstance(link, dict):
                continue
            label = _safe_str(link.get("label")) or _safe_str(link.get("url"))
            icon = _safe_str(link.get("icon")) or "\u2022"
            if not label:
                continue
            link_rows.append(_sidebar_contact_row(icon, label, accent_soft=accent_soft))
        if link_rows:
            sidebar_children.append(_sidebar_block("Online", link_rows, accent_soft=accent_soft))

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
                                color=accent_soft,
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
            sidebar_children.append(
                _sidebar_block("Tech Stack", skill_blocks, accent_soft=accent_soft)
            )

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
                        ft.Text(level, color=accent_soft, size=10.5, weight=ft.FontWeight.W_600),
                    ],
                    spacing=8,
                )
            )
        if lang_rows:
            sidebar_children.append(
                _sidebar_block("Languages", lang_rows, accent_soft=accent_soft)
            )

    sidebar = ft.Container(
        content=ft.Column(
            controls=sidebar_children,
            spacing=4,
            tight=True,
            scroll=ft.ScrollMode.AUTO,
        ),
        bgcolor=accent,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_CENTER,
            end=ft.Alignment.BOTTOM_CENTER,
            colors=[accent, accent_dark],
        ),
        padding=ft.padding.symmetric(horizontal=20, vertical=22),
        width=240,
        height=_PAPER_HEIGHT,
    )

    # ---------- main column ---------------------------------------------
    main_children: list[ft.Control] = []
    main_children.append(_section_heading("Profile", accent=accent, rule=rule))
    if profile_summary:
        main_children.append(
            _rich_text(
                profile_summary,
                color=ink_700,
                size=11.5,
                bold_color=ink_900,
                bold_weight=ft.FontWeight.W_600,
            )
        )
    if leadership_highlights:
        main_children.append(
            _leadership_banner(
                leadership_highlights,
                accent=accent,
                accent_dark=accent_dark,
                rule=rule,
                ink_700=ink_700,
            )
        )

    if experience:
        main_children.append(_section_heading("Work Experience", accent=accent, rule=rule))
        for entry in experience:
            if isinstance(entry, dict):
                main_children.append(
                    _job_card(
                        entry,
                        accent=accent,
                        accent_dark=accent_dark,
                        rule=rule,
                        ink_900=ink_900,
                        ink_700=ink_700,
                        ink_500=ink_500,
                        accent_soft=accent_soft,
                    )
                )

    if projects:
        main_children.append(_section_heading("Projects", accent=accent, rule=rule))
        for entry in projects:
            if isinstance(entry, dict):
                main_children.append(
                    _project_card(
                        entry,
                        accent=accent,
                        accent_dark=accent_dark,
                        rule=rule,
                        ink_700=ink_700,
                        ink_900=ink_900,
                    )
                )

    if education:
        main_children.append(_section_heading("Education", accent=accent, rule=rule))
        for entry in education:
            if isinstance(entry, dict):
                main_children.append(_edu_row(entry, ink_900=ink_900, ink_500=ink_500))

    if certifications:
        main_children.append(_section_heading("Certifications & Courses", accent=accent, rule=rule))
        for entry in certifications:
            if isinstance(entry, dict):
                main_children.append(
                    _cert_item(entry, accent_dark=accent_dark, ink_700=ink_700, ink_900=ink_900)
                )

    main_column = ft.Container(
        content=ft.Column(
            controls=main_children,
            spacing=4,
            tight=True,
            scroll=ft.ScrollMode.AUTO,
        ),
        bgcolor=paper,
        padding=ft.padding.symmetric(horizontal=24, vertical=22),
        expand=True,
        height=_PAPER_HEIGHT,
    )

    # The paper has explicit width + height so the ListView wrapper in
    # tab_documents has something to size against - without this the
    # body collapses to 0 height (the bug the user reported as "Modern
    # CV preview shows a black square").
    paper_card = ft.Container(
        content=ft.Row(
            controls=[sidebar, main_column],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        bgcolor=paper,
        border_radius=6,
        width=_PAPER_WIDTH,
        height=_PAPER_HEIGHT,
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=18,
            color=ft.Colors.with_opacity(0.18, "#0F172A"),
            offset=ft.Offset(0, 6),
        ),
    )

    # Wrap the paper in a centring container with explicit height so the
    # whole assembly has a real intrinsic height inside the parent
    # ListView. ``alignment=TOP_CENTER`` keeps the paper centred when
    # the Documents tab is wider than _PAPER_WIDTH.
    return ft.Container(
        content=paper_card,
        alignment=ft.Alignment.TOP_CENTER,
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        height=_PAPER_HEIGHT + 24,
    )


# --- HTML export ------------------------------------------------------------


def render_html(data: dict | None, *, output_lang: str = "en") -> str:
    """Render a self-contained HTML document via the active theme.

    The HTML structure + CSS comes from the ported themes module so the
    in-app preview, the on-disk HTML, and the Playwright PDF all use
    the same palette + layout.
    """
    return themes.render_modern_cv_html(data or {}, _active_theme(), output_lang=output_lang)


# --- PDF export -------------------------------------------------------------


def render_pdf(data: dict | None, target: Path, *, output_lang: str = "en") -> Path:
    """Render the Modern CV to ``target`` as a Playwright A4 PDF."""
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
