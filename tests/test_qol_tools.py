import types

import pytest

from quality_of_life.clipboard import ClipboardController
from quality_of_life.permissions import Capability, CapabilityPolicy, CapabilityDenied
from quality_of_life.windows import WindowsController


def policy(*allowed, confirmations=()):
    return CapabilityPolicy(frozenset(allowed), frozenset(confirmations))


def test_clipboard_round_trip_uses_bounded_text(monkeypatch):
    state = {"text": "hello"}
    class FakeRoot:
        def withdraw(self): pass
        def clipboard_get(self): return state["text"]
        def clipboard_clear(self): state["text"] = ""
        def clipboard_append(self, value): state["text"] = value
        def update(self): pass
        def destroy(self): pass
    fake = types.SimpleNamespace(Tk=FakeRoot)
    monkeypatch.setitem(__import__("sys").modules, "tkinter", fake)
    controller = ClipboardController(policy(Capability.CLIPBOARD))
    assert controller.read() == "hello"
    controller.write("world")
    assert controller.read() == "world"


def test_clipboard_is_denied_without_capability():
    controller = ClipboardController(policy())
    with pytest.raises(CapabilityDenied):
        controller.read()


def test_windows_controller_uses_explicit_window_handles(monkeypatch):
    class User32:
        def EnumWindows(self, callback, _extra):
            callback(100, None)
        def IsWindowVisible(self, _hwnd): return 1
        def GetWindowTextLengthW(self, _hwnd): return 5
        def GetWindowTextW(self, _hwnd, buffer, length): buffer.value = "Title"
        def IsWindow(self, hwnd): return hwnd == 100
        def ShowWindow(self, hwnd, command): self.last = (hwnd, command)
        def SetForegroundWindow(self, hwnd): self.focused = hwnd; return 1
        def PostMessageW(self, hwnd, message, _wparam, _lparam): self.closed = (hwnd, message); return 1
    fake = User32()
    monkeypatch.setattr("quality_of_life.windows.platform.system", lambda: "Windows")
    controller = WindowsController(policy(Capability.WINDOW_CONTROL, Capability.APP_LAUNCH), user32=fake)
    assert controller.list_windows() == [{"handle": 100, "title": "Title"}]
    controller.focus_window(100)
    assert fake.focused == 100
    controller.minimize_window(100)
    controller.maximize_window(100)
    controller.close_window(100)


def test_windows_controller_rejects_unknown_handle(monkeypatch):
    monkeypatch.setattr("quality_of_life.windows.platform.system", lambda: "Windows")
    controller = WindowsController(policy(Capability.WINDOW_CONTROL))
    with pytest.raises(LookupError):
        controller.focus_window(999)
