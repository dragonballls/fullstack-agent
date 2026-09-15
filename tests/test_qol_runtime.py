import os
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


class FakeMaintenance:
    def handle(self, request, confirmed=False):
        return {"request": request, "confirmed": confirmed}
    def diagnose(self):
        return {"diagnose": True}


class JarvisRuntimeTests(unittest.TestCase):
    def test_runtime_exposes_all_capability_tools_and_dispatches_gods_eye(self):
        policy = CapabilityPolicy(frozenset({Capability.LOCATION_READ}))
        runtime = JarvisRuntime(policy, factories={"gods_eye": lambda: FakeEye()})
        names = set(runtime.available_tools())
        self.assertTrue({"computer", "screen", "browser", "clipboard", "windows", "background", "cloud_router", "gods_eye", "windows_maintenance"} <= names)
        places = runtime.dispatch(Capability.LOCATION_READ, "gods_eye.search", query="Tokyo")
        self.assertEqual(places[0].name, "Tokyo")

    def test_runtime_defaults_cloud_router_to_omniroute(self):
        old = {name: os.environ.get(name) for name in ("JARVIS_CLOUD_BASE_URL", "JARVIS_CLOUD_MODEL", "JARVIS_OMNIROUTE_ENABLED")}
        try:
            for name in old:
                os.environ.pop(name, None)
            runtime = JarvisRuntime(CapabilityPolicy())
            router = runtime._tool("cloud_router")
            self.assertEqual(len(router.targets), 1)
            self.assertEqual(router.targets[0].name, "omniroute")
            self.assertEqual(router.targets[0].base_url, "http://127.0.0.1:20128/v1")
            self.assertEqual(router.targets[0].model, "auto")
            self.assertEqual(router.targets[0].api_key_env, "OMNIROUTE_API_KEY")
        finally:
            for name, value in old.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

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

    def test_read_only_maintenance_diagnosis_has_no_confirmation_gate(self):
        policy = CapabilityPolicy(frozenset({Capability.SYSTEM_DIAGNOSTICS}), require_confirmation=frozenset())
        runtime = JarvisRuntime(policy, factories={"windows_maintenance": lambda: FakeMaintenance()})
        result = runtime.handle_text("diagnose my PC")
        self.assertEqual(result["intent"].kind, "windows_maintenance")
        self.assertEqual(result["result"], {"diagnose": True})

    def test_maintenance_mutation_still_uses_confirmed_capability(self):
        policy = CapabilityPolicy(frozenset({Capability.SYSTEM_MAINTENANCE}), require_confirmation=frozenset())
        runtime = JarvisRuntime(policy, factories={"windows_maintenance": lambda: FakeMaintenance()})
        result = runtime.handle_text("repair my PC")
        self.assertEqual(result["result"]["confirmed"], False)
