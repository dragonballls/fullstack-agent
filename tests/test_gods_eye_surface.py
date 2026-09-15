import unittest

from quality_of_life.gods_eye import GeoPoint, Place
from quality_of_life.gods_eye_map import GodsEyeMap
from quality_of_life.gods_eye_surface import GodsEyeSurface


class GodsEyeSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.place = Place("Tokyo", GeoPoint(35.6762, 139.6503), "tokyo", "fake")
        self.view = GodsEyeMap.build_search_view((self.place,), selected=self.place)

    def test_html_contains_map_and_location_control(self):
        page = GodsEyeSurface.html_for(self.view)
        self.assertIn("God’s Eye", page)
        self.assertIn("Locate me", page)
        self.assertIn("tile.openstreetmap.org", page)
        self.assertIn("navigator.geolocation.getCurrentPosition", page)
        self.assertIn("35.6762", page)

    def test_dynamic_place_text_is_script_tag_safe(self):
        dangerous = Place("</script><script>alert(1)</script>", GeoPoint(1, 2), "x", "fake")
        page = GodsEyeSurface.html_for(GodsEyeMap.build_search_view((dangerous,), selected=dangerous))
        self.assertNotIn("</script><script>alert(1)</script>", page)
        self.assertIn("\\u003c", page)

    def test_show_uses_webview_window_and_gui_loop(self):
        calls = []
        class FakeWebview:
            def create_window(self, *args, **kwargs): calls.append(("create_window", args, kwargs))
            def start(self): calls.append(("start",))
        GodsEyeSurface(FakeWebview()).show(self.view)
        self.assertEqual(calls[0][0], "create_window")
        self.assertEqual(calls[0][1][0], "God’s Eye")
        self.assertEqual(calls[0][2]["width"], 1400)
        self.assertEqual(calls[1], ("start",))
