import unittest
from unittest.mock import patch

from quality_of_life import spatial_windows
from quality_of_life.permissions import CapabilityPolicy
from quality_of_life.spatial_windows import SpatialWindowManager, SpatialWindowUnavailable, WindowRect


class SpatialWindowTests(unittest.TestCase):
    def test_rect_serialization(self):
        self.assertEqual(WindowRect(1, 2, 100, 50).as_dict(), {"x": 1, "y": 2, "width": 100, "height": 50})

    def test_non_windows_is_safe(self):
        try:
            SpatialWindowManager(CapabilityPolicy())
        except SpatialWindowUnavailable:
            return
        self.skipTest("runner is Windows")

    def test_graphics_capture_probe_is_cached(self):
        previous = spatial_windows._WINRT_CAPTURE
        spatial_windows._WINRT_CAPTURE = None
        calls = 0
        real_import = __import__

        def fake_import(name, *args, **kwargs):
            nonlocal calls
            if name == "winrt.windows.graphics.capture":
                calls += 1
                raise ImportError("not installed")
            return real_import(name, *args, **kwargs)

        try:
            with patch("builtins.__import__", side_effect=fake_import):
                self.assertFalse(spatial_windows._winrt_capture_available())
                self.assertFalse(spatial_windows._winrt_capture_available())
            self.assertEqual(calls, 1)
        finally:
            spatial_windows._WINRT_CAPTURE = previous

    def test_policy_is_enforced(self):
        class User32:
            def IsWindow(self, _): return True
        try:
            manager = SpatialWindowManager(CapabilityPolicy(), user32=User32())
        except SpatialWindowUnavailable:
            self.skipTest("unexpected platform restriction")
        with self.assertRaises(PermissionError):
            manager.list_windows()


if __name__ == "__main__":
    unittest.main()
