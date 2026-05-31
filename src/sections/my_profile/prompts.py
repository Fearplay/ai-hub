"""Prompts for the shared career-profile extraction.

The system prompt restates the domain rules (the global no-hallucination
clause is added by ``ai_provider.run``). The task is a pure extraction:
read the CV (+ optional LinkedIn export + GitHub summary + notes) and emit
the unified ``CAREER_PROFILE_SCHEMA`` JSON - no tailoring to any job.
"""

from __future__ import annotations

from typing import Any


PROFILE_RULES = """\
You are a meticulous career-data extractor. You read a person's CV and
supporting materials and produce ONE structured profile.

POLICY (binding - never break these):

1. NO HALLUCINATION. Never invent facts, employers, projects,
   certifications, metrics, dates, contact details, links or quotes. Use
   only what is present in the provided context. If a value is missing,
   leave it empty ("" or []) - never fabricate.

2. KEEP EVERYTHING. Every work experience, education entry, certification
   and language present in the source must appear in the output. Do not
   drop entries to save space.

3. DEDUPLICATION. One job / school / certification / language = one row.
   Merge obvious CZ/EN duplicates rather than listing them twice.

4. OUTPUT LANGUAGE. Every human-readable string must be in the declared
   OUTPUT_LANGUAGE. Technology names and proper nouns are exempt.

5. PERIODS. Keep date ranges in the format the source uses
   (e.g. "2022-2024", "06/2022 - 09/2024").

6. LANGUAGES - CEFR ONLY. Map proficiency to the closest A1/A2/B1/B2/C1/C2
   level, or leave it empty. Never "Native" / "Fluent" / "Intermediate".

7. LINKS. Only include online_links that literally appear in the source
   (portfolio, personal site, LinkedIn, GitHub). Never invent a URL.

8. ASCII PUNCTUATION. Use plain hyphens (-), never em/en dashes.
"""


PROFILE_SYSTEM = (
    PROFILE_RULES
    + "\n\nTASK: Read the resume text (and optional LinkedIn export, GitHub "
    "summary and free-form notes) and emit the person as the structured JSON "
    "described by the schema. This is a neutral profile - do NOT tailor it to "
    "any specific job. Apply rules 1-8. If a section is empty in the source, "
    "leave the corresponding array empty."
)


def _language_directive(output_lang: str) -> str:
    lang = "Czech" if (output_lang or "").startswith("cs") else "English"
    return f"OUTPUT_LANGUAGE: {lang}. Write every human-readable value in {lang}."


def _trim(text: str, limit: int) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


def build_profile_user(
    *,
    output_lang: str,
    resume_text: str,
    linkedin_text: str = "",
    github_summary: str = "",
    notes: str = "",
) -> str:
    parts: list[str] = [
        _language_directive(output_lang),
        "",
        "=== RESUME TEXT ===",
        _trim(resume_text, 18000),
    ]
    if linkedin_text:
        parts += ["", "=== LINKEDIN EXPORT ===", _trim(linkedin_text, 8000)]
    if github_summary:
        parts += ["", "=== GITHUB SUMMARY ===", _trim(github_summary, 4000)]
    if notes:
        parts += ["", "=== USER NOTES ===", _trim(notes, 2000)]
    parts += ["", "Return only the profile JSON described by the schema."]
    return "\n".join(parts)


def serialize_github_summary(profile: Any) -> str:
    """Compact text view of a ``GitHubProfile`` for the extraction prompt."""
    if profile is None:
        return ""
    lines: list[str] = []
    user_part = f"{getattr(profile, 'name', '') or ''} (@{getattr(profile, 'username', '')})".strip()
    lines.append(user_part)
    if getattr(profile, "bio", None):
        lines.append(f"Bio: {profile.bio}")
    if getattr(profile, "location", None):
        lines.append(f"Location: {profile.location}")
    lines.append(
        f"Public repos: {getattr(profile, 'public_repos', 0)}, "
        f"followers: {getattr(profile, 'followers', 0)}"
    )
    repos = getattr(profile, "repos", None) or []
    if repos:
        lines.append("")
        lines.append("Top repositories:")
        for repo in repos:
            langs = ", ".join(getattr(repo, "languages", []) or []) or "-"
            lines.append(
                f"- {getattr(repo, 'name', '')} | stars {getattr(repo, 'stars', 0)} "
                f"| langs {langs} | {getattr(repo, 'description', '') or '-'}"
            )
    return "\n".join(lines)
