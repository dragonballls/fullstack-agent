from __future__ import annotations

import unittest

from quality_of_life.capabilities import OPERATION_CATALOG
from quality_of_life.manifest import default_registry
from quality_of_life.permissions import Capability, CapabilityPolicy
from quality_of_life.runtime import JarvisRuntime


class UniversalIntegrationTests(unittest.TestCase):
    def test_registered_tools_are_importable_without_instantiation(self):
        registry = default_registry()
        for name in registry.names():
            self.assertIsNotNone(registry.get(name).resolve())

    def test_catalog_capabilities_exist_in_policy_enum(self):
        for spec in OPERATION_CATALOG:
            self.assertIsInstance(spec.capability, Capability)

    def test_runtime_registers_universal_operations_without_executing_them(self):
        runtime = JarvisRuntime(CapabilityPolicy())
        self.assertIn("files", runtime.available_tools())
        self.assertIn("applications", runtime.available_tools())
        self.assertIn("browser_registry", runtime.available_tools())
        self.assertIn("system", runtime.available_tools())
        self.assertIn("scheduler", runtime.available_tools())
        self.assertEqual(runtime._instances, {})


if __name__ == "__main__":
    unittest.main()
