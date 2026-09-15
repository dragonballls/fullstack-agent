"""Optional browser automation adapter."""

from __future__ import annotations

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
    _selected_browser: str | None = None

    def _registry(self) -> BrowserRegistry:
        if self.registry is None:
            self.registry = BrowserRegistry()
        return self.registry

    def start(self, browser: str | None = None) -> None:
        self.policy.check(Capability.BROWSER_CONTROL)
        try:
            if self.playwright is None:
                from playwright.sync_api import sync_playwright  # type: ignore
                self.playwright = sync_playwright().start()
            if self.browser is None:
                if browser:
                    installation = self._registry().resolve(browser)
                    engine = self.playwright.firefox if installation.family == "gecko" else self.playwright.chromium
                    self.browser = engine.launch(headless=False, executable_path=str(installation.executable))
                    self._selected_browser = installation.id
                else:
                    self.browser = self.playwright.chromium.launch(headless=False)
                    self._selected_browser = None
        except (BrowserUnavailable, OSError) as exc:
            self._registry().invalidate()
            raise BrowserControlUnavailable(f"Unable to start requested browser: {browser or 'default'}") from exc
        except Exception as exc:
            raise BrowserControlUnavailable(f"Unable to start browser automation: {exc}") from exc

    @staticmethod
    def _validate_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Only absolute http:// and https:// URLs are allowed")

    def _page(self) -> Any:
        if self.browser is None:
            self.start(self._selected_browser)
        if self.browser.contexts and self.browser.contexts[0].pages:
            return self.browser.contexts[0].pages[0]
        return self.browser.new_context().new_page()

    def open_url(self, url: str, browser: str | None = None) -> None:
        self.policy.check(Capability.BROWSER_CONTROL)
        self._validate_url(url)
        if browser is not None:
            requested_id = self._registry().resolve(browser).id
            if self.browser is not None and self._selected_browser != requested_id:
                self.close()
        self.start(browser)
        self._page().goto(url, wait_until="domcontentloaded")

    def navigate(self, url: str) -> None:
        self.policy.check(Capability.BROWSER_CONTROL)
        self._validate_url(url)
        self._page().goto(url, wait_until="domcontentloaded")

    def click(self, selector: str) -> None:
        self.policy.check(Capability.BROWSER_CONTROL)
        if not selector.strip():
            raise ValueError("selector is required")
        self._page().click(selector)

    def fill(self, selector: str, text: str) -> None:
        self.policy.check(Capability.BROWSER_CONTROL)
        if not selector.strip():
            raise ValueError("selector is required")
        self._page().fill(selector, text)

    def read_text(self, selector: str = "body") -> str:
        self.policy.check(Capability.BROWSER_CONTROL)
        if not selector.strip():
            raise ValueError("selector is required")
        return str(self._page().locator(selector).inner_text())

    def pages(self) -> tuple[str, ...]:
        self.policy.check(Capability.BROWSER_CONTROL)
        if self.browser is None:
            return ()
        return tuple(str(page.url) for context in self.browser.contexts for page in context.pages)

    def close(self) -> None:
        if self.browser is not None:
            self.browser.close()
            self.browser = None
        if self.playwright is not None:
            self.playwright.stop()
            self.playwright = None
        self._selected_browser = None
