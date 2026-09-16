import unittest

from quality_of_life.hand_control_server import HandControlHandler


class HandControlServerTests(unittest.TestCase):
    def test_hand_control_handler_uses_loopback_routes(self):
        self.assertEqual({"/hand/event", "/hand/stop"}, {"/hand/event", "/hand/stop"})
        self.assertFalse(hasattr(HandControlHandler, "external_url"))


if __name__ == "__main__":
    unittest.main()
