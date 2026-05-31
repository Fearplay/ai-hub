"""Visual themes (palette + layout) for the Modern CV + Cover Letter HTML.

The user wants the exported documents to vary visually so they don't all
look identical, AND to follow the colour the user picked. This module is
the registry of those visual variants.

Two axes:

* **Palette** (eight choices: teal, burgundy, slate, forest, indigo,
  sunset, graphite, plum) - colour + typography only.
* **Layout** (four choices: ``two_column_sidebar``, ``single_column_serif``,
  ``single_column_minimal``, ``centered_header_band``) - structural
  CSS only.

A user-facing :class:`ResumeTheme` is the cross product of one palette
and one layout. The cycle buttons in the Documents tab call
:func:`pick_next_palette` / :func:`pick_next_layout` to rotate one axis
at a time so the user can change the colour without losing the layout
they liked, or vice-versa.

Public renderers:

* :func:`render_modern_cv_html` - drives the printable Modern CV from
  the existing ``MODERN_CV_SCHEMA`` payload (``STATE.modern_cv_data``).
* :func:`render_cover_letter_html` - wraps a cover-letter markdown body
  into a themed page with a coloured banner that picks up the active
  palette.

The renderers are deliberately self-contained (every CSS rule lives
inline in the returned HTML) so the file we hand to Playwright is
print-ready without external assets.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any, Iterable, Literal


# ---------------------------------------------------------------------------
# Palettes (colour + typography)
# ---------------------------------------------------------------------------
ThemeLayout = Literal[
    "two_column_sidebar",
    "single_column_serif",
    "single_column_minimal",
    "centered_header_band",
]


#: Layout slugs in display order. Used by :func:`pick_next_layout` to
#: walk the universe of layouts deterministically.
LAYOUTS: tuple[ThemeLayout, ...] = (
    "two_column_sidebar",
    "single_column_serif",
    "single_column_minimal",
    "centered_header_band",
)


@dataclass(frozen=True)
class Palette:
    """Colour + typography tokens used by every layout's CSS builder."""

    slug: str
    display_name_en: str
    display_name_cs: str
    accent: str          # primary accent (sidebar / banner / heading colour)
    accent_dark: str     # darker shade used for gradients / hover
    accent_soft: str     # tint used for chip backgrounds / pills
    on_accent: str       # text colour rendered on top of the accent
    text_primary: str    # main body text colour
    text_muted: str      # secondary text (period dates, captions)
    rule: str            # border / underline colour for section headings
    body_font: str       # CSS font-family stack for body text
    heading_font: str    # CSS font-family stack for headings


#: Eight palettes - same slugs as the applypilot-ai project so saved
#: runs can round-trip later if we share data between the two apps.
PALETTES: dict[str, Palette] = {
    "teal": Palette(
        slug="teal",
        display_name_en="Teal",
        display_name_cs="Teal",
        accent="#0E7490",
        accent_dark="#0F766E",
        accent_soft="#7DD3FC",
        on_accent="#FFFFFF",
        text_primary="#0F172A",
        text_muted="#64748B",
        rule="#14B8A6",
        body_font="'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif",
        heading_font="'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif",
    ),
    "burgundy": Palette(
        slug="burgundy",
        display_name_en="Burgundy",
        display_name_cs="Bordó",
        accent="#7F1D1D",
        accent_dark="#5B0F0F",
        accent_soft="#FECACA",
        on_accent="#FFFFFF",
        text_primary="#1F1A18",
        text_muted="#7B6F6A",
        rule="#B91C1C",
        body_font="'Source Sans 3','Segoe UI',Arial,sans-serif",
        heading_font="'Playfair Display','Georgia','Times New Roman',serif",
    ),
    "slate": Palette(
        slug="slate",
        display_name_en="Slate",
        display_name_cs="Břidlice",
        accent="#1E293B",
        accent_dark="#0F172A",
        accent_soft="#CBD5E1",
        on_accent="#FFFFFF",
        text_primary="#0F172A",
        text_muted="#64748B",
        rule="#475569",
        body_font="'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif",
        heading_font="'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif",
    ),
    "forest": Palette(
        slug="forest",
        display_name_en="Forest",
        display_name_cs="Lesní",
        accent="#065F46",
        accent_dark="#064E3B",
        accent_soft="#A7F3D0",
        on_accent="#FFFFFF",
        text_primary="#111827",
        text_muted="#4B5563",
        rule="#10B981",
        body_font="'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif",
        heading_font="'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif",
    ),
    "indigo": Palette(
        slug="indigo",
        display_name_en="Indigo",
        display_name_cs="Indigo",
        accent="#3730A3",
        accent_dark="#1E1B4B",
        accent_soft="#C7D2FE",
        on_accent="#FFFFFF",
        text_primary="#1F2937",
        text_muted="#6B7280",
        rule="#6366F1",
        body_font="'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif",
        heading_font="'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif",
    ),
    "sunset": Palette(
        slug="sunset",
        display_name_en="Sunset",
        display_name_cs="Západ slunce",
        accent="#C2410C",
        accent_dark="#9A3412",
        accent_soft="#FED7AA",
        on_accent="#FFFFFF",
        text_primary="#1F2937",
        text_muted="#57534E",
        rule="#F97316",
        body_font="'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif",
        heading_font="'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif",
    ),
    "graphite": Palette(
        slug="graphite",
        display_name_en="Graphite",
        display_name_cs="Grafit",
        accent="#374151",
        accent_dark="#1F2937",
        accent_soft="#D1D5DB",
        on_accent="#FFFFFF",
        text_primary="#111827",
        text_muted="#6B7280",
        rule="#4B5563",
        body_font="'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif",
        heading_font="'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif",
    ),
    "plum": Palette(
        slug="plum",
        display_name_en="Plum",
        display_name_cs="Švestka",
        accent="#6B21A8",
        accent_dark="#4C1D95",
        accent_soft="#E9D5FF",
        on_accent="#FFFFFF",
        text_primary="#1F1A24",
        text_muted="#6B5876",
        rule="#9333EA",
        body_font="'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif",
        heading_font="'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif",
    ),
}


#: Default identity used when the user has not picked anything yet. The
#: teal + two_column_sidebar pair preserves the original look the
#: section shipped with so existing screenshots still match.
DEFAULT_PALETTE = "teal"
DEFAULT_LAYOUT: ThemeLayout = "two_column_sidebar"


@dataclass(frozen=True)
class ResumeTheme:
    """Concrete (palette, layout) pair the renderers consume."""

    palette_slug: str
    layout_slug: ThemeLayout
    palette: Palette

    @property
    def accent(self) -> str:
        return self.palette.accent

    @property
    def accent_dark(self) -> str:
        return self.palette.accent_dark

    @property
    def accent_soft(self) -> str:
        return self.palette.accent_soft

    @property
    def on_accent(self) -> str:
        return self.palette.on_accent

    @property
    def text_primary(self) -> str:
        return self.palette.text_primary

    @property
    def text_muted(self) -> str:
        return self.palette.text_muted

    @property
    def rule(self) -> str:
        return self.palette.rule

    @property
    def body_font(self) -> str:
        return self.palette.body_font

    @property
    def heading_font(self) -> str:
        return self.palette.heading_font

    def display_name(self, lang: str) -> str:
        code = (lang or "en").strip().lower()
        if code == "cs":
            return self.palette.display_name_cs
        return self.palette.display_name_en


def resolve_theme(palette_slug: str | None, layout_slug: str | None) -> ResumeTheme:
    """Turn a stored ``(palette, layout)`` pair into a :class:`ResumeTheme`.

    Unknown slugs fall back to :data:`DEFAULT_PALETTE` / :data:`DEFAULT_LAYOUT`
    so opening a saved run with an out-of-date theme never crashes the
    renderer.
    """
    p_code = (palette_slug or "").strip().lower() or DEFAULT_PALETTE
    if p_code not in PALETTES:
        p_code = DEFAULT_PALETTE
    l_code = (layout_slug or "").strip().lower() or DEFAULT_LAYOUT
    if l_code not in LAYOUTS:
        l_code = DEFAULT_LAYOUT
    return ResumeTheme(
        palette_slug=p_code,
        layout_slug=l_code,  # type: ignore[arg-type]
        palette=PALETTES[p_code],
    )


def pick_next_palette(current: str | None) -> str:
    """Round-robin to the next palette slug after ``current``.

    Deterministic so ``Change colour`` feels predictable - the user can
    cycle forward to find the look they want without random surprises.
    """
    slugs = list(PALETTES.keys())
    if not slugs:
        return DEFAULT_PALETTE
    code = (current or "").strip().lower()
    if code not in PALETTES:
        return slugs[0]
    idx = slugs.index(code)
    return slugs[(idx + 1) % len(slugs)]


def pick_next_layout(current: str | None) -> ThemeLayout:
    """Round-robin to the next layout slug after ``current``."""
    slugs = list(LAYOUTS)
    if not slugs:
        return DEFAULT_LAYOUT
    code = (current or "").strip().lower()
    if code not in slugs:
        return slugs[0]
    idx = slugs.index(code)  # type: ignore[arg-type]
    return slugs[(idx + 1) % len(slugs)]


# ---------------------------------------------------------------------------
# Localised section labels
# ---------------------------------------------------------------------------
_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "profile": "Profile",
        "experience": "Work Experience",
        "projects": "Personal Projects",
        "education": "Education",
        "certifications": "Certifications & Courses",
        "contact": "Contact",
        "online": "Online",
        "tech_stack": "Tech Stack",
        "languages": "Languages",
        "leadership": "Leadership Highlights",
    },
    "cs": {
        "profile": "Profil",
        "experience": "Pracovní zkušenosti",
        "projects": "Vlastní projekty",
        "education": "Vzdělání",
        "certifications": "Certifikáty & kurzy",
        "contact": "Kontakt",
        "online": "Online",
        "tech_stack": "Technologie",
        "languages": "Jazyky",
        "leadership": "Klíčové úspěchy",
    },
}


def _labels(lang: str) -> dict[str, str]:
    code = (lang or "en").strip().lower()
    return _LABELS.get(code) or _LABELS["en"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _safe_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    return []


def _esc(text: str | None) -> str:
    return html.escape(text or "", quote=True)


def _bold_to_html(text: str | None) -> str:
    """Escape ``text`` then convert ``**...**`` to ``<strong>...</strong>``."""
    escaped = _esc(text)
    return _BOLD_RE.sub(lambda m: f"<strong>{m.group(1)}</strong>", escaped)


# ---------------------------------------------------------------------------
# Layout-specific CSS
# ---------------------------------------------------------------------------
# Page sizing + page-break rules shared by every layout. ``min-height`` on
# ``.page`` keeps each printed sheet at a full A4 height even when the
# CV is short - that way the sidebar / banner background extends to the
# bottom of the page rather than collapsing to content height.
_CSS_BASE_PAGE = """
*{box-sizing:border-box;margin:0;padding:0;-webkit-print-color-adjust:exact;print-color-adjust:exact}
@page{size:A4;margin:0}
::selection{background:#FDE68A;color:#0F172A}
@media print{
  html,body{background:#fff !important}
  .page{box-shadow:none !important;margin:0}
  .sidebar,.banner,.header,.summary,.leadership-banner,.highlight-pill,.skill-tag,.contact-bar,.skills-row,.skills-grid,.lang-list,.job ul li,section.block{-webkit-print-color-adjust:exact !important;print-color-adjust:exact !important}
  a[href]{text-decoration:underline}
}
.job,.project-card,.edu-row,.cert-item,.lang-row,.skill-group,.skills-row .group,.skills-grid .group,.lang-list .lang,section.block{break-inside:avoid;page-break-inside:avoid}
.job-header,.edu-row .top{break-inside:avoid;page-break-inside:avoid}
h1,h2,h3{break-after:avoid-page;page-break-after:avoid}
p,li{orphans:2;widows:2}
""".strip()


def _two_column_css(theme: ResumeTheme) -> str:
    """Classic teal-style sidebar layout, retuned to read from the active palette.

    The page background uses a tiled gradient on the .page element so
    multi-page CVs keep the sidebar stripe on every printed sheet
    (``repeat-y`` reseeds the gradient at every A4 boundary). The
    matching ``.bg-stripe`` element is print-only and pinned via
    ``position:fixed`` so the stripe also extends past the .page
    element on the last page when the right column is short.
    """
    return f"""
{_CSS_BASE_PAGE}
html,body{{font-family:{theme.body_font};color:{theme.text_primary};background:#F8FAFC;line-height:1.45;font-size:10.5pt}}
.bg-stripe{{display:none}}
@media print{{.bg-stripe{{display:block;position:fixed;top:0;left:50%;transform:translateX(-105mm);width:73mm;height:100vh;background:linear-gradient(180deg,{theme.accent} 0%,{theme.accent_dark} 50%,{theme.accent} 100%);-webkit-print-color-adjust:exact;print-color-adjust:exact;z-index:-1}}}}
.page{{max-width:210mm;min-height:297mm;margin:0 auto;box-shadow:0 8px 30px rgba(15,23,42,0.08);display:grid;grid-template-columns:73mm 1fr;align-items:stretch;background-color:#FFFFFF;background-image:linear-gradient(180deg,{theme.accent} 0%,{theme.accent_dark} 50%,{theme.accent} 100%);background-size:73mm 297mm;background-repeat:repeat-y;background-position:top left;position:relative}}
.sidebar{{color:{theme.on_accent};padding:14mm 9mm 12mm 9mm;position:relative;z-index:1}}
.sidebar h1{{font-family:{theme.heading_font};font-size:20pt;line-height:1.1;font-weight:800;letter-spacing:-0.02em;margin-bottom:3mm}}
.sidebar .role{{font-size:10.5pt;color:{theme.accent_soft};font-weight:500;margin-bottom:6mm;letter-spacing:0.02em}}
.sidebar .role-sub{{font-size:9pt;color:{theme.accent_soft};font-weight:400;display:block;margin-top:1mm;opacity:0.9}}
.sb-section{{margin-top:7mm}}
.sb-section h3{{font-size:9pt;text-transform:uppercase;letter-spacing:0.18em;font-weight:700;color:{theme.accent_soft};border-bottom:1px solid rgba(255,255,255,0.35);padding-bottom:1.5mm;margin-bottom:3mm}}
.sb-section p,.sb-section li{{font-size:9.5pt;color:rgba(255,255,255,0.92);margin-bottom:1.5mm;word-wrap:break-word}}
.sb-section a{{color:{theme.on_accent};text-decoration:none;border-bottom:1px dotted rgba(255,255,255,0.4)}}
.sb-section ul{{list-style:none}}
.sb-section .contact-line{{display:flex;align-items:center;gap:2.2mm;font-size:9pt;margin-bottom:1.8mm}}
.sb-section .contact-line .ic{{flex:0 0 5mm;color:{theme.accent_soft};font-weight:700;font-size:10.5pt;line-height:1}}
.skill-group{{margin-bottom:3.5mm}}
.skill-group .group-label{{font-size:8.5pt;color:{theme.accent_soft};font-weight:600;margin-bottom:1mm;text-transform:uppercase;letter-spacing:0.06em}}
.skill-tags{{display:flex;flex-wrap:wrap;gap:1.5mm}}
.skill-tag{{background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.2);padding:0.8mm 2mm;border-radius:2mm;font-size:8.5pt;color:{theme.on_accent}}}
.lang-row{{display:flex;justify-content:space-between;align-items:center;font-size:9.5pt;margin-bottom:1.5mm}}
.lang-row .lvl{{font-size:8.5pt;color:{theme.accent_soft};font-weight:600}}
.main{{padding:14mm 12mm 12mm 12mm;background:#FFFFFF;position:relative;z-index:1}}
.main h2{{font-family:{theme.heading_font};font-size:11pt;text-transform:uppercase;letter-spacing:0.16em;color:{theme.accent};font-weight:800;border-bottom:2px solid {theme.rule};padding-bottom:1.2mm;margin:0 0 4mm 0}}
.main h2:not(:first-child){{padding-top:8mm;margin-top:0}}
.summary{{font-size:10pt;color:{theme.text_primary};line-height:1.55}}
.summary strong{{color:{theme.text_primary};font-weight:700}}
.leadership-banner{{background:linear-gradient(90deg,rgba(0,0,0,0.04) 0%,rgba(0,0,0,0) 100%);border-left:4px solid {theme.rule};padding:3mm 4mm;margin:5mm 0 6mm 0;border-radius:0 2mm 2mm 0}}
.leadership-banner .lb-title{{font-size:9pt;color:{theme.accent_dark};font-weight:700;text-transform:uppercase;letter-spacing:0.12em;margin-bottom:1.5mm}}
.leadership-banner .lb-list{{display:flex;flex-direction:column;gap:1.2mm;font-size:9.5pt;color:{theme.text_primary}}}
.leadership-banner .lb-list strong{{color:{theme.accent_dark};font-weight:700}}
.job{{margin-bottom:5mm}}
.job-header{{display:flex;justify-content:space-between;align-items:baseline;gap:3mm;margin-bottom:0.5mm}}
.job-title{{font-size:10.5pt;font-weight:700;color:{theme.text_primary}}}
.job-period{{font-size:9pt;color:{theme.text_muted};font-variant-numeric:tabular-nums;white-space:nowrap;font-weight:500}}
.job-company{{font-size:9.5pt;color:{theme.accent_dark};font-weight:600;margin-bottom:1.5mm}}
.job-company .ctx{{color:{theme.text_muted};font-weight:400;font-style:italic}}
.highlight-row{{display:flex;flex-wrap:wrap;gap:2mm;margin:1.5mm 0 2mm 0}}
.highlight-pill{{background:rgba(0,0,0,0.04);border:1px solid {theme.accent_soft};color:{theme.accent_dark};font-size:8.5pt;padding:0.6mm 2mm;border-radius:2mm;font-weight:600}}
.job ul{{list-style:none;padding-left:0}}
.job ul li{{position:relative;padding-left:4mm;margin-bottom:1.4mm;font-size:9.5pt;color:{theme.text_primary};line-height:1.45}}
.job ul li::before{{content:'\\25B8';position:absolute;left:0;top:0;color:{theme.rule};font-weight:700;font-size:9pt}}
.job ul li strong{{color:{theme.text_primary};font-weight:700}}
.project-card{{border-left:3px solid {theme.rule};padding-left:3mm;margin-bottom:3mm}}
.project-card .pname{{font-size:10pt;font-weight:700;color:{theme.text_primary};margin-bottom:0.5mm}}
.project-card .pdesc{{font-size:9.5pt;color:{theme.text_primary};line-height:1.45}}
.project-card a{{color:{theme.accent_dark};text-decoration:none;font-weight:500;font-size:9pt}}
.edu-row{{margin-bottom:3mm}}
.edu-row .top{{display:flex;justify-content:space-between;font-size:10pt;font-weight:600;color:{theme.text_primary}}}
.edu-row .sub{{font-size:9.5pt;color:{theme.text_muted};font-style:italic}}
.cert-list{{display:grid;grid-template-columns:1fr 1fr;gap:1.5mm 4mm}}
.cert-item{{font-size:9.5pt;color:{theme.text_primary}}}
.cert-item .y{{color:{theme.accent_dark};font-weight:600;font-variant-numeric:tabular-nums}}
""".strip()


def _single_column_serif_css(theme: ResumeTheme) -> str:
    return f"""
{_CSS_BASE_PAGE}
html,body{{font-family:{theme.body_font};color:{theme.text_primary};background:#FAF7F2;line-height:1.55;font-size:10.5pt}}
.page{{max-width:210mm;min-height:297mm;margin:0 auto;background:#FFFFFF;box-shadow:0 8px 30px rgba(31,26,24,0.06);padding:18mm 18mm 16mm 18mm}}
.title-block{{border-top:4px solid {theme.accent};padding-top:6mm;margin-bottom:8mm;text-align:center}}
.title-block h1{{font-family:{theme.heading_font};font-size:30pt;font-weight:700;color:{theme.accent_dark};letter-spacing:0.02em;margin-bottom:2mm}}
.title-block .meta{{font-size:9.5pt;color:{theme.text_muted};letter-spacing:0.06em;text-transform:uppercase}}
.contact-bar{{display:flex;justify-content:center;flex-wrap:wrap;gap:6mm;margin-bottom:9mm;font-size:9.5pt;color:{theme.text_primary}}}
.contact-bar .ic{{color:{theme.accent};margin-right:1.5mm;font-weight:700}}
.contact-bar a{{color:{theme.text_primary};text-decoration:none;border-bottom:1px dotted {theme.accent_soft}}}
section.block{{padding-top:7mm;margin-bottom:0}}
section.block:first-of-type{{padding-top:0}}
section.block h2{{font-family:{theme.heading_font};font-size:14pt;color:{theme.accent_dark};font-weight:700;letter-spacing:0.04em;border-bottom:1px solid {theme.rule};padding-bottom:1.5mm;margin-bottom:4mm;text-transform:uppercase}}
.summary{{font-size:10.5pt;color:{theme.text_primary};line-height:1.6}}
.summary strong{{color:{theme.accent_dark};font-weight:700}}
.leadership-banner{{border-left:3px solid {theme.rule};padding:2mm 0 2mm 4mm;margin:4mm 0 5mm 0}}
.leadership-banner .lb-title{{font-family:{theme.heading_font};font-size:9.5pt;color:{theme.accent_dark};font-weight:700;text-transform:uppercase;letter-spacing:0.12em;margin-bottom:1.5mm}}
.leadership-banner .lb-list{{display:flex;flex-direction:column;gap:1mm;font-size:10pt;color:{theme.text_primary}}}
.leadership-banner .lb-list strong{{color:{theme.accent_dark};font-weight:700}}
.job{{margin-bottom:5mm}}
.job-header{{display:flex;justify-content:space-between;align-items:baseline;gap:3mm;margin-bottom:0.5mm}}
.job-title{{font-family:{theme.heading_font};font-size:11.5pt;font-weight:700;color:{theme.text_primary}}}
.job-period{{font-size:9.5pt;color:{theme.text_muted};font-style:italic;white-space:nowrap}}
.job-company{{font-size:10pt;color:{theme.accent_dark};font-style:italic;margin-bottom:1.5mm}}
.highlight-row{{display:flex;flex-wrap:wrap;gap:2mm;margin:1.5mm 0 2mm 0}}
.highlight-pill{{color:{theme.accent_dark};font-size:9pt;font-weight:600;font-style:italic}}
.highlight-pill::after{{content:" ·";color:{theme.text_muted};margin:0 1mm}}
.highlight-pill:last-child::after{{content:""}}
.job ul{{list-style:none;padding-left:0}}
.job ul li{{position:relative;padding-left:5mm;margin-bottom:1.5mm;font-size:10pt;color:{theme.text_primary};line-height:1.5}}
.job ul li::before{{content:'\\2014';position:absolute;left:0;top:0;color:{theme.accent}}}
.job ul li strong{{color:{theme.text_primary};font-weight:700}}
.project-card{{border-left:2px solid {theme.accent};padding:0 0 0 4mm;margin-bottom:3.5mm}}
.project-card .pname{{font-family:{theme.heading_font};font-size:11pt;font-weight:700;color:{theme.text_primary};margin-bottom:0.5mm}}
.project-card .pdesc{{font-size:10pt;color:{theme.text_primary};line-height:1.5}}
.edu-row{{margin-bottom:3mm}}
.edu-row .top{{display:flex;justify-content:space-between;font-family:{theme.heading_font};font-size:10.5pt;font-weight:700;color:{theme.text_primary}}}
.edu-row .sub{{font-size:10pt;color:{theme.text_muted};font-style:italic}}
.cert-list{{display:grid;grid-template-columns:1fr 1fr;gap:1.5mm 6mm}}
.cert-item{{font-size:10pt;color:{theme.text_primary}}}
.cert-item .y{{color:{theme.accent_dark};font-weight:700;font-variant-numeric:tabular-nums}}
.skills-row{{display:flex;flex-wrap:wrap;gap:2mm 4mm;font-size:10pt}}
.skills-row .group{{margin-right:6mm}}
.skills-row .group strong{{font-family:{theme.heading_font};color:{theme.accent_dark};font-weight:700;margin-right:1.5mm}}
.languages-row{{display:flex;gap:6mm;flex-wrap:wrap;font-size:10pt}}
.languages-row .lang{{padding:1mm 0}}
.languages-row .lang strong{{color:{theme.accent_dark}}}
""".strip()


def _single_column_minimal_css(theme: ResumeTheme) -> str:
    return f"""
{_CSS_BASE_PAGE}
html,body{{font-family:{theme.body_font};color:{theme.text_primary};background:#FFFFFF;line-height:1.55;font-size:10.5pt}}
.page{{max-width:210mm;min-height:297mm;margin:0 auto;background:#FFFFFF;padding:18mm 22mm 18mm 22mm}}
.title-block{{margin-bottom:9mm}}
.title-block h1{{font-family:{theme.heading_font};font-size:24pt;font-weight:700;color:{theme.text_primary};letter-spacing:-0.01em;margin-bottom:2.5mm}}
.title-block .meta{{font-size:10pt;color:{theme.text_muted}}}
.contact-bar{{display:flex;flex-wrap:wrap;gap:5mm;font-size:10pt;color:{theme.text_primary};margin-bottom:8mm}}
.contact-bar .ic{{color:{theme.accent};margin-right:1.2mm;font-weight:700}}
.contact-bar a{{color:{theme.text_primary};text-decoration:none;border-bottom:1px solid {theme.accent_soft}}}
section.block{{padding-top:7mm;margin-bottom:0}}
section.block:first-of-type{{padding-top:0}}
section.block h2{{font-family:{theme.heading_font};font-size:11pt;color:{theme.accent};font-weight:700;letter-spacing:0.18em;text-transform:uppercase;margin-bottom:3mm}}
section.block h2::after{{content:"";display:block;width:14mm;height:1.4pt;background:{theme.rule};margin-top:1.5mm}}
.summary{{font-size:10.5pt;color:{theme.text_primary};line-height:1.65}}
.summary strong{{color:{theme.accent};font-weight:700}}
.leadership-banner{{padding:3mm 0 4mm 0;margin-bottom:5mm}}
.leadership-banner .lb-title{{font-size:9pt;color:{theme.accent};font-weight:700;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:1.5mm}}
.leadership-banner .lb-list{{display:flex;flex-direction:column;gap:1.2mm;font-size:10pt;color:{theme.text_primary}}}
.leadership-banner .lb-list strong{{color:{theme.accent};font-weight:700}}
.job{{margin-bottom:5mm}}
.job-header{{display:flex;justify-content:space-between;align-items:baseline;gap:3mm;margin-bottom:0.5mm}}
.job-title{{font-size:11pt;font-weight:600;color:{theme.text_primary}}}
.job-period{{font-size:9.5pt;color:{theme.text_muted};white-space:nowrap}}
.job-company{{font-size:10pt;color:{theme.accent};font-weight:500;margin-bottom:1.5mm}}
.highlight-row{{display:flex;flex-wrap:wrap;gap:2mm;margin:1.5mm 0 2mm 0}}
.highlight-pill{{color:{theme.accent};font-size:9pt;font-weight:600}}
.highlight-pill::after{{content:" /";color:{theme.text_muted};margin:0 1mm}}
.highlight-pill:last-child::after{{content:""}}
.job ul{{list-style:none;padding-left:0}}
.job ul li{{position:relative;padding-left:4mm;margin-bottom:1.4mm;font-size:10pt;color:{theme.text_primary};line-height:1.55}}
.job ul li::before{{content:'\\2022';position:absolute;left:0;top:0;color:{theme.accent}}}
.job ul li strong{{color:{theme.text_primary};font-weight:700}}
.project-card{{margin-bottom:3.5mm}}
.project-card .pname{{font-size:10.5pt;font-weight:600;color:{theme.text_primary}}}
.project-card .pdesc{{font-size:10pt;color:{theme.text_primary};line-height:1.55}}
.edu-row{{margin-bottom:3mm}}
.edu-row .top{{display:flex;justify-content:space-between;font-size:10.5pt;font-weight:600;color:{theme.text_primary}}}
.edu-row .sub{{font-size:10pt;color:{theme.text_muted}}}
.cert-list{{display:grid;grid-template-columns:1fr 1fr;gap:1.5mm 6mm}}
.cert-item{{font-size:10pt;color:{theme.text_primary}}}
.cert-item .y{{color:{theme.accent};font-weight:700;font-variant-numeric:tabular-nums}}
.skills-row{{display:flex;flex-wrap:wrap;gap:2mm 5mm;font-size:10pt}}
.skills-row .group{{margin-right:6mm}}
.skills-row .group strong{{color:{theme.accent};font-weight:600;margin-right:1.5mm;letter-spacing:0.06em;text-transform:uppercase;font-size:9pt}}
.languages-row{{display:flex;flex-wrap:wrap;gap:5mm;font-size:10pt}}
.languages-row .lang strong{{color:{theme.accent};font-weight:600}}
""".strip()


def _centered_header_css(theme: ResumeTheme) -> str:
    return f"""
{_CSS_BASE_PAGE}
html,body{{font-family:{theme.body_font};color:{theme.text_primary};background:#F8FAFC;line-height:1.5;font-size:10.5pt}}
.page{{max-width:210mm;min-height:297mm;margin:0 auto;background:#FFFFFF;box-shadow:0 8px 30px rgba(15,23,42,0.08)}}
.banner{{background:linear-gradient(135deg,{theme.accent} 0%,{theme.accent_dark} 100%);color:{theme.on_accent};padding:16mm 18mm 12mm 18mm;text-align:center}}
.banner h1{{font-family:{theme.heading_font};font-size:26pt;font-weight:800;letter-spacing:0.01em;margin-bottom:3mm}}
.banner .role{{font-size:11pt;color:{theme.accent_soft};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:5mm}}
.banner .contact-bar{{display:flex;justify-content:center;flex-wrap:wrap;gap:6mm;font-size:9.5pt;color:rgba(255,255,255,0.92)}}
.banner .contact-bar a{{color:{theme.on_accent};text-decoration:none;border-bottom:1px dotted rgba(255,255,255,0.5)}}
.banner .contact-bar .ic{{color:{theme.accent_soft};margin-right:1.2mm;font-weight:700}}
.body{{padding:12mm 18mm 16mm 18mm}}
section.block{{padding-top:7mm;margin-bottom:0}}
section.block:first-of-type{{padding-top:0}}
section.block h2{{font-family:{theme.heading_font};font-size:12pt;color:{theme.accent_dark};font-weight:800;letter-spacing:0.14em;text-transform:uppercase;border-bottom:2px solid {theme.rule};padding-bottom:1.5mm;margin-bottom:4mm}}
.summary{{font-size:10.5pt;color:{theme.text_primary};line-height:1.6;text-align:justify}}
.summary strong{{color:{theme.accent_dark};font-weight:700}}
.leadership-banner{{background:rgba(0,0,0,0.03);border-left:4px solid {theme.rule};padding:3mm 4mm;margin:4mm 0 5mm 0;border-radius:0 2mm 2mm 0}}
.leadership-banner .lb-title{{font-size:9.5pt;color:{theme.accent_dark};font-weight:800;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:1.5mm}}
.leadership-banner .lb-list{{display:flex;flex-direction:column;gap:1.2mm;font-size:10pt;color:{theme.text_primary}}}
.leadership-banner .lb-list strong{{color:{theme.accent_dark};font-weight:700}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:9mm}}
.job{{margin-bottom:5mm}}
.job-header{{display:flex;justify-content:space-between;align-items:baseline;gap:3mm;margin-bottom:0.5mm}}
.job-title{{font-size:11pt;font-weight:700;color:{theme.text_primary}}}
.job-period{{font-size:9.5pt;color:{theme.text_muted};white-space:nowrap}}
.job-company{{font-size:10pt;color:{theme.accent};font-weight:600;margin-bottom:1.5mm}}
.highlight-row{{display:flex;flex-wrap:wrap;gap:2mm;margin:1.5mm 0 2mm 0}}
.highlight-pill{{background:{theme.accent_soft};color:{theme.accent_dark};font-size:8.5pt;padding:0.6mm 2mm;border-radius:2mm;font-weight:600}}
.job ul{{list-style:none;padding-left:0}}
.job ul li{{position:relative;padding-left:4mm;margin-bottom:1.5mm;font-size:10pt;color:{theme.text_primary};line-height:1.5}}
.job ul li::before{{content:'\\25C6';position:absolute;left:0;top:0;color:{theme.rule};font-size:8pt}}
.job ul li strong{{color:{theme.text_primary};font-weight:700}}
.skills-grid{{display:grid;grid-template-columns:1fr 1fr;gap:3mm 6mm;font-size:10pt}}
.skills-grid .group strong{{color:{theme.accent};font-weight:700;font-size:9pt;text-transform:uppercase;letter-spacing:0.08em;display:block;margin-bottom:1mm}}
.lang-list{{display:flex;flex-direction:column;gap:1.5mm;font-size:10pt}}
.lang-list .lang{{display:flex;justify-content:space-between;border-bottom:1px dashed {theme.accent_soft};padding-bottom:1mm}}
.lang-list .lang strong{{color:{theme.text_primary};font-weight:600}}
.lang-list .lang .lvl{{color:{theme.accent};font-weight:700}}
.project-card{{background:#F1F5F9;border-radius:2mm;padding:3mm 4mm;margin-bottom:3mm}}
.project-card .pname{{font-size:10.5pt;font-weight:700;color:{theme.accent_dark};margin-bottom:0.5mm}}
.project-card .pdesc{{font-size:10pt;color:{theme.text_primary};line-height:1.5}}
.edu-row{{margin-bottom:3mm}}
.edu-row .top{{display:flex;justify-content:space-between;font-size:10.5pt;font-weight:700;color:{theme.text_primary}}}
.edu-row .sub{{font-size:10pt;color:{theme.text_muted}}}
.cert-list{{display:grid;grid-template-columns:1fr 1fr;gap:1.5mm 6mm}}
.cert-item{{font-size:10pt;color:{theme.text_primary}}}
.cert-item .y{{color:{theme.accent};font-weight:700;font-variant-numeric:tabular-nums}}
""".strip()


def _theme_css(theme: ResumeTheme) -> str:
    if theme.layout_slug == "two_column_sidebar":
        return _two_column_css(theme)
    if theme.layout_slug == "single_column_serif":
        return _single_column_serif_css(theme)
    if theme.layout_slug == "single_column_minimal":
        return _single_column_minimal_css(theme)
    if theme.layout_slug == "centered_header_band":
        return _centered_header_css(theme)
    return _two_column_css(theme)


# ---------------------------------------------------------------------------
# Modern CV - shared HTML fragment builders
# ---------------------------------------------------------------------------
def _contact_rows(data: dict) -> list[tuple[str, str]]:
    """Return ``[(icon, text), ...]`` rows for the contact block."""
    contact = data.get("contact") or {}
    rows: list[tuple[str, str]] = []
    if isinstance(contact, dict):
        location = _safe_str(contact.get("location"))
        email = _safe_str(contact.get("email"))
        phone = _safe_str(contact.get("phone"))
        if location:
            rows.append(("&#x1F4CD;", _esc(location)))
        if email:
            rows.append(("&#x2709;", _esc(email)))
        if phone:
            rows.append(("&#x260E;", _esc(phone)))
    return rows


def _online_rows(data: dict) -> list[tuple[str, str, str]]:
    """Return ``[(icon, url, label), ...]`` rows for the online-links block."""
    rows: list[tuple[str, str, str]] = []
    for link in _safe_list(data.get("online_links")):
        if not isinstance(link, dict):
            continue
        label = _safe_str(link.get("label")) or _safe_str(link.get("url"))
        url = _safe_str(link.get("url"))
        icon = _safe_str(link.get("icon")) or "&bull;"
        if not label:
            continue
        rows.append((_esc(icon), _esc(url), _esc(label)))
    return rows


def _experience_html(data: dict) -> str:
    parts: list[str] = []
    for entry in _safe_list(data.get("experience")):
        if not isinstance(entry, dict):
            continue
        role = _esc(_safe_str(entry.get("role")))
        period = _esc(_safe_str(entry.get("period")))
        company = _esc(_safe_str(entry.get("company")))
        context = _esc(_safe_str(entry.get("context")))
        pills = [_safe_str(p) for p in _safe_list(entry.get("highlight_pills")) if _safe_str(p)]
        bullets = [_safe_str(b) for b in _safe_list(entry.get("bullets")) if _safe_str(b)]
        pill_html = "".join(
            f'<span class="highlight-pill">{_esc(p)}</span>' for p in pills
        )
        bullet_html = "".join(f"<li>{_bold_to_html(b)}</li>" for b in bullets)
        parts.append(
            '<div class="job">'
            '<div class="job-header">'
            f'<div class="job-title">{role}</div>'
            f'<div class="job-period">{period}</div>'
            "</div>"
            + (
                f'<div class="job-company">{company}'
                + (f' <span class="ctx">{context}</span>' if context else "")
                + "</div>"
                if (company or context)
                else ""
            )
            + (f'<div class="highlight-row">{pill_html}</div>' if pill_html else "")
            + (f"<ul>{bullet_html}</ul>" if bullet_html else "")
            + "</div>"
        )
    return "".join(parts)


def _projects_html(data: dict) -> str:
    parts: list[str] = []
    for entry in _safe_list(data.get("projects")):
        if not isinstance(entry, dict):
            continue
        name = _esc(_safe_str(entry.get("name")))
        url = _esc(_safe_str(entry.get("url")))
        description = _bold_to_html(_safe_str(entry.get("description")))
        link_html = f' <a href="{url}">{url}</a>' if url else ""
        parts.append(
            '<div class="project-card">'
            f'<div class="pname">{name}</div>'
            f'<div class="pdesc">{description}{link_html}</div>'
            "</div>"
        )
    return "".join(parts)


def _education_html(data: dict) -> str:
    parts: list[str] = []
    for entry in _safe_list(data.get("education")):
        if not isinstance(entry, dict):
            continue
        title = _esc(_safe_str(entry.get("title")))
        sub = _esc(_safe_str(entry.get("sub")))
        period = _esc(_safe_str(entry.get("period")))
        parts.append(
            '<div class="edu-row">'
            f'<div class="top"><span>{title}</span><span class="job-period">{period}</span></div>'
            + (f'<div class="sub">{sub}</div>' if sub else "")
            + "</div>"
        )
    return "".join(parts)


def _certifications_html(data: dict) -> str:
    items: list[str] = []
    for entry in _safe_list(data.get("certifications")):
        if not isinstance(entry, dict):
            continue
        year = _esc(_safe_str(entry.get("year")))
        text = _bold_to_html(_safe_str(entry.get("text")))
        items.append(
            f'<div class="cert-item"><span class="y">{year}</span> {text}</div>'
        )
    if not items:
        return ""
    return f'<div class="cert-list">{"".join(items)}</div>'


def _leadership_html(data: dict, labels: dict[str, str]) -> str:
    items = [
        _safe_str(x) for x in _safe_list(data.get("leadership_highlights")) if _safe_str(x)
    ]
    if not items:
        return ""
    items_html = "".join(f"<div>&bull; {_bold_to_html(item)}</div>" for item in items)
    title = _esc(labels.get("leadership", "Leadership Highlights"))
    return (
        '<div class="leadership-banner">'
        f'<div class="lb-title">{title}</div>'
        f'<div class="lb-list">{items_html}</div>'
        "</div>"
    )


def _skill_groups_html(data: dict) -> list[tuple[str, list[str]]]:
    """Return ``[(label, tags), ...]`` for the active skill groups."""
    groups: list[tuple[str, list[str]]] = []
    for group in _safe_list(data.get("skill_groups")):
        if not isinstance(group, dict):
            continue
        label = _safe_str(group.get("label"))
        tags = [_safe_str(t) for t in _safe_list(group.get("tags")) if _safe_str(t)]
        if not (label and tags):
            continue
        groups.append((label, tags))
    return groups


def _languages_rows(data: dict) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for entry in _safe_list(data.get("languages")):
        if not isinstance(entry, dict):
            continue
        name = _safe_str(entry.get("name"))
        level = _safe_str(entry.get("level"))
        if not name:
            continue
        rows.append((name, level))
    return rows


# ---------------------------------------------------------------------------
# Modern CV - layout-specific renderers
# ---------------------------------------------------------------------------
def _render_two_column(data: dict, theme: ResumeTheme, labels: dict[str, str]) -> str:
    full_name = _esc(_safe_str(data.get("full_name")))
    role_headline = _esc(_safe_str(data.get("role_headline")))
    role_subtitle = _esc(_safe_str(data.get("role_subtitle")))

    sidebar_parts: list[str] = [f"<h1>{full_name}</h1>"]
    if role_headline or role_subtitle:
        role_html = role_headline
        if role_subtitle:
            role_html += f"<span class='role-sub'>{role_subtitle}</span>"
        sidebar_parts.append(f"<div class='role'>{role_html}</div>")

    contact_rows = _contact_rows(data)
    if contact_rows:
        body = "".join(
            f'<div class="contact-line"><span class="ic">{ic}</span><span>{txt}</span></div>'
            for ic, txt in contact_rows
        )
        sidebar_parts.append(
            f'<div class="sb-section"><h3>{_esc(labels["contact"])}</h3>{body}</div>'
        )

    online_rows = _online_rows(data)
    if online_rows:
        rows: list[str] = []
        for ic, url, label in online_rows:
            if url:
                rows.append(
                    f'<div class="contact-line"><span class="ic">{ic}</span>'
                    f'<a href="{url}">{label}</a></div>'
                )
            else:
                rows.append(
                    f'<div class="contact-line"><span class="ic">{ic}</span>'
                    f'<span>{label}</span></div>'
                )
        sidebar_parts.append(
            f'<div class="sb-section"><h3>{_esc(labels["online"])}</h3>{"".join(rows)}</div>'
        )

    skill_groups = _skill_groups_html(data)
    if skill_groups:
        groups_html: list[str] = []
        for label, tags in skill_groups:
            tag_html = "".join(f'<span class="skill-tag">{_esc(t)}</span>' for t in tags)
            groups_html.append(
                '<div class="skill-group">'
                f'<div class="group-label">{_esc(label)}</div>'
                f'<div class="skill-tags">{tag_html}</div>'
                "</div>"
            )
        sidebar_parts.append(
            f'<div class="sb-section"><h3>{_esc(labels["tech_stack"])}</h3>'
            + "".join(groups_html)
            + "</div>"
        )

    languages = _languages_rows(data)
    if languages:
        rows = "".join(
            f'<div class="lang-row"><span>{_esc(name)}</span>'
            f'<span class="lvl">{_esc(level)}</span></div>'
            for name, level in languages
        )
        sidebar_parts.append(
            f'<div class="sb-section"><h3>{_esc(labels["languages"])}</h3>{rows}</div>'
        )

    main_parts: list[str] = []
    profile_summary = _safe_str(data.get("profile_summary"))
    if profile_summary:
        main_parts.append(
            f'<h2>{_esc(labels["profile"])}</h2>'
            f'<p class="summary">{_bold_to_html(profile_summary)}</p>'
        )
    main_parts.append(_leadership_html(data, labels))

    experience_html = _experience_html(data)
    if experience_html:
        main_parts.append(f'<h2>{_esc(labels["experience"])}</h2>')
        main_parts.append(experience_html)

    projects_html = _projects_html(data)
    if projects_html:
        main_parts.append(f'<h2>{_esc(labels["projects"])}</h2>')
        main_parts.append(projects_html)

    education_html = _education_html(data)
    if education_html:
        main_parts.append(f'<h2>{_esc(labels["education"])}</h2>')
        main_parts.append(education_html)

    cert_html = _certifications_html(data)
    if cert_html:
        main_parts.append(f'<h2>{_esc(labels["certifications"])}</h2>')
        main_parts.append(cert_html)

    return (
        '<div class="bg-stripe"></div>'
        '<div class="page">'
        f'<aside class="sidebar">{"".join(sidebar_parts)}</aside>'
        f'<main class="main">{"".join(main_parts)}</main>'
        "</div>"
    )


def _flat_contact_bar(data: dict) -> str:
    """Single-line contact bar used by every non-sidebar layout."""
    bits: list[str] = []
    for ic, txt in _contact_rows(data):
        bits.append(f'<span><span class="ic">{ic}</span>{txt}</span>')
    for ic, url, label in _online_rows(data):
        if url:
            bits.append(
                f'<span><span class="ic">{ic}</span>'
                f'<a href="{url}">{label}</a></span>'
            )
        else:
            bits.append(f'<span><span class="ic">{ic}</span>{label}</span>')
    if not bits:
        return ""
    return f'<div class="contact-bar">{"".join(bits)}</div>'


def _flat_skills_html(data: dict) -> str:
    groups = _skill_groups_html(data)
    if not groups:
        return ""
    rows = "".join(
        '<div class="group">'
        f"<strong>{_esc(label)}:</strong>"
        f' {_esc(", ".join(tags))}'
        "</div>"
        for label, tags in groups
    )
    return f'<div class="skills-row">{rows}</div>'


def _flat_languages_html(data: dict) -> str:
    rows = _languages_rows(data)
    if not rows:
        return ""
    parts = "".join(
        f'<div class="lang"><strong>{_esc(name)}</strong>'
        f"{' (' + _esc(level) + ')' if level else ''}</div>"
        for name, level in rows
    )
    return f'<div class="languages-row">{parts}</div>'


def _grid_skills_html(data: dict) -> str:
    groups = _skill_groups_html(data)
    if not groups:
        return ""
    rows = "".join(
        '<div class="group">'
        f"<strong>{_esc(label)}</strong>"
        f"<span>{_esc(', '.join(tags))}</span>"
        "</div>"
        for label, tags in groups
    )
    return f'<div class="skills-grid">{rows}</div>'


def _grid_languages_html(data: dict) -> str:
    rows = _languages_rows(data)
    if not rows:
        return ""
    parts = "".join(
        f'<div class="lang"><strong>{_esc(name)}</strong>'
        f'<span class="lvl">{_esc(level)}</span></div>'
        for name, level in rows
    )
    return f'<div class="lang-list">{parts}</div>'


def _render_single_column(
    data: dict, theme: ResumeTheme, labels: dict[str, str], *, flat: bool
) -> str:
    full_name = _esc(_safe_str(data.get("full_name")))
    role_headline = _safe_str(data.get("role_headline"))
    role_subtitle = _safe_str(data.get("role_subtitle"))
    meta_bits = " · ".join(b for b in [role_headline, role_subtitle] if b)

    parts: list[str] = ['<div class="page">']
    parts.append(
        '<div class="title-block">'
        f"<h1>{full_name}</h1>"
        + (f'<div class="meta">{_esc(meta_bits)}</div>' if meta_bits else "")
        + "</div>"
    )
    parts.append(_flat_contact_bar(data))

    profile_summary = _safe_str(data.get("profile_summary"))
    if profile_summary:
        parts.append(
            f'<section class="block"><h2>{_esc(labels["profile"])}</h2>'
            f'<p class="summary">{_bold_to_html(profile_summary)}</p></section>'
        )

    leadership = _leadership_html(data, labels)
    if leadership:
        parts.append(f'<section class="block">{leadership}</section>')

    skills = _flat_skills_html(data)
    if skills:
        parts.append(
            f'<section class="block"><h2>{_esc(labels["tech_stack"])}</h2>{skills}</section>'
        )

    experience_html = _experience_html(data)
    if experience_html:
        parts.append(
            f'<section class="block"><h2>{_esc(labels["experience"])}</h2>'
            f"{experience_html}</section>"
        )

    projects_html = _projects_html(data)
    if projects_html:
        parts.append(
            f'<section class="block"><h2>{_esc(labels["projects"])}</h2>'
            f"{projects_html}</section>"
        )

    education_html = _education_html(data)
    if education_html:
        parts.append(
            f'<section class="block"><h2>{_esc(labels["education"])}</h2>'
            f"{education_html}</section>"
        )

    cert_html = _certifications_html(data)
    if cert_html:
        parts.append(
            f'<section class="block"><h2>{_esc(labels["certifications"])}</h2>'
            f"{cert_html}</section>"
        )

    languages_html = _flat_languages_html(data)
    if languages_html:
        parts.append(
            f'<section class="block"><h2>{_esc(labels["languages"])}</h2>'
            f"{languages_html}</section>"
        )

    parts.append("</div>")
    return "".join(parts)


def _render_centered_header(
    data: dict, theme: ResumeTheme, labels: dict[str, str]
) -> str:
    full_name = _esc(_safe_str(data.get("full_name")))
    role_headline = _safe_str(data.get("role_headline"))
    role_subtitle = _safe_str(data.get("role_subtitle"))
    role_meta = " · ".join(b for b in [role_headline, role_subtitle] if b)

    contact_inline_parts: list[str] = []
    for ic, txt in _contact_rows(data):
        contact_inline_parts.append(
            f'<span><span class="ic">{ic}</span>{txt}</span>'
        )
    for ic, url, label in _online_rows(data):
        if url:
            contact_inline_parts.append(
                f'<span><span class="ic">{ic}</span>'
                f'<a href="{url}">{label}</a></span>'
            )
        else:
            contact_inline_parts.append(
                f'<span><span class="ic">{ic}</span>{label}</span>'
            )
    contact_bar_html = (
        f'<div class="contact-bar">{"".join(contact_inline_parts)}</div>'
        if contact_inline_parts
        else ""
    )

    parts: list[str] = ['<div class="page">']
    banner_bits: list[str] = [f"<h1>{full_name}</h1>"]
    if role_meta:
        banner_bits.append(f'<div class="role">{_esc(role_meta)}</div>')
    banner_bits.append(contact_bar_html)
    parts.append(f'<div class="banner">{"".join(banner_bits)}</div>')

    parts.append('<div class="body">')
    profile_summary = _safe_str(data.get("profile_summary"))
    if profile_summary:
        parts.append(
            f'<section class="block"><h2>{_esc(labels["profile"])}</h2>'
            f'<p class="summary">{_bold_to_html(profile_summary)}</p></section>'
        )

    leadership = _leadership_html(data, labels)
    if leadership:
        parts.append(f'<section class="block">{leadership}</section>')

    skills_grid = _grid_skills_html(data)
    languages_grid = _grid_languages_html(data)
    if skills_grid or languages_grid:
        sub_blocks: list[str] = []
        if skills_grid:
            sub_blocks.append(
                f'<section class="block"><h2>{_esc(labels["tech_stack"])}</h2>{skills_grid}</section>'
            )
        if languages_grid:
            sub_blocks.append(
                f'<section class="block"><h2>{_esc(labels["languages"])}</h2>{languages_grid}</section>'
            )
        parts.append(f'<div class="two-col">{"".join(sub_blocks)}</div>')

    experience_html = _experience_html(data)
    if experience_html:
        parts.append(
            f'<section class="block"><h2>{_esc(labels["experience"])}</h2>'
            f"{experience_html}</section>"
        )

    projects_html = _projects_html(data)
    if projects_html:
        parts.append(
            f'<section class="block"><h2>{_esc(labels["projects"])}</h2>'
            f"{projects_html}</section>"
        )

    education_html = _education_html(data)
    if education_html:
        parts.append(
            f'<section class="block"><h2>{_esc(labels["education"])}</h2>'
            f"{education_html}</section>"
        )

    cert_html = _certifications_html(data)
    if cert_html:
        parts.append(
            f'<section class="block"><h2>{_esc(labels["certifications"])}</h2>'
            f"{cert_html}</section>"
        )

    parts.append("</div>")
    parts.append("</div>")
    return "".join(parts)


def _render_modern_cv_body(
    data: dict, theme: ResumeTheme, labels: dict[str, str]
) -> str:
    if theme.layout_slug == "two_column_sidebar":
        return _render_two_column(data, theme, labels)
    if theme.layout_slug == "single_column_serif":
        return _render_single_column(data, theme, labels, flat=False)
    if theme.layout_slug == "single_column_minimal":
        return _render_single_column(data, theme, labels, flat=True)
    if theme.layout_slug == "centered_header_band":
        return _render_centered_header(data, theme, labels)
    return _render_two_column(data, theme, labels)


# ---------------------------------------------------------------------------
# Public renderers
# ---------------------------------------------------------------------------
def render_modern_cv_html(
    data: dict | None,
    theme: ResumeTheme,
    *,
    output_lang: str = "en",
) -> str:
    """Return a fully-styled, self-contained Modern CV HTML document.

    The HTML is what we hand to Playwright in
    :mod:`src.services.html_pdf`; it also doubles as the in-app preview
    (shown via ``ft.WebView`` in non-Modern-CV cases) and the on-disk
    HTML export.
    """
    if not isinstance(data, dict):
        data = {}
    labels = _labels(output_lang)
    css = _theme_css(theme)
    body = _render_modern_cv_body(data, theme, labels)
    title = _safe_str(data.get("full_name")) or "Modern CV"
    lang = (output_lang or "en").strip().lower() or "en"
    return (
        "<!doctype html>\n"
        f'<html lang="{lang}"><head><meta charset="utf-8"/>'
        f"<title>{_esc(title)} - Modern CV</title>"
        f"<style>{css}</style></head>"
        f"<body>{body}</body></html>"
    )


# ---------------------------------------------------------------------------
# Cover Letter renderer
# ---------------------------------------------------------------------------
def _cover_letter_css(theme: ResumeTheme) -> str:
    return f"""
{_CSS_BASE_PAGE}
html,body{{font-family:{theme.body_font};color:{theme.text_primary};background:#FFFFFF;line-height:1.6;font-size:11pt}}
.page{{max-width:210mm;min-height:297mm;margin:0 auto;background:#FFFFFF;padding:0}}
.header{{background:linear-gradient(135deg,{theme.accent} 0%,{theme.accent_dark} 100%);color:{theme.on_accent};padding:18mm 22mm 14mm 22mm}}
.header h1{{font-family:{theme.heading_font};font-size:24pt;font-weight:800;letter-spacing:-0.01em;margin-bottom:3mm}}
.header .contact-bar{{display:flex;flex-wrap:wrap;gap:5mm;font-size:10pt;color:rgba(255,255,255,0.92)}}
.header .contact-bar a{{color:{theme.on_accent};text-decoration:none;border-bottom:1px dotted rgba(255,255,255,0.5)}}
.header .contact-bar .ic{{color:{theme.accent_soft};margin-right:1mm;font-weight:700}}
.body{{padding:14mm 22mm 18mm 22mm}}
.salutation{{font-size:11pt;font-weight:600;color:{theme.text_primary};margin-bottom:6mm}}
.body p{{font-size:11pt;color:{theme.text_primary};line-height:1.65;margin-bottom:5mm;text-align:justify}}
.body p strong{{color:{theme.accent_dark};font-weight:700}}
.signoff{{margin-top:7mm;font-size:11pt;color:{theme.text_primary}}}
.signoff .closing{{margin-bottom:8mm}}
.signoff .signature{{font-family:{theme.heading_font};font-weight:700;color:{theme.accent_dark};font-size:12pt}}
""".strip()


def _parse_cover_letter(text: str) -> tuple[str, list[str], str, str]:
    """Split a cover-letter markdown body into structural pieces.

    Returns ``(salutation, paragraphs, closing, signature)``. The parser
    is intentionally permissive - the LLM-emitted markdown follows a
    loose convention (``Dear ... team,`` line, blank-line-separated
    paragraphs, ``Thank you for your time,`` line, candidate name on
    the last line) - so anything that does not match those heuristics
    becomes a plain paragraph.
    """
    if not text:
        return "", [], "", ""

    raw_lines = text.replace("\r\n", "\n").split("\n")
    # Strip the leading bold-name / contact lines that the LLM puts at
    # the top of the document; the themed banner re-renders them.
    skip_until_salutation = True
    body_lines: list[str] = []
    for line in raw_lines:
        stripped = line.strip()
        if skip_until_salutation:
            if not stripped:
                continue
            low = stripped.lower()
            if low.startswith("dear ") or low.startswith("vážen") or low.startswith("vazen"):
                skip_until_salutation = False
                body_lines.append(stripped)
                continue
            # Anything other than salutation before the salutation is
            # the candidate name + contact line - skip silently.
            continue
        body_lines.append(line.rstrip())

    if not body_lines:
        body_lines = [ln.rstrip() for ln in raw_lines if ln.strip()]

    salutation = ""
    paragraphs: list[str] = []
    closing = ""
    signature = ""

    if body_lines and (
        body_lines[0].lower().startswith("dear ")
        or body_lines[0].lower().startswith("vážen")
        or body_lines[0].lower().startswith("vazen")
    ):
        salutation = body_lines[0].rstrip(",")
        body_lines = body_lines[1:]

    # Group remaining lines into blank-line-separated paragraphs.
    blocks: list[str] = []
    current: list[str] = []
    for line in body_lines:
        if not line.strip():
            if current:
                blocks.append(" ".join(s.strip() for s in current).strip())
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(" ".join(s.strip() for s in current).strip())

    # Detect a closing line + signature: typically "Thank you for your
    # time," / "Děkuji za váš čas," followed by the candidate name.
    closing_keywords = ("thank you", "děkuji", "dekuji", "sincerely", "best regards", "s úctou", "s uctou", "with regards", "kind regards")
    if blocks:
        last = blocks[-1]
        # Last block might be just the candidate name (single short line).
        if len(last.split()) <= 4 and "," not in last and "." not in last:
            signature = last
            blocks = blocks[:-1]
            if blocks:
                tail = blocks[-1]
                if any(kw in tail.lower() for kw in closing_keywords):
                    closing = tail.rstrip(",")
                    blocks = blocks[:-1]

    paragraphs = [b for b in blocks if b]
    return salutation, paragraphs, closing, signature


def render_cover_letter_html(
    text: str,
    *,
    candidate_name: str = "",
    candidate_contact: dict | None = None,
    theme: ResumeTheme,
    output_lang: str = "en",
) -> str:
    """Wrap a cover-letter markdown body in a themed A4 HTML page.

    ``candidate_name`` and ``candidate_contact`` come straight from the
    Modern CV payload (or the candidate JSON) so the header banner can
    show the candidate's name + email + phone alongside the chosen
    palette colour.
    """
    salutation, paragraphs, closing, signature = _parse_cover_letter(text or "")
    name = candidate_name.strip() or signature.strip() or "Candidate"

    contact_bits: list[str] = []
    contact = candidate_contact or {}
    location = _safe_str(contact.get("location"))
    email = _safe_str(contact.get("email"))
    phone = _safe_str(contact.get("phone"))
    if location:
        contact_bits.append(
            f'<span><span class="ic">&#x1F4CD;</span>{_esc(location)}</span>'
        )
    if email:
        contact_bits.append(
            f'<span><span class="ic">&#x2709;</span>{_esc(email)}</span>'
        )
    if phone:
        contact_bits.append(
            f'<span><span class="ic">&#x260E;</span>{_esc(phone)}</span>'
        )

    contact_bar = (
        f'<div class="contact-bar">{"".join(contact_bits)}</div>'
        if contact_bits
        else ""
    )

    paragraphs_html = "".join(
        f"<p>{_bold_to_html(para)}</p>" for para in paragraphs if para
    )
    closing_html = ""
    if closing or signature:
        closing_html = (
            '<div class="signoff">'
            + (
                f'<div class="closing">{_esc(closing)}</div>'
                if closing
                else ""
            )
            + (
                f'<div class="signature">{_esc(signature or name)}</div>'
                if (signature or name)
                else ""
            )
            + "</div>"
        )

    body_inner = (
        (f'<div class="salutation">{_esc(salutation)},</div>' if salutation else "")
        + paragraphs_html
        + closing_html
    )

    css = _cover_letter_css(theme)
    lang = (output_lang or "en").strip().lower() or "en"
    return (
        "<!doctype html>\n"
        f'<html lang="{lang}"><head><meta charset="utf-8"/>'
        f"<title>{_esc(name)} - Cover letter</title>"
        f"<style>{css}</style></head>"
        '<body><div class="page">'
        f'<div class="header"><h1>{_esc(name)}</h1>{contact_bar}</div>'
        f'<div class="body">{body_inner}</div>'
        "</div></body></html>"
    )


__all__ = [
    "ResumeTheme",
    "Palette",
    "ThemeLayout",
    "PALETTES",
    "LAYOUTS",
    "DEFAULT_PALETTE",
    "DEFAULT_LAYOUT",
    "resolve_theme",
    "pick_next_palette",
    "pick_next_layout",
    "render_modern_cv_html",
    "render_cover_letter_html",
]
