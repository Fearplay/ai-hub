"""Shared upload zone with click-to-browse + paste-path + real OS drop.

Used by both AI Career and AI LinkedIn (and any future section that
needs a "drop a CV here" affordance) so we have a single tested
implementation.

Unlike the Flet original, the PySide6 build supports OS drag-and-drop
out of the box: ``setAcceptDrops(True)`` + ``dragEnterEvent`` /
``dropEvent`` give us native file drops without any prerequisite. The
zone still keeps:

1. Click-to-browse via ``QFileDialog.getOpenFileName``,
2. "Paste path" button hooked to :mod:`src.services.clipboard` so power
   users on Windows can ``Shift+Right-click - Copy as path`` in
   Explorer and paste the path with one click,
3. Inline error message under the zone for unsupported formats / parse
   failures,
4. Logging through :mod:`src.services.logger` for every interesting
   outcome - no silent "nothing happens when I drop" reports.
"""

from __future__ import annotations

import os
from typing import Callable, Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QSizePolicy,
    QWidget,
)

from src.qt.icons import Icons
from src.qt.runtime import get_main_window
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    ClickFrame,
    IconLabel,
    MutedLabel,
    custom_label,
    hbox,
    vbox,
)
from src.services import clipboard, logger as logger_service
from src.services.file_parser import ParsedFile, parse_file
from src.theme import Theme


class _DropZone(ClickFrame):
    """Inner ``ClickFrame`` extended to handle OS drops."""

    def __init__(
        self,
        *,
        theme: Theme,
        log_area: str,
        extensions: tuple[str, ...],
        unsupported_message: str,
        on_emit: Callable[[Optional[ParsedFile], str], None],
        height: int,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self._log_area = log_area
        self._extensions = extensions
        self._unsupported = unsupported_message
        self._on_emit = on_emit
        self.setAcceptDrops(True)
        self.setMinimumHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self._apply_idle_style()

    # styling ---------------------------------------------------------------

    def _apply_idle_style(self) -> None:
        self.setStyleSheet(
            f"""
            ClickFrame {{
                background-color: {rgba(self._theme.primary, 0.10)};
                border: 2px dashed {rgba(self._theme.primary, 0.30)};
                border-radius: 12px;
            }}
            ClickFrame:hover {{
                background-color: {rgba(self._theme.primary, 0.18)};
                border: 2px dashed {self._theme.primary};
            }}
            """
        )

    def _apply_hover_style(self) -> None:
        self.setStyleSheet(
            f"""
            ClickFrame {{
                background-color: {rgba(self._theme.primary, 0.18)};
                border: 2px dashed {self._theme.primary};
                border-radius: 12px;
            }}
            """
        )

    # OS DnD ----------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._apply_hover_style()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:  # noqa: N802
        self._apply_idle_style()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        self._apply_idle_style()
        if not urls:
            event.ignore()
            return
        local = urls[0].toLocalFile()
        logger_service.log_event(
            "INFO",
            self._log_area,
            "os_drop_received",
            count=len(urls),
            first_ext=os.path.splitext(local)[1].lower() if local else "",
        )
        event.acceptProposedAction()
        self._on_emit(_resolve_path(local, self._extensions), "os_drop")


def _resolve_path(path: str, extensions: tuple[str, ...]) -> Optional[ParsedFile]:
    if not path:
        return None
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext not in extensions:
        return None
    return parse_file(path)


def file_drop_zone(
    theme: Theme,
    *,
    log_area: str,
    title: str,
    hint: str,
    extensions: Sequence[str],
    unsupported_message: str,
    on_file_resolved: Callable[[ParsedFile], None],
    height: int = 132,
    paste_path_label: Optional[str] = "Paste path",
    paste_path_tooltip: Optional[str] = (
        "Tip on Windows: Shift+Right-click a file in Explorer -> Copy as path, then click here."
    ),
    cta_label: str = "Click to browse",
) -> QWidget:
    """Click-to-browse drop zone with paste-path + native OS drop.

    Parameters mirror the Flet original (``log_area``, ``title``,
    ``hint``, ``extensions``, ``unsupported_message``,
    ``on_file_resolved``, ``height``, ``paste_path_label``,
    ``paste_path_tooltip``, ``cta_label``) so existing call sites in
    ``ai_career`` / ``ai_linkedin`` work without edits.
    """
    allowed_lower: tuple[str, ...] = tuple(e.lower().lstrip(".") for e in extensions)

    container = QFrame()
    container.setStyleSheet("background: transparent;")
    container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
    outer_layout = vbox(spacing=6, margins=(0, 0, 0, 0))
    container.setLayout(outer_layout)

    error_label = custom_label("", color="#EF4444", size=11, selectable=True)
    error_label.setVisible(False)

    def _show_error(msg: Optional[str]) -> None:
        if msg:
            error_label.setText(msg)
            error_label.setVisible(True)
        else:
            error_label.setText("")
            error_label.setVisible(False)

    def _emit(parsed: Optional[ParsedFile], source: str) -> None:
        if parsed is None:
            logger_service.log_event(
                "WARNING", log_area, "drop_unsupported", source=source
            )
            _show_error(unsupported_message)
            return
        if parsed.error:
            logger_service.log_event(
                "WARNING",
                log_area,
                "drop_parse_failed",
                source=source,
                error=parsed.error,
            )
            _show_error(parsed.error)
            return
        logger_service.log_event(
            "INFO",
            log_area,
            "drop_ok",
            source=source,
            ext=parsed.ext,
            chars=len(parsed.text or ""),
        )
        _show_error(None)
        on_file_resolved(parsed)

    drop = _DropZone(
        theme=theme,
        log_area=log_area,
        extensions=allowed_lower,
        unsupported_message=unsupported_message,
        on_emit=_emit,
        height=height,
    )

    inner_layout = vbox(spacing=4, margins=(14, 14, 14, 14))
    inner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    drop.setLayout(inner_layout)

    inner_layout.addWidget(IconLabel(Icons.CLOUD_UPLOAD_OUTLINED, color=theme.primary, size=28),
                           alignment=Qt.AlignmentFlag.AlignCenter)
    title_label = BodyLabel(title, theme=theme, size=13)
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    inner_layout.addWidget(title_label)
    hint_label = MutedLabel(hint, theme=theme, size=11)
    hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    inner_layout.addWidget(hint_label)
    cta = custom_label(cta_label, color=theme.primary, size=10, weight=700)
    cta.setStyleSheet(
        f"color: {theme.primary}; background: transparent; letter-spacing: 1.2px;"
    )
    cta.setAlignment(Qt.AlignmentFlag.AlignCenter)
    inner_layout.addWidget(cta)

    def _open_picker() -> None:
        parent = get_main_window()
        ext_glob = " ".join(f"*.{e}" for e in allowed_lower)
        filt = f"Supported files ({ext_glob});;All files (*.*)"
        path, _ = QFileDialog.getOpenFileName(parent, title, "", filt)
        if not path:
            logger_service.log_event("DEBUG", log_area, "picker_cancelled")
            return
        _emit(_resolve_path(path, allowed_lower), "picker")

    drop.clicked.connect(_open_picker)
    drop.setToolTip(title)

    outer_layout.addWidget(drop)

    if paste_path_label and clipboard.available():
        paste_row = hbox(spacing=0, margins=(0, 0, 0, 0))
        paste_row.addStretch(1)
        paste_btn = ClickFrame()
        paste_btn.setStyleSheet(
            f"""
            ClickFrame {{
                background-color: {theme.surface};
                border: 1px solid {theme.border};
                border-radius: 10px;
            }}
            ClickFrame:hover {{
                background-color: {theme.surface_2};
            }}
            """
        )
        if paste_path_tooltip:
            paste_btn.setToolTip(paste_path_tooltip)
        paste_layout = hbox(spacing=6, margins=(10, 6, 10, 6))
        paste_btn.setLayout(paste_layout)
        paste_layout.addWidget(IconLabel(Icons.CONTENT_PASTE, color=theme.text_muted, size=14))
        paste_layout.addWidget(BodyLabel(paste_path_label, theme=theme, size=11))

        def _paste_path() -> None:
            text = clipboard.paste()
            if not text:
                logger_service.log_event(
                    "DEBUG", log_area, "paste_empty",
                    backend=clipboard.backend_name(),
                )
                _show_error(unsupported_message)
                return
            first_line = next(
                (line.strip() for line in text.splitlines() if line.strip()),
                "",
            )
            path = first_line.strip('"').strip("'").strip()
            logger_service.log_event(
                "INFO", log_area, "paste_path",
                chars=len(path), backend=clipboard.backend_name(),
            )
            _emit(_resolve_path(path, allowed_lower), "paste")

        paste_btn.clicked.connect(_paste_path)
        paste_row.addWidget(paste_btn)
        paste_holder = QFrame()
        paste_holder.setStyleSheet("background: transparent;")
        paste_holder.setLayout(paste_row)
        outer_layout.addWidget(paste_holder)

    outer_layout.addWidget(error_label)
    return container
