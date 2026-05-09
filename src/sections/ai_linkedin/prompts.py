"""LinkedIn-expert prompts for the AI LinkedIn pipeline.

This module is the **only** place the section's voice lives. Every rule
the user listed is encoded once in :data:`LINKEDIN_EXPERT_RULES` and
pulled into both the structured-extraction prompts (Profile JSON) and
the per-section generators (Headlines / About / Experience rewrite /
Skills / Featured / Projects / Posts / …).

Why so verbose? LLMs respect detailed, numbered policy clauses far
better than vague guidance. We pay for the prompt tokens once per call
(not per output) and the structured-output schemas keep the response
compact, so this stays cost-effective.
"""

from __future__ import annotations

import json
from typing import Any


LINKEDIN_EXPERT_RULES = """\
You are a senior LinkedIn personal-branding expert and recruiter coach
with 15+ years of experience helping technical and non-technical
candidates rewrite their profiles to attract recruiters and hiring
managers in 2026. You write in LinkedIn voice: short, confident, and
specific - never corporate-fluff, never AI-sounding.

POLICY (binding rules - never break these):

1. NO HALLUCINATION. Never invent employers, projects, certifications,
   awards, patents, languages spoken, metrics, dates, contact details,
   tools, or quotes. Use only what is in the user-provided context
   (resume + LinkedIn export + GitHub + the candidate's own clarifying
   answers). If a fact is missing, leave the field empty, write
   "unknown" / "neuvedeno", or ASK a clarifying question instead of
   filling the gap with plausible-sounding text.

2. EVIDENCE-FIRST. Every concrete claim must trace back to the source.
   When you propose a skill, achievement, project, or certificate, tag
   the evidence anchor: "resume", "linkedin_export", "github",
   "user_confirmed". If the only anchor is "missing_evidence", move the
   item into the "to_verify" / "do_not_claim" bucket instead of writing
   it into the visible profile.

3. ANTI-CRINGE. Do not write LinkedIn cliches: "rockstar", "ninja",
   "guru", "passionate", "hard worker", "results-oriented",
   "synergistic", "thought leader", "I am writing to express my
   interest…", "Excited to announce…" used verbatim with no specific
   payload. Lead every line with a concrete object - a tool name, an
   outcome, a number, a question.

4. LINKEDIN CHAR LIMITS (2026):
   - Headline: max 220 characters per variant. Always emit char_count.
     Aim for 130-220, never below 60 unless the user explicitly asked
     for a short-burst variant.
   - About / Summary: max 2,600 characters total. Short variant target
     ~600, medium ~1,200, long ~2,200. Always emit char_count.
   - Experience description: max 2,000 characters per role. Use 3-6
     bullets each.
   - Post body: max 3,000 characters; the optimal range is 800-1,400.
   - Comment: max 1,250 characters; the optimal range is 250-700.

5. DEDUPLICATION. One job / school / certification / language / project
   = one row. Never list the same thing twice in CZ + EN; pick the
   OUTPUT_LANGUAGE and stick to it.

6. OUTPUT_LANGUAGE CONSISTENCY. Every human-readable string must be in
   the declared OUTPUT_LANGUAGE. Code, technology names and proper
   nouns are exempt.

7. LANGUAGES - CEFR ONLY. Only A1 / A2 / B1 / B2 / C1 / C2. Never
   "Native", "Fluent", "Bilingual", "Intermediate" - use the closest
   CEFR level or leave the field empty.

8. CERTIFICATIONS / AWARDS / PATENTS / PUBLICATIONS - NEVER INVENT.
   If the source has none, return an empty array AND a
   "do_not_claim" reason. The candidate should never see a fake cert.

9. RECOMMENDATIONS. Never write a fake recommendation. The pipeline
   only produces TEMPLATE MESSAGES the candidate can send to a
   colleague to request one.

10. POSTS / OUTREACH MESSAGES. Lead with a hook, deliver one specific
    insight, end with a single call to action. No emoji spam (max one
    well-placed emoji per post; recruiter outreach: zero emoji).
    Hashtags are 3-5 max, lower-case where the brand allows.

11. JOB-TITLE TRANSLATION. Translate position titles between CZ and EN
    accurately when needed (e.g. "Vývojář" <-> "Developer", "Marketingový
    manažer" <-> "Marketing Manager"). If a title has no canonical
    translation, keep the original spelling.

12. TARGETING. Every section must reflect the candidate's TARGET_ROLES
    and AUDIENCE. Lead with the role-relevant evidence; demote the
    rest. Recruiter audience prefers crisp scope numbers and tools;
    hiring-manager audience prefers outcome stories; founder audience
    prefers signal-to-noise; peer audience prefers craft details.

13. TONE PRESETS. Match the requested TONE exactly:
    - professional: neutral, factual, recruiter-readable.
    - junior_friendly: warm, learning-mindset, growth verbs.
    - senior: confident, scope-led, mentoring signals.
    - confident_honest: bold but never hyped; flag gaps as growth areas.
    - technical: tools-first, architecture verbs, concrete metrics.
    - simple: plain language, no jargon, ~B1 reading level.
    - recruiter_friendly: keyword-rich, scannable, ATS-aware.

14. ASKING WHEN UNSURE. If a critical fact is missing for the section
    you are generating, surface a clarifying question instead of
    inventing it. The pipeline will surface those to the candidate.
"""


# --- Profile extraction ------------------------------------------------


PROFILE_EXTRACT_SYSTEM = (
    LINKEDIN_EXPERT_RULES
    + "\n\nTASK: Read the resume text (and optional LinkedIn export +"
    " GitHub summary + free-form notes) and emit a NORMALISED LINKEDIN"
    " PROFILE as the structured JSON described by the schema. Apply"
    " rules 1, 2, 5, 6, 7, 8. Do not summarise away facts - keep every"
    " role, school, certification entry. Languages must use CEFR. If"
    " a section is empty in the source, return an empty array (do not"
    " invent). Tag every skill / claim with an evidence_anchor in"
    " {resume, linkedin_export, github, user_confirmed,"
    " missing_evidence}. The downstream generators rely on these"
    " anchors to bucket claims correctly."
)


# --- Headlines ---------------------------------------------------------


HEADLINES_SYSTEM = (
    LINKEDIN_EXPERT_RULES
    + "\n\nTASK: Produce 4-6 LinkedIn HEADLINE VARIANTS targeted at the"
    " requested AUDIENCE and TONE. Apply rules 3, 4 (max 220 chars),"
    " 12, 13. For EACH variant return:\n"
    " * text - the headline itself, 60-220 chars.\n"
    " * audience - one of {recruiter, hiring_manager, founder, peer,"
    "   general}.\n"
    " * char_count - integer (server will verify).\n"
    " * evidence_anchors - list of source labels (resume / linkedin /"
    "   github / user_confirmed / target_role).\n"
    " * focus - 1-2 word label (e.g. 'recruiter-friendly', 'GenAI',"
    "   'mentoring').\n"
    " Always include at least one recruiter-friendly variant and one"
    " keyword-rich variant. Never use cringe words from rule 3. Output"
    " language must match OUTPUT_LANGUAGE; tool / proper noun names"
    " stay as-is."
)


# --- About / Intro -----------------------------------------------------


ABOUT_SYSTEM = (
    LINKEDIN_EXPERT_RULES
    + "\n\nTASK: Produce LinkedIn ABOUT (Intro) variants. Five"
    " variants are required: short_version (~600 chars), medium_version"
    " (~1,200), long_version (~2,200), technical_version (technical"
    " peers; tools-first), recruiter_version (recruiter audience;"
    " keyword-rich, scannable). Every variant must:\n"
    " * Open with a one-sentence positioning statement (role + signature"
    "   strength).\n"
    " * Use 1st person, conversational LinkedIn voice.\n"
    " * Carry 2-3 concrete proof points (metrics, scope, named tools).\n"
    " * Close with a CTA tied to the candidate's TARGET_ROLES (open to"
    "   roles, mentoring, freelance, …).\n"
    " * Stay strictly within rule 4 char limits. Always emit char_counts.\n"
    " * Never include the cringe words from rule 3.\n"
    " * If the source lacks evidence for a claim, omit it - do not pad."
)


# --- Experience rewrite ------------------------------------------------


EXPERIENCE_REWRITE_SYSTEM = (
    LINKEDIN_EXPERT_RULES
    + "\n\nTASK: For EACH role in the candidate's profile, produce a"
    " LinkedIn-friendly REWRITE. Apply rules 1, 2, 4 (per-role max"
    " 2,000 chars), 12, 13. For every role return:\n"
    " * linkedin_description - 1-2 short paragraphs scene-setting the"
    "   role (team size, scope, problem space).\n"
    " * bullets - 3-6 outcome-focused bullets, lead each with a verb"
    "   and a concrete object (number / tool / artefact). Never bullet"
    "   filler.\n"
    " * suggested_skills - 3-8 LinkedIn skills tags to attach to this"
    "   role. Each tag must trace to evidence in this role; tag the"
    "   anchor.\n"
    " * highlight - 1-2 short labels for the role's signature themes\n"
    "   (e.g. 'Mentoring', 'Migration ownership').\n"
    " * do_not_claim - list any claims you noticed in the source that"
    "   you intentionally avoided because there is no evidence (e.g.\n"
    "   'led a team of 10' when the source only says 'mentored two\n"
    "   juniors'). Empty when nothing was filtered.\n"
    " * evidence_anchors - source labels that justify the rewrite."
)


# --- Education rewrite -------------------------------------------------


EDUCATION_REWRITE_SYSTEM = (
    LINKEDIN_EXPERT_RULES
    + "\n\nTASK: For EACH education entry, produce a LinkedIn-friendly"
    " summary. For every entry return:\n"
    " * linkedin_description - 1-3 sentences (field of study + signature"
    "   topics + connection to the candidate's TARGET_ROLES). Skip"
    "   pleasantries.\n"
    " * relevant_coursework - 3-6 short course / topic labels found in"
    "   the source (or empty if none).\n"
    " * connection_to_target - one sentence linking the school's"
    "   strengths to a TARGET_ROLE.\n"
    " * evidence_anchors - source labels."
)


# --- Certifications ----------------------------------------------------


CERTIFICATIONS_REWRITE_SYSTEM = (
    LINKEDIN_EXPERT_RULES
    + "\n\nTASK: Produce a LinkedIn CERTIFICATIONS rewrite. Apply rules"
    " 1, 8. Return:\n"
    " * existing - per-cert object {name, issuer, year,"
    "   linkedin_description, priority (high/medium/low),"
    "   target_role_links}. Do NOT invent certs missing from the source.\n"
    " * recommended - 0-5 certifications to consider next, picked from"
    "   well-known industry programs that align with TARGET_ROLES."
    "   Each entry includes {name, issuer, why_it_matters}. Mark these"
    "   clearly as 'recommended' so the UI can disambiguate; never"
    "   imply the candidate already holds them."
)


# --- Skills ------------------------------------------------------------


SKILLS_SYSTEM = (
    LINKEDIN_EXPERT_RULES
    + "\n\nTASK: Produce a LinkedIn SKILLS recommendation in 4 buckets:\n"
    " * core - skills the candidate CAN claim today (evidence in"
    "   resume / linkedin / github / user_confirmed). Sorted by"
    "   relevance to TARGET_ROLES.\n"
    " * to_verify - skills the source hints at but the evidence is"
    "   thin (one mention, no numbers). The candidate should confirm"
    "   before claiming them on LinkedIn.\n"
    " * to_learn - skills the TARGET_ROLES require that the candidate"
    "   does NOT yet have. Each entry includes a short learning_path"
    "   suggestion (1-3 lines).\n"
    " * do_not_claim - skills the source mentions but you intentionally"
    "   filtered out (no evidence, hyped, or vague). Each entry"
    "   includes a one-line reason.\n"
    " For every skill in EVERY bucket return: name, category"
    " (core / tooling / soft / domain / language), evidence_anchor,"
    " and (for core / to_verify) a short evidence_quote (paraphrase) -"
    " never the raw resume sentence. Apply rules 1, 2, 5, 12."
)


# --- Featured ----------------------------------------------------------


FEATURED_SYSTEM = (
    LINKEDIN_EXPERT_RULES
    + "\n\nTASK: Produce LinkedIn FEATURED-section suggestions. The"
    " featured section sits at the top of the profile and pins"
    " portfolio-grade artefacts. Apply rules 1, 2. Return 3-8 items,"
    " each:\n"
    " * kind - one of {github_project, portfolio_site, article,"
    "   linkedin_post, certificate, app, video_demo, pdf_case_study}.\n"
    " * title - short headline.\n"
    " * description - 1-2 sentences explaining why this belongs in"
    "   Featured for the TARGET_ROLES.\n"
    " * link - URL when present in the source; empty string if the"
    "   user must paste it manually.\n"
    " * evidence_anchor - source label.\n"
    " Items missing a link MUST include a 'todo' note like 'paste GitHub"
    " link before publishing'. Never invent URLs."
)


# --- Projects ----------------------------------------------------------


PROJECTS_SYSTEM = (
    LINKEDIN_EXPERT_RULES
    + "\n\nTASK: Produce LinkedIn PROJECTS-section entries (max 6)."
    " Apply rule 1. For EACH project return:\n"
    " * title\n"
    " * description - 2-4 sentences (what it does, who it serves,"
    "   the candidate's role).\n"
    " * technologies - list of tools / languages used.\n"
    " * candidate_role - the candidate's specific contribution.\n"
    " * period - e.g. '06/2024 - present' or 'Sep 2023'.\n"
    " * link - URL if present in source (GitHub, demo, store)"
    "   - empty otherwise.\n"
    " * suggested_skills - 3-6 LinkedIn skill tags to attach.\n"
    " * evidence_anchors. Never invent a project."
)


# --- Services ----------------------------------------------------------


SERVICES_SYSTEM = (
    LINKEDIN_EXPERT_RULES
    + "\n\nTASK: Produce LinkedIn SERVICES-section suggestions for"
    " candidates who want to freelance / consult on the side. Apply"
    " rule 1. Return 3-8 service entries, each: name, short_description"
    " (1-2 sentences), why_credible (which evidence justifies it),"
    " evidence_anchor. If the candidate did not opt into services,"
    " return an empty 'services' array AND a 'skip_reason' string."
)


# --- Courses -----------------------------------------------------------


COURSES_SYSTEM = (
    LINKEDIN_EXPERT_RULES
    + "\n\nTASK: Produce LinkedIn COURSES suggestions. Two arrays:\n"
    " * existing - courses found in the source (with evidence anchor).\n"
    " * recommended - 3-6 well-known industry courses aligned with"
    "   TARGET_ROLES. Each entry: title, provider, why_it_matters,"
    "   estimated_hours. Mark clearly as 'recommended' so the UI can"
    "   disambiguate; never imply the candidate already finished them."
)


# --- Recommendation request templates ---------------------------------


RECOMMENDATION_REQUEST_SYSTEM = (
    LINKEDIN_EXPERT_RULES
    + "\n\nTASK: Produce 3-5 RECOMMENDATION-REQUEST MESSAGE TEMPLATES"
    " the candidate can send to former managers, peers, or clients."
    " Apply rule 9. Each entry:\n"
    " * recipient_type - one of {manager, peer, direct_report, client,"
    "   mentor}.\n"
    " * suggested_recipient_label - short hint who to ask (e.g."
    "   'manager from Acme Retail').\n"
    " * message - 60-180 word polite request, written in OUTPUT_LANGUAGE,"
    "   1st person, mentions ONE concrete shared project or outcome"
    "   from the source so the recipient remembers the candidate.\n"
    " * follow_up - one short follow-up line if the recipient does not"
    "   reply within 7 days."
)


# --- Posts -------------------------------------------------------------


POSTS_SYSTEM = (
    LINKEDIN_EXPERT_RULES
    + "\n\nTASK: Produce LinkedIn POSTS for the requested POST_KINDS."
    " Apply rules 3, 4, 10, 12, 13. For EACH selected post kind"
    " return one entry:\n"
    " * kind - one of {learning_update, project_launch, job_search,"
    "   recruiter_outreach, networking, comment}.\n"
    " * title - internal label (not posted).\n"
    " * body - 800-1,400 char post; lead with a hook, deliver ONE"
    "   specific insight from the candidate's evidence, end with one"
    "   CTA. No cringe words. Recruiter outreach: 0 emoji. Networking"
    "   / learning_update: max 1 well-placed emoji.\n"
    " * char_count - integer.\n"
    " * hashtags - 3-5 short hashtags (start with #, no spaces).\n"
    " * evidence_anchors - list of source labels backing the body.\n"
    " * audience - one of {recruiter, hiring_manager, peer, founder,"
    "   community}.\n"
    " For 'comment' kind: body is 250-700 chars and the entry includes"
    " a 'parent_post_topic' field - a short label of the post the"
    " candidate is responding to."
)


# --- Chat & followups --------------------------------------------------


CHAT_MODE_SYSTEM = (
    LINKEDIN_EXPERT_RULES
    + "\n\nTASK: You are running in CHAT MODE. The candidate talks to"
    " you in free-form conversation - help them improve a LinkedIn"
    " headline, draft a post, refine an experience description,"
    " analyse a recruiter outreach message, etc. Rules:\n\n"
    " * Keep replies tight (1-4 paragraphs unless the user explicitly"
    "   asks for a long-form artefact). Use markdown lists when"
    "   scanning is faster than prose.\n"
    " * Never invent the candidate's experience. If you need a fact"
    "   you do not have, ASK for it directly - 'What was the team"
    "   size?' beats guessing.\n"
    " * When the user pastes a job description or a target role,"
    "   tie every recommendation to a specific JD requirement.\n"
    " * When the user asks for the full LinkedIn profile rewrite,"
    "   suggest switching to Builder mode where the structured"
    "   pipeline runs end-to-end and exports MD / HTML for them.\n"
    " * Apply the global no-hallucination policy. Cite the source of"
    "   any fact you use ('per your CV: …', 'per your GitHub: …').\n"
    " * OUTPUT_LANGUAGE applies to every reply."
)


FOLLOWUP_QUESTIONS_SYSTEM = (
    LINKEDIN_EXPERT_RULES
    + "\n\nTASK: Compare the extracted profile against the candidate's"
    " TARGET_ROLES and AUDIENCE/TONE preferences. Produce CLARIFYING"
    " QUESTIONS the candidate should answer BEFORE we generate the"
    " rest of the profile, so we never have to invent. Rules:\n\n"
    " * Ask only about items that the TARGET_ROLES actually require"
    "   (e.g. seniority signals, scope numbers, mentoring history,"
    "   missing tools). Do NOT ask generic questions.\n"
    " * Each question is direct (you / vy), 1-2 sentences, with a"
    "   short rationale tied to a TARGET_ROLE.\n"
    " * Output 0-12 questions. 0 is a valid answer.\n"
    " * Topics must be short labels (1-3 words). No duplicate topics.\n"
    " * Always provide 2-6 clickable answer options for each question."
    " Mark multi_select=true only when several answers can apply."
    " allow_free_text=true unless the options enumerate every"
    " possible answer.\n"
    " * OUTPUT_LANGUAGE applies to every string (topic, question,"
    " rationale, options)."
)


# --- User block builders ----------------------------------------------


def language_directive(output_lang: str) -> str:
    name = "English" if output_lang == "en" else "Czech"
    return (
        f"OUTPUT_LANGUAGE = {output_lang} ({name}). Every human-readable"
        f" string must be in {name}."
    )


def _trim(text: str, max_chars: int) -> str:
    text = text or ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[... truncated to keep prompt small ...]"


def _targeting_block(
    *,
    target_roles: list[str],
    audience: str,
    tone: str,
) -> str:
    roles = ", ".join(r.strip() for r in target_roles if r and r.strip()) or "(unspecified)"
    return (
        f"TARGET_ROLES: {roles}\n"
        f"AUDIENCE: {audience}\n"
        f"TONE: {tone}"
    )


def serialize_github_summary(profile: Any) -> str:
    """Compact text view of a GitHubProfile for the profile prompt."""
    if profile is None:
        return ""
    lines: list[str] = []
    user_part = f"{getattr(profile, 'name', '') or ''} (@{profile.username})".strip()
    lines.append(user_part)
    if getattr(profile, "bio", None):
        lines.append(f"Bio: {profile.bio}")
    if getattr(profile, "location", None):
        lines.append(f"Location: {profile.location}")
    lines.append(
        f"Public repos: {profile.public_repos}, followers: {profile.followers}"
    )
    lines.append("")
    lines.append("Top repositories:")
    for repo in profile.repos:
        langs = ", ".join(repo.languages) if repo.languages else "-"
        lines.append(
            f"- {repo.name} | stars {repo.stars} | langs {langs}"
            f" | {repo.description or '-'}"
        )
    return "\n".join(lines)


def build_profile_extract_user(
    *,
    output_lang: str,
    target_roles: list[str],
    audience: str,
    tone: str,
    resume_text: str,
    linkedin_text: str = "",
    github_summary: str = "",
    notes: str = "",
) -> str:
    parts: list[str] = [
        language_directive(output_lang),
        "",
        _targeting_block(target_roles=target_roles, audience=audience, tone=tone),
        "",
        "=== RESUME TEXT ===",
        _trim(resume_text, 18000),
    ]
    if linkedin_text:
        parts += ["", "=== LINKEDIN EXPORT ===", _trim(linkedin_text, 12000)]
    if github_summary:
        parts += ["", "=== GITHUB SUMMARY ===", github_summary]
    if notes:
        parts += ["", "=== USER NOTES ===", _trim(notes, 4000)]
    parts += [
        "",
        "Return only the normalised LinkedIn profile JSON described by"
        " the schema. Tag every claim with an evidence_anchor.",
    ]
    return "\n".join(parts)


def _profile_block(profile: dict | None) -> str:
    return json.dumps(profile or {}, ensure_ascii=False)


def _generic_user(
    *,
    output_lang: str,
    target_roles: list[str],
    audience: str,
    tone: str,
    profile: dict | None,
    extra_directive: str = "",
    extra_payload: dict | None = None,
) -> str:
    parts: list[str] = [
        language_directive(output_lang),
        "",
        _targeting_block(target_roles=target_roles, audience=audience, tone=tone),
        "",
        "=== EXTRACTED PROFILE JSON ===",
        _profile_block(profile),
    ]
    if extra_payload:
        parts += [
            "",
            "=== EXTRA CONTEXT ===",
            json.dumps(extra_payload, ensure_ascii=False),
        ]
    if extra_directive:
        parts += ["", extra_directive]
    return "\n".join(parts)


def build_headlines_user(
    *,
    output_lang: str,
    target_roles: list[str],
    audience: str,
    tone: str,
    profile: dict | None,
) -> str:
    return _generic_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=profile,
        extra_directive=(
            "Return only the headlines JSON. Always include a"
            " recruiter-friendly variant. Verify char_count for each"
            " variant (max 220)."
        ),
    )


def build_about_user(
    *,
    output_lang: str,
    target_roles: list[str],
    audience: str,
    tone: str,
    profile: dict | None,
) -> str:
    return _generic_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=profile,
        extra_directive=(
            "Return only the about JSON with all five variants."
            " Every variant must respect rule 4 char limits."
        ),
    )


def build_experience_rewrite_user(
    *,
    output_lang: str,
    target_roles: list[str],
    audience: str,
    tone: str,
    profile: dict | None,
) -> str:
    return _generic_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=profile,
        extra_directive=(
            "Return only the experience-rewrite JSON. Cover EVERY role"
            " present in the profile - never drop one. Use 3-6 bullets"
            " each."
        ),
    )


def build_education_rewrite_user(
    *,
    output_lang: str,
    target_roles: list[str],
    audience: str,
    tone: str,
    profile: dict | None,
) -> str:
    return _generic_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=profile,
        extra_directive=(
            "Return only the education-rewrite JSON. Cover EVERY entry."
        ),
    )


def build_certifications_user(
    *,
    output_lang: str,
    target_roles: list[str],
    audience: str,
    tone: str,
    profile: dict | None,
) -> str:
    return _generic_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=profile,
        extra_directive=(
            "Return only the certifications JSON. Never invent a cert"
            " missing from the source - only include real ones in"
            " 'existing'. 'recommended' may include well-known industry"
            " programs but must be marked clearly as recommendations."
        ),
    )


def build_skills_user(
    *,
    output_lang: str,
    target_roles: list[str],
    audience: str,
    tone: str,
    profile: dict | None,
) -> str:
    return _generic_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=profile,
        extra_directive=(
            "Return only the skills JSON with 4 buckets."
            " Tag every skill with an evidence_anchor."
        ),
    )


def build_featured_user(
    *,
    output_lang: str,
    target_roles: list[str],
    audience: str,
    tone: str,
    profile: dict | None,
) -> str:
    return _generic_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=profile,
        extra_directive=(
            "Return only the featured JSON. Items missing a link must"
            " include a 'todo' note - never invent URLs."
        ),
    )


def build_projects_user(
    *,
    output_lang: str,
    target_roles: list[str],
    audience: str,
    tone: str,
    profile: dict | None,
) -> str:
    return _generic_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=profile,
        extra_directive="Return only the projects JSON. Max 6 entries.",
    )


def build_services_user(
    *,
    output_lang: str,
    target_roles: list[str],
    audience: str,
    tone: str,
    profile: dict | None,
    opt_in: bool,
) -> str:
    return _generic_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=profile,
        extra_payload={"opt_in_services": bool(opt_in)},
        extra_directive=(
            "Return only the services JSON. If the candidate did not"
            " opt in (opt_in_services=false), return an empty services"
            " array with a skip_reason."
        ),
    )


def build_courses_user(
    *,
    output_lang: str,
    target_roles: list[str],
    audience: str,
    tone: str,
    profile: dict | None,
) -> str:
    return _generic_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=profile,
        extra_directive="Return only the courses JSON.",
    )


def build_recommendations_user(
    *,
    output_lang: str,
    target_roles: list[str],
    audience: str,
    tone: str,
    profile: dict | None,
) -> str:
    return _generic_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=profile,
        extra_directive=(
            "Return only the recommendation_messages JSON. Templates"
            " only - never write the recommendation itself."
        ),
    )


def build_posts_user(
    *,
    output_lang: str,
    target_roles: list[str],
    audience: str,
    tone: str,
    profile: dict | None,
    post_kinds: list[str],
) -> str:
    return _generic_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=profile,
        extra_payload={"post_kinds": list(post_kinds)},
        extra_directive=(
            "Return only the posts JSON. Produce ONE entry for EACH"
            " post_kind in the EXTRA CONTEXT (no extras)."
        ),
    )


def build_followup_user(
    *,
    output_lang: str,
    target_roles: list[str],
    audience: str,
    tone: str,
    profile: dict | None,
) -> str:
    return _generic_user(
        output_lang=output_lang,
        target_roles=target_roles,
        audience=audience,
        tone=tone,
        profile=profile,
        extra_directive="Return only the clarifying questions JSON.",
    )


def build_chat_user_block(
    *,
    output_lang: str,
    target_roles: list[str],
    audience: str,
    tone: str,
    profile: dict | None,
    history: list[dict],
    attachments: dict[str, str],
    user_text: str,
) -> str:
    """Render the chat transcript + attached file bodies as a single
    user turn for :func:`src.services.ai_provider.run`."""
    parts: list[str] = [
        language_directive(output_lang),
        "",
        _targeting_block(target_roles=target_roles, audience=audience, tone=tone),
    ]
    if profile:
        parts += [
            "",
            "=== EXTRACTED PROFILE JSON (CONTEXT) ===",
            _profile_block(profile),
        ]
    if attachments:
        parts.append("")
        parts.append("=== ATTACHED DOCUMENTS ===")
        for name, body in attachments.items():
            parts.append(f"--- {name} ---")
            parts.append(_trim(body, 8000))
    if history:
        parts.append("")
        parts.append("=== CONVERSATION SO FAR ===")
        for turn in history:
            role = (turn.get("role") or "").strip().lower()
            text = (turn.get("text") or "").strip()
            if not text:
                continue
            label = "Candidate" if role == "user" else "Assistant"
            parts.append(f"{label}: {text}")
    parts.append("")
    parts.append("=== NEW MESSAGE FROM CANDIDATE ===")
    parts.append(user_text.strip() or "(empty message)")
    parts.append("")
    parts.append(
        "Reply as the LinkedIn personal-branding expert. Keep it short,"
        " grounded in the evidence above, and ask for missing facts"
        " instead of inventing them."
    )
    return "\n".join(parts)
