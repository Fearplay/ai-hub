"""Drop zone for AI Career uploads (resume, LinkedIn export).

Same idea as :mod:`src.sections.ai_legal.drop_zone` but parametrised by the
allowed extensions and the callback shape. A native OS drag-drop bridge
is provided by ``flet-dropzone`` once the user has run ``flet build`` at
least once - until then we fall back to ``ft.FilePicker``, which still
gets the job done.
"""

from __future__ import annotations

import os
from typing import Callable, Optional, Sequence

import flet as ft

from src.services.file_parser import ParsedFile, parse_file
from src.theme import Theme


try:
    import flet_dropzone as ftd  # type: ignore[import-not-found]

    _DROPZONE_AVAILABLE = True
except Exception:
    ftd = None  # type: ignore[assignment]
    _DROPZONE_AVAILABLE = False


def _idle_bg(theme: Theme) -> str:
    return ft.Colors.with_opacity(0.10, theme.primary)


def _idle_border(theme: Theme) -> ft.Border:
    return ft.border.all(2, ft.Colors.with_opacity(0.30, theme.primary))


def _active_bg(theme: Theme) -> str:
    return ft.Colors.with_opacity(0.22, theme.primary)


def _active_border(theme: Theme) -> ft.Border:
    return ft.border.all(2, ft.Colors.with_opacity(0.65, theme.primary))


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
    """Drag-drop + click-to-browse zone with custom extensions."""
    file_picker = ft.FilePicker()
    picker_registered: dict[str, bool] = {"done": False}

    inner_ref = ft.Ref[ft.Container]()
    error_ref = ft.Ref[ft.Text]()

    allowed_lower = tuple(e.lower().lstrip(".") for e in extensions)

    def _set_active(active: bool) -> None:
        c = inner_ref.current
        if c is None:
            return
        c.bgcolor = _active_bg(theme) if active else _idle_bg(theme)
        c.border = _active_border(theme) if active else _idle_border(theme)
        try:
            c.update()
        except Exception:
            pass

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
        parsed = parse_file(path)
        if not parsed.ok:
            return parsed
        return parsed

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

    def _on_dropped(event) -> None:
        _set_active(False)
        files = getattr(event, "files", None) or []
        if not files:
            return
        first = files[0]
        path = first if isinstance(first, str) else getattr(first, "path", "")
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

    inner = ft.Container(
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

    if _DROPZONE_AVAILABLE and ftd is not None:
        return ftd.Dropzone(
            content=inner,
            allowed_file_types=list(allowed_lower),
            on_dropped=_on_dropped,
            on_entered=lambda e: _set_active(True),
            on_exited=lambda e: _set_active(False),
        )
    return inner
