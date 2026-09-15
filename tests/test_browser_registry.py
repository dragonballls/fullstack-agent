from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from quality_of_life.browser import BrowserController
from quality_of_life.browser_registry import BrowserRegistry, BrowserUnavailable
from quality_of_life.permissions import Capability, CapabilityPolicy


class BrowserRegistryTests(unittest.TestCase):
    def test_common_aliases_resolve_to_normalized_ids(self):
        root = Path(tempfile.mkdtemp())
        paths = {}
        for browser_id in ("edge", "chrome", "opera-gx"):
            path = root / f"{browser_id}.exe"
            path.write_text("stub", encoding="utf-8")
            paths[browser_id] = path
        registry = BrowserRegistry(lambda: {
            "edge": ("Microsoft Edge", "chromium", (paths["edge"],)),
            "chrome": ("Google Chrome", "chromium", (paths["chrome"],)),
            "opera-gx": ("Opera GX", "chromium", (paths["opera-gx"],)),
        })
        self.assertEqual(registry.resolve("Microsoft Edge").id, "edge")
        self.assertEqual(registry.resolve("Opera GX").id, "opera-gx")
        with self.assertRaises(BrowserUnavailable):
            registry.resolve("Firefox")

    def test_browser_controller_rejects_non_http_urls(self):
        controller = BrowserController(CapabilityPolicy(allowed=frozenset({Capability.BROWSER_CONTROL})))
        with self.assertRaises(ValueError):
            controller.open_url("file:///etc/passwd")

    def test_browser_controller_click_validates_selector(self):
        page = Mock()
        browser = Mock(contexts=[Mock(pages=[page])])
        controller = BrowserController(CapabilityPolicy(allowed=frozenset({Capability.BROWSER_CONTROL})), browser=browser)
        with self.assertRaises(ValueError):
            controller.click("   ")
        page.click.assert_not_called()


if __name__ == "__main__":
    unittest.main()
