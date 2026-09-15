"""Optional browser automation adapter."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from .browser_registry import BrowserRegistry, BrowserUnavailable
from .permissions import Capability, CapabilityPolicy


class BrowserControlUnavailable(RuntimeError):
    """Raised when browser automation or a requested browser is unavailable."""


@dataclass
class BrowserController:
    policy: CapabilityPolicy
    playwright: Any | None = None
    browser: Any | None = None
    registry: BrowserRegistry | None = None

    def _registry(self) -> BrowserRegistry:
        if self.registry is None:
            self.registry = BrowserRegistry()
        return self.registry

    def start(self) -> None:
        self.policy.check(Capability.BROWSER_CONTROL)
        try:
            if self.playwright is None:
                from playwright.sync_api import sync_playwright  # type: ignore
                self.playwright = sync_playwright().start()
            if self.browser is None:
                self.browser = self.playwright.chromium.launch(headless=False)
        except Exception as exc:
            raise BrowserControlUnavailable(f"Unable to start browser automation: {exc}") from exc

    @staticmethod
    def _validate_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Only absolute http:// and https:// URLs are allowed")

    def open_url(self, url: str, browser: str | None = None) -> None:
        self.policy.check(Capability.BROWSER_CONTROL)
        self._validate_url(url)
        if browser is not None:
            try:
                installation = self._registry().resolve(browser)
                subprocess.Popen([str(installation.executable), url], shell=False)
            except (BrowserUnavailable, OSError) as exc:
                self._registry().invalidate()
                raise BrowserControlUnavailable(f"Unable to launch requested browser: {browser}") from exc
            return
        self.start()
        page = self.browser.contexts[0].pages[0] if self.browser.contexts else self.browser.new_context().new_page()
        page.goto(url, wait_until="domcontentloaded")

    def close(self) -> None:
        if self.browser is not None:
            self.browser.close()
            self.browser = None
        if self.playwright is not None:
            self.playwright.stop()
            self.playwright = None
