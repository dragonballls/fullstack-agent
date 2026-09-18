import unittest
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
