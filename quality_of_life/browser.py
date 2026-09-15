"""Optional browser automation adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .permissions import Capability, CapabilityPolicy


class BrowserControlUnavailable(RuntimeError):
    """Raised when Playwright is not installed."""


@dataclass
class BrowserController:
    policy: CapabilityPolicy
    playwright: Any | None = None
    browser: Any | None = None

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

    def open_url(self, url: str) -> None:
        self.policy.check(Capability.BROWSER_CONTROL)
        if not (url.startswith("https://") or url.startswith("http://")):
            raise ValueError("Only http:// and https:// URLs are allowed")
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
