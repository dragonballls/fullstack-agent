import sys
import types
import unittest
from unittest.mock import patch

from quality_of_life.clipboard import ClipboardController
from quality_of_life.permissions import Capability, CapabilityPolicy, CapabilityDenied
from quality_of_life.windows import WindowsController


def policy(*allowed, confirmations=()):
    return CapabilityPolicy(frozenset(allowed), frozenset(confirmations))


class QoLToolsTests(unittest.TestCase):
    def test_clipboard_round_trip_uses_bounded_text(self):
        state = {"text": "hello"}
        class FakeRoot:
            def withdraw(self): pass
            def clipboard_get(self): return state["text"]
            def clipboard_clear(self): state["text"] = ""
            def clipboard_append(self, value): state["text"] = value
            def update(self): pass
            def destroy(self): pass
        fake = types.SimpleNamespace(Tk=FakeRoot)
        with patch.dict(sys.modules, {"tkinter": fake}):
            controller = ClipboardController(policy(Capability.CLIPBOARD))
            self.assertEqual(controller.read(), "hello")
            controller.write("world")
            self.assertEqual(controller.read(), "world")

    def test_clipboard_is_denied_without_capability(self):
        controller = ClipboardController(policy())
        with self.assertRaises(CapabilityDenied):
            controller.read()

    def test_windows_controller_uses_explicit_window_handles(self):
        class User32:
            def EnumWindows(self, callback, _extra): callback(100, None)
            def IsWindowVisible(self, _hwnd): return 1
            def GetWindowTextLengthW(self, _hwnd): return 5
            def GetWindowTextW(self, _hwnd, buffer, length): buffer.value = "Title"
            def IsWindow(self, hwnd): return hwnd == 100
            def ShowWindow(self, hwnd, command): self.last = (hwnd, command)
            def SetForegroundWindow(self, hwnd): self.focused = hwnd; return 1
            def PostMessageW(self, hwnd, message, _wparam, _lparam): self.closed = (hwnd, message); return 1
        fake = User32()
        with patch("quality_of_life.windows.platform.system", return_value="Windows"):
            controller = WindowsController(policy(Capability.WINDOW_CONTROL), user32=fake)
        self.assertEqual(controller.list_windows(), [{"handle": 100, "title": "Title"}])
        controller.focus_window(100)
        self.assertEqual(fake.focused, 100)
        controller.minimize_window(100)
        controller.maximize_window(100)
        controller.close_window(100)

    def test_windows_controller_rejects_unknown_handle(self):
        class User32:
            def IsWindow(self, _hwnd): return False
            def SetForegroundWindow(self, _hwnd): raise AssertionError("unknown handles must be rejected first")
        with patch("quality_of_life.windows.platform.system", return_value="Windows"):
            controller = WindowsController(policy(Capability.WINDOW_CONTROL), user32=User32())
        with self.assertRaises(LookupError):
            controller.focus_window(999)
