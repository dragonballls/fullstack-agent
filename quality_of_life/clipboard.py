"""Cross-platform clipboard adapter with explicit capability checks."""

from __future__ import annotations

from typing import Any

from .permissions import Capability, CapabilityPolicy


class ClipboardUnavailable(RuntimeError):
    pass


class ClipboardController:
    MAX_TEXT = 8000

    def __init__(self, policy: CapabilityPolicy, tkinter_module: Any | None = None) -> None:
        self.policy = policy
        self._tkinter = tkinter_module

    def _root(self):
        if self._tkinter is None:
            try:
                import tkinter
            except ImportError as exc:
                raise ClipboardUnavailable("tkinter is required for clipboard access") from exc
            self._tkinter = tkinter
        root = self._tkinter.Tk()
        root.withdraw()
        return root

    def read(self) -> str:
        self.policy.check(Capability.CLIPBOARD)
        root = self._root()
        try:
            value = root.clipboard_get()
            if not isinstance(value, str):
                raise ClipboardUnavailable("clipboard content is not text")
            return value[: self.MAX_TEXT]
        except Exception as exc:
            raise ClipboardUnavailable(f"unable to read clipboard: {exc}") from exc
        finally:
            root.destroy()

    def write(self, text: str) -> None:
        self.policy.check(Capability.CLIPBOARD)
        if len(text) > self.MAX_TEXT:
            raise ValueError(f"clipboard text exceeds the {self.MAX_TEXT}-character limit")
        root = self._root()
        try:
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
        except Exception as exc:
            raise ClipboardUnavailable(f"unable to write clipboard: {exc}") from exc
        finally:
            root.destroy()
