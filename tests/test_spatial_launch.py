import unittest
from types import SimpleNamespace

from quality_of_life.permissions import Capability, CapabilityPolicy
from quality_of_life.runtime import JarvisRuntime


class FakeComputer:
    def open_known_app(self, name):
        return None

    def open_app(self, command):
        return SimpleNamespace(pid=4242)


class FakeApplications:
    def resolve(self, name):
        return SimpleNamespace(name=name)


class FakeSpatial:
    def __init__(self):
        self.calls = 0
        self.embeds = []

    def list_windows(self):
        self.calls += 1
        if self.calls == 1:
            return [{"handle": 100, "title": "Jarvis", "process_id": 999, "rect": {"width": 1200, "height": 800}}]
        return [
            {"handle": 100, "title": "Jarvis", "process_id": 999, "rect": {"width": 1200, "height": 800}},
            {"handle": 321, "title": "Opera GX", "process_id": 4242, "rect": {"width": 900, "height": 600}},
        ]

    def embed(self, handle, **kwargs):
        self.embeds.append((handle, kwargs))
        return {"ok": True, "embedded": True, "handle": handle}


class SpatialLaunchTests(unittest.TestCase):
    def test_generic_spatial_launch_finds_new_window_and_embeds(self):
        spatial = FakeSpatial()
        runtime = JarvisRuntime(
            CapabilityPolicy(allowed=frozenset({
                Capability.APP_LAUNCH,
                Capability.WINDOW_CONTROL,
            })),
            confirmation=lambda *_: True,
            factories={
                "applications": lambda: FakeApplications(),
                "computer": lambda: FakeComputer(),
                "spatial_windows": lambda: spatial,
            },
        )
        result = runtime.open_application_spatial("Opera GX", confirmed=True, embed=True)
        self.assertTrue(result["launched"])
        self.assertTrue(result["embedded"])
        self.assertEqual(spatial.embeds[0][0], 321)


if __name__ == "__main__":
    unittest.main()
