"""Mock data for the AI Study section."""

from __future__ import annotations

from src.qt.icons import Icons

from src.sections.ai_study.strings import s


SECTION_ICON = Icons.SCHOOL_OUTLINED


def tabs(lang: str) -> list[str]:
    txt = s(lang)
    return [
        txt["tab_chat"],
        txt["tab_summary"],
        txt["tab_explain"],
        txt["tab_tasks"],
        txt["tab_quizzes"],
        txt["tab_sources"],
    ]


def assistant_actions(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"icon": Icons.AUTO_FIX_HIGH, "label": txt["action_simpler"]},
        {"icon": Icons.LIGHTBULB_OUTLINE, "label": txt["action_real"]},
        {"icon": Icons.HUB_OUTLINED, "label": txt["action_diagram"]},
        {"icon": Icons.HELP_OUTLINE, "label": txt["action_more"]},
    ]


def recommended_sources(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {
            "icon": Icons.SCHOOL_OUTLINED,
            "title": txt["source_khan_title"],
            "domain": txt["source_khan_domain"],
            "color": "#14B58A",
        },
        {
            "icon": Icons.PLAY_CIRCLE_OUTLINE,
            "title": txt["source_youtube_title"],
            "domain": txt["source_youtube_domain"],
            "color": "#EF4444",
        },
        {
            "icon": Icons.MENU_BOOK_OUTLINED,
            "title": txt["source_wiki_title"],
            "domain": txt["source_wiki_domain"],
            "color": "#94A3B8",
        },
    ]


def today_overview(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {
            "icon": Icons.MENU_BOOK_OUTLINED,
            "value": txt["today_topics_value"],
            "label": txt["today_topics_label"],
        },
        {
            "icon": Icons.SCHEDULE,
            "value": txt["today_time_value"],
            "label": txt["today_time_label"],
        },
        {
            "icon": Icons.TRACK_CHANGES,
            "value": txt["today_progress_value"],
            "label": txt["today_progress_label"],
        },
    ]


def subjects(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {
            "icon": Icons.SCIENCE_OUTLINED,
            "name": txt["subject_physics"],
            "percent": 85,
            "color_start": "#7C5CFC",
            "color_end": "#A78BFA",
        },
        {
            "icon": Icons.FUNCTIONS,
            "name": txt["subject_math"],
            "percent": 70,
            "color_start": "#38BDF8",
            "color_end": "#22D3EE",
        },
        {
            "icon": Icons.CODE,
            "name": txt["subject_programming"],
            "percent": 60,
            "color_start": "#22C55E",
            "color_end": "#86EFAC",
        },
        {
            "icon": Icons.TRENDING_UP,
            "name": txt["subject_economics"],
            "percent": 40,
            "color_start": "#F59E0B",
            "color_end": "#FBBF24",
        },
    ]


def quick_tools(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"icon": Icons.SHORT_TEXT, "label": txt["tool_summarise"]},
        {"icon": Icons.LIGHTBULB_OUTLINE, "label": txt["tool_explain"]},
        {"icon": Icons.QUIZ_OUTLINED, "label": txt["tool_quiz"]},
        {"icon": Icons.ASSIGNMENT_OUTLINED, "label": txt["tool_assignment"]},
        {"icon": Icons.HUB_OUTLINED, "label": txt["tool_mindmap"]},
        {"icon": Icons.TRANSLATE, "label": txt["tool_translate"]},
    ]


def upcoming_tasks(lang: str) -> list[dict]:
    txt = s(lang)
    return [
        {"title": txt["task_math"], "due": txt["task_math_due"]},
        {"title": txt["task_physics"], "due": txt["task_physics_due"]},
        {"title": txt["task_programming"], "due": txt["task_programming_due"]},
    ]
