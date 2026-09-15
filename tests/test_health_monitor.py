import os
import unittest

from quality_of_life.health_monitor import HealthMonitor


class FakeFacade:
    def __init__(self):
        self.calls = 0
        self.mutation_calls = 0

    def diagnose(self):
        self.calls += 1
        return type("Response", (), {"message": "health looks normal"})()


class HealthMonitorTests(unittest.TestCase):
    def test_monitor_is_disabled_by_default(self):
        old = os.environ.pop("JARVIS_HEALTH_MONITOR", None)
        try:
            monitor = HealthMonitor.from_environment(FakeFacade())
            self.assertFalse(monitor.enabled)
        finally:
            if old is not None:
                os.environ["JARVIS_HEALTH_MONITOR"] = old

    def test_monitor_reports_without_mutating(self):
        facade = FakeFacade()
        monitor = HealthMonitor(facade, interval_seconds=60, enabled=True)
        result = monitor.snapshot()
        self.assertEqual(result["message"], "health looks normal")
        self.assertEqual(facade.mutation_calls, 0)
        self.assertEqual(facade.calls, 1)


if __name__ == "__main__":
    unittest.main()
