import tempfile
import unittest
from pathlib import Path

from quality_of_life.gods_eye import GeoPoint, GodsEye, LocationSnapshot
from quality_of_life.location_memory import SavedLocationStore
from quality_of_life.permissions import Capability, CapabilityPolicy
from quality_of_life.runtime import JarvisRuntime


class FakeLocationProvider:
    def current(self):
        return LocationSnapshot(GeoPoint(34.1, -117.7), 15.0, True, "device-test")


class FakeGeocoder:
    def search(self, query):
        return []


class SavedLocationRuntimeTests(unittest.TestCase):
    def test_determine_current_location_then_save_and_retrieve_by_name(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SavedLocationStore(Path(directory) / "locations.json")
            eye = GodsEye(FakeGeocoder(), FakeLocationProvider())
            policy = CapabilityPolicy(
                allowed=frozenset({Capability.LOCATION_READ, Capability.LOCATION_WRITE}),
                require_confirmation=frozenset(),
            )
            runtime = JarvisRuntime(
                policy,
                factories={"gods_eye": lambda: eye, "locations": lambda: store},
            )

            current = runtime.handle_text("where am I")["result"]
            self.assertTrue(current.permitted)
            self.assertEqual(current.point, GeoPoint(34.1, -117.7))

            saved = runtime.dispatch(Capability.LOCATION_WRITE, "locations.save_current", name="my high school", confirmed=True)
            restored = runtime.dispatch(Capability.LOCATION_READ, "locations.get", name="my high school")
            self.assertEqual(restored, saved)
            self.assertEqual(restored.point, current.point)

    def test_runtime_requires_confirmation_when_policy_protects_location_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            policy = CapabilityPolicy(
                allowed=frozenset({Capability.LOCATION_READ, Capability.LOCATION_WRITE}),
                require_confirmation=frozenset({Capability.LOCATION_WRITE}),
            )
            runtime = JarvisRuntime(
                policy,
                factories={"gods_eye": lambda: GodsEye(FakeGeocoder(), FakeLocationProvider()), "locations": lambda: SavedLocationStore(Path(directory) / "locations.json")},
            )
            with self.assertRaises(PermissionError):
                runtime.dispatch(Capability.LOCATION_WRITE, "locations.save_current", name="home", confirmed=True)


if __name__ == "__main__":
    unittest.main()
