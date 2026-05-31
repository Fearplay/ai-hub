"""Deterministic generator for the big ``full_linkedin_profile.html``.

We render every cached LinkedIn section (headlines, about, experience
rewrite, skills buckets, featured, projects, services, courses,
recommendation requests, posts, completeness checklist, unsupported
claims, profile score) into one printable, self-contained HTML
document the user can mail to themselves or attach to a recruiter
exchange.

No LLM call - this is a pure cache-to-HTML rollup. ``profile_score``
shows up as a banner at the top, the completeness checklist becomes a
TOC the user can click. Every section gracefully no-ops when its
payload is missing so the document still renders mid-pipeline.
"""

from __future__ import annotations

from html import escape
from typing import Any, Optional

from src.sections.ai_linkedin import themes


def render_full_profile_html(
    *,
    extracted_profile: dict,
    headlines: Optional[dict],
    about: Optional[dict],
    experience_rewrites: Optional[dict],
    education_rewrites: Optional[dict],
    certifications_rewrites: Optional[dict],
    skills_buckets: Optional[dict],
    featured: Optional[dict],
    projects: Optional[dict],
    services: Optional[dict],
    courses: Optional[dict],
    recommendation_messages: Optional[dict],
    posts: Optional[dict],
    completeness: Optional[dict],
    unsupported_claims: Optional[dict],
    profile_score: Optional[dict],
    target_roles: list[str],
    audience: str,
    tone: str,
    output_lang: str,
    timestamp: str,
    theme_slug: str | None = None,
) -> str:
    """Return a self-contained HTML document with every cached section."""
    is_cs = (output_lang or "en").lower() == "cs"
    theme = themes.resolve_theme(theme_slug)

    name = (extracted_profile or {}).get("full_name") or _h(
        "Your name", "Tvoje jméno", is_cs,
    )
    sub = (extracted_profile or {}).get("headline_current") or ""

    sections_html: list[str] = []
    toc_entries: list[tuple[str, str]] = []

    def _add_section(anchor: str, title: str, body: str) -> None:
        if not body.strip():
            return
        toc_entries.append((anchor, title))
        sections_html.append(
            f'<section id="{anchor}"><h2>{escape(title)}</h2>{body}</section>'
        )

    if profile_score:
        score = profile_score.get("score", 0)
        max_score = profile_score.get("max", 100)
        breakdown_rows = "".join(
            f'<tr><td>{escape(item.get("label", ""))}</td>'
            f'<td>{item.get("weight", 0)}</td>'
            f'<td>{item.get("factor", 0):.2f}</td>'
            f'<td>{item.get("contribution", 0):.1f}</td></tr>'
            for item in (profile_score.get("breakdown") or [])
        )
        score_banner = (
            f'<div class="score-banner"><div class="score-num">{score}<span>/{max_score}</span></div>'
            f'<div class="score-label">{escape(_h("LinkedIn profile score", "Skóre LinkedIn profilu", is_cs))}</div>'
            f'<details><summary>{escape(_h("Breakdown", "Rozpis", is_cs))}</summary>'
            f'<table><thead><tr><th>{escape(_h("Section", "Sekce", is_cs))}</th>'
            f'<th>{escape(_h("Weight", "Váha", is_cs))}</th>'
            f'<th>{escape(_h("Factor", "Koeficient", is_cs))}</th>'
            f'<th>{escape(_h("Contribution", "Příspěvek", is_cs))}</th></tr></thead>'
            f'<tbody>{breakdown_rows}</tbody></table></details></div>'
        )
    else:
        score_banner = ""

    if headlines:
        body_lines = []
        for v in headlines.get("variants") or []:
            text = escape(v.get("text") or "")
            chars = v.get("char_count")
            focus = escape(v.get("focus") or "")
            audience_label = escape(v.get("audience") or "")
            body_lines.append(
                f'<div class="card"><div class="badges"><span class="badge">{focus}</span>'
                f'<span class="badge">{audience_label}</span>'
                f'<span class="badge">{chars} {escape(_h("chars", "znaků", is_cs))}</span></div>'
                f'<p class="big">{text}</p></div>'
            )
        _add_section(
            "headlines",
            _h("Headline variants", "Varianty headlinu", is_cs),
            "".join(body_lines),
        )

    if about:
        sections = [
            ("short_version", _h("Short", "Krátká", is_cs)),
            ("medium_version", _h("Medium", "Střední", is_cs)),
            ("long_version", _h("Long", "Dlouhá", is_cs)),
            ("technical_version", _h("Technical", "Technická", is_cs)),
            ("recruiter_version", _h("Recruiter-friendly", "Recruiter-friendly", is_cs)),
        ]
        char_counts = about.get("char_counts") or {}
        rows = []
        for key, label in sections:
            body = (about.get(key) or "").strip()
            if not body:
                continue
            n = char_counts.get(key, len(body))
            rows.append(
                f'<div class="card"><h3>{escape(label)} <span class="muted">({n})</span></h3>'
                f'<p class="multiline">{escape(body)}</p></div>'
            )
        _add_section("about", _h("About / Intro", "About / Úvod", is_cs), "".join(rows))

    if experience_rewrites:
        rows = []
        for role in experience_rewrites.get("roles") or []:
            if not isinstance(role, dict):
                continue
            title = f"{escape(role.get('role') or '')} - {escape(role.get('company') or '')}".strip(" -")
            period = escape(role.get("period") or "")
            desc = escape((role.get("linkedin_description") or "").strip())
            bullets = "".join(f"<li>{escape(b)}</li>" for b in role.get("bullets") or [])
            skills = ", ".join(escape(s.get("name") or "") for s in role.get("suggested_skills") or [] if isinstance(s, dict))
            do_not = role.get("do_not_claim") or []
            do_not_html = ""
            if do_not:
                do_not_html = (
                    f"<div class=\"warn\"><strong>{escape(_h('Do NOT claim', 'NEUVÁDĚT', is_cs))}:</strong>"
                    + "<ul>"
                    + "".join(f"<li>{escape(n)}</li>" for n in do_not)
                    + "</ul></div>"
                )
            rows.append(
                f'<div class="card"><h3>{title}</h3><p class="muted">{period}</p>'
                + (f'<p>{desc}</p>' if desc else '')
                + (f'<ul>{bullets}</ul>' if bullets else '')
                + (f'<p><strong>{escape(_h("Skills:", "Skills:", is_cs))}</strong> {skills}</p>' if skills else '')
                + do_not_html
                + '</div>'
            )
        _add_section("experience", _h("Experience rewrite", "Přepis zkušeností", is_cs), "".join(rows))

    if skills_buckets:
        bucket_labels = [
            ("core", _h("Claim now", "Uveď hned", is_cs)),
            ("to_verify", _h("Verify first", "Nejdřív ověř", is_cs)),
            ("to_learn", _h("Learn next", "Naučit se příště", is_cs)),
            ("do_not_claim", _h("Do not claim", "Neuvádět", is_cs)),
        ]
        rows = []
        for key, label in bucket_labels:
            items = skills_buckets.get(key) or []
            if not items:
                continue
            chips = "".join(
                f'<span class="chip" title="{escape(s.get("evidence_anchor") or "")}">{escape(s.get("name") or "")}</span>'
                for s in items if isinstance(s, dict)
            )
            rows.append(
                f'<div class="card"><h3>{escape(label)}</h3><div class="chips">{chips}</div></div>'
            )
        _add_section("skills", _h("Skills recommendation", "Doporučení skills", is_cs), "".join(rows))

    if featured:
        rows = []
        for item in featured.get("items") or []:
            if not isinstance(item, dict):
                continue
            title = escape(item.get("title") or "")
            kind = escape(item.get("kind") or "")
            desc = escape(item.get("description") or "")
            link = (item.get("link") or "").strip()
            link_html = (
                f'<p><a href="{escape(link)}" target="_blank" rel="noopener">{escape(link)}</a></p>'
                if link
                else ""
            )
            todo = (item.get("todo") or "").strip()
            todo_html = f'<p class="warn">{escape(todo)}</p>' if todo else ""
            rows.append(
                f'<div class="card"><h3>{title} <span class="muted">({kind})</span></h3>'
                f'<p>{desc}</p>{link_html}{todo_html}</div>'
            )
        _add_section("featured", _h("Featured suggestions", "Featured návrhy", is_cs), "".join(rows))

    if projects:
        rows = []
        for proj in projects.get("projects") or []:
            if not isinstance(proj, dict):
                continue
            title = escape(proj.get("title") or "")
            period = escape(proj.get("period") or "")
            desc = escape(proj.get("description") or "")
            techs = ", ".join(escape(t) for t in proj.get("technologies") or [])
            link = (proj.get("link") or "").strip()
            link_html = (
                f'<p><a href="{escape(link)}" target="_blank" rel="noopener">{escape(link)}</a></p>'
                if link
                else ""
            )
            rows.append(
                f'<div class="card"><h3>{title}</h3><p class="muted">{period}</p>'
                f'<p>{desc}</p>'
                + (f'<p><strong>{escape(_h("Stack", "Stack", is_cs))}:</strong> {techs}</p>' if techs else '')
                + link_html
                + '</div>'
            )
        _add_section("projects", _h("Projects", "Projekty", is_cs), "".join(rows))

    if certifications_rewrites:
        rows = []
        existing = certifications_rewrites.get("existing") or []
        if existing:
            cert_rows = "".join(
                f'<li><strong>{escape(c.get("name") or "")}</strong> ({escape(c.get("issuer") or "")}, '
                f'{escape(c.get("year") or "")}) - {escape(c.get("priority") or "")}<br>'
                f'<span class="muted">{escape(c.get("linkedin_description") or "")}</span></li>'
                for c in existing if isinstance(c, dict)
            )
            rows.append(
                f'<div class="card"><h3>{escape(_h("Existing", "Stávající", is_cs))}</h3>'
                f'<ul>{cert_rows}</ul></div>'
            )
        recommended = certifications_rewrites.get("recommended") or []
        if recommended:
            rec_rows = "".join(
                f'<li><strong>{escape(c.get("name") or "")}</strong> ({escape(c.get("issuer") or "")}) - '
                f'{escape(c.get("why_it_matters") or "")}</li>'
                for c in recommended if isinstance(c, dict)
            )
            rows.append(
                f'<div class="card"><h3>{escape(_h("Recommended", "Doporučené", is_cs))}</h3>'
                f'<ul>{rec_rows}</ul></div>'
            )
        _add_section("certifications", _h("Certifications", "Certifikace", is_cs), "".join(rows))

    if education_rewrites:
        rows = []
        for entry in education_rewrites.get("entries") or []:
            if not isinstance(entry, dict):
                continue
            inst = escape(entry.get("institution") or "")
            degree = escape(entry.get("degree") or "")
            period = escape(entry.get("period") or "")
            desc = escape(entry.get("linkedin_description") or "")
            connection = escape((entry.get("connection_to_target") or "").strip())
            coursework = ", ".join(escape(c) for c in entry.get("relevant_coursework") or [])
            rows.append(
                f'<div class="card"><h3>{inst}</h3>'
                f'<p class="muted">{degree} ({period})</p>'
                f'<p>{desc}</p>'
                + (f'<p><strong>{escape(_h("Coursework", "Předměty", is_cs))}:</strong> {coursework}</p>' if coursework else '')
                + (f'<p><em>{connection}</em></p>' if connection else '')
                + '</div>'
            )
        _add_section("education", _h("Education", "Vzdělání", is_cs), "".join(rows))

    if services:
        services_list = services.get("services") or []
        skip_reason = (services.get("skip_reason") or "").strip()
        if services_list:
            rows = "".join(
                f'<div class="card"><h3>{escape(svc.get("name") or "")}</h3>'
                f'<p>{escape(svc.get("short_description") or "")}</p>'
                f'<p class="muted"><em>{escape(_h("Why credible", "Proč věrohodné", is_cs))}: '
                f'{escape(svc.get("why_credible") or "")}</em></p></div>'
                for svc in services_list if isinstance(svc, dict)
            )
        elif skip_reason:
            rows = f'<div class="card warn">{escape(skip_reason)}</div>'
        else:
            rows = ""
        _add_section("services", _h("Services", "Služby", is_cs), rows)

    if courses:
        rows = []
        existing = courses.get("existing") or []
        if existing:
            existing_rows = "".join(
                f'<li><strong>{escape(c.get("title") or "")}</strong> - '
                f'{escape(c.get("provider") or "")} ({escape(c.get("year") or "")})</li>'
                for c in existing if isinstance(c, dict)
            )
            rows.append(
                f'<div class="card"><h3>{escape(_h("Existing", "Stávající", is_cs))}</h3>'
                f'<ul>{existing_rows}</ul></div>'
            )
        recommended = courses.get("recommended") or []
        if recommended:
            rec_rows = "".join(
                f'<li><strong>{escape(c.get("title") or "")}</strong> - '
                f'{escape(c.get("provider") or "")} (~{c.get("estimated_hours", 0)}h)<br>'
                f'<span class="muted">{escape(c.get("why_it_matters") or "")}</span></li>'
                for c in recommended if isinstance(c, dict)
            )
            rows.append(
                f'<div class="card"><h3>{escape(_h("Recommended next", "Doporučené dál", is_cs))}</h3>'
                f'<ul>{rec_rows}</ul></div>'
            )
        _add_section("courses", _h("Courses & training", "Kurzy & školení", is_cs), "".join(rows))

    if recommendation_messages:
        rows = []
        for tpl in recommendation_messages.get("templates") or []:
            if not isinstance(tpl, dict):
                continue
            recipient = escape(tpl.get("suggested_recipient_label") or "")
            kind = escape(tpl.get("recipient_type") or "")
            body = escape(tpl.get("message") or "")
            follow = escape(tpl.get("follow_up") or "")
            rows.append(
                f'<div class="card"><h3>{recipient} <span class="muted">({kind})</span></h3>'
                f'<p class="multiline">{body}</p>'
                + (f'<p><strong>{escape(_h("Follow-up", "Follow-up", is_cs))}:</strong> {follow}</p>' if follow else '')
                + '</div>'
            )
        _add_section(
            "recommendations",
            _h("Recommendation request templates", "Šablony žádostí o doporučení", is_cs),
            "".join(rows),
        )

    if posts:
        rows = []
        for post in posts.get("posts") or []:
            if not isinstance(post, dict):
                continue
            kind = escape(post.get("kind") or "")
            title = escape(post.get("title") or "")
            body = escape(post.get("body") or "")
            chars = post.get("char_count")
            hashtags = " ".join(escape(t) for t in post.get("hashtags") or [])
            rows.append(
                f'<div class="card"><h3>[{kind}] {title} <span class="muted">({chars} {escape(_h("chars", "znaků", is_cs))})</span></h3>'
                f'<p class="multiline">{body}</p>'
                + (f'<p class="muted">{hashtags}</p>' if hashtags else '')
                + '</div>'
            )
        _add_section("posts", _h("LinkedIn posts", "LinkedIn posty", is_cs), "".join(rows))

    if completeness:
        priority_labels = {
            "high": _h("High priority", "Vysoká priorita", is_cs),
            "medium": _h("Medium priority", "Střední priorita", is_cs),
            "low": _h("Low priority", "Nízká priorita", is_cs),
            "skip": _h("Skip", "Vynechat", is_cs),
        }
        rows = []
        for prio in ("high", "medium", "low", "skip"):
            items = [i for i in (completeness.get("items") or []) if i.get("priority") == prio]
            if not items:
                continue
            list_html = "".join(
                f'<li>{"✅" if i.get("ok") else "🟡"} <strong>{escape(i.get("label") or "")}</strong> - '
                f'{escape(i.get("reason") or "")}</li>'
                for i in items
            )
            rows.append(
                f'<div class="card"><h3>{escape(priority_labels[prio])}</h3>'
                f'<ul class="checklist">{list_html}</ul></div>'
            )
        _add_section("checklist", _h("Profile completeness", "Úplnost profilu", is_cs), "".join(rows))

    if unsupported_claims and (unsupported_claims.get("rows") or []):
        list_html = "".join(
            f'<li><strong>{escape(r.get("label") or "")}</strong> '
            f'<span class="muted">({escape(r.get("kind") or "")})</span><br>'
            f'<span>{escape(r.get("reason") or "")}</span></li>'
            for r in (unsupported_claims.get("rows") or [])
            if isinstance(r, dict)
        )
        body = (
            f'<div class="card warn"><ul>{list_html}</ul></div>'
            f'<p class="muted">{escape(_h("Confirm before adding to LinkedIn.", "Před přidáním na LinkedIn ověř.", is_cs))}</p>'
        )
        _add_section("unsupported", _h("Unsupported claims report", "Nepodložená tvrzení", is_cs), body)

    toc_html = "".join(
        f'<li><a href="#{escape(anchor)}">{escape(title)}</a></li>'
        for anchor, title in toc_entries
    )

    target_roles_html = ", ".join(escape(r) for r in target_roles) or "-"
    css = _css(theme)

    return (
        "<!doctype html>\n<html><head>\n"
        '<meta charset="utf-8" />\n'
        f'<title>{escape(name)} - LinkedIn profile build</title>\n'
        f'<style>{css}</style>\n'
        "</head><body>\n"
        f'<header class="hero">'
        f'<h1>{escape(name)}</h1>'
        + (f'<p class="hero-sub">{escape(sub)}</p>' if sub else '')
        + f'<p class="muted">{escape(_h("Generated", "Vygenerováno", is_cs))}: {escape(timestamp)}'
        f' • {escape(_h("Roles", "Pozice", is_cs))}: {target_roles_html}'
        f' • {escape(_h("Audience", "Publikum", is_cs))}: {escape(audience)}'
        f' • {escape(_h("Tone", "Tón", is_cs))}: {escape(tone)}</p>'
        f'</header>'
        f'{score_banner}'
        f'<nav class="toc"><h2>{escape(_h("Contents", "Obsah", is_cs))}</h2><ol>{toc_html}</ol></nav>'
        f'<main>{"".join(sections_html)}</main>'
        "</body></html>\n"
    )


def _h(en: str, cs: str, is_cs: bool) -> str:
    return cs if is_cs else en


def _css(theme: themes.ProfileTheme) -> str:
    return (
        f":root {{ --accent: {theme.accent}; --accent-dark: {theme.accent_dark};"
        f" --bg: {theme.bg}; --bg-alt: {theme.bg_alt}; --ink: {theme.ink};"
        f" --muted: {theme.muted}; --border: {theme.border}; }}\n"
        "* { box-sizing: border-box; }\n"
        "* { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }\n"
        "body { font-family: 'Inter', 'Segoe UI', Arial, sans-serif; color: var(--ink);"
        " background: var(--bg); margin: 0; padding: 0; line-height: 1.55; }\n"
        ".hero { background: linear-gradient(135deg, var(--accent), var(--accent-dark));"
        " color: #fff; padding: 32px 48px; }\n"
        ".hero h1 { margin: 0; font-size: 28px; }\n"
        ".hero-sub { margin: 6px 0 4px; font-size: 16px; opacity: 0.95; }\n"
        ".hero .muted { color: rgba(255,255,255,0.85); font-size: 12px; }\n"
        ".score-banner { display: flex; gap: 16px; align-items: center; padding: 16px 48px;"
        " background: var(--bg-alt); border-bottom: 1px solid var(--border); }\n"
        ".score-num { font-size: 38px; font-weight: 700; color: var(--accent); line-height: 1; }\n"
        ".score-num span { color: var(--muted); font-size: 18px; }\n"
        ".score-label { color: var(--muted); }\n"
        ".score-banner details { margin-left: auto; max-width: 520px; }\n"
        ".score-banner table { font-size: 12px; border-collapse: collapse; width: 100%; }\n"
        ".score-banner th, .score-banner td { border-bottom: 1px solid var(--border); padding: 4px 8px; text-align: left; }\n"
        ".toc { padding: 16px 48px; background: var(--bg); border-bottom: 1px solid var(--border); }\n"
        ".toc h2 { font-size: 14px; margin: 0 0 6px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }\n"
        ".toc ol { display: flex; flex-wrap: wrap; gap: 12px; padding: 0; margin: 0; list-style: none; }\n"
        ".toc a { color: var(--accent); text-decoration: none; }\n"
        ".toc a:hover { text-decoration: underline; }\n"
        "main { padding: 24px 48px 64px; max-width: 980px; margin: 0 auto; }\n"
        "section { margin-top: 28px; }\n"
        "section h2 { font-size: 20px; color: var(--ink); border-left: 4px solid var(--accent);"
        " padding-left: 10px; margin-bottom: 12px; }\n"
        ".card { background: var(--bg-alt); border: 1px solid var(--border); border-radius: 10px;"
        " padding: 14px 16px; margin-bottom: 10px; }\n"
        ".card h3 { margin: 0 0 6px; font-size: 16px; }\n"
        ".muted { color: var(--muted); font-size: 12px; }\n"
        ".big { font-size: 16px; }\n"
        ".badges { display: flex; gap: 6px; margin-bottom: 6px; flex-wrap: wrap; }\n"
        ".badge { display: inline-block; padding: 2px 8px; border-radius: 999px;"
        " background: rgba(79, 70, 229, 0.12); color: var(--accent); font-size: 11px;"
        " font-weight: 600; }\n"
        ".chips { display: flex; flex-wrap: wrap; gap: 6px; }\n"
        ".chip { display: inline-block; padding: 4px 10px; border-radius: 999px;"
        " background: var(--bg); border: 1px solid var(--border); font-size: 12px; }\n"
        ".multiline { white-space: pre-wrap; }\n"
        ".warn { background: #FEF3C7; color: #92400E; border-color: #FCD34D; padding: 10px 12px;"
        " border-radius: 8px; margin-top: 6px; }\n"
        ".checklist { list-style: none; padding-left: 0; }\n"
        ".checklist li { padding: 4px 0; }\n"
        "a { color: var(--accent); }\n"
        "a:hover { color: var(--accent-dark); }\n"
        "@media print { .toc, .score-banner details { page-break-inside: avoid; } }\n"
    )
