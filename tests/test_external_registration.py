import unittest

from quality_of_life import default_registry, ExternalSkillRegistry, HindsightMemoryBridge


class ExternalRegistrationTests(unittest.TestCase):
    def test_external_integrations_are_registered_without_removing_existing_tools(self):
        names = default_registry().names()
        self.assertIn("workflows", names)
        self.assertIn("external_integrations", names)
        self.assertIn("computer", names)

    def test_external_registry_resolves_without_network_access(self):
        registry = default_registry()
        target = registry.get("external_integrations").resolve()
        self.assertIs(target, ExternalSkillRegistry)

    def test_hindsight_bridge_fails_closed_when_unconfigured(self):
        bridge = HindsightMemoryBridge("")
        self.assertFalse(bridge.configured)
        with self.assertRaises(RuntimeError):
            bridge.recall("jarvis", "test")


if __name__ == "__main__":
    unittest.main()
