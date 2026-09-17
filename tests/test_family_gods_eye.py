from __future__ import annotations

from datetime import datetime, timezone
import unittest

from quality_of_life.family_gods_eye import FamilyGodsEyeSurface
from quality_of_life.family_locations import FamilyLocation, FamilyLocationService


class FakeWebView:
    def __init__(self):
        self.windows = []
        self.started = 0

    def create_window(self, *args, **kwargs):
        self.windows.append((args, kwargs))
        return object()

    def start(self):
        self.started += 1


class FamilyGodsEyeSurfaceTests(unittest.TestCase):
    def test_html_contains_family_map_and_follow_controls(self):
        html = FamilyGodsEyeSurface.html_for({"surface": "gods-eye", "family_markers": []})
        self.assertIn("God’s Eye — Family", html)
        self.assertIn("Stop following", html)
        self.assertIn("family_markers", html)
        self.assertIn("setInterval", html)

    def test_show_uses_webview_without_network_provider(self):
        service = FamilyLocationService()
        webview = FakeWebView()
        result = FamilyGodsEyeSurface(service, webview_module=webview).show()
        self.assertEqual(result, 0)
        self.assertEqual(len(webview.windows), 1)
        self.assertEqual(webview.started, 1)

    def test_show_can_focus_a_followed_family_member(self):
        service = FamilyLocationService()
        service.apply([FamilyLocation("a", "Alex", 34.1, -117.9, None, "fixture", datetime.now(timezone.utc), "on")])
        webview = FakeWebView()
        FamilyGodsEyeSurface(service, webview_module=webview).show("a")
        self.assertEqual(service.following().member_id, "a")


if __name__ == "__main__":
    unittest.main()
