"""Markdown → MD / HTML / DOCX / PDF writers.

The renderer is intentionally narrow: it understands the subset of
markdown that the AI Career pipeline produces (headings up to H3, bold,
italics, ordered + unordered bullet lists, paragraphs, soft line breaks).
Everything else is rendered as plain paragraph text.

ATS friendliness drives all formatting decisions:

* single column
* no tables
* readable serif body / sans heading
* generous left margin
* page breaks on H1 only

PDF uses :mod:`reportlab` (pure Python - no GTK / Office / Pandoc).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET_RE = re.compile(r"^([*\-+])\s+(.*)$")
_ORDERED_RE = re.compile(r"^(\d+)\.\s+(.*)$")


@dataclass
class Block:
    kind: str  # "h1" / "h2" / "h3" / "p" / "ul" / "ol"
    text: str = ""
    items: list[str] | None = None


def parse_markdown(text: str) -> list[Block]:
    """Lightweight markdown parser tuned for our outputs."""
    blocks: list[Block] = []
    if not text:
        return blocks

    lines = text.replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines):
        raw = lines[i].rstrip()
        stripped = raw.strip()

        if not stripped:
            i += 1
            continue

        heading = _HEADING_RE.match(stripped)
        if heading:
            level = min(3, len(heading.group(1)))
            blocks.append(Block(kind=f"h{level}", text=heading.group(2).strip()))
            i += 1
            continue

        bullet = _BULLET_RE.match(stripped)
        if bullet:
            items: list[str] = [bullet.group(2).strip()]
            i += 1
            while i < len(lines):
                nxt = _BULLET_RE.match(lines[i].strip())
                if not nxt or not lines[i].strip():
                    break
                items.append(nxt.group(2).strip())
                i += 1
            blocks.append(Block(kind="ul", items=items))
            continue

        ordered = _ORDERED_RE.match(stripped)
        if ordered:
            items = [ordered.group(2).strip()]
            i += 1
            while i < len(lines):
                nxt = _ORDERED_RE.match(lines[i].strip())
                if not nxt or not lines[i].strip():
                    break
                items.append(nxt.group(2).strip())
                i += 1
            blocks.append(Block(kind="ol", items=items))
            continue

        para_lines: list[str] = [stripped]
        i += 1
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                break
            if _HEADING_RE.match(line) or _BULLET_RE.match(line) or _ORDERED_RE.match(line):
                break
            para_lines.append(line)
            i += 1
        blocks.append(Block(kind="p", text=" ".join(para_lines)))
    return blocks


def export_markdown(text: str, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text or "", encoding="utf-8")
    return target


def export_html(text: str, target: Path, *, title: str = "Document") -> Path:
    try:
        import markdown2  # type: ignore[import-not-found]

        body = markdown2.markdown(text or "", extras=["fenced-code-blocks", "tables", "strike"])
    except ImportError:
        body = _blocks_to_html(parse_markdown(text or ""))

    html = (
        "<!doctype html>\n"
        "<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\" />\n"
        f"<title>{_escape_html(title)}</title>\n"
        "<style>\n"
        "  body { font-family: 'Segoe UI', Arial, sans-serif; color: #1f2937; "
        "max-width: 760px; margin: 32px auto; padding: 0 24px; line-height: 1.5; }\n"
        "  h1 { font-size: 24px; margin: 18px 0 8px; }\n"
        "  h2 { font-size: 18px; margin: 16px 0 6px; }\n"
        "  h3 { font-size: 15px; margin: 12px 0 4px; }\n"
        "  p, li { font-size: 13px; }\n"
        "  ul, ol { margin: 4px 0 12px 22px; }\n"
        "</style>\n"
        "</head>\n<body>\n"
        + body
        + "\n</body>\n</html>\n"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return target


def export_docx(text: str, target: Path, *, title: str = "Document") -> Path:
    try:
        from docx import Document  # type: ignore[import-not-found]
        from docx.shared import Pt
    except ImportError as exc:
        raise RuntimeError("python-docx not installed - run pip install -r requirements.txt") from exc

    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    blocks = parse_markdown(text or "")
    for block in blocks:
        if block.kind in ("h1", "h2", "h3"):
            level = int(block.kind[1])
            doc.add_heading(block.text, level=level)
        elif block.kind == "p":
            doc.add_paragraph(_strip_inline(block.text))
        elif block.kind == "ul":
            for item in block.items or []:
                doc.add_paragraph(_strip_inline(item), style="List Bullet")
        elif block.kind == "ol":
            for item in block.items or []:
                doc.add_paragraph(_strip_inline(item), style="List Number")

    target.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(target))
    return target


def export_pdf(text: str, target: Path, *, title: str = "Document") -> Path:
    try:
        from reportlab.lib.pagesizes import A4  # type: ignore[import-not-found]
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore[import-not-found]
        from reportlab.lib.units import cm  # type: ignore[import-not-found]
        from reportlab.platypus import (  # type: ignore[import-not-found]
            ListFlowable,
            ListItem,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
        )
    except ImportError as exc:
        raise RuntimeError("reportlab not installed - run pip install -r requirements.txt") from exc

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        spaceAfter=4,
    )
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=18, leading=22, spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=14, leading=18, spaceAfter=6)
    h3 = ParagraphStyle("h3", parent=styles["Heading3"], fontSize=11, leading=14, spaceAfter=4)

    doc = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title=title,
    )

    flowables: list = []
    blocks = parse_markdown(text or "")
    for block in blocks:
        if block.kind == "h1":
            flowables.append(Paragraph(_inline_to_html(block.text), h1))
        elif block.kind == "h2":
            flowables.append(Paragraph(_inline_to_html(block.text), h2))
        elif block.kind == "h3":
            flowables.append(Paragraph(_inline_to_html(block.text), h3))
        elif block.kind == "p":
            flowables.append(Paragraph(_inline_to_html(block.text), body))
            flowables.append(Spacer(1, 4))
        elif block.kind == "ul":
            items = [
                ListItem(Paragraph(_inline_to_html(item), body), leftIndent=12)
                for item in (block.items or [])
            ]
            if items:
                flowables.append(ListFlowable(items, bulletType="bullet", leftIndent=18))
                flowables.append(Spacer(1, 4))
        elif block.kind == "ol":
            items = [
                ListItem(Paragraph(_inline_to_html(item), body), leftIndent=12)
                for item in (block.items or [])
            ]
            if items:
                flowables.append(ListFlowable(items, bulletType="1", leftIndent=18))
                flowables.append(Spacer(1, 4))

    if not flowables:
        flowables.append(Paragraph(_escape_html(text or ""), body))

    target.parent.mkdir(parents=True, exist_ok=True)
    doc.build(flowables)
    return target


def export_all(text: str, folder: Path, basename: str, *, title: Optional[str] = None) -> dict[str, Path]:
    """Convenience helper - writes MD, HTML, DOCX, PDF using one base name."""
    folder.mkdir(parents=True, exist_ok=True)
    title = title or basename
    out: dict[str, Path] = {}
    out["md"] = export_markdown(text, folder / f"{basename}.md")
    out["html"] = export_html(text, folder / f"{basename}.html", title=title)
    try:
        out["docx"] = export_docx(text, folder / f"{basename}.docx", title=title)
    except RuntimeError:
        pass
    try:
        out["pdf"] = export_pdf(text, folder / f"{basename}.pdf", title=title)
    except RuntimeError:
        pass
    return out


def _strip_inline(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text


def _inline_to_html(text: str) -> str:
    escaped = _escape_html(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"\*(.+?)\*", r"<i>\1</i>", escaped)
    escaped = re.sub(r"`([^`]+)`", r"<font face='Courier'>\1</font>", escaped)
    return escaped


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _blocks_to_html(blocks: Iterable[Block]) -> str:
    out: list[str] = []
    for block in blocks:
        if block.kind in ("h1", "h2", "h3"):
            level = block.kind[1]
            out.append(f"<h{level}>{_escape_html(block.text)}</h{level}>")
        elif block.kind == "p":
            out.append(f"<p>{_escape_html(block.text)}</p>")
        elif block.kind == "ul":
            inner = "".join(f"<li>{_escape_html(item)}</li>" for item in (block.items or []))
            out.append(f"<ul>{inner}</ul>")
        elif block.kind == "ol":
            inner = "".join(f"<li>{_escape_html(item)}</li>" for item in (block.items or []))
            out.append(f"<ol>{inner}</ol>")
    return "\n".join(out)
