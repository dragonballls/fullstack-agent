import unittest
from types import SimpleNamespace

from quality_of_life.neural_discovery import NeuralDiscovery
from quality_of_life.neural_world import NeuralWorld


class DiscoveryTests(unittest.TestCase):
    def test_discovery_creates_stable_application_and_process_nodes(self):
        world = NeuralWorld()
        runtime = SimpleNamespace(
            _tool=lambda name: {
                "applications": SimpleNamespace(list=lambda: [
                    SimpleNamespace(id="Opera.GX", name="Opera GX", publisher="Opera", version="1", source="test")
                ]),
                "processes": SimpleNamespace(list_processes=lambda: [
                    SimpleNamespace(pid=123, name="opera.exe", executable="C:/opera.exe")
                ], list_services=lambda: [
                    SimpleNamespace(name="Dnscache", display_name="DNS Client", state="RUNNING")
                ]),
            }[name]
        )
        result = NeuralDiscovery(world, runtime).sync()
        self.assertEqual(result, {"applications": 1, "processes": 1})
        self.assertEqual(world.search("Opera GX", kind="application")[0]["id"], "app:opera.gx")
        self.assertEqual(world.search("opera.exe", kind="process")[0]["id"], "process:123")


if __name__ == "__main__":
    unittest.main()
