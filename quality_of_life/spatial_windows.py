"""Guarded Windows spatial window adapter with preview-capture fallback."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
from io import BytesIO
import platform
from typing import Any

from .permissions import Capability, CapabilityPolicy


class SpatialWindowUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class WindowRect:
    x: int
    y: int
    width: int
    height: int

    def as_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


class SpatialWindowManager:
    SW_HIDE = 0
    SW_SHOW = 5
    SW_MINIMIZE = 6
    SW_RESTORE = 9
    SW_MAXIMIZE = 3
    SWP_NOACTIVATE = 0x0010
    SWP_NOZORDER = 0x0004
    SWP_FRAMECHANGED = 0x0020
    SWP_SHOWWINDOW = 0x0040
    GWL_STYLE = -16
    GWL_EXSTYLE = -20
    WS_CHILD = 0x40000000
    WS_POPUP = 0x80000000
    WS_EX_APPWINDOW = 0x00040000
    WS_EX_TOOLWINDOW = 0x00000080

    def __init__(self, policy: CapabilityPolicy, user32: Any | None = None) -> None:
        if platform.system() != "Windows" and user32 is None:
            raise SpatialWindowUnavailable("spatial window control is supported only on Windows")
        self.policy = policy
        self.user32 = user32 or ctypes.windll.user32
        self._host_handle: int | None = None
        self._embedded: dict[int, dict[str, int]] = {}

    def set_host_handle(self, host_handle: int) -> int:
        handle = self._validate(host_handle)
        self._host_handle = handle
        return handle

    @property
    def host_handle(self) -> int | None:
        return self._host_handle

    def _get_long(self, handle: int, index: int) -> int:
        getter = getattr(self.user32, "GetWindowLongPtrW", None) or getattr(self.user32, "GetWindowLongW", None)
        if getter is None:
            raise SpatialWindowUnavailable("native style API is unavailable")
        return int(getter(handle, index))

    def _set_long(self, handle: int, index: int, value: int) -> int:
        setter = getattr(self.user32, "SetWindowLongPtrW", None) or getattr(self.user32, "SetWindowLongW", None)
        if setter is None:
            raise SpatialWindowUnavailable("native style API is unavailable")
        return int(setter(handle, index, value))

    def embedding_state(self, identifier: int) -> dict[str, object]:
        handle = self._validate(identifier)
        state = self._embedded.get(handle)
        return {"embedded": state is not None, **(state or {})}

    def embed(
        self, identifier: int, *, host_handle: int | None = None,
        x: int = 24, y: int = 24, width: int = 960, height: int = 640,
        confirmed: bool = False,
    ) -> dict[str, object]:
        self.policy.check(Capability.WINDOW_CONTROL)
        if not confirmed:
            raise PermissionError("confirmation is required to embed a native application")
        child = self._validate(identifier)
        host = self._validate(host_handle or self._host_handle or 0)
        if child == host:
            raise ValueError("a window cannot embed itself")
        if child in self._embedded:
            self.move_resize(child, x, y, width, height, confirmed=True)
            return {"ok": True, "embedded": True, "handle": child, "host_handle": host, "already_embedded": True}

        get_parent = getattr(self.user32, "GetParent", None)
        old_parent = int(get_parent(child)) if get_parent else 0
        if old_parent != 0:
            raise SpatialWindowUnavailable("only top-level windows can be spatially embedded")
        original_style = self._get_long(child, self.GWL_STYLE)
        original_exstyle = self._get_long(child, self.GWL_EXSTYLE)
        original_rect = self.rect(child).as_dict()

        if not self.user32.SetParent(child, host):
            raise SpatialWindowUnavailable("Windows rejected the spatial parent change")
        try:
            self._set_long(child, self.GWL_STYLE, (original_style & ~self.WS_POPUP) | self.WS_CHILD)
            self._set_long(child, self.GWL_EXSTYLE, (original_exstyle & ~self.WS_EX_APPWINDOW) | self.WS_EX_TOOLWINDOW)
            ok = self.user32.SetWindowPos(
                child, 0, int(x), int(y), int(width), int(height),
                self.SWP_NOACTIVATE | self.SWP_NOZORDER | self.SWP_FRAMECHANGED | self.SWP_SHOWWINDOW,
            )
            if not ok:
                raise SpatialWindowUnavailable("embedded window could not be positioned")
        except Exception:
            try:
                self.user32.SetParent(child, 0)
                self._set_long(child, self.GWL_STYLE, original_style)
                self._set_long(child, self.GWL_EXSTYLE, original_exstyle)
            except Exception:
                pass
            raise

        self._embedded[child] = {
            "host_handle": host, "original_parent": old_parent,
            "original_style": original_style, "original_exstyle": original_exstyle,
            "original_x": original_rect["x"], "original_y": original_rect["y"],
            "original_width": original_rect["width"], "original_height": original_rect["height"],
        }
        return {"ok": True, "embedded": True, "handle": child, "host_handle": host, "x": x, "y": y, "width": width, "height": height}

    def unembed(self, identifier: int, *, confirmed: bool = False) -> dict[str, object]:
        self.policy.check(Capability.WINDOW_CONTROL)
        if not confirmed:
            raise PermissionError("confirmation is required to restore a native application window")
        handle = self._validate(identifier)
        state = self._embedded.get(handle)
        if state is None:
            return {"ok": True, "embedded": False, "handle": handle}
        if not self.user32.SetParent(handle, int(state["original_parent"])):
            raise SpatialWindowUnavailable("Windows rejected the spatial parent restore")
        self._set_long(handle, self.GWL_STYLE, int(state["original_style"]))
        self._set_long(handle, self.GWL_EXSTYLE, int(state["original_exstyle"]))
        self.user32.SetWindowPos(
            handle, 0, int(state["original_x"]), int(state["original_y"]),
            int(state["original_width"]), int(state["original_height"]),
            self.SWP_NOACTIVATE | self.SWP_NOZORDER | self.SWP_FRAMECHANGED | self.SWP_SHOWWINDOW,
        )
        self._embedded.pop(handle, None)
        return {"ok": True, "embedded": False, "handle": handle}

    def _validate(self, identifier: int) -> int:
        try:
            handle = int(identifier)
        except (TypeError, ValueError) as exc:
            raise ValueError("window handle must be an integer") from exc
        if handle <= 0 or not self.user32.IsWindow(handle):
            raise LookupError(f"window not found: {identifier}")
        return handle

    def rect(self, identifier: int) -> WindowRect:
        handle = self._validate(identifier)
        from ctypes import wintypes
        rect = wintypes.RECT()
        if not self.user32.GetWindowRect(handle, ctypes.byref(rect)):
            raise SpatialWindowUnavailable("window rectangle is unavailable")
        return WindowRect(int(rect.left), int(rect.top), max(1, int(rect.right - rect.left)), max(1, int(rect.bottom - rect.top)))

    def list_windows(self) -> list[dict[str, object]]:
        self.policy.check(Capability.WINDOW_CONTROL)
        results: list[dict[str, object]] = []
        callback_type = getattr(ctypes, "WINFUNCTYPE", lambda *_types: lambda function: function)
        enum_proc = callback_type(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def callback(hwnd: int, _lparam: int) -> bool:
            handle = int(hwnd)
            if not self.user32.IsWindowVisible(handle):
                return True
            length = self.user32.GetWindowTextLengthW(handle)
            if length <= 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(handle, buffer, length + 1)
            title = buffer.value.strip()
            if not title:
                return True
            rect = self.rect(handle)
            pid_value = ctypes.c_ulong()
            process_id = None
            try:
                self.user32.GetWindowThreadProcessId(handle, ctypes.byref(pid_value))
                process_id = int(pid_value.value)
            except Exception:
                pass
            results.append({
                "handle": handle, "title": title[:500], "process_id": process_id,
                "rect": rect.as_dict(), "visible": True,
                "minimized": bool(self.user32.IsIconic(handle)),
                "presentation": self.presentation_capabilities(handle),
            })
            return True

        self.user32.EnumWindows(enum_proc(callback), 0)
        return results

    def focus(self, identifier: int, *, confirmed: bool = False) -> bool:
        self.policy.check(Capability.WINDOW_CONTROL)
        if not confirmed:
            raise PermissionError("confirmation is required to focus a spatial window")
        return bool(self.user32.SetForegroundWindow(self._validate(identifier)))

    def move_resize(self, identifier: int, x: int, y: int, width: int, height: int, *, confirmed: bool = False) -> bool:
        self.policy.check(Capability.WINDOW_CONTROL)
        if not confirmed:
            raise PermissionError("confirmation is required to move or resize a spatial window")
        if width <= 0 or height <= 0 or width > 16_384 or height > 16_384:
            raise ValueError("window dimensions are outside supported bounds")
        return bool(self.user32.SetWindowPos(self._validate(identifier), 0, int(x), int(y), int(width), int(height), self.SWP_NOACTIVATE | self.SWP_NOZORDER))

    def set_visible(self, identifier: int, visible: bool, *, confirmed: bool = False) -> bool:
        self.policy.check(Capability.WINDOW_CONTROL)
        if not confirmed:
            raise PermissionError("confirmation is required to change visibility")
        return bool(self.user32.ShowWindow(self._validate(identifier), self.SW_SHOW if visible else self.SW_HIDE))

    def restore(self, identifier: int, *, confirmed: bool = False) -> bool:
        self.policy.check(Capability.WINDOW_CONTROL)
        if not confirmed:
            raise PermissionError("confirmation is required to restore a window")
        return bool(self.user32.ShowWindow(self._validate(identifier), self.SW_RESTORE))

    def minimize(self, identifier: int, *, confirmed: bool = False) -> bool:
        self.policy.check(Capability.WINDOW_CONTROL)
        if not confirmed:
            raise PermissionError("confirmation is required to minimize a window")
        return bool(self.user32.ShowWindow(self._validate(identifier), self.SW_MINIMIZE))

    def maximize(self, identifier: int, *, confirmed: bool = False) -> bool:
        self.policy.check(Capability.WINDOW_CONTROL)
        if not confirmed:
            raise PermissionError("confirmation is required to maximize a window")
        return bool(self.user32.ShowWindow(self._validate(identifier), self.SW_MAXIMIZE))

    def close(self, identifier: int, *, confirmed: bool = False) -> bool:
        self.policy.check(Capability.WINDOW_CONTROL)
        if not confirmed:
            raise PermissionError("confirmation is required to close a window")
        return bool(self.user32.PostMessageW(self._validate(identifier), 0x0010, 0, 0))

    def presentation_capabilities(self, identifier: int) -> dict[str, bool]:
        self._validate(identifier)
        try:
            import winrt.windows.graphics.capture  # type: ignore # noqa: F401
            winrt_capture = True
        except ImportError:
            winrt_capture = False
        return {
            "native_window": True,
            "windows_graphics_capture": winrt_capture,
            "preview_capture": True,
            "interactive_embedding": False,
        }

    def capture_png(self, identifier: int, *, max_width: int = 720) -> str:
        self.policy.check(Capability.SCREEN_READ)
        if max_width < 64:
            raise ValueError("max_width must be at least 64")
        handle = self._validate(identifier)
        rect = self.rect(handle)
        try:
            from PIL import ImageGrab  # type: ignore
        except ImportError as exc:
            raise SpatialWindowUnavailable("Pillow is required for window previews") from exc
        try:
            image = ImageGrab.grab(
                bbox=(rect.x, rect.y, rect.x + rect.width, rect.y + rect.height),
                include_layered_windows=True,
            )
        except TypeError:
            image = ImageGrab.grab(bbox=(rect.x, rect.y, rect.x + rect.width, rect.y + rect.height))
        ratio = min(1.0, float(max_width) / max(1, image.width))
        if ratio < 1.0:
            image = image.resize((max_width, max(1, int(image.height * ratio))))
        output = BytesIO()
        image.save(output, format="PNG", optimize=False)
        import base64
        return base64.b64encode(output.getvalue()).decode("ascii")


class UnavailableSpatialWindowManager:
    def list_windows(self) -> list[dict[str, object]]:
        return []
