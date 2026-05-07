"""Click-to-browse upload zone for AI Career uploads (resume, LinkedIn export).

We intentionally do **not** depend on ``flet-dropzone`` here. That package
ships only the Flet/Python facade and expects a Flutter native bridge to
be built via ``flet build windows``. Our distribution path is
``flet pack`` (PyInstaller, single-file ``.exe`` on a clean Windows box -
no Flutter SDK required), which means the native bridge is **never**
available at runtime - so rendering ``ftd.Dropzone`` ends up as the red
"Unknown control: flet_dropzone" banner.

The same visual zone reacts to a click and opens ``ft.FilePicker``, so
the user can attach a resume the conventional way - identical behaviour
from ``STATE.resume`` / ``STATE.linkedin``'s point of view.
"""

from __future__ import annotations

import os
from typing import Callable, Optional, Sequence

import flet as ft

from src.services.file_parser import ParsedFile, parse_file
from src.theme import Theme


def _idle_bg(theme: Theme) -> str:
    return ft.Colors.with_opacity(0.10, theme.primary)


def _idle_border(theme: Theme) -> ft.Border:
    return ft.border.all(2, ft.Colors.with_opacity(0.30, theme.primary))


def upload_zone(
    theme: Theme,
    *,
    title: str,
    hint: str,
    extensions: Sequence[str],
    unsupported_message: str,
    on_file_resolved: Callable[[ParsedFile], None],
    height: int = 132,
) -> ft.Control:
    """Click-to-browse zone that opens a native file picker for the given extensions."""
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
        try:
            e.update()
        except Exception:
            pass

    def _resolve_path(path: str) -> Optional[ParsedFile]:
        if not path:
            return None
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        if ext not in allowed_lower:
            return None
        return parse_file(path)

    def _emit(parsed: Optional[ParsedFile]) -> None:
        if parsed is None:
            _show_error(unsupported_message)
            return
        if parsed.error:
            _show_error(parsed.error)
            return
        _show_error(None)
        on_file_resolved(parsed)

    async def _open_picker(e: ft.ControlEvent) -> None:
        page = e.page
        if page is None:
            return
        if not picker_registered["done"]:
            registry = getattr(page, "_services", None)
            if registry is not None:
                try:
                    registry.register_service(file_picker)
                except Exception:
                    pass
            picker_registered["done"] = True
        try:
            files = await file_picker.pick_files(
                dialog_title=title,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=list(allowed_lower),
            )
        except Exception:
            files = []
        if not files:
            return
        first = files[0]
        path = getattr(first, "path", "") or ""
        if path:
            _emit(_resolve_path(path))

    icon = ft.Icon(ft.Icons.CLOUD_UPLOAD_OUTLINED, color=theme.primary, size=28)
    title_text = ft.Text(title, color=theme.text, size=13, weight=ft.FontWeight.W_600)
    hint_text = ft.Text(hint, color=theme.text_muted, size=11)
    error = ft.Text(
        ref=error_ref,
        value="",
        color="#EF4444",
        size=11,
        weight=ft.FontWeight.W_500,
        visible=False,
    )

    return ft.Container(
        ref=inner_ref,
        content=ft.Column(
            controls=[icon, title_text, hint_text, error],
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
    )
