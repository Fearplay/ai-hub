"""Shared upload zone with click-to-browse + paste-path + best-effort OS drop.

Used by both AI Career and AI LinkedIn (and any future section that
needs a "drop a CV here" affordance) so we have a single tested
implementation.

Reality of OS drag-and-drop in our deployment story:

* The native file-drop bridge (``flet-dropzone``) requires
  ``flet build windows`` + the Flutter SDK + the Visual Studio C++
  workload, which violates the "no prerequisites" promise documented in
  ``build-exe.mdc``.
* ``flet pack`` (PyInstaller, single-file ``.exe``) is what we ship and
  it does not currently expose OS-level file drop events.

Because of those limits the click-to-browse + paste-path workflow is the
guaranteed path. The widget therefore:

1. Renders a dashed-bordered drop zone with a cloud-upload affordance
  and an explicit "Click to browse" call to action,
2. Always exposes a "Paste path" button beneath the zone - power users
  on Windows can ``Shift+Right-click → Copy as path`` in Explorer and
  paste the path here without leaving the keyboard,
3. Opens an ``ft.FilePicker`` whenever the user clicks the zone (or
  hits the keyboard shortcut),
4. Hooks ``page.on_drop`` / ``page.on_file_drop`` if a future Flet
  release adds OS drop events on the ``flet pack`` runtime - we wire
  several attribute names so it "just works" the moment they ship,
5. Uses :mod:`src.services.clipboard` for the paste path - the
  synchronous, pyperclip-backed helper avoids the
  ``RuntimeError("Session closed")`` crashes the previous async
  ``ft.Clipboard`` calls suffered after a navigation,
6. Logs every interesting outcome through :mod:`src.services.logger`
  so we never get silent "nothing happens when I drop a file" reports.
"""

from __future__ import annotations

import os
from typing import Callable, Optional, Sequence

import flet as ft

from src.services import clipboard, logger as logger_service
from src.services.file_parser import ParsedFile, parse_file
from src.theme import Theme


def _idle_bg(theme: Theme) -> str:
    return ft.Colors.with_opacity(0.10, theme.primary)


def _idle_border(theme: Theme) -> ft.Border:
    return ft.border.all(2, ft.Colors.with_opacity(0.30, theme.primary))


def _hover_bg(theme: Theme) -> str:
    return ft.Colors.with_opacity(0.18, theme.primary)


def _hover_border(theme: Theme) -> ft.Border:
    return ft.border.all(2, theme.primary)


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
) -> ft.Control:
    """Click-to-browse drop zone with paste-path + best-effort OS drop.

    Parameters
    ----------
    log_area:
        Subsystem name used for ``logger_service.log_event`` (e.g.
        ``"ai_career.upload"`` so debug logs route per section).
    title / hint:
        Localised copy displayed inside the zone.
    extensions:
        Whitelist of file extensions (without the leading dot) the zone
        will accept. Anything else triggers ``unsupported_message``.
    on_file_resolved:
        Callback invoked exactly once per successful pick / drop with a
        :class:`ParsedFile` (already extracted to plain text).
    paste_path_label:
        Short label shown on the "Paste path" button. Defaults to
        ``"Paste path"`` so every upload zone surfaces the affordance -
        pass an explicit ``None`` to hide it (no AI Hub call site does
        this currently).
    paste_path_tooltip:
        Hover hint explaining how to copy a file path on Windows.
    cta_label:
        Tiny "CLICK TO BROWSE" call-to-action rendered under the title
        so the affordance is impossible to miss (OS drag-and-drop is
        not delivered by ``flet pack``, see the module docstring).
    """
    file_picker = ft.FilePicker()
    picker_registered: dict[str, bool] = {"done": False}

    inner_ref = ft.Ref[ft.Container]()
    error_ref = ft.Ref[ft.Text]()

    allowed_lower = tuple(e.lower().lstrip(".") for e in extensions)

    def _show_error(message: Optional[str]) -> None:
        e = error_ref.current
        if e is None:
            return
        e.value = message or ""
        e.visible = bool(message)
        logger_service.try_update(e)

    def _set_idle_visuals() -> None:
        c = inner_ref.current
        if c is None:
            return
        c.bgcolor = _idle_bg(theme)
        c.border = _idle_border(theme)
        logger_service.try_update(c)

    def _set_hover_visuals() -> None:
        c = inner_ref.current
        if c is None:
            return
        c.bgcolor = _hover_bg(theme)
        c.border = _hover_border(theme)
        logger_service.try_update(c)

    def _resolve_path(path: str) -> Optional[ParsedFile]:
        if not path:
            return None
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        if ext not in allowed_lower:
            return None
        return parse_file(path)

    def _emit(parsed: Optional[ParsedFile], *, source: str) -> None:
        if parsed is None:
            logger_service.log_event(
                "WARNING", log_area, "drop_unsupported", source=source,
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

    def _ensure_picker_registered(page: ft.Page) -> None:
        if picker_registered["done"]:
            return
        registry = getattr(page, "_services", None)
        if registry is not None:
            try:
                registry.register_service(file_picker)
            except Exception as exc:
                logger_service.log_exception(
                    log_area, "register_picker_failed", exc,
                )
        picker_registered["done"] = True

    async def _open_picker(e: ft.ControlEvent) -> None:
        page = e.page
        if page is None:
            logger_service.log_event(
                "WARNING", log_area, "open_picker_no_page",
            )
            return
        _ensure_picker_registered(page)
        _try_wire_os_drop(page)
        try:
            files = await file_picker.pick_files(
                dialog_title=title,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=list(allowed_lower),
            )
        except Exception as exc:
            logger_service.log_exception(
                log_area, "open_picker_failed", exc,
            )
            _show_error(str(exc) or unsupported_message)
            return
        if not files:
            logger_service.log_event(
                "DEBUG", log_area, "picker_cancelled",
            )
            return
        first = files[0]
        path = getattr(first, "path", "") or ""
        if path:
            _emit(_resolve_path(path), source="picker")

    def _handle_dropped_paths(paths: Sequence[str]) -> None:
        if not paths:
            return
        first = paths[0]
        logger_service.log_event(
            "INFO", log_area, "os_drop_received",
            count=len(paths), first_ext=os.path.splitext(first)[1].lower(),
        )
        _emit(_resolve_path(first), source="os_drop")

    def _try_wire_os_drop(page: ft.Page) -> None:
        """Best-effort hook for OS-level file drops.

        Flet 0.84 does not expose OS drop events on the ``flet pack``
        runtime we ship, but we still try to wire several attribute
        names so the drop "just works" the moment a future release
        starts delivering them.
        """
        if getattr(page, "_aihub_drop_wired", False):
            return
        attempted = False
        for attr in ("on_drop", "on_file_drop", "on_files_drop"):
            handler = getattr(page, attr, "missing")
            if handler == "missing":
                continue
            attempted = True
            try:
                def _on_drop(evt: ft.ControlEvent, _attr: str = attr) -> None:
                    paths: list[str] = []
                    raw = getattr(evt, "files", None) or getattr(evt, "paths", None)
                    if raw:
                        for item in raw:
                            path = getattr(item, "path", "") or (item if isinstance(item, str) else "")
                            if path:
                                paths.append(path)
                    if paths:
                        _handle_dropped_paths(paths)
                setattr(page, attr, _on_drop)
                logger_service.log_event(
                    "INFO", log_area, "os_drop_wired", attr=attr,
                )
                break
            except Exception as exc:
                logger_service.log_exception(
                    log_area, "os_drop_wire_failed", exc, attr=attr,
                )
        if not attempted:
            logger_service.log_event(
                "DEBUG", log_area, "os_drop_unavailable",
            )
        try:
            setattr(page, "_aihub_drop_wired", True)
        except Exception as exc:
            logger_service.log_exception(
                log_area, "os_drop_marker_failed", exc,
            )

    def _paste_path(_e: ft.ControlEvent) -> None:
        # Synchronous OS clipboard read - no Flet session, no asyncio,
        # and therefore no "Session closed" race the old async path
        # was hitting.
        text = clipboard.paste()
        if not text:
            logger_service.log_event(
                "DEBUG", log_area, "paste_empty",
                backend=clipboard.backend_name(),
            )
            _show_error(unsupported_message)
            return
        # Windows ``Copy as path`` wraps the path in quotes; some users
        # paste a multi-line block. We take the first non-empty line and
        # strip surrounding quotes / whitespace.
        first_line = next(
            (line.strip() for line in text.splitlines() if line.strip()),
            "",
        )
        path = first_line.strip('"').strip("'").strip()
        logger_service.log_event(
            "INFO", log_area, "paste_path",
            chars=len(path), backend=clipboard.backend_name(),
        )
        _emit(_resolve_path(path), source="paste")

    icon = ft.Icon(ft.Icons.CLOUD_UPLOAD_OUTLINED, color=theme.primary, size=28)
    title_text = ft.Text(title, color=theme.text, size=13, weight=ft.FontWeight.W_600)
    hint_text = ft.Text(hint, color=theme.text_muted, size=11)
    # Explicit call-to-action under the hint. ``flet pack`` does not
    # currently surface OS file-drop events (see module docstring), so
    # the click + paste path workflow is the supported path - this row
    # makes the affordance impossible to miss.
    cta_text = ft.Text(
        cta_label,
        color=theme.primary,
        size=10,
        weight=ft.FontWeight.W_700,
        style=ft.TextStyle(letter_spacing=1.2),
    )
    error = ft.Text(
        ref=error_ref,
        value="",
        color="#EF4444",
        size=11,
        weight=ft.FontWeight.W_500,
        visible=False,
    )

    def _on_hover(evt: ft.ControlEvent) -> None:
        try:
            entered = bool(getattr(evt, "data", "") and evt.data == "true")
        except Exception:
            entered = False
        if entered:
            _set_hover_visuals()
        else:
            _set_idle_visuals()

    def _on_long_press(_e: ft.ControlEvent) -> None:
        _show_error(None)

    drop_zone = ft.Container(
        ref=inner_ref,
        content=ft.Column(
            controls=[icon, title_text, hint_text, cta_text, error],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
        padding=14,
        bgcolor=_idle_bg(theme),
        border=_idle_border(theme),
        border_radius=12,
        alignment=ft.Alignment.CENTER,
        height=height,
        ink=True,
        on_click=_open_picker,
        on_hover=_on_hover,
        on_long_press=_on_long_press,
        tooltip=title,
    )

    if paste_path_label and clipboard.available():
        paste_btn = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.CONTENT_PASTE, color=theme.text_muted, size=14),
                    ft.Text(
                        paste_path_label,
                        color=theme.text,
                        size=11,
                        weight=ft.FontWeight.W_500,
                    ),
                ],
                spacing=6,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            bgcolor=theme.surface,
            border=ft.border.all(1, theme.border),
            border_radius=10,
            ink=True,
            on_click=_paste_path,
            tooltip=paste_path_tooltip or paste_path_label,
        )
        return ft.Column(
            controls=[
                drop_zone,
                ft.Row(
                    controls=[ft.Container(expand=True), paste_btn],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=6,
            tight=True,
        )

    return drop_zone
