"""Material Icons (Outlined) integration for PySide6.

We bundle Google's ``MaterialIconsOutlined-Regular.otf`` (Apache-2.0)
under :file:`assets/fonts/`. The companion ``.codepoints`` file maps
every icon name to its single-character Unicode glyph in that font.
Both are loaded once at process start: the font goes into the Qt font
database and the codepoints are read into a ``dict[str, str]``.

Usage from a widget module:

.. code-block:: python

    from src.qt.icons import Icons, glyph, icon_font

    label = QLabel(glyph(Icons.SEND))
    label.setFont(icon_font(18))
    label.setStyleSheet(f"color: {theme.primary};")

Icon constants follow the Flet ``ft.Icons.X`` naming so the migration
keeps the same vocabulary in section views (``Icons.WORK_OUTLINE``,
``Icons.ATTACH_FILE``, ...).

Naming rule for the constants: each ``Icons.X`` constant maps to a
Material Icons codepoint name in the bundled Outlined font. Because the
font is already the outlined variant, names ending in ``_OUTLINED`` in
the Flutter catalog (``DESCRIPTION_OUTLINED``, ``WARNING_AMBER_OUTLINED``,
``SHIELD_OUTLINED``, ...) resolve to the base name (``description``,
``warning_amber``, ``shield``). Names ending in ``_OUTLINE`` denote a
distinct stroke-only glyph the font ships separately (``MAIL_OUTLINE``,
``WORK_OUTLINE``, ``LIGHTBULB_OUTLINE``).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtGui import QFont, QFontDatabase


_FONT_FAMILY: Optional[str] = None
_CODEPOINTS: dict[str, str] = {}


def _bundled_root() -> Path:
    """Return the directory we look at for ``assets/fonts/``.

    When running from source, this resolves to the repo root
    (``main.py`` lives next to ``assets/``). When running from the
    PyInstaller-frozen ``AIHub.exe`` we read from ``sys._MEIPASS`` -
    PyInstaller extracts ``--add-data "assets\\fonts;assets/fonts"`` to
    that temp directory.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parents[2]


def _load_codepoints() -> dict[str, str]:
    path = _bundled_root() / "assets" / "fonts" / "MaterialIconsOutlined-Regular.codepoints"
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            continue
        name, code = parts
        try:
            out[name] = chr(int(code, 16))
        except ValueError:
            continue
    return out


def _ensure_loaded() -> None:
    """Lazy initialize the icon font + codepoints map.

    The ``QFontDatabase.addApplicationFont`` call requires a live
    ``QApplication``. Sections sometimes import this module before the
    application object exists (during section auto-discovery) -
    initializing on first call avoids the chicken-and-egg.
    """
    global _FONT_FAMILY, _CODEPOINTS
    if not _CODEPOINTS:
        _CODEPOINTS = _load_codepoints()
    if _FONT_FAMILY is not None:
        return
    font_path = _bundled_root() / "assets" / "fonts" / "MaterialIconsOutlined-Regular.otf"
    if not font_path.exists():
        _FONT_FAMILY = ""
        return
    font_id = QFontDatabase.addApplicationFont(str(font_path))
    if font_id < 0:
        _FONT_FAMILY = ""
        return
    families = QFontDatabase.applicationFontFamilies(font_id)
    _FONT_FAMILY = families[0] if families else ""


def icon_font(pixel_size: int = 18) -> QFont:
    """Return a ``QFont`` configured for the bundled icon set.

    ``pixel_size`` follows the Flet convention (``ft.Icon(size=18)``) -
    it sets the glyph height in pixels. Returns a default sans-serif
    font when the icon font failed to load (so the UI never crashes,
    just renders text fallback).
    """
    _ensure_loaded()
    family = _FONT_FAMILY or "Segoe UI"
    font = QFont(family)
    font.setPixelSize(int(pixel_size))
    return font


def glyph(name: str) -> str:
    """Return the unicode glyph for an icon name (or ``"?"`` if unknown).

    Accepts both raw Material Icons names (``"send"``) and the
    ``Icons.SEND`` constants (whose values are pre-mapped names). When
    the icon is missing from the bundled codepoints, returns a question
    mark so the layout stays intact and a ``WARNING`` log line surfaces
    in :mod:`src.services.logger`.
    """
    _ensure_loaded()
    if not name:
        return ""
    char = _CODEPOINTS.get(name)
    if char is not None:
        return char
    if name.endswith("_outlined"):
        char = _CODEPOINTS.get(name[: -len("_outlined")])
        if char is not None:
            return char
    try:
        from src.services import logger as logger_service

        logger_service.log_event(
            "WARNING", "qt.icons", "missing_codepoint", name=name
        )
    except Exception:
        pass
    return "?"


class Icons:
    """Material Icons name registry.

    Each constant value is a Material Icons base name that resolves to
    a glyph in the bundled Outlined font.
    """

    ACCOUNT_BALANCE_OUTLINED = "account_balance"
    ACCOUNT_BALANCE_WALLET_OUTLINED = "account_balance_wallet"
    ADD = "add"
    ALTERNATE_EMAIL = "alternate_email"
    APPLE = "apple"
    ARROW_BACK = "arrow_back"
    ARROW_FORWARD = "arrow_forward"
    ARTICLE_OUTLINED = "article"
    ASSIGNMENT_OUTLINED = "assignment"
    ATTACH_FILE = "attach_file"
    AUTO_AWESOME = "auto_awesome"
    AUTO_FIX_HIGH = "auto_fix_high"
    AUTO_STORIES_OUTLINED = "auto_stories"
    BAR_CHART = "bar_chart"
    BOLT_OUTLINED = "bolt"
    BOOKMARK_BORDER = "bookmark_border"
    BOOKMARK_OUTLINE = "bookmark_outline"
    BUSINESS_CENTER_OUTLINED = "business_center"
    CALCULATE_OUTLINED = "calculate"
    CALENDAR_TODAY = "calendar_today"
    CAMPAIGN_OUTLINED = "campaign"
    CHECK = "check"
    CHECKLIST = "checklist"
    CHECK_BOX_OUTLINED = "check_box"
    CHECK_CIRCLE = "check_circle"
    CHECK_CIRCLE_OUTLINED = "check_circle"
    CHEVRON_RIGHT = "chevron_right"
    CIRCLE = "circle"
    CLOSE = "close"
    CLOUD_UPLOAD_OUTLINED = "cloud_upload"
    CODE = "code"
    COMPARE_ARROWS = "compare_arrows"
    CONTENT_COPY = "content_copy"
    CONTENT_PASTE = "content_paste"
    COPY_ALL = "copy_all"
    CREDIT_CARD = "credit_card"
    CURRENCY_BITCOIN = "currency_bitcoin"
    CURRENCY_EXCHANGE = "currency_exchange"
    DASHBOARD_OUTLINED = "dashboard"
    DELETE_OUTLINE = "delete_outline"
    DELETE_SWEEP_OUTLINED = "delete_sweep"
    DESCRIPTION = "description"
    DESCRIPTION_OUTLINED = "description"
    DIRECTIONS_CAR_OUTLINED = "directions_car"
    DOWNLOAD_OUTLINED = "download"
    EDIT_NOTE_OUTLINED = "edit_note"
    EDIT_OUTLINED = "edit"
    ELDERLY = "elderly"
    ERROR_OUTLINE = "error_outline"
    EURO = "euro"
    EVENT_NOTE = "event_note"
    FAVORITE_BORDER = "favorite_border"
    FILE_DOWNLOAD_OUTLINED = "file_download"
    FILE_UPLOAD_OUTLINED = "file_upload"
    FOLDER_OPEN = "folder_open"
    FOLDER_SPECIAL_OUTLINED = "folder_special"
    FORWARD_TO_INBOX = "forward_to_inbox"
    FUNCTIONS = "functions"
    GAVEL_OUTLINED = "gavel"
    GRID_VIEW_OUTLINED = "grid_view"
    HANDYMAN_OUTLINED = "handyman"
    HEALTH_AND_SAFETY = "health_and_safety"
    HELP_OUTLINE = "help_outline"
    HISTORY = "history"
    HISTORY_TOGGLE_OFF = "history_toggle_off"
    HOME_OUTLINED = "home"
    HOURGLASS_EMPTY_ROUNDED = "hourglass_empty"
    HTML = "html"
    HUB_OUTLINED = "hub"
    IMAGE_OUTLINED = "image"
    INFO = "info"
    INFO_OUTLINE = "info"
    INSIGHTS_OUTLINED = "insights"
    IOS_SHARE = "ios_share"
    KEYBOARD_ARROW_DOWN = "keyboard_arrow_down"
    LIGHTBULB_OUTLINE = "lightbulb"
    LOCAL_MALL_OUTLINED = "local_mall"
    LOCK_OUTLINE = "lock"
    MAIL_OUTLINE = "mail_outline"
    MEMORY = "memory"
    MENU_BOOK_OUTLINED = "menu_book"
    MIC_NONE_OUTLINED = "mic_none"
    MOOD_OUTLINED = "mood"
    MORE_HORIZ = "more_horiz"
    NOTES = "notes"
    OPEN_IN_FULL = "open_in_full"
    OPEN_IN_NEW = "open_in_new"
    PALETTE_OUTLINED = "palette"
    PAYMENTS_OUTLINED = "payments"
    PERSON = "person"
    PERSON_OUTLINE = "person_outline"
    PHOTO_CAMERA_OUTLINED = "photo_camera"
    PHOTO_LIBRARY_OUTLINED = "photo_library"
    PICTURE_AS_PDF = "picture_as_pdf"
    PIE_CHART_OUTLINE = "pie_chart_outline"
    PLAY_ARROW_ROUNDED = "play_arrow"
    PLAY_CIRCLE_OUTLINE = "play_circle_outline"
    POST_ADD = "post_add"
    PSYCHOLOGY_ALT_OUTLINED = "psychology_alt"
    PSYCHOLOGY_OUTLINED = "psychology"
    PUBLIC = "public"
    PUSH_PIN = "push_pin"
    PUSH_PIN_OUTLINED = "push_pin"
    QUERY_STATS = "query_stats"
    QUESTION_ANSWER_OUTLINED = "question_answer"
    QUIZ_OUTLINED = "quiz"
    RADIO_BUTTON_CHECKED = "radio_button_checked"
    RADIO_BUTTON_UNCHECKED = "radio_button_unchecked"
    RECEIPT_LONG_OUTLINED = "receipt_long"
    REFRESH = "refresh"
    RESTART_ALT = "restart_alt"
    RESTAURANT_OUTLINED = "restaurant"
    SAVE_OUTLINED = "save"
    SAVINGS_OUTLINED = "savings"
    SCHEDULE = "schedule"
    SCHOOL_OUTLINED = "school"
    SCIENCE_OUTLINED = "science"
    SCOREBOARD_OUTLINED = "scoreboard"
    SEND = "send"
    SENTIMENT_SATISFIED_OUTLINED = "sentiment_satisfied"
    SETTINGS_OUTLINED = "settings"
    SHIELD_OUTLINED = "shield"
    SHORT_TEXT = "short_text"
    SHOW_CHART = "show_chart"
    STAR_OUTLINE = "star_outline"
    SUBJECT = "subject"
    SUMMARIZE_OUTLINED = "summarize"
    THUMB_UP_OUTLINED = "thumb_up"
    TIMELINE = "timeline"
    TITLE = "title"
    TRACK_CHANGES = "track_changes"
    TRANSLATE = "translate"
    TRENDING_UP = "trending_up"
    TUNE = "tune"
    UNDO = "undo"
    UNFOLD_LESS = "unfold_less"
    UPLOAD_FILE = "upload_file"
    UPLOAD_FILE_OUTLINED = "upload_file"
    VIEW_QUILT_OUTLINED = "view_quilt"
    VISIBILITY_OFF_OUTLINED = "visibility_off"
    VISIBILITY_OUTLINED = "visibility"
    WARNING_AMBER_OUTLINED = "warning_amber"
    WARNING_AMBER_ROUNDED = "warning_amber"
    WEB_OUTLINED = "web"
    WORK_OUTLINE = "work_outline"
    WORKSPACE_PREMIUM_OUTLINED = "workspace_premium"
    X = "close"


__all__ = ["Icons", "icon_font", "glyph"]
