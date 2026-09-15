"""Deterministic discovery and selection of installed desktop browsers."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


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
    program_files = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
    program_files_x86 = Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
    local_app_data = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    return {
        "edge": ("Microsoft Edge", "chromium", (program_files / "Microsoft/Edge/Application/msedge.exe", program_files_x86 / "Microsoft/Edge/Application/msedge.exe", local_app_data / "Microsoft/Edge/Application/msedge.exe")),
        "chrome": ("Google Chrome", "chromium", (program_files / "Google/Chrome/Application/chrome.exe", program_files_x86 / "Google/Chrome/Application/chrome.exe", local_app_data / "Google/Chrome/Application/chrome.exe")),
        "firefox": ("Firefox", "gecko", (program_files / "Mozilla Firefox/firefox.exe", program_files_x86 / "Mozilla Firefox/firefox.exe", local_app_data / "Mozilla Firefox/firefox.exe")),
        "opera": ("Opera", "chromium", (program_files / "Opera/launcher.exe", program_files_x86 / "Opera/launcher.exe", local_app_data / "Programs/Opera/launcher.exe", local_app_data / "Opera/launcher.exe")),
        "opera-gx": ("Opera GX", "chromium", (program_files / "Opera GX/launcher.exe", program_files_x86 / "Opera GX/launcher.exe", local_app_data / "Programs/Opera GX/launcher.exe", local_app_data / "Opera Software/Opera GX/launcher.exe")),
        "brave": ("Brave", "chromium", (program_files / "BraveSoftware/Brave-Browser/Application/brave.exe", program_files_x86 / "BraveSoftware/Brave-Browser/Application/brave.exe", local_app_data / "BraveSoftware/Brave-Browser/Application/brave.exe")),
        "vivaldi": ("Vivaldi", "chromium", (program_files / "Vivaldi/Application/vivaldi.exe", program_files_x86 / "Vivaldi/Application/vivaldi.exe", local_app_data / "Vivaldi/Application/vivaldi.exe")),
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
        commands = {"edge": "msedge", "chrome": "chrome", "firefox": "firefox", "opera": "opera", "opera-gx": "opera-gx", "brave": "brave", "vivaldi": "vivaldi"}
        for browser_id, (name, family, candidates) in self._candidates().items():
            executable = next((path for path in candidates if path.is_file()), None)
            if executable is None:
                command = shutil.which(commands.get(browser_id, ""))
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
