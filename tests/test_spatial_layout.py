import unittest
from tempfile import TemporaryDirectory

from quality_of_life.spatial_layout import SpatialLayoutStore


class SpatialLayoutTests(unittest.TestCase):
    def test_round_trip(self):
        with TemporaryDirectory() as tmp:
            path = f"{tmp}/layout.json"
            first = SpatialLayoutStore(path)
            first.upsert("opera:123", position=(1, 2, 3), rotation=(0.1, 0.2, 0.3), scale=2.5, pinned=True, mode="portal")
            second = SpatialLayoutStore(path)
            loaded = second.get("opera:123")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.position, (1.0, 2.0, 3.0))
            self.assertEqual(loaded.rotation, (0.1, 0.2, 0.3))
            self.assertTrue(loaded.pinned)
            self.assertEqual(loaded.mode, "portal")

    def test_invalid_mode_rejected(self):
        with TemporaryDirectory() as tmp:
            store = SpatialLayoutStore(f"{tmp}/layout.json")
            with self.assertRaises(ValueError):
                store.upsert("x", mode="bad")

    def test_scale_is_bounded(self):
        with TemporaryDirectory() as tmp:
            store = SpatialLayoutStore(f"{tmp}/layout.json")
            self.assertEqual(store.upsert("x", scale=999).scale, 100.0)
            self.assertEqual(store.upsert("x", scale=0).scale, 0.05)
