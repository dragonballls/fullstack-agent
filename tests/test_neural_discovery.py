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
        self.assertEqual(result["applications"], 1)
        self.assertEqual(result["processes"], 1)
        self.assertEqual(result["telemetry"], 6)
        self.assertEqual(world.search("Opera GX", kind="application")[0]["id"], "app:opera.gx")
        self.assertEqual(world.search("opera.exe", kind="process")[0]["id"], "process:123")


    def test_browser_classification_avoids_substring_false_positive(self):
        world = NeuralWorld()
        applications = SimpleNamespace(list=lambda: [
            SimpleNamespace(id="knowledge-base", name="Knowledge Base", publisher="", version="1", source="test"),
            SimpleNamespace(id="microsoft-edge", name="Microsoft Edge", publisher="", version="1", source="test"),
        ])
        discovery = NeuralDiscovery(world, SimpleNamespace(_tool=lambda name: applications))

        self.assertEqual(discovery.sync_applications(), 2)
        self.assertEqual(world.search("Knowledge Base", kind="application")[0]["parent_id"], "jarvis.system")
        self.assertEqual(world.search("Microsoft Edge", kind="application")[0]["parent_id"], "jarvis.browser")

    def test_first_cpu_sample_is_initialized_before_publish(self):
        from unittest.mock import patch
        class Memory:
            percent = 41.5
        class Swap:
            percent = 12.0
        class Disk:
            percent = 55.0
        class Net:
            bytes_sent = 1000000
            bytes_recv = 2000000

        calls = []
        def cpu_percent(interval=None):
            calls.append(interval)
            return 0.0 if interval is None and len(calls) == 1 else 17.0

        fake_psutil = SimpleNamespace(
            cpu_percent=cpu_percent,
            virtual_memory=lambda: Memory(),
            swap_memory=lambda: Swap(),
            disk_usage=lambda root: Disk(),
            net_io_counters=lambda: Net(),
        )
        world = NeuralWorld()
        discovery = NeuralDiscovery(world, SimpleNamespace())
        with patch.dict("sys.modules", {"psutil": fake_psutil}):
            self.assertEqual(discovery.sync_telemetry(), 6)

        node = world.search("CPU Utilization", kind="performance")[0]
        self.assertEqual(node["metadata"]["value"], 17.0)
        self.assertEqual(calls, [None, 0.1])

    def test_discovery_includes_services(self):
        world = NeuralWorld()
        services = SimpleNamespace(list_services=lambda: [
            SimpleNamespace(name="Dnscache", display_name="DNS Client", state="RUNNING")
        ])
        runtime = SimpleNamespace(_tool=lambda name: services)
        self.assertEqual(NeuralDiscovery(world, runtime).sync_services(), 1)
        node = world.search("DNS Client", kind="service")[0]
        self.assertEqual(node["parent_id"], "jarvis.system")
        self.assertEqual(node["lifecycle"], "active")
        self.assertTrue(node["metadata"]["auto_layout"])

    def test_discovery_includes_read_only_telemetry(self):
        from unittest.mock import patch
        class Memory:
            percent = 41.5
        class Swap:
            percent = 12.0
        class Disk:
            percent = 55.0
        class Net:
            bytes_sent = 1000000
            bytes_recv = 2000000
        world = NeuralWorld()
        discovery = NeuralDiscovery(world, SimpleNamespace())
        fake_psutil = SimpleNamespace(
            cpu_percent=lambda interval=None: 17.0,
            virtual_memory=lambda: Memory(),
            swap_memory=lambda: Swap(),
            disk_usage=lambda root: Disk(),
            net_io_counters=lambda: Net(),
        )
        with patch.dict("sys.modules", {"psutil": fake_psutil}):
            self.assertEqual(discovery.sync_telemetry(), 6)
        node = world.search("CPU Utilization", kind="performance")[0]
        self.assertEqual(node["parent_id"], "jarvis.system")
        self.assertTrue(node["metadata"]["read_only"])
        self.assertEqual(node["metadata"]["metric"], "percent")


if __name__ == "__main__":
    unittest.main()
