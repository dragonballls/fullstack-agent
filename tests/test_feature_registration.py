import unittest

from quality_of_life import Capability, CapabilityPolicy, JarvisRuntime, default_registry


class FeatureRegistrationTests(unittest.TestCase):
    def test_new_services_are_registered_without_removing_existing_tools(self):
        runtime = JarvisRuntime(CapabilityPolicy())
        names = runtime.available_tools()
        self.assertIn("workflows", names)
        self.assertIn("family_locations", names)
        self.assertIn("gods_eye", names)
        self.assertIn("computer", names)

    def test_family_location_capability_is_read_only_by_default(self):
        policy = CapabilityPolicy()
        self.assertFalse(policy.needs_confirmation(Capability.FAMILY_LOCATION_READ))
        with self.assertRaises(PermissionError):
            policy.check(Capability.FAMILY_LOCATION_READ)

    def test_manifest_resolves_new_services_without_network_access(self):
        registry = default_registry()
        workflow_store = registry.get("workflows").resolve()
        family_service = registry.get("family_locations").resolve()
        self.assertIsNotNone(workflow_store)
        self.assertIsNotNone(family_service)


if __name__ == "__main__":
    unittest.main()
