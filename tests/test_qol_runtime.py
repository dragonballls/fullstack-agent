import unittest

from quality_of_life.gods_eye import GeoPoint, LocationSnapshot, Place
from quality_of_life.permissions import Capability, CapabilityDenied, CapabilityPolicy
from quality_of_life.runtime import JarvisRuntime


class FakeEye:
    def __init__(self):
        self.place = Place("Tokyo", GeoPoint(35.6762, 139.6503), "tokyo", "fake")
    def search(self, query):
        return [self.place]
    def locate_me(self):
        return LocationSnapshot(GeoPoint(34.1, -117.7), 20, True, "fake")
    def open_place(self, place):
        return {"surface": "gods-eye", "place": place.as_dict()}


class JarvisRuntimeTests(unittest.TestCase):
    def test_runtime_exposes_all_capability_tools_and_dispatches_gods_eye(self):
        policy = CapabilityPolicy(frozenset({Capability.LOCATION_READ}))
        runtime = JarvisRuntime(policy, factories={"gods_eye": lambda: FakeEye()})
        names = set(runtime.available_tools())
        self.assertTrue({"computer", "screen", "browser", "clipboard", "windows", "background", "cloud_router", "gods_eye"} <= names)
        places = runtime.dispatch(Capability.LOCATION_READ, "gods_eye.search", query="Tokyo")
        self.assertEqual(places[0].name, "Tokyo")

    def test_runtime_preserves_deny_by_default(self):
        runtime = JarvisRuntime(CapabilityPolicy(), factories={"gods_eye": FakeEye})
        with self.assertRaises(CapabilityDenied):
            runtime.dispatch(Capability.LOCATION_READ, "gods_eye.locate_me")

    def test_runtime_requires_confirmation_for_mutations(self):
        calls = []
        policy = CapabilityPolicy(frozenset({Capability.MOUSE_CONTROL}))
        fake = type("Computer", (), {"move": lambda self, x, y: calls.append((x, y))})()
        runtime = JarvisRuntime(policy, factories={"computer": lambda: fake})
        with self.assertRaises(PermissionError):
            runtime.dispatch(Capability.MOUSE_CONTROL, "computer.move", x=1, y=2)
        runtime.confirmation = lambda capability, operation: True
        runtime.dispatch(Capability.MOUSE_CONTROL, "computer.move", x=1, y=2)
        self.assertEqual(calls, [(1, 2)])
