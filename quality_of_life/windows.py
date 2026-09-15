"""Narrow Windows window-management adapter."""

from __future__ import annotations

import ctypes
import platform
from typing import Any

from .permissions import Capability, CapabilityPolicy


class WindowsControlUnavailable(RuntimeError):
    pass


class WindowsController:
    SW_MINIMIZE = 6
    SW_MAXIMIZE = 3
    WM_CLOSE = 0x0010

    def __init__(self, policy: CapabilityPolicy, user32: Any | None = None) -> None:
        if platform.system() != "Windows" and user32 is None:
            raise WindowsControlUnavailable("window control is supported only on Windows")
        self.policy = policy
        self.user32 = user32 or ctypes.windll.user32

    def list_windows(self) -> list[dict[str, object]]:
        self.policy.check(Capability.WINDOW_CONTROL)
        results: list[dict[str, object]] = []
        callback_type = getattr(ctypes, "WINFUNCTYPE", lambda *_types: lambda function: function)
        enum_proc = callback_type(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def callback(hwnd: int, _lparam: int) -> bool:
            if not self.user32.IsWindowVisible(hwnd):
                return True
            length = self.user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value.strip()
            if title:
                results.append({"handle": int(hwnd), "title": title})
            return True

        self.user32.EnumWindows(enum_proc(callback), 0)
        return results

    def _validate(self, identifier: int) -> int:
        try:
            handle = int(identifier)
        except (TypeError, ValueError) as exc:
            raise ValueError("window handle must be an integer") from exc
        if handle <= 0 or not self.user32.IsWindow(handle):
            raise LookupError(f"window not found: {identifier}")
        return handle

    def focus_window(self, identifier: int) -> None:
        self.policy.check(Capability.WINDOW_CONTROL)
        self.user32.SetForegroundWindow(self._validate(identifier))

    def minimize_window(self, identifier: int) -> None:
        self.policy.check(Capability.WINDOW_CONTROL)
        self.user32.ShowWindow(self._validate(identifier), self.SW_MINIMIZE)

    def maximize_window(self, identifier: int) -> None:
        self.policy.check(Capability.WINDOW_CONTROL)
        self.user32.ShowWindow(self._validate(identifier), self.SW_MAXIMIZE)

    def close_window(self, identifier: int) -> None:
        self.policy.check(Capability.WINDOW_CONTROL)
        self.user32.PostMessageW(self._validate(identifier), self.WM_CLOSE, 0, 0)
