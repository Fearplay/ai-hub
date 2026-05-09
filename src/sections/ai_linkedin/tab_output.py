"""Output tab - render every generated LinkedIn section as a card.

Cards are rendered in the same order :func:`pipeline._render_section_markdown`
walks them so the screen, the on-disk markdown files and the composite
HTML report stay in sync.

Each card supports:

* a copy-to-clipboard button (per body of text),
* a chars / variant counter where useful,
* evidence badges showing where each claim was sourced from.

A bottom action bar surfaces "Save complete profile package" + "Open last
run folder". When STATE has no results yet we render a friendly empty
state that nudges the user back to Setup.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from typing import Callable, Optional

import flet as ft

from src.services import clipboard, logger as logger_service
from src.sections.ai_linkedin import pipeline
from src.sections.ai_linkedin.refs import REFS, safe
from src.sections.ai_linkedin.state import STATE, TAB_SETUP
from src.sections.ai_linkedin.strings import s
from src.theme import Theme


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.tab_output", "request_full_refresh_import", exc,
        )
        return
    request_section_refresh()


def _open_in_explorer(path: str) -> None:
    if not path or not os.path.isdir(path):
        logger_service.log_event(
            "WARNING", "ai_linkedin.tab_output", "open_in_explorer_no_path",
            path=str(path),
        )
        return
    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.tab_output", "open_in_explorer_failed", exc, path=path,
        )


def _empty_state(theme: Theme, txt: dict, on_navigate_tab: Callable[[int], None]) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.HUB_OUTLINED, color=theme.primary, size=42),
                    width=84,
                    height=84,
                    bgcolor=ft.Colors.with_opacity(0.16, theme.primary),
                    border_radius=22,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text(
                    txt["output_empty_title"],
                    color=theme.text,
                    size=18,
                    weight=ft.FontWeight.W_700,
                ),
                ft.Text(
                    txt["output_empty_desc"],
                    color=theme.text_muted,
                    size=13,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=12),
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.ARROW_BACK, color=theme.primary, size=14),
                            ft.Text(
                                txt["builder_tab_setup"],
                                color=theme.primary,
                                size=12,
                                weight=ft.FontWeight.W_600,
                            ),
                        ],
                        spacing=6,
                        tight=True,
                    ),
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    bgcolor=ft.Colors.with_opacity(0.10, theme.primary),
                    border_radius=10,
                    ink=True,
                    on_click=lambda e: on_navigate_tab(TAB_SETUP),
                ),
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            tight=True,
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
        padding=40,
    )


def _copy_button(theme: Theme, txt: dict, get_text: Callable[[], str]) -> ft.Container:
    def _on_click(e: ft.ControlEvent) -> None:
        # Synchronous OS clipboard copy via :mod:`src.services.clipboard`.
        # Avoids the previous async ``ft.Clipboard().set`` race that died
        # with ``RuntimeError("Session closed")`` after a navigation.
        ok = clipboard.copy(get_text() or "")
        page = e.page
        if not ok:
            logger_service.log_event(
                "ERROR", "ai_linkedin.tab_output", "copy_failed",
                backend=clipboard.backend_name(),
            )
            return
        if page is None:
            return
        try:
            page.snack_bar = ft.SnackBar(content=ft.Text(txt["output_copy"]))
            page.snack_bar.open = True
            page.update()
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.tab_output", "copy_snack_failed", exc,
            )

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.CONTENT_COPY, color=theme.text_muted, size=14),
                ft.Text(
                    txt["output_copy"],
                    color=theme.text,
                    size=11,
                    weight=ft.FontWeight.W_600,
                ),
            ],
            spacing=6,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        bgcolor=theme.surface_2,
        border=ft.border.all(1, theme.border),
        border_radius=8,
        ink=True,
        on_click=_on_click,
    )


def _evidence_chip(theme: Theme, label: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            label,
            color=theme.primary,
            size=10,
            weight=ft.FontWeight.W_700,
            style=ft.TextStyle(letter_spacing=0.6),
        ),
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        bgcolor=ft.Colors.with_opacity(0.14, theme.primary),
        border_radius=6,
    )


def _section_card(
    theme: Theme, *, icon: str, title: str, body: ft.Control,
    actions: Optional[list[ft.Control]] = None,
) -> ft.Container:
    header_children: list[ft.Control] = [
        ft.Container(
            content=ft.Icon(icon, color=theme.primary, size=18),
            width=36,
            height=36,
            bgcolor=ft.Colors.with_opacity(0.14, theme.primary),
            border_radius=10,
            alignment=ft.Alignment.CENTER,
        ),
        ft.Text(title, color=theme.text, size=15, weight=ft.FontWeight.W_700, expand=True),
    ]
    if actions:
        header_children.extend(actions)
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=header_children,
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=8),
                body,
            ],
            spacing=2,
            tight=True,
        ),
        padding=18,
        bgcolor=theme.surface,
        border_radius=14,
        border=ft.border.all(1, theme.border),
    )


def _evidence_label(theme_anchor: str, txt: dict) -> str:
    mapping = {
        "resume": txt["evidence_resume"],
        "linkedin_export": txt["evidence_linkedin_export"],
        "github": txt["evidence_github"],
        "user_confirmed": txt["evidence_user_confirmed"],
        "missing_evidence": txt["evidence_missing_evidence"],
    }
    return mapping.get(theme_anchor, theme_anchor.replace("_", " ").title())


def _score_banner(theme: Theme, txt: dict) -> ft.Container:
    score = int((STATE.profile_score or {}).get("score") or 0)
    score_color = "#22C55E" if score >= 80 else ("#F97316" if score < 60 else theme.primary)
    breakdown = (STATE.profile_score or {}).get("breakdown") or []
    breakdown_lines: list[ft.Control] = []
    for entry in breakdown:
        label = entry.get("label") or entry.get("key") or ""
        contribution = entry.get("contribution", 0)
        weight = entry.get("weight", 0)
        breakdown_lines.append(
            ft.Row(
                controls=[
                    ft.Text(label, color=theme.text, size=12, expand=True),
                    ft.Text(
                        f"{contribution}/{weight}",
                        color=theme.text_muted,
                        size=11,
                        weight=ft.FontWeight.W_600,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
    return _section_card(
        theme,
        icon=ft.Icons.SCOREBOARD_OUTLINED,
        title=txt["output_score_card_title"],
        body=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Text(
                                f"{score}",
                                color=ft.Colors.WHITE,
                                size=28,
                                weight=ft.FontWeight.W_700,
                            ),
                            padding=ft.padding.symmetric(horizontal=18, vertical=8),
                            bgcolor=score_color,
                            border_radius=12,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    f"/ 100",
                                    color=theme.text_muted,
                                    size=14,
                                    weight=ft.FontWeight.W_500,
                                ),
                                ft.Text(
                                    txt["output_score_card_desc"],
                                    color=theme.text_muted,
                                    size=11,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                            tight=True,
                        ),
                    ],
                    spacing=14,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=8),
                ft.Text(
                    txt["output_score_breakdown_label"],
                    color=theme.text,
                    size=12,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Column(controls=breakdown_lines, spacing=4, tight=True),
            ],
            spacing=4,
            tight=True,
        ),
    )


def _checklist_card(theme: Theme, txt: dict) -> ft.Container:
    items = (STATE.completeness or {}).get("items") or []
    if not items:
        return _section_card(
            theme,
            icon=ft.Icons.CHECKLIST,
            title=txt["output_checklist_title"],
            body=ft.Text(
                txt["output_no_evidence_skip"],
                color=theme.text_muted,
                size=12,
            ),
        )
    grouped: dict[str, list[dict]] = {"high": [], "medium": [], "low": [], "skip": []}
    for item in items:
        prio = item.get("priority") or "low"
        grouped.setdefault(prio, []).append(item)

    rows: list[ft.Control] = []
    priority_labels = {
        "high": txt["priority_high"],
        "medium": txt["priority_medium"],
        "low": txt["priority_low"],
        "skip": txt["priority_skip"],
    }
    priority_colors = {
        "high": "#EF4444",
        "medium": "#F59E0B",
        "low": "#0EA5E9",
        "skip": theme.text_muted,
    }
    for prio in ("high", "medium", "low", "skip"):
        bucket = grouped.get(prio) or []
        if not bucket:
            continue
        rows.append(
            ft.Container(
                content=ft.Text(
                    priority_labels[prio],
                    color=priority_colors[prio],
                    size=11,
                    weight=ft.FontWeight.W_700,
                    style=ft.TextStyle(letter_spacing=0.6),
                ),
                padding=ft.padding.only(top=10, bottom=4),
            )
        )
        for entry in bucket:
            mark_icon = ft.Icons.CHECK_CIRCLE if entry.get("ok") else ft.Icons.RADIO_BUTTON_UNCHECKED
            mark_color = "#22C55E" if entry.get("ok") else theme.text_muted
            rows.append(
                ft.Row(
                    controls=[
                        ft.Icon(mark_icon, color=mark_color, size=16),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    entry.get("label") or "",
                                    color=theme.text,
                                    size=12,
                                    weight=ft.FontWeight.W_600,
                                ),
                                ft.Text(
                                    entry.get("reason") or "",
                                    color=theme.text_muted,
                                    size=11,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                            tight=True,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
            )
    return _section_card(
        theme,
        icon=ft.Icons.CHECKLIST,
        title=txt["output_checklist_title"],
        body=ft.Column(controls=rows, spacing=6, tight=True),
    )


def _headlines_card(theme: Theme, txt: dict) -> ft.Container:
    payload = STATE.headlines or {}
    variants = payload.get("variants") or []
    if not variants:
        return _section_card(
            theme,
            icon=ft.Icons.TITLE,
            title=txt["output_headlines_title"],
            body=ft.Text(txt["output_no_evidence_skip"], color=theme.text_muted, size=12),
        )
    rows: list[ft.Control] = []
    for v in variants:
        text = (v.get("text") or "").strip()
        chars = v.get("char_count") or len(text)
        focus = (v.get("focus") or v.get("audience") or "").strip()
        anchors = v.get("evidence_anchors") or []
        rows.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text(
                                    focus or "—",
                                    color=theme.primary,
                                    size=11,
                                    weight=ft.FontWeight.W_700,
                                    style=ft.TextStyle(letter_spacing=0.6),
                                ),
                                ft.Container(expand=True),
                                ft.Text(
                                    f"{chars} {txt['output_chars_suffix']}",
                                    color=theme.text_muted,
                                    size=11,
                                ),
                                _copy_button(theme, txt, lambda t=text: t),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Text(text, color=theme.text, size=13, selectable=True),
                        ft.Row(
                            controls=[
                                _evidence_chip(theme, _evidence_label(a, txt)) for a in anchors
                            ],
                            spacing=6,
                            wrap=True,
                            run_spacing=6,
                        ),
                    ],
                    spacing=6,
                    tight=True,
                ),
                padding=12,
                bgcolor=theme.surface_2,
                border_radius=10,
                border=ft.border.all(1, theme.border),
            )
        )
    return _section_card(
        theme,
        icon=ft.Icons.TITLE,
        title=txt["output_headlines_title"],
        body=ft.Column(controls=rows, spacing=8, tight=True),
    )


def _about_card(theme: Theme, txt: dict) -> ft.Container:
    payload = STATE.about_variants or {}
    if not payload:
        return _section_card(
            theme,
            icon=ft.Icons.SUBJECT,
            title=txt["output_about_title"],
            body=ft.Text(txt["output_no_evidence_skip"], color=theme.text_muted, size=12),
        )
    parts = [
        ("short_version", txt["output_about_short"]),
        ("medium_version", txt["output_about_medium"]),
        ("long_version", txt["output_about_long"]),
        ("technical_version", txt["output_about_technical"]),
        ("recruiter_version", txt["output_about_recruiter"]),
    ]
    char_counts = payload.get("char_counts") or {}
    rows: list[ft.Control] = []
    for key, label in parts:
        body = (payload.get(key) or "").strip()
        if not body:
            continue
        chars = char_counts.get(key, len(body))
        rows.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text(
                                    label,
                                    color=theme.primary,
                                    size=11,
                                    weight=ft.FontWeight.W_700,
                                    style=ft.TextStyle(letter_spacing=0.6),
                                ),
                                ft.Container(expand=True),
                                ft.Text(
                                    f"{chars} {txt['output_chars_suffix']}",
                                    color=theme.text_muted,
                                    size=11,
                                ),
                                _copy_button(theme, txt, lambda b=body: b),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Text(body, color=theme.text, size=13, selectable=True),
                    ],
                    spacing=6,
                    tight=True,
                ),
                padding=12,
                bgcolor=theme.surface_2,
                border_radius=10,
                border=ft.border.all(1, theme.border),
            )
        )
    return _section_card(
        theme,
        icon=ft.Icons.SUBJECT,
        title=txt["output_about_title"],
        body=ft.Column(controls=rows, spacing=8, tight=True),
    )


def _experience_card(theme: Theme, txt: dict) -> ft.Container:
    payload = STATE.experience_rewrites or {}
    roles = payload.get("roles") or []
    if not roles:
        return _section_card(
            theme,
            icon=ft.Icons.WORK_OUTLINE,
            title=txt["output_experience_title"],
            body=ft.Text(txt["output_no_evidence_skip"], color=theme.text_muted, size=12),
        )
    rows: list[ft.Control] = []
    for role in roles:
        if not isinstance(role, dict):
            continue
        title = f"{role.get('role') or ''} · {role.get('company') or ''}".strip(" ·")
        period = role.get("period") or ""
        desc = (role.get("linkedin_description") or "").strip()
        bullets = role.get("bullets") or []
        skills = role.get("suggested_skills") or []
        do_not = role.get("do_not_claim") or []
        anchors = role.get("evidence_anchors") or []

        chunk: list[ft.Control] = [
            ft.Row(
                controls=[
                    ft.Text(
                        title,
                        color=theme.text,
                        size=13,
                        weight=ft.FontWeight.W_700,
                        expand=True,
                    ),
                    ft.Text(period, color=theme.text_muted, size=11, italic=True),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ]
        if desc:
            chunk.append(ft.Text(desc, color=theme.text, size=12, selectable=True))
        if bullets:
            chunk.append(
                ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text("•", color=theme.primary, size=12),
                                ft.Text(
                                    str(b), color=theme.text, size=12, expand=True,
                                    selectable=True,
                                ),
                            ],
                            spacing=6,
                        )
                        for b in bullets
                    ],
                    spacing=4,
                    tight=True,
                )
            )
        if skills:
            chunk.append(
                ft.Row(
                    controls=[
                        _evidence_chip(theme, str(s.get("name") or s if isinstance(s, dict) else s))
                        for s in skills
                    ],
                    spacing=6,
                    run_spacing=6,
                    wrap=True,
                )
            )
        if do_not:
            chunk.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "Do NOT claim:",
                                color="#EF4444",
                                size=11,
                                weight=ft.FontWeight.W_700,
                            ),
                            *[
                                ft.Text(f"• {note}", color=theme.text_muted, size=11)
                                for note in do_not
                            ],
                        ],
                        spacing=2,
                        tight=True,
                    ),
                    padding=8,
                    border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.06, "#EF4444"),
                )
            )
        if anchors:
            chunk.append(
                ft.Row(
                    controls=[
                        _evidence_chip(theme, _evidence_label(a, txt)) for a in anchors
                    ],
                    spacing=6,
                    wrap=True,
                    run_spacing=6,
                )
            )
        rows.append(
            ft.Container(
                content=ft.Column(controls=chunk, spacing=6, tight=True),
                padding=12,
                bgcolor=theme.surface_2,
                border_radius=10,
                border=ft.border.all(1, theme.border),
            )
        )
    return _section_card(
        theme,
        icon=ft.Icons.WORK_OUTLINE,
        title=txt["output_experience_title"],
        body=ft.Column(controls=rows, spacing=10, tight=True),
    )


def _bucketed_skills_card(theme: Theme, txt: dict) -> ft.Container:
    payload = STATE.skills_buckets or {}
    if not payload:
        return _section_card(
            theme,
            icon=ft.Icons.STAR_OUTLINE,
            title=txt["output_skills_title"],
            body=ft.Text(txt["output_no_evidence_skip"], color=theme.text_muted, size=12),
        )
    buckets = [
        ("core", txt["output_skill_bucket_core"], "#22C55E"),
        ("to_verify", txt["output_skill_bucket_to_verify"], "#F59E0B"),
        ("to_learn", txt["output_skill_bucket_to_learn"], "#0EA5E9"),
        ("do_not_claim", txt["output_skill_bucket_do_not_claim"], "#EF4444"),
    ]
    rows: list[ft.Control] = []
    for key, label, color in buckets:
        items = payload.get(key) or []
        if not items:
            continue
        rows.append(
            ft.Container(
                content=ft.Text(
                    label,
                    color=color,
                    size=11,
                    weight=ft.FontWeight.W_700,
                    style=ft.TextStyle(letter_spacing=0.6),
                ),
                padding=ft.padding.only(top=8, bottom=4),
            )
        )
        for s in items:
            if not isinstance(s, dict):
                continue
            quote = (s.get("evidence_quote") or "").strip()
            reason = (s.get("reason") or "").strip()
            anchor = s.get("evidence_anchor") or ""
            rows.append(
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Text(
                                str(s.get("name") or ""),
                                color=theme.text,
                                size=12,
                                weight=ft.FontWeight.W_600,
                            ),
                            padding=ft.padding.symmetric(horizontal=10, vertical=4),
                            bgcolor=theme.surface_2,
                            border=ft.border.all(1, theme.border),
                            border_radius=8,
                        ),
                        ft.Text(
                            quote or reason,
                            color=theme.text_muted,
                            size=11,
                            expand=True,
                        ),
                        _evidence_chip(theme, _evidence_label(anchor, txt)) if anchor else ft.Container(),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
    return _section_card(
        theme,
        icon=ft.Icons.STAR_OUTLINE,
        title=txt["output_skills_title"],
        body=ft.Column(controls=rows, spacing=4, tight=True),
    )


def _featured_card(theme: Theme, txt: dict) -> ft.Container:
    items = (STATE.featured or {}).get("items") or []
    if not items:
        return _section_card(
            theme,
            icon=ft.Icons.PUSH_PIN_OUTLINED,
            title=txt["output_featured_title"],
            body=ft.Text(txt["output_no_evidence_skip"], color=theme.text_muted, size=12),
        )
    rows: list[ft.Control] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or ""
        kind = item.get("kind") or ""
        desc = (item.get("description") or "").strip()
        link = (item.get("link") or "").strip()
        todo = (item.get("todo") or "").strip()
        anchor = item.get("evidence_anchor") or ""
        chunk: list[ft.Control] = [
            ft.Row(
                controls=[
                    ft.Text(title, color=theme.text, size=13, weight=ft.FontWeight.W_700, expand=True),
                    ft.Text(kind, color=theme.text_muted, size=11, italic=True),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ]
        if desc:
            chunk.append(ft.Text(desc, color=theme.text, size=12, selectable=True))
        if link:
            chunk.append(ft.Text(link, color=theme.primary, size=11, selectable=True))
        if todo:
            chunk.append(
                ft.Text(
                    f"TODO: {todo}",
                    color="#F59E0B",
                    size=11,
                    italic=True,
                )
            )
        if anchor:
            chunk.append(_evidence_chip(theme, _evidence_label(anchor, txt)))
        rows.append(
            ft.Container(
                content=ft.Column(controls=chunk, spacing=4, tight=True),
                padding=12,
                bgcolor=theme.surface_2,
                border_radius=10,
                border=ft.border.all(1, theme.border),
            )
        )
    return _section_card(
        theme,
        icon=ft.Icons.PUSH_PIN_OUTLINED,
        title=txt["output_featured_title"],
        body=ft.Column(controls=rows, spacing=8, tight=True),
    )


def _projects_card(theme: Theme, txt: dict) -> ft.Container:
    projects = (STATE.projects or {}).get("projects") or []
    if not projects:
        return _section_card(
            theme,
            icon=ft.Icons.FOLDER_SPECIAL_OUTLINED,
            title=txt["output_projects_title"],
            body=ft.Text(txt["output_no_evidence_skip"], color=theme.text_muted, size=12),
        )
    rows: list[ft.Control] = []
    for proj in projects:
        if not isinstance(proj, dict):
            continue
        title = proj.get("title") or ""
        period = proj.get("period") or ""
        desc = (proj.get("description") or "").strip()
        techs = proj.get("technologies") or []
        link = (proj.get("link") or "").strip()
        chunk: list[ft.Control] = [
            ft.Row(
                controls=[
                    ft.Text(title, color=theme.text, size=13, weight=ft.FontWeight.W_700, expand=True),
                    ft.Text(period, color=theme.text_muted, size=11, italic=True),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ]
        if desc:
            chunk.append(ft.Text(desc, color=theme.text, size=12, selectable=True))
        if techs:
            chunk.append(
                ft.Row(
                    controls=[_evidence_chip(theme, t) for t in techs],
                    spacing=6,
                    run_spacing=6,
                    wrap=True,
                )
            )
        if link:
            chunk.append(ft.Text(link, color=theme.primary, size=11, selectable=True))
        rows.append(
            ft.Container(
                content=ft.Column(controls=chunk, spacing=4, tight=True),
                padding=12,
                bgcolor=theme.surface_2,
                border_radius=10,
                border=ft.border.all(1, theme.border),
            )
        )
    return _section_card(
        theme,
        icon=ft.Icons.FOLDER_SPECIAL_OUTLINED,
        title=txt["output_projects_title"],
        body=ft.Column(controls=rows, spacing=8, tight=True),
    )


def _certifications_card(theme: Theme, txt: dict) -> ft.Container:
    payload = STATE.certifications_rewrites or {}
    if not payload:
        return _section_card(
            theme,
            icon=ft.Icons.WORKSPACE_PREMIUM_OUTLINED,
            title=txt["output_certifications_title"],
            body=ft.Text(txt["output_no_evidence_skip"], color=theme.text_muted, size=12),
        )
    existing = payload.get("existing") or []
    recommended = payload.get("recommended") or []
    rows: list[ft.Control] = []
    for cert in existing:
        if not isinstance(cert, dict):
            continue
        name = cert.get("name") or ""
        issuer = cert.get("issuer") or ""
        year = cert.get("year") or ""
        desc = (cert.get("linkedin_description") or "").strip()
        rows.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            f"{name} ({issuer}, {year})",
                            color=theme.text, size=12, weight=ft.FontWeight.W_700,
                        ),
                        ft.Text(desc, color=theme.text_muted, size=11) if desc else ft.Container(),
                    ],
                    spacing=2,
                    tight=True,
                ),
                padding=10,
                bgcolor=theme.surface_2,
                border_radius=10,
                border=ft.border.all(1, theme.border),
            )
        )
    for cert in recommended:
        if not isinstance(cert, dict):
            continue
        name = cert.get("name") or ""
        issuer = cert.get("issuer") or ""
        why = (cert.get("why_it_matters") or "").strip()
        rows.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                _evidence_chip(theme, "Recommended"),
                                ft.Text(
                                    f"{name} ({issuer})",
                                    color=theme.text, size=12, weight=ft.FontWeight.W_700,
                                    expand=True,
                                ),
                            ],
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Text(why, color=theme.text_muted, size=11) if why else ft.Container(),
                    ],
                    spacing=4,
                    tight=True,
                ),
                padding=10,
                bgcolor=theme.surface_2,
                border_radius=10,
                border=ft.border.all(1, theme.border),
            )
        )
    return _section_card(
        theme,
        icon=ft.Icons.WORKSPACE_PREMIUM_OUTLINED,
        title=txt["output_certifications_title"],
        body=ft.Column(controls=rows, spacing=8, tight=True),
    )


def _education_card(theme: Theme, txt: dict) -> ft.Container:
    entries = (STATE.education_rewrites or {}).get("entries") or []
    if not entries:
        return _section_card(
            theme,
            icon=ft.Icons.SCHOOL_OUTLINED,
            title=txt["output_education_title"],
            body=ft.Text(txt["output_no_evidence_skip"], color=theme.text_muted, size=12),
        )
    rows: list[ft.Control] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        institution = entry.get("institution") or ""
        degree = entry.get("degree") or ""
        period = entry.get("period") or ""
        desc = (entry.get("linkedin_description") or "").strip()
        connection = (entry.get("connection_to_target") or "").strip()
        coursework = entry.get("relevant_coursework") or []
        chunk: list[ft.Control] = [
            ft.Text(institution, color=theme.text, size=13, weight=ft.FontWeight.W_700),
            ft.Text(
                f"{degree} · {period}".strip(" ·"),
                color=theme.text_muted, size=11, italic=True,
            ),
        ]
        if desc:
            chunk.append(ft.Text(desc, color=theme.text, size=12, selectable=True))
        if coursework:
            chunk.append(
                ft.Row(
                    controls=[_evidence_chip(theme, c) for c in coursework],
                    spacing=6,
                    run_spacing=6,
                    wrap=True,
                )
            )
        if connection:
            chunk.append(ft.Text(connection, color=theme.text_muted, size=11, italic=True))
        rows.append(
            ft.Container(
                content=ft.Column(controls=chunk, spacing=4, tight=True),
                padding=10,
                bgcolor=theme.surface_2,
                border_radius=10,
                border=ft.border.all(1, theme.border),
            )
        )
    return _section_card(
        theme,
        icon=ft.Icons.SCHOOL_OUTLINED,
        title=txt["output_education_title"],
        body=ft.Column(controls=rows, spacing=8, tight=True),
    )


def _services_card(theme: Theme, txt: dict) -> ft.Container:
    payload = STATE.services or {}
    if not payload:
        return _section_card(
            theme,
            icon=ft.Icons.HANDYMAN_OUTLINED,
            title=txt["output_services_title"],
            body=ft.Text(txt["output_no_evidence_skip"], color=theme.text_muted, size=12),
        )
    services = payload.get("services") or []
    if not services:
        skip = payload.get("skip_reason") or txt["output_no_evidence_skip"]
        return _section_card(
            theme,
            icon=ft.Icons.HANDYMAN_OUTLINED,
            title=txt["output_services_title"],
            body=ft.Text(skip, color=theme.text_muted, size=12),
        )
    rows: list[ft.Control] = []
    for svc in services:
        if not isinstance(svc, dict):
            continue
        name = svc.get("name") or ""
        desc = (svc.get("short_description") or "").strip()
        cred = (svc.get("why_credible") or "").strip()
        rows.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(name, color=theme.text, size=13, weight=ft.FontWeight.W_700),
                        ft.Text(desc, color=theme.text, size=12, selectable=True) if desc else ft.Container(),
                        ft.Text(cred, color=theme.text_muted, size=11, italic=True) if cred else ft.Container(),
                    ],
                    spacing=4,
                    tight=True,
                ),
                padding=10,
                bgcolor=theme.surface_2,
                border_radius=10,
                border=ft.border.all(1, theme.border),
            )
        )
    return _section_card(
        theme,
        icon=ft.Icons.HANDYMAN_OUTLINED,
        title=txt["output_services_title"],
        body=ft.Column(controls=rows, spacing=8, tight=True),
    )


def _courses_card(theme: Theme, txt: dict) -> ft.Container:
    payload = STATE.courses or {}
    if not payload:
        return _section_card(
            theme,
            icon=ft.Icons.MENU_BOOK_OUTLINED,
            title=txt["output_courses_title"],
            body=ft.Text(txt["output_no_evidence_skip"], color=theme.text_muted, size=12),
        )
    rows: list[ft.Control] = []
    for cert in payload.get("existing") or []:
        if not isinstance(cert, dict):
            continue
        rows.append(
            ft.Text(
                f"{cert.get('title') or ''} ({cert.get('provider') or ''})",
                color=theme.text, size=12,
            )
        )
    for rec in payload.get("recommended") or []:
        if not isinstance(rec, dict):
            continue
        rows.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            f"{rec.get('title') or ''} · {rec.get('provider') or ''}",
                            color=theme.text, size=12, weight=ft.FontWeight.W_700,
                        ),
                        ft.Text(
                            rec.get("why_it_matters") or "",
                            color=theme.text_muted, size=11,
                        ),
                    ],
                    spacing=2,
                    tight=True,
                ),
                padding=10,
                bgcolor=theme.surface_2,
                border_radius=10,
                border=ft.border.all(1, theme.border),
            )
        )
    return _section_card(
        theme,
        icon=ft.Icons.MENU_BOOK_OUTLINED,
        title=txt["output_courses_title"],
        body=ft.Column(controls=rows, spacing=6, tight=True),
    )


def _recommendations_card(theme: Theme, txt: dict) -> ft.Container:
    templates = (STATE.recommendation_messages or {}).get("templates") or []
    if not templates:
        return _section_card(
            theme,
            icon=ft.Icons.MAIL_OUTLINE,
            title=txt["output_recommendations_title"],
            body=ft.Text(txt["output_no_evidence_skip"], color=theme.text_muted, size=12),
        )
    rows: list[ft.Control] = []
    for tpl in templates:
        if not isinstance(tpl, dict):
            continue
        recipient = tpl.get("suggested_recipient_label") or "—"
        rec_kind = tpl.get("recipient_type") or ""
        body = (tpl.get("message") or "").strip()
        followup = (tpl.get("follow_up") or "").strip()
        chunk: list[ft.Control] = [
            ft.Row(
                controls=[
                    ft.Text(recipient, color=theme.text, size=13, weight=ft.FontWeight.W_700, expand=True),
                    ft.Text(rec_kind, color=theme.text_muted, size=11, italic=True),
                    _copy_button(theme, txt, lambda b=body: b),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ]
        if body:
            chunk.append(ft.Text(body, color=theme.text, size=12, selectable=True))
        if followup:
            chunk.append(
                ft.Text(
                    f"Follow-up: {followup}",
                    color=theme.text_muted, size=11, italic=True,
                )
            )
        rows.append(
            ft.Container(
                content=ft.Column(controls=chunk, spacing=4, tight=True),
                padding=12,
                bgcolor=theme.surface_2,
                border_radius=10,
                border=ft.border.all(1, theme.border),
            )
        )
    return _section_card(
        theme,
        icon=ft.Icons.MAIL_OUTLINE,
        title=txt["output_recommendations_title"],
        body=ft.Column(controls=rows, spacing=8, tight=True),
    )


def _posts_card(theme: Theme, txt: dict) -> ft.Container:
    posts = (STATE.posts or {}).get("posts") or []
    if not posts:
        return _section_card(
            theme,
            icon=ft.Icons.POST_ADD,
            title=txt["output_posts_title"],
            body=ft.Text(txt["output_no_evidence_skip"], color=theme.text_muted, size=12),
        )
    rows: list[ft.Control] = []
    for post in posts:
        if not isinstance(post, dict):
            continue
        kind = post.get("kind") or ""
        title = post.get("title") or ""
        chars = post.get("char_count")
        body = (post.get("body") or "").strip()
        hashtags = post.get("hashtags") or []
        chunk: list[ft.Control] = [
            ft.Row(
                controls=[
                    _evidence_chip(theme, kind),
                    ft.Text(title, color=theme.text, size=13, weight=ft.FontWeight.W_700, expand=True),
                    ft.Text(
                        f"{chars} {txt['output_chars_suffix']}" if chars is not None else "",
                        color=theme.text_muted, size=11,
                    ),
                    _copy_button(theme, txt, lambda b=body: b),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Text(body, color=theme.text, size=12, selectable=True),
        ]
        if hashtags:
            chunk.append(
                ft.Text(
                    " ".join(hashtags),
                    color=theme.primary, size=11, weight=ft.FontWeight.W_500,
                )
            )
        rows.append(
            ft.Container(
                content=ft.Column(controls=chunk, spacing=4, tight=True),
                padding=12,
                bgcolor=theme.surface_2,
                border_radius=10,
                border=ft.border.all(1, theme.border),
            )
        )
    return _section_card(
        theme,
        icon=ft.Icons.POST_ADD,
        title=txt["output_posts_title"],
        body=ft.Column(controls=rows, spacing=8, tight=True),
    )


def _unsupported_card(theme: Theme, txt: dict) -> Optional[ft.Container]:
    rows = (STATE.unsupported_claims or {}).get("rows") or []
    if not rows:
        return None
    items: list[ft.Control] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        items.append(
            ft.Row(
                controls=[
                    ft.Icon(ft.Icons.WARNING_AMBER_OUTLINED, color="#F59E0B", size=14),
                    ft.Column(
                        controls=[
                            ft.Text(
                                row.get("label") or "",
                                color=theme.text, size=12, weight=ft.FontWeight.W_600,
                            ),
                            ft.Text(
                                row.get("reason") or "",
                                color=theme.text_muted, size=11,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                        tight=True,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        )
    return _section_card(
        theme,
        icon=ft.Icons.WARNING_AMBER_OUTLINED,
        title=txt["output_unsupported_title"],
        body=ft.Column(controls=items, spacing=6, tight=True),
    )


def build_output_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Callable[[], None],
    on_navigate_tab: Callable[[int], None],
) -> ft.Column:
    txt = s(lang)

    if not STATE.has_results():
        return ft.Column(
            controls=[_empty_state(theme, txt, on_navigate_tab)],
            spacing=0,
            expand=True,
            tight=True,
        )

    cards: list[ft.Control] = [
        _score_banner(theme, txt),
        _checklist_card(theme, txt),
        _headlines_card(theme, txt),
        _about_card(theme, txt),
        _experience_card(theme, txt),
        _bucketed_skills_card(theme, txt),
        _featured_card(theme, txt),
        _projects_card(theme, txt),
        _certifications_card(theme, txt),
        _education_card(theme, txt),
        _services_card(theme, txt),
        _courses_card(theme, txt),
        _recommendations_card(theme, txt),
        _posts_card(theme, txt),
    ]
    unsupported = _unsupported_card(theme, txt)
    if unsupported is not None:
        cards.append(unsupported)

    body = ft.ListView(
        controls=cards,
        spacing=14,
        padding=ft.padding.symmetric(horizontal=24, vertical=18),
        expand=True,
    )

    save_holder = ft.Container()

    def _on_open_folder(_e: ft.ControlEvent) -> None:
        if STATE.last_run_folder:
            _open_in_explorer(STATE.last_run_folder)

    def _on_save(e: ft.ControlEvent) -> None:
        page = e.page
        if page is not None:
            REFS.page = page
        STATE.activity = "saving"
        safe(REFS.rerender_context)

        def _worker() -> None:
            try:
                pipeline.save_full_profile()
            except Exception as exc:
                logger_service.log_exception(
                    "ai_linkedin.tab_output", "save_worker_failed", exc,
                )
            REFS.dispatch(_request_full_refresh)

        threading.Thread(target=_worker, daemon=True).start()

    save_btn = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.SAVE_OUTLINED, color=ft.Colors.WHITE, size=14),
                ft.Text(
                    txt["output_save_button"],
                    color=ft.Colors.WHITE, size=12, weight=ft.FontWeight.W_600,
                ),
            ],
            spacing=6,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        bgcolor=theme.primary,
        border_radius=10,
        ink=True,
        on_click=_on_save,
    )
    open_btn = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.FOLDER_OPEN, color=theme.text, size=14),
                ft.Text(
                    txt["output_open_folder_button"],
                    color=theme.text, size=12, weight=ft.FontWeight.W_600,
                ),
            ],
            spacing=6,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        bgcolor=theme.surface_2,
        border=ft.border.all(1, theme.border),
        border_radius=10,
        ink=bool(STATE.last_run_folder),
        opacity=1.0 if STATE.last_run_folder else 0.55,
        on_click=_on_open_folder if STATE.last_run_folder else None,
    )
    save_holder.content = ft.Row(
        controls=[
            open_btn,
            ft.Container(expand=True),
            save_btn,
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    footer = ft.Container(
        content=save_holder,
        padding=ft.padding.symmetric(horizontal=24, vertical=12),
        border=ft.border.only(top=ft.BorderSide(1, theme.border)),
        bgcolor=theme.bg,
    )

    return ft.Column(
        controls=[body, footer],
        spacing=0,
        expand=True,
        tight=True,
    )
