import unittest

from quality_of_life.intents import parse_intent
from quality_of_life.manifest import default_registry
from windows_maintenance import MaintenanceFacade, RiskClass


class WindowsMaintenanceIntegrationTests(unittest.TestCase):
    def test_registry_exposes_maintenance_lazily(self):
        spec = default_registry().get("windows_maintenance")
        self.assertEqual(spec.factory, "windows_maintenance.facade.MaintenanceFacade")

    def test_intent_parser_routes_maintenance_requests(self):
        intent = parse_intent("diagnose my PC")
        self.assertEqual(intent.kind, "windows_maintenance")

    def test_package_imports_without_windows_execution(self):
        facade = MaintenanceFacade()
        self.assertIsNotNone(facade)
        self.assertEqual(RiskClass.HIGH_RISK.value, "HIGH_RISK")


if __name__ == "__main__":
    unittest.main()
