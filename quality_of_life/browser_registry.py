"""Deterministic discovery and selection of installed desktop browsers."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


class BrowserUnavailable(RuntimeError):
    """Raised when a requested browser is not installed or cannot be launched."""


@dataclass(frozen=True)
class BrowserInstallation:
    id: str
    name: str
    family: str
    executable: Path
    available: bool = True


_ALIASES = {
    "edge": "edge", "microsoft edge": "edge", "ms edge": "edge",
    "chrome": "chrome", "google chrome": "chrome",
    "firefox": "firefox", "mozilla firefox": "firefox",
    "opera": "opera", "opera browser": "opera",
    "opera gx": "opera-gx", "operagx": "opera-gx", "opera-gx": "opera-gx",
    "brave": "brave", "brave browser": "brave",
    "vivaldi": "vivaldi",
}


def _windows_candidates() -> dict[str, tuple[str, str, tuple[Path, ...]]]:
    roots = [Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")),
             Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")),
             Path(os.environ.get("LOCALAPPDATA", ""))]
    return {
        "edge": ("Microsoft Edge", "chromium", tuple(root / "Microsoft" / "Edge" / "Application" / "msedge.exe" for root in roots)),
        "chrome": ("Google Chrome", "chromium", tuple(root / "Google" / "Chrome" / "Application" / "chrome.exe" for root in roots)),
        "firefox": ("Firefox", "gecko", tuple(root / "Mozilla Firefox" / "firefox.exe" for root in roots)),
        "opera": ("Opera", "chromium", tuple(root / "Opera" / "launcher.exe" for root in roots)),
        "opera-gx": ("Opera GX", "chromium", tuple(root / "Opera Software" / "Opera GX" / "launcher.exe" for root in roots)),
        "brave": ("Brave", "chromium", tuple(root / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe" for root in roots)),
        "vivaldi": ("Vivaldi", "chromium", tuple(root / "Vivaldi" / "Application" / "vivaldi.exe" for root in roots)),
    }


class BrowserRegistry:
    """Discover installed browsers without executing arbitrary registry data."""

    def __init__(self, candidates: Callable[[], dict[str, tuple[str, str, tuple[Path, ...]]]] | None = None) -> None:
        self._candidates = candidates or _windows_candidates
        self._cache: tuple[BrowserInstallation, ...] | None = None

    def invalidate(self) -> None:
        self._cache = None

    def discover(self) -> tuple[BrowserInstallation, ...]:
        if self._cache is not None:
            return self._cache
        found: list[BrowserInstallation] = []
        for browser_id, (name, family, candidates) in self._candidates().items():
            executable = next((path for path in candidates if path.is_file()), None)
            if executable is None:
                command = shutil.which({"edge": "msedge", "chrome": "chrome", "firefox": "firefox", "opera": "opera", "opera-gx": "opera-gx", "brave": "brave", "vivaldi": "vivaldi"}.get(browser_id, ""))
                if command:
                    executable = Path(command)
            if executable is not None:
                found.append(BrowserInstallation(browser_id, name, family, executable.resolve()))
        self._cache = tuple(sorted(found, key=lambda item: item.id))
        return self._cache

    def resolve(self, name: str) -> BrowserInstallation:
        key = " ".join(name.strip().casefold().replace("_", " ").replace("-", " ").split())
        browser_id = _ALIASES.get(key)
        if browser_id is None:
            raise BrowserUnavailable(f"Unknown browser: {name}")
        for installation in self.discover():
            if installation.id == browser_id:
                return installation
        raise BrowserUnavailable(f"Browser is not installed or unavailable: {name}")
