"""Optional Windows desktop controls for quality-of-life automation."""

from __future__ import annotations

import os
from pathlib import Path
import platform
import subprocess
from dataclasses import dataclass
from typing import Any

from .permissions import Capability, CapabilityPolicy


class ComputerControlUnavailable(RuntimeError):
    """Raised when optional desktop-control dependencies are unavailable."""


@dataclass
class ComputerController:
    policy: CapabilityPolicy
    pyautogui: Any | None = None

    def __post_init__(self) -> None:
        if self.pyautogui is None and platform.system() != "Windows":
            raise ComputerControlUnavailable("Windows computer control is currently supported only on Windows.")
        try:
            if self.pyautogui is None:
                import pyautogui  # type: ignore
                self.pyautogui = pyautogui
        except ImportError as exc:
            raise ComputerControlUnavailable("Install quality_of_life optional dependencies to enable mouse/keyboard control.") from exc
        self.pyautogui.FAILSAFE = True
        self.pyautogui.PAUSE = 0.05

    def move(self, x: int, y: int) -> None:
        self.policy.check(Capability.MOUSE_CONTROL)
        self.pyautogui.moveTo(x, y, duration=0.15)

    def click(self, button: str = "left", clicks: int = 1) -> None:
        self.policy.check(Capability.MOUSE_CONTROL)
        if button not in {"left", "middle", "right"}:
            raise ValueError("button must be left, middle, or right")
        if not 1 <= clicks <= 3:
            raise ValueError("clicks must be between 1 and 3")
        self.pyautogui.click(button=button, clicks=clicks)

    def scroll(self, amount: int) -> None:
        self.policy.check(Capability.MOUSE_CONTROL)
        if not -20 <= amount <= 20:
            raise ValueError("scroll amount must be between -20 and 20")
        self.pyautogui.scroll(amount)

    def type_text(self, text: str) -> None:
        self.policy.check(Capability.KEYBOARD_CONTROL)
        if len(text) > 4000:
            raise ValueError("text exceeds the 4000-character safety limit")
        self.pyautogui.write(text, interval=0.01)

    def hotkey(self, *keys: str) -> None:
        self.policy.check(Capability.KEYBOARD_CONTROL)
        if not 1 <= len(keys) <= 5:
            raise ValueError("hotkey requires 1-5 keys")
        self.pyautogui.hotkey(*keys)

    def open_app(self, command: str, *args: str) -> subprocess.Popen[bytes]:
        self.policy.check(Capability.APP_LAUNCH)
        if not command.strip() or any("\x00" in part for part in (command, *args)):
            raise ValueError("invalid application command")
        return subprocess.Popen([command, *args], shell=False)

    def open_known_app(self, name: str) -> None:
        """Open an exact-match Windows Start Menu shortcut without shell parsing."""
        self.policy.check(Capability.APP_LAUNCH)
        normalized = " ".join(name.split()).casefold()
        if not normalized or any(ch in name for ch in "\\/:*?\"<>|"):
            raise ValueError("invalid application name")
        roots = (
            Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
            Path(os.environ.get("ProgramData", "")) / "Microsoft/Windows/Start Menu/Programs",
            Path(os.environ.get("USERPROFILE", "")) / "Desktop",
        )
        matches: list[Path] = []
        for root in roots:
            if not root.is_dir():
                continue
            try:
                for path in root.rglob("*.lnk"):
                    if path.stem.strip().casefold() == normalized:
                        matches.append(path)
                        if len(matches) > 2:
                            raise ValueError("application name is ambiguous")
            except OSError:
                continue
        if len(matches) != 1:
            raise FileNotFoundError(f"No unique Start Menu shortcut found for: {name}")
        os.startfile(str(matches[0]))  # type: ignore[attr-defined]

    @staticmethod
    def is_supported() -> bool:
        return platform.system() == "Windows" and bool(os.environ.get("SESSIONNAME") or os.environ.get("USERNAME"))
