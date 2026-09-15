import tempfile
import unittest
from pathlib import Path

from quality_of_life.capabilities import operation
from quality_of_life.gods_eye import GeoPoint, LocationSnapshot
from quality_of_life.intents import parse_intent
from quality_of_life.location_memory import SavedLocationStore
from quality_of_life.permissions import Capability


class SavedLocationIntegrationTests(unittest.TestCase):
    def test_parse_save_current_location_intent(self):
        intent = parse_intent("save my current location as my high school")
        self.assertEqual(intent.kind, "save_current_location")
        self.assertEqual(intent.arguments["name"], "my high school")

    def test_location_write_operations_use_location_write_capability(self):
        self.assertEqual(operation("locations.save").capability, Capability.LOCATION_WRITE)
        self.assertEqual(operation("locations.delete").capability, Capability.LOCATION_WRITE)
        self.assertEqual(operation("locations.get").capability, Capability.LOCATION_READ)

    def test_saved_current_location_round_trips_through_store(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SavedLocationStore(Path(directory) / "locations.json")
            snapshot = LocationSnapshot(GeoPoint(34.1, -117.7), 12.0, True, "device")
            saved = store.save_current("my high school", snapshot)
            self.assertEqual(store.get("MY HIGH SCHOOL"), saved)


if __name__ == "__main__":
    unittest.main()
