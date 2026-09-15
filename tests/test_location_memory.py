import json
import tempfile
import unittest
from pathlib import Path

from quality_of_life.gods_eye import GeoPoint, LocationSnapshot
from quality_of_life.location_memory import SavedLocationStore


class SavedLocationStoreTests(unittest.TestCase):
    def test_save_and_retrieve_named_location_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "locations.json"
            store = SavedLocationStore(path)
            point = GeoPoint(34.1, -117.7)

            saved = store.save("my high school", point, address="123 Main St", source="system")
            restored = SavedLocationStore(path).get("my high school")

            self.assertEqual(saved.name, "my high school")
            self.assertEqual(restored.point, point)
            self.assertEqual(restored.address, "123 Main St")
            self.assertEqual(restored.source, "system")

    def test_saved_location_store_never_writes_credentials_or_runtime_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "locations.json"
            store = SavedLocationStore(path)
            store.save("home", GeoPoint(34.1, -117.7), address="123 Main St", source="device")
            raw = path.read_text(encoding="utf-8")
            self.assertNotIn("token", raw.casefold())
            self.assertNotIn("password", raw.casefold())
            json.loads(raw)

    def test_delete_is_explicit_and_listing_is_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "locations.json"
            store = SavedLocationStore(path)
            store.save("work", GeoPoint(34.2, -117.8))
            store.save("school", GeoPoint(34.3, -117.9))

            self.assertEqual([item.name for item in store.list()], ["school", "work"])
            self.assertTrue(store.delete("school"))
            self.assertIsNone(store.get("school"))
            self.assertFalse(store.delete("school"))

    def test_current_location_can_be_saved_only_when_permitted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "locations.json"
            store = SavedLocationStore(path)
            denied = LocationSnapshot(None, None, False, "permission-denied")
            with self.assertRaises(PermissionError):
                store.save_current("home", denied)

            allowed = LocationSnapshot(GeoPoint(34.1, -117.7), 25.0, True, "device")
            saved = store.save_current("home", allowed)
            self.assertEqual(saved.point, allowed.point)
            self.assertEqual(saved.accuracy_m, 25.0)


if __name__ == "__main__":
    unittest.main()
