"""QtAwesome-backed icon registry for AI Hub.

We render icons via the bundled `QtAwesome <https://github.com/spyder-ide/qtawesome>`_
library using **Material Design Icons 6** (``mdi6.*`` prefix). QtAwesome
lazily loads its font files from inside its own wheel and rasterises
each glyph into a transparent ``QIcon`` / ``QPixmap`` via Qt's font
database, so we never have to bundle our own OTF / codepoints file or
hand-write a custom ``QLabel`` font.

To add an icon to the app:

1. Pick a glyph from the Material Design Icons catalogue
   (https://pictogrammers.com/library/mdi/). The catalogue search is
   the fastest way to find a name; QtAwesome ships an interactive
   browser too (``qta-browser`` after ``pip install qtawesome``).
2. Add an entry to :class:`Icons` whose value is ``"mdi6.<name>"``
   (kebab-case).
3. Pass the constant to :class:`src.qt.widgets.IconLabel`,
   ``GhostButton(icon=...)``, ``section_card(icon=...)``, or any other
   widget that takes a ``str`` icon name.

QtAwesome supports several icon families (``fa5``, ``fa6``, ``mdi``,
``mdi6``, ``ph``, ``ri``, ``msc``). We standardised on ``mdi6`` so the
visual language is uniform across every screen. The :class:`Icons`
class is the single source of truth - section code never hand-codes a
``"mdi6.X"`` string, it only references ``Icons.X``.

Usage from a widget module:

.. code-block:: python

    from src.qt.icons import Icons, icon_pixmap
    from src.qt.widgets import IconLabel

    icon = IconLabel(Icons.SEND, color=theme.primary, size=18)

    # If you need a raw pixmap (e.g. for QPainter), reach for the
    # helper directly instead of going through the widget:
    pix = icon_pixmap(Icons.LINKEDIN, color="#0A66C2", size=24)
"""

from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import QSize
from PySide6.QtGui import QFont, QIcon, QPixmap

# Force qtpy (qtawesome's Qt-binding shim) to pick PySide6 instead of
# trying PyQt5 / PyQt6 first. Has to happen *before* the first
# ``import qtawesome`` call - hence this side-effect at module import
# time. Cheap (env-variable set), safe to do repeatedly.
os.environ.setdefault("QT_API", "pyside6")

import qtawesome as qta  # noqa: E402  - must follow QT_API setup above


def qicon(name: str, *, color: Optional[str] = None) -> QIcon:
    """Return a ``QIcon`` for an icon name (``mdi6.X``) coloured ``color``.

    Falls back to an empty ``QIcon`` when the name is unknown so the UI
    never crashes - just shows nothing in that slot. Missing names are
    logged once (``WARNING``) so they surface in
    **Settings -> Debug logs**.
    """
    if not name:
        return QIcon()
    try:
        if color is None:
            return qta.icon(name)
        return qta.icon(name, color=color)
    except Exception:
        try:
            from src.services import logger as logger_service

            logger_service.log_event(
                "WARNING", "qt.icons", "missing_icon", name=name
            )
        except Exception:
            pass
        return QIcon()


def icon_pixmap(name: str, *, color: str, size: int) -> QPixmap:
    """Return a ``QPixmap`` of an icon coloured ``color`` at ``size``x``size``.

    Used by :class:`src.qt.widgets.IconLabel` to render an icon inside
    a ``QLabel``. Returns an empty pixmap when the name is unknown.
    """
    icon = qicon(name, color=color)
    return icon.pixmap(QSize(int(size), int(size)))


def icon_font(pixel_size: int = 18) -> QFont:
    """Legacy stub - return a regular sans-serif ``QFont``.

    Pre-migration the app rendered Material Symbols glyphs as text
    inside a ``QLabel``, so this helper returned the bundled icon font.
    Icons are now real pixmaps (:func:`icon_pixmap`), so the function
    only stays around as a no-op for the rare callsite that still
    wanted a typography font sized to match an icon row.
    """
    font = QFont()
    font.setPixelSize(int(pixel_size))
    return font


def glyph(name: str) -> str:  # noqa: ARG001 - intentionally ignored
    """Legacy stub - return an empty string.

    Old callers used to set ``QLabel.setText(glyph(name))`` paired with
    :func:`icon_font`. The new path is :func:`icon_pixmap`; this helper
    survives only so leftover imports do not break at module-load time.
    """
    return ""


class Icons:
    """Material Design Icons 6 registry.

    Every constant value is a kebab-case MDI6 name prefixed with
    ``mdi6.`` so it can be passed straight to
    :func:`qtawesome.icon(...)`. Constant names mirror the pre-migration
    Material Symbols Rounded vocabulary so all section view code keeps
    working with ``Icons.WORK_OUTLINE`` etc. without churn.
    """

    ACCOUNT_BALANCE_OUTLINED = "mdi6.bank-outline"
    ACCOUNT_BALANCE_WALLET_OUTLINED = "mdi6.wallet-outline"
    ADD = "mdi6.plus"
    ALTERNATE_EMAIL = "mdi6.at"
    APPLE = "mdi6.apple"
    ARROW_BACK = "mdi6.arrow-left"
    ARROW_FORWARD = "mdi6.arrow-right"
    ARTICLE_OUTLINED = "mdi6.file-document-outline"
    ASSIGNMENT_IND_OUTLINED = "mdi6.file-account-outline"
    ASSIGNMENT_OUTLINED = "mdi6.clipboard-text-outline"
    ATTACH_FILE = "mdi6.paperclip"
    AUTO_AWESOME = "mdi6.shimmer"
    AUTO_FIX_HIGH = "mdi6.auto-fix"
    AUTO_STORIES_OUTLINED = "mdi6.book-open-variant"
    BAR_CHART = "mdi6.chart-bar"
    BOLT_OUTLINED = "mdi6.lightning-bolt-outline"
    BOOKMARK_BORDER = "mdi6.bookmark-outline"
    BOOKMARK_OUTLINE = "mdi6.bookmark-outline"
    BRIEFCASE_SEARCH_OUTLINED = "mdi6.briefcase-search-outline"
    BUG_REPORT_OUTLINED = "mdi6.bug-outline"
    BUSINESS_CENTER_OUTLINED = "mdi6.briefcase-outline"
    CALCULATE_OUTLINED = "mdi6.calculator-variant-outline"
    CALENDAR_TODAY = "mdi6.calendar"
    CAMPAIGN_OUTLINED = "mdi6.bullhorn-outline"
    CHECK = "mdi6.check"
    CHECKLIST = "mdi6.format-list-checks"
    CHECK_BOX_OUTLINED = "mdi6.checkbox-outline"
    CHECK_CIRCLE = "mdi6.check-circle"
    CHECK_CIRCLE_OUTLINED = "mdi6.check-circle-outline"
    CHEVRON_RIGHT = "mdi6.chevron-right"
    CIRCLE = "mdi6.circle"
    CLOSE = "mdi6.close"
    CLOUD_UPLOAD_OUTLINED = "mdi6.cloud-upload-outline"
    CODE = "mdi6.code-tags"
    COMPARE_ARROWS = "mdi6.compare-horizontal"
    CONTENT_COPY = "mdi6.content-copy"
    CONTENT_PASTE = "mdi6.content-paste"
    COPY_ALL = "mdi6.content-duplicate"
    CREDIT_CARD = "mdi6.credit-card-outline"
    CURRENCY_BITCOIN = "mdi6.bitcoin"
    CURRENCY_EXCHANGE = "mdi6.swap-horizontal"
    DASHBOARD_OUTLINED = "mdi6.view-dashboard-outline"
    DELETE_OUTLINE = "mdi6.delete-outline"
    DELETE_SWEEP_OUTLINED = "mdi6.delete-sweep-outline"
    DESCRIPTION = "mdi6.file-document-outline"
    DESCRIPTION_OUTLINED = "mdi6.file-document-outline"
    DIRECTIONS_CAR_OUTLINED = "mdi6.car-outline"
    DOWNLOAD_OUTLINED = "mdi6.download-outline"
    DRAG_INDICATOR = "mdi6.drag-vertical"
    EDIT_NOTE_OUTLINED = "mdi6.note-edit-outline"
    EDIT_OUTLINED = "mdi6.pencil-outline"
    ELDERLY = "mdi6.human-cane"
    ERROR_OUTLINE = "mdi6.alert-circle-outline"
    EURO = "mdi6.currency-eur"
    EVENT_NOTE = "mdi6.calendar-text"
    FAVORITE_BORDER = "mdi6.heart-outline"
    FILE_DOWNLOAD_OUTLINED = "mdi6.file-download-outline"
    FILE_UPLOAD_OUTLINED = "mdi6.file-upload-outline"
    FOLDER_OPEN = "mdi6.folder-open-outline"
    FOLDER_SPECIAL_OUTLINED = "mdi6.folder-star-outline"
    FORWARD_TO_INBOX = "mdi6.email-fast-outline"
    FUNCTIONS = "mdi6.function-variant"
    GAVEL_OUTLINED = "mdi6.gavel"
    GOOGLE_PLAY = "mdi6.google-play"
    GRID_VIEW_OUTLINED = "mdi6.view-grid-outline"
    HANDYMAN_OUTLINED = "mdi6.hammer-wrench"
    HEALTH_AND_SAFETY = "mdi6.shield-check-outline"
    HELP_OUTLINE = "mdi6.help-circle-outline"
    HISTORY = "mdi6.history"
    HISTORY_TOGGLE_OFF = "mdi6.history"
    HOME_OUTLINED = "mdi6.home-outline"
    HOURGLASS_EMPTY_ROUNDED = "mdi6.timer-sand"
    HTML = "mdi6.language-html5"
    HUB_OUTLINED = "mdi6.hub-outline"
    ID_CARD = "mdi6.card-account-details-outline"
    IMAGE_OUTLINED = "mdi6.image-outline"
    INFO = "mdi6.information"
    INFO_OUTLINE = "mdi6.information-outline"
    INSIGHTS_OUTLINED = "mdi6.chart-line"
    IOS_SHARE = "mdi6.share-variant-outline"
    KEYBOARD_ARROW_DOWN = "mdi6.chevron-down"
    LIGHTBULB_OUTLINE = "mdi6.lightbulb-outline"
    LINKEDIN = "mdi6.linkedin"
    LOCAL_MALL_OUTLINED = "mdi6.shopping-outline"
    LOCATION_ON = "mdi6.map-marker"
    LOCK_OUTLINE = "mdi6.lock-outline"
    MAIL_OUTLINE = "mdi6.email-outline"
    MANAGE_SEARCH = "mdi6.file-search-outline"
    MEMORY = "mdi6.memory"
    MENU_BOOK_OUTLINED = "mdi6.book-open-page-variant-outline"
    MIC_NONE_OUTLINED = "mdi6.microphone-outline"
    MOOD_OUTLINED = "mdi6.emoticon-outline"
    MORE_HORIZ = "mdi6.dots-horizontal"
    MORE_VERT = "mdi6.dots-vertical"
    NOTES = "mdi6.note-text-outline"
    OPEN_IN_FULL = "mdi6.arrow-expand"
    OPEN_IN_NEW = "mdi6.open-in-new"
    PALETTE_OUTLINED = "mdi6.palette-outline"
    PAYMENTS_OUTLINED = "mdi6.cash"
    PERSON = "mdi6.account"
    PERSON_OUTLINE = "mdi6.account-outline"
    PERSON_SEARCH_OUTLINED = "mdi6.account-search-outline"
    PHOTO_CAMERA_OUTLINED = "mdi6.camera-outline"
    PHOTO_LIBRARY_OUTLINED = "mdi6.image-multiple-outline"
    PICTURE_AS_PDF = "mdi6.file-pdf-box"
    PIE_CHART_OUTLINE = "mdi6.chart-pie"
    PLAY_ARROW_ROUNDED = "mdi6.play"
    PLAY_CIRCLE_OUTLINE = "mdi6.play-circle-outline"
    POST_ADD = "mdi6.file-plus-outline"
    PSYCHOLOGY_ALT_OUTLINED = "mdi6.head-cog-outline"
    PSYCHOLOGY_OUTLINED = "mdi6.brain"
    PUBLIC = "mdi6.earth"
    PUSH_PIN = "mdi6.pin"
    PUSH_PIN_OUTLINED = "mdi6.pin"
    QUERY_STATS = "mdi6.chart-bell-curve"
    QUESTION_ANSWER_OUTLINED = "mdi6.message-question-outline"
    QUIZ_OUTLINED = "mdi6.head-question-outline"
    RADIO_BUTTON_CHECKED = "mdi6.radiobox-marked"
    RADIO_BUTTON_UNCHECKED = "mdi6.radiobox-blank"
    RECEIPT_LONG_OUTLINED = "mdi6.receipt-text-outline"
    REFRESH = "mdi6.refresh"
    RESTART_ALT = "mdi6.restart"
    RESTAURANT_OUTLINED = "mdi6.silverware-fork-knife"
    SAVE_OUTLINED = "mdi6.content-save-outline"
    SAVINGS_OUTLINED = "mdi6.piggy-bank-outline"
    SCHEDULE = "mdi6.clock-outline"
    SCHOOL_OUTLINED = "mdi6.school-outline"
    SCIENCE_OUTLINED = "mdi6.flask-outline"
    SCOREBOARD_OUTLINED = "mdi6.scoreboard-outline"
    SEARCH = "mdi6.magnify"
    SEND = "mdi6.send"
    SENTIMENT_SATISFIED_OUTLINED = "mdi6.emoticon-happy-outline"
    SETTINGS_OUTLINED = "mdi6.cog-outline"
    SHIELD_OUTLINED = "mdi6.shield-outline"
    SHORT_TEXT = "mdi6.text-short"
    SHOW_CHART = "mdi6.chart-line"
    STAR_OUTLINE = "mdi6.star-outline"
    SUBJECT = "mdi6.format-align-left"
    SUMMARIZE_OUTLINED = "mdi6.text-box-outline"
    THUMB_UP_OUTLINED = "mdi6.thumb-up-outline"
    TIMELINE = "mdi6.timeline-outline"
    TITLE = "mdi6.format-title"
    TRACK_CHANGES = "mdi6.target"
    TRANSLATE = "mdi6.translate"
    TRENDING_UP = "mdi6.trending-up"
    TUNE = "mdi6.tune-variant"
    UNDO = "mdi6.undo"
    UNFOLD_LESS = "mdi6.unfold-less-horizontal"
    UPLOAD_FILE = "mdi6.file-upload-outline"
    UPLOAD_FILE_OUTLINED = "mdi6.file-upload-outline"
    VIEW_QUILT_OUTLINED = "mdi6.view-quilt-outline"
    VISIBILITY_OFF_OUTLINED = "mdi6.eye-off-outline"
    VISIBILITY_OUTLINED = "mdi6.eye-outline"
    WARNING_AMBER_OUTLINED = "mdi6.alert-outline"
    WARNING_AMBER_ROUNDED = "mdi6.alert-outline"
    WEB_OUTLINED = "mdi6.web"
    WORK_OUTLINE = "mdi6.briefcase-outline"
    WORKSPACE_PREMIUM_OUTLINED = "mdi6.medal-outline"
    X = "mdi6.close"


__all__ = ["Icons", "glyph", "icon_font", "icon_pixmap", "qicon"]
