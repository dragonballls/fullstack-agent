import unittest

from quality_of_life.capabilities import operation
from quality_of_life.manifest import default_registry


class HandControlCatalogTests(unittest.TestCase):
    def test_hand_control_operations_are_cataloged(self):
        self.assertEqual(operation("hand_control.start").capability.value, "mouse.control")
        self.assertEqual(operation("hand_control.stop").capability.value, "mouse.control")

    def test_hand_control_tool_is_discoverable(self):
        self.assertIn("hand_control", default_registry().names())


if __name__ == "__main__":
    unittest.main()
